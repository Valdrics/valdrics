# ADR-0007: Redis-Backed Circuit Breakers for Distributed Runtime Guards

- Date: 2026-03-06
- Status: Superseded by the unified managed GCP runtime contract on 2026-04-11
- Owners: Platform, Reliability, Security

## Context

At the time of this decision, runtime protection required breaker state that was
consistent across multiple workers and execution surfaces (API, scheduler, and
async jobs). Pure in-memory breakers were simple but diverged across processes
and could not enforce shared fail-open/fail-closed behavior in distributed
deployments.

## Decision

The interim decision was to use Redis-backed breaker state for distributed
control paths where cross-worker consistency was required, while retaining
process-local guards where deployment constraints explicitly allowed
single-worker behavior.

Decision details:

- Redis-backed breakers were the default for distributed enforcement and
  reliability-sensitive flows.
- In-memory breakers remain acceptable only where architecture explicitly enforces
  single-worker constraints and fail-closed validation.

## Consequences

- Historical benefits:
  - Consistent breaker state across workers and nodes.
  - Stronger safety against split-brain breaker behavior.
  - Better observability and incident triage for degraded dependencies.
- Current managed-platform consequence:
  - The supported Cloud Run profile now runs one API process per instance,
    binds the injected `PORT`, and keeps breaker state process-local as an
    internal implementation detail.
  - Redis-backed breaker state is no longer part of the supported managed GCP
    runtime contract.

## Operational Guardrails

- Historical guardrails:
  - Fail closed when Redis is required but unavailable for protected control paths.
  - Emit explicit telemetry for breaker transitions and Redis-unavailable fallback.
- Current guardrails:
  - Validate the Cloud Run managed profile as process-local breaker state only.
  - Scale via Cloud Run request concurrency and instance counts, not worker fan-out.
