"""Record a real browser session: every WebSocket frame (decoded) plus game HTTP calls.

Usage (credentials come from the environment, never from files in the repo):
    export IT_USER=... IT_PASS=... IT_ZONE=E104
    python -m it_client.record --out recordings/earth.jsonl

A Chromium window opens on the game. Do ONE task at a time by hand. Before each task,
type a label in the terminal (e.g. `soul_wander`) and press Enter, so the catalog tool
can tell which frames belong to which task. Type `q` to finish.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

from .auth import game_url, login, parse_zone
from .codec import decode_client_frame, decode_server_frame

SECRET_QS = re.compile(r"(accessToken|token|password|user_name)=[^&\s\"']+")


def redact_url(url: str) -> str:
    return SECRET_QS.sub(r"\1=<redacted>", url)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"recordings/session-{int(time.time())}.jsonl")
    ap.add_argument("--zone", default=os.environ.get("IT_ZONE", "E"))
    args = ap.parse_args()

    user, password = os.environ["IT_USER"], os.environ["IT_PASS"]
    region, _ = parse_zone(args.zone)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fh = out.open("a", encoding="utf-8")

    def write(rec: dict) -> None:
        rec["t"] = round(time.time(), 3)
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()

    def on_frame(direction: str, ws_url: str, payload: bytes | str) -> None:
        if isinstance(payload, str):
            write({
                "kind": "ws_text",
                "dir": direction,
                "ws": ws_url,
                "text": payload[:2000]
            })
            return

        try:
            decoded = (
                decode_client_frame(payload)
                if direction == "out"
                else decode_server_frame(payload)
            )
            write({
                "kind": "ws",
                "dir": direction,
                "ws": ws_url,
                "decoded": decoded
            })
        except Exception as exc:
            write({
                "kind": "ws_raw",
                "dir": direction,
                "ws": ws_url,
                "error": str(exc),
                "hex": payload.hex()
            })

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        headers={"User-Agent": "Mozilla/5.0"},
        ) as http:
        session = await login(http, user, password, parse_zone(args.zone)[1])

    url = game_url(session.access_token, region)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--window-size=600,800"]
        )

        ctx = await browser.new_context(
            viewport={"width": 500, "height": 730},
            device_scale_factor=1
        )

        page = await ctx.new_page()

        def on_ws(ws) -> None:
            write({"kind": "ws_open", "ws": ws.url})
            ws.on("framesent", lambda p: on_frame("out", ws.url, p))
            ws.on("framereceived", lambda p: on_frame("in", ws.url, p))
            ws.on("close", lambda *_: write({
                "kind": "ws_close",
                "ws": ws.url
            }))

        async def on_response(resp) -> None:
            if "hkpctimes" not in resp.url:
                return

            try:
                body = (await resp.text())[: (None if "centerLogin" in resp.url else 3000)]
            except Exception:
                body = None

            write({
                "kind": "http",
                "method": resp.request.method,
                "url": redact_url(resp.url),
                "status": resp.status,
                "body": body
            })

        page.on("websocket", on_ws)
        page.on(
            "response",
            lambda r: asyncio.create_task(on_response(r))
        )

        await page.goto(url)

        print(
            "Game open. Type a label + Enter before each manual task; `q` to quit."
        )

        loop = asyncio.get_running_loop()

        while True:
            try:
                line = (
                    await loop.run_in_executor(
                        None,
                        input,
                        "label> "
                    )
                ).strip()
            except EOFError:
                break

            if line.lower() in {"q", "quit"}:
                break

            if line:
                write({
                    "kind": "marker",
                    "label": line
                })

        await browser.close()

    fh.close()

    print(
        f"Saved {out}. It contains session hashes: scrub before sharing."
    )


if __name__ == "__main__":
    asyncio.run(main())