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

MARKETPLACE=".claude-plugin/marketplace.json"

[ -f "$MARKETPLACE" ] || { echo "FAIL: $MARKETPLACE missing"; exit 1; }

jq -e '.name == "searchatlas"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace name wrong"; exit 1; }

jq -e '.owner.name == "SearchAtlas"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace owner.name wrong"; exit 1; }

jq -e '.plugins[0].name == "searchatlas-toolkit"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace plugin name wrong"; exit 1; }

jq -e '.plugins[0].source.source == "url"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace plugin source.source must be \"url\""; exit 1; }

jq -e '.plugins[0].source.url | test("github.com/search-atlas-group/amm-toolkit")' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace plugin source.url must point to search-atlas-group/amm-toolkit"; exit 1; }

echo "PASS: marketplace manifest valid"
