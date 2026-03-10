"""Pydantic models for investor health dashboard responses."""

from pydantic import BaseModel


class SystemHealth(BaseModel):
    """Overall system health status."""

    status: str  # healthy, degraded, critical
    uptime_hours: float
    last_check: str


class TenantMetrics(BaseModel):
    """Tenant growth and activity metrics."""

    total_tenants: int
    active_last_24h: int
    active_last_7d: int
    free_tenants: int
    paid_tenants: int
    churn_risk: int  # Inactive paid tenants


class JobQueueHealth(BaseModel):
    """Background job queue metrics."""

    pending_jobs: int
    running_jobs: int
    failed_last_24h: int
    dead_letter_count: int
    avg_processing_time_ms: float
    p50_processing_time_ms: float
    p95_processing_time_ms: float
    p99_processing_time_ms: float


class LLMUsageMetrics(BaseModel):
    """LLM cost and usage metrics."""

    total_requests_24h: int
    cache_hit_rate: float
    estimated_cost_24h: float
    budget_utilization: float


class LLMFairUseThresholds(BaseModel):
    """Configured fair-use guard thresholds."""

    pro_daily_soft_cap: int | None
    enterprise_daily_soft_cap: int | None
    per_minute_cap: int | None
    per_tenant_concurrency_cap: int | None
    concurrency_lease_ttl_seconds: int
    enforced_tiers: list[str]


class LLMFairUseRuntime(BaseModel):
    """Tenant-scoped fair-use runtime state and thresholds."""

    generated_at: str
    guards_enabled: bool
    tenant_tier: str
    tier_eligible: bool
    active_for_tenant: bool
    thresholds: LLMFairUseThresholds


class CloudPlusProviderHealth(BaseModel):
    """Connection health snapshot for one Cloud+ provider."""

    total_connections: int
    active_connections: int
    inactive_connections: int
    errored_connections: int


class CloudPlusConnectionHealth(BaseModel):
    """Aggregated Cloud+ connection status across providers."""

    total_connections: int
    active_connections: int
    inactive_connections: int
    errored_connections: int
    providers: dict[str, CloudPlusProviderHealth]


class CloudConnectionHealth(BaseModel):
    """Aggregated core-cloud connection status for AWS/Azure/GCP."""

    total_connections: int
    active_connections: int
    inactive_connections: int
    errored_connections: int
    providers: dict[str, CloudPlusProviderHealth]


class LicenseGovernanceHealth(BaseModel):
    """License governance execution metrics."""

    window_hours: int
    active_license_connections: int
    requests_created_24h: int
    requests_completed_24h: int
    requests_failed_24h: int
    requests_in_flight: int
    completion_rate_percent: float
    failure_rate_percent: float
    avg_time_to_complete_hours: float | None


class LandingFunnelWindowSummary(BaseModel):
    """Current or previous weekly landing-to-paid funnel snapshot."""

    total_events: int = 0
    cta_events: int = 0
    signup_intent_events: int = 0
    onboarded_tenants: int = 0
    connected_tenants: int = 0
    first_value_tenants: int = 0
    pql_tenants: int = 0
    pricing_view_tenants: int = 0
    checkout_started_tenants: int = 0
    paid_tenants: int = 0
    signup_to_connection_rate: float | None = None
    connection_to_first_value_rate: float | None = None


class LandingFunnelWeeklyDelta(BaseModel):
    """Week-over-week delta for the landing-to-paid funnel."""

    total_events: int = 0
    signup_intent_events: int = 0
    onboarded_tenants: int = 0
    connected_tenants: int = 0
    first_value_tenants: int = 0
    pql_tenants: int = 0
    pricing_view_tenants: int = 0
    checkout_started_tenants: int = 0
    paid_tenants: int = 0
    signup_to_connection_rate: float | None = None
    connection_to_first_value_rate: float | None = None


class LandingFunnelHealthAlert(BaseModel):
    """Operational alert for a critical funnel conversion step."""

    key: str
    label: str
    status: str
    threshold_rate: float
    current_rate: float | None = None
    previous_rate: float | None = None
    weekly_delta: float | None = None
    current_numerator: int = 0
    current_denominator: int = 0
    message: str


class LandingFunnelHealth(BaseModel):
    """Internal weekly landing-funnel health state for ops dashboards."""

    weekly_current: LandingFunnelWindowSummary
    weekly_previous: LandingFunnelWindowSummary
    weekly_delta: LandingFunnelWeeklyDelta
    alerts: list[LandingFunnelHealthAlert]


class InvestorHealthDashboard(BaseModel):
    """Complete health dashboard for investors."""

    generated_at: str
    system: SystemHealth
    tenants: TenantMetrics
    job_queue: JobQueueHealth
    llm_usage: LLMUsageMetrics
    cloud_connections: CloudConnectionHealth
    cloud_plus_connections: CloudPlusConnectionHealth
    license_governance: LicenseGovernanceHealth
    landing_funnel: LandingFunnelHealth


__all__ = [
    "CloudConnectionHealth",
    "CloudPlusConnectionHealth",
    "CloudPlusProviderHealth",
    "InvestorHealthDashboard",
    "JobQueueHealth",
    "LandingFunnelHealth",
    "LandingFunnelHealthAlert",
    "LandingFunnelWeeklyDelta",
    "LandingFunnelWindowSummary",
    "LLMFairUseRuntime",
    "LLMFairUseThresholds",
    "LLMUsageMetrics",
    "LicenseGovernanceHealth",
    "SystemHealth",
    "TenantMetrics",
]
