from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import httpx

from scripts.capture_acceptance_runner import (
    build_capture_specs,
    capture_acceptance_evidence,
)


def _windows() -> dict[str, date]:
    return {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 31),
        "close_start_date": date(2025, 12, 1),
        "close_end_date": date(2025, 12, 31),
    }


def _expected_capture_count() -> int:
    specs, _ = build_capture_specs(
        **_windows(),
        close_provider="all",
        close_enforce_finalized=False,
    )
    return len(specs)


def test_build_capture_specs_omits_provider_for_all() -> None:
    specs, normalized_provider = build_capture_specs(
        **_windows(),
        close_provider="all",
        close_enforce_finalized=False,
    )
    by_name = {spec.name: spec for spec in specs}

    assert len(specs) >= 23
    assert normalized_provider == "all"
    assert "provider" not in (by_name["close_package_json"].query_params or {})
    assert "provider" not in (by_name["close_package_csv"].query_params or {})
    assert "provider" not in (by_name["restatements_csv"].query_params or {})


def test_build_capture_specs_normalizes_specific_provider() -> None:
    specs, normalized_provider = build_capture_specs(
        **_windows(),
        close_provider="AWS",
        close_enforce_finalized=True,
    )
    by_name = {spec.name: spec for spec in specs}

    assert normalized_provider == "aws"
    assert (by_name["close_package_json"].query_params or {}).get("provider") == "aws"
    assert (by_name["close_package_csv"].query_params or {}).get("provider") == "aws"
    assert (by_name["restatements_csv"].query_params or {}).get("provider") == "aws"


def test_capture_acceptance_evidence_writes_manifest_and_artifacts(
    tmp_path: Path,
) -> None:
    requests: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/public/csrf":
            return httpx.Response(200, json={"csrf_token": "csrf-token"})
        if "response_format=csv" in request.url.query.decode():
            return httpx.Response(200, text="col_a,col_b\n1,2\n")
        return httpx.Response(200, json={"ok": True, "api_key": "top-secret"})

    bundle_dir, results = asyncio.run(
        capture_acceptance_evidence(
            base_url="http://test",
            token="token",
            output_root=tmp_path,
            transport=httpx.MockTransport(_handler),
            **_windows(),
        )
    )

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(results) == _expected_capture_count()
    assert all(result.ok for result in results)
    assert len(manifest["results"]) == _expected_capture_count()
    assert manifest["close_window"]["provider"] == "all"
    assert (bundle_dir / "acceptance_kpis.json").exists()
    assert (bundle_dir / "acceptance_kpis.csv").exists()

    slo_post_requests = [
        req
        for req in requests
        if req.method == "POST" and req.url.path == "/api/v1/audit/jobs/slo/evidence"
    ]
    assert len(slo_post_requests) == 1
    assert slo_post_requests[0].headers.get("x-csrf-token") == "csrf-token"


def test_capture_acceptance_evidence_continues_after_single_request_failure(
    tmp_path: Path,
) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/public/csrf":
            return httpx.Response(200, json={"csrf_token": "csrf-token"})
        if (
            request.url.path == "/api/v1/costs/acceptance/kpis"
            and "response_format=json" in request.url.query.decode()
        ):
            raise httpx.ConnectError("network down", request=request)
        if "response_format=csv" in request.url.query.decode():
            return httpx.Response(200, text="col_a,col_b\n1,2\n")
        return httpx.Response(200, json={"ok": True})

    bundle_dir, results = asyncio.run(
        capture_acceptance_evidence(
            base_url="http://test",
            token="token",
            output_root=tmp_path,
            transport=httpx.MockTransport(_handler),
            **_windows(),
        )
    )

    failed = [result for result in results if not result.ok]
    assert len(results) == _expected_capture_count()
    assert len(failed) == 1
    assert failed[0].name == "acceptance_kpis_json"
    assert failed[0].error is not None and "ConnectError" in failed[0].error
    assert any(result.ok for result in results)

    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_failed = [item for item in manifest["results"] if not item["ok"]]
    assert len(manifest_failed) == 1
    assert manifest_failed[0]["name"] == "acceptance_kpis_json"
