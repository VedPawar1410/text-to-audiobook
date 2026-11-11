#!/usr/bin/env bash
# Run Narrate for everyday use: the API and a production build of the web app, together.
#
#   ./scripts/start.sh              this computer only             -> http://localhost:3000
#   ./scripts/start.sh --tailscale  your own devices, anywhere      -> https://<this-mac>.<tailnet>.ts.net
#   ./scripts/start.sh --phone      phones on the same Wi-Fi       -> http://<this computer's IP>:3000
#
# Ctrl-C stops everything. The production server is used (not `next dev`) because it's faster and
# because Next.js's dev server blocks pages opened from another device. The API only ever
# listens on 127.0.0.1: other devices reach it through the web app's /api proxy.
#
# --tailscale (recommended for a phone): Tailscale Serve gives this computer a real HTTPS address
# that only devices signed in to your Tailscale account can open, on any network. The web app
# itself stays on 127.0.0.1; nothing is opened on the local Wi-Fi, and the serve is switched off
# again on exit. Needs the free Tailscale app on this computer and the phone (see the README).
# --phone: Narrate has no login, so it lets anyone on that Wi-Fi use it. Fine at home; not on
# public Wi-Fi.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/services/api"
WEB="$ROOT/apps/web"
MODE="${1:-local}"
case "$MODE" in
  local | --tailscale) HOST=127.0.0.1 ;;
  --phone) HOST=0.0.0.0 ;;
  *) echo "Usage: ./scripts/start.sh [--tailscale | --phone]" >&2; exit 1 ;;
esac

if [ ! -d "$API/.venv" ] || [ ! -d "$WEB/node_modules" ]; then
  echo "Run ./scripts/setup.sh first." >&2
  exit 1
fi

TAILSCALE=""
if [ "$MODE" = "--tailscale" ]; then
  # The CLI is on the PATH on Linux and with the open-source macOS build; the Mac app bundles it
  if command -v tailscale >/dev/null 2>&1; then
    TAILSCALE="$(command -v tailscale)"
  elif [ -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ]; then
    TAILSCALE=/Applications/Tailscale.app/Contents/MacOS/Tailscale
  else
    echo "Tailscale isn't installed. Get the free app from https://tailscale.com/download and sign in." >&2
    exit 1
  fi
  if ! "$TAILSCALE" status >/dev/null 2>&1; then
    echo "Tailscale is installed but not connected: open the Tailscale app and sign in." >&2
    exit 1
  fi
fi

# Rebuild the web app only when its code changed since the last build, or when the last build
# wasn't made here (e.g. a showcase build with NEXT_PUBLIC_DEMO=1, which has no backend)
if [ ! -f "$WEB/.next/narrate-local-build" ] || [ -n "$(cd "$WEB" && find src next.config.ts package-lock.json -newer .next/narrate-local-build 2>/dev/null | head -1)" ]; then
  echo "Building the web app (about a minute, only after changes)..."
  (cd "$WEB" && NEXT_PUBLIC_DEMO= npm run build >/dev/null && touch .next/narrate-local-build)
fi

(cd "$API" && exec uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning) &
api_pid=$!
(cd "$WEB" && exec npx next start --hostname "$HOST" --port 3000) &
web_pid=$!

stop() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
  if [ -n "$TAILSCALE" ]; then
    "$TAILSCALE" serve --https=443 off >/dev/null 2>&1 || true  # --bg serves persist until switched off
  fi
}
trap stop EXIT INT TERM

echo ""
echo "Narrate is starting: http://localhost:3000"
if [ "$MODE" = "--phone" ]; then
  ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true)"
  ip="${ip:-YOUR-COMPUTER-IP}"  # (no apostrophes inside ${...}: bash 3.2 can't parse them)
  echo "On your phone (same Wi-Fi):  http://$ip:3000"
fi
if [ -n "$TAILSCALE" ]; then
  # The first time, Tailscale may print a link to switch on HTTPS certificates for your account
  "$TAILSCALE" serve --bg --https=443 http://127.0.0.1:3000
  url="$("$TAILSCALE" serve status 2>/dev/null | grep -o 'https://[^ ]*' | head -1 || true)"
  echo "On your phone (any network, your devices only):  ${url:-see the address above}"
fi
echo "Ctrl-C stops it."

# bash 3.2 has no `wait -n`: stop when either server exits
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
