from __future__ import annotations

from pathlib import Path

from app.shared.core.config import Settings
from app.shared.core.migration_settings import MigrationSettings
from app.shared.core.runtime_paths import DEFAULT_ENV_FILE, PROJECT_ROOT, STATIC_DIR


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_paths_anchor_to_repo_root() -> None:
    assert PROJECT_ROOT == REPO_ROOT
    assert STATIC_DIR == REPO_ROOT / "app" / "static"
    assert DEFAULT_ENV_FILE == REPO_ROOT / ".env"


def test_settings_default_env_file_is_absolute_repo_path() -> None:
    env_file = Path(str(Settings.model_config["env_file"]))

    assert env_file.is_absolute()
    assert env_file == REPO_ROOT / ".env"


def test_migration_settings_default_env_file_is_absolute_repo_path() -> None:
    env_file = Path(str(MigrationSettings.model_config["env_file"]))

    assert env_file.is_absolute()
    assert env_file == REPO_ROOT / ".env"
