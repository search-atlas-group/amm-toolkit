#!/usr/bin/env bash
# Discover SearchAtlas MCP tool schemas via Claude Code
#
# Outputs a JSON file listing every tool group and its available operations,
# based on schema discovery (calling each tool group with empty params {}).
#
# Usage:
#   bash scripts/discover-tools.sh [output_file]
#
# Arguments:
#   output_file   Optional. Path to write the JSON output.
#                 Defaults to: scripts/tool-schemas-$(date +%Y-%m-%d).json
#
# Requirements:
#   - claude CLI installed and authenticated
#   - SearchAtlas MCP connected (claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp)
#
# This script generates a discovery prompt that you paste into Claude Code.
# Claude runs the schema calls and saves results as structured JSON.

set -e

OUTPUT="${1:-scripts/tool-schemas-$(date +%Y-%m-%d).json}"

DISCOVERY_PROMPT=$(cat <<'PROMPT'
Run schema discovery on all SearchAtlas MCP tool groups. For each tool group, call it with empty params {} to discover the available operations and their parameter schemas.

Tool groups to discover:
- brand_vault
- project_management
- audit_management
- suggestion_management
- schema_markup
- indexing_management
- recrawl_management
- seo_analysis
- holistic_audit
- topical_maps
- content_generation
- article_management
- content_retrieval
- content_publication
- gbp_locations_crud
- gbp_locations_recommendations
- gbp_locations_categories_crud
- gbp_locations_services_crud
- gbp_locations_attributes_crud
- gbp_posts_generation
- gbp_posts_automation
- gbp_posts_crud
- gbp_reviews
- business_crud
- product_crud
- product_mgmt
- campaign
- task
- ads_account_crud
- ads_account_mgmt
- organic
- backlinks
- analysis
- keyword_research
- local_seo_grids
- local_seo_rankings
- local_seo_competitors
- visibility
- sentiment
- queries
- prompt_simulator
- image_upload
- quota_management
- website_studio_tools

For each tool group, output a JSON block:
{
  "tool_group": "<name>",
  "operations": ["<op1>", "<op2>", ...],
  "required_params": { "<op>": ["<param1>", ...] }
}

Combine all results into a single JSON array and write it to: OUTFILE
PROMPT
)

# Replace OUTFILE placeholder with actual path
FINAL_PROMPT="${DISCOVERY_PROMPT/OUTFILE/$OUTPUT}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   SearchAtlas MCP — Tool Schema Discovery                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Output file: $OUTPUT"
echo ""
echo "Paste the following prompt into Claude Code to run discovery:"
echo ""
echo "────────────────────────────────────────────────────────────"
echo "$FINAL_PROMPT"
echo "────────────────────────────────────────────────────────────"
echo ""
echo "Or pipe it directly if claude CLI supports stdin:"
echo "  bash scripts/discover-tools.sh | pbcopy   # macOS — copies prompt to clipboard"
echo ""

# Copy to clipboard on macOS if available
if command -v pbcopy &>/dev/null; then
  echo "$FINAL_PROMPT" | pbcopy
  echo "Prompt copied to clipboard."
fi
