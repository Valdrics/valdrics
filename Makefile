# Valdrics Makefile
# Developer convenience commands using uv

.PHONY: help install dev test lint format security clean docker-build docker-up docker-down observability observability-down helm-install env-dev env-compose bootstrap-local-db clean-local-db smoke-local-db verify-managed-bundle public-quality docs-hygiene

# Default target
help:
	@echo "Valdrics Development Commands"
	@echo ""
	@echo "  make install     - Install dependencies with uv"
	@echo "  make env-dev     - Generate deterministic .env.dev for local sqlite development"
	@echo "  make env-compose - Generate deterministic .env.compose.dev for local docker compose development"
	@echo "  make bootstrap-local-db - Bootstrap current ORM schema into local sqlite without replaying legacy migrations"
	@echo "  make clean-local-db - Remove local sqlite bootstrap artifacts from the repo root"
	@echo "  make smoke-local-db - Prove the local sqlite bootstrap path reaches a healthy app state"
	@echo "  make verify-managed-bundle ENVIRONMENT=<staging|production> - Verify runtime, migration, and deployment artifacts stay coherent"
	@echo "  make public-quality [DASHBOARD_URL=http://localhost:5174] - Run public smoke + a11y + perf + visual gates"
	@echo "  make docs-hygiene - Fail on orphaned dated docs and prohibited active duplicates"
	@echo "  make dev         - Start development servers (auto-uses .env.dev when present)"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"
	@echo "  make security    - Run security checks"
	@echo "  make clean       - Clean build artifacts"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start the local docker compose stack"
	@echo "  make observability - Start Prometheus/Grafana stack for local compose"
	@echo ""
	@echo "Deployment:"
	@echo "  make helm-install  - Install to Kubernetes with Helm"
	@echo "  make migrate       - Run database migrations"
	@echo "  make deploy ENVIRONMENT=<staging|production> VERSION=<immutable-release-tag> API_IMAGE_DIGEST=<sha256:...> DASHBOARD_IMAGE_DIGEST=<sha256:...> - Generate and verify the Koyeb release bundle"

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

public-quality:
	@/bin/bash -lc 'ARGS=""; if [ -n "$(DASHBOARD_URL)" ]; then ARGS="--dashboard-url $(DASHBOARD_URL) --skip-webserver"; fi; uv run python3 scripts/run_public_frontend_quality_gate.py $$ARGS'

docs-hygiene:
	uv run python3 scripts/verify_docs_archive_hygiene.py

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
	rm -rf .coverage coverage.xml htmlcov
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

# Kubernetes/Helm
helm-lint:
	helm lint helm/valdrics/

helm-template:
	helm template valdrics helm/valdrics/ --debug

helm-install:
	helm install valdrics helm/valdrics/ \
		--set existingSecrets.name=valdrics-secrets

helm-upgrade:
	helm upgrade valdrics helm/valdrics/

helm-uninstall:
	helm uninstall valdrics

# Pre-commit
hooks-install:
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

hooks-run:
	uv run pre-commit run --all-files

# OpenAPI
generate-client:
	./scripts/generate-api-client.sh

# ============================================================================
# Deployment (Koyeb)
# ============================================================================

deploy:
	@test -n "$(ENVIRONMENT)" || (echo "ENVIRONMENT must be set to staging or production" && exit 1)
	@test -n "$(VERSION)" || (echo "VERSION must be set to an immutable release tag" && exit 1)
	@test -n "$(API_IMAGE_DIGEST)" || (echo "API_IMAGE_DIGEST must be set to a sha256:<64-hex> digest from the GHCR publish workflow" && exit 1)
	@test -n "$(DASHBOARD_IMAGE_DIGEST)" || (echo "DASHBOARD_IMAGE_DIGEST must be set to a sha256:<64-hex> digest from the GHCR publish workflow" && exit 1)
	@test -f ".runtime/$(ENVIRONMENT).env" || (echo "Missing .runtime/$(ENVIRONMENT).env. Generate the managed runtime env first." && exit 1)
	@echo "📦 Generating Koyeb release bundle for $(ENVIRONMENT) with immutable tag $(VERSION) and digest-pinned promotion refs..."
	uv run python3 scripts/generate_managed_deployment_artifacts.py --environment $(ENVIRONMENT) --runtime-env-file .runtime/$(ENVIRONMENT).env --release-tag $(VERSION) --api-image-digest $(API_IMAGE_DIGEST) --dashboard-image-digest $(DASHBOARD_IMAGE_DIGEST)
	uv run python3 scripts/verify_managed_deployment_bundle.py --environment $(ENVIRONMENT)
	@echo "✅ Release bundle ready: .runtime/deploy/$(ENVIRONMENT)/koyeb-release.json"
	@echo "Next step: follow docs/runbooks/koyeb_release_promotion.md"

deploy-status:
	@echo "Koyeb status:"
	koyeb service list --app valdrics
