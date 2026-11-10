#!/usr/bin/env bash
# One-time setup for Narrate on macOS or Linux. Safe to run again.
#
#   ./scripts/setup.sh
#
# Checks the tools Narrate needs, creates services/api/.env from the example, creates the
# Postgres database, and installs the Python and web dependencies from their lockfiles.
# Written for bash 3.2 (the one macOS ships), so no newer bash features.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/services/api"
WEB="$ROOT/apps/web"

missing=""
need() {
  command -v "$1" >/dev/null 2>&1 || missing="$missing\n  - $1: $2"
}
need uv "Python tooling. macOS: brew install uv. Linux: https://docs.astral.sh/uv/"
need node "Node 20+. macOS: brew install node. Linux: https://nodejs.org"
need npm "comes with Node"
need ffmpeg "joins recorded clips into chapters and exports. brew install ffmpeg / apt install ffmpeg"
need espeak-ng "Kokoro uses it to pronounce unusual words. brew install espeak-ng / apt install espeak-ng"
need psql "Postgres 14+. brew install postgresql@14 && brew services start postgresql@14 / apt install postgresql"
need pg_isready "comes with Postgres"
if [ -n "$missing" ]; then
  printf "Narrate needs a few tools that aren't installed yet:$missing\n" >&2
  exit 1
fi
if [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  echo "Node 20 or newer is needed (found $(node --version))." >&2
  exit 1
fi
if ! pg_isready -q; then
  echo "Postgres is installed but not running. macOS: brew services start postgresql@14" >&2
  exit 1
fi

if [ ! -f "$API/.env" ]; then
  cp "$API/.env.example" "$API/.env"
  echo "Created services/api/.env. Add a free Gemini key (GEMINI_API_KEY) to switch on the AI director."
fi

# The database named in DATABASE_URL (environment first, then .env)
url="${DATABASE_URL:-$(grep -E '^DATABASE_URL=' "$API/.env" | cut -d= -f2- || true)}"
url="${url:-postgresql+psycopg://localhost/text_to_audiobook}"
database="${url##*/}"
database="${database%%\?*}"
if psql -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$database'" | grep -q 1; then
  echo "Database $database already exists."
else
  createdb "$database"
  echo "Created database $database."
fi

echo "Installing the API's Python packages (uv picks the right Python version)..."
(cd "$API" && uv sync)
echo "Installing the web app's packages..."
(cd "$WEB" && npm ci --no-audit --no-fund)

cat <<'DONE'

Narrate is set up. Start it with:

  ./scripts/start.sh           # this computer only: http://localhost:3000
  ./scripts/start.sh --phone   # also your phone, on the same Wi-Fi

The first recording downloads the Kokoro voice model (about 330 MB) from Hugging Face.
DONE
