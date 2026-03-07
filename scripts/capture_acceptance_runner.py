"""Core capture runner for acceptance evidence artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode, urljoin

import httpx

from app.shared.core.evidence_capture import redact_secrets

EVIDENCE_CAPTURE_RECOVERABLE_EXCEPTIONS = (
    httpx.HTTPError,
    json.JSONDecodeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)

CaptureResponseKind = Literal["json", "text"]


@dataclass(frozen=True)
class CaptureResult:
    name: str
    path: str
    status_code: int | None
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class CaptureSpec:
    name: str
    output_file: str
    method: Literal["GET", "POST"]
    path: str
    response_kind: CaptureResponseKind
    query_params: dict[str, str] | None = None
    request_json: dict[str, Any] | None = None


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    safe_mkdir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def format_exception(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return f"{exc.__class__.__name__}: {message}"
    return exc.__class__.__name__


def build_url(base_url: str, path: str) -> str:
    normalized_base = base_url if base_url.endswith("/") else base_url + "/"
    normalized_path = path[1:] if path.startswith("/") else path
    return urljoin(normalized_base, normalized_path)


def _slo_window_hours(start_date: date, end_date: date) -> int:
    try:
        delta_days = (end_date - start_date).days
        return max(24, min(24 * 30, int(delta_days) * 24))
    except EVIDENCE_CAPTURE_RECOVERABLE_EXCEPTIONS:
        return 24 * 7


def build_capture_specs(
    *,
    start_date: date,
    end_date: date,
    close_start_date: date,
    close_end_date: date,
    close_provider: str,
    close_enforce_finalized: bool,
) -> tuple[list[CaptureSpec], str]:
    common_window = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    normalized_provider = str(close_provider or "all").strip().lower() or "all"
    close_params = {
        "start_date": close_start_date.isoformat(),
        "end_date": close_end_date.isoformat(),
        "enforce_finalized": str(bool(close_enforce_finalized)).lower(),
    }
    if normalized_provider != "all":
        close_params["provider"] = normalized_provider

    specs: list[CaptureSpec] = [
        CaptureSpec(
            name="acceptance_kpis_json",
            output_file="acceptance_kpis.json",
            method="GET",
            path="/api/v1/costs/acceptance/kpis",
            response_kind="json",
            query_params={**common_window, "response_format": "json"},
        ),
        CaptureSpec(
            name="acceptance_kpis_csv",
            output_file="acceptance_kpis.csv",
            method="GET",
            path="/api/v1/costs/acceptance/kpis",
            response_kind="text",
            query_params={**common_window, "response_format": "csv"},
        ),
        CaptureSpec(
            name="leadership_kpis_json",
            output_file="leadership_kpis.json",
            method="GET",
            path="/api/v1/leadership/kpis",
            response_kind="json",
            query_params={**common_window, "response_format": "json"},
        ),
        CaptureSpec(
            name="leadership_kpis_csv",
            output_file="leadership_kpis.csv",
            method="GET",
            path="/api/v1/leadership/kpis",
            response_kind="text",
            query_params={**common_window, "response_format": "csv"},
        ),
        CaptureSpec(
            name="savings_proof_json",
            output_file="savings_proof.json",
            method="GET",
            path="/api/v1/savings/proof",
            response_kind="json",
            query_params={**common_window, "response_format": "json"},
        ),
        CaptureSpec(
            name="savings_proof_csv",
            output_file="savings_proof.csv",
            method="GET",
            path="/api/v1/savings/proof",
            response_kind="text",
            query_params={**common_window, "response_format": "csv"},
        ),
        CaptureSpec(
            name="commercial_quarterly_report_json",
            output_file="commercial_quarterly_report.json",
            method="GET",
            path="/api/v1/leadership/reports/quarterly",
            response_kind="json",
            query_params={"period": "previous", "response_format": "json"},
        ),
        CaptureSpec(
            name="commercial_quarterly_report_csv",
            output_file="commercial_quarterly_report.csv",
            method="GET",
            path="/api/v1/leadership/reports/quarterly",
            response_kind="text",
            query_params={"period": "previous", "response_format": "csv"},
        ),
        CaptureSpec(
            name="integration_acceptance_evidence_json",
            output_file="integration_acceptance_evidence.json",
            method="GET",
            path="/api/v1/settings/notifications/acceptance-evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="jobs_slo_json",
            output_file="jobs_slo.json",
            method="GET",
            path="/api/v1/jobs/slo",
            response_kind="json",
        ),
        CaptureSpec(
            name="job_slo_evidence_capture_json",
            output_file="job_slo_evidence_capture.json",
            method="POST",
            path="/api/v1/audit/jobs/slo/evidence",
            response_kind="json",
            request_json={
                "window_hours": int(_slo_window_hours(start_date, end_date)),
                "target_success_rate_percent": 95.0,
            },
        ),
        CaptureSpec(
            name="job_slo_evidence_json",
            output_file="job_slo_evidence.json",
            method="GET",
            path="/api/v1/audit/jobs/slo/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="profile_json",
            output_file="profile.json",
            method="GET",
            path="/api/v1/settings/profile",
            response_kind="json",
        ),
        CaptureSpec(
            name="close_package_json",
            output_file="close_package.json",
            method="GET",
            path="/api/v1/costs/reconciliation/close-package",
            response_kind="json",
            query_params={**close_params, "response_format": "json"},
        ),
        CaptureSpec(
            name="close_package_csv",
            output_file="close_package.csv",
            method="GET",
            path="/api/v1/costs/reconciliation/close-package",
            response_kind="text",
            query_params={**close_params, "response_format": "csv"},
        ),
        CaptureSpec(
            name="restatements_csv",
            output_file="restatements.csv",
            method="GET",
            path="/api/v1/costs/reconciliation/restatements",
            response_kind="text",
            query_params={**close_params, "response_format": "csv"},
        ),
        CaptureSpec(
            name="realized_savings_json",
            output_file="realized_savings.json",
            method="GET",
            path="/api/v1/savings/realized/events",
            response_kind="json",
            query_params={**common_window, "response_format": "json", "limit": "500"},
        ),
        CaptureSpec(
            name="realized_savings_csv",
            output_file="realized_savings.csv",
            method="GET",
            path="/api/v1/savings/realized/events",
            response_kind="text",
            query_params={**common_window, "response_format": "csv", "limit": "500"},
        ),
        CaptureSpec(
            name="performance_load_test_evidence_json",
            output_file="performance_load_test_evidence.json",
            method="GET",
            path="/api/v1/audit/performance/load-test/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="ingestion_persistence_benchmark_evidence_json",
            output_file="ingestion_persistence_benchmark_evidence.json",
            method="GET",
            path="/api/v1/audit/performance/ingestion/persistence/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="ingestion_soak_evidence_json",
            output_file="ingestion_soak_evidence.json",
            method="GET",
            path="/api/v1/audit/performance/ingestion/soak/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="partitioning_evidence_json",
            output_file="partitioning_evidence.json",
            method="GET",
            path="/api/v1/audit/performance/partitioning/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="tenant_isolation_evidence_json",
            output_file="tenant_isolation_evidence.json",
            method="GET",
            path="/api/v1/audit/tenancy/isolation/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="identity_smoke_evidence_json",
            output_file="identity_smoke_evidence.json",
            method="GET",
            path="/api/v1/audit/identity/idp-smoke/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="sso_federation_validation_evidence_json",
            output_file="sso_federation_validation_evidence.json",
            method="GET",
            path="/api/v1/audit/identity/sso-federation/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
        CaptureSpec(
            name="carbon_assurance_evidence_json",
            output_file="carbon_assurance_evidence.json",
            method="GET",
            path="/api/v1/audit/carbon/assurance/evidence",
            response_kind="json",
            query_params={"limit": "200"},
        ),
    ]
    return specs, normalized_provider


def _request_url(base_url: str, spec: CaptureSpec) -> str:
    url = build_url(base_url, spec.path)
    if spec.query_params:
        return f"{url}?{urlencode(spec.query_params)}"
    return url


def _record_result(
    results: list[CaptureResult],
    *,
    output_root: Path,
    name: str,
    file_path: Path,
    status_code: int | None,
    ok: bool,
    error: str | None = None,
) -> None:
    results.append(
        CaptureResult(
            name=name,
            path=str(file_path.relative_to(output_root)),
            status_code=status_code,
            ok=ok,
            error=error,
        )
    )


async def _capture_spec(
    *,
    client: httpx.AsyncClient,
    base_url: str,
    bundle_dir: Path,
    output_root: Path,
    spec: CaptureSpec,
    results: list[CaptureResult],
) -> None:
    output_path = bundle_dir / spec.output_file
    try:
        response = await client.request(
            spec.method,
            _request_url(base_url, spec),
            json=spec.request_json if spec.method != "GET" else None,
        )
        if response.is_success:
            if spec.response_kind == "json":
                payload = redact_secrets(response.json())
                write_json(output_path, payload)
            else:
                write_text(output_path, response.text)
            _record_result(
                results,
                output_root=output_root,
                name=spec.name,
                file_path=output_path,
                status_code=response.status_code,
                ok=True,
            )
            return
        _record_result(
            results,
            output_root=output_root,
            name=spec.name,
            file_path=output_path,
            status_code=response.status_code,
            ok=False,
            error=response.text,
        )
    except EVIDENCE_CAPTURE_RECOVERABLE_EXCEPTIONS as exc:
        _record_result(
            results,
            output_root=output_root,
            name=spec.name,
            file_path=output_path,
            status_code=None,
            ok=False,
            error=format_exception(exc),
        )


async def _bootstrap_csrf(
    *,
    client: httpx.AsyncClient,
    base_url: str,
) -> None:
    # CSRF is best-effort and only impacts unsafe methods in this script.
    try:
        csrf_resp = await client.get(build_url(base_url, "/api/v1/public/csrf"))
        if csrf_resp.is_success:
            token_value = (csrf_resp.json() or {}).get("csrf_token")
            if token_value:
                client.headers["X-CSRF-Token"] = str(token_value)
    except EVIDENCE_CAPTURE_RECOVERABLE_EXCEPTIONS:
        pass


async def capture_acceptance_evidence(
    *,
    base_url: str,
    token: str,
    output_root: Path,
    start_date: date,
    end_date: date,
    close_start_date: date,
    close_end_date: date,
    close_provider: str = "all",
    close_enforce_finalized: bool = False,
    timeout_seconds: float = 60.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[Path, list[CaptureResult]]:
    timestamp = utc_now_compact()
    bundle_dir = output_root / timestamp
    safe_mkdir(bundle_dir)

    headers = {"Authorization": f"Bearer {token}"}
    results: list[CaptureResult] = []
    specs, normalized_provider = build_capture_specs(
        start_date=start_date,
        end_date=end_date,
        close_start_date=close_start_date,
        close_end_date=close_end_date,
        close_provider=close_provider,
        close_enforce_finalized=close_enforce_finalized,
    )

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        headers=headers,
        transport=transport,
    ) as client:
        await _bootstrap_csrf(client=client, base_url=base_url)
        for spec in specs:
            await _capture_spec(
                client=client,
                base_url=base_url,
                bundle_dir=bundle_dir,
                output_root=output_root,
                spec=spec,
                results=results,
            )

    manifest = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "close_window": {
            "start_date": close_start_date.isoformat(),
            "end_date": close_end_date.isoformat(),
            "provider": normalized_provider or "all",
            "enforce_finalized": bool(close_enforce_finalized),
        },
        "results": [result.__dict__ for result in results],
    }
    write_json(bundle_dir / "manifest.json", manifest)
    return bundle_dir, results
