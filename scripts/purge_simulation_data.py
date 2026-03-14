from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql.elements import ColumnElement

import app.models  # noqa: F401 - register ORM metadata
from app.shared.db.base import Base
from app.shared.db.session import async_session_maker, mark_session_system_context
from scripts.safety_guardrails import (
    current_environment,
    ensure_environment_confirmation,
    ensure_force_and_phrase,
    ensure_interactive_confirmation,
    ensure_operator_reason,
    ensure_protected_environment_bypass,
)

CONFIRM_PHRASE = (
    "PURGE_TENANT_DATA"
    # nosec B105 - explicit operator confirmation phrase
)
INTERACTIVE_CONFIRM_TOKEN = (
    "PURGE_TENANTS"
    # nosec B105 - explicit interactive confirmation token
)
PROD_BYPASS = (
    "I_UNDERSTAND_TENANT_PURGE_RISK"
    # nosec B105 - explicit protected-environment bypass phrase
)
NONINTERACTIVE_BYPASS_ENV = "VALDRICS_ALLOW_NONINTERACTIVE_TENANT_PURGE"
MIN_REASON_LENGTH = 16
BATCH_SIZE = 50_000


@dataclass(frozen=True)
class PurgeTarget:
    table_name: str
    tenant_columns: tuple[str, ...]
    user_columns: tuple[str, ...]
    batched: bool = False


def _validate_request(
    *,
    force: bool,
    phrase: str,
    confirm_environment: str,
    no_prompt: bool,
    operator: str,
    reason: str,
) -> None:
    environment = current_environment()
    ensure_protected_environment_bypass(
        environment=environment,
        bypass_env_var="VALDRICS_ALLOW_PROD_SCALE_TENANT_PURGE",
        bypass_phrase=PROD_BYPASS,
        operation_label="simulation tenant purge",
    )
    ensure_force_and_phrase(force=force, phrase=phrase, expected_phrase=CONFIRM_PHRASE)
    ensure_environment_confirmation(
        confirm_environment=confirm_environment,
        environment=environment,
    )
    ensure_interactive_confirmation(
        token=INTERACTIVE_CONFIRM_TOKEN,
        no_prompt=no_prompt,
        noninteractive_env_var=NONINTERACTIVE_BYPASS_ENV,
    )
    ensure_operator_reason(
        operator=operator,
        reason=reason,
        min_reason_length=MIN_REASON_LENGTH,
        operation_label="simulation tenant purge",
    )


def _foreign_key_matches(column: object, table_name: str) -> bool:
    foreign_keys = getattr(column, "foreign_keys", None)
    if foreign_keys is None:
        return False
    for foreign_key in foreign_keys:
        target_column = getattr(foreign_key, "column", None)
        if target_column is None:
            continue
        if str(getattr(target_column.table, "name", "")).strip().lower() == table_name:
            return True
    return False


def collect_purge_targets(metadata: MetaData) -> tuple[PurgeTarget, ...]:
    targets: list[PurgeTarget] = []
    seen: set[str] = set()

    for table in reversed(metadata.sorted_tables):
        table_name = str(table.name)
        if table_name in seen or table_name == "alembic_version":
            continue

        tenant_columns: list[str] = []
        user_columns: list[str] = []
        for column in table.columns:
            column_name = str(column.name)
            if column_name == "tenant_id" or _foreign_key_matches(column, "tenants"):
                tenant_columns.append(column_name)
            if (
                column_name == "user_id"
                or _foreign_key_matches(column, "users")
            ):
                user_columns.append(column_name)

        if table_name == "tenants":
            tenant_columns = ["id"]
        elif table_name == "users":
            tenant_columns = list(dict.fromkeys([*tenant_columns, "tenant_id"]))

        tenant_columns = list(dict.fromkeys(tenant_columns))
        user_columns = list(dict.fromkeys(user_columns))

        if not tenant_columns and not user_columns:
            continue

        targets.append(
            PurgeTarget(
                table_name=table_name,
                tenant_columns=tuple(tenant_columns),
                user_columns=tuple(user_columns),
                batched=table_name == "cost_records",
            )
        )
        seen.add(table_name)

    return tuple(targets)


def _build_delete_predicates(
    *,
    table: Table,
    target: PurgeTarget,
    tenant_ids: Iterable[object],
    user_ids: Iterable[object],
) -> list[ColumnElement[bool]]:
    predicates: list[ColumnElement[bool]] = []
    tenant_id_list = tuple(tenant_ids)
    user_id_list = tuple(user_ids)

    for column_name in target.tenant_columns:
        if tenant_id_list and column_name in table.c:
            predicates.append(table.c[column_name].in_(tenant_id_list))
    for column_name in target.user_columns:
        if user_id_list and column_name in table.c:
            predicates.append(table.c[column_name].in_(user_id_list))
    return predicates


async def _delete_batched(
    *,
    session: object,
    table: Table,
    predicates: list[ColumnElement[bool]],
    batch_size: int = BATCH_SIZE,
) -> int:
    id_column = table.c.get("id")
    if id_column is None:
        result = await session.execute(delete(table).where(or_(*predicates)))
        await session.commit()
        return int(result.rowcount or 0)

    total_deleted = 0
    while True:
        id_rows = await session.execute(
            select(id_column).where(or_(*predicates)).limit(batch_size)
        )
        batch_ids = [row[0] for row in id_rows.fetchall()]
        if not batch_ids:
            break
        result = await session.execute(delete(table).where(id_column.in_(batch_ids)))
        await session.commit()
        total_deleted += int(result.rowcount or 0)
    return total_deleted


async def purge_simulation_data(
    *,
    dry_run: bool,
    tenant_ids: tuple[str, ...],
    operator: str,
    reason: str,
) -> dict[str, object]:
    if not tenant_ids:
        raise RuntimeError("--tenant-id is required at least once.")
    targets = collect_purge_targets(Base.metadata)
    parsed_tenant_ids = [UUID(str(raw_id).strip()) for raw_id in tenant_ids]

    async with async_session_maker() as session:
        await mark_session_system_context(session)
        tenant_rows = await session.execute(
            select(Base.metadata.tables["tenants"].c.id).where(
                Base.metadata.tables["tenants"].c.id.in_(parsed_tenant_ids)
            )
        )
        existing_tenant_ids = [row[0] for row in tenant_rows.fetchall()]
        missing_tenant_ids = sorted(
            str(tenant_id) for tenant_id in (set(parsed_tenant_ids) - set(existing_tenant_ids))
        )
        if missing_tenant_ids:
            raise RuntimeError(
                "Tenant IDs not found: " + ", ".join(missing_tenant_ids)
            )
        if not existing_tenant_ids:
            payload = {
                "tenant_count": 0,
                "user_count": 0,
                "table_targets": [],
            }
            print(json.dumps({"mode": "dry_run" if dry_run else "executed", **payload}, sort_keys=True))
            return payload

        user_rows = await session.execute(
            select(Base.metadata.tables["users"].c.id).where(
                Base.metadata.tables["users"].c.tenant_id.in_(existing_tenant_ids)
            )
        )
        user_ids = [row[0] for row in user_rows.fetchall()]

        preview: list[dict[str, object]] = []
        deleted_rows: dict[str, int] = {}
        for target in targets:
            table = Base.metadata.tables[target.table_name]
            predicates = _build_delete_predicates(
                table=table,
                target=target,
                tenant_ids=existing_tenant_ids,
                user_ids=user_ids,
            )
            if not predicates:
                continue
            preview.append(
                {
                    "table": target.table_name,
                    "tenant_columns": list(target.tenant_columns),
                    "user_columns": list(target.user_columns),
                    "batched": target.batched,
                }
            )
            if dry_run:
                continue
            if target.batched:
                deleted_rows[target.table_name] = await _delete_batched(
                    session=session,
                    table=table,
                    predicates=predicates,
                )
            else:
                result = await session.execute(delete(table).where(or_(*predicates)))
                await session.commit()
                deleted_rows[target.table_name] = int(result.rowcount or 0)

        payload = {
            "tenant_count": len(existing_tenant_ids),
            "user_count": len(user_ids),
            "tenant_ids": [str(tenant_id) for tenant_id in existing_tenant_ids],
            "table_targets": preview,
            "deleted_rows": deleted_rows,
            "operator": operator.strip() if not dry_run else None,
            "reason": reason.strip() if not dry_run else None,
        }
        print(json.dumps({"mode": "dry_run" if dry_run else "executed", **payload}, sort_keys=True))
        return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run by default. Purge all data for explicitly supplied tenant IDs."
    )
    parser.add_argument(
        "--tenant-id",
        action="append",
        default=[],
        help="Tenant UUID to purge. Repeat for multiple tenants.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the purge. Without this flag the script only reports impact.",
    )
    parser.add_argument("--operator", default="", help="Operator identifier (email or handle).")
    parser.add_argument(
        "--reason",
        default="",
        help=f"Break-glass reason (minimum {MIN_REASON_LENGTH} characters).",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--confirm-phrase", default="")
    parser.add_argument("--confirm-environment", default="")
    parser.add_argument("--no-prompt", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.execute:
            _validate_request(
                force=bool(args.force),
                phrase=str(args.confirm_phrase),
                confirm_environment=str(args.confirm_environment),
                no_prompt=bool(args.no_prompt),
                operator=str(args.operator),
                reason=str(args.reason),
            )
        asyncio.run(
            purge_simulation_data(
                dry_run=not bool(args.execute),
                tenant_ids=tuple(args.tenant_id),
                operator=str(args.operator),
                reason=str(args.reason),
            )
        )
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    except (OSError, TypeError, ValueError) as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
