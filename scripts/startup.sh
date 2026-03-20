#!/usr/bin/env bash
set -euo pipefail

# Startup script: stops services, runs migrations and build, then starts backend + frontend preview.
# Usage: ./scripts/startup.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Stopping known services (backend, vite)..."
pkill -f "backend/app.py" || true
pkill -f "node.*vite" || true
pkill -f "npm.*run preview" || true
sleep 1

echo "Running migrations..."
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi
"$PYTHON" work-process/scripts/migrate.py

echo "Ensure backend virtualenv and dependencies..."
if [ ! -d "$ROOT/.venv" ]; then
  echo "Creating virtualenv at $ROOT/.venv"
  "$PYTHON" -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/pip" install -r backend/requirements.txt

if [ -d "$ROOT/frontend" ]; then
  echo "Installing frontend dependencies and building..."
  cd "$ROOT/frontend"
  npm install
  npm run build
  cd "$ROOT"
fi

mkdir -p "$ROOT/run" "$ROOT/logs"

echo "Starting backend..."
nohup "$ROOT/.venv/bin/python" backend/app.py > "$ROOT/logs/backend.log" 2>&1 &
echo $! > "$ROOT/run/backend.pid"

if [ -d "$ROOT/frontend" ]; then
  echo "Starting frontend preview server..."
  cd "$ROOT/frontend"
  nohup npm run preview > "$ROOT/logs/frontend_preview.log" 2>&1 &
  echo $! > "$ROOT/run/frontend.pid"
  cd "$ROOT"
fi

echo "Startup complete. PIDs:"
if [ -f "$ROOT/run/backend.pid" ]; then
  echo " backend: $(cat "$ROOT/run/backend.pid")"
fi
if [ -f "$ROOT/run/frontend.pid" ]; then
  echo " frontend preview: $(cat "$ROOT/run/frontend.pid")"
fi

echo "Logs: $ROOT/logs"

chmod +x scripts/startup.sh
