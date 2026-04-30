#!/usr/bin/env bash
# Agentic Marketing Mastermind — Setup Script
# Installs slash commands and configures the SearchAtlas MCP.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMANDS_SRC="$SCRIPT_DIR/commands"
COMMANDS_DST="$HOME/.claude/commands"

echo "=== Agentic Marketing Mastermind Setup ==="
echo ""

# ── 1. Check prerequisites ───────────────────────────────────────────────────

if [[ -f "$SCRIPT_DIR/Scripts/preflight.sh" ]]; then
  bash "$SCRIPT_DIR/Scripts/preflight.sh"
fi

# ── 2. Install slash commands ────────────────────────────────────────────────

mkdir -p "$COMMANDS_DST"

if [ -d "$COMMANDS_SRC" ] && [ "$(ls -A "$COMMANDS_SRC" 2>/dev/null)" ]; then
    cp "$COMMANDS_SRC"/*.md "$COMMANDS_DST/" 2>/dev/null || true
    echo "Installed commands:"
    for f in "$COMMANDS_SRC"/*.md; do
        name=$(basename "$f" .md)
        echo "  /$name"
    done
else
    echo "No commands found in $COMMANDS_SRC"
fi

echo ""

# ── 2b. Make scripts executable ──────────────────────────────────────────────

chmod +x "$SCRIPT_DIR/Scripts/"*.sh 2>/dev/null || true

# ── 2c. Stamp toolkit path into the security scanner UI ──────────────────────

SCANNER_HTML="$SCRIPT_DIR/tools/security/index.html"
if [ -f "$SCANNER_HTML" ]; then
    sed -i.bak "s|__TOOLKIT_PATH__|$SCRIPT_DIR|g" "$SCANNER_HTML" && rm -f "$SCANNER_HTML.bak"
    echo "Security scanner configured for: $SCRIPT_DIR"
fi

echo ""



# ── 5. Configure SearchAtlas MCP ─────────────────────────────────────────────

if claude mcp list 2>/dev/null | grep -q "searchatlas"; then
    echo "SearchAtlas MCP already configured."
else
    echo "Adding SearchAtlas MCP server..."
    claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
    echo "SearchAtlas MCP configured."
fi

echo ""

# ── 4. Optional: communication channels ──────────────────────────────────────

WIZARD="$SCRIPT_DIR/Scripts/setup-interactive.sh"

if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$WIZARD" ]; then
    echo "No communication channels configured yet."
    read -p "Set up Slack/Discord/Email/Circle integrations? (y/n): " SETUP_COMMS
    if [[ "$SETUP_COMMS" == "y" || "$SETUP_COMMS" == "Y" ]]; then
        bash "$WIZARD"
    else
        echo "Skipped. Run 'bash Scripts/setup-interactive.sh' anytime to configure."
    fi
elif [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Communication channels already configured."
    echo "To reconfigure, run: bash Scripts/setup-interactive.sh"
fi

echo ""

# ── 5. Optional: security scanning tools ─────────────────────────────────────

echo "Security scanning tools (trivy, gitleaks, trufflehog, semgrep) enable /security-scan."
read -p "Install security scanning tools? (y/n): " SETUP_SECURITY
if [[ "$SETUP_SECURITY" == "y" || "$SETUP_SECURITY" == "Y" ]]; then
    bash "$SCRIPT_DIR/Scripts/install-security-tools.sh"
else
    echo "Skipped. Run 'bash Scripts/install-security-tools.sh' anytime to install."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Open Claude Code in this directory"
echo "  2. Try: /my-account  (will prompt OAuth authorization on first use)"
echo "  3. Connect your other tools: /setup-integrations"
echo "     Supports: HubSpot, ClickUp, Linear, Notion, Slack, Gmail, Google Calendar, GitHub"
echo "  4. Verify everything: bash Scripts/verify-setup.sh"
echo "  5. Scan any repo before cloning: /security-scan <repo_url>"
