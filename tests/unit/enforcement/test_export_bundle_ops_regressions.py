from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.enforcement.domain.export_bundle_ops import (
    build_export_bundle_payload,
    build_signed_export_manifest_payload,
)


def _count_result(value: int) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalars_result(rows: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    return result


def _canonical_json(payload: dict[str, object]) -> str:
    def _default(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_default)


@pytest.mark.asyncio
async def test_build_export_bundle_collapses_computed_context_lineage_across_generated_at() -> None:
    tenant_id = uuid4()
    base_generated_at = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    snapshot_one = {
        "context_version": "v1",
        "generated_at": base_generated_at.isoformat(),
        "month_start": "2026-03-01T00:00:00+00:00",
        "month_end": "2026-03-31T23:59:59+00:00",
        "month_elapsed_days": 1,
        "month_total_days": 31,
        "observed_cost_days": 1,
        "latest_cost_date": "2026-03-01",
        "data_source_mode": "actual",
    }
    snapshot_two = dict(snapshot_one)
    snapshot_two["generated_at"] = (base_generated_at + timedelta(seconds=5)).isoformat()
    decisions = [
        SimpleNamespace(id=uuid4(), response_payload=snapshot_one),
        SimpleNamespace(id=uuid4(), response_payload=snapshot_two),
    ]
    db = AsyncMock()
    db.execute.side_effect = [
        _count_result(2),
        _scalars_result(decisions),
        _count_result(0),
        _scalars_result([]),
    ]
    export_events_counter = MagicMock()
    export_events_counter.labels.return_value.inc = MagicMock()

    bundle = await build_export_bundle_payload(
        db=db,
        tenant_id=tenant_id,
        window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        max_rows=100,
        as_utc_fn=lambda value: value,
        normalize_policy_document_schema_version_fn=lambda value: value or "unknown",
        normalize_policy_document_sha256_fn=lambda value: value or "0" * 64,
        computed_context_snapshot_fn=lambda payload: dict(payload or {}),
        json_default_fn=lambda value: value.isoformat()
        if isinstance(value, datetime)
        else str(value),
        render_decisions_csv_fn=lambda _rows: "decisions",
        render_approvals_csv_fn=lambda _rows: "approvals",
        export_events_counter=export_events_counter,
        utcnow_fn=lambda: datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
    )

    assert len(bundle["computed_context_lineage"]) == 1
    assert bundle["computed_context_lineage"][0]["decision_count"] == 2
    assert bundle["computed_context_lineage"][0]["generated_at"] == snapshot_one["generated_at"]


def test_build_signed_export_manifest_payload_signs_generated_at() -> None:
    generated_at = datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)
    bundle = SimpleNamespace(
        generated_at=generated_at,
        window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        decision_count_db=2,
        decision_count_exported=2,
        approval_count_db=1,
        approval_count_exported=1,
        decisions_sha256="a" * 64,
        approvals_sha256="b" * 64,
        policy_lineage_sha256="c" * 64,
        policy_lineage=[{"policy_document_schema_version": "v1", "decision_count": 2}],
        computed_context_lineage_sha256="d" * 64,
        computed_context_lineage=[{"context_version": "v1", "decision_count": 2}],
        parity_ok=True,
    )

    manifest = build_signed_export_manifest_payload(
        tenant_id=uuid4(),
        bundle=bundle,
        resolve_signing_secret_fn=lambda: "x" * 32,
        resolve_signing_key_id_fn=lambda: "test-key",
        canonical_json_fn=_canonical_json,
    )

    canonical_payload = json.loads(manifest["canonical_content_json"])
    assert canonical_payload["generated_at"] == generated_at.isoformat()
