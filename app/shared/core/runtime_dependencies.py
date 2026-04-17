"""Runtime dependency validation for production startup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
import sys

import structlog

from app.shared.core.config import ENV_PRODUCTION, ENV_STAGING, Settings
from app.shared.orchestration.contracts import observability_backend

logger = structlog.get_logger()
SUPPORTED_PYTHON_MAJOR_MINOR = (3, 12)


def _module_available(module_name: str) -> bool:
    """Return True when the import target can be resolved."""
    return find_spec(module_name) is not None


def _parse_iso8601_utc(value: str) -> datetime:
    """Parse ISO-8601 and normalize to UTC."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timezone offset required")
    return parsed.astimezone(timezone.utc)


def _is_supported_python_runtime() -> bool:
    """Return True when the interpreter matches the repository runtime contract."""
    version = sys.version_info
    return (version.major, version.minor) == SUPPORTED_PYTHON_MAJOR_MINOR


def _validate_supported_python_runtime() -> None:
    """Fail fast when startup uses an interpreter outside the supported contract."""
    if _is_supported_python_runtime():
        return

    version = sys.version_info
    expected = ".".join(str(part) for part in SUPPORTED_PYTHON_MAJOR_MINOR)
    current = f"{version.major}.{version.minor}.{version.micro}"
    raise RuntimeError(
        "Unsupported Python runtime "
        f"{current}. Valdrics is pinned to Python {expected}.x. "
        "Use the repository .python-version for local uv workflows and "
        "Python 3.12 container/runtime images for deployment."
    )


def _validate_prophet_break_glass(settings: Settings, strict_env: bool) -> tuple[str, datetime] | None:
    """
    Validate break-glass metadata for Prophet fallback in strict env.

    Returns:
        tuple(reason, expires_at_utc) when break-glass is active and valid.
        None when break-glass is not active.
    """
    if not strict_env or not settings.FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK:
        return None

    reason = str(settings.FORECASTER_BREAK_GLASS_REASON or "").strip()
    if len(reason) < 10:
        raise RuntimeError(
            "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK=true in staging/production "
            "requires FORECASTER_BREAK_GLASS_REASON (min 10 chars)."
        )

    expires_raw = str(settings.FORECASTER_BREAK_GLASS_EXPIRES_AT or "").strip()
    if not expires_raw:
        raise RuntimeError(
            "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK=true in staging/production "
            "requires FORECASTER_BREAK_GLASS_EXPIRES_AT (ISO-8601 UTC timestamp)."
        )
    try:
        expires_at = _parse_iso8601_utc(expires_raw)
    except ValueError as exc:
        raise RuntimeError(
            "FORECASTER_BREAK_GLASS_EXPIRES_AT must be a valid ISO-8601 timestamp "
            "with timezone (e.g. 2026-02-22T10:00:00Z)."
        ) from exc

    now_utc = datetime.now(timezone.utc)
    if expires_at <= now_utc:
        raise RuntimeError(
            "FORECASTER_BREAK_GLASS_EXPIRES_AT is in the past. "
            "Renew or disable FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK."
        )
    max_duration_hours = int(
        getattr(settings, "FORECASTER_BREAK_GLASS_MAX_DURATION_HOURS", 168)
    )
    if max_duration_hours <= 0:
        raise RuntimeError(
            "FORECASTER_BREAK_GLASS_MAX_DURATION_HOURS must be >= 1 in strict environments."
        )
    max_expires_at = now_utc + timedelta(hours=max_duration_hours)
    if expires_at > max_expires_at:
        raise RuntimeError(
            "FORECASTER_BREAK_GLASS_EXPIRES_AT exceeds the allowed strict-environment "
            f"window of {max_duration_hours} hour(s)."
        )

    return reason, expires_at


def validate_runtime_dependencies(settings: Settings) -> None:
    """
    Enforce required runtime dependencies for strict environments.

    Rules:
    - Production/staging: ``tiktoken`` is mandatory for accurate LLM budgeting.
    - Production/staging: Cloud Trace exporter is mandatory.
    - Production/staging: structured JSON logs are emitted to stdout/stderr for
      Cloud Run integrated logging.
    - ``prophet`` remains optional, controlled by fallback policy:
      ``FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK``.
    """
    if settings.TESTING:
        logger.info("runtime_dependency_validation_skipped_testing")
        return

    _validate_supported_python_runtime()

    strict_env = settings.ENVIRONMENT in {ENV_PRODUCTION, ENV_STAGING}
    break_glass = _validate_prophet_break_glass(settings, strict_env)
    selected_observability_backend = observability_backend(settings)
    if selected_observability_backend.value != "gcp":
        raise RuntimeError("OBSERVABILITY_BACKEND must resolve to gcp.")

    if strict_env and not _module_available("tiktoken"):
        raise RuntimeError(
            "Missing required dependency 'tiktoken' in production/staging. "
            "Install tiktoken to ensure accurate LLM token accounting."
        )

    if strict_env and not _module_available("opentelemetry.exporter.cloud_trace"):
        raise RuntimeError(
            "Cloud Trace export is configured for production/staging but the exporter dependency is missing."
        )

    prophet_available = _module_available("prophet")
    if prophet_available:
        logger.info("prophet_dependency_available")
        return

    if strict_env and not settings.FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK:
        raise RuntimeError(
            "Missing required dependency 'prophet' in production/staging. "
            "Install prophet, or set FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK=true "
            "as a temporary break-glass override."
        )

    log_method = logger.warning if strict_env else logger.debug
    log_method(
        "prophet_unavailable_using_holt_winters_fallback",
        environment=settings.ENVIRONMENT,
        strict_env=strict_env,
        break_glass_override=bool(break_glass),
        break_glass_reason=(break_glass[0] if break_glass else None),
        break_glass_expires_at=(
            break_glass[1].isoformat() if break_glass else None
        ),
    )
