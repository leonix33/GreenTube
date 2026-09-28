#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/web"
if [[ ! -d node_modules ]]; then
  npm install
fi
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

# App Router only — a partial .next (page.js / _document.js missing) crashes at runtime.
# Default: fresh cache each dev start. Set KEEP_NEXT=1 to reuse .next for faster restarts.
if [[ "${KEEP_NEXT:-}" != "1" ]]; then
  if [[ -d .next ]]; then
    echo "==> Clearing .next (use KEEP_NEXT=1 to skip)"
    rm -rf .next
  fi
elif [[ -d .next ]] && [[ ! -f .next/server/app/page.js ]]; then
  echo "==> Removing broken .next cache"
  rm -rf .next
fi

exec npm run dev
