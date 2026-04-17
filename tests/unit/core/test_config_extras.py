from unittest.mock import patch

from app.shared.core.config import Settings, get_settings
from app.shared.core.config_sections_core import CoreRuntimeSettings
from app.shared.core.config_sections_governance import GovernanceSettings
from app.shared.core.config_sections_integrations import IntegrationSettings
from app.shared.core.config_sections_security import SecuritySettings

FAKE_KDF_SALT = "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s="


def test_settings_excludes_removed_shared_coordination_settings() -> None:
    with patch.dict("os.environ", {}, clear=True):
        Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            SUPABASE_JWT_SECRET="x" * 32,
            ENCRYPTION_KEY="k" * 32,
            CSRF_SECRET_KEY="c" * 32,
            KDF_SALT=FAKE_KDF_SALT,
            TESTING=False,
            _env_file=None,
        )

        assert "REDIS_URL" not in Settings.model_fields
        assert "REDIS_HOST" not in Settings.model_fields
        assert "REDIS_PORT" not in Settings.model_fields
        assert "UPSTASH_REDIS_URL" not in Settings.model_fields
        assert "UPSTASH_REDIS_TOKEN" not in Settings.model_fields
        assert "CIRCUIT_BREAKER_DISTRIBUTED_STATE" not in Settings.model_fields
        assert "CIRCUIT_BREAKER_DISTRIBUTED_KEY_PREFIX" not in Settings.model_fields


def test_get_settings_does_not_mutate_csrf_key():
    class DummySettings:
        CSRF_SECRET_KEY = ""
        ENVIRONMENT = "development"

        @property
        def is_production(self) -> bool:
            return False

    get_settings.cache_clear()
    with patch("app.shared.core.config.Settings", return_value=DummySettings()):
        settings = get_settings()
        assert settings.CSRF_SECRET_KEY == ""


def test_get_settings_caches_singleton():
    class DummySettings:
        CSRF_SECRET_KEY = "x"
        ENVIRONMENT = "development"

        @property
        def is_production(self) -> bool:
            return False

    get_settings.cache_clear()
    with patch("app.shared.core.config.Settings", return_value=DummySettings()):
        first = get_settings()
        second = get_settings()
        assert first is second


def test_config_section_fields_are_unique() -> None:
    field_owners: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}

    for section in (
        CoreRuntimeSettings,
        SecuritySettings,
        IntegrationSettings,
        GovernanceSettings,
    ):
        for field_name in getattr(section, "__annotations__", {}):
            owner = field_owners.get(field_name)
            if owner is None:
                field_owners[field_name] = section.__name__
                continue
            duplicates.setdefault(field_name, [owner]).append(section.__name__)

    assert duplicates == {}


def test_list_backed_settings_fields_use_default_factories() -> None:
    list_fields = (
        "WEBHOOK_ALLOWED_DOMAINS",
        "TRUSTED_PROXY_CIDRS",
        "CORS_ORIGINS",
        "ENCRYPTION_FALLBACK_KEYS",
        "JIRA_ALLOWED_DOMAINS",
        "TEAMS_WEBHOOK_ALLOWED_DOMAINS",
        "PAYSTACK_WEBHOOK_ALLOWED_IPS",
        "ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS",
        "SUPPORTED_CURRENCIES",
        "AWS_SUPPORTED_REGIONS",
    )

    for field_name in list_fields:
        assert Settings.model_fields[field_name].default_factory is not None
