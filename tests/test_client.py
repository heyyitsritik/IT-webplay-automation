import json

import websockets

from it_client.client import GameClient, req_id_of, status_of
from it_client.codec import decode_client_frame


def server_frame(obj) -> bytes:
    body = json.dumps(obj, separators=(",", ":")).encode()
    return bytes([0, 0, 0, 1, len(body) & 0xFF]) + body


async def handler(ws):
    async for raw in ws:
        req = decode_client_frame(raw)
        if "accessToken" in req:
            await ws.send(server_frame({"r": "mp", "type": 4, "d": {"t": "push.msg", "d": {"uId": 1}}}))
        else:
            await ws.send(server_frame({"r": "mp", "type": 4, "d": {
                "t": req["route"], "sc": 1.0, "d": {"reqId": req["reqId"], "s": 0, "echo": req.get("x")}}}))


async def test_request_response_and_push():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        async with GameClient(f"ws://127.0.0.1:{port}") as game:
            push = await game.authenticate("tok")
            assert push["d"]["t"] == "push.msg"
            a = await game.request("a.b", x=1)
            b = await game.request("c.d", x=2)
            assert (req_id_of(a), req_id_of(b)) == (1, 2)
            assert status_of(a) == 0 and a["d"]["d"]["echo"] == 1 and b["d"]["d"]["echo"] == 2
