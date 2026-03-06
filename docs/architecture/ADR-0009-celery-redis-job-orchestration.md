# ADR-0009: Celery + Redis over FastAPI BackgroundTasks for Core Orchestration

- Date: 2026-03-06
- Status: Accepted
- Owners: Platform, Reliability, Data Engineering

## Context

Core workflows require scheduled and asynchronous execution with retry controls,
state tracking, and separation from request lifecycles.

FastAPI `BackgroundTasks` is suitable for lightweight request-adjacent work but
does not provide the same distributed queue semantics, durable retries, and
operational tooling expected for long-running orchestration.

## Decision

Use Celery with Redis-backed brokering/result coordination for core scheduled and
asynchronous orchestration paths.

Rationale:

- Reliability and control:
  - Supports bounded retries, delayed execution, and worker isolation.
- Operational visibility:
  - Better observability and queue-level control for production incidents.
- Separation of concerns:
  - Keeps heavy/background execution independent from request thread lifecycles.

## Consequences

- Positive:
  - More robust scheduler and job execution model for enterprise operations.
  - Reduced risk of request-path starvation from heavy background work.
- Tradeoffs:
  - Additional distributed runtime components to operate (workers + Redis).
  - Requires stricter configuration management and health monitoring.

## Review Trigger

Re-open this decision when either condition occurs:

1. Workload shape becomes simple enough that distributed queueing is unnecessary.
2. A managed orchestration platform supersedes current Celery/Redis operations.

