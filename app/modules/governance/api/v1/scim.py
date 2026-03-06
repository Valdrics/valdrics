"""
SCIM 2.0 (Minimal) Provisioning API.

Goals:
- Enterprise-only, tenant-scoped provisioning (create/disable/update users)
- No dependency on browser cookies/CSRF (Bearer token auth)
- Deterministic lookup via blind index (no decrypt required for auth)

Supported resources:
- Users
- Groups (optional, for IdPs that manage membership via /Groups)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.scim_group import ScimGroup
from app.models.tenant_identity_settings import TenantIdentitySettings
from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLogger
from app.modules.governance.api.v1.scim_group_route_ops import (
    create_group_route as _create_group_route_impl,
    delete_group_route as _delete_group_route_impl,
    list_groups_route as _list_groups_route_impl,
    patch_group_route as _patch_group_route_impl,
    put_group_route as _put_group_route_impl,
)
from app.shared.core.pricing import FeatureFlag, is_feature_enabled, normalize_tier
from app.shared.core.security import generate_secret_blind_index
from app.shared.db import session as db_session
from app.modules.governance.api.v1.scim_errors import ScimError, scim_error_response
from app.modules.governance.api.v1.scim_metadata_routes import (
    get_resource_types,
    get_schema,
    get_service_provider_config,
    list_schemas,
    register_metadata_routes,
)
from app.modules.governance.api.v1.scim_models import (
    ScimGroupCreate,
    ScimGroupPut,
    ScimGroupRef,
    ScimListResponse,
    ScimPatchRequest,
    ScimUserCreate,
    ScimUserPut,
)
from app.modules.governance.api.v1.scim_schemas import (
    SCIM_GROUP_SCHEMA,
    SCIM_USER_SCHEMA,
)
from app.modules.governance.api.v1.scim_runtime_helpers import (
    _apply_patch_operation,
    _apply_scim_group_mappings,
    _get_or_create_scim_group,
    _recompute_entitlements_for_users,
    _resolve_entitlements_from_groups,
    _resolve_groups_from_refs,
    _resolve_member_user_ids,
    _scim_group_resource,
    _scim_user_resource,
)
from app.modules.governance.api.v1.scim_utils import (
    normalize_scim_group as _normalize_scim_group,
    parse_group_filter as _parse_group_filter,
    parse_member_filter_from_path as _parse_member_filter_from_path,
    parse_user_filter as _parse_user_filter,
    parse_uuid as _parse_uuid,
)
from app.modules.governance.api.v1.scim_membership_ops import (
    apply_group_patch_operations as _apply_group_patch_operations_impl,
    load_group_member_refs_map as _load_group_member_refs_map_impl,
    load_group_member_user_ids as _load_group_member_user_ids_impl,
    load_scim_group_mappings as _load_scim_group_mappings_impl,
    load_user_group_names_from_memberships as _load_user_group_names_from_memberships_impl,
    load_user_group_refs_map as _load_user_group_refs_map_impl,
    set_group_memberships as _set_group_memberships_impl,
    set_user_group_memberships as _set_user_group_memberships_impl,
)
from app.modules.governance.api.v1.scim_user_route_ops import (
    create_user_route as _create_user_route_impl,
    delete_user_route as _delete_user_route_impl,
    get_user_route as _get_user_route_impl,
    list_users_route as _list_users_route_impl,
    patch_user_route as _patch_user_route_impl,
    put_user_route as _put_user_route_impl,
)

logger = structlog.get_logger()
router = APIRouter(tags=["SCIM"])
__all__ = [
    "SCIM_GROUP_SCHEMA",
    "SCIM_USER_SCHEMA",
    "ScimError",
    "get_resource_types",
    "get_schema",
    "get_scim_context",
    "get_scim_db",
    "get_service_provider_config",
    "list_schemas",
    "router",
    "scim_error_response",
    "_apply_patch_operation",
    "_apply_scim_group_mappings",
    "_extract_bearer_token",
    "_get_or_create_scim_group",
    "_load_group_member_refs_map",
    "_load_group_member_user_ids",
    "_load_scim_group_mappings",
    "_load_user_group_names_from_memberships",
    "_load_user_group_refs_map",
    "_recompute_entitlements_for_users",
    "_resolve_entitlements_from_groups",
    "_resolve_groups_from_refs",
    "_resolve_member_user_ids",
    "_scim_group_resource",
    "_scim_user_resource",
    "_set_group_memberships",
    "_set_user_group_memberships",
]


@dataclass(frozen=True, slots=True)
class ScimContext:
    tenant_id: UUID


def _extract_bearer_token(request: Request) -> str:
    raw = (request.headers.get("Authorization") or "").strip()
    if not raw.lower().startswith("bearer "):
        raise ScimError(
            401, "Missing or invalid Authorization header", scim_type="invalidSyntax"
        )
    token = raw.split(" ", 1)[-1].strip()
    if not token:
        raise ScimError(401, "Missing bearer token", scim_type="invalidSyntax")
    return token


async def get_scim_context(request: Request) -> ScimContext:
    token = _extract_bearer_token(request)
    token_bidx = generate_secret_blind_index(token)
    if not token_bidx:
        raise ScimError(401, "Invalid bearer token", scim_type="invalidSyntax")

    # NOTE: We intentionally reference `db_session.async_session_maker` at runtime so
    # tests can patch it to a per-test engine (instead of capturing the symbol at import).
    async with db_session.async_session_maker() as db:
        await db_session.mark_session_system_context(db)
        result = await db.execute(
            select(
                TenantIdentitySettings.tenant_id, TenantIdentitySettings.scim_enabled
            ).where(TenantIdentitySettings.scim_token_bidx == token_bidx)
        )
        row = result.first()
        if not row:
            raise ScimError(401, "Unauthorized", scim_type="invalidToken")

        tenant_id, scim_enabled = row
        if not bool(scim_enabled):
            raise ScimError(
                403, "SCIM is disabled for this tenant", scim_type="forbidden"
            )

        tenant_plan = (
            await db.execute(select(Tenant.plan).where(Tenant.id == tenant_id))
        ).scalar_one_or_none()
        tier = normalize_tier(tenant_plan)
        if not is_feature_enabled(tier, FeatureFlag.SCIM):
            raise ScimError(403, "SCIM requires Enterprise tier", scim_type="forbidden")

        request.state.tenant_id = tenant_id
        return ScimContext(tenant_id=tenant_id)


async def get_scim_db(
    ctx: ScimContext = Depends(get_scim_context),
) -> AsyncGenerator[AsyncSession, None]:
    # We use a fresh session that we control, and set tenant context before touching tenant tables.
    async with db_session.async_session_maker() as db:
        await db_session.set_session_tenant_id(db, ctx.tenant_id)
        yield db


_load_user_group_refs_map = _load_user_group_refs_map_impl
_load_group_member_refs_map = _load_group_member_refs_map_impl
_load_group_member_user_ids = _load_group_member_user_ids_impl
_set_user_group_memberships = _set_user_group_memberships_impl
_set_group_memberships = _set_group_memberships_impl
_load_scim_group_mappings = _load_scim_group_mappings_impl
_load_user_group_names_from_memberships = _load_user_group_names_from_memberships_impl


def _make_scim_error(
    status_code: int, detail: str, scim_type: str | None = None
) -> ScimError:
    return ScimError(status_code, detail, scim_type=scim_type)


register_metadata_routes(router)


@router.get("/Users")
async def list_users(
    request: Request,
    startIndex: int = 1,
    count: int = 100,
    filter: str | None = None,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> ScimListResponse:
    return await _list_users_route_impl(
        request=request,
        start_index=startIndex,
        count=count,
        filter_expr=filter,
        tenant_id=ctx.tenant_id,
        db=db,
        parse_user_filter_fn=_parse_user_filter,
        load_user_group_refs_map_fn=_load_user_group_refs_map,
        scim_user_resource_fn=_scim_user_resource,
        scim_error_factory=_make_scim_error,
    )


@router.post("/Users")
async def create_user(
    request: Request,
    body: ScimUserCreate,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _create_user_route_impl(
        request=request,
        body=body,
        tenant_id=ctx.tenant_id,
        db=db,
        apply_scim_group_mappings_fn=_apply_scim_group_mappings,
        load_user_group_refs_map_fn=_load_user_group_refs_map,
        scim_user_resource_fn=_scim_user_resource,
        scim_error_factory=_make_scim_error,
        audit_logger_cls=AuditLogger,
        audit_event_type=AuditEventType,
    )


@router.get("/Users/{user_id}")
async def get_user(
    request: Request,
    user_id: str,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _get_user_route_impl(
        request=request,
        user_id=user_id,
        tenant_id=ctx.tenant_id,
        db=db,
        load_user_group_refs_map_fn=_load_user_group_refs_map,
        scim_user_resource_fn=_scim_user_resource,
        scim_error_factory=_make_scim_error,
    )


@router.put("/Users/{user_id}")
async def put_user(
    request: Request,
    user_id: str,
    body: ScimUserPut,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _put_user_route_impl(
        request=request,
        user_id=user_id,
        body=body,
        tenant_id=ctx.tenant_id,
        db=db,
        apply_scim_group_mappings_fn=_apply_scim_group_mappings,
        load_user_group_refs_map_fn=_load_user_group_refs_map,
        scim_user_resource_fn=_scim_user_resource,
        scim_error_factory=_make_scim_error,
        audit_logger_cls=AuditLogger,
        audit_event_type=AuditEventType,
    )


@router.patch("/Users/{user_id}")
async def patch_user(
    request: Request,
    user_id: str,
    body: ScimPatchRequest,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _patch_user_route_impl(
        request=request,
        user_id=user_id,
        body=body,
        tenant_id=ctx.tenant_id,
        db=db,
        apply_patch_operation_fn=_apply_patch_operation,
        apply_scim_group_mappings_fn=_apply_scim_group_mappings,
        load_user_group_refs_map_fn=_load_user_group_refs_map,
        scim_user_resource_fn=_scim_user_resource,
        scim_group_ref_model=ScimGroupRef,
        scim_error_factory=_make_scim_error,
        audit_logger_cls=AuditLogger,
        audit_event_type=AuditEventType,
    )


@router.delete("/Users/{user_id}")
async def delete_user(
    user_id: str,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _delete_user_route_impl(
        user_id=user_id,
        tenant_id=ctx.tenant_id,
        db=db,
        scim_error_factory=_make_scim_error,
        audit_logger_cls=AuditLogger,
        audit_event_type=AuditEventType,
    )


@router.get("/Groups")
async def list_groups(
    request: Request,
    startIndex: int = 1,
    count: int = 100,
    filter: str | None = None,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> ScimListResponse:
    base_url = str(request.base_url).rstrip("/")
    return await _list_groups_route_impl(
        db=db,
        tenant_id=ctx.tenant_id,
        start_index=startIndex,
        count=count,
        filter_expr=filter,
        base_url=base_url,
        parse_group_filter_fn=_parse_group_filter,
        normalize_scim_group_fn=_normalize_scim_group,
        load_group_member_refs_map_fn=_load_group_member_refs_map,
        scim_group_resource_fn=_scim_group_resource,
        scim_error_factory=_make_scim_error,
    )


@router.post("/Groups")
async def create_group(
    request: Request,
    body: ScimGroupCreate,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")
    return await _create_group_route_impl(
        db=db,
        tenant_id=ctx.tenant_id,
        body=body,
        base_url=base_url,
        parse_uuid_fn=_parse_uuid,
        normalize_scim_group_fn=_normalize_scim_group,
        resolve_member_user_ids_fn=_resolve_member_user_ids,
        set_group_memberships_fn=_set_group_memberships,
        recompute_entitlements_for_users_fn=_recompute_entitlements_for_users,
        load_group_member_refs_map_fn=_load_group_member_refs_map,
        scim_group_resource_fn=_scim_group_resource,
        scim_error_factory=_make_scim_error,
    )


@router.get("/Groups/{group_id}")
async def get_group(
    request: Request,
    group_id: str,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    try:
        parsed_id = UUID(group_id)
    except ValueError as exc:
        raise ScimError(404, "Resource not found") from exc

    group = (
        await db.execute(
            select(ScimGroup).where(
                ScimGroup.tenant_id == ctx.tenant_id, ScimGroup.id == parsed_id
            )
        )
    ).scalar_one_or_none()
    if not group:
        raise ScimError(404, "Resource not found")

    base_url = str(request.base_url).rstrip("/")
    member_map = await _load_group_member_refs_map(
        db,
        tenant_id=ctx.tenant_id,
        group_ids=[group.id],
    )
    return JSONResponse(
        status_code=200,
        content=_scim_group_resource(
            group,
            base_url=base_url,
            members=member_map.get(group.id, []),
        ),
    )


@router.put("/Groups/{group_id}")
async def put_group(
    request: Request,
    group_id: str,
    body: ScimGroupPut,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")
    return await _put_group_route_impl(
        db=db,
        tenant_id=ctx.tenant_id,
        group_id=group_id,
        body=body,
        base_url=base_url,
        parse_uuid_fn=_parse_uuid,
        normalize_scim_group_fn=_normalize_scim_group,
        resolve_member_user_ids_fn=_resolve_member_user_ids,
        set_group_memberships_fn=_set_group_memberships,
        recompute_entitlements_for_users_fn=_recompute_entitlements_for_users,
        load_group_member_refs_map_fn=_load_group_member_refs_map,
        scim_group_resource_fn=_scim_group_resource,
        scim_error_factory=_make_scim_error,
    )


@router.patch("/Groups/{group_id}")
async def patch_group(
    request: Request,
    group_id: str,
    body: ScimPatchRequest,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")
    return await _patch_group_route_impl(
        db=db,
        tenant_id=ctx.tenant_id,
        group_id=group_id,
        body=body,
        base_url=base_url,
        parse_uuid_fn=_parse_uuid,
        apply_group_patch_operations_fn=_apply_group_patch_operations_impl,
        normalize_scim_group_fn=_normalize_scim_group,
        parse_member_filter_from_path_fn=_parse_member_filter_from_path,
        resolve_member_user_ids_fn=_resolve_member_user_ids,
        set_group_memberships_fn=_set_group_memberships,
        load_group_member_user_ids_fn=_load_group_member_user_ids,
        recompute_entitlements_for_users_fn=_recompute_entitlements_for_users,
        load_group_member_refs_map_fn=_load_group_member_refs_map,
        scim_group_resource_fn=_scim_group_resource,
        scim_error_factory=_make_scim_error,
    )


@router.delete("/Groups/{group_id}")
async def delete_group(
    group_id: str,
    ctx: ScimContext = Depends(get_scim_context),
    db: AsyncSession = Depends(get_scim_db),
) -> JSONResponse:
    return await _delete_group_route_impl(
        db=db,
        tenant_id=ctx.tenant_id,
        group_id=group_id,
        parse_uuid_fn=_parse_uuid,
        load_group_member_user_ids_fn=_load_group_member_user_ids,
        recompute_entitlements_for_users_fn=_recompute_entitlements_for_users,
        scim_error_factory=_make_scim_error,
    )
