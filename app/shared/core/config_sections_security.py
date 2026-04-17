from pydantic import Field


class SecuritySettings:
    # Database
    DATABASE_URL: str | None = None  # Required in prod, optional in dev/test
    DB_SSL_MODE: str = "require"  # Options: disable, require, verify-ca, verify-full
    DB_SSL_CA_CERT_PATH: str | None = None  # Path to CA cert for verify modes
    # Conservative default for broad compatibility; tune based on worker count and DB capacity.
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False
    DB_SLOW_QUERY_THRESHOLD_SECONDS: float = 0.2
    # Set true only when an external DB pooler (e.g. Supavisor transaction pooler)
    # is explicitly used and double-pooling is undesirable.
    DB_USE_NULL_POOL: bool = False
    DB_EXTERNAL_POOLER: bool = False
    # Local-only escape from replaying the historical Postgres Alembic graph on sqlite.
    # When enabled, the app bootstraps current ORM metadata and stamps the current head.
    LOCAL_SQLITE_BOOTSTRAP: bool = False
    # Tests default to in-memory sqlite to avoid accidental side-effects on real databases.
    # Set true to allow tests to use DATABASE_URL (e.g., integration tests against Postgres).
    ALLOW_TEST_DATABASE_URL: bool = False
    # Enable RLS enforcement listener in tests when running against Postgres.
    ENFORCE_RLS_IN_TESTS: bool = True

    # Supabase Auth
    SUPABASE_URL: str | None = None
    SUPABASE_JWT_SECRET: str | None = None  # Required for auth middleware
    SUPABASE_JWT_ISSUER: str = "supabase"
    JWT_SIGNING_KID: str | None = None

    # OIDC / GCP Workload Identity
    GCP_OIDC_AUDIENCE: str | None = None
    GCP_OIDC_STS_URL: str = "https://sts.googleapis.com/v1/token"
    GCP_OIDC_SCOPE: str = "https://www.googleapis.com/auth/cloud-platform"
    GCP_OIDC_VERIFY_TIMEOUT_SECONDS: int = 10

    # Encryption & Secret Rotation
    ENCRYPTION_KEY: str | None = None
    PII_ENCRYPTION_KEY: str | None = None
    API_KEY_ENCRYPTION_KEY: str | None = None
    ENCRYPTION_FALLBACK_KEYS: list[str] = Field(default_factory=list)
    ENCRYPTION_KEY_CACHE_TTL_SECONDS: int = 3600
    ENCRYPTION_KEY_CACHE_MAX_SIZE: int = 1000
    BLIND_INDEX_KEY: str | None = None  # SEC-06: Separation of keys

    # KDF Settings for password-to-key derivation (SEC-06)
    # PRODUCTION FIX #6: Per-environment encryption salt (not hardcoded)
    # Set via environment variable: export KDF_SALT="<base64-encoded-random-32-bytes>"
    # Generate: python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
    KDF_SALT: str | None = None
    KDF_ITERATIONS: int = 100000
    # Blind index key-stretching to slow offline guessing if key material is exposed.
    BLIND_INDEX_KDF_ITERATIONS: int = 50000
