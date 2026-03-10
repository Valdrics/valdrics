# All Changes Categorization Register Follow-Up (2026-03-09)

Generated from live working tree using `git status --porcelain -uall`.

## Summary

- Total changed paths: 239
- Modified paths: 181
- New/untracked paths: 54
- Deleted paths: 4

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track BA | Backend services, governance, enforcement, and shared core changes | 56 | #259 |
| Track BB | Frontend dashboard, marketing, pricing, and product surface changes | 115 | #260 |
| Track BC | Verification scripts, release gates, and test coverage | 57 | #261 |
| Track BD | Documentation, ops evidence, and pricing artifacts | 11 | #262 |

## Full Inventory By Track

### Track BA - Backend services, governance, enforcement, and shared core changes (56)

| Status | Path |
|---|---|
| `M` | `app/models/__init__.py` |
| `M` | `app/modules/billing/api/v1/billing_ops.py` |
| `M` | `app/modules/billing/domain/billing/paystack_service_runtime_ops.py` |
| `M` | `app/modules/enforcement/domain/action_errors.py` |
| `M` | `app/modules/enforcement/domain/approval_token_ops.py` |
| `M` | `app/modules/enforcement/domain/service.py` |
| `M` | `app/modules/enforcement/domain/service_response_ops.py` |
| `M` | `app/modules/enforcement/domain/service_runtime_ledger_ops.py` |
| `M` | `app/modules/governance/api/v1/audit_evidence.py` |
| `M` | `app/modules/governance/api/v1/public.py` |
| `M` | `app/modules/governance/api/v1/public_marketing.py` |
| `M` | `app/modules/governance/api/v1/scim_core_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/account.py` |
| `M` | `app/modules/governance/api/v1/settings/notification_diagnostics_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/notification_settings_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/notifications.py` |
| `M` | `app/modules/governance/api/v1/settings/notifications_acceptance_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/notifications_models.py` |
| `M` | `app/modules/governance/domain/jobs/cur_ingestion.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/notifications.py` |
| `M` | `app/modules/governance/domain/security/audit_log.py` |
| `M` | `app/modules/governance/domain/security/compliance_pack_bundle.py` |
| `M` | `app/modules/governance/domain/security/compliance_pack_bundle_exports.py` |
| `M` | `app/modules/notifications/domain/__init__.py` |
| `M` | `app/modules/notifications/domain/email_service.py` |
| `M` | `app/modules/notifications/domain/slack.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/rightsizing.py` |
| `M` | `app/modules/optimization/domain/actions/gcp/compute.py` |
| `M` | `app/modules/optimization/domain/actions/license/base.py` |
| `M` | `app/modules/optimization/domain/actions/saas/github.py` |
| `M` | `app/modules/optimization/domain/ports.py` |
| `M` | `app/modules/optimization/domain/unified_discovery.py` |
| `M` | `app/modules/optimization/domain/zombie_scan_state.py` |
| `M` | `app/modules/reporting/api/v1/costs.py` |
| `M` | `app/modules/reporting/api/v1/costs_acceptance_payload.py` |
| `M` | `app/modules/reporting/domain/service.py` |
| `M` | `app/shared/adapters/aws_utils.py` |
| `M` | `app/shared/adapters/hybrid.py` |
| `M` | `app/shared/adapters/rate_limiter.py` |
| `M` | `app/shared/connections/oidc.py` |
| `M` | `app/shared/core/aws_credentials.py` |
| `M` | `app/shared/core/cloud_pricing_data.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/config_validation_runtime.py` |
| `M` | `app/shared/core/health_check_ops.py` |
| `M` | `app/shared/core/maintenance.py` |
| `M` | `app/shared/core/middleware.py` |
| `M` | `app/shared/core/ops_metrics.py` |
| `M` | `app/shared/core/performance_testing.py` |
| `M` | `app/shared/core/retry.py` |
| `M` | `app/shared/core/sentry.py` |
| `M` | `app/shared/core/turnstile.py` |
| `M` | `app/shared/db/session.py` |
| `M` | `app/shared/llm/delta_analysis.py` |
| `??` | `app/models/public_sales_inquiry.py` |
| `??` | `migrations/versions/o1p2q3r4s5t6_add_public_sales_inquiries.py` |

### Track BB - Frontend dashboard, marketing, pricing, and product surface changes (115)

| Status | Path |
|---|---|
| `M` | `dashboard/e2e/landing-visual.spec.ts` |
| `M` | `dashboard/e2e/public-a11y.spec.ts` |
| `M` | `dashboard/e2e/public-marketing.spec.ts` |
| `M` | `dashboard/playwright.config.ts` |
| `M` | `dashboard/src/lib/components/EnforcementOpsCard.svelte` |
| `M` | `dashboard/src/lib/components/EnforcementOpsCard.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/EnforcementSettingsCard.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/EnforcementSettingsCardView.svelte` |
| `M` | `dashboard/src/lib/components/FindingsTable.svelte` |
| `M` | `dashboard/src/lib/components/IdentitySettingsCard.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/IdentitySettingsCardContent.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.css` |
| `M` | `dashboard/src/lib/components/LandingHero.motion.surface.css` |
| `M` | `dashboard/src/lib/components/LandingHero.roi-plans.css` |
| `M` | `dashboard/src/lib/components/LandingHero.signal-preview.css` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.css` |
| `M` | `dashboard/src/lib/components/landing/LandingExitIntentPrompt.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingPlansSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.lead_exit.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/public/PublicMarketingPage.css` |
| `M` | `dashboard/src/lib/landing/heroContent.extended.ts` |
| `M` | `dashboard/src/lib/pricing/publicPlans.ts` |
| `M` | `dashboard/src/lib/routeProtection.ts` |
| `M` | `dashboard/src/routes/billing/+page.svelte` |
| `M` | `dashboard/src/routes/connections/ConnectionsOrgDiscoverySection.svelte` |
| `M` | `dashboard/src/routes/connections/ConnectionsPlatformHybridCards.svelte` |
| `M` | `dashboard/src/routes/connections/ConnectionsPublicCloudCards.svelte` |
| `M` | `dashboard/src/routes/connections/ConnectionsSaasLicenseCards.svelte` |
| `M` | `dashboard/src/routes/connections/connections-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/docs/+page.svelte` |
| `M` | `dashboard/src/routes/docs/api/+page.svelte` |
| `M` | `dashboard/src/routes/docs/api/docs-api-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/docs/docs-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/docs/technical-validation/+page.svelte` |
| `M` | `dashboard/src/routes/docs/technical-validation/technical-validation-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/enterprise/+page.svelte` |
| `M` | `dashboard/src/routes/enterprise/enterprise-page.layout.css` |
| `M` | `dashboard/src/routes/enterprise/enterprise-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/greenops/GreenOpsTierPreview.svelte` |
| `M` | `dashboard/src/routes/insights/+page.svelte` |
| `M` | `dashboard/src/routes/insights/insights-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/onboarding/OnboardingStepSelectProviderSection.svelte` |
| `M` | `dashboard/src/routes/onboarding/onboarding-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/pricing/+page.svelte` |
| `M` | `dashboard/src/routes/pricing/pricing-page.css` |
| `M` | `dashboard/src/routes/pricing/pricing-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/proof/+page.svelte` |
| `M` | `dashboard/src/routes/proof/proof-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/resources/+page.svelte` |
| `M` | `dashboard/src/routes/resources/resources-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/resources/valdrics-enterprise-one-pager.md/+server.ts` |
| `M` | `dashboard/src/routes/resources/valdrics-enterprise-one-pager.md/one-pager.server.test.ts` |
| `M` | `dashboard/src/routes/savings/SavingsPageViewContent.svelte` |
| `M` | `dashboard/src/routes/savings/savings-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/settings/SettingsActiveOpsCard.svelte` |
| `M` | `dashboard/src/routes/settings/SettingsNotificationControls.svelte` |
| `M` | `dashboard/src/routes/settings/SettingsPageViewBody.svelte` |
| `M` | `dashboard/src/routes/settings/SettingsWorkflowAutomationCard.svelte` |
| `M` | `dashboard/src/routes/settings/settings-page.advanced.svelte.test.ts` |
| `M` | `dashboard/src/routes/settings/settings-page.core.svelte.test.ts` |
| `M` | `dashboard/src/routes/settings/settingsPageInitialState.ts` |
| `M` | `dashboard/src/routes/settings/settingsPageSchemas.ts` |
| `M` | `dashboard/src/routes/sitemap.xml/+server.ts` |
| `M` | `dashboard/src/routes/sitemap.xml/sitemap.server.test.ts` |
| `M` | `dashboard/src/routes/status/+page.svelte` |
| `M` | `dashboard/src/routes/talk-to-sales/+page.svelte` |
| `M` | `dashboard/src/routes/talk-to-sales/talk-to-sales-page.svelte.test.ts` |
| `??` | `dashboard/src/lib/components/FindingsTable.svelte.test.ts` |
| `??` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css` |
| `??` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.support.css` |
| `??` | `dashboard/src/lib/components/LandingHero.motion.surface.shell.css` |
| `??` | `dashboard/src/lib/components/LandingHero.motion.surface.story.css` |
| `??` | `dashboard/src/lib/components/LandingHero.roi-plans.outcomes.css` |
| `??` | `dashboard/src/lib/components/LandingHero.roi-plans.simulator.css` |
| `??` | `dashboard/src/lib/components/LandingHero.signal-preview.approval-chain.css` |
| `??` | `dashboard/src/lib/components/LandingHero.signal-preview.controls.css` |
| `??` | `dashboard/src/lib/components/LandingHero.signal-preview.core.css` |
| `??` | `dashboard/src/lib/components/LandingHero.signal-preview.shell.css` |
| `??` | `dashboard/src/lib/components/LandingHero.trust.core.css` |
| `??` | `dashboard/src/lib/components/LandingHero.trust.coverage.css` |
| `??` | `dashboard/src/lib/components/LandingHero.trust.details.css` |
| `??` | `dashboard/src/lib/components/LandingHero.trust.plan-rollout.css` |
| `??` | `dashboard/src/lib/components/public/PublicContentArticlePage.svelte` |
| `??` | `dashboard/src/lib/components/public/PublicContentArticlePage.svelte.test.ts` |
| `??` | `dashboard/src/lib/components/public/PublicMarketingPage.article.css` |
| `??` | `dashboard/src/lib/components/public/PublicMarketingPage.layout.css` |
| `??` | `dashboard/src/lib/components/public/PublicPageMeta.svelte` |
| `??` | `dashboard/src/lib/components/public/PublicPageMeta.svelte.test.ts` |
| `??` | `dashboard/src/lib/content/publicContent.docs.ts` |
| `??` | `dashboard/src/lib/content/publicContent.insights.ts` |
| `??` | `dashboard/src/lib/content/publicContent.proof.ts` |
| `??` | `dashboard/src/lib/content/publicContent.resources.ts` |
| `??` | `dashboard/src/lib/content/publicContent.test.ts` |
| `??` | `dashboard/src/lib/content/publicContent.ts` |
| `??` | `dashboard/src/lib/pricing/upgradePrompt.ts` |
| `??` | `dashboard/src/lib/seo/publicMeta.test.ts` |
| `??` | `dashboard/src/lib/seo/publicMeta.ts` |
| `??` | `dashboard/src/routes/api/marketing/talk-to-sales/+server.ts` |
| `??` | `dashboard/src/routes/api/marketing/talk-to-sales/talk-to-sales.server.test.ts` |
| `??` | `dashboard/src/routes/billing/billing-page.css` |
| `??` | `dashboard/src/routes/billing/billing-page.svelte.test.ts` |
| `??` | `dashboard/src/routes/docs/[slug]/+page.svelte` |
| `??` | `dashboard/src/routes/docs/[slug]/+page.ts` |
| `??` | `dashboard/src/routes/insights/[slug]/+page.svelte` |
| `??` | `dashboard/src/routes/insights/[slug]/+page.ts` |
| `??` | `dashboard/src/routes/proof/[slug]/+page.svelte` |
| `??` | `dashboard/src/routes/proof/[slug]/+page.ts` |
| `??` | `dashboard/src/routes/resources/[slug]/+page.svelte` |
| `??` | `dashboard/src/routes/resources/[slug]/+page.ts` |
| `??` | `dashboard/src/routes/talk-to-sales/talk-to-sales-page-content.ts` |
| `??` | `dashboard/src/routes/talk-to-sales/talk-to-sales-page.css` |

### Track BC - Verification scripts, release gates, and test coverage (57)

| Status | Path |
|---|---|
| `M` | `scripts/audit_report_controls_core.py` |
| `M` | `scripts/audit_report_controls_registry.py` |
| `M` | `scripts/audit_schema.py` |
| `M` | `scripts/capture_acceptance_bootstrap.py` |
| `M` | `scripts/capture_acceptance_evidence.py` |
| `M` | `scripts/check_frontend_hygiene.py` |
| `M` | `scripts/emergency_token.py` |
| `M` | `scripts/enterprise_tdd_gate_coverage.py` |
| `M` | `scripts/generate_enforcement_failure_injection_evidence.py` |
| `M` | `scripts/generate_enforcement_stress_evidence.py` |
| `M` | `scripts/generate_finance_telemetry_snapshot.py` |
| `M` | `scripts/generate_key_rotation_drill_evidence.py` |
| `M` | `scripts/generate_valdrics_disposition_register.py` |
| `M` | `scripts/list_partitions.py` |
| `M` | `scripts/load_test_api.py` |
| `M` | `scripts/purge_simulation_data.py` |
| `M` | `scripts/run_enforcement_release_evidence_gate.py` |
| `M` | `scripts/run_enterprise_tdd_gate.py` |
| `M` | `scripts/smoke_test_sso_federation.py` |
| `M` | `scripts/stress_test.py` |
| `M` | `scripts/verify_activeops_e2e.py` |
| `M` | `scripts/verify_all_plugins.py` |
| `M` | `scripts/verify_env_hygiene.py` |
| `M` | `scripts/verify_plugins.py` |
| `M` | `scripts/verify_remediation.py` |
| `M` | `scripts/verify_rls_detailed.py` |
| `M` | `scripts/verify_supply_chain_attestations.py` |
| `M` | `scripts/verify_tenant_isolation.py` |
| `M` | `tests/conftest.py` |
| `M` | `tests/unit/core/test_health_deep.py` |
| `M` | `tests/unit/core/test_retry_utils.py` |
| `M` | `tests/unit/core/test_retry_utils_branch_paths.py` |
| `M` | `tests/unit/core/test_turnstile.py` |
| `M` | `tests/unit/enforcement/test_enforcement_actions_service.py` |
| `M` | `tests/unit/governance/api/test_public.py` |
| `M` | `tests/unit/governance/domain/jobs/handlers/test_notification_handler.py` |
| `M` | `tests/unit/governance/settings/conftest.py` |
| `M` | `tests/unit/governance/settings/test_governance_deep.py` |
| `M` | `tests/unit/governance/settings/test_notifications_core_slack.py` |
| `M` | `tests/unit/governance/settings/test_notifications_diagnostics_workflow.py` |
| `M` | `tests/unit/llm/test_analyzer.py` |
| `M` | `tests/unit/notifications/domain/test_email_service.py` |
| `M` | `tests/unit/notifications/domain/test_slack_service.py` |
| `M` | `tests/unit/ops/test_check_frontend_hygiene.py` |
| `M` | `tests/unit/ops/test_finance_guardrails_evidence_pack.py` |
| `M` | `tests/unit/ops/test_pkg_fin_policy_decisions_pack.py` |
| `M` | `tests/unit/ops/test_verify_audit_report_resolved.py` |
| `M` | `tests/unit/services/adapters/test_rate_limiter.py` |
| `M` | `tests/unit/supply_chain/test_run_enforcement_release_evidence_gate.py` |
| `M` | `tests/unit/supply_chain/test_verify_supply_chain_attestations.py` |
| `M` | `tests/unit/zombies/test_tier_gating_phase8.py` |
| `??` | `scripts/plugin_registry_verification.py` |
| `??` | `tests/unit/enforcement/enforcement_actions_orchestrator_support.py` |
| `??` | `tests/unit/enforcement/test_enforcement_actions_service_branches.py` |
| `??` | `tests/unit/governance/settings/test_notification_entitlement_ops.py` |
| `??` | `tests/unit/llm/test_analyzer_production_quality.py` |
| `??` | `tests/unit/ops/test_verify_plugins.py` |

### Track BD - Documentation, ops evidence, and pricing artifacts (11)

| Status | Path |
|---|---|
| `M` | `docs/integrations/workflow_automation.md` |
| `D` | `docs/notes/feedback_2026-02-22.md` |
| `D` | `docs/notes/useLanding.md` |
| `M` | `docs/ops/audit_remediation_2026-02-20.md` |
| `M` | `docs/ops/enforcement_control_plane_gap_register_2026-02-23.md` |
| `M` | `docs/ops/evidence/all_changes_inventory_2026-03-02.txt` |
| `D` | `docs/ops/pkg_fin_decision_memo_2026-02-27.md` |
| `D` | `docs/ops/pricing_competitiveness_fact_check_2026-02-17.md` |
| `M` | `docs/pricing_model.md` |
| `??` | `docs/ops/pkg_fin_operating_contract.md` |
| `??` | `docs/ops/pricing_packaging_correction_closure_2026-03-09.md` |
