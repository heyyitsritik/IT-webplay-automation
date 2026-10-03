import json

from it_client.codec import (decode_client_frame, decode_server_frame,
                             encode_client_frame)

# Real browser frame captured by you (client -> server). Contains no secrets.
SYS_A_FRAME = bytes.fromhex(
    "0400003a7b2263727970746f223a223972535873666d756b31783144464455396c74732b30"
    "75765a6c774f2f706a53433738524931356a79436f3d227d00"
)

# Real server frame (server -> client), a 'tpp.a' reply with reqId 13.
TPP_A_FRAME = bytes.fromhex(
    "000000018a7b2272223a226d70222c2274797065223a342c2264223a7b2274223a227470702e61222c"
    "227363223a313739303432383633332e3833383933372c2264223a7b2262696e64223a312c22666f63"
    "7573223a302c226662427574746f6e223a312c226e657742696e645374617465223a66616c73652c22"
    "6e657742696e644177617264223a5b7b226974656d4964223a31313031312c226e756d223a317d2c7b"
    "226974656d4964223a313030312c226e756d223a31307d2c7b226974656d4964223a31303231342c22"
    "6e756d223a32307d2c7b226974656d4964223a313033302c226e756d223a31303030307d5d2c22666f"
    "637573526577617264223a5b5d2c2262696e64526577617264223a5b7b2270726f704964223a313030"
    "322c226e756d223a323030307d2c7b2270726f704964223a313030332c226e756d223a323030307d2c"
    "7b2270726f704964223a313031302c226e756d223a337d5d2c227265714964223a31332c2273223a30"
    "7d7d7d"
)


def test_decode_real_client_frame():
    assert decode_client_frame(SYS_A_FRAME) == {"reqId": 27, "route": "sys.a"}


def test_encode_reproduces_real_frame_byte_for_byte():
    assert encode_client_frame({"reqId": 27, "route": "sys.a"}) == SYS_A_FRAME


def test_decode_real_server_frame():
    (msg,) = decode_server_frame(TPP_A_FRAME)
    assert msg["d"]["t"] == "tpp.a"
    assert msg["d"]["d"]["reqId"] == 13 and msg["d"]["d"]["s"] == 0
    assert msg["d"]["d"]["newBindAward"][1] == {"itemId": 1001, "num": 10}


def test_roundtrip_drops_null_keys_like_js():
    frame = encode_client_frame({"route": "x", "a": None, "b": [None, 1]})
    assert decode_client_frame(frame) == {"route": "x", "b": [None, 1]}


def test_compressed_frame():
    import zlib
    payload = json.dumps({"r": "mp", "d": {"t": "z"}}).encode()
    frame = bytes([1, 0, 0, 0, 1]) + zlib.compress(payload)
    assert decode_server_frame(frame)[0]["d"]["t"] == "z"
