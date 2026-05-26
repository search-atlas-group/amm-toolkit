#!/bin/bash
# SearchAtlas Toolkit — SessionStart hook
# Three jobs: ensure client data dir, detect legacy data, check MCP auth.
# Always exit 0 — hooks must not block session start.

set +e  # do not propagate failures

# 1. Ensure client data home exists
SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"
mkdir -p "$SA_CLIENTS_DIR" 2>/dev/null

# 2. Detect legacy ~/.amm/clients and nudge toward migration
if [ -d "$HOME/.amm/clients" ] && [ -z "$(ls -A "$SA_CLIENTS_DIR" 2>/dev/null)" ]; then
  echo "📦 Found legacy ~/.amm/clients/ — run /searchatlas:help migrate-data to move it."
fi

# 3. Verify SearchAtlas MCP is registered (best-effort, never hard-fail)
if command -v claude >/dev/null 2>&1; then
  if ! claude mcp list 2>/dev/null | grep -q "searchatlas"; then
    echo "⚠️  SearchAtlas MCP not registered. Plugin commands will fail until it is."
    echo "   This usually self-heals when the plugin loads — restart Claude Code if needed."
  fi
fi

exit 0
