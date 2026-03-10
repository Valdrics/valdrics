"""Static configuration for the enterprise TDD gate."""

from __future__ import annotations

ENTERPRISE_GATE_TEST_TARGETS: tuple[str, ...] = (
    "tests/unit/enforcement",
    "tests/unit/api/v1/test_attribution_branch_paths.py",
    "tests/unit/api/v1/test_carbon.py",
    "tests/unit/api/v1/test_costs_metrics_branch_paths.py",
    "tests/unit/api/v1/test_currency_endpoints.py",
    "tests/unit/api/v1/test_leaderboards_endpoints.py",
    "tests/unit/api/v1/test_leadership_kpis_branch_paths.py",
    "tests/unit/api/v1/test_leadership_kpis_branch_paths_2.py",
    "tests/unit/api/v1/test_leadership_kpis_endpoints.py",
    "tests/unit/api/v1/test_savings_branch_paths.py",
    "tests/unit/api/v1/test_usage_endpoints.py",
    "tests/unit/api/v1/test_usage_branch_paths.py",
    "tests/unit/shared/llm/test_budget_fair_use_branches.py",
    "tests/unit/shared/llm/test_budget_execution_branches.py",
    "tests/unit/shared/llm/test_budget_scheduler.py",
    "tests/unit/shared/llm/test_pricing_data.py",
    "tests/unit/core/test_budget_manager_fair_use.py",
    "tests/unit/core/test_budget_manager_audit.py",
    "tests/unit/llm/test_circuit_breaker.py",
    "tests/unit/llm/test_delta_analysis.py",
    "tests/unit/llm/test_delta_analysis_branch_paths_2.py",
    "tests/unit/llm/test_delta_analysis_exhaustive.py",
    "tests/unit/llm/test_budget_manager.py",
    "tests/unit/llm/test_budget_manager_exhaustive.py",
    "tests/unit/llm/test_guardrails_audit.py",
    "tests/unit/llm/test_hybrid_scheduler.py",
    "tests/unit/llm/test_hybrid_scheduler_exhaustive.py",
    "tests/unit/llm/test_factory_exhaustive.py",
    "tests/unit/llm/test_providers.py",
    "tests/unit/llm/test_usage_tracker.py",
    "tests/unit/llm/test_usage_tracker_audit.py",
    "tests/unit/llm/test_zombie_analyzer.py",
    "tests/unit/llm/test_zombie_analyzer_exhaustive.py",
    "tests/unit/llm/test_analyzer_exhaustive.py",
    "tests/unit/llm/test_analyzer_branch_edges.py",
    "tests/unit/services/llm/test_guardrails_logic.py",
    "tests/unit/api/v1/test_costs_endpoints.py",
    "tests/unit/api/v1/test_costs_acceptance_payload_branches.py",
    "tests/unit/api/v1/test_costs_reconciliation_routes.py",
    "tests/unit/api/v1/test_reconciliation_endpoints.py",
    "tests/unit/services/llm/test_llm_logic.py",
    "tests/unit/ops/test_enforcement_failure_injection_pack.py",
    "tests/unit/ops/test_enforcement_stress_evidence_pack.py",
    "tests/unit/ops/test_key_rotation_drill_evidence_pack.py",
    "tests/unit/ops/test_verify_key_rotation_drill_evidence.py",
    "tests/unit/ops/test_verify_enforcement_failure_injection_evidence.py",
    "tests/unit/ops/test_verify_enforcement_stress_evidence.py",
    "tests/unit/ops/test_verify_enforcement_post_closure_sanity.py",
    "tests/unit/ops/test_verify_alembic_head_integrity.py",
    "tests/unit/ops/test_webhook_job_reliability_drill_pack.py",
    "tests/unit/ops/test_verify_finance_guardrails_evidence.py",
    "tests/unit/ops/test_finance_guardrails_evidence_pack.py",
    "tests/unit/ops/test_verify_monthly_finance_evidence_refresh.py",
    "tests/unit/ops/test_collect_finance_telemetry_snapshot.py",
    "tests/unit/ops/test_verify_finance_telemetry_snapshot.py",
    "tests/unit/ops/test_generate_finance_committee_packet.py",
    "tests/unit/ops/test_finance_telemetry_snapshot_pack.py",
    "tests/unit/ops/test_verify_pkg015_launch_gate.py",
    "tests/unit/ops/test_verify_pricing_benchmark_register.py",
    "tests/unit/ops/test_pricing_benchmark_register_pack.py",
    "tests/unit/ops/test_verify_pkg_fin_policy_decisions.py",
    "tests/unit/ops/test_pkg_fin_policy_decisions_pack.py",
    "tests/unit/ops/test_verify_valdrics_disposition_freshness.py",
    "tests/unit/ops/test_verify_alertmanager_channels.py",
    "tests/unit/ops/test_valdrics_disposition_register_pack.py",
    "tests/unit/ops/test_release_artifact_templates_pack.py",
    "tests/unit/ops/test_verify_exception_governance.py",
    "tests/unit/ops/test_verify_env_hygiene.py",
    "tests/unit/ops/test_verify_dependency_locking.py",
    "tests/unit/ops/test_verify_adapter_test_coverage.py",
    "tests/unit/ops/test_verify_repo_root_hygiene.py",
    "tests/unit/ops/test_verify_python_module_size_budget.py",
    "tests/unit/ops/test_verify_frontend_module_size_budget.py",
    "tests/unit/ops/test_verify_architecture_decision_records.py",
    "tests/unit/ops/test_verify_test_to_production_ratio.py",
    "tests/unit/ops/test_db_diagnostics.py",
    "tests/unit/ops/test_verify_audit_report_resolved.py",
    "tests/unit/shared/adapters/test_license_vendor_types.py",
    "tests/unit/supply_chain/test_verify_jwt_bcp_checklist.py",
    "tests/unit/supply_chain/test_feature_enforceability_matrix.py",
    "tests/unit/supply_chain/test_run_enforcement_release_evidence_gate.py",
    "tests/contract/test_openapi_contract.py",
)

ENTERPRISE_GATE_COVERAGE_TARGETS: tuple[str, ...] = (
    "app/modules/enforcement",
    "app/shared/llm",
    "app/modules/reporting/api/v1",
)

ENFORCEMENT_COVERAGE_FAIL_UNDER = 95
LLM_COVERAGE_FAIL_UNDER = 90
ANALYTICS_VISIBILITY_COVERAGE_FAIL_UNDER = 99

LLM_GUARDRAIL_COVERAGE_INCLUDE: tuple[str, ...] = (
    "app/shared/llm/budget_fair_use.py",
    "app/shared/llm/budget_execution.py",
    "app/shared/llm/budget_manager.py",
    "app/shared/llm/usage_tracker.py",
    "app/shared/llm/factory.py",
    "app/shared/llm/providers/openai.py",
    "app/shared/llm/providers/anthropic.py",
    "app/shared/llm/providers/google.py",
    "app/shared/llm/providers/groq.py",
)

ANALYTICS_VISIBILITY_COVERAGE_INCLUDE: tuple[str, ...] = (
    "app/shared/llm/analyzer.py",
    "app/modules/reporting/api/v1/costs.py",
)

ENFORCEMENT_STRESS_EVIDENCE_PATH_ENV = "ENFORCEMENT_STRESS_EVIDENCE_PATH"
ENFORCEMENT_STRESS_EVIDENCE_MAX_AGE_HOURS_ENV = (
    "ENFORCEMENT_STRESS_EVIDENCE_MAX_AGE_HOURS"
)
ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_ENV = "ENFORCEMENT_STRESS_EVIDENCE_REQUIRED"
ENFORCEMENT_STRESS_EVIDENCE_MIN_DURATION_SECONDS_ENV = (
    "ENFORCEMENT_STRESS_EVIDENCE_MIN_DURATION_SECONDS"
)
ENFORCEMENT_STRESS_EVIDENCE_MIN_CONCURRENT_USERS_ENV = (
    "ENFORCEMENT_STRESS_EVIDENCE_MIN_CONCURRENT_USERS"
)
ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_DATABASE_ENGINE_ENV = (
    "ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_DATABASE_ENGINE"
)
DEFAULT_ENFORCEMENT_STRESS_MIN_DURATION_SECONDS = "30"
DEFAULT_ENFORCEMENT_STRESS_MIN_CONCURRENT_USERS = "10"
DEFAULT_ENFORCEMENT_STRESS_REQUIRED_DATABASE_ENGINE = "postgresql"
ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_PATH_ENV = (
    "ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_PATH"
)
ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_MAX_AGE_HOURS_ENV = (
    "ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_MAX_AGE_HOURS"
)
ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_REQUIRED_ENV = (
    "ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_REQUIRED"
)
ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH_ENV = (
    "ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH"
)
ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_MAX_AGE_HOURS_ENV = (
    "ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_MAX_AGE_HOURS"
)
ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_REQUIRED_ENV = (
    "ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_REQUIRED"
)
DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH = (
    "docs/ops/evidence/finance_guardrails_2026-02-27.json"
)
DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_MAX_AGE_HOURS = "744"
ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH_ENV = (
    "ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH"
)
ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_REQUIRED_ENV = (
    "ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_REQUIRED"
)
ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS_ENV = (
    "ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS"
)
DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH = (
    "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json"
)
DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS = "744"
ENFORCEMENT_PRICING_BENCHMARK_REGISTER_PATH_ENV = (
    "ENFORCEMENT_PRICING_BENCHMARK_REGISTER_PATH"
)
ENFORCEMENT_PRICING_BENCHMARK_REGISTER_REQUIRED_ENV = (
    "ENFORCEMENT_PRICING_BENCHMARK_REGISTER_REQUIRED"
)
ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS_ENV = (
    "ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS"
)
DEFAULT_ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS = "120"
ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH_ENV = (
    "ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH"
)
ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_REQUIRED_ENV = (
    "ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_REQUIRED"
)
ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS_ENV = (
    "ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS"
)
DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH = (
    "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json"
)
DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS = "744"
ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS_ENV = (
    "ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS"
)
ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS_ENV = (
    "ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS"
)
DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS = "35"
DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS = "14"
ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH_ENV = (
    "ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH"
)
ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS_ENV = (
    "ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS"
)
ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS_ENV = (
    "ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS"
)
ENFORCEMENT_RUNTIME_EVIDENCE_ONLY_ENV = "ENFORCEMENT_RUNTIME_EVIDENCE_ONLY"
DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH = (
    "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json"
)
DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS = "45"
DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS = "120"
ENFORCEMENT_KEY_ROTATION_DRILL_PATH_ENV = "ENFORCEMENT_KEY_ROTATION_DRILL_PATH"
ENFORCEMENT_KEY_ROTATION_DRILL_MAX_AGE_DAYS_ENV = (
    "ENFORCEMENT_KEY_ROTATION_DRILL_MAX_AGE_DAYS"
)
DEFAULT_KEY_ROTATION_DRILL_PATH = "docs/ops/key-rotation-drill-2026-02-27.md"
DEFAULT_KEY_ROTATION_DRILL_MAX_AGE_DAYS = "120"
