#!/usr/bin/env bash
# AMM Mission Control supervisor — launches the tiny always-on daemon that
# wakes the bridge servers on demand. Idle-shutdowns from the bridges leave
# this process running so welcome.html can always reach it.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8764}"

if ! command -v python3 &>/dev/null; then
  echo "python3 not found"; exit 1
fi

VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

if ! python -c "import fastapi, uvicorn" &>/dev/null; then
  pip install --quiet --upgrade pip
  pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

PORT="$PORT" exec python "$SCRIPT_DIR/server.py"
