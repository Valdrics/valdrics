# Valdrics Makefile
# Developer convenience commands using uv

.PHONY: help install dev test lint format security clean docker-build docker-up docker-down observability observability-down env-dev env-compose bootstrap-local-db clean-local-db smoke-local-db verify-managed-bundle render-managed-release-blockers public-quality docs-hygiene

# Default target
help:
	@echo "Valdrics Development Commands"
	@echo ""
	@echo "  make install     - Install dependencies with uv"
	@echo "  make env-dev     - Generate deterministic .env.dev for local sqlite development"
	@echo "  make env-compose - Generate deterministic .env.compose.dev for cacheless local docker compose development"
	@echo "  make bootstrap-local-db - Bootstrap current ORM schema into local sqlite without replaying legacy migrations"
	@echo "  make clean-local-db - Remove local sqlite bootstrap artifacts from the repo root"
	@echo "  make smoke-local-db - Prove the local sqlite bootstrap path reaches a healthy app state"
	@echo "  make verify-managed-bundle ENVIRONMENT=<staging|production> - Verify runtime, migration, and deployment artifacts stay coherent"
	@echo "  make render-managed-release-blockers [NON_SECRET_BUNDLE=true] - Render the cross-environment blocker summary from staging + production bundles"
	@echo "  make public-quality [DASHBOARD_URL=http://localhost:5174] - Run public smoke + a11y + perf + visual gates"
	@echo "  make docs-hygiene - Fail on orphaned dated docs/reports and prohibited active duplicates"
	@echo "  make dev         - Start development servers (auto-uses .env.dev when present)"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make security    - Run security checks"
	@echo "  make clean       - Clean build artifacts"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start the default local docker compose stack (Postgres + API + dashboard)"
	@echo "  make observability - Start Prometheus/Grafana stack for local compose"
	@echo ""
	@echo "Deployment:"
	@echo "  make migrate       - Run database migrations"
	@echo "  make deploy ENVIRONMENT=<staging|production> VERSION=<immutable-release-tag> API_PROMOTION_REF=<repo@sha256:...> [BATCH_PROMOTION_REF=<repo@sha256:...>] - Generate and verify the unified-platform release bundle"

# Development
install:
	uv sync --dev
	cd dashboard && pnpm install

env-dev:
	uv run python3 scripts/generate_local_dev_env.py

env-compose:
	uv run python3 scripts/generate_local_compose_env.py

bootstrap-local-db:
	@/bin/bash -lc 'if [ ! -f .env.dev ]; then echo "Missing .env.dev. Run '\''make env-dev'\'' first."; exit 1; fi; set -a && source .env.dev && set +a && uv run python3 scripts/bootstrap_local_sqlite_schema.py'

clean-local-db:
	@rm -f valdrics_local*.sqlite3 valdrics_local*.sqlite3-journal valdrics_local*.sqlite3-shm valdrics_local*.sqlite3-wal valdrics_local*.sqlite3.bootstrap.lock

smoke-local-db:
	uv run python3 scripts/smoke_test_local_sqlite_bootstrap.py

verify-managed-bundle:
	@test -n "$(ENVIRONMENT)" || (echo "ENVIRONMENT must be set to staging or production" && exit 1)
	uv run python3 scripts/verify_managed_deployment_bundle.py --environment $(ENVIRONMENT)

render-managed-release-blockers:
	@/bin/bash -lc 'ARGS=""; if [ "$(NON_SECRET_BUNDLE)" = "true" ]; then ARGS="--non-secret-deployment-bundle"; fi; uv run python3 scripts/render_managed_release_blocker_summary.py $$ARGS'

public-quality:
	@/bin/bash -lc 'ARGS=""; if [ -n "$(DASHBOARD_URL)" ]; then ARGS="--dashboard-url $(DASHBOARD_URL) --skip-webserver"; fi; uv run python3 scripts/run_public_frontend_quality_gate.py $$ARGS'

docs-hygiene:
	uv run python3 scripts/verify_docs_archive_hygiene.py
	uv run python3 scripts/verify_reports_archive_hygiene.py

dev:
	@if [ -f .env.dev ]; then \
		echo "Starting API server with .env.dev local sqlite bootstrap..."; \
		/bin/bash -lc 'set -a && source .env.dev && set +a && uv run python3 scripts/bootstrap_local_sqlite_schema.py && exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000' & \
	else \
		echo "Starting API server..."; \
		uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	fi
	@echo "Starting dashboard..."
	cd dashboard && pnpm run dev

test:
	uv run pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

test-unit:
	uv run pytest tests/ -v --ignore=tests/integration --ignore=tests/security --ignore=tests/governance

test-fast:
	uv run pytest tests/ -x -q --tb=line

lint:
	uv run ruff check app/ tests/
	uv run ruff format --check app/ tests/

format:
	uv run ruff check --fix app/ tests/
	uv run ruff format app/ tests/

typecheck:
	uv run mypy app/ --ignore-missing-imports

security:
	uv run bandit -r app/ -ll -ii -s B101,B104
	@echo "Running Trivy scan..."
	trivy fs --severity HIGH,CRITICAL .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf __pycache__ app/__pycache__ tests/__pycache__
	rm -rf .coverage coverage.xml htmlcov reports/coverage
	rm -rf dist build *.egg-info

# Docker
docker-build:
	docker build -t valdrics:latest .

docker-up:
	@/bin/bash -lc 'if [ ! -f .env.compose.dev ]; then echo "Missing .env.compose.dev. Run '\''make env-compose'\'' first."; exit 1; fi; docker compose --env-file .env.compose.dev up -d'

docker-down:
	@/bin/bash -lc 'if [ ! -f .env.compose.dev ]; then echo "Missing .env.compose.dev. Run '\''make env-compose'\'' first."; exit 1; fi; docker compose --env-file .env.compose.dev down'

observability:
	@/bin/bash -lc 'if [ ! -f .env.compose.dev ]; then echo "Missing .env.compose.dev. Run '\''make env-compose'\'' first."; exit 1; fi; docker compose --env-file .env.compose.dev -f docker-compose.observability.yml up -d'
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3005 (admin / see GRAFANA_PASSWORD in .env.compose.dev)"
	@echo "Alertmanager: http://localhost:9093"

observability-down:
	@/bin/bash -lc 'if [ ! -f .env.compose.dev ]; then echo "Missing .env.compose.dev. Run '\''make env-compose'\'' first."; exit 1; fi; docker compose --env-file .env.compose.dev -f docker-compose.observability.yml down'

# Database
migrate:
	uv run alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; \
	uv run alembic revision --autogenerate -m "$$name"

# Pre-commit
hooks-install:
	uv run pre-commit install --install-hooks

hooks-run:
	uv run pre-commit run --all-files

# OpenAPI
generate-client:
	./scripts/generate-api-client.sh

# ============================================================================
# Deployment (Unified Platform)
# ============================================================================

deploy:
	@test -n "$(ENVIRONMENT)" || (echo "ENVIRONMENT must be set to staging or production" && exit 1)
	@test -n "$(VERSION)" || (echo "VERSION must be set to an immutable release tag" && exit 1)
	@test -n "$(API_PROMOTION_REF)" || (echo "API_PROMOTION_REF must be set to a digest-pinned Artifact Registry ref (<repo>@sha256:...)" && exit 1)
	@test -f ".runtime/$(ENVIRONMENT).env" || (echo "Missing .runtime/$(ENVIRONMENT).env. Generate the managed runtime env first." && exit 1)
	@echo "📦 Generating unified-platform release bundle for $(ENVIRONMENT) with immutable tag $(VERSION) and digest-pinned Artifact Registry refs..."
	uv run python3 scripts/generate_managed_deployment_artifacts.py --environment $(ENVIRONMENT) --runtime-env-file .runtime/$(ENVIRONMENT).env --release-tag $(VERSION) --api-promotion-ref $(API_PROMOTION_REF) --batch-promotion-ref $(or $(BATCH_PROMOTION_REF),$(API_PROMOTION_REF))
	uv run python3 scripts/verify_managed_deployment_bundle.py --environment $(ENVIRONMENT)
	@echo "✅ Release bundle ready: .runtime/deploy/$(ENVIRONMENT)/artifact-registry-release.json"
	@echo "Next step: follow docs/runbooks/unified_platform_release.md"

deploy-status:
	@echo "Unified platform deploy status:"
	@echo "  - GitHub Actions: .github/workflows/deploy-unified-platform.yml"
	@echo "  - Runtime services: Google Cloud Run / Cloud Run Jobs / Cloud Tasks / Cloud Scheduler"
