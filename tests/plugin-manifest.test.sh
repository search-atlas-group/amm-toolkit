#!/bin/bash
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" 2>/dev/null || exit 1
set -e
MANIFEST=".claude-plugin/plugin.json"

[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST missing"; exit 1; }

jq -e '.name == "searchatlas-toolkit"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: name field wrong"; exit 1; }

jq -e '.version | test("^[0-9]+\\.[0-9]+\\.[0-9]+$")' "$MANIFEST" >/dev/null \
  || { echo "FAIL: version not SemVer"; exit 1; }

jq -e '.mcpServers.searchatlas.type == "http"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: searchatlas MCP type wrong (expected http)"; exit 1; }

jq -e '.mcpServers.searchatlas.url == "https://mcp.searchatlas.com/mcp"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: searchatlas MCP not registered correctly"; exit 1; }

echo "PASS: plugin manifest valid"
