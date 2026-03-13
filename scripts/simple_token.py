#!/usr/bin/env python3
"""Retired legacy token helper.

This entrypoint is intentionally disabled. Operators must use
`scripts/emergency_token.py`, which enforces explicit break-glass controls,
environment confirmation, short TTLs, and audit attribution.
"""

from __future__ import annotations

import sys


DEPRECATION_MESSAGE = (
    "scripts/simple_token.py is retired. "
    "Use scripts/emergency_token.py for the guarded emergency-token flow."
)


def main() -> int:
    print(DEPRECATION_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
