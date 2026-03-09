from __future__ import annotations

from scripts.plugin_registry_verification import verify_providers


def main() -> int:
    print("Verifying Plugin Registry...")
    results = verify_providers()
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
