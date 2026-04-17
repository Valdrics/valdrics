# Pricing Packaging Correction Closure

Date: March 9, 2026

## Scope

This closure note covers the pricing/package correction memo only:

1. Keep the 5-tier ladder.
2. Make Starter a real team-visibility tier.
3. Move Slack to Growth.
4. Move SSO to Growth.
5. Keep SCIM in Enterprise.
6. Keep finance-grade governance capabilities in Pro.
7. Keep Enterprise focused on true enterprise differentiators.
8. Align upgrade hooks and package language across active frontend, backend, and docs.

## Completion Status

1. `5-tier ladder kept` - Done
   - Backend catalog still exposes `free`, `starter`, `growth`, `pro`, `enterprise`.
   - Files:
     - `app/shared/core/pricing_catalog.py`
     - `app/shared/core/pricing.py`
     - `app/shared/core/pricing_types.py`

2. `Starter widened to limited non-AWS visibility` - Done
   - Starter now includes up to `5 AWS` accounts plus `1 Azure` tenant and `1 GCP` project.
   - Files:
     - `app/shared/core/pricing_catalog.py`
     - `app/modules/governance/api/v1/settings/connections_helpers.py`
     - `app/modules/governance/api/v1/settings/connections_azure_gcp.py`
     - `dashboard/src/lib/pricing/publicPlans.ts`
     - `dashboard/src/routes/pricing/+page.svelte`
     - `dashboard/src/routes/billing/+page.svelte`
     - `docs/pricing_model.md`

3. `Slack moved to Growth` - Done
   - Product copy, runtime entitlement checks, diagnostics, test delivery, and settings UI now treat Slack as `Growth+`.
   - Files:
     - `app/modules/governance/api/v1/settings/notification_settings_ops.py`
     - `app/modules/governance/api/v1/settings/notification_diagnostics_ops.py`
     - `app/modules/governance/api/v1/settings/notifications_models.py`
     - `app/modules/governance/api/v1/settings/notifications_acceptance_ops.py`
     - `app/modules/governance/api/v1/settings/notifications.py`
     - `app/modules/notifications/domain/slack.py`
     - `dashboard/src/routes/settings/SettingsNotificationControls.svelte`
     - `dashboard/src/routes/settings/settingsPageInitialState.ts`
     - `dashboard/src/routes/settings/settingsPageSchemas.ts`

4. `SSO moved to Growth` - Done
   - SSO discovery, identity settings gating, and active docs now treat SSO as `Growth+`.
   - Files:
     - `dashboard/src/lib/components/identity/identitySettingsHelpers.ts`
     - `dashboard/src/lib/components/IdentitySettingsCardContent.svelte`
     - `tests/unit/governance/api/test_public.py`
     - `tests/unit/governance/api/test_public_branch_paths.py`
     - `tests/unit/governance/settings/test_identity_settings.py`
     - `tests/unit/governance/settings/test_identity_settings_additional_branches.py`
     - `tests/unit/governance/settings/test_identity_settings_direct_branches.py`
     - `tests/unit/governance/settings/test_identity_settings_high_impact_branches.py`
     - `docs/integrations/sso.md`
     - `docs/integrations/idp_reference_configs.md`

5. `SCIM stays Enterprise` - Done
   - Enterprise-only identity lifecycle positioning remains intact in product and docs.
   - Files:
     - `app/shared/core/pricing_catalog.py`
     - `docs/integrations/scim.md`
     - `docs/integrations/idp_reference_configs.md`
     - `dashboard/src/routes/enterprise/+page.svelte`

6. `Pro keeps finance-grade governance capabilities` - Done
   - Pro remains the lane for:
     - `audit_logs`
     - `api_access`
     - `reconciliation`
     - `close_workflow`
     - `compliance_exports`
     - `savings_proof`
     - `cloud_plus_connectors`
     - `policy_configuration`
     - `incident_integrations`
   - Files:
     - `app/shared/core/pricing_catalog.py`
     - `dashboard/src/lib/pricing/publicPlans.ts`
     - `dashboard/src/routes/pricing/+page.svelte`
     - `dashboard/src/routes/billing/+page.svelte`
     - `docs/pricing_model.md`

7. `Enterprise remains procurement/security/commercial lane` - Done
   - Enterprise messaging now centers on SCIM, private deployment, procurement review, custom controls, and scale.
   - Files:
     - `dashboard/src/routes/enterprise/+page.svelte`
     - `dashboard/src/routes/talk-to-sales/+page.svelte`
     - `dashboard/src/routes/resources/valdrics-enterprise-one-pager.md/+server.ts`
     - `docs/pricing_model.md`

8. `Upgrade hooks aligned across authenticated/public product surfaces` - Done
   - Shared package-story prompts now drive:
     - pricing
     - billing
     - landing plan summaries
     - settings lock states
     - connections lock states
     - onboarding lock states
     - savings proof lock state
   - Files:
     - `dashboard/src/lib/pricing/publicPlans.ts`
     - `dashboard/src/lib/pricing/upgradePrompt.ts`
     - `dashboard/src/routes/pricing/+page.svelte`
     - `dashboard/src/routes/billing/+page.svelte`
     - `dashboard/src/lib/components/landing/LandingPlansSection.svelte`
     - `dashboard/src/lib/landing/heroContent.extended.ts`
     - `dashboard/src/routes/settings/SettingsActiveOpsCard.svelte`
     - `dashboard/src/routes/settings/SettingsWorkflowAutomationCard.svelte`
     - `dashboard/src/routes/connections/ConnectionsPublicCloudCards.svelte`
     - `dashboard/src/routes/connections/ConnectionsSaasLicenseCards.svelte`
     - `dashboard/src/routes/connections/ConnectionsPlatformHybridCards.svelte`
     - `dashboard/src/routes/connections/ConnectionsOrgDiscoverySection.svelte`
     - `dashboard/src/routes/onboarding/OnboardingStepSelectProviderSection.svelte`
     - `dashboard/src/routes/savings/SavingsPageViewContent.svelte`
     - `dashboard/src/lib/components/FindingsTable.svelte`
     - `app/modules/optimization/domain/zombie_scan_state.py`

## Validation

Executed and passing:

1. Frontend package-alignment suites
   - `pnpm --dir dashboard exec vitest run src/lib/components/FindingsTable.svelte.test.ts src/lib/components/IdentitySettingsCard.svelte.test.ts src/lib/components/EnforcementSettingsCard.svelte.test.ts src/lib/components/EnforcementOpsCard.svelte.test.ts src/routes/settings/settings-page.advanced.svelte.test.ts src/routes/savings/savings-page.svelte.test.ts src/routes/connections/connections-page.svelte.test.ts src/routes/onboarding/onboarding-page.svelte.test.ts src/routes/billing/billing-page.svelte.test.ts src/routes/pricing/pricing-page.svelte.test.ts src/lib/components/LandingHero.svelte.test.ts`
   - Result: `33 passed`

2. Billing/catalog and connection gate validation
   - `DEBUG=false uv run pytest -q --no-cov tests/billing/test_tier_guard.py tests/unit/governance/test_connections_api_aws.py tests/unit/governance/settings/test_connections_branches.py`
   - Result: `56 passed`

3. Public SSO + identity tier validation
   - `DEBUG=false uv run pytest -q --no-cov tests/unit/governance/api/test_public.py tests/unit/governance/api/test_public_branch_paths.py tests/unit/governance/settings/test_identity_settings.py tests/unit/governance/settings/test_identity_settings_additional_branches.py tests/unit/governance/settings/test_identity_settings_direct_branches.py tests/unit/governance/settings/test_identity_settings_high_impact_branches.py`
   - Result: `89 passed`

4. Notification entitlement/runtime validation
   - `DEBUG=false uv run pytest -q --no-cov tests/unit/governance/settings/test_notification_entitlement_ops.py tests/unit/notifications/domain/test_slack_service.py tests/billing/test_tier_guard.py`
   - Result: `34 passed`

5. Zombie tier masking wording normalization
   - `UV_CACHE_DIR=/tmp/uv-cache DEBUG=false uv run pytest -q --no-cov tests/unit/zombies/test_tier_gating_phase8.py`
   - Result: `4 passed`

6. Documentation/runtime contract check
   - `DEBUG=false uv run python3 scripts/verify_documentation_runtime_contracts.py`
   - Result: `PASS`

## CI Note

No `.github/workflows/*` change was required for this correction memo.

Reason:

- The package correction was enforced through updated runtime code, active docs, and test suites.
- Existing CI already runs the relevant frontend/backend/doc validation paths.

## Exclusions

This closure does not rewrite historical/archive notes under `docs/ops` or `docs/notes` as if they were live product contracts.

Those files remain historical records, not the active pricing/package source of truth.
