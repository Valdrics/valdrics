import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from prometheus_client import REGISTRY
from app.shared.core import ops_metrics


def test_zombie_metrics_existence():
    """Verify that the new zombie metrics are defined in ops_metrics."""
    # This will fail until we define them in ops_metrics.py
    assert hasattr(ops_metrics, "ZOMBIES_DETECTED")
    assert hasattr(ops_metrics, "POTENTIAL_SAVINGS")
    assert hasattr(ops_metrics, "CLOUD_API_CALLS_TOTAL")
    assert hasattr(ops_metrics, "CLOUD_API_BUDGET_DECISIONS_TOTAL")
    assert hasattr(ops_metrics, "CLOUD_API_BUDGET_REMAINING")
    assert hasattr(ops_metrics, "CLOUD_API_ESTIMATED_COST_USD")


def test_zombie_metrics_behavior():
    """Verify that we can record values into these metrics."""
    ops_metrics.ZOMBIES_DETECTED.labels(
        provider="aws", account_id="123456789012", resource_type="ebs_volume"
    ).inc()

    val = REGISTRY.get_sample_value(
        "valdrics_ops_zombies_detected_total",
        labels={
            "provider": "aws",
            "account_id": "123456789012",
            "resource_type": "ebs_volume",
        },
    )
    assert val == 1.0

    ops_metrics.POTENTIAL_SAVINGS.labels(provider="aws", account_id="123456789012").set(
        99.99
    )

    savings = REGISTRY.get_sample_value(
        "valdrics_ops_potential_savings_monthly",
        labels={"provider": "aws", "account_id": "123456789012"},
    )
    assert savings == 99.99


def test_existing_metrics_integrity():
    """Ensure we haven't broken existing metrics like API_ERRORS_TOTAL."""
    assert hasattr(ops_metrics, "API_ERRORS_TOTAL")
    # Register a sample so it appears in the registry
    ops_metrics.API_ERRORS_TOTAL.labels(
        path="/test", method="GET", status_code="500"
    ).inc()
    val = REGISTRY.get_sample_value(
        "valdrics_ops_api_errors_total",
        labels={"path": "/test", "method": "GET", "status_code": "500"},
    )
    assert val == 1.0


def test_llm_fair_use_metrics_existence_and_behavior():
    assert hasattr(ops_metrics, "LLM_FAIR_USE_DENIALS")
    assert hasattr(ops_metrics, "LLM_FAIR_USE_EVALUATIONS")
    assert hasattr(ops_metrics, "LLM_FAIR_USE_OBSERVED")

    ops_metrics.LLM_FAIR_USE_DENIALS.labels(gate="unit_test", tenant_tier="pro").inc()
    denial_val = REGISTRY.get_sample_value(
        "valdrics_ops_llm_fair_use_denials_total",
        labels={"gate": "unit_test", "tenant_tier": "pro"},
    )
    assert denial_val == 1.0

    ops_metrics.LLM_FAIR_USE_EVALUATIONS.labels(
        gate="unit_test",
        outcome="allow",
        tenant_tier="pro",
    ).inc()
    eval_val = REGISTRY.get_sample_value(
        "valdrics_ops_llm_fair_use_evaluations_total",
        labels={"gate": "unit_test", "outcome": "allow", "tenant_tier": "pro"},
    )
    assert eval_val == 1.0

    ops_metrics.LLM_FAIR_USE_OBSERVED.labels(
        gate="unit_test",
        tenant_tier="pro",
    ).set(3)
    observed_val = REGISTRY.get_sample_value(
        "valdrics_ops_llm_fair_use_observed",
        labels={"gate": "unit_test", "tenant_tier": "pro"},
    )
    assert observed_val == 3.0


def test_record_runtime_carbon_emissions_updates_counter_and_last_run_gauge():
    ops_metrics.record_runtime_carbon_emissions(1.25)

    total = REGISTRY.get_sample_value("valdrics_ops_runtime_carbon_emissions_kg_total")
    last_run = REGISTRY.get_sample_value(
        "valdrics_ops_runtime_carbon_emissions_last_run_kg"
    )

    assert total is not None and total >= 1.25
    assert last_run == 1.25


def test_record_runtime_carbon_emissions_ignores_empty_or_invalid_values() -> None:
    with (
        patch("app.shared.core.ops_metrics.structlog.get_logger") as mock_logger,
        patch("app.shared.core.ops_metrics.RUNTIME_CARBON_EMISSIONS_TOTAL") as mock_total,
        patch("app.shared.core.ops_metrics.RUNTIME_CARBON_EMISSIONS_LAST_RUN") as mock_last,
    ):
        ops_metrics.record_runtime_carbon_emissions(None)
        ops_metrics.record_runtime_carbon_emissions(-1)

    mock_total.inc.assert_not_called()
    mock_last.set.assert_not_called()
    mock_logger.return_value.warning.assert_called_once()


def test_record_cost_retention_purge_updates_counter_and_last_run_gauge() -> None:
    ops_metrics.record_cost_retention_purge("growth", 3)

    total = REGISTRY.get_sample_value(
        "valdrics_ops_cost_record_retention_purged_total",
        labels={"tenant_tier": "growth"},
    )
    last_run = REGISTRY.get_sample_value(
        "valdrics_ops_cost_record_retention_last_run_deleted",
        labels={"tenant_tier": "growth"},
    )

    assert total == 3.0
    assert last_run == 3.0


def test_record_cost_retention_purge_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="deleted_count must be >= 0"):
        ops_metrics.record_cost_retention_purge("free", -1)


def test_record_audit_log_retention_purge_updates_counter_and_last_run_gauge() -> None:
    ops_metrics.record_audit_log_retention_purge(4)

    total = REGISTRY.get_sample_value(
        "valdrics_ops_audit_log_retention_purged_total",
    )
    last_run = REGISTRY.get_sample_value(
        "valdrics_ops_audit_log_retention_last_run_deleted",
    )

    assert total is not None and total >= 4.0
    assert last_run == 4.0


def test_record_audit_log_retention_purge_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="deleted_count must be >= 0"):
        ops_metrics.record_audit_log_retention_purge(-1)


def test_background_job_reliability_metrics_record_expected_values() -> None:
    ops_metrics.record_background_job_stale_running_recovery(
        "webhook_retry",
        outcome="requeued",
    )
    ops_metrics.record_background_job_dead_letter(
        "webhook_retry",
        reason="max_attempts_exhausted",
    )
    ops_metrics.set_background_jobs_overdue_pending(4)
    ops_metrics.record_audit_log_retention_failure("audit_logs_retention")
    ops_metrics.record_scheduler_inline_fallback(
        "background_job_processing",
        outcome="succeeded",
    )

    recovered = REGISTRY.get_sample_value(
        "valdrics_ops_background_jobs_stale_running_recovered_total",
        labels={"job_type": "webhook_retry", "outcome": "requeued"},
    )
    dead_lettered = REGISTRY.get_sample_value(
        "valdrics_ops_background_jobs_dead_lettered_total",
        labels={
            "job_type": "webhook_retry",
            "reason": "max_attempts_exhausted",
        },
    )
    overdue = REGISTRY.get_sample_value(
        "valdrics_ops_background_jobs_overdue_pending_count"
    )
    audit_failures = REGISTRY.get_sample_value(
        "valdrics_ops_audit_log_retention_failures_total",
        labels={"operation": "audit_logs_retention"},
    )
    inline_fallbacks = REGISTRY.get_sample_value(
        "valdrics_scheduler_inline_fallback_total",
        labels={
            "job_name": "background_job_processing",
            "outcome": "succeeded",
        },
    )

    assert recovered == 1.0
    assert dead_lettered == 1.0
    assert overdue == 4.0
    assert audit_failures == 1.0
    assert inline_fallbacks == 1.0


def test_record_landing_funnel_health_snapshot_updates_gauges() -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    alerts = [
        SimpleNamespace(
            key="signup_to_connection",
            status="critical",
            threshold_rate=0.35,
            current_rate=0.25,
            weekly_delta=-0.15,
            current_numerator=1,
            current_denominator=4,
        ),
        SimpleNamespace(
            key="connection_to_first_value",
            status="watch",
            threshold_rate=0.40,
            current_rate=0.45,
            weekly_delta=-0.11,
            current_numerator=9,
            current_denominator=20,
        ),
    ]

    ops_metrics.record_landing_funnel_health_snapshot(
        evaluated_at=now,
        alerts=alerts,
    )

    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_weekly_conversion_rate",
        labels={"step": "signup_to_connection"},
    ) == 0.25
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_weekly_delta_rate",
        labels={"step": "signup_to_connection"},
    ) == -0.15
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_weekly_threshold_rate",
        labels={"step": "signup_to_connection"},
    ) == 0.35
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_weekly_numerator",
        labels={"step": "signup_to_connection"},
    ) == 1.0
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_weekly_denominator",
        labels={"step": "signup_to_connection"},
    ) == 4.0
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_health_status",
        labels={"step": "signup_to_connection"},
    ) == 2.0
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_health_status",
        labels={"step": "connection_to_first_value"},
    ) == 1.0
    assert REGISTRY.get_sample_value(
        "valdrics_ops_landing_funnel_last_evaluated_unixtime"
    ) == now.timestamp()


def test_set_background_jobs_overdue_pending_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="count must be >= 0"):
        ops_metrics.set_background_jobs_overdue_pending(-1)


def test_time_operation_records_db_duration():
    """Decorator should record DB duration for db operations."""
    with patch("app.shared.core.ops_metrics.DB_QUERY_DURATION") as mock_hist:
        decorator = ops_metrics.time_operation("db_query")

        @decorator
        def work():
            return "ok"

        assert work() == "ok"
        mock_hist.labels.assert_called_once_with(operation_type="db_query")
        mock_hist.labels.return_value.observe.assert_called_once()


def test_time_operation_records_db_error_duration():
    """Decorator should record DB error duration on failure."""
    with patch("app.shared.core.ops_metrics.DB_QUERY_DURATION") as mock_hist:
        decorator = ops_metrics.time_operation("db_query")

        @decorator
        def work():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            work()

        mock_hist.labels.assert_called_once_with(operation_type="db_query_error")
        mock_hist.labels.return_value.observe.assert_called_once()


def test_time_operation_skips_api_and_cache_metrics():
    with patch("app.shared.core.ops_metrics.DB_QUERY_DURATION") as mock_hist:
        api_decorator = ops_metrics.time_operation("api_request")
        cache_decorator = ops_metrics.time_operation("cache_get")

        @api_decorator
        def api_work():
            return "ok"

        @cache_decorator
        def cache_work():
            return "ok"

        assert api_work() == "ok"
        assert cache_work() == "ok"
        mock_hist.labels.assert_not_called()


def test_time_operation_error_skips_api_and_cache_metrics():
    with patch("app.shared.core.ops_metrics.DB_QUERY_DURATION") as mock_hist:
        api_decorator = ops_metrics.time_operation("api_request")
        cache_decorator = ops_metrics.time_operation("cache_get")

        @api_decorator
        def api_work():
            raise RuntimeError("api boom")

        @cache_decorator
        def cache_work():
            raise RuntimeError("cache boom")

        with pytest.raises(RuntimeError):
            api_work()
        with pytest.raises(RuntimeError):
            cache_work()

        mock_hist.labels.assert_not_called()


def test_record_circuit_breaker_metrics():
    """Record circuit breaker state + counters."""
    with (
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_STATE") as mock_state,
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_FAILURES") as mock_failures,
        patch(
            "app.shared.core.ops_metrics.CIRCUIT_BREAKER_RECOVERIES"
        ) as mock_recoveries,
    ):
        ops_metrics.record_circuit_breaker_metrics(
            circuit_name="cb",
            state="open",
            failures=2,
            successes=3,
        )

        mock_state.labels.assert_called_once_with(circuit_name="cb")
        mock_state.labels.return_value.set.assert_called_once_with(1)
        mock_failures.labels.assert_called_once_with(circuit_name="cb")
        mock_failures.labels.return_value.inc.assert_called_once_with(2)
        mock_recoveries.labels.assert_called_once_with(circuit_name="cb")
        mock_recoveries.labels.return_value.inc.assert_called_once_with(3)


def test_record_circuit_breaker_metrics_zero_counts():
    with (
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_STATE") as mock_state,
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_FAILURES") as mock_failures,
        patch(
            "app.shared.core.ops_metrics.CIRCUIT_BREAKER_RECOVERIES"
        ) as mock_recoveries,
    ):
        ops_metrics.record_circuit_breaker_metrics(
            circuit_name="cb-zero",
            state="closed",
            failures=0,
            successes=0,
        )

        mock_state.labels.assert_called_once_with(circuit_name="cb-zero")
        mock_state.labels.return_value.set.assert_called_once_with(0)
        mock_failures.labels.assert_not_called()
        mock_recoveries.labels.assert_not_called()


def test_record_circuit_breaker_metrics_unknown_state():
    with (
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_STATE") as mock_state,
        patch("app.shared.core.ops_metrics.CIRCUIT_BREAKER_FAILURES") as mock_failures,
        patch(
            "app.shared.core.ops_metrics.CIRCUIT_BREAKER_RECOVERIES"
        ) as mock_recoveries,
    ):
        ops_metrics.record_circuit_breaker_metrics(
            circuit_name="cb-unknown",
            state="invalid_state",
            failures=1,
            successes=0,
        )

        mock_state.labels.assert_called_once_with(circuit_name="cb-unknown")
        mock_state.labels.return_value.set.assert_called_once_with(0)
        mock_failures.labels.assert_called_once_with(circuit_name="cb-unknown")
        mock_failures.labels.return_value.inc.assert_called_once_with(1)
        mock_recoveries.labels.assert_not_called()


def test_record_retry_and_timeout_metrics():
    with (
        patch("app.shared.core.ops_metrics.OPERATION_RETRIES_TOTAL") as mock_retries,
        patch("app.shared.core.ops_metrics.OPERATION_TIMEOUTS_TOTAL") as mock_timeouts,
    ):
        ops_metrics.record_retry_metrics("op", 2)
        ops_metrics.record_timeout_metrics("op")

        mock_retries.labels.assert_called_once_with(operation_type="op", attempt="2")
        mock_retries.labels.return_value.inc.assert_called_once()
        mock_timeouts.labels.assert_called_once_with(operation_type="op")
        mock_timeouts.labels.return_value.inc.assert_called_once()
