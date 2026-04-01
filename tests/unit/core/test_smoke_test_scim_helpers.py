from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

import scripts.smoke_test_scim_helpers as scim_helpers
from scripts.smoke_test_scim_helpers import (
    Check,
    build_group_add_member_patch,
    record_check,
    require_success,
    scim_url,
    safe_json,
)


def test_scim_url_keeps_scim_root_path() -> None:
    assert (
        scim_url("https://example.com/scim/v2", "/Users")
        == "https://example.com/scim/v2/Users"
    )


def test_require_success_includes_scim_detail_for_non_2xx() -> None:
    response = httpx.Response(
        400,
        json={"detail": "invalid patch"},
        request=httpx.Request("PATCH", "https://example.com/scim/v2/Groups/1"),
    )
    ok, detail = require_success(response)
    assert ok is False
    assert detail == "invalid patch"


def test_safe_json_returns_none_for_invalid_json() -> None:
    response = httpx.Response(
        500,
        text="plain text error",
        request=httpx.Request("GET", "https://example.com/scim/v2/Schemas"),
    )
    assert safe_json(response) is None


def test_record_check_appends_structured_check_with_status_code() -> None:
    checks: list[Check] = []
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://example.com/scim/v2/ServiceProviderConfig"),
    )
    record_check(
        checks,
        name="scim.service_provider_config",
        resp=response,
        started=0.0,
        ok=True,
        detail=None,
    )
    assert len(checks) == 1
    assert checks[0].name == "scim.service_provider_config"
    assert checks[0].passed is True
    assert checks[0].status_code == 200


def test_record_check_uses_perf_counter_for_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks: list[Check] = []
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://example.com/scim/v2/Schemas"),
    )
    monkeypatch.setattr(scim_helpers, "_perf_counter", lambda: 10.5)

    record_check(
        checks,
        name="scim.schemas",
        resp=response,
        started=10.0,
        ok=True,
        detail=None,
    )

    assert checks[0].duration_ms == 500.0


def test_build_group_add_member_patch_uses_patchop_schema() -> None:
    payload = build_group_add_member_patch("abc123")
    assert payload["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    operations = payload["Operations"]
    assert isinstance(operations, list)
    assert operations[0]["path"] == "members"


def test_write_out_stages_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "scim-smoke.json"
    staged_path = tmp_path / ".scim-smoke.json.tmp"

    def _fake_stage(path: Path, payload: object, **_: object) -> Path:
        assert path == output_path
        staged_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return staged_path

    def _fake_promote(staged: Path, output: Path) -> None:
        staged.replace(output)

    monkeypatch.setattr(scim_helpers, "stage_json_file", _fake_stage)
    monkeypatch.setattr(scim_helpers, "promote_staged_file", _fake_promote)

    scim_helpers.write_out(str(output_path), {"passed": True})

    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True
