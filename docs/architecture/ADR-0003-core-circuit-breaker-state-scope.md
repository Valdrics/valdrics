# ADR-0003: Core Circuit Breaker State Scope

- Date: 2026-02-20
- Status: Superseded by ADR-0007 on 2026-03-06

## Context

At the time of this decision, `app/shared/core/circuit_breaker.py` maintained
breaker state in-process. In multi-worker deployments, this could create
divergent state per worker.

## Decision

The interim control was to keep production safe by enforcing:

- `WEB_CONCURRENCY` must be `1` in `staging`/`production`.
- Multi-worker deployment is blocked until distributed breaker state is implemented.

This fail-closed guard is implemented in `app/shared/core/config.py`.

## Consequences

- This ADR remains useful as historical context for why the single-worker guard
  existed.
- Production defaults now assume Redis-backed distributed breaker state instead
  of a process-local constraint.
- Use ADR-0007 as the current runtime authority.
