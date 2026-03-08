from __future__ import annotations

from datetime import date

import pytest

from app.modules.governance.domain.security.compliance_pack_contracts import (
    CompliancePackValidationError,
)
from app.modules.governance.domain.security.compliance_pack_support import (
    normalize_optional_provider,
    resolve_window,
)


def test_normalize_optional_provider_rejects_unsupported_values() -> None:
    with pytest.raises(CompliancePackValidationError, match="Unsupported focus_provider"):
        normalize_optional_provider(
            provider="oracle",
            provider_name="focus_provider",
        )


def test_resolve_window_raises_domain_validation_error_for_inverted_dates() -> None:
    with pytest.raises(CompliancePackValidationError, match="window must be ordered"):
        resolve_window(
            start=date(2026, 3, 8),
            end=date(2026, 3, 1),
            default_start=date(2026, 2, 1),
            default_end=date(2026, 2, 28),
            error_detail="window must be ordered",
        )


def test_resolve_window_uses_defaults_when_inputs_missing() -> None:
    start, end = resolve_window(
        start=None,
        end=None,
        default_start=date(2026, 2, 1),
        default_end=date(2026, 2, 28),
        error_detail="window must be ordered",
    )

    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)
