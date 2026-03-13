# All Changes Categorization (2026-03-13)

Snapshot scope captured from the local worktree on 2026-03-13.

## Summary

- Total changed paths: `111`
- Change shape: CI/runtime hardening, AWS/public onboarding and identity controls, FinOps/reporting correctness, and shared adapter/http/zombie resilience.
- Merge intent: consolidate the current local batch into one PR with issue-backed tracking and closeout.

## Track AS: CI, Runtime, and Managed Deployment Hardening

Purpose: split backend CI execution into quality plus sharded pytest coverage, add AWS trust-principal runtime inputs, and keep managed deployment generation and exception-governance evidence aligned.

Paths:

- `.env.example`
- `.github/workflows/ci.yml`
- `app/shared/core/config.py`
- `docs/ops/evidence/exception_governance_baseline.json`
- `docs/runbooks/production_env_checklist.md`
- `pyproject.toml`
- `scripts/generate_local_dev_env.py`
- `scripts/generate_managed_deployment_artifacts.py`
- `scripts/generate_managed_runtime_env.py`
- `scripts/verify_exception_governance.py`
- `tests/unit/core/test_config_validation.py`
- `tests/unit/ops/test_generate_local_dev_env.py`
- `tests/unit/ops/test_generate_managed_deployment_artifacts.py`
- `tests/unit/ops/test_generate_managed_runtime_env.py`
- `tests/unit/ops/test_validate_runtime_env.py`
- `tests/unit/ops/test_verify_managed_deployment_bundle.py`
- `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py`

Notes:

- Renames the main backend CI job to a pure quality gate and adds four backend pytest shards with coverage artifact combine.
- Adds `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN` as an operator-managed runtime contract across example envs and managed artifact generation.
- Converts `CLOUDFORMATION_TEMPLATE_URL` into an optional override instead of a fixed raw GitHub dependency.
- Normalizes exception-governance paths to repository-relative output so the baseline is portable across worktrees and CI runners.

## Track AT: Governance Public Surface, Cloud Onboarding, and Identity Operations

Purpose: harden public AWS onboarding assets, enforce tier boundaries for AWS organization discovery, and make identity settings/audit behavior fail safely.

Paths:

- `app/modules/governance/api/v1/public.py`
- `app/modules/governance/api/v1/settings/connections_helpers.py`
- `app/modules/governance/api/v1/settings/connections_setup_aws_discovery.py`
- `app/modules/governance/api/v1/settings/connections_setup_snippets.py`
- `app/modules/governance/api/v1/settings/identity_diagnostics_ops.py`
- `app/modules/governance/api/v1/settings/identity_settings_ops.py`
- `app/shared/connections/aws.py`
- `cloudformation/valdrics-role.yaml`
- `dashboard/src/routes/connections/ConnectionsPublicCloudCards.svelte`
- `dashboard/src/routes/connections/connections-page.svelte.test.ts`
- `dashboard/src/routes/onboarding/OnboardingPageViewBody.svelte`
- `dashboard/src/routes/onboarding/OnboardingPageViewContent.svelte`
- `dashboard/src/routes/onboarding/OnboardingStepSelectProviderSection.svelte`
- `dashboard/src/routes/onboarding/onboarding-page.svelte.test.ts`
- `dashboard/src/routes/onboarding/onboardingSetupActions.ts`
- `dashboard/src/routes/onboarding/onboardingTierAccess.ts`
- `dashboard/src/routes/onboarding/onboardingUiActions.ts`
- `tests/unit/connections/test_cloud_connections_deep.py`
- `tests/unit/core/test_cloud_connection.py`
- `tests/unit/core/test_cloud_connection_audit.py`
- `tests/unit/governance/api/test_public.py`
- `tests/unit/governance/settings/conftest.py`
- `tests/unit/governance/settings/test_connections.py`
- `tests/unit/governance/settings/test_connections_branches.py`
- `tests/unit/governance/settings/test_governance_deep.py`
- `tests/unit/governance/settings/test_identity_settings_direct_branches.py`
- `tests/unit/governance/settings/test_notifications_core_slack.py`
- `tests/unit/governance/settings/test_profile_settings.py`
- `tests/unit/governance/settings/test_settings_branch_paths.py`
- `tests/unit/governance/test_connections_api_aws.py`
- `tests/unit/governance/test_connections_api_azure.py`
- `tests/unit/governance/test_connections_api_discovered.py`
- `tests/unit/governance/test_connections_api_gcp.py`
- `tests/unit/governance/test_onboard_audit.py`

Notes:

- Serves the release-owned AWS CloudFormation template from the public API with cache headers and ETag support.
- Injects the configured AWS trust principal into the template at runtime and derives launch links from `API_URL` when no override is set.
- Gates AWS Organizations discovery and management-account workflows to `Growth` and above.
- Converts identity audit persistence failures into explicit HTTP 500 responses with rollback, rather than leaking raw storage exceptions.
- Aligns onboarding UI/test coverage with the revised cloud-card and provider-selection behavior.

## Track AU: Reporting, FinOps Scheduler, and Datetime Correctness

Purpose: normalize naive timestamps across reporting and scheduler paths, stabilize savings query coercion, and extend FinOps maintenance coverage.

Paths:

- `app/modules/governance/domain/jobs/metrics.py`
- `app/modules/governance/domain/scheduler/cohorts.py`
- `app/modules/reporting/api/v1/costs_metrics.py`
- `app/modules/reporting/api/v1/savings.py`
- `app/modules/reporting/domain/carbon_scheduler.py`
- `app/modules/reporting/domain/tenant_growth_funnel.py`
- `app/shared/core/currency.py`
- `app/shared/core/datetime_ops.py`
- `tests/unit/api/v1/test_costs_metrics_branch_paths.py`
- `tests/unit/governance/domain/jobs/handlers/test_billing_handler.py`
- `tests/unit/governance/jobs/test_finops.py`
- `tests/unit/governance/jobs/test_finops_handler_branches.py`
- `tests/unit/governance/scheduler/test_cohorts.py`
- `tests/unit/governance/test_job_metrics_branches.py`
- `tests/unit/modules/reporting/test_carbon_scheduler_comprehensive.py`
- `tests/unit/reporting/test_attribution_engine.py`
- `tests/unit/services/billing/test_currency_service.py`
- `tests/unit/tasks/test_daily_finops_scan.py`
- `tests/unit/tasks/test_scheduler_tasks_branch_paths_2.py`
- `tests/unit/tasks/test_scheduler_tasks_comprehensive.py`
- `tests/unit/tasks/test_scheduler_tasks_reliability.py`

Notes:

- Introduces shared UTC datetime normalization helpers for scheduler and reporting math.
- Hardens savings query parameter coercion so `Query(...)` defaults and mixed test doubles do not leak into runtime logic.
- Makes stale carbon profile reads degrade safely for scheduler reads while keeping strict validation available.
- Updates tenant growth funnel stage handling and snapshot normalization for stable replay/export behavior.
- Extends maintenance sweep coverage to include supported AWS pricing sync and cloud resource pricing refresh paths.

## Track AV: Shared Adapter, HTTP, Session, and Zombie Resilience

Purpose: make shared adapters and HTTP/session plumbing more defensive under mocked or multi-loop runtimes, and align zombie/remediation tests with the current multi-provider service contract.

Paths:

- `app/modules/governance/domain/security/audit_log.py`
- `app/modules/optimization/adapters/azure/plugins/rightsizing.py`
- `app/shared/adapters/hybrid.py`
- `app/shared/adapters/license.py`
- `app/shared/adapters/platform.py`
- `app/shared/core/http.py`
- `app/shared/db/session.py`
- `tests/conftest.py`
- `tests/core/test_http_branch_paths.py`
- `tests/unit/llm/test_factory_audit.py`
- `tests/unit/llm/test_factory_exhaustive.py`
- `tests/unit/modules/optimization/adapters/aws/plugins/test_storage_branch_paths.py`
- `tests/unit/modules/optimization/adapters/aws/test_aws_next_gen.py`
- `tests/unit/modules/optimization/adapters/azure/test_azure_rightsizing.py`
- `tests/unit/modules/optimization/adapters/gcp/test_gcp_next_gen.py`
- `tests/unit/modules/optimization/adapters/gcp/test_gcp_rightsizing.py`
- `tests/unit/modules/optimization/adapters/gcp/test_gcp_search_network_branch_paths.py`
- `tests/unit/modules/optimization/adapters/saas/test_saas_api_branch_paths.py`
- `tests/unit/modules/optimization/adapters/saas/test_saas_next_gen.py`
- `tests/unit/modules/test_module_init_lazy_loading.py`
- `tests/unit/optimization/test_remediation_service_audit.py`
- `tests/unit/optimization/test_saas_action_wiring.py`
- `tests/unit/optimization/test_zombie_service_audit.py`
- `tests/unit/services/adapters/cloud_plus_test_helpers.py`
- `tests/unit/services/adapters/conftest.py`
- `tests/unit/services/adapters/license_verification_stream_test_helpers.py`
- `tests/unit/services/adapters/platform_additional_test_helpers.py`
- `tests/unit/services/adapters/test_cloud_plus_adapters_license_adapter.py`
- `tests/unit/services/adapters/test_cloud_plus_adapters_license_resilience.py`
- `tests/unit/services/adapters/test_cloud_plus_adapters_platform_hybrid.py`
- `tests/unit/services/adapters/test_cloud_plus_adapters_saas_resilience.py`
- `tests/unit/services/adapters/test_hybrid_additional_branches.py`
- `tests/unit/services/adapters/test_license_verification_stream_http_and_manual.py`
- `tests/unit/services/adapters/test_platform_additional_branches_http.py`
- `tests/unit/services/jobs/test_job_handlers.py`
- `tests/unit/services/notifications/test_email_service.py`
- `tests/unit/services/zombies/saas_provider/test_saas_detector.py`
- `tests/unit/services/zombies/test_zombie_service.py`
- `tests/unit/services/zombies/test_zombie_service_cloud_plus.py`
- `tests/unit/shared/adapters/test_saas_adapter_branch_paths.py`
- `tests/unit/zombies/test_tier_gating_phase8.py`

Notes:

- Makes audit-log flushes compatible with async mocks and tightens audit-log immutability SQL detection.
- Adds loop-aware HTTP client reinitialization and explicit outbound TLS verification resolution.
- Broadens adapter secret resolution to accept `SecretStr`-like test doubles with `get_secret_value()`.
- Hardens Azure rightsizing exception-base resolution when the SDK is partially mocked.
- Resets shared HTTP clients between tests and updates zombie/adapters coverage to the current multi-provider connection model.

## Recommended Merge Notes

- Keep as one PR because the changes are already coupled through shared runtime contracts, CI structure, and cross-module test fixtures.
- Close the four tracking issues directly from the PR body.
- Follow up separately on any GitHub Actions failures surfaced after merge rather than splitting this local batch by file type alone.
