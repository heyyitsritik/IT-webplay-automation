"""Async WebSocket client: request/response correlation by reqId, push handlers."""
from __future__ import annotations

import asyncio
import random
from collections import deque
from typing import Any, Awaitable, Callable

import websockets

from .codec import decode_server_frame, encode_client_frame

PushHandler = Callable[[dict], Awaitable[None] | None]


class GameError(RuntimeError):
    pass


def req_id_of(msg: Any) -> int | None:
    """reqId lives at msg['d']['d']['reqId'] in responses (and flat for some messages)."""
    if not isinstance(msg, dict):
        return None
    if isinstance(msg.get("reqId"), int):
        return msg["reqId"]
    inner = msg.get("d")
    if isinstance(inner, dict):
        inner = inner.get("d")
        if isinstance(inner, dict) and isinstance(inner.get("reqId"), int):
            return inner["reqId"]
    return None


def topic_of(msg: Any) -> str | None:
    """Message topic, e.g. 'tpp.a' or 'push.msg' (msg['d']['t'])."""
    if isinstance(msg, dict) and isinstance(msg.get("d"), dict):
        t = msg["d"].get("t")
        return t if isinstance(t, str) else None
    return None


def status_of(msg: Any) -> int | None:
    """Status code 's' (0 = ok in every sample seen so far)."""
    if isinstance(msg, dict) and isinstance(msg.get("d"), dict):
        inner = msg["d"].get("d")
        if isinstance(inner, dict) and isinstance(inner.get("s"), int):
            return inner["s"]
    return None


class GameClient:
    def __init__(self, url: str, *, history: int = 500) -> None:
        self.url = url
        self._ws: Any = None
        self._reader: asyncio.Task | None = None
        self._next_req = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._waiters: list[tuple[str, asyncio.Future]] = []
        self._handlers: dict[str, list[PushHandler]] = {}
        self.events: deque[dict] = deque(maxlen=history)

    async def __aenter__(self) -> "GameClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.url, max_size=None)
        self._reader = asyncio.create_task(self._read_loop())

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._reader is not None:
            await asyncio.gather(self._reader, return_exceptions=True)

    def on(self, topic: str, handler: PushHandler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def send(self, obj: dict) -> None:
        await self._ws.send(encode_client_frame(obj))

    async def request(self, route: str, timeout: float = 15.0, **params: Any) -> dict:
        """Send {'route': route, 'reqId': n, **params} and wait for the matching reply."""
        req_id = self._next_req
        self._next_req += 1
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        try:
            await self.send({**params, "reqId": req_id, "route": route})
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(req_id, None)

    async def expect(self, topic: str, timeout: float = 15.0) -> dict:
        """Wait for the next message with this topic (e.g. the first 'push.msg')."""
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        entry = (topic, fut)
        self._waiters.append(entry)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            if entry in self._waiters:
                self._waiters.remove(entry)

    async def authenticate(self, access_token: str, timeout: float = 15.0) -> dict:
        """First packet after connecting; your Node test got a 'push.msg' with player info back."""
        waiter = asyncio.create_task(self.expect("push.msg", timeout))
        await self.send({"accessToken": access_token})
        return await waiter

    async def enter(self, server_id: int, hash_: str, version: str = "7.6.3") -> dict:
        return await self.request("g.enter", sId=server_id, hash=hash_, ver=version)

    @staticmethod
    async def pause(lo: float = 0.4, hi: float = 1.6) -> None:
        """Human-ish pacing between actions."""
        await asyncio.sleep(random.uniform(lo, hi))

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                if isinstance(raw, str):
                    continue
                try:
                    messages = decode_server_frame(raw)
                except ValueError:
                    self.events.append({"undecodable": raw.hex()})
                    continue
                for msg in messages:
                    await self._dispatch(msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            err = GameError("connection closed")
            for fut in list(self._pending.values()):
                if not fut.done():
                    fut.set_exception(err)

    async def _dispatch(self, msg: dict) -> None:
        self.events.append(msg)
        rid = req_id_of(msg)
        fut = self._pending.get(rid) if rid is not None else None
        if fut is not None and not fut.done():
            fut.set_result(msg)
        topic = topic_of(msg)
        if topic is None:
            return
        for t, waiter in list(self._waiters):
            if t == topic and not waiter.done():
                waiter.set_result(msg)
        for handler in self._handlers.get(topic, []):
            res = handler(msg)
            if asyncio.iscoroutine(res):
                await res
