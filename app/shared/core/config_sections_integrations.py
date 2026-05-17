from pydantic import Field


DEFAULT_JIRA_ALLOWED_DOMAINS = ("atlassian.net",)
DEFAULT_TEAMS_WEBHOOK_ALLOWED_DOMAINS = (
    "office.com",
    "office365.com",
    "webhook.office.com",
    "logic.azure.com",
    "powerautomate.com",
)
DEFAULT_PAYSTACK_WEBHOOK_ALLOWED_IPS = (
    "52.31.139.75",
    "52.49.173.169",
    "52.214.14.220",
)


class IntegrationSettings:
    # Notifications
    SAAS_STRICT_INTEGRATIONS: bool = False
    SLACK_BOT_TOKEN: str | None = None
    SLACK_CHANNEL_ID: str | None = None
    JIRA_BASE_URL: str | None = None
    JIRA_EMAIL: str | None = None
    JIRA_API_TOKEN: str | None = None
    JIRA_PROJECT_KEY: str | None = None
    JIRA_ISSUE_TYPE: str = "Task"
    JIRA_TIMEOUT_SECONDS: float = 10.0
    JIRA_ALLOWED_DOMAINS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_JIRA_ALLOWED_DOMAINS)
    )
    JIRA_REQUIRE_HTTPS: bool = True
    JIRA_BLOCK_PRIVATE_IPS: bool = True
    WORKFLOW_DISPATCH_TIMEOUT_SECONDS: float = 10.0
    WORKFLOW_EVIDENCE_BASE_URL: str | None = None
    TEAMS_TIMEOUT_SECONDS: float = 10.0
    # Teams incoming webhooks are validated with SSRF controls and a domain allowlist.
    # This defaults to common Microsoft endpoints and can be overridden via env for self-host.
    TEAMS_WEBHOOK_ALLOWED_DOMAINS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_TEAMS_WEBHOOK_ALLOWED_DOMAINS)
    )
    TEAMS_WEBHOOK_REQUIRE_HTTPS: bool = True
    TEAMS_WEBHOOK_BLOCK_PRIVATE_IPS: bool = True

    # GitHub Actions workflow dispatch
    GITHUB_ACTIONS_ENABLED: bool = False
    GITHUB_ACTIONS_OWNER: str | None = None
    GITHUB_ACTIONS_REPO: str | None = None
    GITHUB_ACTIONS_WORKFLOW_ID: str | None = None
    GITHUB_ACTIONS_REF: str = "main"
    GITHUB_ACTIONS_TOKEN: str | None = None

    # GitLab CI trigger
    GITLAB_CI_ENABLED: bool = False
    GITLAB_CI_BASE_URL: str = "https://gitlab.com"
    GITLAB_CI_PROJECT_ID: str | None = None
    GITLAB_CI_REF: str = "main"
    GITLAB_CI_TRIGGER_TOKEN: str | None = None

    # Generic CI webhook trigger
    GENERIC_CI_WEBHOOK_ENABLED: bool = False
    GENERIC_CI_WEBHOOK_URL: str | None = None
    GENERIC_CI_WEBHOOK_BEARER_TOKEN: str | None = None

    # SMTP Email (for carbon alerts)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "alerts@valdrics.ai"

    # GreenOps & Carbon APIs
    WATT_TIME_API_KEY: str | None = None
    ELECTRICITY_MAPS_API_KEY: str | None = None
    CARBON_LOW_INTENSITY_THRESHOLD: float = 250.0
    CARBON_INTENSITY_API_TIMEOUT_SECONDS: float = 5.0

    # Paystack Billing (Nigeria Support)
    PAYSTACK_SECRET_KEY: str | None = None
    PAYSTACK_PUBLIC_KEY: str | None = None
    PAYSTACK_ACTIVATION_PENDING: bool = False
    # Explicit offline-validation escape hatch for CI contract checks.
    # Never enable this in real staging/production deployments.
    ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION: bool = False
    # Monthly plans
    PAYSTACK_PLAN_STARTER: str | None = None
    PAYSTACK_PLAN_GROWTH: str | None = None
    PAYSTACK_PLAN_PRO: str | None = None
    PAYSTACK_PLAN_ENTERPRISE: str | None = None
    # Annual plans (17% discount - 2 months free)
    PAYSTACK_PLAN_STARTER_ANNUAL: str | None = None
    PAYSTACK_PLAN_GROWTH_ANNUAL: str | None = None
    PAYSTACK_PLAN_PRO_ANNUAL: str | None = None
    PAYSTACK_PLAN_ENTERPRISE_ANNUAL: str | None = None
    PAYSTACK_DEFAULT_CHECKOUT_CURRENCY: str = "NGN"
    PAYSTACK_ENABLE_USD_CHECKOUT: bool = False
    PAYSTACK_WEBHOOK_ALLOWED_IPS: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PAYSTACK_WEBHOOK_ALLOWED_IPS)
    )
