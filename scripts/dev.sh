#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/3] Starting backend (FastAPI) ..."
(
  cd "${ROOT_DIR}/server"
  # Use your current python env (conda/venv). Ensure deps installed:
  #   pip install -r requirements.txt
  uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
) &
BACKEND_PID=$!

echo "[2/3] Starting frontend (Vite) ..."
(
  cd "${ROOT_DIR}/frontend"
  if [[ ! -f .env ]]; then
    cp .env.example .env
  fi
  npm install
  npm run dev
)

echo "[3/3] Shutting down backend ..."
kill "${BACKEND_PID}" >/dev/null 2>&1 || true
