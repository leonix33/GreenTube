#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Postgres + Redis (optional but recommended)"
cd "$ROOT/infra"
docker compose up -d || echo "Docker compose skipped/failed — seed catalog still works without DB"

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

echo "==> Starting API on :8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
