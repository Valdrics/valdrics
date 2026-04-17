from pathlib import Path
import tempfile

from pydantic import Field


class CoreRuntimeSettings:
    APP_NAME: str = "Valdrics"
    VERSION: str = "0.1.0"
    APP_VERSION: str | None = None
    DEBUG: bool = False
    # ENVIRONMENT options: local, development, staging, production
    # is_production property ensures strict security for 'production'
    ENVIRONMENT: str = "development"
    API_URL: str = "http://localhost:8000"  # Base URL for OIDC and Magic Links
    PLATFORM_RUNTIME_PROFILE: str = "gcp"  # gcp
    OBSERVABILITY_BACKEND: str = "gcp"  # gcp
    INTERNAL_METRICS_AUTH_TOKEN: str | None = None
    CSRF_SECRET_KEY: str | None = None  # SEC-01: CSRF
    CSRF_TEST_SECRET_KEY: str | None = None
    TESTING: bool = False
    PYTEST_CURRENT_TEST: str | None = None
    EXPOSE_API_DOCUMENTATION_PUBLICLY: bool = False
    APP_RUNTIME_DATA_DIR: str = str(Path(tempfile.gettempdir()) / "valdrics")
    RATELIMIT_ENABLED: bool = False
    # Supported managed GCP runtime delegates public API throttling to Cloudflare
    # WAF rate limiting rules and keeps the in-app limiter disabled by default.
    PUBLIC_API_RATE_LIMITING_BACKEND: str = "cloudflare"
    ANALYSIS_RATE_LIMIT_FREE_PER_HOUR: int = 1
    ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR: int = 2
    ANALYSIS_RATE_LIMIT_GROWTH_PER_HOUR: int = 10
    ANALYSIS_RATE_LIMIT_PRO_PER_HOUR: int = 50
    ANALYSIS_RATE_LIMIT_ENTERPRISE_PER_HOUR: int = 200
    # When the shared application limiter is explicitly enabled in staging/production,
    # in-memory state is allowed only as controlled break-glass.
    ALLOW_IN_MEMORY_RATE_LIMITS: bool = False
    AUTOPILOT_BYPASS_GRACE_PERIOD: bool = False
    TURNSTILE_ENABLED: bool = False
    TURNSTILE_ENFORCE_IN_TESTING: bool = False
    TURNSTILE_SECRET_KEY: str | None = None
    TURNSTILE_VERIFY_URL: str = (
        "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    )
    TURNSTILE_TIMEOUT_SECONDS: float = 3.0
    TURNSTILE_FAIL_OPEN: bool = False
    TURNSTILE_REQUIRE_PUBLIC_ASSESSMENT: bool = True
    TURNSTILE_REQUIRE_SSO_DISCOVERY: bool = True
    TURNSTILE_REQUIRE_ONBOARD: bool = True
    TURNSTILE_REQUIRE_PUBLIC_SALES_INTAKE: bool = True
    WEBHOOK_ALLOWED_DOMAINS: list[str] = Field(
        default_factory=list
    )  # Allowlist for generic webhook retries
    WEBHOOK_REQUIRE_HTTPS: bool = True
    WEBHOOK_BLOCK_PRIVATE_IPS: bool = True
    ALLOW_INSECURE_OUTBOUND_TLS: bool = False
    OUTBOUND_TLS_BREAK_GLASS_REASON: str | None = None
    OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT: str | None = None
    OUTBOUND_TLS_BREAK_GLASS_MAX_DURATION_HOURS: int = 24
    MARKETING_SUBSCRIBE_WEBHOOK_URL: str | None = None
    # Only trust X-Forwarded-For when the deployment path is explicitly trusted.
    TRUST_PROXY_HEADERS: bool = False
    # Number of trusted reverse-proxy hops when resolving client IP from XFF.
    # 1 = trust the nearest proxy and use the right-most forwarded address.
    TRUSTED_PROXY_HOPS: int = 1
    # Explicit proxy network allowlist used before trusting X-Forwarded-For.
    TRUSTED_PROXY_CIDRS: list[str] = Field(default_factory=list)
    SSE_MAX_CONNECTIONS_PER_TENANT: int = 5
    SSE_POLL_INTERVAL_SECONDS: int = 3

    # AWS Credentials
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: str | None = (
        None  # Added for local testing (MotoServer/LocalStack)
    )
    AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN: str | None = None
    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str | None = None
    GCP_CLOUD_TASKS_QUEUE: str | None = None
    GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL: str | None = None
    GCP_CLOUD_RUN_SERVICE_NAME: str | None = None
    GCP_CLOUD_RUN_BATCH_JOB_NAME: str | None = None
    GCP_INTERNAL_BASE_URL: str | None = None
    GCP_INTERNAL_AUTH_AUDIENCE: str | None = None
    GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS: list[str] = Field(default_factory=list)

    # Optional override for a publicly reachable CloudFormation template URL.
    # When empty, onboarding derives a release-owned public API URL from API_URL.
    CLOUDFORMATION_TEMPLATE_URL: str = ""

    # Security
    CORS_ORIGINS: list[str] = Field(
        default_factory=list
    )  # Empty by default - restricted in prod
    FRONTEND_URL: str = "http://localhost:5174"  # Used for billing callbacks
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"  # High performance for complex analysis

    # Claude/Anthropic Credentials
    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-3-7-sonnet"
    ANTHROPIC_API_KEY: str | None = None

    # Google Gemini Credentials
    GOOGLE_API_KEY: str | None = None
    GOOGLE_MODEL: str = "gemini-2.0-flash"

    # Groq Credentials
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # LLM Provider
    LLM_PROVIDER: str = "groq"  # Options: openai, claude, google, groq
    ENABLE_DELTA_ANALYSIS: bool = True  # Innovation 1: Reduce token usage by 90%
    DELTA_ANALYSIS_DAYS: int = 3
    # Forecasting policy in strict environments (staging/production):
    # false -> require Prophet at startup (default)
    # true  -> allow temporary Holt-Winters break-glass fallback
    FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK: bool = False
    # Break-glass audit metadata when fallback is enabled in strict env.
    FORECASTER_BREAK_GLASS_REASON: str | None = None
    FORECASTER_BREAK_GLASS_EXPIRES_AT: str | None = None
    FORECASTER_BREAK_GLASS_MAX_DURATION_HOURS: int = 168
    # Disabled-by-default fairness guardrails for future "near-unlimited" tiers.
    # Keep OFF until production evidence gates are met.
    LLM_FAIR_USE_GUARDS_ENABLED: bool = False
    LLM_FAIR_USE_PRO_DAILY_SOFT_CAP: int = 1200
    LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP: int = 4000
    LLM_FAIR_USE_PER_MINUTE_CAP: int = 30
    LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP: int = 4
    LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS: int = 180
    LLM_GLOBAL_ABUSE_GUARDS_ENABLED: bool = True
    LLM_GLOBAL_ABUSE_PER_MINUTE_CAP: int = 600
    LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD: int = 30
    LLM_GLOBAL_ABUSE_BLOCK_SECONDS: int = 120
    LLM_GLOBAL_ABUSE_KILL_SWITCH: bool = False

    # Scheduler sweep controls for managed trigger execution.
    SCHEDULER_SYSTEM_SWEEP_MAX_TENANTS: int = 5000
    SCHEDULER_SYSTEM_SWEEP_MAX_CONNECTIONS: int = 5000
    BACKGROUND_JOB_PROCESS_BATCH_SIZE: int = 25
    BACKGROUND_JOB_PROCESS_MAX_BATCHES_PER_TICK: int = 8
    BACKGROUND_JOB_PENDING_OVERDUE_ALERT_MINUTES: int = 60
    BACKGROUND_JOB_RUNNING_TIMEOUT_MINUTES: int = 30
    # Background job retention (terminal states) enforced by maintenance sweep.
    BACKGROUND_JOB_COMPLETED_RETENTION_DAYS: int = 7
    BACKGROUND_JOB_FAILED_RETENTION_DAYS: int = 30
    BACKGROUND_JOB_DEAD_LETTER_RETENTION_DAYS: int = 30
    BACKGROUND_JOB_RETENTION_PURGE_BATCH_SIZE: int = 1000
    BACKGROUND_JOB_RETENTION_PURGE_MAX_BATCHES: int = 20
    AUDIT_LOG_RETENTION_DAYS: int = 90
    AUDIT_LOG_RETENTION_PURGE_BATCH_SIZE: int = 5000
    AUDIT_LOG_RETENTION_PURGE_MAX_BATCHES: int = 20
    # Cost-record retention is plan-aware and enforced by the maintenance sweep.
    COST_RECORD_RETENTION_PURGE_BATCH_SIZE: int = 5000
    COST_RECORD_RETENTION_PURGE_MAX_BATCHES: int = 50
    # Managed scheduler dispatch lock should fail-closed by default.
    # Enable only as temporary emergency bypass.
    SCHEDULER_LOCK_FAIL_OPEN: bool = False
    TENANT_ISOLATION_EVIDENCE_MAX_AGE_HOURS: int = 168

    # Admin API Key
    ADMIN_API_KEY: str | None = None
