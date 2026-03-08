from __future__ import annotations

from typing import Any

from app.shared.core.config import get_settings


def resolve_outbound_tls_verification(
    verify_requested: bool,
    *,
    settings_obj: Any | None = None,
) -> bool:
    """
    Normalize outbound TLS verification posture for strict environments.

    Strict environments must fail closed on ``verify=False`` unless an explicit,
    time-bounded break-glass override is enabled in configuration.
    """
    if verify_requested:
        return True

    settings = settings_obj or get_settings()
    if not getattr(settings, "is_strict_environment", False):
        return False

    if bool(getattr(settings, "ALLOW_INSECURE_OUTBOUND_TLS", False)):
        return False

    raise ValueError(
        "verify_ssl=false is forbidden in staging/production unless "
        "ALLOW_INSECURE_OUTBOUND_TLS=true with active break-glass metadata."
    )


__all__ = ["resolve_outbound_tls_verification"]
