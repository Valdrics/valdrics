# ADR-0009: Celery + Redis over FastAPI BackgroundTasks for Core Orchestration

- Date: 2026-03-06
- Status: Superseded by the unified managed GCP orchestration stack on 2026-04-11
- Owners: Platform, Reliability, Data Engineering

## Context

At the time of this decision, core workflows required scheduled and
asynchronous execution with retry controls, state tracking, and separation from
request lifecycles.

FastAPI `BackgroundTasks` is suitable for lightweight request-adjacent work but
does not provide the same distributed queue semantics, durable retries, and
operational tooling expected for long-running orchestration.

## Decision

The interim decision was to use Celery with Redis-backed brokering/result
coordination for core scheduled and asynchronous orchestration paths.

Rationale:

- At the time, Celery provided bounded retries, delayed execution, and worker isolation.
- At the time, Celery provided queue-level operational visibility that FastAPI `BackgroundTasks` could not.
- The supported replacement is now:
  - Cloud Tasks for request-adjacent async work
  - Cloud Scheduler for scheduled dispatch
  - Cloud Run Jobs for long-running batch work

## Consequences

- Historical benefits:
  - More robust scheduler and job execution model for enterprise operations.
  - Reduced risk of request-path starvation from heavy background work.
- Current managed-platform consequence:
  - Celery and Redis are no longer part of the supported production runtime.
  - Managed orchestration now relies on Cloud Tasks, Cloud Scheduler, and Cloud Run Jobs.

## Review Trigger

This review trigger has been reached and closed: the managed orchestration
platform now supersedes Celery/Redis operations in the supported runtime.
