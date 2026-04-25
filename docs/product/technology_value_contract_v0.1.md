# Technology Value Contract (TVC) v0.1

Status: Draft candidate
Last updated: 2026-04-20
Owner: Product / Platform

## Purpose

Technology Value Contract (TVC) is a machine-readable contract for declaring:

- what a workload, service, model, or delivery lane is expected to achieve
- what cost, carbon, performance, and compliance guardrails apply
- what evidence must be emitted so intent can be reconciled against runtime reality

TVC is meant to close the gap between design-time intent and post-deployment financial reporting.

## Why This Exists

Existing standards already solve important pieces of the problem:

- `FOCUS` normalizes billing and usage datasets across technology vendors.
- `OpenCost` standardizes allocation for Kubernetes and cloud-native shared environments.
- `OpenSLO` defines service level objectives as code.
- `CloudEvents` provides a portable event envelope for runtime evidence.
- `FinOps Framework` and `Unit Economics` define the operating model and decision language.

What is still missing is one portable artifact that binds:

- the intended business outcome
- the allowed cost and carbon envelope
- the residency and policy boundaries
- the required runtime evidence
- the reconciliation path back to unit economics and leadership decisions

That is the role of TVC.

## Design Goals

- Git-friendly: contracts should be reviewed like code and infrastructure changes.
- Standard-composable: TVC should reference existing standards instead of replacing them.
- Policy-enforceable: CI/CD and runtime controls should be able to validate contract fields.
- Auditable: contract changes and runtime receipts should support evidence-grade review.
- Business-readable: finance, product, engineering, and leadership should share one artifact.

## Non-Goals

- TVC does not replace `FOCUS`, `OpenCost`, `OpenSLO`, or `CloudEvents`.
- TVC does not define a new provider billing schema.
- TVC does not require one orchestration engine, policy engine, or event bus.
- TVC v0.1 does not attempt full ESG-grade carbon accounting or advanced outcome-causality proof.

## Artifact Model

TVC v0.1 defines two artifacts:

1. `Technology Value Contract`
   - YAML or JSON
   - checked into the repository
   - reviewed before deployment

2. `Execution Receipt`
   - JSON
   - emitted at admission time or during runtime on a declared cadence
   - formatted as a CloudEvent-compatible envelope in v0.1

## Contract Structure

The canonical schema lives at:

- `contracts/schemas/technology_value_contract.schema.json`

The example manifest lives at:

- `contracts/examples/technology_value_contract.example.yaml`

### Required Top-Level Sections

- `apiVersion`
- `kind`
- `metadata`
- `subject`
- `intent`
- `unit_economics`
- `guardrails`
- `measurement`
- `governance`

### Required Semantics

TVC v0.1 requires each contract to declare:

- one stable subject:
  - service, workload, pipeline, model, or product-capability
- one primary unit-economics metric:
  - for example `cost_per_request`, `cost_per_analysis`, or `cost_per_token`
- at least one business-value hypothesis:
  - the explicit reason the spend exists
- explicit cost guardrails:
  - at minimum currency, monthly limit, and alert threshold
- explicit compliance boundaries:
  - data residency and applicable frameworks
- measurement sources:
  - the cost, allocation, telemetry, and business systems that provide evidence
- governance settings:
  - approvers, enforcement mode, and receipt cadence

### Optional But Strongly Recommended Sections

- `guardrails.carbon`
- `guardrails.performance`
- `guardrails.commitment`
- `extensions`

For production workloads, carbon and performance guardrails should be treated as normal, not exceptional.

## Execution Receipt Structure

The canonical schema lives at:

- `contracts/schemas/execution_receipt.schema.json`

The example receipt lives at:

- `contracts/examples/execution_receipt.example.json`

## Repo Placement

Repository convention for this draft:

- human-readable standard and product explanation stays in `docs/`
- machine-readable contract artifacts live in `contracts/`
- operational `.yml` and `.yaml` files stay with the subsystem that owns them
  - for example `prometheus/`, `grafana/`, and `cloudformation/`

Receipts are runtime evidence envelopes. In v0.1 they are modeled as CloudEvents-shaped JSON with:

- `specversion`
- `id`
- `source`
- `type`
- `subject`
- `time`
- `dataschema`
- `datacontenttype`
- `data`

The `data` section records:

- the receipt `phase` (`admission` or `runtime`)
- the contract reference
- the deployment or runtime subject
- the evaluation window
- actual cost, carbon, unit-economics, and performance values
- pass/warn/fail evaluations
- anomaly indicators
- provenance and evidence references

For admission receipts, not every runtime metric will be measured yet. In that case:

- unit-economics evidence can represent the admission outcome for the governed pipeline
- cost and carbon statuses can remain `not_measured`
- the receipt can include an `admission` block with readiness flags and blocker lists

## Normative Rules

The following rules are the intended v0.1 contract surface:

1. A production workload SHOULD have exactly one active TVC per deployment subject and environment.
2. A TVC MUST change `metadata.version` when the contract semantics change materially.
3. A TVC MUST define at least one primary unit-economics metric and one business-value hypothesis.
4. A TVC MUST define cost and compliance guardrails.
5. A receipt MUST reference the contract `name` and `version` it is evaluating.
6. A receipt MUST identify the deployment or runtime unit that produced the evidence.
7. Receipt producers SHOULD emit CloudEvents 1.0 envelopes.
8. Cost actuals SHOULD reconcile to a FOCUS-aligned ledger when available.
9. Shared compute allocation SHOULD reference OpenCost or an equivalent allocation substrate when relevant.
10. Performance objectives SHOULD reference OpenSLO artifacts when the organization uses SLO-as-code.

## Relationship To Existing Standards

TVC is intentionally designed as a composition layer:

- `FOCUS` answers: what cost and usage happened.
- `OpenCost` answers: how shared cloud-native spend was allocated.
- `OpenSLO` answers: what reliability and latency objectives were promised.
- `CloudEvents` answers: how runtime evidence is carried across systems.
- `TVC` answers: what the spend was supposed to achieve, what guardrails applied, and whether the result stayed inside the declared contract.

## Reference Validation Command

The repo validator for the draft artifacts is:

```bash
uv run python3 scripts/verify_technology_value_contract.py \
  --contract-path contracts/examples/technology_value_contract.example.yaml \
  --receipt-path contracts/examples/execution_receipt.example.json
```

Environment-scoped managed deployment contracts currently live at:

- `contracts/examples/unified-platform-deploy-staging.yaml`
- `contracts/examples/unified-platform-deploy-production.yaml`

## Suggested Adoption Path

### Phase 1

- declare TVCs for a small number of production services
- validate them in CI
- emit advisory-only receipts

### Phase 2

- block high-risk changes on contract violations
- join receipts to FOCUS and allocation evidence
- expose intent-versus-actual reconciliation in product and finance workflows

### Phase 3

- publish the spec publicly
- stabilize the namespace and versioning strategy
- invite ecosystem feedback as a complement to FOCUS and OpenCost

## Sources

- FinOps Framework: https://www.finops.org/framework/
- FinOps Unit Economics: https://www.finops.org/framework/capabilities/unit-economics/
- FOCUS: https://focus.finops.org/
- OpenCost: https://opencost.io/
- OpenSLO: https://openslo.com/
- CloudEvents: https://cloudevents.io/
