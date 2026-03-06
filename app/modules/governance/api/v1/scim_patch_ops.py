from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scim_group import ScimGroup
from app.modules.governance.api.v1.scim_models import ScimMemberRef


async def apply_group_patch_operations(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    group: ScimGroup,
    operations: list[Any],
    normalize_scim_group_fn: Callable[[str], str],
    parse_member_filter_from_path_fn: Callable[[str], UUID | None],
    resolve_member_user_ids_fn: Callable[..., Awaitable[set[UUID]]],
    set_group_memberships_fn: Callable[..., Awaitable[set[UUID]]],
    load_group_member_user_ids_fn: Callable[..., Awaitable[set[UUID]]],
    scim_error_factory: Callable[[int, str, str | None], Exception],
) -> tuple[bool, set[UUID]]:
    member_action = False
    impacted_user_ids: set[UUID] = set()

    for operation in operations:
        op = str(getattr(operation, "op", "")).lower().strip()
        path = str(getattr(operation, "path", "") or "").strip()
        value = getattr(operation, "value", None)

        if op not in {"add", "replace", "remove"}:
            raise scim_error_factory(400, "Unsupported patch op", "invalidValue")

        if not path:
            if op in {"add", "replace"} and isinstance(value, dict):
                if "displayName" in value:
                    name_val = str(value.get("displayName") or "").strip()
                    if not name_val:
                        raise scim_error_factory(
                            400, "displayName is required", "invalidValue"
                        )
                    group.display_name = name_val
                    group.display_name_norm = normalize_scim_group_fn(name_val)
                if "externalId" in value:
                    ext_val = str(value.get("externalId") or "").strip() or None
                    group.external_id = ext_val
                    group.external_id_norm = (
                        normalize_scim_group_fn(ext_val or "") or None
                    )
                if "members" in value:
                    member_action = True
                    member_refs = value.get("members")
                    if not isinstance(member_refs, list):
                        raise scim_error_factory(
                            400, "members must be a list", "invalidValue"
                        )
                    parsed_refs = [
                        ScimMemberRef.model_validate(item)
                        for item in member_refs
                        if isinstance(item, dict)
                    ]
                    member_user_ids = await resolve_member_user_ids_fn(
                        db, tenant_id=tenant_id, members=parsed_refs
                    )
                    impacted_user_ids |= await set_group_memberships_fn(
                        db,
                        tenant_id=tenant_id,
                        group_id=group.id,
                        member_user_ids=member_user_ids,
                    )
                continue
            raise scim_error_factory(400, "Patch path is required", "invalidPath")

        path_norm = path.lower()
        if path_norm == "displayname":
            if op == "remove":
                raise scim_error_factory(
                    400, "displayName cannot be removed", "invalidValue"
                )
            if not isinstance(value, str):
                raise scim_error_factory(400, "displayName must be string", "invalidValue")
            name_val = value.strip()
            if not name_val:
                raise scim_error_factory(400, "displayName is required", "invalidValue")
            group.display_name = name_val
            group.display_name_norm = normalize_scim_group_fn(name_val)
            continue

        if path_norm == "externalid":
            if op == "remove":
                group.external_id = None
                group.external_id_norm = None
                continue
            if not isinstance(value, str):
                raise scim_error_factory(400, "externalId must be string", "invalidValue")
            ext_val = value.strip() or None
            group.external_id = ext_val
            group.external_id_norm = normalize_scim_group_fn(ext_val or "") or None
            continue

        if path_norm == "members" or path_norm.startswith("members["):
            member_action = True

            existing = await load_group_member_user_ids_fn(
                db, tenant_id=tenant_id, group_id=group.id
            )
            remove_from_path = (
                parse_member_filter_from_path_fn(path)
                if path_norm.startswith("members[")
                else None
            )

            if op == "replace":
                if not isinstance(value, list):
                    raise scim_error_factory(
                        400, "members patch value must be a list", "invalidValue"
                    )
                parsed_refs = [
                    ScimMemberRef.model_validate(item)
                    for item in value
                    if isinstance(item, dict)
                ]
                member_user_ids = await resolve_member_user_ids_fn(
                    db, tenant_id=tenant_id, members=parsed_refs
                )
                impacted_user_ids |= await set_group_memberships_fn(
                    db,
                    tenant_id=tenant_id,
                    group_id=group.id,
                    member_user_ids=member_user_ids,
                )
                continue

            if op == "add":
                if isinstance(value, dict):
                    value_list = [value]
                elif isinstance(value, list):
                    value_list = value
                else:
                    raise scim_error_factory(
                        400, "members add value must be list or object", "invalidValue"
                    )
                parsed_refs = [
                    ScimMemberRef.model_validate(item)
                    for item in value_list
                    if isinstance(item, dict)
                ]
                to_add = await resolve_member_user_ids_fn(
                    db, tenant_id=tenant_id, members=parsed_refs
                )
                impacted_user_ids |= await set_group_memberships_fn(
                    db,
                    tenant_id=tenant_id,
                    group_id=group.id,
                    member_user_ids=(existing | to_add),
                )
                continue

            if op == "remove":
                if remove_from_path is not None:
                    to_remove = {remove_from_path}
                elif isinstance(value, dict):
                    to_remove = await resolve_member_user_ids_fn(
                        db,
                        tenant_id=tenant_id,
                        members=[ScimMemberRef.model_validate(value)],
                    )
                elif isinstance(value, list):
                    parsed_refs = [
                        ScimMemberRef.model_validate(item)
                        for item in value
                        if isinstance(item, dict)
                    ]
                    to_remove = await resolve_member_user_ids_fn(
                        db, tenant_id=tenant_id, members=parsed_refs
                    )
                elif value is None:
                    to_remove = set()
                else:
                    raise scim_error_factory(
                        400,
                        "members remove value must be list or object",
                        "invalidValue",
                    )

                impacted_user_ids |= await set_group_memberships_fn(
                    db,
                    tenant_id=tenant_id,
                    group_id=group.id,
                    member_user_ids=(existing - to_remove),
                )
                continue

        raise scim_error_factory(400, "Unsupported patch path", "invalidPath")

    return member_action, impacted_user_ids
