from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _extract_assignment_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def test_env_example_contains_required_runtime_contract_keys() -> None:
    keys = _extract_assignment_keys(REPO_ROOT / ".env.example")

    required = {
        "ENVIRONMENT",
        "DATABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_JWT_SECRET",
        "ENCRYPTION_KEY",
        "KDF_SALT",
        "CSRF_SECRET_KEY",
        "ADMIN_API_KEY",
        "LLM_PROVIDER",
        "APP_RUNTIME_DATA_DIR",
    }

    missing = required - keys
    assert not missing, f".env.example missing keys: {sorted(missing)}"


def test_env_example_excludes_retired_runtime_contract_keys() -> None:
    keys = _extract_assignment_keys(REPO_ROOT / ".env.example")

    forbidden = {
        "REDIS_URL",
        "UPSTASH_REDIS_URL",
        "UPSTASH_REDIS_TOKEN",
        "CIRCUIT_BREAKER_DISTRIBUTED_STATE",
        "CIRCUIT_BREAKER_DISTRIBUTED_KEY_PREFIX",
        "SENTRY_DSN",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_LOGS_EXPORT_ENABLED",
    }

    present = forbidden & keys
    assert not present, f".env.example still exposes retired keys: {sorted(present)}"
