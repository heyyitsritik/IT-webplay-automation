import json

h = None
hash_ = None

with open("recordings/login-test.jsonl", encoding="utf-8") as f:
    for line in f:
        e = json.loads(line)

        if e.get("kind") == "http" and "centerLogin" in e.get("url", ""):
            body = json.loads(e["body"])
            h = body.get("h")

        if (
            e.get("kind") == "ws"
            and e.get("dir") == "out"
            and e.get("decoded", {}).get("route") == "g.enter"
        ):
            hash_ = e["decoded"].get("hash")

print("centerLogin h found:", h is not None)
print("g.enter hash found:", hash_ is not None)
print("match:", h == hash_)