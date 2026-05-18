from __future__ import annotations

import json
import re
from pathlib import Path

from app.shared.orchestration.contracts import ManagedWorkItem
from app.shared.orchestration.schedules import cloud_scheduler_jobs_payload


REPO_ROOT = Path(__file__).resolve().parents[3]


def _terraform_resource_block(source: str, resource_type: str, name: str) -> str:
    pattern = rf'resource "{re.escape(resource_type)}" "{re.escape(name)}" \{{(?P<body>.*?)\n\}}'
    match = re.search(pattern, source, flags=re.DOTALL)
    assert match is not None, f"{resource_type}.{name} resource missing"
    return match.group("body")


def _terraform_variable_block(source: str, name: str) -> str:
    pattern = rf'variable "{re.escape(name)}" \{{(?P<body>.*?)\n\}}'
    match = re.search(pattern, source, flags=re.DOTALL)
    assert match is not None, f"{name} variable missing"
    return match.group("body")


def test_dashboard_csp_is_cloudflare_compatible_without_unsafe_inline() -> None:
    config = (REPO_ROOT / "dashboard/svelte.config.js").read_text(encoding="utf-8")

    assert "mode: 'nonce'" in config
    assert "https://static.cloudflareinsights.com" in config
    assert "https://cloudflareinsights.com" in config
    assert "unsafe-inline" not in config


def test_terraform_root_targets_gcp_cloudflare_and_supabase() -> None:
    providers = (REPO_ROOT / "terraform/providers.tf").read_text(encoding="utf-8")
    main = (REPO_ROOT / "terraform/main.tf").read_text(encoding="utf-8")
    variables = (REPO_ROOT / "terraform/variables.tf").read_text(encoding="utf-8")

    assert 'source  = "hashicorp/google"' in providers
    assert 'source  = "hashicorp/tls"' in providers
    assert 'source  = "cloudflare/cloudflare"' in providers
    assert 'source  = "supabase/supabase"' in providers

    artifact_registry_main = (
        REPO_ROOT / "terraform/artifact-registry/main.tf"
    ).read_text(encoding="utf-8")

    assert 'resource "google_artifact_registry_repository" "runtime"' in (
        artifact_registry_main
    )
    assert 'resource "google_cloud_run_v2_service" "api"' in main
    assert (
        'resource "google_artifact_registry_repository_iam_member" '
        '"cloud_run_service_agent_image_reader"' in main
    )
    assert "serverless-robot-prod.iam.gserviceaccount.com" in main
    assert "roles/artifactregistry.reader" in main
    assert "manage_artifact_registry_reader_iam" in main
    assert "count = local.manage_artifact_registry_reader_iam ? 1 : 0" in main
    assert 'ingress              = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"' in main
    assert "invoker_iam_disabled = true" in main
    assert "custom_audiences     = [var.api_url]" in main
    assert 'resource "google_compute_global_address" "api_edge"' in main
    assert 'resource "google_compute_region_network_endpoint_group" "api"' in main
    assert 'resource "google_compute_security_policy" "api_edge_origin"' in main
    assert 'resource "google_compute_backend_service" "api"' in main
    assert (
        "security_policy       = google_compute_security_policy.api_edge_origin.id"
        in main
    )
    assert "Deny direct origin access that bypasses Cloudflare." in main
    assert 'resource "google_compute_target_https_proxy" "api"' in main
    assert 'resource "cloudflare_dns_record" "api"' in main
    assert 'resource "cloudflare_bot_management" "api_zone"' in main
    assert "fight_mode = false" in main
    assert 'resource "cloudflare_ruleset" "api_rate_limit"' in main
    assert "valdrics-public-api-rate-limit" in main
    assert 'characteristics     = ["cf.colo.id", "ip.src"]' in main
    assert 'expression  = "(http.host eq \\"${local.api_hostname}\\")"' in main
    assert 'resource "cloudflare_dns_record" "dashboard"' in main
    assert 'type    = "CNAME"' in main
    assert "cloudflare_pages_project.dashboard.subdomain" in main
    assert 'resource "cloudflare_pages_domain" "dashboard"' in main
    assert "deployment_configs = {" in main
    assert "env_vars            = local.cloudflare_pages_env_vars" in main
    assert "PRIVATE_API_ORIGIN" in main
    assert "PUBLIC_API_URL" in main
    assert "PUBLIC_SUPABASE_URL" in main
    assert "PUBLIC_SUPABASE_ANON_KEY" in main
    assert 'compatibility_flags = ["nodejs_compat"]' in main
    assert 'resource "cloudflare_ruleset" "api_internal_block"' in main
    assert "valdrics-health-probe-skip" in main
    assert "valdrics-internal-api-block" in main
    assert "ignore_changes = [" in main
    assert "Health probes must bypass Cloudflare browser challenges." in main
    assert 'action      = "skip"' in main
    assert 'http.request.uri.path eq \\"/health/live\\"' in main
    assert '"http_request_sbfm"' in main
    assert '"securityLevel"' in main
    assert '"bic"' in main
    assert 'resource "google_cloud_run_v2_job" "batch"' in main
    assert 'resource "google_cloud_tasks_queue" "runtime"' in main
    assert 'resource "google_cloud_scheduler_job" "managed"' in main
    assert 'resource "google_secret_manager_secret" "runtime"' in main
    assert 'resource "cloudflare_pages_project" "dashboard"' in main
    assert 'resource "supabase_project" "platform"' in main
    assert 'resource "supabase_settings" "platform"' in main
    assert 'resource "google_cloud_run_service_iam_policy" "api_public_invoker"' not in main
    assert '"allUsers"' not in main

    assert 'variable "runtime_plain_env"' in variables
    assert 'variable "runtime_secret_env"' in variables
    assert 'variable "cloudflare_zone_id"' in variables
    assert 'variable "cloudflare_origin_allow_cidrs"' in variables
    assert 'variable "cloudflare_pages_project_name"' in variables
    assert 'variable "supabase_project_ref"' in variables
    assert 'variable "supabase_project_name"' in variables
    assert (
        'managed_scheduler_jobs              = jsondecode(file("${path.module}/managed_scheduler_jobs.json"))'
        in main
    )

    compute_resources = {
        "api_edge": "google_compute_global_address",
        "api_origin": "google_compute_ssl_certificate",
        "api": "google_compute_region_network_endpoint_group",
        "api_edge_origin": "google_compute_security_policy",
        "api_http_redirect": "google_compute_url_map",
    }
    for resource_name, resource_type in compute_resources.items():
        block = _terraform_resource_block(main, resource_type, resource_name)
        assert "depends_on" in block
        assert "google_project_service.required" in block

    rate_limit_period = _terraform_variable_block(
        variables, "cloudflare_api_rate_limit_period_seconds"
    )
    rate_limit_threshold = _terraform_variable_block(
        variables, "cloudflare_api_rate_limit_requests_per_period"
    )
    rate_limit_mitigation = _terraform_variable_block(
        variables, "cloudflare_api_rate_limit_mitigation_timeout_seconds"
    )
    assert "default     = 10" in rate_limit_period
    assert "default     = 50" in rate_limit_threshold
    assert "default     = 10" in rate_limit_mitigation
    assert (
        "cloudflare_api_rate_limit_mitigation_timeout_seconds must be 10"
        in rate_limit_mitigation
    )


def test_terraform_root_excludes_archived_aws_failover_and_secret_rotation_inputs() -> (
    None
):
    providers = (REPO_ROOT / "terraform/providers.tf").read_text(encoding="utf-8")
    main = (REPO_ROOT / "terraform/main.tf").read_text(encoding="utf-8")
    variables = (REPO_ROOT / "terraform/variables.tf").read_text(encoding="utf-8")

    assert 'source  = "hashicorp/aws"' not in providers
    assert 'module "secrets_rotation"' not in main
    assert 'module "secondary_network"' not in main
    assert 'module "secondary_eks"' not in main
    assert 'module "secondary_db"' not in main
    assert 'module "secondary_cache"' not in main
    assert 'variable "enable_secret_rotation"' not in variables
    assert 'variable "secret_rotation_lambda_arn"' not in variables
    assert 'variable "enable_multi_region_failover"' not in variables
    assert 'variable "secondary_aws_region"' not in variables


def test_terraform_managed_scheduler_contract_matches_backend_contract() -> None:
    main = (REPO_ROOT / "terraform/main.tf").read_text(encoding="utf-8")
    scheduler_contract = json.loads(
        (REPO_ROOT / "terraform/managed_scheduler_jobs.json").read_text(
            encoding="utf-8"
        )
    )
    allowed_work_items = {item.value for item in ManagedWorkItem}

    assert scheduler_contract == cloud_scheduler_jobs_payload()
    assert set(item["work_item"] for item in scheduler_contract.values()).issubset(
        allowed_work_items
    )
    assert "stuck_job_detector" in scheduler_contract
    assert (
        scheduler_contract["stuck_job_detector"]["work_item"]
        == ManagedWorkItem.BACKGROUND_JOB_STUCK_DETECTION.value
    )
    assert "cohort_high_value_scan" in scheduler_contract
    assert "cohort_active_scan" in scheduler_contract
    assert "cohort_dormant_scan" in scheduler_contract
    assert '"--work-item", "background_jobs.process", "--payload", "{}"' in main
    assert "audience              = var.api_url" in main


def test_publish_artifact_registry_workflow_uses_wif_and_digest_promotion() -> None:
    workflow = (
        REPO_ROOT / ".github/workflows/publish-artifact-registry-images.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_call:" in workflow
    assert "api_promotion_ref:" in workflow
    assert "google-github-actions/auth@" in workflow
    assert "google-github-actions/setup-gcloud@" in workflow
    assert "gcloud auth configure-docker" in workflow
    assert (
        "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f # v3"
        in workflow
    )
    assert (
        "docker/build-push-action@263435318d21b8e681c14492fe198d362a7d2c83 # v6.18.0"
        in workflow
    )
    assert "artifact-registry-release.json" in workflow
    assert "artifact-registry-release.env" in workflow
    assert "immutable_artifact_registry_promotion" in workflow
    assert "concurrency:" in workflow
    assert "group: publish-artifact-registry-images-${{ inputs.release_tag }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "github.workflow" not in workflow
    assert "timeout-minutes: 35" in workflow


def test_deploy_unified_platform_workflow_applies_terraform_and_cloudflare_pages() -> (
    None
):
    workflow = (REPO_ROOT / ".github/workflows/deploy-unified-platform.yml").read_text(
        encoding="utf-8"
    )
    upload_section = workflow.split(
        "Upload non-secret deployment evidence bundle", maxsplit=1
    )[1].split("Terraform apply unified platform", maxsplit=1)[0]

    assert "workflow_call:" in workflow
    assert "release_tag:" in workflow
    assert "batch_promotion_ref:" in workflow
    assert "concurrency:" in workflow
    assert (
        "group: deploy-unified-platform-${{ inputs.environment }}-${{ inputs.release_tag }}"
        in workflow
    )
    assert "cancel-in-progress: false" in workflow
    assert "github.workflow" not in workflow
    assert "timeout-minutes: 90" in workflow
    assert "hashicorp/setup-terraform@" in workflow
    assert "b9cd54a3c349d3f38e8881555d616ced269862dd # v3" in workflow
    assert "uses: ./.github/actions/setup-python-uv" in workflow
    assert "uses: ./.github/actions/setup-dashboard" in workflow
    assert "Cache Playwright Browsers" in workflow
    assert "pnpm exec playwright install --with-deps chromium" in workflow
    assert "RUNTIME_PLAIN_ENV_JSON" in workflow
    assert "RUNTIME_SECRET_ENV_JSON" in workflow
    assert "generate_managed_runtime_env.py" in workflow
    assert "generate_managed_migration_env.py" in workflow
    assert "generate_managed_deployment_artifacts.py" in workflow
    assert "verify_managed_deployment_bundle.py" in workflow
    assert "render_managed_deployment_handoff.py" in workflow
    assert "refresh_codebase_audit_report.py" in workflow
    assert "verify_managed_release_readiness.py" in workflow
    assert "actions/upload-artifact@" in workflow
    assert ".runtime/${{ inputs.environment }}.report.json" in upload_section
    assert ".runtime/${{ inputs.environment }}.migrate.report.json" in upload_section
    assert "deployment.report.json" in upload_section
    assert "operator-handoff.md" in upload_section
    assert "secret-manager-runtime-secrets.json" not in upload_section
    assert "terraform.runtime.auto.tfvars.json" not in upload_section
    assert "terraform -chdir=terraform init" in workflow
    assert "terraform.runtime.auto.tfvars.json" in workflow
    assert "-var-file=" in workflow
    assert "terraform -chdir=terraform import" in workflow
    assert "supabase_project.platform" in workflow
    assert "scripts/sync_cloudflare_rulesets.py" in workflow
    assert "--import-terraform-state" in workflow
    assert "CLOUDFLARE_API_TOKEN" in workflow
    assert "steps.managed_bundle.outputs.supabase_project_ref" in workflow
    assert "apply_infrastructure" in workflow
    assert "if: ${{ inputs.apply_infrastructure }}" in workflow
    assert "terraform -chdir=terraform apply -auto-approve tfplan" in workflow
    assert "if: ${{ ! inputs.apply_infrastructure }}" in workflow
    assert "Update Cloud Run app images" in workflow
    assert "gcloud run services update" in workflow
    assert "gcloud run jobs update" in workflow
    assert "GCP_CLOUD_RUN_SERVICE_NAME" in workflow
    assert "GCP_CLOUD_RUN_BATCH_JOB_NAME" in workflow
    assert 'source "${{ steps.managed_bundle.outputs.migration_env_path }}"' in workflow
    assert "uv run alembic upgrade head" in workflow
    assert "wrangler pages deploy" in workflow
    assert 'Path("dashboard/wrangler.toml").write_text' in workflow
    assert "[vars]" in workflow
    assert "PRIVATE_API_ORIGIN" in workflow
    assert "PUBLIC_SUPABASE_ANON_KEY" in workflow
    assert "/health/live" in workflow
    assert "api_health_url=" in workflow
    assert "for attempt in $(seq 1 18)" in workflow
    assert "--dump-header" in workflow
    assert '--write-out "%{http_code}"' in workflow
    assert "status=${http_status:-curl_error}" in workflow
    assert "GCP_WORKLOAD_IDENTITY_PROVIDER" in workflow
    assert "TF_VAR_runtime_plain_env" not in workflow
    assert "TF_VAR_runtime_secret_env" not in workflow
    assert "vars.PUBLIC_API_URL" not in workflow
    assert "vars.PUBLIC_SUPABASE_URL" not in workflow
    assert "secrets.DATABASE_URL" not in workflow
    assert "secrets.SUPABASE_ANON_KEY" not in workflow


def test_release_unified_platform_workflow_promotes_one_digest_through_environments() -> (
    None
):
    workflow = (REPO_ROOT / ".github/workflows/release-unified-platform.yml").read_text(
        encoding="utf-8"
    )
    cloudflare_preflight = (
        REPO_ROOT / "scripts/preflight_cloudflare_bot_management.py"
    ).read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "group: release-unified-platform-${{ inputs.release_tag }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "github.workflow" not in workflow
    assert "timeout-minutes: 20" in workflow
    assert "timeout-minutes: 35" in workflow
    assert "Bootstrap Terraform State" in workflow
    assert "Bootstrap Production Terraform State" in workflow
    assert "Bootstrap Artifact Registry" in workflow
    assert "Grant production Artifact Registry readers" in workflow
    assert "PRODUCTION_GCP_PROJECT_ID" in workflow
    assert "PRODUCTION_GCP_PROJECT_NUMBER" in workflow
    assert "PRODUCTION_GCP_DEPLOYER_SERVICE_ACCOUNT" in workflow
    assert "serviceAccount:${production_deployer_service_account}" in workflow
    assert "serverless-robot-prod.iam.gserviceaccount.com" in workflow
    assert "gcloud artifacts repositories add-iam-policy-binding" in workflow
    assert "terraform/state-backend" in workflow
    assert "terraform/artifact-registry" in workflow
    assert "uses: ./.github/actions/setup-python-uv" in workflow
    assert "uses: ./.github/actions/setup-dashboard" in workflow
    assert workflow.count("Cache Playwright Browsers") >= 2
    assert workflow.count("pnpm exec playwright install --with-deps chromium") >= 2
    assert "Publish Backend Artifact" in workflow
    assert "Preflight Staging Managed Platform" in workflow
    assert "Preflight Production Managed Platform" in workflow
    assert "preflight_managed_platform.py" in workflow
    assert "preflight_gcp_managed_platform.py" in workflow
    assert "preflight_cloudflare_bot_management.py" in workflow
    assert "preflight_runtime_env_contract.py" in workflow
    assert "Validate GCP deployer Terraform IAM permissions" in workflow
    assert "Validate managed runtime contract" in workflow
    assert "Enforce Cloudflare Bot Fight Mode disabled" in workflow
    assert "/bot_management" in cloudflare_preflight
    assert "Zone > Bot Management > Edit" in cloudflare_preflight
    assert '"fight_mode": False' in cloudflare_preflight
    assert "gcloud services enable" in workflow
    assert "cloudresourcemanager.googleapis.com" in workflow
    assert "preflight-staging-managed-platform" in workflow
    assert "./.github/workflows/publish-artifact-registry-images.yml" in workflow
    assert workflow.index("bootstrap-artifact-registry:") < workflow.index("publish:")
    staging_preflight = workflow.split(
        "preflight-staging-managed-platform:", maxsplit=1
    )[1].split("preflight-production-managed-platform:", maxsplit=1)[0]
    production_preflight = workflow.split(
        "preflight-production-managed-platform:", maxsplit=1
    )[1].split("publish:", maxsplit=1)[0]
    bootstrap_artifact_registry = workflow.split(
        "bootstrap-artifact-registry:", maxsplit=1
    )[1].split("preflight-staging-managed-platform:", maxsplit=1)[0]
    assert "preflight_runtime_env_contract.py" in staging_preflight
    assert "--environment staging" in staging_preflight
    assert "preflight_runtime_env_contract.py" in production_preflight
    assert "--environment production" in production_preflight
    assert "preflight_runtime_env_contract.py" not in bootstrap_artifact_registry
    assert "- preflight-staging-managed-platform" in bootstrap_artifact_registry
    assert "./.github/workflows/deploy-unified-platform.yml" in workflow
    assert "ARTIFACT_REGISTRY_PROJECT_ID" in workflow
    assert "deploy-staging:" in workflow
    assert "deploy-production:" in workflow
    assert "bootstrap-production-terraform-state:" in workflow
    assert "inputs.release_tag" in workflow
    assert "needs.publish.outputs.api_promotion_ref" in workflow
    assert "needs.publish.outputs.batch_promotion_ref" in workflow
    assert "--non-secret-deployment-bundle" in workflow
    assert "render-release-blocker-summary:" in workflow
    assert "Render Managed Release Blocker Summary" in workflow
    assert "render_managed_release_blocker_summary.py" in workflow
    assert "managed-release-blocker-summary-${{ inputs.release_tag }}" in workflow
    assert "promote_production" in workflow


def test_release_beta_app_workflow_skips_terraform_for_fast_product_releases() -> None:
    workflow = (REPO_ROOT / ".github/workflows/release-beta-app.yml").read_text(
        encoding="utf-8"
    )

    assert "name: Release Beta App" in workflow
    assert "release-beta-app-${{ inputs.environment }}-${{ inputs.release_tag }}" in (
        workflow
    )
    assert "Validate Beta App Release Contract" in workflow
    assert "Preflight Public API Route" in workflow
    assert "/health/live" in workflow
    assert "cf-mitigated: challenge" in workflow
    assert "Bot Fight Mode" in workflow
    assert "./.github/workflows/publish-artifact-registry-images.yml" in workflow
    assert "./.github/workflows/deploy-unified-platform.yml" in workflow
    assert "Deploy App Without Terraform" in workflow
    assert "apply_infrastructure: false" in workflow
    assert "terraform -chdir=terraform" not in workflow


def test_dashboard_package_exposes_wrangler_for_pages_deploy() -> None:
    package = json.loads(
        (REPO_ROOT / "dashboard/package.json").read_text(encoding="utf-8")
    )

    assert "wrangler" in package["devDependencies"]


def test_unified_platform_release_runbook_matches_new_control_plane() -> None:
    runbook = (REPO_ROOT / "docs/runbooks/unified_platform_release.md").read_text(
        encoding="utf-8"
    )

    assert "release-unified-platform.yml" in runbook
    assert "Google Cloud Run" in runbook
    assert "Cloud Tasks" in runbook
    assert "Cloud Scheduler" in runbook
    assert "Cloud Run Jobs" in runbook
    assert "Artifact Registry" in runbook
    assert "Cloudflare Pages" in runbook
    assert "Supabase" in runbook
    assert "roles/iam.workloadIdentityUser" in runbook
    assert "attribute.repository/Arvenqor/valdrics" in runbook
    assert "same `api_promotion_ref`" in runbook
    assert "same `batch_promotion_ref`" in runbook
    assert "verify_managed_release_readiness.py" in runbook
    assert "managed deployment bundle" in runbook
    assert "managed-release-blocker-summary-<release-tag>" in runbook
    assert "make render-managed-release-blockers NON_SECRET_BUNDLE=true" in runbook
