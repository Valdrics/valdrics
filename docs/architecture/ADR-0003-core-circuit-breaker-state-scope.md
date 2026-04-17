# ADR-0003: Core Circuit Breaker State Scope

- Date: 2026-02-20
- Status: Superseded by archived ADR-0007 on 2026-03-06; replaced for the supported runtime by the unified managed GCP contract on 2026-04-11

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
- The supported managed GCP runtime no longer exposes `WEB_CONCURRENCY`; Cloud
  Run owns per-instance concurrency and the API container binds the injected
  `PORT`.
- The supported managed GCP runtime now treats breaker state as an internal
  process-local implementation detail instead of an exposed runtime knob.
- Use `docs/DEPLOYMENT.md` and `scheduler_orchestration_sequence.md` as the
  current managed runtime authority.
