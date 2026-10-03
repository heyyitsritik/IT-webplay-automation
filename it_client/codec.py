"""Codec for the Immortal Taoist web-client WebSocket protocol.

Client -> server (verified against captured browser frames):
    [0x04][payload length: 3 bytes big-endian][ {"crypto": "<base64>"} ][0x00]
    where <base64> = AES-128-ECB / PKCS7 of the request JSON, key KEY.
    The length counts the JSON wrapper plus the trailing 0x00.

Server -> client:
    type 0: plain JSON, preceded by a 5-byte header (00 00 00 01 xx). The last
            header byte varies and is NOT the JSON length, so we locate the JSON
            by scanning for '{' like the original client does.
    type 1: zlib-compressed JSON after a 5-byte header (client uses pako.inflate).
"""
from __future__ import annotations

import base64
import json
import zlib
from typing import Any, Iterator

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

KEY = b"qjf87KbsvQoh7Pfb"
CLIENT_FRAME_TYPE = 4


def _strip_none(value: Any) -> Any:
    """Mimic the JS replacer: null-valued object keys are dropped (array nulls stay)."""
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_none(v) for v in value]
    return value


def _dumps(obj: Any) -> str:
    return json.dumps(_strip_none(obj), separators=(",", ":"), ensure_ascii=False)


def encrypt_payload(obj: Any) -> str:
    cipher = AES.new(KEY, AES.MODE_ECB)
    ct = cipher.encrypt(pad(_dumps(obj).encode("utf-8"), AES.block_size))
    return base64.b64encode(ct).decode("ascii")


def decrypt_payload(b64: str) -> Any:
    cipher = AES.new(KEY, AES.MODE_ECB)
    pt = unpad(cipher.decrypt(base64.b64decode(b64)), AES.block_size)
    return json.loads(pt.decode("utf-8"))


def encode_client_frame(obj: Any) -> bytes:
    body = json.dumps({"crypto": encrypt_payload(obj)}, separators=(",", ":")).encode("utf-8")
    body += b"\x00"
    return bytes([CLIENT_FRAME_TYPE]) + len(body).to_bytes(3, "big") + body


def decode_client_frame(frame: bytes) -> Any:
    """Decode a client->server frame (used by the recorder on browser traffic)."""
    wrapper = json.loads(frame[4:].rstrip(b"\x00").decode("utf-8"))
    return decrypt_payload(wrapper["crypto"])


def _iter_json(text: str) -> Iterator[Any]:
    decoder = json.JSONDecoder()
    i = text.find("{")
    while 0 <= i < len(text):
        try:
            obj, end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        yield obj
        i = text.find("{", end)


def decode_server_frame(frame: bytes) -> list[Any]:
    """Decode a server->client frame into a list of JSON objects (usually one)."""
    if not frame:
        return []
    ftype = frame[0]
    if ftype == 0:
        data = frame[4:]
    elif ftype == 1:
        data = None
        for skip in (5, 4):
            try:
                data = zlib.decompress(frame[skip:])
                break
            except zlib.error:
                continue
        if data is None:
            raise ValueError("could not inflate type-1 frame")
    else:
        raise ValueError(f"unknown server frame type {ftype}")
    return list(_iter_json(data.decode("utf-8", errors="replace")))
