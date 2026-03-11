# Deployment Guide

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL (or Supabase)
- Redis (for caching/Celery)

---

## Local Development

```bash
# Clone and setup
git clone https://github.com/Valdrics/valdrics.git
cd valdrics

# Install dependencies (using uv)
uv sync

# Fast local sqlite path
make env-dev
make bootstrap-local-db
make dev
```

For the full local Postgres/Redis path instead:

```bash
# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations (Postgres only)
uv run alembic upgrade head

# Start API
uv run uvicorn app.main:app --reload
```

Do not replay the historical Alembic graph against local sqlite. Use
`scripts/bootstrap_local_sqlite_schema.py` or `make bootstrap-local-db` for the local sqlite profile.

---

## Docker Deployment

```bash
# Build
export VERSION=2026.03.06
docker build -t valdrics/api:${VERSION} .

# Run
docker run -d \
  --name valdrics-api \
  -p 8000:8000 \
  --env-file .env \
  valdrics/api:${VERSION}
```

---

## Kubernetes Production

### Quick Start

```bash
# Add the helm chart (if using a repo) or use the local one
helm upgrade --install valdrics ./helm/valdrics --namespace valdrics --create-namespace

# Verify deployment
kubectl get pods -n valdrics -l app.kubernetes.io/name=valdrics
```

### Helm Chart Structure

| Component | Description |
|---|---|
| `templates/deployment.yaml` | API deployment and probes |
| `templates/worker-deployment.yaml` | Background worker deployment |
| `templates/service.yaml` | Internal services |
| `templates/hpa.yaml` | Optional autoscaling |
| `templates/ingress.yaml` | External access with TLS |

### Required Secrets

Create before deployment:
```bash
kubectl create secret generic valdrics-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=ENCRYPTION_KEY='your-key' \
  --from-literal=OPENAI_API_KEY='sk-...'
```

---

## Load Testing

Before production, validate performance:

```bash
# Install k6
brew install k6  # or apt/yum

# Run load test
k6 run loadtest/k6-test.js

# Expected results:
# - p95 latency < 500ms
# - Error rate < 1%
```

---

## Monitoring

### Prometheus Metrics
- Endpoint: `/_internal/metrics`
- Exposure: cluster-internal only, or token-gated with `INTERNAL_METRICS_AUTH_TOKEN` when the edge cannot fully isolate the path
- Includes: request latency, error rates, active connections

### Health Check
- Liveness: `/health/live`
- Readiness/dependency health: `/health`
- `/health` returns a detailed dependency payload and can return HTTP `503` when critical dependencies are unavailable
- Container images must ship the probe/runtime tools used by the deployment contract, including `curl` for liveness probes and `pgrep` support for worker exec probes

---

## DB Pool Sizing Matrix (Enterprise)

Use an explicit capacity budget instead of static defaults when scaling:

```
max_db_connections_required =
  api_replicas * WEB_CONCURRENCY * (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

Target `max_db_connections_required <= 0.8 * database_max_connections` to preserve headroom for migrations, admin sessions, and background jobs.

| Profile | API Replicas | WEB_CONCURRENCY | DB_POOL_SIZE | DB_MAX_OVERFLOW | Max DB Connections |
|---|---:|---:|---:|---:|---:|
| Dev/Single node | 1 | 2 | 20 | 10 | 60 |
| Production (small) | 2 | 2 | 15 | 5 | 80 |
| Production (medium) | 4 | 3 | 12 | 4 | 192 |
| Production (large) | 6 | 4 | 10 | 3 | 312 |

Scaling rule:
- Scale pods first when CPU saturation or request concurrency rises.
- Increase `DB_POOL_SIZE` only when query queueing persists and DB connection headroom remains.
- For dedicated databases, tune `DB_POOL_SIZE` with worker count and node cores; do not keep free-tier defaults unchanged.

---

## Production Checklist

- [ ] Secrets configured in Kubernetes
- [ ] `API_URL` and `FRONTEND_URL` set to explicit `https://` public domains
- [ ] TLS certificates deployed
- [ ] Database migrations run
- [ ] HPA tested under load
- [ ] Monitoring/alerting configured
- [ ] SBOM generated and reviewed
