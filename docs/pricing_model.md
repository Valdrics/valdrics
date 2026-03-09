# Pricing Metric Model

Last updated: March 9, 2026

## Default Value Metric

Primary pricing metric for early SaaS packaging:

- Connected cloud scope (accounts/subscriptions/projects) by tier
- Feature tier access (for example: Cloud+, reconciliation, compliance exports)
- Plan-level operational limits (retention, backfill, scan frequency)

Reference implementation:

- `app/shared/core/pricing.py`
- `app/shared/core/pricing_catalog.py`
- `app/shared/core/pricing_types.py`

## Plan Baseline

- `free`: permanent entry tier with strict limits and no credit card requirement.
- `starter`: small-team operating tier with up to `5 AWS` accounts plus limited non-AWS visibility (`1 Azure` tenant, `1 GCP` project).
- `growth`: first full team rollout tier with broad multi-cloud coverage, Slack integration, and SSO.
- `pro`: finance-grade controls including API access, audit logs, Cloud+ connectors, reconciliation, compliance exports, and incident integrations.
- `enterprise`: SCIM, effectively unbounded scale limits, and enterprise commercial controls such as private deployment and custom support motions.
- BYOK is available on all tiers.
- BYOK does not add a separate platform surcharge.
- Tier AI usage limits still apply even when BYOK is used.

## Current Packaging Corrections

The current package shape intentionally preserves a simple `Free -> Starter -> Growth -> Pro -> Enterprise` ladder.

- `Free` stays permanent and is used as the proof-of-value entry path.
- `Starter` is now a real team-visibility tier rather than AWS-only expansion.
- `Growth` is the first cross-functional rollout lane and now includes:
  - full AWS/Azure/GCP coverage,
  - Slack-integrated workflows,
  - SSO federation + enforcement.
- `Pro` remains the finance-grade governance tier and keeps:
  - `audit_logs`
  - `api_access`
  - `reconciliation`
  - `close_workflow`
  - `compliance_exports`
  - `savings_proof`
  - `cloud_plus_connectors`
  - `policy_configuration`
  - `incident_integrations`
- `Enterprise` remains reserved for enterprise differentiators:
  - SCIM
  - effectively unlimited scale
  - private/on-prem deployment
  - white-label and custom delivery motions
  - 24/7 support and procurement/security customization

## Upgrade Logic

Current intended upgrade path:

- `Free -> Starter`: more accounts, daily cadence, AI insights, limited cross-cloud visibility, longer retention.
- `Starter -> Growth`: owner routing, anomalies, remediation, backfill, chargeback, policy preview, Slack workflows, SSO.
- `Growth -> Pro`: auditability, API access, finance close support, compliance evidence, Cloud+ connectors, incident routing.
- `Pro -> Enterprise`: SCIM, procurement-ready deployment options, custom controls, and effectively unlimited scale.

## Billing Event Mapping (Product to Billing)

| Product action | Billing impact |
| --- | --- |
| Plan selected/changed | Plan price + feature/limit envelope updates |
| Connection count growth beyond plan limits | Upgrade prompt / policy gate before overage |
| Cloud+ connector enablement | Feature gate by tier (for example Pro+) |
| Backfill window increase | Tier-gated limit check |
| Compliance export / advanced workflows | Tier-gated access |

## Guardrails

1. Pricing must not penalize customers for reducing waste.
2. Core allocation/reconciliation signals remain available at practical tiers.
3. Hard limits should fail with clear guidance, not silent degradation.
4. Tier checks must be deterministic and test-covered.
5. BYOK is a control/privacy option, not a discount model.
6. Collaboration hooks should land before enterprise procurement hooks when that improves acquisition realism.
