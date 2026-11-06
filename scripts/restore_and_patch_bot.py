#!/usr/bin/env python3
"""Disabled legacy bot-restoration utility.

The former implementation wrote directly to the main branch and restored
out-of-scope FX plus manual Trading 212-vs-futures price comparisons.
Repository changes must now be made on a reviewed feature branch and proposed
through a pull request. This script intentionally performs no network or
repository writes.
"""


def main() -> int:
    print(
        "DISABLED: this legacy restore script is inert. "
        "Use a reviewed feature branch and pull request; "
        "do not write directly to main."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
