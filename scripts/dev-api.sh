#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${SKIP_DOCKER:-}" == "1" ]] || ! command -v docker >/dev/null 2>&1; then
  echo "==> Postgres + Redis skipped (set SKIP_DOCKER=0 and install Docker Desktop to enable)"
else
  echo "==> Postgres + Redis (optional — catalog works with MongoDB only)"
  cd "$ROOT/infra"
  docker compose up -d 2>/dev/null || echo "Docker compose skipped/failed — OK for MongoDB catalog + playback"
fi

echo "==> API venv + deps"
cd "$ROOT/services/api"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> Generate open demo audio"
python -c "from app.catalog_seed import ensure_demo_audio; ensure_demo_audio(); print('audio ok')"

if docker compose -f "$ROOT/infra/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
  echo "==> Seed Postgres catalog"
  export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://greentube:greentube@localhost:5432/greentube}"
  PYTHONPATH=. python scripts/seed_catalog.py || echo "DB seed skipped"
fi

API_PORT="${API_PORT:-8000}"
if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  echo "==> API already running on :${API_PORT} ($(curl -sf "http://127.0.0.1:${API_PORT}/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("catalog_source","?"), "mongodb="+str(d.get("mongodb",{}).get("connected")))' 2>/dev/null || echo ok))"
  echo "    Health: http://localhost:${API_PORT}/health"
  echo "    No need to start again — use ./scripts/dev-web.sh and open http://localhost:3000"
  exit 0
fi
if lsof -nP -iTCP:"${API_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: Port ${API_PORT} is in use but /health did not respond. Free the port or set API_PORT=8001"
  exit 1
fi

echo "==> Starting API on :${API_PORT}"
uvicorn app.main:app --reload --host 0.0.0.0 --port "${API_PORT}"
