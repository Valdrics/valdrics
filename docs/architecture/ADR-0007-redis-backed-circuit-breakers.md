# ADR-0007: Redis-Backed Circuit Breakers for Distributed Runtime Guards

- Date: 2026-03-06
- Status: Accepted
- Owners: Platform, Reliability, Security

## Context

Runtime protection requires breaker state that is consistent across workers and
execution surfaces (API, scheduler, and async jobs). Pure in-memory breakers are
simple but diverge across processes and cannot enforce shared fail-open/fail-closed
behavior in distributed deployments.

## Decision

Use Redis-backed breaker state for distributed control paths where cross-worker
consistency is required, while retaining process-local guards where deployment
constraints explicitly allow single-worker behavior.

Decision details:

- Redis-backed breakers are the default for distributed enforcement and
  reliability-sensitive flows.
- In-memory breakers remain acceptable only where architecture explicitly enforces
  single-worker constraints and fail-closed validation.

## Consequences

- Positive:
  - Consistent breaker state across workers and nodes.
  - Stronger safety against split-brain breaker behavior.
  - Better observability and incident triage for degraded dependencies.
- Tradeoffs:
  - Redis availability and configuration become part of runtime safety posture.
  - Misconfiguration risk shifts from code-only to distributed system operations.

## Operational Guardrails

- Fail closed when Redis is required but unavailable for protected control paths.
- Emit explicit telemetry for breaker transitions and Redis-unavailable fallback.
- Validate environment configuration for breaker thresholds and recovery windows.

