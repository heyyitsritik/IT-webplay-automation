"""HTTP login flow, ported from site/webBrowser.js (login is a POST with query params)."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import httpx

API = "https://m-xmjen.hkpctimes.com/api/index.php"
GAME_PAGE = "https://xztwcdn.hkpctimes.com/staticOne/global.html"
GAME_ID = "1704"


class LoginError(RuntimeError):
    pass


@dataclass
class Session:
    device_no: str
    token: str
    access_token: str
    down_url: str
    server_id: int
    server_hash: str
    ws_url: str


def parse_zone(zone: str) -> tuple[str, int | None]:
    """'E104' -> ('E', 104); 'E' -> ('E', None)."""
    m = re.fullmatch(r"([EW])(\d*)", zone.strip().upper())
    if not m:
        raise ValueError(f"unrecognised zone {zone!r} (expected like E104 or W12)")
    return m.group(1), int(m.group(2)) if m.group(2) else None


def game_url(access_token: str, region: str) -> str:
    """Same URL the account-manager site opens. '+' is kept literal on purpose."""
    url = f"{GAME_PAGE}?locate=en_us&pf=gcathkh5&gv=release&accessToken={access_token}"
    if region == "E":
        url += "&timeZone=+5"
    elif region == "W":
        url += "&timeZone=-5"
    return url


async def center_login(
    http: httpx.AsyncClient,
    access_token: str,
    server_id: int,
) -> tuple[str, str]:
    r = await http.get(
        "https://xztwgame.hkpctimes.com/web/centerLogin.php",
        params={
            "language": "fan",
            "accessToken": access_token,
            "gcatId": "",
            "loginType": "gcathkAndroid1",
            "time": "undefined",
            "qTime": "undefined",
        },
    )
    r.raise_for_status()

    body = r.json()

    server = next(
        (s for s in body["al"] if s["sId"] == server_id),
        None,
    )

    if server is None:
        raise LoginError(f"server {server_id} not found in centerLogin")

    server_hash = body.get("h")
    if not server_hash:
        raise LoginError("centerLogin did not return h")

    ws_url = f"wss://{server['wsHost']}/{server['wsPort']}"

    return server_hash, ws_url


async def login(
    http: httpx.AsyncClient,
    user: str,
    password: str,
    server_id: int,
    device_no: str | None = None,
) -> Session:
    device_no = device_no or str(uuid.uuid4())

    base = {
        "phone_brand": "oneplus",
        "device_no": device_no,
        "lang": "en-US",
        "promote": "17",
    }

    r = await http.post(
        API,
        params={
            **base,
            "user_name": user,
            "password": password,
            "action": "user.login",
            "game_id": GAME_ID,
        },
    )
    r.raise_for_status()
    body = r.json()

    if not body.get("status"):
        raise LoginError(f"user.login failed: {body.get('msg') or body}")

    token = body["token"]

    r = await http.get(
        API,
        params={
            **base,
            "token": token,
            "action": "game.info",
            "id": GAME_ID,
        },
    )
    r.raise_for_status()
    info = r.json()

    if not info.get("status"):
        raise LoginError(f"game.info failed: {info.get('msg') or info}")

    # server.tap returned status=false in your tests and the flow still worked; ignore the result.
    await http.get(
        API,
        params={
            **base,
            "token": token,
            "action": "server.tap",
            "id": GAME_ID,
        },
    )

    down_url = info["down_url"]

    # Don't use parse_qs here because it converts '+' to a space.
    match = re.search(r"[?&]accessToken=([^&#]+)", down_url)
    if not match:
        raise LoginError("accessToken missing from down_url")

    access_token = unquote(match.group(1))

    server_hash, ws_url = await center_login(
        http,
        access_token,
        server_id,
    )

    return Session(
        device_no=device_no,
        token=token,
        access_token=access_token,
        down_url=down_url,
        server_id=server_id,
        server_hash=server_hash,
        ws_url=ws_url,
    )