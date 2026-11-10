#!/usr/bin/env bash
# Run Narrate for everyday use: the API and a production build of the web app, together.
#
#   ./scripts/start.sh           this computer only           -> http://localhost:3000
#   ./scripts/start.sh --phone   also phones on the same Wi-Fi -> http://<this computer's IP>:3000
#
# Ctrl-C stops both. The production server is used (not `next dev`) because it's faster and
# because Next.js's dev server blocks pages opened from another device. The API only ever
# listens on 127.0.0.1: a phone reaches it through the web app's /api proxy.
# Narrate has no login, so --phone lets anyone on that network use it. Fine at home; not on
# public Wi-Fi.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/services/api"
WEB="$ROOT/apps/web"
HOST=127.0.0.1
if [ "${1:-}" = "--phone" ]; then
  HOST=0.0.0.0
fi

if [ ! -d "$API/.venv" ] || [ ! -d "$WEB/node_modules" ]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

# Rebuild the web app only when its code changed since the last build
if [ ! -f "$WEB/.next/BUILD_ID" ] || [ -n "$(cd "$WEB" && find src next.config.ts package-lock.json -newer .next/BUILD_ID 2>/dev/null | head -1)" ]; then
  echo "Building the web app (about a minute, only after changes)..."
  (cd "$WEB" && npm run build >/dev/null)
fi

(cd "$API" && exec uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning) &
api_pid=$!
(cd "$WEB" && exec npx next start --hostname "$HOST" --port 3000) &
web_pid=$!
trap 'kill $api_pid $web_pid 2>/dev/null || true' EXIT INT TERM

echo ""
echo "Narrate is starting: http://localhost:3000"
if [ "$HOST" = "0.0.0.0" ]; then
  ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true)"
  ip="${ip:-YOUR-COMPUTER-IP}"  # (no apostrophes inside ${...}: bash 3.2 can't parse them)
  echo "On your phone (same Wi-Fi):  http://$ip:3000"
fi
echo "Ctrl-C stops it."

# bash 3.2 has no `wait -n`: stop when either server exits
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
