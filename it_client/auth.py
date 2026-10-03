"""HTTP login flow, ported from site/webBrowser.js (login is a POST with query params)."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

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


async def login(http: httpx.AsyncClient, user: str, password: str) -> Session:
    device_no = str(uuid.uuid4())
    base = {"phone_brand": "oneplus", "device_no": device_no, "lang": "en-US", "promote": "17"}

    r = await http.post(API, params={**base, "user_name": user, "password": password,
                                     "action": "user.login", "game_id": GAME_ID})
    r.raise_for_status()
    body = r.json()
    if not body.get("status"):
        raise LoginError(f"user.login failed: {body.get('msg') or body}")
    token = body["token"]

    r = await http.get(API, params={**base, "token": token, "action": "game.info", "id": GAME_ID})
    r.raise_for_status()
    info = r.json()
    if not info.get("status"):
        raise LoginError(f"game.info failed: {info.get('msg') or info}")

    # server.tap returned status=false in your tests and the flow still worked; ignore the result.
    await http.get(API, params={**base, "token": token, "action": "server.tap", "id": GAME_ID})

    down_url = info["down_url"]
    qs = parse_qs(urlparse(down_url).query)
    if "accessToken" not in qs:
        raise LoginError("accessToken missing from down_url")
    return Session(device_no, token, qs["accessToken"][0], down_url)
