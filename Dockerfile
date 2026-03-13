# ============================================================
# STAGE 1: Build dependencies
# ============================================================
# python:3.12-slim as of 2026-02-28
FROM python:3.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c AS builder

# Labels for OCI compliance
LABEL org.opencontainers.image.source="https://github.com/valdrics/valdrics"
LABEL org.opencontainers.image.description="Valdrics AI - Autonomous FinOps & GreenOps Guardian"
LABEL org.opencontainers.image.licenses="BUSL-1.1"

WORKDIR /app

ARG UV_VERSION=0.10.9

# Install uv for fast dependency management
ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_HTTP_TIMEOUT=120
RUN pip install --no-cache-dir "uv==${UV_VERSION}"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install third-party dependencies from the committed lockfile before copying app code.
RUN uv sync --frozen --no-dev --no-editable --no-install-project

# Copy application code and install the project itself from the same lockfile.
COPY app ./app
RUN uv sync --frozen --no-dev --no-editable

# ============================================================
# STAGE 2: Runtime (minimal image)
# ============================================================
FROM python:3.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c AS runtime

WORKDIR /app

# Install only the probe/runtime tools required by shipped container contracts.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y curl procps && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy the lock-synchronized virtual environment from the builder image.
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

# Metadata and Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/opt/venv/bin:$PATH

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail --silent --show-error http://127.0.0.1:8000/health/live || exit 1

EXPOSE 8000

CMD ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]
