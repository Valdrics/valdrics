from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

AUTH_IDENTITY_POLICY_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    DBAPIError,
    SQLAlchemyError,
    RuntimeError,
)


async def enforce_tenant_identity_policy(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    email: str,
    is_production: bool,
) -> None:
    """Enforce tenant-scoped identity domain policy where configured."""
    try:
        from app.models.tenant_identity_settings import TenantIdentitySettings

        identity_settings = (
            await db.execute(
                select(TenantIdentitySettings).where(
                    TenantIdentitySettings.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if identity_settings and bool(getattr(identity_settings, "sso_enabled", False)):
            allowed_domains = [
                str(domain).strip().lower()
                for domain in (
                    getattr(identity_settings, "allowed_email_domains", None) or []
                )
                if str(domain).strip()
            ]
            if allowed_domains:
                email_value = str(email or "")
                email_domain = (
                    email_value.split("@")[-1].strip().lower()
                    if "@" in email_value
                    else ""
                )
                if not email_domain or email_domain not in allowed_domains:
                    logger.warning(
                        "auth_domain_not_allowed",
                        user_id=str(user_id),
                        tenant_id=str(tenant_id),
                        email_domain=email_domain,
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Access denied: email domain is not allowed for this tenant."
                        ),
                    )
    except HTTPException:
        raise
    except AUTH_IDENTITY_POLICY_RECOVERABLE_ERRORS as exc:
        if is_production:
            logger.error(
                "auth_identity_policy_check_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            raise HTTPException(
                status_code=500,
                detail="Identity policy enforcement failed. Please contact support.",
            )
        logger.warning("auth_identity_policy_check_skipped", error=str(exc))
