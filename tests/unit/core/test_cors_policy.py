from __future__ import annotations

import pytest

from app.shared.core.cors_policy import (
	InvalidCorsConfiguration,
	resolve_cors_allowed_origins,
	validate_strict_cors_allowed_origins,
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


def test_validate_strict_cors_allowed_origins_rejects_non_https_or_localhost() -> None:
	with pytest.raises(InvalidCorsConfiguration, match="explicit https:// origins"):
		validate_strict_cors_allowed_origins(
			["http://app.valdrics.io"],
			frontend_url="https://app.valdrics.io",
		)

	with pytest.raises(InvalidCorsConfiguration, match="must not point to localhost"):
		validate_strict_cors_allowed_origins(
			["https://localhost:4173"],
			frontend_url="https://localhost:4173",
		)


def test_validate_strict_cors_allowed_origins_requires_frontend_origin() -> None:
	with pytest.raises(InvalidCorsConfiguration, match="must include the explicit FRONTEND_URL"):
		validate_strict_cors_allowed_origins(
			["https://ops.valdrics.io"],
			frontend_url="https://app.valdrics.io",
		)


def test_validate_strict_cors_allowed_origins_accepts_public_https_frontend_origin() -> None:
	out = validate_strict_cors_allowed_origins(
		["https://app.valdrics.io", "https://ops.valdrics.io"],
		frontend_url="https://app.valdrics.io",
	)

	assert out == ["https://app.valdrics.io", "https://ops.valdrics.io"]


def test_validate_strict_cors_allowed_origins_defaults_to_frontend_origin_when_omitted() -> None:
	out = validate_strict_cors_allowed_origins(
		[],
		frontend_url="https://app.valdrics.io",
	)

	assert out == ["https://app.valdrics.io"]
