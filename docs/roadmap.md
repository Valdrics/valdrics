# Valdrics Roadmap (Internal)

Last reviewed: **March 10, 2026**

This is the active planning document for forward-looking delivery priorities.
Shipped execution history and evidence snapshots live in the progress archive:
- `reports/roadmap/ROADMAP_PROGRESS_2026-02-20.md`
- `reports/roadmap/ROADMAP_PROGRESS_2026-02-15.md`
- `reports/roadmap/ROADMAP_PROGRESS_2026-02-14.md`
- `reports/roadmap/ROADMAP_PROGRESS_2026-02-13.md`

## Delivery Guardrails (Always)
1. Deterministic-first core: allocation, anomaly detection, reconciliation, and savings math remain rule/model based; LLM is used for summarization/explanation/remediation guidance only.
2. Ingestion contracts: all connectors must be scheduled, idempotent, and schema-versioned with explicit replay/backfill behavior.
3. Unified normalized model: all sources (cloud + Cloud+) emit one internal shape: provider, account/subscription/project, service, resource_id, usage_amount, usage_unit, cost, currency, timestamp, tags/labels.
4. Operational loop: every detection path supports ownership + action (ticket/workflow/policy/notification), not dashboards-only.
5. Persona separation: Engineering, Finance, Platform, and Leadership get role-appropriate views and APIs.
6. Acceptance evidence: each epic closes only when code/tests pass and repeatable acceptance evidence is captured.

## Sprint Standard (How We Ship)
1. Pick one sprint goal with crisp acceptance criteria.
2. Review existing implementation patterns first (avoid duplication).
3. Implement end-to-end (API + domain + persistence) with security, performance, and tenancy isolation in mind.
4. Add targeted tests for happy paths and failure paths.
5. Run the focused tests for the changed modules.
6. Capture acceptance evidence (Ops automation where possible) and record pointers in the progress archive.

## Planning Horizons

### Now: Control-Loop Product Hardening
1. Canonical billing ledger + FOCUS-ready normalization.
2. Reconciliation and close workflows with audit-grade export integrity.
3. Decision-loop product surfaces: owner routing, approval path, recorded outcome.
4. Ingestion source parity across AWS, Azure, GCP, SaaS, and license signals with replay/backfill and SLIs.
5. Pricing, packaging, and billing clarity across landing, pricing, and authenticated plan surfaces.

### Next: Financial Productization
1. Chargeback/showback product APIs + workflows (rules + simulation + coverage KPIs).
2. Unit economics layer (configurable unit-cost KPIs + anomaly routing).
3. Ingestion completeness and backfill (idempotent overlap windows, SLAs, monitoring).
4. Deterministic anomaly detection v1.
5. Waste/rightsizing detection v1.
6. Architectural inefficiency detection v1.

### Later: Enterprise Close + Cloud+ Expansion
1. Reconciliation v2 close workflow (JSON/CSV + audit trail, preliminary vs final lifecycle).
2. Cloud+ scope expansion (SaaS/license/platform/hybrid connectors through the same pipeline).
3. Carbon assurance v2 (factor versioning, auditability, reproducibility).
4. Governance/policy workflows (allow|warn|block|escalate + approval flow).
5. Integrations/action automation (Slack/Teams, Jira, GitHub/GitLab/CI webhooks).

### Horizon: Scale, Procurement, and Proof
1. Enterprise packaging hardening (SSO/SCIM, compliance exports, isolation verification).
2. Performance and reliability scale-up (10x ingestion volume, p95 dashboard targets, job SLOs).
3. Commercial proof system (savings realized vs opportunity + close package + procurement bundle).
4. Cloud+ domain expansion beyond IaaS/SaaS basics (platform + hybrid).
5. Persona-specific product experience hardening.

## Current Focus

1. Keep the product differentiated around governed action instead of generic visibility.
2. Finish public-surface hardening: pricing clarity, proof surfaces, docs/resources consistency, and sales intake quality.
3. Keep local and production operations explicit: bootstrap-only sqlite dev, fail-closed migrations, strict env/runbook contracts.
4. Expand enterprise readiness only where backed by real controls and verifiable evidence.

## How to Use This Document

- Use this file for current priorities and near-term sequencing.
- Use `reports/roadmap/*` for shipped-history snapshots.
- Use evidence/runbook/contract documents under `docs/ops`, `docs/runbooks`, and `docs/security` for operational truth.
