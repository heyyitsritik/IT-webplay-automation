from __future__ import annotations

import asyncio


async def fishing(client, casts: int = 2, delay: float = 10.0):
    """Run fishing casts using the known web protocol."""

    state = await client.request("f.a")

    print("Fishing state:")
    print(state)

    data = state.get("d", {}).get("d", state.get("d", {}))

    in_num = data.get("inNum", 0)
    throw_num = data.get("throwNum", 0)
    fishing_id = data.get("id", 0)

    print(f"Fishing sessions remaining: {in_num}")
    print(f"Casts remaining: {throw_num}")
    print(f"Current fishing id: {fishing_id}")

    if throw_num <= 0:
        print("No casts remaining.")
        return

    # If we're not already inside a fishing session, enter one.
    if fishing_id == 0:
        print("Starting fishing session...")
        start = await client.request("f.b", id=2)
        print("f.b:", start)

    casts_to_make = min(casts, throw_num)

    for i in range(casts_to_make):
        print(f"\nCast {i + 1}/{casts_to_make}")

        result = await client.request("f.c", hook=1)

        print("Result:")
        print(result)

        if i < casts_to_make - 1:
            await asyncio.sleep(delay)

    print("\nFishing finished.")