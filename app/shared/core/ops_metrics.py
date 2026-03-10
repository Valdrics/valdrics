"""Operational and performance Prometheus metrics for Valdrics."""

from typing import Any

from prometheus_client import Counter, Histogram, Gauge
import structlog
import sys
from app.shared.core import ops_metrics_runtime as _ops_metrics_runtime
from app.shared.core import ops_metrics_recorders as _ops_metrics_recorders

COST_RECORD_RETENTION_LAST_RUN = _ops_metrics_runtime.COST_RECORD_RETENTION_LAST_RUN
COST_RECORD_RETENTION_PURGED_TOTAL = _ops_metrics_runtime.COST_RECORD_RETENTION_PURGED_TOTAL
AUDIT_LOG_RETENTION_LAST_RUN = _ops_metrics_runtime.AUDIT_LOG_RETENTION_LAST_RUN
AUDIT_LOG_RETENTION_PURGED_TOTAL = _ops_metrics_runtime.AUDIT_LOG_RETENTION_PURGED_TOTAL
RUNTIME_CARBON_EMISSIONS_LAST_RUN = _ops_metrics_runtime.RUNTIME_CARBON_EMISSIONS_LAST_RUN
RUNTIME_CARBON_EMISSIONS_TOTAL = _ops_metrics_runtime.RUNTIME_CARBON_EMISSIONS_TOTAL


def _sync_runtime_metric_exports() -> None:
    setattr(_ops_metrics_runtime, "structlog", structlog)
    _ops_metrics_runtime.COST_RECORD_RETENTION_LAST_RUN = COST_RECORD_RETENTION_LAST_RUN
    _ops_metrics_runtime.COST_RECORD_RETENTION_PURGED_TOTAL = COST_RECORD_RETENTION_PURGED_TOTAL
    _ops_metrics_runtime.AUDIT_LOG_RETENTION_LAST_RUN = AUDIT_LOG_RETENTION_LAST_RUN
    _ops_metrics_runtime.AUDIT_LOG_RETENTION_PURGED_TOTAL = AUDIT_LOG_RETENTION_PURGED_TOTAL
    _ops_metrics_runtime.RUNTIME_CARBON_EMISSIONS_LAST_RUN = RUNTIME_CARBON_EMISSIONS_LAST_RUN
    _ops_metrics_runtime.RUNTIME_CARBON_EMISSIONS_TOTAL = RUNTIME_CARBON_EMISSIONS_TOTAL


def record_runtime_carbon_emissions(emissions_kg: float | None) -> None:
    _sync_runtime_metric_exports()
    _ops_metrics_runtime.record_runtime_carbon_emissions(emissions_kg)


def record_cost_retention_purge(tenant_tier: str, deleted_count: int) -> None:
    _sync_runtime_metric_exports()
    _ops_metrics_runtime.record_cost_retention_purge(tenant_tier, deleted_count)


def record_audit_log_retention_purge(deleted_count: int) -> None:
    _sync_runtime_metric_exports()
    _ops_metrics_runtime.record_audit_log_retention_purge(deleted_count)


def _normalize_metric_label(value: Any, *, default: str = "unknown") -> str:
    normalized = str(value or "").strip().lower()
    return normalized or default

# --- Roadmap Compatibility Metrics ---
STUCK_JOB_COUNT = Gauge(
    "stuck_job_count", "Current number of jobs detected as stuck in scheduler sweeps"
)

LLM_BUDGET_BURN_RATE = Gauge(
    "llm_budget_burn_rate",
    "Average monthly LLM budget burn rate percentage across tenants",
)

RLS_ENFORCEMENT_LATENCY = Histogram(
    "rls_enforcement_latency",
    "Latency in seconds to apply RLS tenant context in DB session setup",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1),
)

# --- Queue & Scheduling Metrics ---
BACKGROUND_JOBS_ENQUEUED = Counter(
    "valdrics_ops_jobs_enqueued_total",
    "Total number of background jobs enqueued",
    ["job_type", "priority"],
)

BACKGROUND_JOBS_PENDING = Gauge(
    "valdrics_ops_jobs_pending_count",
    "Current number of pending background jobs in the database",
    ["job_type"],
)

BACKGROUND_JOB_DURATION = Histogram(
    "valdrics_ops_job_duration_seconds",
    "Duration of background job execution",
    ["job_type", "status"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800),
)

BACKGROUND_JOBS_STALE_RUNNING_RECOVERED_TOTAL = Counter(
    "valdrics_ops_background_jobs_stale_running_recovered_total",
    "Total number of stale RUNNING background jobs recovered after lock timeout",
    ["job_type", "outcome"],
)

BACKGROUND_JOBS_DEAD_LETTERED_TOTAL = Counter(
    "valdrics_ops_background_jobs_dead_lettered_total",
    "Total number of background jobs moved to dead-letter state",
    ["job_type", "reason"],
)

BACKGROUND_JOBS_OVERDUE_PENDING = Gauge(
    "valdrics_ops_background_jobs_overdue_pending_count",
    "Current number of pending background jobs whose scheduled time is overdue",
)

AUDIT_LOG_RETENTION_FAILURES_TOTAL = Counter(
    "valdrics_ops_audit_log_retention_failures_total",
    "Total number of audit-log retention sweep failures",
    ["operation"],
)

SCHEDULER_INLINE_FALLBACK_TOTAL = Counter(
    "valdrics_scheduler_inline_fallback_total",
    "Total number of scheduler inline fallback executions by job and outcome",
    ["job_name", "outcome"],
)

# --- Scan Performance Metrics ---
SCAN_LATENCY = Histogram(
    "valdrics_ops_scan_latency_seconds",
    "Latency of cloud resource scans",
    ["provider", "region"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

SCAN_TIMEOUTS = Counter(
    "valdrics_ops_scan_timeouts_total",
    "Total number of scan timeouts",
    ["level", "provider"],  # 'plugin', 'region', 'overall'
)

SCAN_SUCCESS_TOTAL = Counter(
    "valdrics_ops_scan_success_total",
    "Total number of successful scans",
    ["provider", "region"],
)

SCAN_FAILURE_TOTAL = Counter(
    "valdrics_ops_scan_failure_total",
    "Total number of failed scans",
    ["provider", "region", "error_type"],
)

FINOPS_PROVIDER_FAILURES_TOTAL = Counter(
    "valdrics_ops_finops_provider_failures_total",
    "Total number of provider-specific failures encountered during FinOps background analysis",
    ["provider", "error_type"],
)

# --- Cloud API Cost Governance ---
CLOUD_API_CALLS_TOTAL = Counter(
    "valdrics_ops_cloud_api_calls_total",
    "Total expensive cloud API calls executed by the optimization engine",
    ["provider", "api"],
)

CLOUD_API_BUDGET_DECISIONS_TOTAL = Counter(
    "valdrics_ops_cloud_api_budget_decisions_total",
    "Budget-governor decisions for expensive cloud API calls",
    ["provider", "api", "decision"],  # allow | deny | would_deny
)

CLOUD_API_BUDGET_REMAINING = Gauge(
    "valdrics_ops_cloud_api_budget_remaining_calls",
    "Remaining expensive cloud API call budget for the current UTC day",
    ["provider", "api"],
)

CLOUD_API_ESTIMATED_COST_USD = Counter(
    "valdrics_ops_cloud_api_estimated_cost_usd_total",
    "Estimated cloud API cost exposure in USD from expensive telemetry calls",
    ["provider", "api"],
)

# --- API & Remediation Metrics ---
API_REQUESTS_TOTAL = Counter(
    "valdrics_ops_api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

API_REQUEST_DURATION = Histogram(
    "valdrics_ops_api_request_duration_seconds",
    "Duration of API requests",
    ["method", "endpoint"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)

API_ERRORS_TOTAL = Counter(
    "valdrics_ops_api_errors_total",
    "Total number of API errors by status code and path",
    ["path", "method", "status_code"],
)

LANDING_TELEMETRY_EVENTS_TOTAL = Counter(
    "valdrics_ops_landing_telemetry_events_total",
    "Landing telemetry events received by event, section, and funnel stage",
    ["event_name", "section", "funnel_stage"],
)

LANDING_TELEMETRY_INGEST_OUTCOMES_TOTAL = Counter(
    "valdrics_ops_landing_telemetry_ingest_outcomes_total",
    "Landing telemetry ingestion outcomes",
    ["outcome"],  # accepted|rejected_timestamp
)

ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL = Counter(
    "valdrics_ops_enforcement_reservation_reconciliations_total",
    "Total reservation reconciliation actions in the enforcement control plane",
    ["trigger", "status"],  # trigger: manual|auto, status: matched|overage|savings|auto_release
)

ENFORCEMENT_RESERVATION_DRIFT_USD_TOTAL = Counter(
    "valdrics_ops_enforcement_reservation_drift_usd_total",
    "Absolute reservation reconciliation drift observed in USD",
    ["direction"],  # direction: overage|savings
)

ENFORCEMENT_APPROVAL_TOKEN_EVENTS_TOTAL = Counter(
    "valdrics_ops_enforcement_approval_token_events_total",
    "Approval token security events in enforcement workflow",
    ["event"],  # consumed, replay_detected, expired, and mismatch classifications
)

ENFORCEMENT_RECONCILIATION_SWEEP_RUNS_TOTAL = Counter(
    "valdrics_ops_enforcement_reconciliation_sweep_runs_total",
    "Scheduled enforcement reconciliation sweep runs by outcome",
    ["status"],  # success | failure | skipped_disabled
)

ENFORCEMENT_RECONCILIATION_ALERTS_TOTAL = Counter(
    "valdrics_ops_enforcement_reconciliation_alerts_total",
    "Enforcement reconciliation alerts emitted by alert type and severity",
    ["alert_type", "severity"],  # sla_release|drift_exception, warning|error
)

ENFORCEMENT_GATE_DECISIONS_TOTAL = Counter(
    "valdrics_ops_enforcement_gate_decisions_total",
    "Enforcement gate decisions by source, decision type, and evaluation path",
    ["source", "decision", "path"],  # path: normal|failsafe
)

ENFORCEMENT_GATE_DECISION_REASONS_TOTAL = Counter(
    "valdrics_ops_enforcement_gate_decision_reasons_total",
    "Enforcement gate decision reason-code distribution",
    ["source", "reason"],
)

ENFORCEMENT_GATE_LATENCY_SECONDS = Histogram(
    "valdrics_ops_enforcement_gate_latency_seconds",
    "End-to-end latency of enforcement gate evaluation",
    ["source", "path"],  # path: normal|failsafe
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

ENFORCEMENT_GATE_FAILURES_TOTAL = Counter(
    "valdrics_ops_enforcement_gate_failures_total",
    "Enforcement gate failures before deterministic fail-safe fallback",
    ["source", "failure_type"],  # timeout|evaluation_error|lock_timeout|lock_contended
)

ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL = Counter(
    "valdrics_ops_enforcement_gate_lock_events_total",
    "Enforcement gate serialization lock events by source and event",
    ["source", "event"],  # acquired|contended|timeout|not_acquired|error
)

ENFORCEMENT_GATE_LOCK_WAIT_SECONDS = Histogram(
    "valdrics_ops_enforcement_gate_lock_wait_seconds",
    "Wait time spent acquiring the enforcement gate serialization lock",
    ["source", "outcome"],  # acquired|timeout|error
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

ENFORCEMENT_EXPORT_EVENTS_TOTAL = Counter(
    "valdrics_ops_enforcement_export_events_total",
    "Enforcement export events by artifact and outcome",
    ["artifact", "outcome"],  # parity|archive|bundle, success|mismatch|rejected_limit
)

ENFORCEMENT_APPROVAL_QUEUE_BACKLOG = Gauge(
    "valdrics_ops_enforcement_approval_queue_backlog",
    "Current number of pending approvals visible to the caller",
    ["viewer_role"],
)

TURNSTILE_VERIFICATION_EVENTS_TOTAL = Counter(
    "valdrics_ops_turnstile_verification_events_total",
    "Turnstile verification events by surface and outcome",
    ["surface", "outcome"],
)

LANDING_FUNNEL_WEEKLY_CONVERSION_RATE = Gauge(
    "valdrics_ops_landing_funnel_weekly_conversion_rate",
    "Current 7-day conversion rate for internal landing funnel steps",
    ["step"],
)

LANDING_FUNNEL_WEEKLY_DELTA_RATE = Gauge(
    "valdrics_ops_landing_funnel_weekly_delta_rate",
    "Week-over-week delta for 7-day landing funnel conversion rates",
    ["step"],
)

LANDING_FUNNEL_WEEKLY_THRESHOLD_RATE = Gauge(
    "valdrics_ops_landing_funnel_weekly_threshold_rate",
    "Operating floor threshold for 7-day landing funnel conversion rates",
    ["step"],
)

LANDING_FUNNEL_WEEKLY_NUMERATOR = Gauge(
    "valdrics_ops_landing_funnel_weekly_numerator",
    "Current 7-day numerator volume for landing funnel conversion steps",
    ["step"],
)

LANDING_FUNNEL_WEEKLY_DENOMINATOR = Gauge(
    "valdrics_ops_landing_funnel_weekly_denominator",
    "Current 7-day denominator volume for landing funnel conversion steps",
    ["step"],
)

LANDING_FUNNEL_HEALTH_STATUS = Gauge(
    "valdrics_ops_landing_funnel_health_status",
    "Landing funnel health status by step (-1=insufficient_data, 0=healthy, 1=watch, 2=critical)",
    ["step"],
)

LANDING_FUNNEL_LAST_EVALUATED_UNIXTIME = Gauge(
    "valdrics_ops_landing_funnel_last_evaluated_unixtime",
    "Unix timestamp of the last successful landing funnel health metric refresh",
)

REMEDIATION_DURATION_SECONDS = Histogram(
    "valdrics_ops_remediation_duration_seconds",
    "Duration of remediation execution in seconds",
    ["action", "provider"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)


def record_background_job_stale_running_recovery(
    job_type: str,
    *,
    outcome: str,
) -> None:
    BACKGROUND_JOBS_STALE_RUNNING_RECOVERED_TOTAL.labels(
        job_type=_normalize_metric_label(job_type),
        outcome=_normalize_metric_label(outcome),
    ).inc()


def record_background_job_dead_letter(job_type: str, *, reason: str) -> None:
    BACKGROUND_JOBS_DEAD_LETTERED_TOTAL.labels(
        job_type=_normalize_metric_label(job_type),
        reason=_normalize_metric_label(reason),
    ).inc()


def set_background_jobs_overdue_pending(count: int) -> None:
    normalized = int(count)
    if normalized < 0:
        raise ValueError("count must be >= 0")
    BACKGROUND_JOBS_OVERDUE_PENDING.set(normalized)


def record_audit_log_retention_failure(operation: str) -> None:
    AUDIT_LOG_RETENTION_FAILURES_TOTAL.labels(
        operation=_normalize_metric_label(operation),
    ).inc()


def record_scheduler_inline_fallback(job_name: str, *, outcome: str) -> None:
    SCHEDULER_INLINE_FALLBACK_TOTAL.labels(
        job_name=_normalize_metric_label(job_name),
        outcome=_normalize_metric_label(outcome),
    ).inc()


def record_landing_funnel_health_snapshot(*, evaluated_at: Any, alerts: list[Any]) -> None:
    status_map = {
        "insufficient_data": -1.0,
        "healthy": 0.0,
        "watch": 1.0,
        "critical": 2.0,
    }
    if hasattr(evaluated_at, "timestamp"):
        LANDING_FUNNEL_LAST_EVALUATED_UNIXTIME.set(float(evaluated_at.timestamp()))
    else:
        LANDING_FUNNEL_LAST_EVALUATED_UNIXTIME.set(float(evaluated_at))

    for alert in alerts:
        step = _normalize_metric_label(getattr(alert, "key", None))
        LANDING_FUNNEL_WEEKLY_THRESHOLD_RATE.labels(step=step).set(
            float(getattr(alert, "threshold_rate", 0.0) or 0.0)
        )
        LANDING_FUNNEL_WEEKLY_CONVERSION_RATE.labels(step=step).set(
            float(getattr(alert, "current_rate", 0.0) or 0.0)
        )
        LANDING_FUNNEL_WEEKLY_DELTA_RATE.labels(step=step).set(
            float(getattr(alert, "weekly_delta", 0.0) or 0.0)
        )
        LANDING_FUNNEL_WEEKLY_NUMERATOR.labels(step=step).set(
            int(getattr(alert, "current_numerator", 0) or 0)
        )
        LANDING_FUNNEL_WEEKLY_DENOMINATOR.labels(step=step).set(
            int(getattr(alert, "current_denominator", 0) or 0)
        )
        LANDING_FUNNEL_HEALTH_STATUS.labels(step=step).set(
            status_map.get(
                _normalize_metric_label(getattr(alert, "status", None), default="healthy"),
                0.0,
            )
        )

REMEDIATION_FAILURE = Counter(
    "valdrics_ops_remediation_failure_total",
    "Total number of remediation failures",
    ["action", "provider", "error_type"],
)

REMEDIATION_SUCCESS_TOTAL = Counter(
    "valdrics_ops_remediation_success_total",
    "Total number of successful remediations",
    ["action", "provider"],
)

# --- LLM & Financial Metrics ---
LLM_SPEND_USD = Counter(
    "valdrics_ops_llm_spend_usd_total",
    "Total LLM spend tracked in USD",
    ["tenant_tier", "provider", "model"],
)

LLM_PRE_AUTH_DENIALS = Counter(
    "valdrics_ops_llm_pre_auth_denials_total",
    "Total number of LLM requests denied by financial guardrails",
    ["reason", "tenant_tier"],
)

LLM_FAIR_USE_DENIALS = Counter(
    "valdrics_ops_llm_fair_use_denials_total",
    "Total number of LLM requests denied by fair-use throughput guardrails",
    ["gate", "tenant_tier"],
)

LLM_FAIR_USE_EVALUATIONS = Counter(
    "valdrics_ops_llm_fair_use_evaluations_total",
    "Total fair-use evaluations by gate and outcome",
    ["gate", "outcome", "tenant_tier"],
)

LLM_FAIR_USE_OBSERVED = Gauge(
    "valdrics_ops_llm_fair_use_observed",
    "Observed usage value at fair-use gate checks",
    ["gate", "tenant_tier"],
)

LLM_REQUEST_DURATION = Histogram(
    "valdrics_ops_llm_request_duration_seconds",
    "Duration of LLM API requests",
    ["provider", "model"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60),
)

LLM_TOKENS_TOTAL = Counter(
    "valdrics_ops_llm_tokens_total",
    "Total number of LLM tokens processed",
    ["provider", "model", "token_type"],  # input, output
)

LLM_AUTH_ABUSE_SIGNALS = Counter(
    "valdrics_ops_llm_auth_abuse_signals_total",
    "Authenticated LLM abuse signals by actor type and client IP bucket",
    ["tenant_tier", "actor_type", "ip_bucket"],
)

LLM_AUTH_IP_RISK_SCORE = Gauge(
    "valdrics_ops_llm_auth_ip_risk_score",
    "Latest authenticated LLM client IP risk score by tier and actor",
    ["tenant_tier", "actor_type"],
)

# --- Circuit Breaker Metrics ---
CIRCUIT_BREAKER_STATE = Gauge(
    "valdrics_ops_circuit_breaker_state",
    "Current state of circuit breakers (0=closed, 1=open, 2=half_open)",
    ["circuit_name"],
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "valdrics_ops_circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    ["circuit_name"],
)

CIRCUIT_BREAKER_RECOVERIES = Counter(
    "valdrics_ops_circuit_breaker_recoveries_total",
    "Total number of circuit breaker recoveries",
    ["circuit_name"],
)

# --- Retry & Resilience Metrics ---
OPERATION_RETRIES_TOTAL = Counter(
    "valdrics_ops_operation_retries_total",
    "Total number of operation retries",
    ["operation_type", "attempt"],
)

OPERATION_TIMEOUTS_TOTAL = Counter(
    "valdrics_ops_operation_timeouts_total",
    "Total number of operation timeouts",
    ["operation_type"],
)

# --- Database Metrics ---
DB_CONNECTIONS_ACTIVE = Gauge(
    "valdrics_ops_db_connections_active",
    "Current number of active database connections",
    ["pool_name"],
)

DB_CONNECTIONS_IDLE = Gauge(
    "valdrics_ops_db_connections_idle",
    "Current number of idle database connections",
    ["pool_name"],
)

DB_QUERY_DURATION = Histogram(
    "valdrics_ops_db_query_duration_seconds",
    "Duration of database queries",
    ["operation_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5),
)

DB_DEADLOCKS_TOTAL = Counter(
    "valdrics_ops_db_deadlocks_total", "Total number of database deadlocks detected"
)

# --- Cache Metrics ---
CACHE_HITS_TOTAL = Counter(
    "valdrics_ops_cache_hits_total", "Total number of cache hits", ["cache_type"]
)

CACHE_MISSES_TOTAL = Counter(
    "valdrics_ops_cache_misses_total", "Total number of cache misses", ["cache_type"]
)

CACHE_ERRORS_TOTAL = Counter(
    "valdrics_ops_cache_errors_total",
    "Total number of cache errors",
    ["cache_type", "error_type"],
)

# --- RLS & Security Ops ---
RLS_CONTEXT_MISSING = Counter(
    "valdrics_ops_rls_context_missing_total",
    "Total number of database queries executed without RLS context in request lifecycle",
    ["statement_type"],
)

SECURITY_VIOLATIONS_TOTAL = Counter(
    "valdrics_ops_security_violations_total",
    "Total number of security violations detected",
    ["violation_type", "severity"],
)

# --- System Health Metrics ---
MEMORY_USAGE_BYTES = Gauge(
    "valdrics_ops_memory_usage_bytes", "Current memory usage in bytes", ["process"]
)

CPU_USAGE_PERCENT = Gauge(
    "valdrics_ops_cpu_usage_percent", "Current CPU usage percentage", ["process"]
)

# --- Business Metrics ---
TENANTS_ACTIVE = Gauge("valdrics_ops_tenants_active", "Current number of active tenants")

COST_SAVINGS_TOTAL = Counter(
    "valdrics_ops_cost_savings_total",
    "Total cost savings identified through optimization",
    ["provider", "optimization_type"],
)

ZOMBIES_DETECTED = Counter(
    "valdrics_ops_zombies_detected_total",
    "Total number of zombie resources detected",
    ["provider", "account_id", "resource_type"],
)

POTENTIAL_SAVINGS = Gauge(
    "valdrics_ops_potential_savings_monthly",
    "Estimated monthly savings from identified zombies",
    ["provider", "account_id"],
)

def time_operation(operation_name: str) -> Any:
    return _ops_metrics_recorders.time_operation(
        operation_name=operation_name,
        db_query_duration=DB_QUERY_DURATION,
        sys_module=sys,
    )


def record_circuit_breaker_metrics(
    circuit_name: str, state: str, failures: int, successes: int
) -> None:
    _ops_metrics_recorders.record_circuit_breaker_metrics(
        circuit_name=circuit_name,
        state=state,
        failures=failures,
        successes=successes,
        circuit_breaker_state=CIRCUIT_BREAKER_STATE,
        circuit_breaker_failures=CIRCUIT_BREAKER_FAILURES,
        circuit_breaker_recoveries=CIRCUIT_BREAKER_RECOVERIES,
    )


def record_retry_metrics(operation_type: str, attempt: int) -> None:
    _ops_metrics_recorders.record_retry_metrics(
        operation_type=operation_type,
        attempt=attempt,
        operation_retries_total=OPERATION_RETRIES_TOTAL,
    )


def record_timeout_metrics(operation_type: str) -> None:
    _ops_metrics_recorders.record_timeout_metrics(
        operation_type=operation_type,
        operation_timeouts_total=OPERATION_TIMEOUTS_TOTAL,
    )
