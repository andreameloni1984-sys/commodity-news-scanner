#!/usr/bin/env python3
"""Disabled legacy Forex patch utility.

The former script inserted a Forex aggressive block into Telegram's GAGARIN
interface. GAGARIN is restricted to the user's eight-commodity universe.
This utility intentionally performs no file or repository changes.
"""


def main() -> int:
    print("DISABLED: legacy Forex patch is outside GAGARIN's eight-commodity scope.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
