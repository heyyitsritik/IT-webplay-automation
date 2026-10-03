"""Turn a recording into an action catalog: which routes each manual task sent/received.

    python -m it_client.catalog recordings/earth.jsonl > catalog.json
Sensitive values (hash, tokens) are replaced so the output is safe to share.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

SENSITIVE = {"hash", "accessToken", "token", "password", "crypto"}
IGNORED_TOPICS = {"push.msg"}


def scrub(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if k in SENSITIVE else scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value[:3]]
    return value


def route_of(msg: dict) -> str | None:
    if "route" in msg:
        return msg["route"]
    inner = msg.get("d")
    if isinstance(inner, dict) and isinstance(inner.get("t"), str):
        return f"mp:{inner['t']}"
    return None


def build(path: str) -> dict:
    label = "unlabeled"
    out: dict = defaultdict(lambda: {"sent": {}, "received": {}})
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["kind"] == "marker":
                label = rec["label"]
            elif rec["kind"] == "ws" and rec["dir"] == "out":
                route = route_of(rec["decoded"])
                if route:
                    slot = out[label]["sent"].setdefault(route, {"count": 0, "example": scrub(rec["decoded"])})
                    slot["count"] += 1
            elif rec["kind"] == "ws" and rec["dir"] == "in":
                for msg in rec["decoded"]:
                    route = route_of(msg)
                    if route and route.split(":", 1)[-1] not in IGNORED_TOPICS:
                        slot = out[label]["received"].setdefault(route, {"count": 0, "example": scrub(msg)})
                        slot["count"] += 1
    return out


if __name__ == "__main__":
    json.dump(build(sys.argv[1]), sys.stdout, indent=2, ensure_ascii=False)
