from collections.abc import Callable
from typing import Any

from app.modules.enforcement.domain.service_utils import (
    _gate_lock_timeout_seconds as _gate_lock_timeout_seconds_impl,
)
from app.shared.core.config import get_settings


def gate_lock_timeout_seconds(
    *,
    get_settings_fn: Callable[[], Any] = get_settings,
) -> float:
    raw = getattr(get_settings_fn(), "ENFORCEMENT_GATE_TIMEOUT_SECONDS", 2.0)
    try:
        gate_timeout = float(raw)
    except (TypeError, ValueError):
        return _gate_lock_timeout_seconds_impl()
    gate_timeout = max(0.05, min(gate_timeout, 30.0))
    return max(0.05, min(gate_timeout * 0.8, 5.0))
