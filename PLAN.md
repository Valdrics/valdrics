# Valdrics Source of Truth Plan

Last reviewed: 2026-05-09
Status: Canonical
Owner: Product + Engineering

This file is the single source of truth for:

- what Valdrics is building
- what is active now
- what ships next
- what is only research
- what must be live before a phase is considered done

If another document disagrees with this file on planning, sequencing, or phase
scope, this file wins.

## Strategy Labels

Every major idea in this file is assigned one strategy label:

- `core disruption`: the primary standard-setting moves that can redefine the
  category if executed well
- `moat expansion`: high-value differentiators that deepen the product’s
  defensibility once the core disruption engine is live
- `frontier bet`: strategically interesting, market-adjacent, or novel ideas
  that may become category-shaping later but are weaker first wedges

## Non-Negotiable Rules

1. One active phase at a time.
2. A phase is not complete until it is live in production and usable by real
   users.
3. No overlap between phases. If work does not directly serve the active phase,
   it stays out unless it is required for a production incident, security fix,
   or release-blocking defect.
4. Cleanup is part of the phase exit. Superseded docs, files, directories,
   configuration, and code paths must be removed or archived before the phase
   closes.
5. Every phase must be independently shippable. We do not leave a phase
   partially live.
6. Every strategically relevant idea must be captured in a named phase in this
   file. Later phases exist because they depend on earlier foundations, not
   because they are ignored.

## Current Position

- The supported operating model is:
  - backend on Google Cloud Run
  - async work on Cloud Tasks
  - scheduled work on Cloud Scheduler
  - long-running work on Cloud Run Jobs
  - frontend on Cloudflare Pages
  - database, auth, and storage on Supabase
- The repo already contains the managed-platform foundation, deployment
  contracts, release workflows, TVC draft artifacts, and verification surfaces.
- The main unfinished work is not repo plumbing. It is live cutover evidence and
  real production use on the supported managed stack.
- Phase 1 now has two release lanes:
  - `release-beta-app.yml` for fast beta/product releases after infrastructure
    exists. This lane skips Terraform/state bootstrap and updates only Cloud Run
    app images, database migrations, and Cloudflare Pages.
  - `release-unified-platform.yml` for infrastructure changes, Cloudflare policy
    changes, Supabase project settings, and production promotion wiring.
- Current operational track: Cloudflare Bot Fight Mode is now enforced off by
  release preflight and Terraform using a GitHub `CLOUDFLARE_API_TOKEN` with
  Zone `Bot Management:Edit`. The latest staging full-release run passed
  Cloudflare preflight, Terraform, Cloudflare Pages deploy, API liveness,
  public smoke readiness, the in-deploy managed readiness gate, and the
  standalone staging release-readiness verifier. Production promotion was
  intentionally skipped for that run. The beta app-only release lane has also
  passed a staging smoke release with Terraform/state bootstrap skipped,
  including public API preflight, digest-pinned backend image publish, Cloud
  Run image update, database migrations, Cloudflare Pages deploy, API liveness,
  and managed release readiness. The full release lane now keeps Playwright
  browser setup explicit, manages the Cloudflare Pages custom domain, frontend
  CNAME, and Pages runtime variables required by the edge proxy, pins the
  artifact download action to a resolvable commit, restores the `.runtime`
  artifact extraction path for cross-job readiness checks, and keeps
  live-staging public visual baselines committed for the landing hero, product,
  and trust sections.
  Direct-upload Pages deploys render runtime variables into the Wrangler
  deployment config from the managed release bundle. The Cloudflare-hosted
  dashboard CSP uses nonce mode and allows Cloudflare Web Analytics sources so
  Cloudflare JavaScript Detections can run without weakening the policy with
  `unsafe-inline`.

## What Valdrics Is Building

Valdrics is not just a cloud cost dashboard. The product standard is:

1. A unified technology spend ledger across cloud, AI, SaaS, licensing,
   platform, and hybrid signals.
2. Deterministic accounting, allocation, reconciliation, and savings logic.
3. Governed action, not dashboards-only visibility.
4. Shift-left cost, carbon, and policy control in delivery workflows.
5. Unit economics and opportunity-cost decision support, not just raw spend.
6. AI, Cloud+, and GreenOps as first-class operating domains.
7. Enterprise-grade policy for security, compliance, residency, and operating
   control.
8. Open, API-first extension points instead of closed black-box workflows.

## Market Validation Basis

As of 2026-04-21, the current market signals supporting this plan are:

- Unified technology ledger is market-worthy because FinOps has already expanded
  beyond public cloud into AI, SaaS, licensing, private cloud, and data center,
  while FOCUS 1.3 now explicitly positions itself as normalization across cloud,
  SaaS, data center, and contract commitments.
- Shift-left delivery controls and TVC are market-worthy because the FinOps
  Foundation now treats pre-deployment architecture guidance, executive strategy
  alignment, and unit economics as core maturity areas. Inference from the
  standards reviewed: there is still no open standard that binds design-time
  intent, runtime evidence, and business-value reconciliation into one portable
  artifact.
- Unit economics and opportunity-cost analysis are market-worthy because the
  official Unit Economics and Planning & Estimating capabilities now frame
  technology decisions in terms of business unit metrics, cost per token, and
  time to achieve business value.
- AI, Cloud+, and GreenOps controls are market-worthy because the 2026 State of
  FinOps shows AI at 98%, SaaS at 90%, licensing at 64%, private cloud at 57%,
  and data center at 48%, while the Sustainability capability now expects
  allocatable, near-real-time carbon-aware reporting across technology domains.
- Sovereignty, adversarial FinOps, and enterprise policy are market-worthy
  because the 2026 Framework elevates executive strategy and converging
  disciplines, while sovereign-cloud economics now have clear price premiums and
  policy implications in the market.
- Commitment intelligence, claims automation, and recovery are market-worthy
  because adjacent markets already exist: insured cloud commitments, official
  AWS RI resale for eligible Standard RIs, and parametric cloud outage
  insurance.
- Portable execution and capacity-market features are market-worthy because
  multi-cloud, cheapest-infra scheduling and GPU capacity marketplaces are now
  commercially visible, especially for AI, batch, and inference workloads.
- Provider-price intelligence, verifiable receipts, and code-native economics
  are weaker but still worth capturing because the next competitive standard may
  emerge at the boundary between financial intelligence, software delivery, and
  machine-readable trust.

Primary validation sources reviewed:

- State of FinOps 2026: https://data.finops.org/
- FinOps mission update: https://www.finops.org/insights/mission-update/
- FinOps Framework 2026: https://www.finops.org/insights/2026-finops-framework/
- Unit Economics capability: https://www.finops.org/framework/capabilities/unit-economics/
- Planning & Estimating capability: https://www.finops.org/framework/capabilities/planning-estimating/
- Sustainability capability: https://www.finops.org/framework/capabilities/sustainability/
- FOCUS 1.3: https://focus.finops.org/focus-specification/
- OpenCost: https://opencost.io/
- AWS RI Marketplace: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-general.html
- Archera insured commitments: https://www.archera.ai/insured-commitments/
- Parametrix cloud outage insurance: https://www.parametrixinsurance.com/solutions-cloud
- SkyPilot docs: https://docs.skypilot.co/en/stable/docs/
- Compute Exchange: https://compute.exchange/
- BCG sovereign cloud economics: https://www.bcg.com/publications/2025/cloud-cover-price-sovereignty-demands-waste
- Ternary forecasting baseline: https://docs.ternary.app/docs/forecasting

## Completed Foundations

These are already materially established in the repo and should not be reopened
unless they block an active phase:

- supported managed platform contract on GCP + Cloudflare + Supabase
- Cloud Tasks, Cloud Scheduler, and Cloud Run Jobs execution model
- immutable release pipeline using Artifact Registry promotion refs
- fast beta app release lane that avoids Terraform for normal product releases
- managed deployment bundle verification and operator handoff generation
- FOCUS-aligned export and reporting foundations
- chargeback/showback and reconciliation foundations
- governed remediation and approval workflow foundations
- TVC draft schemas, examples, verifier, and admission receipt wiring

## What We Already Have On Ground

The following foundations already exist materially in the repo today:

- managed-platform operating model on GCP + Cloudflare + Supabase
- immutable release pipeline and managed deployment bundle verification
- app-only beta release lane for faster launch iteration on existing
  infrastructure
- Cloud Tasks, Cloud Scheduler, and Cloud Run Jobs execution surfaces
- FOCUS-aligned export and normalized reporting foundations
- chargeback, showback, reconciliation, and close workflow foundations
- governed remediation, approvals, and enforcement ledger foundations
- carbon, GreenOps, and sustainability-control foundations
- AI usage telemetry and budget-control foundations
- TVC draft schemas, examples, verifier, and deployment admission receipt
  surfaces

The following high-value ideas are only partial or missing today and still need
shipping work:

- mature unified technology spend ledger across all target domains
- PR-native and IaC-native shift-left cost, carbon, and policy enforcement
- runtime TVC execution receipts and reconciliation views
- opportunity-cost and business-outcome integrations
- deeper AI outcome attribution and Cloud+ control loops
- sovereign placement policy, adversarial FinOps, and enterprise policy engine
- commitment intelligence, claims recovery, and frontier market features

## Supporting Documents

This file owns planning and sequencing. Supporting docs exist for execution or
evidence only:

- deployment and release operations:
  - `docs/runbooks/unified_platform_release.md`
  - `docs/DEPLOYMENT.md`
  - `docs/runbooks/production_env_checklist.md`
- rollback and recovery:
  - `docs/ROLLBACK_PLAN.md`
  - `docs/runbooks/disaster_recovery.md`
- product research and market validation:
  - `docs/product/external_feedback_validation.md`
- shipping helpers:
  - `docs/runbooks/phased_shipping.md`

None of the documents above should introduce a second roadmap.

## Phase Map For All Strategic Ideas

Every major idea currently in scope or under serious consideration is assigned
to a shipping phase here:

- managed-platform live cutover -> Phase 1 -> `core disruption`
- unified technology spend ledger -> Phase 2 -> `core disruption`
- tag-less and shared-cost attribution -> Phase 2 -> `core disruption`
- audit-grade close and reconciliation -> Phase 3 -> `moat expansion`
- governed action and remediation loop -> Phase 4 -> `core disruption`
- Technology Value Contract standard -> Phase 5 -> `core disruption`
- shift-left PR and IaC cost/carbon/policy control -> Phase 5 -> `core disruption`
- unit economics -> Phase 6 -> `core disruption`
- opportunity-cost decisions -> Phase 6 -> `core disruption`
- AI token economics and Cloud+ controls -> Phase 7 -> `moat expansion`
- GreenOps and carbon-aware controls -> Phase 7 -> `moat expansion`
- sovereign and residency-aware optimization -> Phase 8 -> `moat expansion`
- adversarial FinOps -> Phase 8 -> `moat expansion`
- regret-aware commitments -> Phase 9 -> `moat expansion`
- SLA and outage claims recovery -> Phase 9 -> `moat expansion`
- secondary markets and reverse FinOps -> Phase 10 -> `frontier bet`
- portable-batch arbitrage and capacity exchange -> Phase 10 -> `frontier bet`
- provider-price market intelligence -> Phase 11 -> `frontier bet`
- trustless or cryptographically signed receipts -> Phase 11 -> `frontier bet`
- cost-aware compiler and code-native economics -> Phase 11 -> `frontier bet`

## Current Ground Truth By Phase

| Phase | Strategy | Ground truth now | Ship state |
| --- | --- | --- | --- |
| Phase 1: Managed Platform Live Cutover | `core disruption` | Repo foundations are present; live staging and production cutover evidence are still incomplete | Active |
| Phase 2: Unified Technology Spend Ledger | `core disruption` | Partial foundations exist through the AI-aware canonical spend-ledger API, allocation-aware FOCUS v1.3 export, normalized reporting, and Cloud+ connectors | Not shipped |
| Phase 3: Audit-Grade Close | `moat expansion` | Reconciliation and close foundations exist, but live end-to-end close proof as the canonical customer path is not established here | Not shipped |
| Phase 4: Governed Action Loop | `core disruption` | Approvals, enforcement, and remediation foundations exist, but the full action loop is not yet the closed customer operating standard | Not shipped |
| Phase 5: Technology Value Contract Standard | `core disruption` | Draft TVC schemas, examples, verifier, CI admission checks, and deployment admission receipts exist; runtime receipts and reconciliation views do not | Not shipped |
| Phase 6: Unit Economics and Opportunity Cost | `core disruption` | Unit-economics primitives and leadership KPIs exist, but business-outcome integrations and true opportunity-cost decisions do not | Not shipped |
| Phase 7: AI and Cloud+ Operating Controls | `moat expansion` | AI usage telemetry, budget controls, carbon, and Cloud+ connector foundations exist; mature domain control loops do not | Not shipped |
| Phase 8: Enterprise Policy and Resilience | `moat expansion` | Residency, security, and enforcement foundations exist in part; sovereign placement and adversarial FinOps are not yet production features | Not shipped |
| Phase 9: Commitment Intelligence and Recovery | `moat expansion` | Commitment optimization foundations exist, but regret-aware guidance and claims recovery workflows do not | Not shipped |
| Phase 10: Capacity Markets and Portable Execution | `frontier bet` | Only adjacent primitives exist today; no active marketplace or portable-execution product surface is shipped | Not shipped |
| Phase 11: Market Intelligence and Verifiable Economics | `frontier bet` | Forecasting and pricing baselines exist, but provider-price intelligence, verifiable receipts, and code-native economics are not shipped | Not shipped |

## Active Phase

### Phase 1: Managed Platform Live Cutover

Status: Active
Strategy label: `core disruption`

Outcome:

- Valdrics runs live for users on the supported managed platform only.

In scope:

- deploy `staging` on the managed stack
- use the fast beta app release lane for normal launch iteration once managed
  infrastructure exists
- run parity smoke, workload, and rollback validation
- cut staging traffic fully to the managed stack
- promote the exact same immutable artifact to `production`
- use the full unified release lane only for infrastructure, Cloudflare,
  Supabase, or production-promotion changes
- capture operator evidence packets for staging and production
- obtain final release-operations sign-off
- archive or remove any remaining unsupported operational paths that would
  confuse release ownership

Not in scope:

- new product surface area
- new R&D experiments
- new pricing or packaging work

Ship gate:

- staging is live and validated
- the beta app release lane can deploy without Terraform and pass API/dashboard
  smoke checks
- production is live on the supported stack
- release evidence is complete
- the supported runbooks match reality

Cleanup gate:

- no active docs or release helpers imply a parallel production path
- no retired deployment path is described as supported

## Queued Shipping Phases

### Phase 2: Unified Technology Spend Ledger

Status: Queued
Strategy label: `core disruption`

Outcome:

- users can see technology spend in one canonical ledger, not separate clouds
  and side systems

In scope:

- normalized ledger across cloud, AI, SaaS, licensing, platform, and hybrid
  signals
- FOCUS-native schema ownership and explicit allocation model
- shared-cost and tag-less allocation for multi-tenant services
- canonical ledger API and export contract

Current implementation notes:

- `CostRecord` remains the normalized origin-charge ledger row
- `CostAllocation` is the canonical split-allocation source for the ledger and
  FOCUS export
- `LLMUsage` is projected into the ledger as provider `ai`
- `/api/v1/costs/ledger` exposes the canonical tenant spend-ledger API
- FOCUS v1.3 export now emits resource, usage, pricing, allocation, and AI rows
- `COST_EXPORT` jobs now create bounded inline FOCUS CSV artifacts instead of
  placeholder download URLs
- acceptance KPI ledger-quality evidence now counts AI ledger rows alongside
  origin `CostRecord` rows

Not in scope:

- month-end close workflow
- remediation workflows
- pre-deployment delivery controls

Ship gate:

- at least one live tenant can ingest, allocate, and export unified spend from
  the ledger in production

Cleanup gate:

- duplicate ledger semantics or conflicting spend models are removed or archived

### Phase 3: Audit-Grade Close

Status: Queued
Strategy label: `moat expansion`

Outcome:

- finance and platform teams can reconcile and close from Valdrics without
  external spreadsheet assembly

In scope:

- reconciliation workflow hardening
- month-end close lifecycle
- audit-grade export integrity
- operator-usable evidence packets for close

Not in scope:

- remediation and approval loop
- shift-left engineering controls

Ship gate:

- at least one live close cycle can be run end to end in production

Cleanup gate:

- stale close docs, overlapping export paths, and redundant close surfaces are
  removed

### Phase 4: Governed Action Loop

Status: Queued
Strategy label: `core disruption`

Outcome:

- users can act on financial findings inside Valdrics with ownership, approval,
  execution, and auditability

In scope:

- owner routing
- approvals
- remediation workflow execution
- workflow automation into ticketing and messaging systems
- action ledger and outcome tracking

Not in scope:

- pre-deployment policy in developer workflows
- business-outcome modeling

Ship gate:

- at least one live tenant can detect, assign, approve, execute, and audit a
  cost-control action in production

Cleanup gate:

- dashboards-only duplicate action surfaces are removed or clearly demoted

### Phase 5: Technology Value Contract Standard

Status: Queued
Strategy label: `core disruption`

Outcome:

- Valdrics defines a new standard for pre-deployment intent plus post-deployment
  evidence

In scope:

- first-class `technology-value-contract` ownership
- PR and IaC admission checks for cost, carbon, and policy
- runtime execution receipt emission
- intent-versus-actual reconciliation
- developer-facing shift-left workflows

Not in scope:

- opportunity-cost and revenue trade-off modeling
- frontier market-structure bets

Ship gate:

- at least one engineering team uses TVC checks in CI/CD and receives live
  runtime receipts in production

Cleanup gate:

- overlapping ad hoc preflight policies and duplicate contract drafts are
  removed

### Phase 6: Unit Economics and Opportunity Cost

Status: Queued
Strategy label: `core disruption`

Outcome:

- users can make product and architecture decisions using unit economics and
  value trade-offs, not just raw spend

In scope:

- unit-cost metrics
- revenue and usage-source integrations
- leadership KPI surfaces
- opportunity-cost framing for major decisions
- decision records linked to outcomes

Not in scope:

- sovereign policy engines
- advanced autonomous market strategies

Ship gate:

- at least one live customer-facing or internal business unit can use Valdrics
  to evaluate cost per unit and a documented trade-off decision in production

Cleanup gate:

- stale KPI or reporting paths that duplicate the canonical unit-economics model
  are removed

### Phase 7: AI and Cloud+ Operating Controls

Status: Queued
Strategy label: `moat expansion`

Outcome:

- AI, SaaS, licensing, platform, hybrid, and carbon are governed as first-class
  spend domains

In scope:

- AI token telemetry and budget control
- per-team and per-feature AI allocation
- SaaS, license, platform, and hybrid control loops
- carbon budgets and intensity-aware guidance

Not in scope:

- full enterprise sovereignty engine
- adversarial-spend incident controls

Ship gate:

- at least one live tenant can attribute and govern AI plus one non-IaaS domain
  in production

Cleanup gate:

- domain-specific side logic that bypasses the canonical ledger or control model
  is removed

### Phase 8: Enterprise Policy and Resilience

Status: Queued
Strategy label: `moat expansion`

Outcome:

- Valdrics becomes enterprise-safe for compliance, residency, threat-aware
  spend control, and downside-managed optimization

In scope:

- sovereign and residency policy
- compliance-aware workload placement guidance
- adversarial FinOps and spend-as-threat-signal controls
- human-in-the-loop autonomous controls
- regret-aware commitment guidance

Not in scope:

- experimental secondary markets
- provider price oracles
- blockchain attribution

Ship gate:

- at least one live enterprise tenant can enforce residency or threat-aware
  spend control in production

Cleanup gate:

- overlapping policy logic and unofficial break-glass paths are removed

### Phase 9: Commitment Intelligence and Recovery

Status: Queued
Strategy label: `moat expansion`

Outcome:

- Valdrics helps customers make commitment decisions with bounded downside and
  recover value when providers or commitments underperform.

In scope:

- regret-aware commitment guidance
- insured-commitment decision support
- AWS and multi-provider commitment-transfer intelligence where provider terms
  permit it
- SLA, outage-credit, and claims-evidence workflows
- financial recovery surfaces tied to runtime and reliability signals

Not in scope:

- open marketplace brokering across all cloud products
- hyperscaler price trading strategies

Ship gate:

- at least one live tenant can use Valdrics in production to evaluate commitment
  downside risk or execute a claims or credit-recovery workflow tied to real
  provider events

Cleanup gate:

- overlapping commitment reports, ad hoc credit-recovery playbooks, and
  duplicate recovery logic are removed

### Phase 10: Capacity Markets and Portable Execution

Status: Queued
Strategy label: `frontier bet`

Outcome:

- Valdrics helps customers source, reserve, compare, and place bounded portable
  workloads and capacity across a fragmented provider market.

In scope:

- reverse FinOps and secondary-market workflows where legally and contractually
  supported
- portable batch, inference, and training placement
- GPU and reserved-capacity marketplace integrations
- supplier comparison across cost, SLA, capacity, and region
- capacity reservation planning for portable workloads

Not in scope:

- generic workload migration for every application class
- unsupported resale of provider commitments

Ship gate:

- at least one live tenant can use Valdrics in production to compare, source,
  reserve, or place a bounded portable workload or capacity plan through the
  product

Cleanup gate:

- disconnected capacity-planning helpers, stale marketplace assumptions, and
  one-off placement logic are removed

### Phase 11: Market Intelligence and Verifiable Economics

Status: Queued
Strategy label: `frontier bet`

Outcome:

- Valdrics becomes the economic intelligence layer for next-generation
  technology decisions, including verifiable receipts and code-native economics
  surfaces.

In scope:

- provider-price market intelligence
- buy-now versus wait decision support
- cryptographically signed or otherwise verifiable usage-receipt models
- cost-aware developer feedback that can evolve toward compiler or AST-assisted
  economics
- empirical experimentation framework for new financial-control primitives

Not in scope:

- broad autonomous trading of provider capacity
- promises of universal cost-aware compilation across all stacks

Ship gate:

- at least one live tenant can use a production Valdrics feature for provider
  price intelligence, verifiable receipts, or code-native economics guidance

Cleanup gate:

- ad hoc experimental economics docs, duplicate receipt drafts, and temporary
  market-intelligence scaffolds are removed or consolidated

## Sequencing Rule

All major ideas are captured above. They are later phases because they depend on
earlier ledger, control, policy, and evidence foundations, not because they are
out of scope.

## Phase Exit Checklist

Every phase closes only when all items below are true:

1. the scoped outcome is live in production
2. at least one real user or tenant can use it
3. tests and verification are green for the shipped surface
4. runbooks and docs match the live behavior
5. obsolete docs, code, directories, and configuration are cleaned up
6. the next phase is not opened until the current phase is explicitly closed in
   this file

## Working Rule for the Repo

When deciding what to do next:

1. look here first
2. confirm the active phase
3. reject out-of-phase work unless it is a production blocker
4. ship the phase fully
5. clean up before moving on
