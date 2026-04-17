from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel


class InternalInvoker(BaseModel):
    method: str
    subject: str
    email: str | None = None


def _extract_bearer_token(request: Request) -> str | None:
    auth_headers = (
        request.headers.get("X-Serverless-Authorization"),
        request.headers.get("Authorization"),
    )
    for header_value in auth_headers:
        normalized = str(header_value or "").strip()
        if not normalized:
            continue
        parts = normalized.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
            return parts[1].strip()
    return None


def _allowed_google_service_accounts(settings_obj: object) -> set[str]:
    return {
        str(email or "").strip().lower()
        for email in getattr(settings_obj, "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS", [])
        if str(email or "").strip()
    }


def _internal_google_audience(settings_obj: object) -> str:
    explicit_audience = str(
        getattr(settings_obj, "GCP_INTERNAL_AUTH_AUDIENCE", "") or ""
    ).strip()
    if explicit_audience:
        return explicit_audience

    api_url = str(getattr(settings_obj, "API_URL", "") or "").strip()
    if api_url:
        return api_url

    internal_base_url = str(
        getattr(settings_obj, "GCP_INTERNAL_BASE_URL", "") or ""
    ).strip()
    if internal_base_url:
        return internal_base_url

    return ""


def _verify_google_identity_token(token: str, settings_obj: object) -> InternalInvoker:
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import id_token
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise HTTPException(
            status_code=503,
            detail="google-auth runtime dependencies are not installed.",
        ) from exc
    try:
        from google.auth.exceptions import GoogleAuthError
    except (AttributeError, ImportError):  # pragma: no cover - test shims

        class GoogleAuthError(ValueError):
            """Fallback used when test shims do not expose google.auth.exceptions."""

    audience = _internal_google_audience(settings_obj)
    if not audience:
        raise HTTPException(
            status_code=503,
            detail="GCP internal auth audience is not configured.",
        )

    try:
        claims = id_token.verify_token(
            token,
            GoogleAuthRequest(),
            audience=audience,
        )
    except (GoogleAuthError, ValueError) as exc:
        raise HTTPException(
            status_code=403, detail="Invalid Google identity token."
        ) from exc

    email = str(claims.get("email", "") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=403,
            detail="Google identity token is missing the service account email.",
        )
    if claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=403,
            detail="Google identity token email must be verified.",
        )

    allowed_accounts = _allowed_google_service_accounts(settings_obj)
    if not allowed_accounts:
        raise HTTPException(
            status_code=503,
            detail="GCP internal allowed service accounts are not configured.",
        )
    if email not in allowed_accounts:
        raise HTTPException(
            status_code=403,
            detail="Google identity token is not allowed for internal invocation.",
        )

    subject = str(claims.get("sub", "") or email).strip()
    return InternalInvoker(method="google_oidc", subject=subject, email=email)


async def require_internal_platform_invocation(
    request: Request,
) -> InternalInvoker:
    from app.shared.core.config import get_settings

    settings = get_settings()
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Google identity token is required for internal GCP invocation.",
        )
    return _verify_google_identity_token(token, settings)
