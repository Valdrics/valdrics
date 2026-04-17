"""Observability-specific settings validation helpers."""

from __future__ import annotations

def _normalize_environment(value: object) -> str:
    return str(value or "").strip().lower()


def validate_observability_config(
    settings_obj: object,
    *,
    env_production: str,
    env_staging: str,
) -> None:
    """Require the supported managed GCP observability contract."""
    environment = _normalize_environment(getattr(settings_obj, "ENVIRONMENT", ""))
    strict_env = environment in {env_production, env_staging}
    if not strict_env:
        return

    project_id = str(getattr(settings_obj, "GCP_PROJECT_ID", "") or "").strip()
    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID must be configured when OBSERVABILITY_BACKEND=gcp in staging/production."
        )

    if bool(getattr(settings_obj, "EXPOSE_API_DOCUMENTATION_PUBLICLY", False)):
        raise ValueError(
            "EXPOSE_API_DOCUMENTATION_PUBLICLY must be false in staging/production."
        )


__all__ = ["validate_observability_config"]
