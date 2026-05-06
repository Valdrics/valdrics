from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PINNED_WORKFLOW_PATHS = (
    REPO_ROOT / ".github/workflows/ci.yml",
    REPO_ROOT / ".github/workflows/security-scan.yml",
    REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml",
    REPO_ROOT / ".github/workflows/performance-mainline.yml",
    REPO_ROOT / ".github/workflows/carbon-footprint.yml",
    REPO_ROOT / ".github/workflows/dashboard-browser-mainline.yml",
    REPO_ROOT / ".github/workflows/sbom.yml",
    REPO_ROOT / ".github/workflows/release-unified-platform.yml",
    REPO_ROOT / ".github/workflows/publish-artifact-registry-images.yml",
    REPO_ROOT / ".github/workflows/deploy-unified-platform.yml",
    REPO_ROOT / ".github/workflows/performance-gate.yml",
    REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml",
    REPO_ROOT / ".github/workflows/cla.yml",
)
PINNED_COMPOSITE_ACTION_PATHS = (
    REPO_ROOT / ".github/actions/setup-python-uv/action.yml",
    REPO_ROOT / ".github/actions/setup-dashboard/action.yml",
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
    assert "actions/dependency-review-action@" not in text


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


def test_sbom_workflow_push_paths_cover_frontend_dependency_surface() -> None:
    text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")

    assert "scripts/generate_provenance_manifest.py" in text
    assert "scripts/verify_supply_chain_attestations.py" in text
    assert "dashboard/package.json" in text
    assert "dashboard/pnpm-lock.yaml" in text
    assert ".github/workflows/sbom.yml" in text


def test_publish_artifact_registry_workflow_uses_digest_promotion_contract() -> None:
    text = (
        REPO_ROOT / ".github/workflows/publish-artifact-registry-images.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "id-token: write" in text
    assert "google-github-actions/auth@" in text
    assert "gcloud auth configure-docker" in text
    assert "artifact-registry-release.json" in text
    assert "artifact-registry-release.env" in text
    assert "valdrics-api" in text
    assert "promotion_ref" in text
    assert "API_IMAGE_DIGEST" in text
    assert "immutable_artifact_registry_promotion" in text


def test_ci_workflow_enforces_enterprise_placeholder_guard() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/verify_enterprise_placeholder_guards.py" in text
    assert "scripts/verify_documentation_runtime_contracts.py" in text


def test_ci_workflow_runs_pip_audit_on_pull_requests() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Enforce Python Dependency Vulnerability Gate (pip-audit)" in text
    assert (
        "uv run pip-audit --ignore-vuln CVE-2026-1703 --ignore-vuln CVE-2026-3219"
        in text
    )


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


def test_enterprise_tdd_mainline_workflow_hosts_the_enterprise_gate() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    enterprise_text = (
        REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml"
    ).read_text(encoding="utf-8")

    assert "enterprise-tdd-quality-gate:" not in ci_text
    assert "Enterprise TDD Quality Gate" not in ci_text
    assert "enterprise-tdd-quality-gate:" in enterprise_text
    assert "Enterprise TDD Quality Gate" in enterprise_text
    assert "scripts/run_enterprise_tdd_gate.py" in enterprise_text
    assert "postgres:16.13-alpine" in enterprise_text
    assert 'CSRF_SECRET_KEY: "ci-csrf-secret-key-32-chars-min-000000"' in enterprise_text
    assert 'ENCRYPTION_KEY: "ci-encryption-key-32-chars-min-00000000"' in enterprise_text
    assert 'SUPABASE_JWT_SECRET: "ci-supabase-jwt-secret-32-chars-0000"' in enterprise_text
    assert "--database-url" in enterprise_text
    assert "ENTERPRISE_GATE_DATABASE_URL" in enterprise_text
    assert 'branches: [main]' in enterprise_text
    assert "workflow_dispatch:" in enterprise_text


def test_ci_workflow_shards_backend_pytest_and_combines_coverage() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    coverage_lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    coverage_match = re.search(
        r'\[\[package\]\]\nname = "coverage"\nversion = "([^"]+)"',
        coverage_lock_text,
    )

    assert coverage_match is not None
    coverage_version = coverage_match.group(1)

    assert "classify-changes:" in text
    assert "name: Classify CI Surfaces" in text
    assert "backend_ci: ${{ steps.classify.outputs.backend_ci }}" in text
    assert "dashboard_ci: ${{ steps.classify.outputs.dashboard_ci }}" in text
    assert "github.event_name != 'pull_request' || needs.classify-changes.outputs.backend_ci == 'true'" in text
    assert "github.event_name != 'pull_request' || needs.classify-changes.outputs.dashboard_ci == 'true'" in text
    assert "app/*|tests/*|migrations/*|alembic.ini|pyproject.toml|uv.lock|scripts/*" in text
    assert "pytest:" in text
    assert "Backend Pytest Shard ${{ matrix.shard_id }}" in text
    assert "name: Run Unit Tests" in text
    assert "if: always() && (github.event_name != 'pull_request' || needs.classify-changes.outputs.backend_ci == 'true')" in text
    assert "Require Successful Backend Pytest Shards" in text
    assert "needs.pytest.result != 'success'" in text
    assert f'COVERAGE_VERSION: "{coverage_version}"' in text
    assert 'uvx --from "coverage[toml]==${{ env.COVERAGE_VERSION }}" coverage combine reports/coverage/shards' in text
    assert "backend-coverage-${{ matrix.shard_id }}" in text
    assert "pattern: backend-coverage-*" in text
    assert "merge-multiple: true" in text
    assert "coverage combine reports/coverage/shards" in text


def test_workflows_pin_uv_bootstrap_version() -> None:
    workflow_paths = (
        REPO_ROOT / ".github/workflows/ci.yml",
        REPO_ROOT / ".github/workflows/sbom.yml",
        REPO_ROOT / ".github/workflows/security-scan.yml",
        REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml",
        REPO_ROOT / ".github/workflows/performance-gate.yml",
    )

    for workflow_path in workflow_paths:
        text = workflow_path.read_text(encoding="utf-8")
        assert 'version: "latest"' not in text
        assert "${{ env.UV_VERSION }}" in text


def test_ci_and_release_related_workflows_use_local_setup_composite_actions() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )
    browser_text = (
        REPO_ROOT / ".github/workflows/dashboard-browser-mainline.yml"
    ).read_text(encoding="utf-8")
    enterprise_text = (
        REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml"
    ).read_text(encoding="utf-8")
    release_text = (
        REPO_ROOT / ".github/workflows/release-unified-platform.yml"
    ).read_text(encoding="utf-8")
    deploy_text = (
        REPO_ROOT / ".github/workflows/deploy-unified-platform.yml"
    ).read_text(encoding="utf-8")

    assert "uses: ./.github/actions/setup-python-uv" in ci_text
    assert "uses: ./.github/actions/setup-dashboard" in ci_text
    assert "uses: ./.github/actions/setup-python-uv" in security_text
    assert "uses: ./.github/actions/setup-python-uv" in browser_text
    assert "uses: ./.github/actions/setup-dashboard" in browser_text
    assert "uses: ./.github/actions/setup-python-uv" in enterprise_text
    assert "uses: ./.github/actions/setup-python-uv" in release_text
    assert "uses: ./.github/actions/setup-dashboard" in release_text
    assert "uses: ./.github/actions/setup-python-uv" in deploy_text
    assert "uses: ./.github/actions/setup-dashboard" in deploy_text


def test_workflow_triggers_cover_local_composite_actions_and_container_entrypoints() -> (
    None
):
    security_text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )
    browser_text = (
        REPO_ROOT / ".github/workflows/dashboard-browser-mainline.yml"
    ).read_text(encoding="utf-8")
    enterprise_text = (
        REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml"
    ).read_text(encoding="utf-8")

    assert '.github/actions/**' in security_text
    assert '.github/actions/**' in browser_text
    assert '.github/actions/**' in enterprise_text
    assert '.github/actions/*/action.yml' in security_text
    assert '.dockerignore' in security_text
    assert 'scripts/docker-entrypoint.sh' in security_text


def test_long_running_workflows_define_timeouts_and_serialized_release_concurrency() -> (
    None
):
    timeout_workflow_paths = (
        REPO_ROOT / ".github/workflows/ci.yml",
        REPO_ROOT / ".github/workflows/security-scan.yml",
        REPO_ROOT / ".github/workflows/dashboard-browser-mainline.yml",
        REPO_ROOT / ".github/workflows/enterprise-tdd-mainline.yml",
        REPO_ROOT / ".github/workflows/sbom.yml",
        REPO_ROOT / ".github/workflows/publish-artifact-registry-images.yml",
        REPO_ROOT / ".github/workflows/release-unified-platform.yml",
        REPO_ROOT / ".github/workflows/deploy-unified-platform.yml",
    )

    for workflow_path in timeout_workflow_paths:
        text = workflow_path.read_text(encoding="utf-8")
        assert "timeout-minutes:" in text

    for workflow_path in (
        REPO_ROOT / ".github/workflows/publish-artifact-registry-images.yml",
        REPO_ROOT / ".github/workflows/release-unified-platform.yml",
        REPO_ROOT / ".github/workflows/deploy-unified-platform.yml",
    ):
        text = workflow_path.read_text(encoding="utf-8")
        assert "concurrency:" in text
        assert "cancel-in-progress: false" in text


def test_performance_gate_supports_reuse_and_ci_automation() -> None:
    perf_text = (REPO_ROOT / ".github/workflows/performance-gate.yml").read_text(
        encoding="utf-8"
    )
    perf_mainline_text = (
        REPO_ROOT / ".github/workflows/performance-mainline.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_call:" in perf_text
    assert "start_local_api:" in perf_text
    assert "bootstrap_tenant:" in perf_text
    assert "scripts/bootstrap_performance_tenant.py" in perf_text
    assert "scripts/load_test_api.py" in perf_text
    assert "scripts/run_local_managed_worker.py" in perf_text
    assert "uvicorn app.main:app" in perf_text
    assert "Launch Managed Worker Loop" in perf_text
    assert 'ENVIRONMENT: "staging"' in perf_text
    assert 'TESTING: "false"' in perf_text
    assert 'API_URL: "https://api.staging.valdrics.example"' in perf_text
    assert 'FRONTEND_URL: "https://dashboard.staging.valdrics.example"' in perf_text
    assert 'PLATFORM_RUNTIME_PROFILE: "gcp"' in perf_text
    assert 'OBSERVABILITY_BACKEND: "gcp"' in perf_text
    assert 'PUBLIC_API_RATE_LIMITING_BACKEND: "cloudflare"' in perf_text
    assert 'RATELIMIT_ENABLED: "false"' in perf_text
    assert 'GCP_PROJECT_ID: "valdrics-staging"' in perf_text
    assert 'GCP_CLOUD_TASKS_QUEUE: "valdrics-default"' in perf_text
    assert "postgres:16.13-alpine" in perf_text
    assert 'SENTRY_DSN: "https://example@sentry.io/1"' not in perf_text
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:4317"' not in perf_text
    assert "otel/opentelemetry-collector:0.147.0" not in perf_text
    assert "Wait for OTEL Collector" not in perf_text
    assert (
        "uv run python scripts/validate_runtime_env.py --environment staging"
        in perf_text
    )
    assert "uv run alembic upgrade head" in perf_text
    assert (
        "uv run celery -A app.shared.core.celery_app:celery_app worker -l info"
        not in perf_text
    )
    assert "performance-health-gate:" in perf_mainline_text
    assert "performance-dashboard-gate:" in perf_mainline_text
    assert "performance-ops-gate:" in perf_mainline_text
    assert "uses: ./.github/workflows/performance-gate.yml" in perf_mainline_text
    assert "performance.owner@valdrics.local" not in perf_text
    assert "performance.owner@valdrics.ai" in perf_text
    assert "performance.owner@valdrics.ai" in (
        REPO_ROOT / "scripts/bootstrap_performance_tenant.py"
    ).read_text(encoding="utf-8")
    assert 'p95_target: "1.25"' in perf_mainline_text
    assert "bootstrap_tier:" in perf_text
    assert '--tier "${{ inputs.bootstrap_tier }}"' in perf_text
    assert "tail -n 1 | tr -d" in perf_text
    assert 'bootstrap_tier: "pro"' in perf_mainline_text
    assert "name: perf-gate-evidence-${{ inputs.profile }}" in perf_text
    assert "name: perf-gate-api-log-${{ inputs.profile }}" in perf_text
    assert "name: perf-gate-worker-log-${{ inputs.profile }}" in perf_text


def test_carbon_footprint_workflow_runs_codecarbon_benchmark() -> None:
    text = (REPO_ROOT / ".github/workflows/carbon-footprint.yml").read_text(
        encoding="utf-8"
    )

    assert "CodeCarbon" in text
    assert "EmissionsTracker" in text
    assert "carbon-emissions-report" in text
    assert "pytest" in text
    assert "timeout-minutes: 20" in text
    assert "pytest', 'tests/', '-x'" not in text
    assert "tests/unit/modules/reporting/test_carbon_scheduler_comprehensive.py" in text


def test_dashboard_mainline_browser_workflow_keeps_authenticated_playwright_matrix() -> (
    None
):
    text = (
        REPO_ROOT / ".github/workflows/dashboard-browser-mainline.yml"
    ).read_text(encoding="utf-8")

    assert "Authenticated Shell" in text
    assert "E2E Critical Paths" in text
    assert "e2e/a11y.spec.ts" in text
    assert "e2e/performance.spec.ts" in text
    assert 'PRIVATE_API_ORIGIN: "http://127.0.0.1:8000"' in text
    assert 'PLAYWRIGHT_BACKEND_URL: "http://127.0.0.1:8000"' in text
    assert "pnpm exec playwright test" in text


def test_ci_workflow_reuses_dashboard_preview_build_for_public_browser_gates() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    playwright_text = (REPO_ROOT / "dashboard/playwright.config.ts").read_text(
        encoding="utf-8"
    )

    assert "Package Dashboard Preview Build" in ci_text
    assert "Upload Dashboard Preview Build" in ci_text
    assert "name: dashboard-preview-output" in ci_text
    assert "Download Dashboard Preview Build" in ci_text
    assert "Restore Dashboard Preview Build" in ci_text
    assert 'PLAYWRIGHT_USE_PREBUILT_PREVIEW: "1"' in ci_text
    assert "const usePrebuiltPreview = process.env.PLAYWRIGHT_USE_PREBUILT_PREVIEW === '1';" in playwright_text
    assert "? `${frontendEnv} pnpm run preview`" in playwright_text


def test_strict_runtime_preflight_is_hermetic_and_explicit_in_workflows() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    dr_text = (REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml").read_text(
        encoding="utf-8"
    )

    assert 'API_URL: "https://api.validation.example.com"' in ci_text
    assert 'FRONTEND_URL: "https://app.validation.example.com"' in ci_text
    assert 'OBSERVABILITY_BACKEND: "gcp"' in ci_text
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"' not in ci_text
    assert 'SENTRY_DSN: "https://example@sentry.io/1"' not in ci_text
    assert 'API_URL: "https://api.staging.valdrics.example"' in dr_text
    assert 'FRONTEND_URL: "https://dashboard.staging.valdrics.example"' in dr_text
    assert 'PLATFORM_RUNTIME_PROFILE: "gcp"' in dr_text
    assert 'OBSERVABILITY_BACKEND: "gcp"' in dr_text
    assert 'PUBLIC_API_RATE_LIMITING_BACKEND: "cloudflare"' in dr_text
    assert 'RATELIMIT_ENABLED: "false"' in dr_text
    assert 'GCP_PROJECT_ID: "valdrics-staging"' in dr_text
    assert 'SENTRY_DSN: "https://example@sentry.io/1"' not in dr_text
    assert 'OTEL_EXPORTER_OTLP_ENDPOINT: "http://127.0.0.1:4317"' not in dr_text
    assert "otel/opentelemetry-collector:0.147.0" not in dr_text
    assert "Wait for OTEL Collector" not in dr_text
    assert (
        "uv run python scripts/validate_runtime_env.py --environment staging" in dr_text
    )
    assert "Launch Managed Worker Loop" in dr_text
    assert "scripts/run_local_managed_worker.py" in dr_text
    assert (
        "uv run celery -A app.shared.core.celery_app:celery_app worker -l info"
        not in dr_text
    )


def test_local_postgres_service_workflows_disable_db_ssl() -> None:
    perf_text = (REPO_ROOT / ".github/workflows/performance-gate.yml").read_text(
        encoding="utf-8"
    )
    dr_text = (REPO_ROOT / ".github/workflows/disaster-recovery-drill.yml").read_text(
        encoding="utf-8"
    )

    assert (
        'DATABASE_URL: "postgresql+asyncpg://postgres:local-dev-change-me@127.0.0.1:5432/valdrics"'
        in perf_text
    )
    assert 'DB_SSL_MODE: "disable"' in perf_text
    assert (
        'DATABASE_URL: "postgresql+asyncpg://postgres:local-dev-change-me@127.0.0.1:5432/valdrics"'
        in dr_text
    )
    assert 'DB_SSL_MODE: "disable"' in dr_text


def test_security_scan_workflow_fails_on_high_or_critical_infra_and_container_findings() -> (
    None
):
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )

    assert "Security Audits" not in ci_text
    assert "--severity CRITICAL,HIGH" in security_text
    assert "--exit-code 1" in security_text
    assert "--minimum-severity HIGH" in security_text


def test_security_scan_uses_hermetic_compose_env_for_dast() -> None:
    text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )

    assert "classify-changes:" in text
    assert "Terraform Validate / Lint / Security" in text
    assert "hashicorp/setup-terraform@" in text
    assert "terraform -chdir=terraform init -backend=false" in text
    assert "terraform -chdir=terraform validate -no-color" in text
    assert "cache-from: type=gha,scope=backend-image" in text
    assert "cache-from: type=gha,scope=dashboard-image" in text
    assert "needs.classify-changes.outputs.backend_container == 'true'" in text
    assert "needs.classify-changes.outputs.dashboard_container == 'true'" in text
    assert "needs: [security-scan, container-scan]" in text
    assert "github.event_name != 'pull_request'" in text
    assert (
        "scripts/generate_local_compose_env.py --output-path .env.compose.dev" in text
    )
    assert "cp .env.example .env" not in text
    assert '"PUBLIC_API_RATE_LIMITING_BACKEND": "cloudflare"' in text
    assert '"RATELIMIT_ENABLED": "false"' in text
    assert (
        "docker compose --env-file .env.compose.dev up -d --build postgres api dashboard"
        in text
    )
    assert "docker compose --env-file .env.compose.dev down -v" in text
    assert "docker compose up -d --build postgres redis api dashboard" not in text


def test_security_scan_workflow_pins_tflint_setup_version() -> None:
    security_text = (REPO_ROOT / ".github/workflows/security-scan.yml").read_text(
        encoding="utf-8"
    )

    assert "tflint_version: latest" not in security_text
    assert "tflint_version: v0.61.0" in security_text


def test_cla_workflow_uses_in_repo_python_implementation() -> None:
    text = (REPO_ROOT / ".github/workflows/cla.yml").read_text(encoding="utf-8")

    assert "contributor-assistant/github-action" not in text
    assert "python3 scripts/cla_assistant.py" in text
    assert "CLA_SIGNATURES_BRANCH: cla-signatures" in text
    assert "statuses: write" in text
    assert "issues: write" in text


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


def test_local_composite_actions_use_immutable_action_shas() -> None:
    uses_pattern = re.compile(
        r"uses:\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)@([^\s#]+)"
    )

    for action_path in PINNED_COMPOSITE_ACTION_PATHS:
        text = action_path.read_text(encoding="utf-8")
        for _, ref in uses_pattern.findall(text):
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (
                f"{action_path.name} uses non-immutable action ref {ref!r}"
            )
