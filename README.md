# IT protocol toolkit

Codec, HTTP login, async WebSocket client, browser recorder and route catalog for the
Immortal Taoist web client. Local use only.

## Setup
    pip install -r requirements.txt
    playwright install chromium
    export IT_USER=...  IT_PASS=...  IT_ZONE=E104     # never commit these
    pytest

## Step 1: record the action catalog
    python -m it_client.record --out recordings/earth.jsonl
Chromium opens on the game. For each task: type a label (e.g. `soul_wander`) in the
terminal, press Enter, then do that task once by hand. `q` to finish.
The file contains session hashes: do not share it as-is.

    python -m it_client.catalog recordings/earth.jsonl > catalog.json
The catalog redacts hash/token fields and lists, per task, the routes sent and replies seen.
Send me catalog.json and we turn each entry into a task module.

## What is verified vs not
Verified (tests use your captured frames): client frame encode/decode, byte-for-byte;
server plain-JSON decode; reqId/response correlation against a mock server.
Not verified (needs your network): auth.login (port of webBrowser.js), live connection,
and where `hash` / `sId` for g.enter come from. The recorder logs the game's HTTP calls
(tokens redacted) so we can find that out.
Unknown: server frame header meaning (5 bytes, last varies), heartbeat/`syn` rules,
type-1 (compressed) framing details.
