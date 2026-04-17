# Valdrics Unified Platform Redesign Plan

## Summary

Redesign Valdrics to a single managed operating model built around:

- frontend on Cloudflare Pages/Workers
- database, auth, and storage on Supabase
- backend API, async execution, scheduling, secrets, and release artifacts on GCP

## Current Status (Updated 2026-04-16)

- Phase 0: Complete. The repo now centers on the unified GCP + Cloudflare + Supabase contract, with Terraform/deployment artifacts and managed-runtime docs aligned to that target.
- Phase 1: Complete. Backend orchestration is abstracted behind managed-runtime ports/adapters instead of direct Celery/APScheduler ownership in the supported path.
- Phase 2: Complete in the repo. Cloud Tasks, Cloud Scheduler, and Cloud Run Jobs execution paths, internal handlers, and deployment generators are implemented and covered.
- Phase 3: In progress. Active Celery/Koyeb production dependencies have been removed from the supported profile, the repo-owned enforcement release packet is green, the enterprise TDD/release gate is green, and the repo-owned managed release readiness verifier is green for both `staging` and `production`, but live staging/production cutover evidence and final release-operations sign-off are environment events that are not yet recorded here as completed facts, so they remain the only open completion gates for this phase.
- Phase 4: Complete in the repo. The supported managed GCP profile no longer exposes the retired shared-state Redis and distributed-breaker knobs, active env templates/generators/workflows/Terraform defaults emit only the supported Cloudflare-fronted contract, public rate limiting is normalized to the Cloudflare-only posture, active docs now use current Cloudflare WAF terminology and describe breaker state as an internal process-local detail instead of a runtime toggle, managed runtime logging now follows the Cloud Run integrated structured stdout/stderr path instead of a separate client-library export branch, the active cache surface has been simplified to managed-profile cacheless behavior plus process-local memory outside that profile rather than an external Upstash/Redis contract, the Python runtime dependency set, currency-cache internals, and live status UI no longer carry a Redis-specific contract, ElastiCache analysis paths no longer silently assume Redis when engine metadata is absent, the release pipeline now refreshes the codebase audit report and runs `verify_managed_release_readiness.py` from the reusable deploy workflow, the managed deployment artifact generator now preserves only the supported release bundle plus operator handoff outputs instead of carrying retired runtime-specific filename contracts, the last live self-managed Helm/Kubernetes reference, legacy AWS/EKS/Redis Terraform modules, provider-specific AWS tenant smoke flow, stale dated audit/production-fixes report packs, duplicate incident-response docs, unreferenced legacy AWS/CI-CD guide docs, non-canonical identity/discovery/persona notes, and generated change-categorization/inventory archive noise have been archived out of the active tree or removed, and the remaining compliance/evidence cleanup has been consolidated onto canonical undated paths with archive guardrails for historical material.

## What Is Actually Left

The remaining work is now environment-side rather than repo-side:

- deploy `staging` on the managed GCP + Cloudflare + Supabase stack
- run parity smoke, workload, and rollback validation against that live staging environment
- cut staging traffic fully to the managed stack
- promote the same immutable artifact/process to `production`
- capture staging/production cutover evidence in the canonical operator packet
- obtain final release-operations sign-off

Non-blocking repo hygiene may still be done opportunistically, but it is no longer a plan completion gate. Candidate examples include archiving non-contract product/reference docs that are not used by runtime, verification, or operator workflows.

The plan optimizes for the constraints you called out:

- one source of truth for infra
- one deployment pipeline
- one environment model
- one observability model
- one runbook set

The target state is a **single modular-monolith backend** with managed platform primitives, not a microservices split:

- Cloud Run service for the API
- Cloud Tasks for queued async work
- Cloud Scheduler for cron/scheduled triggers
- Cloud Run Jobs for long-running scans/sweeps/batch work
- Artifact Registry for backend images
- Secret Manager for runtime secrets
- Terraform as the infrastructure control plane
- GitHub Actions as the only deployment pipeline

## Key Changes

### 1. Operating model and source of truth

- Make **Terraform** the only source of truth for cloud infrastructure across GCP, Cloudflare, and Supabase project/settings where the provider supports them.
- Keep **Alembic + SQL migrations** as the only source of truth for database schema, RLS, indexes, and data migrations.
- Remove Koyeb as the supported runtime target; move Helm/EKS to archived reference material because it is not part of the active delivery plan.
- Replace GHCR-based backend promotion with **Artifact Registry** image promotion on GCP.
- Standardize environments to:
  - `local`
  - `staging`
  - `production`
- Use separate projects/accounts per environment boundary:
  - separate GCP projects for `staging` and `production`
  - separate Supabase projects for `staging` and `production`
  - Cloudflare Pages preview/staging and production environments mapped explicitly

### 2. One deployment pipeline

- Use **GitHub Actions** as the only release pipeline for both frontend and backend.
- Pipeline stages:
  - validate + test
  - build backend image once
  - push backend image to Artifact Registry
  - build/deploy frontend to Cloudflare
  - run Terraform plan/apply for environment infra
  - deploy Cloud Run service + Cloud Run Jobs revision
  - apply migrations
  - run staging smoke checks
  - promote the exact same backend artifact to production
- Do not allow branch-tracked deploys or manual dashboard-driven infra drift.
- Keep release promotion immutable: one build artifact promoted through environments.

### 3. One backend runtime model

- Retain the backend as a modular monolith in `app/modules`, but replace runtime orchestration primitives:
  - Celery -> Cloud Tasks / Cloud Run Jobs
  - Redis-backed async queue -> Cloud Tasks
  - API-embedded APScheduler -> Cloud Scheduler
  - Koyeb service topology -> Cloud Run + Cloud Run Jobs
- Introduce explicit orchestration ports in the backend:
  - `AsyncTaskDispatcher`
  - `ScheduledTriggerDispatcher`
  - `BatchJobLauncher`
- Provide two adapter layers during migration:
  - current adapter set: Celery / Redis / APScheduler
  - target adapter set: Cloud Tasks / Cloud Scheduler / Cloud Run Jobs
- Migrate modules to call the ports instead of calling Celery or scheduler primitives directly.
- Remove Redis as a required production dependency in the target state unless a later, narrowly-scoped need remains after migration.
- Keep the current public API shape stable during migration, especially:
  - `/api/v1/jobs`
  - `/api/v1/zombies`
  - `/api/v1/savings`
  - `/api/v1/settings/*`
- Keep the existing SSE jobs stream initially for compatibility; do not redesign job UX to Realtime in phase 1.

### 4. One environment model

- `local`:
  - local Python/uv workflow
  - local or ephemeral database as currently used for tests/dev
  - no production-like cloud orchestration requirements
- `staging`:
  - same topology as production
  - lower quotas and smaller Cloud Run settings
  - same auth/storage/database model as production
- `production`:
  - identical topology and deployment mechanics as staging
  - only scale knobs differ
- No separate “special” deploy path per environment. Same pipeline, same artifact model, same service graph.

### 5. One observability model

- Use **OpenTelemetry** as the single instrumentation standard across backend code.
- Use **Google Cloud Operations** as the single primary production observability backend:
  - Cloud Logging
  - Cloud Monitoring
  - Cloud Trace
  - alerting policies
- Remove the strict requirement for an external OTLP collector endpoint in the GCP-managed profile; switch to a GCP-native telemetry sink for the target state.
- Treat Sentry as migration-only if retained temporarily; target state is one operational pane, not parallel alerting systems.
- Keep internal metrics semantics, but align them to the Cloud Run/GCP model instead of Koyeb/Helm assumptions.
- Standardize structured event names, task IDs, job IDs, and request correlation across API, task handlers, and batch jobs.

## Important API / Interface / Type Changes

- Add internal-only task endpoints for Cloud Tasks delivery, authenticated by Google-signed identity:
  - `/internal/tasks/...`
- Add internal-only scheduler trigger endpoints for Cloud Scheduler where direct job invocation is not used:
  - `/internal/scheduler/...`
- Add batch job entrypoints for Cloud Run Jobs execution:
  - CLI or command-based entrypoints for scans, sweeps, retention, reconciliation, and reporting jobs
- Replace deployment/runtime config contracts:
  - remove Koyeb-specific deploy bundle outputs from the active contract
  - add Terraform outputs and environment manifests for:
    - Cloud Run service
    - Cloud Run Jobs
    - Cloud Tasks queues
    - Cloud Scheduler jobs
    - Secret Manager bindings
    - Artifact Registry repositories
    - Cloudflare Pages config
    - Supabase project/settings references
- Update config validation so the target GCP profile requires:
  - GCP project/service-account settings
  - Secret Manager access
  - Supabase runtime settings
  - Cloudflare public frontend settings
- Remove strict production dependence on:
  - Redis
  - Celery broker/result backend
  - API-startup APScheduler

## Migration Plan

### Phase 0: Platform contract and IaC foundation

- Add Terraform modules for:
  - GCP project/runtime
  - Artifact Registry
  - Cloud Run service
  - Cloud Run Jobs
  - Cloud Tasks
  - Cloud Scheduler
  - Secret Manager
  - service accounts and IAM
  - Cloudflare Pages/DNS bindings
  - Supabase project/settings resources where supported
- Freeze Koyeb as legacy path in docs only; do not extend it further.
- Replace deployment docs/runbooks with a single GCP + Cloudflare + Supabase runbook set.

### Phase 1: Runtime abstraction inside the backend

- Introduce orchestration interfaces and move all direct Celery/scheduler usage behind adapters.
- Separate work into three categories:
  - synchronous request-path work
  - queued async work
  - long-running batch work
- Classify all current Celery tasks and APScheduler jobs into those categories.
- Make the internal orchestration transport swappable without changing module business logic.

### Phase 2: GCP execution adapters

- Implement Cloud Tasks adapter for request-adjacent async work.
- Implement Cloud Scheduler adapter for scheduled invocations.
- Implement Cloud Run Jobs adapter for heavy scans, sweeps, and long-running jobs.
- Add authenticated internal handlers for Cloud Tasks and scheduler requests.
- Keep public API behavior stable while swapping the execution backend underneath.

### Phase 3: Cutover and removal

- Deploy staging on the new stack.
- Run parity smoke and workload checks.
- Cut staging traffic fully to the GCP-managed backend.
- Promote the same artifact/process to production.
- Remove active Celery/Redis/Koyeb production dependencies from the supported profile.
- Archive or delete obsolete deployment generators and runbooks after successful production cutover.

### Phase 4: Cleanup and simplification

- Remove dead config keys and legacy runtime validators.
- Remove legacy Koyeb deployment artifacts from the active operator flow.
- Remove Redis/Celery operational docs if no remaining production dependency exists.
- Consolidate docs to one architecture overview, one deploy guide, one rollback guide, and one disaster-recovery guide.

## Test Plan

- Unit tests for orchestration ports and both adapter families.
- Integration tests for:
  - authenticated Cloud Tasks delivery
  - scheduler-triggered job dispatch
  - Cloud Run Job launch request generation
  - idempotent task replay and duplicate suppression
- Regression tests proving public APIs remain stable during migration:
  - jobs endpoints
  - zombie/remediation flow
  - savings flow
  - auth/session flows
- Staging validation:
  - provider onboarding and remediation smoke flows still pass end to end
  - background execution works without Redis/Celery
  - scheduled sweeps run through Cloud Scheduler / Cloud Run Jobs
  - observability signals land in the new single telemetry backend
- Deployment validation:
  - Terraform plan clean for each environment
  - one GitHub Actions pipeline can deploy both frontend and backend
  - immutable artifact promotion from staging to production
- Operational tests:
  - rollback to prior Cloud Run revision
  - failed task replay
  - failed job retry
  - migration rollback/forward compatibility
  - secret rotation through Secret Manager
  - environment drift detection

## Acceptance Criteria

- One Terraform-based infra control plane is active for supported environments.
- One GitHub Actions deployment pipeline is the only supported deploy path.
- Staging and production use the same topology and deployment mechanics.
- Backend no longer relies on Koyeb, Celery, or Redis in the supported production profile.
- OpenTelemetry + Google Cloud Operations is the single production observability path.
- Public API behavior remains compatible for dashboard and tenant workflows during migration.
- provider onboarding and remediation flows pass on the new stack before production cutover.

## Assumptions and Defaults

- Chosen target stack is fixed:
  - Cloudflare for frontend
  - Supabase for Postgres/Auth/Storage
  - GCP for backend runtime and operational platform
- The backend remains a modular monolith, not a microservices decomposition.
- Supabase Auth remains the auth model; no auth-provider replacement is included.
- Supabase Storage remains the file/object storage model; no GCS migration is included.
- SSE job streaming remains in scope for compatibility in the first migration; no Realtime rewrite in phase 1.
- Terraform is the infrastructure source of truth; Alembic/SQL migrations are the schema source of truth.
- GitHub Actions remains the one deployment pipeline.
