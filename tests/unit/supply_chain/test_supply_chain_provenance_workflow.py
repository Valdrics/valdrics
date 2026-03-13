from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PINNED_WORKFLOW_PATHS = (
    REPO_ROOT / ".github/workflows/ci.yml",
    REPO_ROOT / ".github/workflows/security-scan.yml",
    REPO_ROOT / ".github/workflows/sbom.yml",
    REPO_ROOT / ".github/workflows/performance-gate.yml",
    REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml",
    REPO_ROOT / ".github/workflows/cla.yml",
)


def test_sbom_workflow_has_attestation_permissions() -> None:
    text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")

    assert "attestations: write" in text
    assert "id-token: write" in text


def test_sbom_workflow_verifies_dependency_locks_before_attestation() -> None:
    text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")

    assert "uv lock --check" in text
    assert "pnpm install --frozen-lockfile" in text
    assert "pnpm audit --audit-level=high" in text


def test_sbom_workflow_attests_provenance_subjects() -> None:
    text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")

    assert "scripts/generate_provenance_manifest.py" in text
    assert "actions/attest-build-provenance@" in text


def test_sbom_workflow_verifies_attestations_before_promotion() -> None:
    text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")

    assert "scripts/verify_supply_chain_attestations.py" in text
    assert "--signer-workflow .github/workflows/sbom.yml" in text
    assert "--artifact ./sbom/valdrics-python-sbom.json" in text
    assert "--artifact ./sbom/valdrics-container-sbom.json" in text
    assert "--artifact ./provenance/supply-chain-manifest.json" in text


def test_ci_workflow_enforces_enterprise_placeholder_guard() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/verify_enterprise_placeholder_guards.py" in text
    assert "scripts/verify_documentation_runtime_contracts.py" in text


def test_ci_workflow_runs_pip_audit_on_pull_requests() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Enforce Python Dependency Vulnerability Gate (pip-audit)" in text
    assert "uv run pip-audit --ignore-vuln CVE-2026-1703" in text


def test_ci_workflow_uses_strict_module_size_gate_and_non_live_fixtures() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert (
        "uv run python3 scripts/verify_python_module_size_budget.py --emit-preferred-signals --emit-cluster-signals"
        in text
    )
    assert "scripts/verify_python_module_preferred_budget_baseline.py" in text
    assert "--enforcement-mode advisory" not in text
    assert "sk_live_ci_testing" not in text
    assert "pk_live_ci_testing" not in text
    assert "sk_live_example_ci_validation_only" not in text
    assert "pk_live_example_ci_validation_only" not in text
    assert "example_paystack_secret_ci_validation_only" in text
    assert "example_paystack_public_ci_validation_only" in text


def test_ci_workflow_has_enterprise_tdd_quality_gate_job() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "enterprise-tdd-quality-gate:" in text
    assert "Enterprise TDD Quality Gate" in text
    assert "scripts/run_enterprise_tdd_gate.py" in text


def test_ci_workflow_shards_backend_pytest_and_combines_coverage() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "pytest:" in text
    assert "Backend Pytest Shard ${{ matrix.shard_id }}" in text
    assert "backend-coverage-${{ matrix.shard_id }}" in text
    assert "pattern: backend-coverage-*" in text
    assert "merge-multiple: true" in text
    assert "coverage combine reports/coverage/shards" in text


def test_workflows_pin_uv_bootstrap_version() -> None:
    workflow_paths = (
        REPO_ROOT / ".github/workflows/ci.yml",
        REPO_ROOT / ".github/workflows/sbom.yml",
        REPO_ROOT / ".github/workflows/security-scan.yml",
        REPO_ROOT / ".github/workflows/performance-gate.yml",
    )

    for workflow_path in workflow_paths:
        text = workflow_path.read_text(encoding="utf-8")
        assert 'version: "latest"' not in text
        assert "${{ env.UV_VERSION }}" in text


def test_performance_gate_supports_reuse_and_ci_automation() -> None:
    perf_text = (REPO_ROOT / ".github/workflows/performance-gate.yml").read_text(
        encoding="utf-8"
    )
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "workflow_call:" in perf_text
    assert "start_local_api:" in perf_text
    assert "bootstrap_tenant:" in perf_text
    assert "scripts/bootstrap_performance_tenant.py" in perf_text
    assert "scripts/load_test_api.py" in perf_text
    assert "uvicorn app.main:app" in perf_text
    assert 'ENVIRONMENT: "staging"' in perf_text
    assert 'TESTING: "false"' in perf_text
    assert 'API_URL: "https://api.staging.valdrics.example"' in perf_text
    assert 'FRONTEND_URL: "https://dashboard.staging.valdrics.example"' in perf_text
    assert "postgres:16.13-alpine" in perf_text
    assert "redis:7.2.13-alpine" in perf_text
    assert "otel/opentelemetry-collector:0.147.0" in perf_text
    assert "Wait for OTEL Collector" in perf_text
    assert "uv run python scripts/validate_runtime_env.py --environment staging" in perf_text
    assert "uv run alembic upgrade head" in perf_text
    assert "uv run celery -A app.shared.core.celery_app:celery_app worker -l info" in perf_text
    assert "performance-health-gate:" in ci_text
    assert "performance-dashboard-gate:" in ci_text
    assert "performance-ops-gate:" in ci_text
    assert "uses: ./.github/workflows/performance-gate.yml" in ci_text
    assert "performance.owner@valdrics.local" not in perf_text
    assert 'performance.owner@valdrics.ai' in perf_text
    assert 'performance.owner@valdrics.ai' in (
        REPO_ROOT / "scripts/bootstrap_performance_tenant.py"
    ).read_text(encoding="utf-8")
    assert 'p95_target: "1.25"' in ci_text
    assert 'name: perf-gate-evidence-${{ inputs.profile }}' in perf_text
    assert 'name: perf-gate-api-log-${{ inputs.profile }}' in perf_text
    assert 'name: perf-gate-worker-log-${{ inputs.profile }}' in perf_text


def test_strict_runtime_preflight_is_hermetic_and_explicit_in_workflows() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    dr_text = (
        REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml"
    ).read_text(encoding="utf-8")

    assert 'API_URL: "https://api.validation.example.com"' in ci_text
    assert 'FRONTEND_URL: "https://app.validation.example.com"' in ci_text
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"' in ci_text
    assert 'API_URL: "https://api.staging.valdrics.example"' in dr_text
    assert 'FRONTEND_URL: "https://dashboard.staging.valdrics.example"' in dr_text
    assert "otel/opentelemetry-collector:0.147.0" in dr_text
    assert "Wait for OTEL Collector" in dr_text
    assert "uv run python scripts/validate_runtime_env.py --environment staging" in dr_text


def test_local_postgres_service_workflows_disable_db_ssl() -> None:
    perf_text = (REPO_ROOT / ".github/workflows/performance-gate.yml").read_text(
        encoding="utf-8"
    )
    dr_text = (
        REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml"
    ).read_text(encoding="utf-8")

    assert 'DATABASE_URL: "postgresql+asyncpg://postgres:local-dev-change-me@127.0.0.1:5432/valdrics"' in perf_text
    assert 'DB_SSL_MODE: "disable"' in perf_text
    assert 'DATABASE_URL: "postgresql+asyncpg://postgres:local-dev-change-me@127.0.0.1:5432/valdrics"' in dr_text
    assert 'DB_SSL_MODE: "disable"' in dr_text


def test_ci_and_security_workflows_fail_on_high_or_critical_infra_and_container_findings() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )

    assert "--severity CRITICAL,HIGH" in ci_text
    assert "--exit-code 1" in ci_text
    assert "--minimum-severity HIGH" in ci_text
    assert "--severity CRITICAL,HIGH" in security_text
    assert "--exit-code 1" in security_text


def test_ci_workflow_pins_tflint_setup_version() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tflint_version: latest" not in ci_text
    assert "tflint_version: v0.61.0" in ci_text




def test_cla_workflow_uses_in_repo_python_implementation() -> None:
    text = (REPO_ROOT / '.github/workflows/cla.yml').read_text(encoding='utf-8')

    assert 'contributor-assistant/github-action' not in text
    assert 'python3 scripts/cla_assistant.py' in text
    assert 'CLA_SIGNATURES_BRANCH: cla-signatures' in text
    assert 'statuses: write' in text
    assert 'issues: write' in text

def test_critical_workflows_use_immutable_action_shas_and_fixed_runner_images() -> None:
    uses_pattern = re.compile(
        r"uses:\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)@([^\s#]+)"
    )

    for workflow_path in PINNED_WORKFLOW_PATHS:
        text = workflow_path.read_text(encoding="utf-8")
        assert "runs-on: ubuntu-latest" not in text
        for _, ref in uses_pattern.findall(text):
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (
                f"{workflow_path.name} uses non-immutable action ref {ref!r}"
            )
