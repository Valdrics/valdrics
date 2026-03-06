from __future__ import annotations

import pytest

from app.shared.core.cors_policy import (
    InvalidCorsConfiguration,
    resolve_cors_allowed_origins,
)


def test_resolve_cors_allowed_origins_normalizes_entries() -> None:
    out = resolve_cors_allowed_origins(
        [" https://app.valdrics.io ", "", "https://ops.valdrics.io"],
        allow_credentials=True,
    )

    assert out == ["https://app.valdrics.io", "https://ops.valdrics.io"]


def test_resolve_cors_allowed_origins_rejects_wildcard_with_credentials() -> None:
    with pytest.raises(InvalidCorsConfiguration, match="allow_credentials=True"):
        resolve_cors_allowed_origins(
            ["https://app.valdrics.io", "*"],
            allow_credentials=True,
        )


def test_resolve_cors_allowed_origins_allows_wildcard_without_credentials() -> None:
    out = resolve_cors_allowed_origins(
        ["*"],
        allow_credentials=False,
    )

    assert out == ["*"]

