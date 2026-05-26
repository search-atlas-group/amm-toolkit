#!/bin/bash
set -e
MANIFEST=".claude-plugin/plugin.json"

[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST missing"; exit 1; }

jq -e '.name == "searchatlas-toolkit"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: name field wrong"; exit 1; }

jq -e '.version | test("^[0-9]+\\.[0-9]+\\.[0-9]+$")' "$MANIFEST" >/dev/null \
  || { echo "FAIL: version not SemVer"; exit 1; }

jq -e '.mcpServers.searchatlas.url == "https://mcp.searchatlas.com/mcp"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: searchatlas MCP not registered correctly"; exit 1; }

echo "PASS: plugin manifest valid"
