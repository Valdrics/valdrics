"""Shared RLS tooling helpers for legacy audit/remediation scripts."""

from __future__ import annotations

from collections.abc import Iterable

from app.shared.core.constants import RLS_EXEMPT_TABLES

RLS_EXEMPT_TABLES_SET = frozenset(
    str(table_name).strip().lower()
    for table_name in RLS_EXEMPT_TABLES
    if str(table_name).strip()
)


def normalize_table_name(table_name: str) -> str:
    return str(table_name or "").strip().lower()


def is_rls_exempt_table(table_name: str) -> bool:
    return normalize_table_name(table_name) in RLS_EXEMPT_TABLES_SET


def requires_rls(*, table_name: str, has_tenant_id: bool) -> bool:
    return bool(has_tenant_id) and not is_rls_exempt_table(table_name)


def filter_rls_candidate_tables(table_names: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        table_name
        for table_name in (str(name).strip() for name in table_names)
        if table_name and not is_rls_exempt_table(table_name)
    )
