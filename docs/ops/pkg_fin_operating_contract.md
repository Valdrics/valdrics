# PKG/FIN Operating Contract

Last Updated: March 9, 2026
Replaces: the retired February 27, 2026 PKG/FIN decision memo

## Purpose

This is the active operating contract for pricing, packaging, and finance-governance release decisions.
It replaces the retired decision memo and defines the current evidence-backed rules that must hold before package or pricing changes are shipped.

## Current Product Contract

1. Valdrics keeps a 5-tier ladder: `Free`, `Starter`, `Growth`, `Pro`, `Enterprise`.
2. `Starter` is the entry team-visibility tier and includes limited cross-cloud visibility:
   - up to `5` AWS accounts,
   - `1` Azure tenant,
   - `1` GCP project.
3. `Growth` is the first real operating tier and includes:
   - owner attribution,
   - anomaly workflows,
   - remediation/backfill lanes,
   - Slack integration,
   - SSO.
4. `Pro` remains the finance-grade governance tier and keeps:
   - `audit_logs`,
   - `api_access`,
   - `reconciliation`,
   - `close_workflow`,
   - `compliance_exports`,
   - `savings_proof`,
   - `cloud_plus_connectors`,
   - `policy_configuration`,
   - `incident_integrations`.
5. `Enterprise` remains the procurement/security/customization lane and keeps:
   - `SCIM`,
   - unlimited scale,
   - on-prem/private deployment,
   - white-label,
   - custom development,
   - `24/7` support,
   - procurement/security customization.

## Why Internal Telemetry and Policy Choices Still Matter

Pricing and packaging release decisions are not safe if they rely on code changes alone.
The controlling inputs remain `internal telemetry` and explicit `policy choices`.

`Internal telemetry` is required to verify:
1. tier-level margin,
2. LLM cost envelopes,
3. conversion and expansion behavior,
4. operational support load,
5. packaging stress under real tenant usage.

`Policy choices` are required to lock:
1. what stays in `Growth` versus `Pro`,
2. what remains `Enterprise` only,
3. discount bands and migration rules,
4. guardrail thresholds that trigger pricing or packaging review,
5. approval owners for release decisions.

## How to resolve the blocker

1. Generate the current monthly finance packet and evidence set.
2. Verify the pricing benchmark register is fresh enough for the motion being reviewed.
3. Verify the `pkg_fin_policy_decisions` artifact records the required owners, approvals, and approval timestamps.
4. Confirm the active packaging contract still matches runtime behavior, docs, and customer-facing surfaces.
5. Block the release if any finance or PKG/FIN evidence gate fails.

## Required Evidence Contracts

The following evidence remains release-relevant for pricing and packaging work:
1. `docs/ops/evidence/finance_guardrails_TEMPLATE.json`
2. `docs/ops/evidence/finance_guardrails_2026-02-27.json`
3. `docs/ops/evidence/pricing_benchmark_register_TEMPLATE.json`
4. `docs/ops/evidence/pricing_benchmark_register_2026-02-27.json`
5. `docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json`
6. `docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json`
7. `scripts/verify_finance_guardrails_evidence.py`
8. `scripts/verify_pricing_benchmark_register.py`
9. `scripts/verify_pkg_fin_policy_decisions.py`

## Active Linked Contracts

1. Public package and entitlement contract:
   - `docs/pricing_model.md`
2. Packaging correction closure record:
   - `docs/ops/pricing_packaging_correction_closure_2026-03-09.md`
3. Workflow automation entitlement split:
   - `docs/integrations/workflow_automation.md`

## External Reference Anchors

These external anchors remain the public justification layer for this contract:
1. `FinOps Framework capabilities` for governance and unit economics control design.
2. `Stripe subscription price-change operations` for controlled migration and grandfathering mechanics.
3. AWS cost-governance guidance for periodic review and measurable control loops.

## Release Rule

No pricing or packaging motion is complete unless:
1. runtime entitlements match the declared package boundary,
2. active docs match runtime behavior,
3. required evidence artifacts validate successfully,
4. the change can survive the post-closure sanity checks for observability, deterministic replay, failure modes, and operational misconfiguration.
