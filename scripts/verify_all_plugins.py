from __future__ import annotations

import argparse

from scripts.plugin_registry_verification import REQUIRED_PLUGIN_CATEGORIES, verify_providers


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify optimization plugin registration.")
    parser.add_argument(
        "--provider",
        dest="providers",
        action="append",
        choices=sorted(REQUIRED_PLUGIN_CATEGORIES),
        help="Only verify the specified provider. May be repeated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    print("Verifying Plugin Registry...")
    providers = tuple(args.providers) if args.providers else tuple(REQUIRED_PLUGIN_CATEGORIES)
    results = verify_providers(providers)
    missing_labels: list[str] = []

    for result in results:
        print(f"\n--- {result.provider.upper()} ---")
        for category in result.categories:
            print(f"✅ {category}")
        missing_labels.extend(f"{result.provider.upper()}: {category}" for category in result.missing)

    print("\n--- SUMMARY ---")
    if missing_labels:
        print(f"❌ FAILURE: Missing plugins: {', '.join(missing_labels)}")
        return 1

    print("🎉 SUCCESS: All required plugins are registered!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
