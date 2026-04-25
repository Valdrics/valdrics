"""Helpers for environment-scoped TVC receipt generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_DEPLOYMENT_TVC_BY_ENV = {
    "staging": Path("contracts/examples/unified-platform-deploy-staging.yaml"),
    "production": Path("contracts/examples/unified-platform-deploy-production.yaml"),
}
DEFAULT_GIT_SHA = "0" * 40


def load_technology_value_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Technology Value Contract must be a mapping: {path}")
    return payload


def iso_timestamp_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _normalized_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def build_managed_deployment_admission_receipt(
    *,
    contract: dict[str, Any],
    environment: str,
    release_tag: str,
    git_sha: str,
    deployment_report: dict[str, Any],
    evidence_refs: list[str],
) -> dict[str, Any]:
    metadata = contract["metadata"]
    subject = contract["subject"]
    primary_metric = contract["unit_economics"]["primary_metric"]
    captured_at = iso_timestamp_now()

    ready_for_unified_platform = bool(deployment_report.get("ready_for_unified_platform"))
    ready_for_release_promotion = bool(
        deployment_report.get("ready_for_release_promotion")
    )
    ready_for_terraform = bool(deployment_report.get("ready_for_terraform"))
    admission_ok = (
        ready_for_unified_platform
        and ready_for_release_promotion
        and ready_for_terraform
    )

    anomalies = sorted(
        set(
            _normalized_strings(deployment_report.get("runtime_validation_blockers"))
            + _normalized_strings(
                deployment_report.get("cloudflare_pages_public_env_blockers")
            )
            + _normalized_strings(
                deployment_report.get("artifact_registry_release_value_blockers")
            )
            + _normalized_strings(deployment_report.get("terraform_value_blockers"))
        )
    )

    return {
        "specversion": "1.0",
        "id": f"urn:valdrics:tvc:admission:{environment}:{release_tag}",
        "source": "urn:valdrics:workflow:deploy-unified-platform",
        "type": "io.valdrics.tvc.execution.receipt.v1",
        "subject": metadata["name"],
        "time": captured_at,
        "dataschema": "urn:valdrics:schemas:execution_receipt:v0.1",
        "datacontenttype": "application/json",
        "data": {
            "phase": "admission",
            "contract_ref": {
                "api_version": contract["apiVersion"],
                "kind": contract["kind"],
                "name": metadata["name"],
                "version": metadata["version"],
            },
            "subject": {
                "system": subject["system"],
                "service": subject["service"],
                "environment": environment,
                "deployment_id": f"{environment}:{release_tag}",
                "git_sha": git_sha or DEFAULT_GIT_SHA,
            },
            "window": {
                "start": captured_at,
                "end": captured_at,
            },
            "actuals": {
                "unit_economics": {
                    "metric": primary_metric["name"],
                    "value": 1.0 if admission_ok else 0.0,
                    "direction": primary_metric["direction"],
                    "business_metric": str(
                        primary_metric.get("business_metric")
                        or "failed_change_rate"
                    ),
                }
            },
            "evaluations": {
                "cost_status": "not_measured",
                "carbon_status": "not_measured",
                "compliance_status": "pass" if admission_ok else "fail",
                "performance_status": "not_measured",
                "recommendation": "accept" if admission_ok else "review",
            },
            "anomalies": anomalies,
            "admission": {
                "ready_for_unified_platform": ready_for_unified_platform,
                "ready_for_release_promotion": ready_for_release_promotion,
                "ready_for_terraform": ready_for_terraform,
                "runtime_validation_blockers": _normalized_strings(
                    deployment_report.get("runtime_validation_blockers")
                ),
                "cloudflare_pages_public_env_blockers": _normalized_strings(
                    deployment_report.get("cloudflare_pages_public_env_blockers")
                ),
                "artifact_registry_release_value_blockers": _normalized_strings(
                    deployment_report.get("artifact_registry_release_value_blockers")
                ),
                "terraform_value_blockers": _normalized_strings(
                    deployment_report.get("terraform_value_blockers")
                ),
            },
            "provenance": {
                "generated_at": captured_at,
                "generator": "valdrics.managed_deployment.tvc_admission",
                "evidence_refs": evidence_refs,
            },
        },
    }
