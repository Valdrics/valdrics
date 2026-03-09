from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


def extract_bearer_token(request: Request, *, scim_error_cls: Any) -> str:
    raw = (request.headers.get("Authorization") or "").strip()
    if not raw.lower().startswith("bearer "):
        raise scim_error_cls(
            401, "Missing or invalid Authorization header", scim_type="invalidSyntax"
        )
    token = raw.split(" ", 1)[-1].strip()
    if not token:
        raise scim_error_cls(401, "Missing bearer token", scim_type="invalidSyntax")
    return token


async def get_scim_context(
    *,
    request: Request,
    extract_bearer_token_fn: Any,
    generate_secret_blind_index_fn: Any,
    async_session_maker: Any,
    mark_session_system_context_fn: Any,
    select_fn: Any,
    tenant_identity_settings_cls: Any,
    tenant_cls: Any,
    normalize_tier_fn: Any,
    is_feature_enabled_fn: Any,
    feature_flag_scim: Any,
    scim_error_cls: Any,
    scim_context_cls: Any,
) -> Any:
    token = extract_bearer_token_fn(request)
    token_bidx = generate_secret_blind_index_fn(token)
    if not token_bidx:
        raise scim_error_cls(401, "Invalid bearer token", scim_type="invalidSyntax")

    async with async_session_maker() as db:
        await mark_session_system_context_fn(db)
        result = await db.execute(
            select_fn(
                tenant_identity_settings_cls.tenant_id,
                tenant_identity_settings_cls.scim_enabled,
            ).where(tenant_identity_settings_cls.scim_token_bidx == token_bidx)
        )
        row = result.first()
        if not row:
            raise scim_error_cls(401, "Unauthorized", scim_type="invalidToken")

        tenant_id, scim_enabled = row
        if not bool(scim_enabled):
            raise scim_error_cls(
                403, "SCIM is disabled for this tenant", scim_type="forbidden"
            )

        tenant_plan = (
            await db.execute(select_fn(tenant_cls.plan).where(tenant_cls.id == tenant_id))
        ).scalar_one_or_none()
        tier = normalize_tier_fn(tenant_plan)
        if not is_feature_enabled_fn(tier, feature_flag_scim):
            raise scim_error_cls(403, "SCIM requires Enterprise tier", scim_type="forbidden")

        request.state.tenant_id = tenant_id
        return scim_context_cls(tenant_id=tenant_id)


def scim_user_resource(
    user: Any,
    *,
    base_url: str,
    groups: list[dict[str, Any]] | None = None,
    scim_user_schema: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemas": [scim_user_schema],
        "id": str(user.id),
        "userName": str(user.email),
        "active": bool(getattr(user, "is_active", True)),
        "emails": [{"value": str(user.email), "primary": True}],
        "meta": {
            "resourceType": "User",
            "location": f"{base_url.rstrip('/')}/scim/v2/Users/{user.id}",
        },
    }
    if groups is not None:
        payload["groups"] = groups
    return payload


def scim_group_resource(
    group: Any,
    *,
    base_url: str,
    members: list[dict[str, Any]] | None = None,
    scim_group_schema: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemas": [scim_group_schema],
        "id": str(group.id),
        "displayName": str(getattr(group, "display_name", "") or ""),
        "meta": {
            "resourceType": "Group",
            "location": f"{base_url.rstrip('/')}/scim/v2/Groups/{group.id}",
        },
    }
    if getattr(group, "external_id", None):
        payload["externalId"] = str(group.external_id)
    if members is not None:
        payload["members"] = members
    return payload


async def get_or_create_scim_group(
    db: Any,
    *,
    tenant_id: UUID,
    display_name: str,
    external_id: str | None,
    normalize_scim_group_fn: Any,
    parse_uuid_fn: Any | None,
    scim_group_cls: Any,
    select_fn: Any,
    uuid4_fn: Any,
    scim_error_cls: Any,
) -> Any:
    del parse_uuid_fn
    display = str(display_name or "").strip()
    if not display:
        raise scim_error_cls(400, "displayName is required", scim_type="invalidValue")
    display_norm = normalize_scim_group_fn(display)
    external_norm = normalize_scim_group_fn(external_id or "") or None

    existing = (
        await db.execute(
            select_fn(scim_group_cls).where(
                scim_group_cls.tenant_id == tenant_id,
                scim_group_cls.display_name_norm == display_norm,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.display_name = display
        existing.display_name_norm = display_norm
        if external_id:
            existing.external_id = external_id
            existing.external_id_norm = external_norm
        return existing

    group = scim_group_cls(
        id=uuid4_fn(),
        tenant_id=tenant_id,
        display_name=display,
        display_name_norm=display_norm,
        external_id=external_id,
        external_id_norm=external_norm,
    )
    try:
        async with db.begin_nested():
            db.add(group)
            await db.flush()
        return group
    except IntegrityError:
        existing = (
            await db.execute(
                select_fn(scim_group_cls).where(
                    scim_group_cls.tenant_id == tenant_id,
                    scim_group_cls.display_name_norm == display_norm,
                )
            )
        ).scalar_one()
        return existing


def resolve_entitlements_from_groups(
    group_names: set[str],
    mappings: list[dict[str, Any]],
    *,
    resolve_entitlements_from_groups_impl: Any,
    normalize_scim_group_fn: Any,
) -> tuple[str | None, str | None]:
    resolved = resolve_entitlements_from_groups_impl(
        group_names,
        mappings,
        normalize_scim_group_fn=normalize_scim_group_fn,
    )
    if not isinstance(resolved, tuple) or len(resolved) != 2:
        raise TypeError("resolve_entitlements_from_groups_impl must return a 2-tuple")
    role_raw, persona_raw = resolved
    if role_raw is not None and not isinstance(role_raw, str):
        raise TypeError("Resolved SCIM role must be a string or None")
    if persona_raw is not None and not isinstance(persona_raw, str):
        raise TypeError("Resolved SCIM persona must be a string or None")
    return role_raw, persona_raw


def make_scim_error(
    status_code: int,
    detail: str,
    scim_type: str | None,
    *,
    scim_error_cls: Any,
) -> Any:
    return scim_error_cls(status_code, detail, scim_type=scim_type)


def apply_patch_operation(
    *,
    user: Any,
    operation: Any,
    scim_error_cls: Any,
) -> None:
    op = operation.op.lower().strip()
    path = (operation.path or "").strip()
    value = operation.value

    if op not in {"add", "replace", "remove"}:
        raise scim_error_cls(400, "Unsupported patch op", scim_type="invalidValue")

    if not path:
        raise scim_error_cls(400, "Patch path is required", scim_type="invalidPath")

    path_norm = path.strip().lower()
    if path_norm == "active":
        if op == "remove":
            user.is_active = False
            return
        if not isinstance(value, bool):
            raise scim_error_cls(400, "active must be boolean", scim_type="invalidValue")
        user.is_active = bool(value)
        return

    if path_norm == "username":
        if op == "remove":
            raise scim_error_cls(400, "userName cannot be removed", scim_type="invalidValue")
        if not isinstance(value, str) or "@" not in value:
            raise scim_error_cls(400, "userName must be an email", scim_type="invalidValue")
        user.email = value.strip()
        return

    raise scim_error_cls(400, "Unsupported patch path", scim_type="invalidPath")


def list_schemas_payload(
    *,
    base_url: str,
    scim_user_schema_resource_fn: Any,
    scim_group_schema_resource_fn: Any,
    scim_list_schema: str,
) -> dict[str, Any]:
    resources = [
        scim_user_schema_resource_fn(base_url=base_url),
        scim_group_schema_resource_fn(base_url=base_url),
    ]
    return {
        "schemas": [scim_list_schema],
        "totalResults": len(resources),
        "startIndex": 1,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


def get_schema_response(
    *,
    base_url: str,
    schema_id: str,
    scim_user_schema: str,
    scim_group_schema: str,
    scim_user_schema_resource_fn: Any,
    scim_group_schema_resource_fn: Any,
    scim_error_cls: Any,
) -> JSONResponse:
    normalized = (schema_id or "").strip()
    if normalized == scim_user_schema:
        return JSONResponse(
            status_code=200, content=scim_user_schema_resource_fn(base_url=base_url)
        )
    if normalized == scim_group_schema:
        return JSONResponse(
            status_code=200, content=scim_group_schema_resource_fn(base_url=base_url)
        )
    raise scim_error_cls(404, "Resource not found")
