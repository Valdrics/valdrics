
from __future__ import annotations

import argparse

from scripts.plugin_registry_verification import REQUIRED_PLUGIN_CATEGORIES, verify_provider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify optimization plugin registration.")
    parser.add_argument(
        "--provider",
        choices=sorted(REQUIRED_PLUGIN_CATEGORIES),
        default="aws",
        help="Provider to verify. Defaults to aws.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    print("Verifying Plugin Registry...")
    result = verify_provider(args.provider)

    for category in result.categories:
        print(f"✅ {result.provider.upper()} Plugin Registered: {category}")

    if result.missing:
        print(f"FAILURE: Missing plugins: {', '.join(result.missing)}")
        return 1

    print(f"SUCCESS: All required {result.provider.upper()} plugins are registered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
