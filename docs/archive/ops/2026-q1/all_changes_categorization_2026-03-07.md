# All Changes Categorization Register (2026-03-07)

Generated from live working tree using `git status --porcelain -uall`.

## Summary

- Total changed paths: 218
- Modified paths: 119
- New/untracked paths: 87
- Deleted paths: 12

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track AI | Backend services, enforcement, optimization, and shared runtime | 49 | #239 |
| Track AJ | Test coverage, quality gates, and automation | 138 | #240 |
| Track AK | Deployment, infrastructure, and environment configuration | 24 | #241 |
| Track AL | Documentation, guides, and legacy artifact cleanup | 7 | #242 |

## Full Inventory By Track

### Track AI - Backend services, enforcement, optimization, and shared runtime (49)

| Status | Path |
|---|---|
| `M` | `app/main.py` |
| `M` | `app/modules/billing/api/v1/billing.py` |
| `M` | `app/modules/billing/api/v1/billing_ops.py` |
| `M` | `app/modules/billing/domain/billing/paystack_service_impl.py` |
| `M` | `app/modules/enforcement/domain/approval_flow_ops.py` |
| `M` | `app/modules/enforcement/domain/computed_context_ops.py` |
| `M` | `app/modules/enforcement/domain/gate_evaluation_ops.py` |
| `M` | `app/modules/enforcement/domain/service.py` |
| `M` | `app/modules/enforcement/domain/service_gate_lock_ops.py` |
| `M` | `app/modules/enforcement/domain/service_private_ops.py` |
| `M` | `app/modules/governance/api/v1/audit_evidence_common.py` |
| `M` | `app/modules/governance/api/v1/jobs.py` |
| `M` | `app/modules/governance/api/v1/settings/notification_settings_ops.py` |
| `M` | `app/modules/governance/domain/security/compliance_pack_bundle_exports.py` |
| `M` | `app/modules/notifications/domain/jira.py` |
| `M` | `app/modules/notifications/domain/slack.py` |
| `M` | `app/modules/notifications/domain/teams.py` |
| `M` | `app/modules/notifications/domain/workflows.py` |
| `M` | `app/modules/optimization/adapters/common/__init__.py` |
| `M` | `app/modules/optimization/adapters/gcp/plugins/ai.py` |
| `M` | `app/modules/optimization/adapters/gcp/plugins/rightsizing.py` |
| `M` | `app/modules/optimization/adapters/gcp/plugins/search.py` |
| `M` | `app/modules/optimization/domain/actions/base.py` |
| `M` | `app/modules/optimization/domain/ports.py` |
| `M` | `app/modules/optimization/domain/remediation_execute.py` |
| `M` | `app/modules/optimization/domain/strategy_service.py` |
| `M` | `app/modules/reporting/api/v1/costs_metrics.py` |
| `M` | `app/shared/adapters/hybrid_native_mixin.py` |
| `M` | `app/shared/adapters/platform.py` |
| `M` | `app/shared/analysis/azure_usage_analyzer.py` |
| `M` | `app/shared/connections/aws.py` |
| `M` | `app/shared/connections/organizations.py` |
| `M` | `app/shared/core/circuit_breaker.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/currency.py` |
| `M` | `app/shared/core/health.py` |
| `M` | `app/shared/core/pricing.py` |
| `M` | `app/shared/core/runtime_dependencies.py` |
| `M` | `app/shared/llm/budget_execution.py` |
| `M` | `app/shared/llm/budget_execution_runtime_ops.py` |
| `M` | `app/shared/testing/sqlite_artifact_cleanup.py` |
| `M` | `app/tasks/scheduler_sweep_ops.py` |
| `M` | `app/tasks/scheduler_tasks.py` |
| `??` | `app/modules/enforcement/domain/gate_evaluation_payload_ops.py` |
| `??` | `app/modules/enforcement/domain/service_approval_ops.py` |
| `??` | `app/modules/enforcement/domain/service_private_credit_token_ops.py` |
| `??` | `app/shared/analysis/azure_usage_analyzer_helpers.py` |
| `??` | `app/shared/core/health_check_ops.py` |
| `??` | `app/tasks/scheduler_background_job_retention_ops.py` |

### Track AJ - Test coverage, quality gates, and automation (138)

| Status | Path |
|---|---|
| `M` | `.github/workflows/ci.yml` |
| `M` | `.github/workflows/performance-gate.yml` |
| `M` | `.github/workflows/sbom.yml` |
| `M` | `.github/workflows/security-scan.yml` |
| `M` | `scripts/audit_report_controls_registry.py` |
| `M` | `scripts/capture_acceptance_evidence.py` |
| `M` | `scripts/collect_finance_telemetry_snapshot.py` |
| `M` | `scripts/enterprise_tdd_gate_commands.py` |
| `M` | `scripts/generate_finance_committee_packet_assumptions.py` |
| `M` | `scripts/generate_valdrics_disposition_register.py` |
| `M` | `scripts/load_test_api.py` |
| `M` | `scripts/pkg_fin_policy_decisions_core.py` |
| `M` | `scripts/smoke_test_scim_idp.py` |
| `M` | `scripts/verify_audit_report_resolved.py` |
| `M` | `scripts/verify_dependency_locking.py` |
| `M` | `scripts/verify_python_module_size_budget.py` |
| `D` | `tests/api/test_endpoints.py` |
| `M` | `tests/conftest.py` |
| `M` | `tests/integration/billing/test_paystack_flows.py` |
| `M` | `tests/integration/test_edge_cases.py` |
| `D` | `tests/unit/analysis/test_azure_usage_analyzer.py` |
| `M` | `tests/unit/api/v1/test_billing.py` |
| `D` | `tests/unit/api/v1/test_costs_endpoints.py` |
| `M` | `tests/unit/api/v1/test_costs_helper_branches.py` |
| `M` | `tests/unit/connections/test_cloud_connections_deep.py` |
| `M` | `tests/unit/connections/test_organizations_deep.py` |
| `M` | `tests/unit/core/test_config_branch_paths.py` |
| `M` | `tests/unit/core/test_config_validation.py` |
| `M` | `tests/unit/core/test_env_contract_templates.py` |
| `M` | `tests/unit/core/test_health_deep.py` |
| `M` | `tests/unit/core/test_main.py` |
| `M` | `tests/unit/core/test_pricing_deep.py` |
| `M` | `tests/unit/core/test_runtime_dependencies.py` |
| `M` | `tests/unit/db/test_session_exhaustive.py` |
| `M` | `tests/unit/governance/settings/test_notifications.py` |
| `D` | `tests/unit/governance/test_connections_api.py` |
| `M` | `tests/unit/governance/test_jobs_api.py` |
| `M` | `tests/unit/modules/optimization/adapters/test_common_runtime.py` |
| `M` | `tests/unit/notifications/domain/test_teams_service.py` |
| `M` | `tests/unit/notifications/test_jira_service.py` |
| `M` | `tests/unit/notifications/test_workflow_dispatchers.py` |
| `M` | `tests/unit/ops/test_verify_audit_report_resolved.py` |
| `M` | `tests/unit/ops/test_verify_dependency_locking.py` |
| `M` | `tests/unit/ops/test_verify_python_module_size_budget.py` |
| `M` | `tests/unit/ops/test_verify_repo_root_hygiene.py` |
| `M` | `tests/unit/optimization/test_connector_action_base_branch_paths.py` |
| `M` | `tests/unit/reporting/test_billing_api.py` |
| `D` | `tests/unit/services/adapters/test_cloud_plus_adapters.py` |
| `D` | `tests/unit/services/adapters/test_license_verification_stream_branches.py` |
| `D` | `tests/unit/services/adapters/test_platform_additional_branches.py` |
| `M` | `tests/unit/services/notifications/test_slack_integration.py` |
| `M` | `tests/unit/services/zombies/test_base.py` |
| `D` | `tests/unit/shared/adapters/test_aws_cur.py` |
| `D` | `tests/unit/shared/connections/test_discovery_service.py` |
| `M` | `tests/unit/shared/llm/test_budget_execution_branches.py` |
| `D` | `tests/unit/shared/llm/test_budget_fair_use_branches.py` |
| `M` | `tests/unit/shared/testing/test_sqlite_artifact_cleanup.py` |
| `M` | `tests/unit/supply_chain/test_enterprise_tdd_gate_runner.py` |
| `M` | `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py` |
| `D` | `tests/unit/tasks/test_scheduler_tasks.py` |
| `M` | `tests/unit/test_main_coverage.py` |
| `??` | `scripts/capture_acceptance_bootstrap.py` |
| `??` | `scripts/capture_acceptance_runner.py` |
| `??` | `scripts/finance_committee_packet_assumptions_engine.py` |
| `??` | `scripts/finance_telemetry_snapshot_queries.py` |
| `??` | `scripts/generate_local_dev_env.py` |
| `??` | `scripts/load_test_api_cli.py` |
| `??` | `scripts/load_test_api_reporting.py` |
| `??` | `scripts/pkg_fin_policy_decisions_parsers.py` |
| `??` | `scripts/smoke_test_scim_helpers.py` |
| `??` | `scripts/verify_container_image_pinning.py` |
| `??` | `tests/api/test_endpoints_health_cors.py` |
| `??` | `tests/api/test_endpoints_security_auth.py` |
| `??` | `tests/api/test_endpoints_validation_jobs.py` |
| `??` | `tests/api/test_endpoints_zombies_approval_execution.py` |
| `??` | `tests/api/test_endpoints_zombies_plan_policy.py` |
| `??` | `tests/api/test_endpoints_zombies_scan_requests.py` |
| `??` | `tests/unit/analysis/test_azure_usage_analyzer_core.py` |
| `??` | `tests/unit/analysis/test_azure_usage_analyzer_production_quality.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_acceptance_base.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_acceptance_export.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_acceptance_ledger.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_core.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_ingest.py` |
| `??` | `tests/unit/api/v1/test_costs_endpoints_sla.py` |
| `??` | `tests/unit/core/test_load_test_api_reporting.py` |
| `??` | `tests/unit/core/test_smoke_test_scim_helpers.py` |
| `??` | `tests/unit/governance/connections_api_fixtures.py` |
| `??` | `tests/unit/governance/test_connections_api_aws.py` |
| `??` | `tests/unit/governance/test_connections_api_azure.py` |
| `??` | `tests/unit/governance/test_connections_api_cloud_plus.py` |
| `??` | `tests/unit/governance/test_connections_api_discovered.py` |
| `??` | `tests/unit/governance/test_connections_api_gcp.py` |
| `??` | `tests/unit/ops/test_capture_acceptance_evidence_script.py` |
| `??` | `tests/unit/ops/test_capture_acceptance_runner.py` |
| `??` | `tests/unit/ops/test_generate_finance_committee_packet_assumptions.py` |
| `??` | `tests/unit/ops/test_generate_local_dev_env.py` |
| `??` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `??` | `tests/unit/ops/test_secret_rotation_contracts.py` |
| `??` | `tests/unit/ops/test_terraform_ha_contracts.py` |
| `??` | `tests/unit/ops/test_verify_container_image_pinning.py` |
| `??` | `tests/unit/services/adapters/cloud_plus_test_helpers.py` |
| `??` | `tests/unit/services/adapters/license_verification_stream_test_helpers.py` |
| `??` | `tests/unit/services/adapters/platform_additional_test_helpers.py` |
| `??` | `tests/unit/services/adapters/test_cloud_plus_adapters_license_adapter.py` |
| `??` | `tests/unit/services/adapters/test_cloud_plus_adapters_license_resilience.py` |
| `??` | `tests/unit/services/adapters/test_cloud_plus_adapters_platform_hybrid.py` |
| `??` | `tests/unit/services/adapters/test_cloud_plus_adapters_saas_adapter.py` |
| `??` | `tests/unit/services/adapters/test_cloud_plus_adapters_saas_resilience.py` |
| `??` | `tests/unit/services/adapters/test_license_verification_stream_activity.py` |
| `??` | `tests/unit/services/adapters/test_license_verification_stream_costs.py` |
| `??` | `tests/unit/services/adapters/test_license_verification_stream_http_and_manual.py` |
| `??` | `tests/unit/services/adapters/test_license_verification_stream_verify.py` |
| `??` | `tests/unit/services/adapters/test_platform_additional_branches_core.py` |
| `??` | `tests/unit/services/adapters/test_platform_additional_branches_http.py` |
| `??` | `tests/unit/services/adapters/test_platform_additional_branches_resolution.py` |
| `??` | `tests/unit/services/adapters/test_platform_additional_branches_vendor_specific.py` |
| `??` | `tests/unit/shared/adapters/aws_cur_test_helpers.py` |
| `??` | `tests/unit/shared/adapters/test_aws_cur_connection_setup.py` |
| `??` | `tests/unit/shared/adapters/test_aws_cur_listing_ingest.py` |
| `??` | `tests/unit/shared/adapters/test_aws_cur_parquet_parsing.py` |
| `??` | `tests/unit/shared/adapters/test_aws_cur_resource_projection.py` |
| `??` | `tests/unit/shared/connections/discovery_service_test_helpers.py` |
| `??` | `tests/unit/shared/connections/test_discovery_service_idp_scans.py` |
| `??` | `tests/unit/shared/connections/test_discovery_service_request_json.py` |
| `??` | `tests/unit/shared/connections/test_discovery_service_signal_inference.py` |
| `??` | `tests/unit/shared/connections/test_discovery_service_stage_a.py` |
| `??` | `tests/unit/shared/llm/budget_fair_use_test_helpers.py` |
| `??` | `tests/unit/shared/llm/conftest.py` |
| `??` | `tests/unit/shared/llm/test_budget_fair_use_core.py` |
| `??` | `tests/unit/shared/llm/test_budget_fair_use_daily_limit_edges.py` |
| `??` | `tests/unit/shared/llm/test_budget_fair_use_daily_limits.py` |
| `??` | `tests/unit/shared/llm/test_budget_fair_use_global_abuse.py` |
| `??` | `tests/unit/shared/llm/test_budget_fair_use_guard_signals.py` |
| `??` | `tests/unit/tasks/test_scheduler_background_job_retention_ops.py` |
| `??` | `tests/unit/tasks/test_scheduler_tasks_cohorts.py` |
| `??` | `tests/unit/tasks/test_scheduler_tasks_reliability.py` |
| `??` | `tests/unit/tasks/test_scheduler_tasks_sweeps.py` |

### Track AK - Deployment, infrastructure, and environment configuration (24)

| Status | Path |
|---|---|
| `M` | `.env.example` |
| `M` | `.gitignore` |
| `M` | `Dockerfile` |
| `M` | `Makefile` |
| `M` | `docker-compose.prod.yml` |
| `M` | `docker-compose.yml` |
| `M` | `helm/valdrics/templates/deployment.yaml` |
| `M` | `helm/valdrics/templates/worker-deployment.yaml` |
| `M` | `helm/valdrics/values.yaml` |
| `M` | `koyeb.yaml` |
| `M` | `prod.env.template` |
| `M` | `prometheus/prometheus.yml` |
| `M` | `pyproject.toml` |
| `M` | `terraform/main.tf` |
| `M` | `terraform/modules/cache/main.tf` |
| `M` | `terraform/modules/db/main.tf` |
| `M` | `terraform/modules/network/main.tf` |
| `M` | `terraform/outputs.tf` |
| `M` | `terraform/variables.tf` |
| `M` | `uv.lock` |
| `??` | `helm/valdrics/templates/external-secrets.yaml` |
| `??` | `terraform/modules/secrets_rotation/main.tf` |
| `??` | `terraform/modules/secrets_rotation/outputs.tf` |
| `??` | `terraform/modules/secrets_rotation/variables.tf` |

### Track AL - Documentation, guides, and legacy artifact cleanup (7)

| Status | Path |
|---|---|
| `M` | `DEPLOYMENT.md` |
| `M` | `README.md` |
| `D` | `dashboard/LandingHero_legacy.svelte` |
| `M` | `docs/DEPLOYMENT.md` |
| `M` | `docs/architecture/ADR-0003-core-circuit-breaker-state-scope.md` |
| `M` | `docs/ops/deep_debt_remediation_2026-03-06.md` |
| `M` | `docs/ops/parallel_backend_hardening_2026-03-05.md` |
