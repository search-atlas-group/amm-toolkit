#!/bin/bash
# SearchAtlas Toolkit — SessionStart hook
# Jobs: ensure client data dir, show branded banner (once, then compact),
# detect legacy data, check MCP auth. Always exit 0 — never block startup.

set +e  # do not propagate failures

SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"

# 1. Ensure client data home + plugin data dir exist
SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"
mkdir -p "$SA_CLIENTS_DIR" 2>/dev/null
DATA_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.searchatlas}"
mkdir -p "$DATA_DIR" 2>/dev/null
FLAG="$DATA_DIR/.welcomed"

# 2. Full branded banner on first run, compact line after.
#    Banner art lives in banner.txt (keeps parens out of the script — avoids
#    a bash 3.2 command-substitution heredoc parser bug on macOS).
if [ ! -f "$FLAG" ] && [ -f "$SCRIPT_DIR/banner.txt" ]; then
  MSG="$(cat "$SCRIPT_DIR/banner.txt")"
  touch "$FLAG" 2>/dev/null
else
  MSG="✦ SearchAtlas · 21 commands · /searchatlas:help"
fi

# 3. Fold in a legacy-data nudge if an old ~/.amm/clients exists
if [ -d "$HOME/.amm/clients" ] && [ -z "$(ls -A "$SA_CLIENTS_DIR" 2>/dev/null)" ]; then
  MSG="$MSG
📦 Found legacy ~/.amm/clients/ — run /searchatlas:help migrate-data to move it."
fi

# 4. Best-effort MCP check (never hard-fail)
if command -v claude >/dev/null 2>&1; then
  if ! claude mcp list 2>/dev/null | grep -q "searchatlas"; then
    MSG="$MSG
⚠️  SearchAtlas MCP not registered yet — run any /searchatlas command to authorize, or restart Claude Code."
  fi
fi

# 5. Emit as a visible systemMessage (jq encodes newlines/specials safely)
if command -v jq >/dev/null 2>&1; then
  jq -n --arg m "$MSG" '{systemMessage:$m}'
else
  printf '%s\n' "$MSG"
fi

exit 0
