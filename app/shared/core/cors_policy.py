from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class InvalidCorsConfiguration(ValueError):
    """Raised when runtime CORS settings violate credential-safety rules."""


def resolve_cors_allowed_origins(
    cors_origins: list[str],
    *,
    allow_credentials: bool,
) -> list[str]:
    normalized = [
        _normalize_origin(origin)
        for origin in cors_origins
        if str(origin or "").strip()
    ]
    if allow_credentials and "*" in normalized:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS must not include '*' when allow_credentials=True."
        )
    return normalized


def _normalize_origin(origin: str) -> str:
    candidate = str(origin or "").strip()
    if candidate == "*":
        return candidate

    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return candidate

    scheme = parsed.scheme.lower()
    hostname = str(parsed.hostname or "").lower()
    if not hostname:
        return candidate

    if parsed.port is None:
        netloc = hostname
    else:
        netloc = f"{hostname}:{parsed.port}"

    return f"{scheme}://{netloc}"


def _validate_strict_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if not parsed.netloc:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must use explicit https:// origins in staging/production."
        )

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname:
        raise InvalidCorsConfiguration("CORS_ORIGINS entries must include a valid hostname.")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must not point to localhost in staging/production."
        )
    if hostname.endswith(".local") or hostname.endswith(".internal"):
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must not point to private DNS suffixes in staging/production."
        )

    if parsed.scheme != "https":
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must use explicit https:// origins in staging/production."
        )
    if parsed.username or parsed.password:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must not include embedded credentials."
        )
    if parsed.query or parsed.fragment:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must not include query strings or fragments."
        )
    if parsed.path not in {"", "/"}:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must be origins only and must not include URL paths."
        )

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return f"{parsed.scheme}://{parsed.netloc}"

    if (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_multicast
        or host_ip.is_unspecified
        or host_ip.is_reserved
    ):
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS entries must not resolve to private or non-routable IPs in staging/production."
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_strict_cors_allowed_origins(
    cors_origins: list[str],
    *,
    frontend_url: str,
) -> list[str]:
    frontend_origin = _validate_strict_origin(frontend_url)
    normalized = resolve_cors_allowed_origins(
        cors_origins,
        allow_credentials=True,
    )
    if not normalized:
        return [frontend_origin]

    allowed_origins = [_validate_strict_origin(origin) for origin in normalized]
    if frontend_origin not in allowed_origins:
        raise InvalidCorsConfiguration(
            "CORS_ORIGINS must include the explicit FRONTEND_URL origin in staging/production."
        )
    deduped_origins: list[str] = []
    for origin in allowed_origins:
        if origin not in deduped_origins:
            deduped_origins.append(origin)
    return deduped_origins
