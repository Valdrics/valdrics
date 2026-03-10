from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_makefile_local_dev_targets_use_env_dev_bootstrap_and_smoke() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "make env-dev" in text
    assert "make bootstrap-local-db" in text
    assert "make smoke-local-db" in text
    assert "source .env.dev" in text
    assert "scripts/bootstrap_local_sqlite_schema.py" in text
    assert "scripts/smoke_test_local_sqlite_bootstrap.py" in text


def test_local_docs_point_sqlite_users_to_bootstrap_not_alembic_history() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    deployment = (REPO_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    db_overview = (
        REPO_ROOT / "docs/architecture/database_schema_overview.md"
    ).read_text(encoding="utf-8")

    assert "make env-dev" in readme
    assert "make bootstrap-local-db" in readme
    assert "`TESTING=false`" in readme
    assert "cp .env.dev .env" not in readme
    assert "historical Alembic chain" in readme

    assert "make bootstrap-local-db" in deployment
    assert "Do not replay the historical Alembic graph against local sqlite" in deployment

    assert "make bootstrap-local-db" in db_overview
    assert "Do not replay the historical Alembic graph" in db_overview
    assert "against sqlite" in db_overview


def test_sqlite_alembic_replay_is_explicitly_blocked_for_local_sqlite() -> None:
    env_text = (REPO_ROOT / "migrations/env.py").read_text(encoding="utf-8")

    assert "_sqlite_replay_disabled_error_message" in env_text
    assert "make bootstrap-local-db" in env_text
    assert "ALLOW_SQLITE_ALEMBIC_COMPAT" not in env_text
    assert not (REPO_ROOT / "app/shared/db/alembic_sqlite_ops.py").exists()


def test_runtime_config_has_no_branding_compat_normalizer() -> None:
    config_validation = (
        REPO_ROOT / "app/shared/core/config_validation.py"
    ).read_text(encoding="utf-8")
    config = (REPO_ROOT / "app/shared/core/config.py").read_text(encoding="utf-8")

    assert "normalize_branding" not in config_validation
    assert "legacy_app_name_normalized" not in config_validation
    assert "APP_NAME must be set to the canonical product name 'Valdrics'." in (
        config_validation
    )
    assert "_normalize_branding" not in config
