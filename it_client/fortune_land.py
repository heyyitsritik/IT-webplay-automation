from __future__ import annotations


async def fortune_land(client, rob=False):
    """Run Fortune Land cultivation and optionally one robbery."""

    print("Checking Fortune Land state...")

    state = await client.request("fd.a")

    print("fd.a:")
    print(state)

    data = state.get("d", {}).get("d", {})
    info = data.get("i", {})

    status = info.get("status", 0)
    practice_time = int(info.get("practiceTime", 0) or 0)

    print(f"Fortune Land status: {status}")
    print(f"Practice time: {practice_time}")

    # Claim completed reward if applicable.
    if status == 1 and practice_time == 0:
        print("Fortune Land is active but has no timer.")
    elif status == 0:
        print("No active Fortune Land session.")

    # Start a new 3-hour session if none is active.
    if status == 0:
        print("Starting Fortune Land...")

        result = await client.request("fd.b")

        print("fd.b:")
        print(result)

        print("Fortune Land started.")

    # Optional robbery.
    if rob:
        print("\nFinding Fortune Land targets...")

        targets = await client.request("fd.f")

        print("fd.f:")
        print(targets)

        print("\nRobbery test using captured target dUid=94...")

        result = await client.request(
            "fd.d",
            dUid="94",
        )

        print("fd.d:")
        print(result)

        print("Robbery finished.")