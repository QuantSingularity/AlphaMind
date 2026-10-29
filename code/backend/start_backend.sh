#!/usr/bin/env sh
# ---------------------------------------------------------------------------
# AlphaMind backend entrypoint.
#
# Launches the FastAPI app with uvicorn. Behaviour is configurable through
# environment variables so the same image works across local, staging, and
# production without changes:
#
#   API_HOST        bind address            (default 0.0.0.0)
#   API_PORT        bind port               (default 8000)
#   WEB_CONCURRENCY number of workers       (default 1)
#   LOG_LEVEL       uvicorn log level       (default info)
#   RUN_MIGRATIONS  run alembic on boot     (default false)
# ---------------------------------------------------------------------------
set -eu

HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Optionally apply database migrations before serving traffic.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations (alembic upgrade head)..."
  alembic upgrade head
fi

echo "Starting AlphaMind backend on ${HOST}:${PORT} (workers=${WORKERS})"
exec python -m uvicorn app.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --log-level "${LOG_LEVEL}"
