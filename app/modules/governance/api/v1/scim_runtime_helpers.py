from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scim_group import ScimGroup
from app.models.tenant import User
from app.modules.governance.api.v1.scim_errors import ScimError
from app.modules.governance.api.v1.scim_membership_ops import (
    apply_scim_group_mappings as _apply_scim_group_mappings_impl,
    recompute_entitlements_for_users as _recompute_entitlements_for_users_impl,
    resolve_entitlements_from_groups as _resolve_entitlements_from_groups_impl,
    resolve_groups_from_refs as _resolve_groups_from_refs_impl,
    resolve_member_user_ids as _resolve_member_user_ids_impl,
)
from app.modules.governance.api.v1.scim_models import (
    ScimGroupRef,
    ScimMemberRef,
    ScimPatchOperation,
)
from app.modules.governance.api.v1.scim_schemas import SCIM_GROUP_SCHEMA, SCIM_USER_SCHEMA
from app.modules.governance.api.v1.scim_utils import (
    normalize_scim_group as _normalize_scim_group,
    parse_uuid as _parse_uuid,
)


def _scim_user_resource(
    user: User,
    *,
    base_url: str,
    tenant_id: UUID,
    groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemas": [SCIM_USER_SCHEMA],
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


def _scim_group_resource(
    group: ScimGroup,
    *,
    base_url: str,
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemas": [SCIM_GROUP_SCHEMA],
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


async def _get_or_create_scim_group(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    display_name: str,
    external_id: str | None = None,
) -> ScimGroup:
    display = str(display_name or "").strip()
    if not display:
        raise ScimError(400, "displayName is required", scim_type="invalidValue")
    display_norm = _normalize_scim_group(display)
    external_norm = _normalize_scim_group(external_id or "") or None

    existing = (
        await db.execute(
            select(ScimGroup).where(
                ScimGroup.tenant_id == tenant_id,
                ScimGroup.display_name_norm == display_norm,
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

    group = ScimGroup(
        id=uuid4(),
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
                select(ScimGroup).where(
                    ScimGroup.tenant_id == tenant_id,
                    ScimGroup.display_name_norm == display_norm,
                )
            )
        ).scalar_one()
        return existing


async def _resolve_groups_from_refs(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    groups: list[ScimGroupRef],
) -> tuple[set[UUID], set[str]]:
    return await _resolve_groups_from_refs_impl(
        db,
        tenant_id=tenant_id,
        groups=groups,
        get_or_create_scim_group_fn=_get_or_create_scim_group,
        parse_uuid_fn=_parse_uuid,
    )


async def _resolve_member_user_ids(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    members: list[ScimMemberRef],
) -> set[UUID]:
    return await _resolve_member_user_ids_impl(
        db,
        tenant_id=tenant_id,
        members=members,
        parse_uuid_fn=_parse_uuid,
    )


def _resolve_entitlements_from_groups(
    group_names: set[str],
    mappings: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    return _resolve_entitlements_from_groups_impl(
        group_names,
        mappings,
        normalize_scim_group_fn=_normalize_scim_group,
    )


async def _recompute_entitlements_for_users(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    user_ids: set[UUID],
) -> None:
    from app.modules.governance.api.v1 import scim as scim_module

    await _recompute_entitlements_for_users_impl(
        db,
        tenant_id=tenant_id,
        user_ids=user_ids,
        load_scim_group_mappings_fn=scim_module._load_scim_group_mappings,
        load_user_group_names_from_memberships_fn=scim_module._load_user_group_names_from_memberships,
        resolve_entitlements_from_groups_fn=scim_module._resolve_entitlements_from_groups,
        normalize_scim_group_fn=_normalize_scim_group,
    )


async def _apply_scim_group_mappings(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    user: User,
    groups: list[ScimGroupRef] | None,
    for_create: bool,
) -> None:
    from app.modules.governance.api.v1 import scim as scim_module

    await _apply_scim_group_mappings_impl(
        db,
        tenant_id=tenant_id,
        user=user,
        groups=groups,
        for_create=for_create,
        resolve_groups_from_refs_fn=scim_module._resolve_groups_from_refs,
        set_user_group_memberships_fn=scim_module._set_user_group_memberships,
        load_scim_group_mappings_fn=scim_module._load_scim_group_mappings,
        resolve_entitlements_from_groups_fn=scim_module._resolve_entitlements_from_groups,
        normalize_scim_group_fn=_normalize_scim_group,
    )


def _apply_patch_operation(user: User, operation: ScimPatchOperation) -> None:
    op = operation.op.lower().strip()
    path = (operation.path or "").strip()
    value = operation.value

    if op not in {"add", "replace", "remove"}:
        raise ScimError(400, "Unsupported patch op", scim_type="invalidValue")

    if not path:
        raise ScimError(400, "Patch path is required", scim_type="invalidPath")

    path_norm = path.strip().lower()
    if path_norm == "active":
        if op == "remove":
            user.is_active = False
            return
        if not isinstance(value, bool):
            raise ScimError(400, "active must be boolean", scim_type="invalidValue")
        user.is_active = bool(value)
        return

    if path_norm == "username":
        if op == "remove":
            raise ScimError(400, "userName cannot be removed", scim_type="invalidValue")
        if not isinstance(value, str) or "@" not in value:
            raise ScimError(400, "userName must be an email", scim_type="invalidValue")
        user.email = value.strip()
        return

    raise ScimError(400, "Unsupported patch path", scim_type="invalidPath")
