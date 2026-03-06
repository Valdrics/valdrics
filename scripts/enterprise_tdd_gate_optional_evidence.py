"""Optional evidence command assembly for enterprise TDD gate."""

from __future__ import annotations

import os

from scripts.enterprise_tdd_gate_config import (
    DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH,
    DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_MAX_AGE_HOURS,
    DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS,
    DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH,
    DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS,
    DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS,
    DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS,
    DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH,
    DEFAULT_ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS,
    DEFAULT_ENFORCEMENT_STRESS_MIN_CONCURRENT_USERS,
    DEFAULT_ENFORCEMENT_STRESS_MIN_DURATION_SECONDS,
    DEFAULT_ENFORCEMENT_STRESS_REQUIRED_DATABASE_ENGINE,
    DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS,
    DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS,
    DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH,
    DEFAULT_KEY_ROTATION_DRILL_MAX_AGE_DAYS,
    DEFAULT_KEY_ROTATION_DRILL_PATH,
    ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_MAX_AGE_HOURS_ENV,
    ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_PATH_ENV,
    ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_REQUIRED_ENV,
    ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_MAX_AGE_HOURS_ENV,
    ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH_ENV,
    ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_REQUIRED_ENV,
    ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS_ENV,
    ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH_ENV,
    ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_REQUIRED_ENV,
    ENFORCEMENT_KEY_ROTATION_DRILL_MAX_AGE_DAYS_ENV,
    ENFORCEMENT_KEY_ROTATION_DRILL_PATH_ENV,
    ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS_ENV,
    ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS_ENV,
    ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS_ENV,
    ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH_ENV,
    ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_REQUIRED_ENV,
    ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS_ENV,
    ENFORCEMENT_PRICING_BENCHMARK_REGISTER_PATH_ENV,
    ENFORCEMENT_PRICING_BENCHMARK_REGISTER_REQUIRED_ENV,
    ENFORCEMENT_RUNTIME_EVIDENCE_ONLY_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_MAX_AGE_HOURS_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_MIN_CONCURRENT_USERS_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_MIN_DURATION_SECONDS_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_PATH_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_DATABASE_ENGINE_ENV,
    ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_ENV,
    ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS_ENV,
    ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS_ENV,
    ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH_ENV,
)


def _is_truthy(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _resolve_path_with_runtime_policy(
    *,
    env_name: str,
    default_path: str,
    runtime_only: bool,
) -> str:
    value = os.getenv(env_name, "").strip()
    if value:
        return value
    if runtime_only:
        raise ValueError(
            f"{env_name} must be set when {ENFORCEMENT_RUNTIME_EVIDENCE_ONLY_ENV}=true"
        )
    return default_path


def append_optional_evidence_commands(commands: list[list[str]]) -> None:
    runtime_evidence_only = _is_truthy(os.getenv(ENFORCEMENT_RUNTIME_EVIDENCE_ONLY_ENV))

    key_rotation_drill_path = _resolve_path_with_runtime_policy(
        env_name=ENFORCEMENT_KEY_ROTATION_DRILL_PATH_ENV,
        default_path=DEFAULT_KEY_ROTATION_DRILL_PATH,
        runtime_only=runtime_evidence_only,
    )
    key_rotation_max_age_days = (
        os.getenv(ENFORCEMENT_KEY_ROTATION_DRILL_MAX_AGE_DAYS_ENV, "").strip()
        or DEFAULT_KEY_ROTATION_DRILL_MAX_AGE_DAYS
    )
    commands.append(
        [
            "uv",
            "run",
            "python3",
            "scripts/verify_key_rotation_drill_evidence.py",
            "--drill-path",
            key_rotation_drill_path,
            "--max-drill-age-days",
            key_rotation_max_age_days,
        ]
    )

    refresh_guardrails_path = _resolve_path_with_runtime_policy(
        env_name=ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH_ENV,
        default_path=DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH,
        runtime_only=runtime_evidence_only,
    )
    refresh_telemetry_path = _resolve_path_with_runtime_policy(
        env_name=ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH_ENV,
        default_path=DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH,
        runtime_only=runtime_evidence_only,
    )
    refresh_pkg_fin_path = _resolve_path_with_runtime_policy(
        env_name=ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH_ENV,
        default_path=DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH,
        runtime_only=runtime_evidence_only,
    )
    refresh_max_age_days = (
        os.getenv(ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS_ENV, "").strip()
        or DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_AGE_DAYS
    )
    refresh_max_capture_spread_days = (
        os.getenv(
            ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS_ENV, ""
        ).strip()
        or DEFAULT_ENFORCEMENT_MONTHLY_FINANCE_REFRESH_MAX_CAPTURE_SPREAD_DAYS
    )
    commands.append(
        [
            "uv",
            "run",
            "python3",
            "scripts/verify_monthly_finance_evidence_refresh.py",
            "--finance-guardrails-path",
            refresh_guardrails_path,
            "--finance-telemetry-snapshot-path",
            refresh_telemetry_path,
            "--pkg-fin-policy-decisions-path",
            refresh_pkg_fin_path,
            "--max-age-days",
            refresh_max_age_days,
            "--max-capture-spread-days",
            refresh_max_capture_spread_days,
        ]
    )

    valdrics_disposition_register_path = _resolve_path_with_runtime_policy(
        env_name=ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH_ENV,
        default_path=DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_REGISTER_PATH,
        runtime_only=runtime_evidence_only,
    )
    valdrics_disposition_max_age_days = (
        os.getenv(ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS_ENV, "").strip()
        or DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_AGE_DAYS
    )
    valdrics_disposition_max_review_window_days = (
        os.getenv(
            ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS_ENV, ""
        ).strip()
        or DEFAULT_ENFORCEMENT_VALDRICS_DISPOSITION_MAX_REVIEW_WINDOW_DAYS
    )
    commands.append(
        [
            "uv",
            "run",
            "python3",
            "scripts/verify_valdrics_disposition_freshness.py",
            "--register-path",
            valdrics_disposition_register_path,
            "--max-artifact-age-days",
            valdrics_disposition_max_age_days,
            "--max-review-window-days",
            valdrics_disposition_max_review_window_days,
        ]
    )

    stress_evidence_path = os.getenv(ENFORCEMENT_STRESS_EVIDENCE_PATH_ENV, "").strip()
    stress_evidence_required = _is_truthy(
        os.getenv(ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_ENV)
    )
    if stress_evidence_required and not stress_evidence_path:
        raise ValueError(
            "ENFORCEMENT_STRESS_EVIDENCE_REQUIRED is true but "
            "ENFORCEMENT_STRESS_EVIDENCE_PATH is not set"
        )
    if stress_evidence_path:
        stress_min_duration_seconds = (
            os.getenv(ENFORCEMENT_STRESS_EVIDENCE_MIN_DURATION_SECONDS_ENV, "").strip()
            or DEFAULT_ENFORCEMENT_STRESS_MIN_DURATION_SECONDS
        )
        stress_min_concurrent_users = (
            os.getenv(ENFORCEMENT_STRESS_EVIDENCE_MIN_CONCURRENT_USERS_ENV, "").strip()
            or DEFAULT_ENFORCEMENT_STRESS_MIN_CONCURRENT_USERS
        )
        stress_required_database_engine = (
            os.getenv(
                ENFORCEMENT_STRESS_EVIDENCE_REQUIRED_DATABASE_ENGINE_ENV, ""
            ).strip()
            or DEFAULT_ENFORCEMENT_STRESS_REQUIRED_DATABASE_ENGINE
        )
        stress_cmd = [
            "uv",
            "run",
            "python3",
            "scripts/verify_enforcement_stress_evidence.py",
            "--evidence-path",
            stress_evidence_path,
            "--min-duration-seconds",
            stress_min_duration_seconds,
            "--min-concurrent-users",
            stress_min_concurrent_users,
            "--required-database-engine",
            stress_required_database_engine,
        ]
        stress_artifact_max_age = os.getenv(
            ENFORCEMENT_STRESS_EVIDENCE_MAX_AGE_HOURS_ENV, ""
        ).strip()
        if stress_artifact_max_age:
            stress_cmd.extend([
                "--max-artifact-age-hours",
                stress_artifact_max_age,
            ])
        commands.append(stress_cmd)

    failure_injection_evidence_path = os.getenv(
        ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_PATH_ENV, ""
    ).strip()
    failure_injection_evidence_required = _is_truthy(
        os.getenv(ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_REQUIRED_ENV)
    )
    if failure_injection_evidence_required and not failure_injection_evidence_path:
        raise ValueError(
            "ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_REQUIRED is true but "
            "ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_PATH is not set"
        )
    if failure_injection_evidence_path:
        failure_injection_cmd = [
            "uv",
            "run",
            "python3",
            "scripts/verify_enforcement_failure_injection_evidence.py",
            "--evidence-path",
            failure_injection_evidence_path,
        ]
        failure_injection_max_age = os.getenv(
            ENFORCEMENT_FAILURE_INJECTION_EVIDENCE_MAX_AGE_HOURS_ENV, ""
        ).strip()
        if failure_injection_max_age:
            failure_injection_cmd.extend([
                "--max-artifact-age-hours",
                failure_injection_max_age,
            ])
        commands.append(failure_injection_cmd)

    finance_evidence_path = os.getenv(
        ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH_ENV, ""
    ).strip()
    finance_evidence_required = _is_truthy(
        os.getenv(ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_REQUIRED_ENV)
    )
    if finance_evidence_required and not finance_evidence_path:
        raise ValueError(
            "ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_REQUIRED is true but "
            "ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_PATH is not set"
        )
    if finance_evidence_path:
        finance_max_age_hours = (
            os.getenv(ENFORCEMENT_FINANCE_GUARDRAILS_EVIDENCE_MAX_AGE_HOURS_ENV, "").strip()
            or DEFAULT_ENFORCEMENT_FINANCE_GUARDRAILS_MAX_AGE_HOURS
        )
        commands.append(
            [
                "uv",
                "run",
                "python3",
                "scripts/verify_finance_guardrails_evidence.py",
                "--evidence-path",
                finance_evidence_path,
                "--max-artifact-age-hours",
                finance_max_age_hours,
            ]
        )

    finance_telemetry_snapshot_path = os.getenv(
        ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH_ENV, ""
    ).strip()
    finance_telemetry_snapshot_required = _is_truthy(
        os.getenv(ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_REQUIRED_ENV)
    )
    if finance_telemetry_snapshot_required and not finance_telemetry_snapshot_path:
        raise ValueError(
            "ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_REQUIRED is true but "
            "ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_PATH is not set"
        )
    if finance_telemetry_snapshot_path:
        finance_telemetry_max_age_hours = (
            os.getenv(ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS_ENV, "").strip()
            or DEFAULT_ENFORCEMENT_FINANCE_TELEMETRY_SNAPSHOT_MAX_AGE_HOURS
        )
        commands.append(
            [
                "uv",
                "run",
                "python3",
                "scripts/verify_finance_telemetry_snapshot.py",
                "--snapshot-path",
                finance_telemetry_snapshot_path,
                "--max-artifact-age-hours",
                finance_telemetry_max_age_hours,
            ]
        )

    pricing_benchmark_register_path = os.getenv(
        ENFORCEMENT_PRICING_BENCHMARK_REGISTER_PATH_ENV, ""
    ).strip()
    pricing_benchmark_register_required = _is_truthy(
        os.getenv(ENFORCEMENT_PRICING_BENCHMARK_REGISTER_REQUIRED_ENV)
    )
    if pricing_benchmark_register_required and not pricing_benchmark_register_path:
        raise ValueError(
            "ENFORCEMENT_PRICING_BENCHMARK_REGISTER_REQUIRED is true but "
            "ENFORCEMENT_PRICING_BENCHMARK_REGISTER_PATH is not set"
        )
    if pricing_benchmark_register_path:
        pricing_max_source_age_days = (
            os.getenv(
                ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS_ENV, ""
            ).strip()
            or DEFAULT_ENFORCEMENT_PRICING_BENCHMARK_MAX_SOURCE_AGE_DAYS
        )
        commands.append(
            [
                "uv",
                "run",
                "python3",
                "scripts/verify_pricing_benchmark_register.py",
                "--register-path",
                pricing_benchmark_register_path,
                "--max-source-age-days",
                pricing_max_source_age_days,
            ]
        )

    pkg_fin_policy_decisions_path = os.getenv(
        ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH_ENV, ""
    ).strip()
    pkg_fin_policy_decisions_required = _is_truthy(
        os.getenv(ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_REQUIRED_ENV)
    )
    if pkg_fin_policy_decisions_required and not pkg_fin_policy_decisions_path:
        raise ValueError(
            "ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_REQUIRED is true but "
            "ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_PATH is not set"
        )
    if pkg_fin_policy_decisions_path:
        pkg_fin_policy_decisions_max_age_hours = (
            os.getenv(
                ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS_ENV, ""
            ).strip()
            or DEFAULT_ENFORCEMENT_PKG_FIN_POLICY_DECISIONS_MAX_AGE_HOURS
        )
        commands.append(
            [
                "uv",
                "run",
                "python3",
                "scripts/verify_pkg_fin_policy_decisions.py",
                "--evidence-path",
                pkg_fin_policy_decisions_path,
                "--max-artifact-age-hours",
                pkg_fin_policy_decisions_max_age_hours,
            ]
        )
