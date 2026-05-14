#!/usr/bin/env bash
# AMM Command Center — local launch script
# Usage: bash run.sh
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8765}"

echo ""
echo -e "  ${GREEN}AMM Command Center${NC}"
echo -e "  ${DIM}local web UI for /onboard-client${NC}"
echo ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo -e "  ${RED}✗${NC}  python3 not found. Install Python 3.10+."
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info[0], sys.version_info[1]))')
echo -e "  ${GREEN}✓${NC}  Python $PY_VER"

# ── 2. Check Claude CLI ──────────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
  echo -e "  ${RED}✗${NC}  claude CLI not found on PATH."
  echo -e "      Install Claude Code first: https://claude.com/code"
  exit 1
fi
echo -e "  ${GREEN}✓${NC}  Claude CLI installed"

# ── 3. Check SearchAtlas MCP ─────────────────────────────────────────────────
if claude mcp list 2>/dev/null | grep -qi "searchatlas"; then
  echo -e "  ${GREEN}✓${NC}  SearchAtlas MCP configured"
else
  echo -e "  ${YELLOW}⚠${NC}  SearchAtlas MCP not configured"
  echo -e "      Run from the toolkit root:"
  echo -e "      ${DIM}claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp${NC}"
  echo ""
fi

# ── 4. Set up venv ───────────────────────────────────────────────────────────
VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
  echo ""
  echo -e "  ${DIM}Creating virtualenv…${NC}"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# ── 5. Install deps (only if missing) ────────────────────────────────────────
if ! python -c "import fastapi, uvicorn" &>/dev/null; then
  echo -e "  ${DIM}Installing dependencies…${NC}"
  pip install --quiet --upgrade pip
  pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi
echo -e "  ${GREEN}✓${NC}  Dependencies installed"

# ── 6. Launch ────────────────────────────────────────────────────────────────
URL="http://localhost:$PORT"
echo ""
echo -e "  Starting on ${GREEN}$URL${NC}"
echo -e "  ${DIM}Ctrl+C to stop${NC}"
echo ""

# Open the browser after a short delay so the server has time to bind
( sleep 1.5 && open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null ) &

PORT="$PORT" exec python "$SCRIPT_DIR/server.py"
