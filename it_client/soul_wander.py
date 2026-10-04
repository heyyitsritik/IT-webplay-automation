from __future__ import annotations


async def soul_wander(client, runs: int = 1):
    """Run Earth Soul Wandering."""

    print("Starting Soul Wandering...")

    result = await client.request(
        "m.h",
        mId=20,
        num=runs,
    )

    print("m.h response:")
    print(result)

    print("Soul Wandering started.")