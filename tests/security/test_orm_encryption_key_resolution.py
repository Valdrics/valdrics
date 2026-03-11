from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.models._encryption import clear_encryption_key_cache, get_encryption_key


def test_get_encryption_key_reads_current_settings_without_module_cache() -> None:
    first = SimpleNamespace(ENCRYPTION_KEY="first-key")
    second = SimpleNamespace(ENCRYPTION_KEY="second-key")

    with patch("app.shared.core.config.get_settings", side_effect=[first, second]):
        assert get_encryption_key() == "first-key"
        assert get_encryption_key() == "second-key"


def test_get_encryption_key_requires_value() -> None:
    with patch(
        "app.shared.core.config.get_settings",
        return_value=SimpleNamespace(ENCRYPTION_KEY=""),
    ):
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY not set"):
            get_encryption_key()


def test_clear_encryption_key_cache_is_safe_noop() -> None:
    clear_encryption_key_cache()
