from __future__ import annotations

import httpx

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


def test_build_group_add_member_patch_uses_patchop_schema() -> None:
    payload = build_group_add_member_patch("abc123")
    assert payload["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    operations = payload["Operations"]
    assert isinstance(operations, list)
    assert operations[0]["path"] == "members"
