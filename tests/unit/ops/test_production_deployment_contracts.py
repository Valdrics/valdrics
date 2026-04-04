from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_helm_values_default_to_ha_api_and_internal_metrics() -> None:
    values = _load_yaml(REPO_ROOT / "helm/valdrics/values.yaml")
    assert isinstance(values, dict)

    assert int(values["replicaCount"]) >= 2
    assert values["env"]["WEB_CONCURRENCY"] == "2"
    assert values["env"]["ENABLE_SCHEDULER"] == "true"
    assert values["podAnnotations"]["prometheus.io/path"] == "/_internal/metrics"
    assert values["externalSecrets"]["enabled"] is True
    assert values["worker"]["podAnnotations"] == {}
    assert values["enforcementWebhook"]["failurePolicy"] == "Fail"
    assert values["enforcementWebhook"]["podDisruptionBudget"]["enabled"] is True
    server_snippet = values["ingress"]["annotations"][
        "nginx.ingress.kubernetes.io/server-snippet"
    ]
    assert "/_internal/metrics" in server_snippet
    assert "location = /metrics" in server_snippet


def test_worker_template_is_conditionally_rendered_and_does_not_embed_beat() -> None:
    text = (REPO_ROOT / "helm/valdrics/templates/worker-deployment.yaml").read_text(
        encoding="utf-8"
    )

    assert "{{- if .Values.worker.enabled }}" in text
    assert ".Values.worker.podAnnotations" in text
    assert ".Values.podAnnotations" not in text
    assert 'include "valdrics.runtimeSecretName" .' in text
    assert "app.shared.core.celery_app:celery_app" in text
    assert '"-B"' not in text
    assert "startupProbe:" in text
    assert "livenessProbe:" in text
    assert "readinessProbe:" in text
    assert "inspect ping" in text


def test_api_template_uses_runtime_secret_helper() -> None:
    text = (REPO_ROOT / "helm/valdrics/templates/deployment.yaml").read_text(
        encoding="utf-8"
    )

    assert 'include "valdrics.runtimeSecretName" .' in text
    assert "name: API_URL" in text
    assert "name: FRONTEND_URL" in text
    assert 'include "valdrics.apiUrl" .' in text
    assert 'include "valdrics.frontendUrl" .' in text


def test_helm_helpers_support_explicit_host_overrides() -> None:
    values_text = (REPO_ROOT / "helm/valdrics/values.yaml").read_text(encoding="utf-8")
    helpers_text = (REPO_ROOT / "helm/valdrics/templates/_helpers.tpl").read_text(
        encoding="utf-8"
    )

    assert "apiHostOverride" in values_text
    assert "frontendHostOverride" in values_text
    assert ".Values.global.apiHostOverride" in helpers_text
    assert ".Values.global.frontendHostOverride" in helpers_text


def test_runtime_healthchecks_use_liveness_only() -> None:
    compose = _load_yaml(REPO_ROOT / "docker-compose.yml")
    prod_compose = _load_yaml(REPO_ROOT / "docker-compose.prod.yml")

    assert isinstance(compose, dict)
    assert isinstance(prod_compose, dict)

    compose_healthcheck = str(compose["services"]["api"]["healthcheck"]["test"]).lower()
    prod_healthcheck = str(
        prod_compose["services"]["api"]["healthcheck"]["test"]
    ).lower()

    assert "/health/live" in compose_healthcheck
    assert "/health/live" in prod_healthcheck
    assert "curl" in compose_healthcheck
    assert "curl" in prod_healthcheck
    assert "urllib" not in compose_healthcheck
    assert "urllib" not in prod_healthcheck


def test_release_images_are_immutable_and_observability_images_are_pinned() -> None:
    compose = _load_yaml(REPO_ROOT / "docker-compose.yml")
    prod_compose = _load_yaml(REPO_ROOT / "docker-compose.prod.yml")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert isinstance(compose, dict)
    assert isinstance(prod_compose, dict)

    assert compose["services"]["prometheus"]["image"] == "prom/prometheus:v2.54.1"
    assert compose["services"]["grafana"]["image"] == "grafana/grafana:11.4.0"
    assert ":latest" not in prod_compose["services"]["api"]["image"]
    assert ":latest" not in prod_compose["services"]["dashboard"]["image"]
    assert "VERSION must be set to an immutable release tag" in makefile_text
    assert (
        "scripts/generate_managed_deployment_artifacts.py --environment $(ENVIRONMENT)"
        in makefile_text
    )
    assert "docs/runbooks/koyeb_release_promotion.md" in makefile_text


def test_local_compose_bootstraps_postgres_and_redis_for_offline_dev() -> None:
    compose = _load_yaml(REPO_ROOT / "docker-compose.yml")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert isinstance(compose, dict)

    services = compose["services"]
    assert services["postgres"]["image"] == "postgres:16.8-alpine"
    assert services["redis"]["image"] == "redis:7.2.5-alpine"

    pg_env = services["postgres"]["environment"]
    pg_ports = services["postgres"]["ports"]
    redis_ports = services["redis"]["ports"]
    dashboard_env = services["dashboard"]["environment"]
    assert "POSTGRES_DB=${POSTGRES_DB:-valdrics}" in pg_env
    assert "POSTGRES_USER=${POSTGRES_USER:-postgres}" in pg_env
    assert (
        "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?Generate .env.compose.dev with `make env-compose` or set POSTGRES_PASSWORD explicitly}"
        in pg_env
    )
    assert "127.0.0.1:5432:5432" in pg_ports
    assert "127.0.0.1:6379:6379" in redis_ports
    assert "ORIGIN=${ORIGIN:-http://localhost:3000}" in dashboard_env

    api_env_files = services["api"]["env_file"]
    assert ".env.compose.dev" in api_env_files
    assert "environment" not in services["api"]

    grafana_env = services["grafana"]["environment"]
    assert (
        "GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:?Generate .env.compose.dev with `make env-compose` or set GRAFANA_PASSWORD explicitly}"
        in grafana_env
    )

    api_depends_on = services["api"]["depends_on"]
    assert api_depends_on["postgres"]["condition"] == "service_healthy"
    assert api_depends_on["redis"]["condition"] == "service_healthy"
    assert "docker compose --env-file .env.compose.dev up -d" in makefile_text
    assert "docker compose --env-file .env.compose.dev down" in makefile_text


def test_dashboard_runtime_requires_explicit_origin_configuration() -> None:
    server_text = (REPO_ROOT / "dashboard" / "server.node.mjs").read_text(
        encoding="utf-8"
    )
    dockerfile_text = (REPO_ROOT / "Dockerfile.dashboard").read_text(encoding="utf-8")

    assert "process.env.ORIGIN" in server_text
    assert "process.env.HOST_HEADER" in server_text
    assert "process.env.PROTOCOL_HEADER" in server_text
    assert "req.headers.host ||" not in server_text
    assert 'CMD ["node", "server.node.mjs"]' in dockerfile_text


def test_backend_dockerfile_healthcheck_uses_curl_liveness_probe() -> None:
    dockerfile_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").lower()
    entrypoint_text = (
        (REPO_ROOT / "scripts/docker-entrypoint.sh").read_text(encoding="utf-8").lower()
    )

    assert "healthcheck" in dockerfile_text
    assert "/health/live" in dockerfile_text
    assert "curl --fail --silent --show-error" in dockerfile_text
    assert "urllib.request" not in dockerfile_text
    assert "procps" in dockerfile_text
    assert 'cmd ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]' in dockerfile_text
    assert "validate_runtime_dependencies" in entrypoint_text
    assert "uvicorn app.main:app" in entrypoint_text


def test_prometheus_contracts_match_internal_metrics_defaults() -> None:
    prometheus_text = (REPO_ROOT / "prometheus/prometheus.yml").read_text(
        encoding="utf-8"
    )

    assert "metrics_path: /_internal/metrics" in prometheus_text


def test_regional_failover_workflow_uses_repo_managed_oidc_aws_auth() -> None:
    workflow_text = (REPO_ROOT / ".github/workflows/regional-failover.yml").read_text(
        encoding="utf-8"
    )

    assert "id-token: write" in workflow_text
    assert "aws_role_to_assume" in workflow_text
    assert "configure_github_oidc_aws_credentials.py" in workflow_text
    assert "FAILOVER_AWS_ROLE_TO_ASSUME" in workflow_text


def test_deployment_docs_match_runtime_contracts() -> None:
    ops_doc = (REPO_ROOT / "docs/DEPLOYMENT.md").read_text(encoding="utf-8")
    release_runbook = (
        REPO_ROOT / "docs/runbooks/koyeb_release_promotion.md"
    ).read_text(encoding="utf-8")
    production_checklist = (
        REPO_ROOT / "docs/runbooks/production_env_checklist.md"
    ).read_text(encoding="utf-8")

    assert "/health/live" in ops_doc
    assert "configured max break-glass window" in ops_doc
    assert "Current supported production deployment profile" in ops_doc
    assert "Koyeb managed services with immutable image promotion" in ops_doc
    assert "Future Scale Profile" in ops_doc
    assert ".github/workflows/publish-release-images.yml" in ops_doc
    assert "verify_dashboard_runtime_contract.py" in ops_doc
    assert "koyeb-release.json" in ops_doc
    assert "promotion_ref" in release_runbook
    assert "ghcr-release.env" in release_runbook
    assert "verify_dashboard_runtime_contract.py" in release_runbook
    assert "verify_dashboard_runtime_contract.py" in production_checklist


def test_root_legacy_deployment_files_are_removed() -> None:
    assert not (REPO_ROOT / "DEPLOYMENT.md").exists()
    assert not (REPO_ROOT / "koyeb.yaml").exists()
    assert not (REPO_ROOT / "koyeb-worker.yaml").exists()
    assert not (REPO_ROOT / "prod.env.template").exists()


def test_frontend_ci_node_version_matches_dashboard_container() -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    sbom_text = (REPO_ROOT / ".github/workflows/sbom.yml").read_text(encoding="utf-8")
    dockerfile_text = (REPO_ROOT / "Dockerfile.dashboard").read_text(encoding="utf-8")

    assert 'NODE_VERSION: "24.14.0"' in ci_text
    assert 'NODE_VERSION: "24.14.0"' in sbom_text
    assert "ARG NODE_BASE_IMAGE=node:24.14.0-slim" in dockerfile_text


def test_readme_does_not_reference_missing_raw_k8s_manifests() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "| **K8s Manifests** | `k8s/` |" not in readme


def test_dead_legacy_landing_component_is_removed() -> None:
    assert not (REPO_ROOT / "dashboard/LandingHero_legacy.svelte").exists()
