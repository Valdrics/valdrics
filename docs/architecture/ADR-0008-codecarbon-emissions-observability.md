# ADR-0008: CodeCarbon for Carbon Emissions Observability

- Date: 2026-03-06
- Status: Accepted
- Owners: Sustainability, Platform, Finance

## Context

The platform reports carbon and efficiency outcomes as a product capability.
Engineering needs a repeatable, auditable mechanism to estimate compute-related
emissions for CI/runtime evidence and trend reporting.

## Decision

Adopt CodeCarbon as the baseline emissions instrumentation component for
engineering telemetry and FinOps sustainability reporting.

Rationale:

- Practical integration:
  - CodeCarbon can be integrated into existing Python CI/runtime workflows.
- Evidence alignment:
  - Produces structured signals usable in governance evidence packs and
    operational reporting.
- Cost/complexity:
  - Lower implementation overhead than maintaining bespoke emissions calculators.

## Consequences

- Positive:
  - Consistent emissions telemetry for engineering workflows.
  - Better traceability for sustainability-related reporting claims.
- Tradeoffs:
  - Estimates depend on model assumptions and environment fidelity.
  - Requires calibration/review discipline as workload patterns change.

## Review Trigger

Re-open this decision when either condition occurs:

1. Product/compliance scope requires a higher-assurance emissions methodology.
2. Existing estimates diverge materially from validated operational measurements.

