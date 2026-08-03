#!/usr/bin/env bash
# One-command launcher for MailPilot (macOS / Linux).
#   ./start.sh            -> installs deps into a local venv, then starts the app
#   PORT=8080 ./start.sh  -> run on a different port
#
# Open http://localhost:5001 (or your chosen PORT) in a browser once it prints
# "Running on ...".
set -euo pipefail
cd "$(dirname "$0")"

# pick a python
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else echo "ERROR: Python 3.10+ is required but was not found." >&2; exit 1; fi
fi

# create venv on first run
if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)…"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
if [ -f ".venv/bin/activate" ]; then source ".venv/bin/activate"
else source ".venv/Scripts/activate"; fi   # Git-Bash on Windows

echo "==> Installing dependencies…"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

PORT="${PORT:-5001}"
echo ""
echo "======================================================================"
echo "  MailPilot is starting."
echo "  Open your browser at:  http://localhost:${PORT}"
echo "  Press Ctrl+C to stop."
echo "======================================================================"
echo ""
PORT="$PORT" python run_saas.py
