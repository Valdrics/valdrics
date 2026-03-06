from __future__ import annotations


class InvalidCorsConfiguration(ValueError):
    """Raised when runtime CORS settings violate credential-safety rules."""


def resolve_cors_allowed_origins(
    cors_origins: list[str],
    *,
    allow_credentials: bool,
) -> list[str]:
    normalized = [origin.strip() for origin in cors_origins if origin.strip()]
    if allow_credentials and "*" in normalized:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS must not include '*' when allow_credentials=True."
        )
    return normalized

