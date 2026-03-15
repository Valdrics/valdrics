# All Changes Categorization (2026-03-16)

Snapshot:
- Captured at: `2026-03-16T00:00:00Z`
- Base commit: `ea9d07e29648580d5344bc67c6c393839f8eff1d`
- Pending paths: `204`
- Branch at snapshot: `chore/all-changes-categorization-2026-03-16`

## Track BI: Governance, Identity, Connection, and Audit Surface Hardening
Scope:
- Consolidate governance API/admin/settings changes across audit, health, SCIM, onboarding, and public marketing surfaces.
- Align shared cloud/identity connection flows with stronger auth coverage and admin health UI updates.
- Carry the matching governance, audit, OIDC, and connection regression suites in the same review track.

Paths:
- `app/modules/governance/api/v1/admin.py`
- `app/modules/governance/api/v1/audit_access.py`
- `app/modules/governance/api/v1/audit_evidence.py`
- `app/modules/governance/api/v1/audit_evidence_carbon.py`
- `app/modules/governance/api/v1/audit_evidence_common.py`
- `app/modules/governance/api/v1/audit_evidence_reliability.py`
- `app/modules/governance/api/v1/audit_partitioning.py`
- `app/modules/governance/api/v1/health_dashboard.py`
- `app/modules/governance/api/v1/health_dashboard_ops.py`
- `app/modules/governance/api/v1/jobs.py`
- `app/modules/governance/api/v1/landing_funnel_health_ops.py`
- `app/modules/governance/api/v1/public_marketing.py`
- `app/modules/governance/api/v1/scim.py`
- `app/modules/governance/api/v1/scim_group_route_ops.py`
- `app/modules/governance/api/v1/scim_user_route_ops.py`
- `app/modules/governance/api/v1/settings/account.py`
- `app/modules/governance/api/v1/settings/activeops.py`
- `app/modules/governance/api/v1/settings/carbon.py`
- `app/modules/governance/api/v1/settings/connections_azure_gcp.py`
- `app/modules/governance/api/v1/settings/connections_cloud_plus.py`
- `app/modules/governance/api/v1/settings/connections_setup_aws_discovery.py`
- `app/modules/governance/api/v1/settings/identity.py`
- `app/modules/governance/api/v1/settings/identity_settings_ops.py`
- `app/modules/governance/api/v1/settings/llm.py`
- `app/modules/governance/api/v1/settings/notification_diagnostics_ops.py`
- `app/modules/governance/api/v1/settings/notification_settings_ops.py`
- `app/modules/governance/api/v1/settings/notifications.py`
- `app/modules/governance/api/v1/settings/onboard.py`
- `app/modules/governance/api/v1/settings/safety.py`
- `app/modules/governance/domain/jobs/metrics.py`
- `app/shared/connections/aws.py`
- `app/shared/connections/azure.py`
- `app/shared/connections/gcp.py`
- `app/shared/connections/oidc.py`
- `app/shared/connections/organizations.py`
- `app/shared/core/auth.py`
- `app/shared/core/connection_queries.py`
- `dashboard/src/routes/admin/health/+page.svelte`
- `tests/security/test_oidc_security.py`
- `tests/unit/api/test_audit.py`
- `tests/unit/api/v1/test_audit_compliance_pack.py`
- `tests/unit/api/v1/test_audit_evidence_capture_list_branches.py`
- `tests/unit/api/v1/test_audit_high_impact_branches.py`
- `tests/unit/api/v1/test_health_dashboard_branches.py`
- `tests/unit/api/v1/test_health_dashboard_endpoints.py`
- `tests/unit/api/v1/test_identity_smoke_evidence_endpoints.py`
- `tests/unit/api/v1/test_ingestion_persistence_evidence_endpoints.py`
- `tests/unit/api/v1/test_ingestion_soak_evidence_endpoints.py`
- `tests/unit/api/v1/test_performance_evidence_endpoints.py`
- `tests/unit/api/v1/test_sso_federation_validation_evidence_endpoints.py`
- `tests/unit/api/v1/test_tenant_isolation_evidence_endpoints.py`
- `tests/unit/connections/test_cloud_connections_deep.py`
- `tests/unit/connections/test_oidc_deep.py`
- `tests/unit/connections/test_organizations_deep.py`
- `tests/unit/governance/api/test_public.py`
- `tests/unit/governance/settings/test_account_settings.py`
- `tests/unit/governance/settings/test_activeops.py`
- `tests/unit/governance/settings/test_activeops_deep.py`
- `tests/unit/governance/settings/test_carbon.py`
- `tests/unit/governance/settings/test_connections_branches.py`
- `tests/unit/governance/settings/test_governance_deep.py`
- `tests/unit/governance/settings/test_identity_settings.py`
- `tests/unit/governance/settings/test_identity_settings_additional_branches.py`
- `tests/unit/governance/settings/test_identity_settings_high_impact_branches.py`
- `tests/unit/governance/settings/test_llm_settings.py`
- `tests/unit/governance/settings/test_notification_entitlement_ops.py`
- `tests/unit/governance/settings/test_notifications_acceptance_evidence.py`
- `tests/unit/governance/settings/test_notifications_core_slack.py`
- `tests/unit/governance/settings/test_notifications_diagnostics_workflow.py`
- `tests/unit/governance/settings/test_notifications_teams_jira.py`
- `tests/unit/governance/settings/test_onboard.py`
- `tests/unit/governance/settings/test_safety.py`
- `tests/unit/governance/settings/test_settings_branch_paths.py`
- `tests/unit/governance/test_admin_api.py`
- `tests/unit/governance/test_connections_api_aws.py`
- `tests/unit/governance/test_connections_api_azure.py`
- `tests/unit/governance/test_connections_api_cloud_plus.py`
- `tests/unit/governance/test_connections_api_discovered.py`
- `tests/unit/governance/test_connections_api_gcp.py`
- `tests/unit/governance/test_job_metrics_branches.py`
- `tests/unit/governance/test_jobs_api.py`
- `tests/unit/governance/test_scim_context_and_race_branches.py`
- `tests/unit/governance/test_scim_direct_endpoint_branches.py`
- `tests/unit/services/connections/test_organizations.py`
- `tests/unit/api/test_audit_data_erasure_integration.py`
- `tests/unit/core/test_connection_queries.py`
- `tests/unit/governance/test_admin_campaign_metrics_branch_paths.py`

Notes:
- This track holds the tenant/admin-facing governance surface, including connection and SCIM path hardening.
- Governance domain compliance-pack internals are split into Track BK to keep preventive-control logic grouped with enforcement work.

## Track BJ: Billing, Reporting, Pricing, and Commercial Analytics
Scope:
- Batch the pricing, billing, paystack, carbon, reconciliation, and commercial reporting changes together.
- Keep reporting API/domain work aligned with dashboard billing changes and commercial KPI/regression coverage.
- Include pricing-model and carbon/discovered-account model updates in the same financial review lane.

Paths:
- `app/models/carbon_settings.py`
- `app/models/discovered_account.py`
- `app/models/pricing.py`
- `app/modules/billing/api/v1/billing.py`
- `app/modules/billing/api/v1/billing_models.py`
- `app/modules/billing/api/v1/billing_ops.py`
- `app/modules/billing/domain/billing/paystack_service_impl.py`
- `app/modules/billing/domain/billing/paystack_webhook_impl.py`
- `app/modules/reporting/api/v1/attribution.py`
- `app/modules/reporting/api/v1/carbon.py`
- `app/modules/reporting/api/v1/costs.py`
- `app/modules/reporting/api/v1/costs_acceptance_payload.py`
- `app/modules/reporting/api/v1/costs_http_routes_extended.py`
- `app/modules/reporting/api/v1/costs_metrics.py`
- `app/modules/reporting/api/v1/costs_reconciliation_routes.py`
- `app/modules/reporting/api/v1/costs_unit_economics_routes.py`
- `app/modules/reporting/api/v1/currency.py`
- `app/modules/reporting/api/v1/leaderboards.py`
- `app/modules/reporting/api/v1/savings.py`
- `app/modules/reporting/api/v1/usage.py`
- `app/modules/reporting/domain/aggregator_governance_ops.py`
- `app/modules/reporting/domain/attribution_engine.py`
- `app/modules/reporting/domain/attribution_engine_rule_crud.py`
- `app/modules/reporting/domain/commercial_reports.py`
- `app/modules/reporting/domain/leadership_kpis.py`
- `app/modules/reporting/domain/persistence_retention_ops.py`
- `app/modules/reporting/domain/reconciliation.py`
- `app/modules/reporting/domain/reconciliation_exports.py`
- `app/modules/reporting/domain/reconciliation_invoice.py`
- `app/modules/reporting/domain/savings_proof_render_ops.py`
- `app/modules/reporting/domain/service.py`
- `app/modules/reporting/domain/tenant_growth_funnel.py`
- `dashboard/src/routes/billing/billingPage.test.ts`
- `dashboard/src/routes/billing/billingPage.ts`
- `tests/governance/test_cost_governance.py`
- `tests/unit/api/v1/test_attribution_branch_paths.py`
- `tests/unit/api/v1/test_billing.py`
- `tests/unit/api/v1/test_carbon.py`
- `tests/unit/api/v1/test_carbon_factor_endpoints.py`
- `tests/unit/api/v1/test_costs_acceptance_payload_alerts.py`
- `tests/unit/api/v1/test_costs_acceptance_payload_core.py`
- `tests/unit/api/v1/test_costs_acceptance_payload_endpoints.py`
- `tests/unit/api/v1/test_costs_endpoints_acceptance_base.py`
- `tests/unit/api/v1/test_costs_endpoints_acceptance_export.py`
- `tests/unit/api/v1/test_costs_endpoints_acceptance_ledger.py`
- `tests/unit/api/v1/test_costs_endpoints_ingest.py`
- `tests/unit/api/v1/test_costs_metrics_branch_paths.py`
- `tests/unit/api/v1/test_currency_endpoints.py`
- `tests/unit/api/v1/test_leaderboards_endpoints.py`
- `tests/unit/api/v1/test_reconciliation_endpoints.py`
- `tests/unit/api/v1/test_savings_branch_paths.py`
- `tests/unit/api/v1/test_unit_economics_endpoints.py`
- `tests/unit/api/v1/test_usage_branch_paths.py`
- `tests/unit/modules/reporting/test_commercial_reports_domain.py`
- `tests/unit/modules/reporting/test_leadership_kpis_domain.py`
- `tests/unit/modules/reporting/test_reporting_service_connections.py`
- `tests/unit/modules/reporting/test_reporting_service_ingestion.py`
- `tests/unit/modules/reporting/test_tenant_growth_funnel.py`
- `tests/unit/reporting/test_aggregator.py`
- `tests/unit/reporting/test_attribution_engine.py`
- `tests/unit/reporting/test_billing_api.py`
- `tests/unit/reporting/test_reconciliation_branch_paths.py`
- `tests/unit/reporting/test_savings_proof_service_edges.py`
- `tests/unit/services/billing/test_paystack_billing.py`
- `tests/unit/services/billing/test_paystack_billing_branches.py`
- `tests/unit/services/carbon/test_budget_alerts.py`
- `tests/unit/reporting/test_billing_usage_ops_regressions.py`

Notes:
- This track is the main revenue/reporting surface and carries the largest concentration of API and domain churn in the batch.

## Track BK: Enforcement, Compliance Controls, Optimization, and Scheduler Flows
Scope:
- Keep enforcement policy/budget/export work grouped with compliance-pack state and optimization execution changes.
- Pair LLM orchestration updates with scheduler/license task changes that affect operational control-plane behavior.
- Carry the related enforcement, optimization, LLM, and task regression suites together.

Paths:
- `app/modules/enforcement/api/v1/policy_budget_credit.py`
- `app/modules/enforcement/domain/export_bundle_ops.py`
- `app/modules/enforcement/domain/policy_contract_ops.py`
- `app/modules/enforcement/domain/service.py`
- `app/modules/governance/domain/security/compliance_pack_bundle.py`
- `app/modules/governance/domain/security/compliance_pack_bundle_state.py`
- `app/modules/governance/domain/security/compliance_pack_evidence.py`
- `app/modules/optimization/domain/remediation_execute_helpers.py`
- `app/modules/optimization/domain/strategy_service.py`
- `app/shared/llm/analyzer.py`
- `app/shared/llm/llm_client.py`
- `app/shared/llm/zombie_analyzer.py`
- `app/tasks/license_tasks.py`
- `app/tasks/scheduler_audit_log_retention_ops.py`
- `app/tasks/scheduler_remediation_ops.py`
- `app/tasks/scheduler_sweep_ops.py`
- `app/tasks/scheduler_tasks.py`
- `tests/governance/test_cleanup_logic.py`
- `tests/unit/enforcement/enforcement_api_cases_part02.py`
- `tests/unit/enforcement/enforcement_api_cases_part05.py`
- `tests/unit/enforcement/test_enforcement_endpoint_wrapper_coverage.py`
- `tests/unit/llm/test_analyzer.py`
- `tests/unit/llm/test_zombie_analyzer_exhaustive.py`
- `tests/unit/optimization/test_optimization_service.py`
- `tests/unit/supply_chain/test_generate_enforcement_stress_evidence.py`
- `tests/unit/tasks/test_enforcement_scheduler_tasks.py`
- `tests/unit/tasks/test_license_tasks.py`
- `tests/unit/tasks/test_scheduler_audit_log_retention_ops.py`
- `tests/unit/tasks/test_scheduler_tasks_branch_paths_2.py`
- `tests/unit/enforcement/test_export_bundle_ops_regressions.py`
- `tests/unit/optimization/test_remediation_execute_helpers.py`

Notes:
- This track is the control-plane and background-execution slice of the batch.

## Track BL: Operational Verification Scripts, Security Checks, and Schema Migrations
Scope:
- Consolidate local verification script hardening, JWT/RLS/tenant-isolation checks, and acceptance bootstrap coverage.
- Keep schema migrations in the same operational track as the verification scripts that exercise their contracts.
- Carry the ops/script regression suites together so release-gate verification stays coherent.

Paths:
- `scripts/check_frontend_api_contracts.py`
- `scripts/security/check_local_env_for_live_secrets.py`
- `scripts/verify_api_auth_coverage.py`
- `scripts/verify_jwt_bcp_checklist.py`
- `scripts/verify_rls.py`
- `scripts/verify_rls_detailed.py`
- `scripts/verify_tenant_isolation.py`
- `tests/unit/ops/test_check_local_env_for_live_secrets.py`
- `tests/unit/ops/test_legacy_script_hardening.py`
- `tests/unit/ops/test_partition_and_rls_scripts.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/ops/test_verify_api_auth_coverage.py`
- `tests/unit/ops/test_webhook_job_reliability_drill_pack.py`
- `tests/unit/scripts/test_check_frontend_api_contracts.py`
- `tests/unit/supply_chain/test_verify_jwt_bcp_checklist.py`
- `migrations/versions/t6u7v8w9x0y_add_carbon_alert_status_column.py`
- `migrations/versions/u7v8w9x0y1z_add_subscription_billing_cycle.py`
- `tests/unit/ops/test_capture_acceptance_bootstrap.py`
- `tests/unit/ops/test_verify_tenant_isolation.py`

Notes:
- This track is intentionally script-heavy and operational rather than product-surface oriented.

## Batching Decision
Decision:
- Merge as one consolidated PR.

Reasoning:
- The changed surfaces are broad but still tied to one cross-cutting batch of governance, reporting, control-plane, and ops verification work.
- Splitting this snapshot would mostly create artificial PR overhead because the tests and runtime contracts cross these subsystems heavily.
- The track split is kept for review/accountability, while delivery remains one batched merge request.
