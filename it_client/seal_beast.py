from __future__ import annotations


async def seal_beast(client, attempts: int = 1):
    print("Checking Seal Beast state...")

    state = await client.request("bs.a")
    print("bs.a:")
    print(state)

    data = state.get("d", {}).get("d", {})
    bosses = data.get("bossIds", [])
    available = int(data.get("num", 0) or 0)

    print(f"Seal Beast attempts available: {available}")
    print(f"Available beasts: {bosses}")

    if available <= 0 or not bosses:
        print("No Seal Beast attempts available.")
        return

    # For now, use the known-good Level 5 beast.
    level5 = next(
        (boss for boss in bosses if boss.get("lv") == 5),
        None,
    )

    if level5 is None:
        print("Level 5 beast not available.")
        return

    runs = min(attempts, available)

    for i in range(runs):
        print(f"\nSeal Beast attempt {i + 1}/{runs}")
        print(f"Attacking id={level5['id']}, lv={level5['lv']}")

        result = await client.request(
            "bs.b",
            id=level5["id"],
            lv=level5["lv"],
        )

        print("bs.b:")
        print(result)

        fight = (
            result
            .get("d", {})
            .get("d", {})
            .get("fightLog", {})
        )

        if fight.get("w") == 1:
            print("✅ Seal Beast defeated.")
        else:
            print("❌ Seal Beast attack failed.")