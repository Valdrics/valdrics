
from __future__ import annotations

from scripts.plugin_registry_verification import verify_provider


def main() -> int:
    print("Verifying Plugin Registry...")
    result = verify_provider("aws")

    for category in result.categories:
        print(f"✅ AWS Plugin Registered: {category}")

    if result.missing:
        print(f"FAILURE: Missing plugins: {', '.join(result.missing)}")
        return 1

    print("SUCCESS: All required AWS plugins are registered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
