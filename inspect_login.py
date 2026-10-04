import json
import glob
import base64

files = glob.glob("recordings/*.jsonl")
f = sorted(files)[-1]

print("Reading:", f)

for line in open(f, encoding="utf-8"):
    e = json.loads(line)

    if e.get("kind") == "http" and "centerLogin" in e.get("url", ""):
        print("\nFound centerLogin:")
        
        body = e.get("body")
        if not body:
            print("No response body captured.")
            continue

        try:
            b = json.loads(body)
        except Exception as exc:
            print("Could not parse body:", exc)
            continue

        print("\nResponse structure:")
        print({
            k: (type(v).__name__, len(str(v)))
            for k, v in b.items()
        })

        al = b.get("al", [])

        print("\nMatching sId 131 entries:")
        print([
            {
                k: ("<redacted>" if k in {"h", "hash", "token", "accessToken"} else v)
                for k, v in s.items()
                if k not in {"h", "hash", "token", "accessToken"}
            }
            for s in al
            if s.get("sId") == 131
        ])

        h = b.get("h")

        if h:
            try:
                print("\nh exists")
                print("h string length:", len(h))
                print("h decoded bytes:", len(base64.b64decode(h)))
            except Exception as exc:
                print("Could not decode h:", exc)
        else:
            print("\nNo top-level h found.")

        print("\nDone.")
