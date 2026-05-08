#!/usr/bin/env bash
# Start the FastAPI backend and the Vite dev server side by side.
# Usage: ./scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Activate venv if one is present (otherwise use system Python).
if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

PYTHON_BIN="${PYTHON:-python3}"

# LLM features are opt-in. Scrub ANTHROPIC_API_KEY from the backend env unless
# ENABLE_LLM is explicitly set. Run dev.sh as `ENABLE_LLM=true ./scripts/dev.sh`
# (with ANTHROPIC_API_KEY exported) to turn the LLM endpoints back on.
if [ "${ENABLE_LLM:-}" != "true" ] && [ "${ENABLE_LLM:-}" != "1" ]; then
  unset ANTHROPIC_API_KEY
fi

echo "[dev.sh] starting backend on :8000 (ENABLE_LLM=${ENABLE_LLM:-false})"
"$PYTHON_BIN" -m uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

cleanup() {
  echo
  echo "[dev.sh] shutting down (backend pid $BACKEND_PID)"
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[dev.sh] starting frontend on :5173"
cd "$ROOT/web"
npm run dev
