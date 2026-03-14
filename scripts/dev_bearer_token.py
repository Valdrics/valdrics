#!/usr/bin/env python3
"""Retired local bearer-token helper.

This script previously minted live bearer tokens directly from the active
runtime secret and database state. That behavior has been removed because it
bypassed the guarded break-glass controls in `scripts/emergency_token.py`.
"""

from __future__ import annotations

import sys

DEPRECATION_MESSAGE = (
    "scripts/dev_bearer_token.py is retired. "
    "Use scripts/emergency_token.py for the guarded break-glass token flow."
)


def main() -> int:
    print(DEPRECATION_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
