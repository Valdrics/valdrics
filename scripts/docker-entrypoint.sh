#!/bin/sh
set -eu

python - <<'PY'
from app.shared.core.config import get_settings
from app.shared.core.runtime_dependencies import validate_runtime_dependencies

settings = get_settings()
validate_runtime_dependencies(settings)
print("runtime_env_validation_passed", f"environment={settings.ENVIRONMENT}")
PY

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-1}"
