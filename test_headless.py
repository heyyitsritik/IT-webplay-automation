import asyncio
import os

import httpx
from dotenv import load_dotenv
from websockets import client

from it_client.seal_beast import seal_beast
from it_client.fortune_land import fortune_land
from it_client.auth import login, parse_zone
from it_client.client import GameClient, status_of, topic_of
from it_client.fishing import fishing
from it_client.soul_wander import soul_wander


load_dotenv()


async def main():
    user = os.environ["IT_USER"]
    password = os.environ["IT_PASS"]
    zone = os.environ["IT_ZONE"]

    region, server_id = parse_zone(zone)

    if server_id is None:
        raise ValueError(
            f"IT_ZONE must include a server number, got: {zone}"
        )

    print(f"Testing server: {server_id}")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        headers={"User-Agent": "Mozilla/5.0"},
    ) as http:

        # -------------------------
        # LOGIN
        # -------------------------
        print("Logging in...")

        session = await login(
            http,
            user,
            password,
            server_id,
        )

        print("Login successful")
        print(f"WebSocket: {session.ws_url}")

        # -------------------------
        # WEBSOCKET
        # -------------------------
        async with GameClient(session) as client:

            print("Connected to WebSocket")
            print("Sending g.enter...")

            result = await client.authenticate(http)

            print("\ng.enter response:")
            print(result)

            print("\nStatus:", status_of(result))
            print("Topic:", topic_of(result))

            # -------------------------
            # SOUL WANDERING
            # -------------------------
            print("\n=== SOUL WANDERING ===")

            await soul_wander(
                client,
                runs=1,
            )
            # -------------------------
            # Fortune Land
            # -------------------------

            print("\n=== FORTUNE LAND ===")
            await fortune_land(client,rob = True)

            # -------------------------
            # Seal beast
            # -------------------------
            print("\n=== SEAL BEAST ===")
            await seal_beast(client, attempts=1)

            # -------------------------
            # FISHING
            # -------------------------
            print("\n=== FISHING ===")

            await fishing(
                client,
                casts=2,
                delay=10,
            )


if __name__ == "__main__":
    asyncio.run(main())