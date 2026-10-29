#!/usr/bin/env bash
# One-command demo: builds the UI, loads synthetic data, runs the app on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")"
[ -d backend/.venv ] || { python3 -m venv backend/.venv && backend/.venv/bin/pip install -q -r backend/requirements.txt; }
[ -d frontend/node_modules ] || (cd frontend && npm install --silent)
(cd frontend && npm run build --silent)
cd backend
.venv/bin/python -m app.seed
.venv/bin/python -m app.process
echo "Open http://localhost:8000  (demo password: demo123, e.g. sup_vizag)"
exec .venv/bin/uvicorn app.main:app --port 8000
