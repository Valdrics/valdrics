from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    db_overview = (
        REPO_ROOT / "docs/architecture/database_schema_overview.md"
    ).read_text(encoding="utf-8")

    assert "make env-dev" in readme
    assert "make env-compose" in readme
    assert "make bootstrap-local-db" in readme
    assert "make docker-up" in readme
    assert "`TESTING=false`" in readme
    assert ".env.compose.dev" in readme
    assert "checked-in compose topology is cacheless by" in readme
    assert "make docker-up-redis" not in readme
    assert "docker-compose.redis.yml" not in readme
    assert "Postgres/Redis docker compose path" not in readme
    assert "dockerized Postgres/Redis path" not in readme
    assert "without Redis" not in readme
    assert "cp .env.dev .env" not in readme
    assert "docker-compose up -d" not in readme
    assert "Zero secrets stored." not in readme
    assert "historical Alembic chain" in readme

    assert "make bootstrap-local-db" in db_overview
    assert "Do not replay the historical Alembic graph" in db_overview
    assert "against sqlite" in db_overview


def test_local_compose_targets_require_generated_env_and_compose_v2() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "make env-compose" in makefile
    assert "docker compose --env-file .env.compose.dev up -d" in makefile
    assert "docker-up-redis" not in makefile
    assert "docker-compose.redis.yml" not in makefile
    assert "docker compose --env-file .env.compose.dev down" in makefile
    assert (
        "docker compose --env-file .env.compose.dev -f docker-compose.observability.yml up -d"
        in makefile
    )
    assert (
        "docker compose --env-file .env.compose.dev -f docker-compose.observability.yml down"
        in makefile
    )
    assert "docker-compose -f docker-compose.observability.yml down" not in makefile
    assert "admin/valdrics" not in makefile
    assert "GRAFANA_PASSWORD in .env.compose.dev" in makefile


def test_local_compose_bootstraps_postgres_and_keeps_shared_state_out_of_checked_in_stack() -> None:
    compose = _load_yaml(REPO_ROOT / "docker-compose.yml")
    observability = _load_yaml(REPO_ROOT / "docker-compose.observability.yml")
    prometheus = _load_yaml(REPO_ROOT / "prometheus/prometheus.yml")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert isinstance(compose, dict)
    assert isinstance(observability, dict)
    assert isinstance(prometheus, dict)

    services = compose["services"]
    assert services["postgres"]["image"] == "postgres:16.8-alpine"
    assert "redis" not in services
    assert "redis" not in compose.get("volumes", {})
    assert "redis" not in observability["services"]
    assert "redis_data" not in observability.get("volumes", {})
    assert "redis" not in {
        str(scrape_config["job_name"])
        for scrape_config in prometheus["scrape_configs"]
    }
    assert "docker compose --env-file .env.compose.dev up -d" in makefile_text
    assert "docker-compose.redis.yml" not in makefile_text


def test_local_compose_api_has_no_checked_in_shared_state_dependency() -> None:
    compose = _load_yaml(REPO_ROOT / "docker-compose.yml")
    assert isinstance(compose, dict)

    api_depends = compose["services"]["api"]["depends_on"]
    assert api_depends["postgres"]["condition"] == "service_healthy"
    assert "redis" not in api_depends
    assert "environment" not in compose["services"]["api"]


def test_sqlite_alembic_replay_is_explicitly_blocked_for_local_sqlite() -> None:
    env_text = (REPO_ROOT / "migrations/env.py").read_text(encoding="utf-8")

    assert "_sqlite_replay_disabled_error_message" in env_text
    assert "make bootstrap-local-db" in env_text
    assert "ALLOW_SQLITE_ALEMBIC_COMPAT" not in env_text
    assert not (REPO_ROOT / "app/shared/db/alembic_sqlite_ops.py").exists()


def test_runtime_config_has_no_branding_compat_normalizer() -> None:
    config_validation = (REPO_ROOT / "app/shared/core/config_validation.py").read_text(
        encoding="utf-8"
    )
    config = (REPO_ROOT / "app/shared/core/config.py").read_text(encoding="utf-8")

    assert "normalize_branding" not in config_validation
    assert "legacy_app_name_normalized" not in config_validation
    assert "APP_NAME must be set to the canonical product name 'Valdrics'." in (
        config_validation
    )
    assert "_normalize_branding" not in config
