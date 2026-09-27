# Build context for this Dockerfile is code/ (see ../docker-compose.yml's
# "context: .. / dockerfile: backend/Dockerfile"), not code/backend/ itself -
# ai_models/ is a sibling of backend/, not a subdirectory of it, so it has
# to be reachable from the build context to be copied into the image.

# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer-cache friendly)
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r alphamind && useradd -r -g alphamind -d /app -s /sbin/nologin alphamind

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=alphamind:alphamind backend/ .
# ai_models/ is imported directly by backend/app/services/backtest_runner.py
# (e.g. `from ai_models.agents import DDPGTradingAgent`) - without this,
# requirements.txt's torch/tensorflow/gymnasium/stable-baselines3 (ai_models'
# own dependencies) would be installed but the package itself would be
# missing, and every such import would fail at runtime.
COPY --chown=alphamind:alphamind ai_models/ ./ai_models/

# Ensure the start script is executable
RUN chmod +x start_backend.sh

# Switch to non-root user
USER alphamind

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command (delegates to the start script for consistent, env-driven boot)
CMD ["./start_backend.sh"]
