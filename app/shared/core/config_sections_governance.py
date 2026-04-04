from pydantic import Field

from app.shared.core.constants import (
    AWS_SUPPORTED_REGIONS as DEFAULT_AWS_SUPPORTED_REGIONS,
)


DEFAULT_SUPPORTED_CURRENCIES = ("USD", "NGN", "EUR", "GBP")


class GovernanceSettings:
    # Circuit Breaker & Safety Guardrails (Phase 12)
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 300
    CIRCUIT_BREAKER_MAX_DAILY_SAVINGS: float = 1000.0
    CIRCUIT_BREAKER_CACHE_SIZE: int = 1000
    # Redis-backed state is the default deployment posture for multi-worker safety.
    CIRCUIT_BREAKER_DISTRIBUTED_STATE: bool = True
    CIRCUIT_BREAKER_DISTRIBUTED_KEY_PREFIX: str = "valdrics:circuit"
    # REMEDIATION KILL SWITCH: Stop all deletions if daily cost impact hits $500
    REMEDIATION_KILL_SWITCH_THRESHOLD: float = 500.0
    REMEDIATION_KILL_SWITCH_SCOPE: str = Field(
        default="tenant", description="Scope: global or tenant"
    )
    REMEDIATION_KILL_SWITCH_ALLOW_GLOBAL_SCOPE: bool = False
    ENFORCE_REMEDIATION_DRY_RUN: bool = False
    ENFORCEMENT_GATE_TIMEOUT_SECONDS: float = 2.0
    ENFORCEMENT_GLOBAL_ABUSE_GUARD_ENABLED: bool = True
    ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP: int = 1200
    ENFORCEMENT_APPROVAL_TOKEN_SECRET: str | None = None
    ENFORCEMENT_EXPORT_SIGNING_SECRET: str | None = None
    ENFORCEMENT_EXPORT_SIGNING_KID: str = "enforcement-export-hmac-v1"
    ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS: int = 86400
    ENFORCEMENT_RECONCILIATION_SWEEP_ENABLED: bool = True
    ENFORCEMENT_RECONCILIATION_SWEEP_MAX_RELEASES: int = 500
    ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT: int = 200
    ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_THRESHOLD_USD: float = 100.0
    ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_EXCEPTION_COUNT: int = 5
    ENFORCEMENT_EXPORT_MAX_DAYS: int = 366
    ENFORCEMENT_EXPORT_MAX_ROWS: int = 10000
    ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS: list[str] = Field(default_factory=list)

    # Multi-Currency & Localization (Phase 12)
    SUPPORTED_CURRENCIES: list[str] = Field(
        default_factory=lambda: list(DEFAULT_SUPPORTED_CURRENCIES)
    )
    EXCHANGE_RATE_SYNC_INTERVAL_HOURS: int = 24
    BASE_CURRENCY: str = "USD"
    WEBHOOK_IDEMPOTENCY_TTL_HOURS: int = 72  # L5: Move to settings

    # AWS Regions (BE-ADAPT-1: Regional Whitelist)
    AWS_SUPPORTED_REGIONS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_AWS_SUPPORTED_REGIONS)
    )

    # Scanner Settings
    ZOMBIE_PLUGIN_TIMEOUT_SECONDS: int = 30
    ZOMBIE_REGION_TIMEOUT_SECONDS: int = 120
    CLOUD_API_BUDGET_GOVERNOR_ENABLED: bool = True
    CLOUD_API_BUDGET_ENFORCE: bool = True
    # Daily per-tenant caps for expensive telemetry APIs.
    # 0 disables capping for the API.
    AWS_CLOUDWATCH_DAILY_CALL_BUDGET: int = 3000
    GCP_MONITORING_DAILY_CALL_BUDGET: int = 3000
    AZURE_MONITOR_DAILY_CALL_BUDGET: int = 3000
    # Estimated API costs per call used only for observability metrics.
    AWS_CLOUDWATCH_ESTIMATED_COST_PER_CALL_USD: float = 0.00001
    GCP_MONITORING_ESTIMATED_COST_PER_CALL_USD: float = 0.0
    AZURE_MONITOR_ESTIMATED_COST_PER_CALL_USD: float = 0.0
    # Bound export window size to keep CSV export queries predictable.
    FOCUS_EXPORT_MAX_DAYS: int = 366
