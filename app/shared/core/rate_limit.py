"""
Rate limiting for Valdrics.

The supported managed GCP runtime delegates public API throttling to Cloudflare
edge controls and keeps the in-app slowapi limiter disabled. Local and test
runtime flows use the in-process limiter with instance-local memory storage.
"""

from typing import Any, Callable, Optional, cast
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
import hashlib
import structlog

from app.shared.core.config import get_settings
from app.shared.core.proxy_headers import resolve_client_ip

__all__ = [
    "get_limiter",
    "reset_rate_limit_runtime",
    "setup_rate_limiting",
    "rate_limit",
    "global_rate_limit",
    "global_limit_key",
    "standard_limit",
    "auth_limit",
    "analysis_limit",
    "RateLimitExceeded",
    "_rate_limit_exceeded_handler",
]

logger = structlog.get_logger()

_limiter: Limiter | None = None
_limiter_enabled: bool | None = None
TOKEN_HASH_FALLBACK_RECOVERABLE_EXCEPTIONS = (RuntimeError, TypeError, ValueError)
ANALYSIS_TIER_RESOLUTION_RECOVERABLE_EXCEPTIONS = (
    AttributeError,
    TypeError,
    ValueError,
    RuntimeError,
)


def _analysis_limit_mapping(settings: Any) -> dict[str, str]:
    return {
        "free": f"{int(getattr(settings, 'ANALYSIS_RATE_LIMIT_FREE_PER_HOUR', 1) or 1)}/hour",
        "starter": f"{int(getattr(settings, 'ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR', 2) or 2)}/hour",
        "growth": f"{int(getattr(settings, 'ANALYSIS_RATE_LIMIT_GROWTH_PER_HOUR', 10) or 10)}/hour",
        "pro": f"{int(getattr(settings, 'ANALYSIS_RATE_LIMIT_PRO_PER_HOUR', 50) or 50)}/hour",
        "enterprise": f"{int(getattr(settings, 'ANALYSIS_RATE_LIMIT_ENTERPRISE_PER_HOUR', 200) or 200)}/hour",
    }


def _managed_cloudflare_edge_profile(settings: Any) -> bool:
    environment = str(getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    runtime_profile = (
        str(getattr(settings, "PLATFORM_RUNTIME_PROFILE", "gcp") or "gcp")
        .strip()
        .lower()
    )
    public_backend = (
        str(
            getattr(settings, "PUBLIC_API_RATE_LIMITING_BACKEND", "cloudflare")
            or "cloudflare"
        )
        .strip()
        .lower()
    )
    return (
        environment in {"production", "staging"}
        and runtime_profile == "gcp"
        and public_backend == "cloudflare"
    )


def context_aware_key(request: Request) -> str:
    """
    Identifies the requester for rate limiting.
    1. Uses tenant_id if user is authenticated (B2B fairness).
    2. Falls back to sub from JWT if auth hasn't run but token exists (Prevents NAT issues).
    3. Falls back to remote IP (Defense-in-depth).
    """
    # Try request state (already populated by get_current_user dependency)
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return f"tenant:{tenant_id}"

    # Fast check for Authorization header (no DB lookup)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"token:{token_hash}"
        except TOKEN_HASH_FALLBACK_RECOVERABLE_EXCEPTIONS:
            pass

    return resolve_client_ip(request, settings_obj=get_settings())


def get_limiter() -> Limiter:
    """Lazy initialization of the Limiter instance.

    Supported postures are:
    - managed GCP profile with Cloudflare edge throttling and the app limiter disabled
    - local/test runtime with process-local in-memory state
    """
    global _limiter, _limiter_enabled
    settings = get_settings()
    enabled = getattr(settings, "RATELIMIT_ENABLED", True) and not getattr(
        settings, "TESTING", False
    )
    storage_uri = "memory://"
    managed_cloudflare_profile = _managed_cloudflare_edge_profile(settings)
    if not enabled:
        if managed_cloudflare_profile:
            logger.info(
                "rate_limiting_delegated_to_cloudflare_edge",
                msg="Cloudflare edge rate limiting is the supported public API throttle for the managed GCP profile.",
            )

    if _limiter is None or _limiter_enabled != bool(enabled):
        _limiter = Limiter(
            key_func=context_aware_key,
            storage_uri=storage_uri,
            strategy="fixed-window",
            enabled=enabled,
        )
        _limiter_enabled = bool(enabled)
    return _limiter


async def reset_rate_limit_runtime() -> None:
    global _limiter, _limiter_enabled
    _limiter = None
    _limiter_enabled = None


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting for the FastAPI application.
    """
    limiter = get_limiter()
    # Add rate limit exceeded handler
    app.state.limiter = limiter

    def _rate_limit_handler(request: Request, exc: Exception) -> Any:
        return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    logger.info("rate_limiting_configured")


# Rate limit decorators for use in routes
def rate_limit(
    limit: str | Callable[[Request], str] = "100/minute",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to apply rate limiting to an endpoint."""
    # Finding #L3: If we bypass the decorator here based on settings.TESTING,
    # it captures the state at import time. Instead, we always return the
    # limiter's decorator, which internally checks its 'enabled' status
    # during each request.
    return cast(
        Callable[[Callable[..., Any]], Callable[..., Any]], get_limiter().limit(limit)
    )


def global_limit_key(namespace: str) -> Callable[[Request], str]:
    """
    Build a stable cross-tenant limiter key for shared fairness controls.
    """

    safe_namespace = "".join(
        ch if (ch.isalnum() or ch in {"_", "-", ".", ":"}) else "_"
        for ch in str(namespace or "").strip().lower()
    )
    if not safe_namespace:
        safe_namespace = "global"
    key = f"global:{safe_namespace}"

    def _key(request: Request | None = None) -> str:
        del request
        return key

    return _key


def global_rate_limit(
    limit: str | Callable[[Request], str] = "1000/minute",
    *,
    namespace: str = "default",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Apply a route-level global throttle shared across tenants.
    """

    return cast(
        Callable[[Callable[..., Any]], Callable[..., Any]],
        get_limiter().limit(limit, key_func=global_limit_key(namespace)),
    )


# Pre-configured rate limits (now using strings for delay)
# Route handlers can use @rate_limit("100/minute") or these helpers
STANDARD_LIMIT = "100/minute"
AUTH_LIMIT = "30/minute"


def get_analysis_limit(request: Optional[Request] = None) -> str:
    """
    BE-LLM-4: Dynamic rate limiting based on tenant tier.
    Protects LLM operational costs while rewarding higher tiers.
    """
    if not request:
        return "1/hour"

    try:
        raw_tier = getattr(request.state, "tier", "starter")
        if hasattr(raw_tier, "value"):
            tier = str(getattr(raw_tier, "value")).strip().lower()
        elif isinstance(raw_tier, str):
            tier = raw_tier.strip().lower()
        else:
            tier = "starter"
        if not tier:
            tier = "starter"
    except ANALYSIS_TIER_RESOLUTION_RECOVERABLE_EXCEPTIONS:
        tier = "starter"

    limits = _analysis_limit_mapping(get_settings())

    return limits.get(tier, "1/hour")


def standard_limit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Apply the standard API limit decorator."""
    return rate_limit(STANDARD_LIMIT)(func)


def auth_limit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Apply the authenticated-route API limit decorator."""
    return rate_limit(AUTH_LIMIT)(func)


# Dynamic analysis limit decorator
def analysis_limit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that applies a dynamic analysis limit based on tenant tier."""
    if get_settings().TESTING:
        return func
    # Pass the callable (not its result) so it's evaluated per-request
    decorated = get_limiter().limit(get_analysis_limit)(func)
    return cast(Callable[..., Any], decorated)
