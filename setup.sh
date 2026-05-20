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

# ── 2d. Install Mission Control bridges as LaunchAgents ──────────────────────

if [[ "$(uname -s)" == "Darwin" ]]; then
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"

    # Capture the user's actual PATH so LaunchAgents can find tools
    # installed via nvm, pyenv, asdf, custom locations, etc. Standard
    # system locations appended as a safety net.
    USER_PATH="${PATH}:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
    USER_PATH="${USER_PATH//&/&amp;}"
    USER_PATH="${USER_PATH//</&lt;}"

    # Helper function to install one bridge as a LaunchAgent
    install_bridge_agent() {
        local NAME="$1"      # e.g. "command-center"
        local PORT="$2"
        local LABEL="com.searchatlas.amm-$NAME"
        local PLIST="$LAUNCH_AGENTS_DIR/$LABEL.plist"
        local RUN_SH="$SCRIPT_DIR/tools/$NAME/run.sh"

        if [ ! -f "$RUN_SH" ]; then
            echo "  ⚠  $RUN_SH not found — skipping $NAME LaunchAgent"
            return
        fi

        # Unload first if it already exists
        launchctl unload "$PLIST" 2>/dev/null || true

        # Write the plist
        cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$RUN_SH</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>NO_BROWSER</key>
        <string>1</string>
        <key>PORT</key>
        <string>$PORT</string>
        <key>PATH</key>
        <string>$USER_PATH</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/amm-$NAME.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/amm-$NAME.err</string>
</dict>
</plist>
PLIST_EOF

        launchctl load "$PLIST" 2>/dev/null && \
            echo "  ✓  $NAME bridge running on port $PORT" || \
            echo "  ⚠  $NAME LaunchAgent installed but failed to load"
    }

    echo "Installing Mission Control bridges..."
    install_bridge_agent "command-center" "8765"
    install_bridge_agent "website-build" "8766"
    install_bridge_agent "website-rebuild" "8767"
    echo ""
fi

# ── 2e. Create Start Bridges.command for manual restart ──────────────────────

START_CMD="$SCRIPT_DIR/Start Bridges.command"
cat > "$START_CMD" <<'START_EOF'
#!/usr/bin/env bash
# Double-click to restart the Mission Control bridges after a manual kill.
# These bridges auto-start on login; this script is the fallback to restart
# them within the same session.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" == "Darwin" ]]; then
    for NAME in command-center website-build website-rebuild; do
        PLIST="$HOME/Library/LaunchAgents/com.searchatlas.amm-$NAME.plist"
        if [ -f "$PLIST" ]; then
            launchctl unload "$PLIST" 2>/dev/null || true
            launchctl load "$PLIST" 2>/dev/null && \
                echo "  ✓  $NAME bridge restarted" || \
                echo "  ✗  $NAME bridge failed to restart"
        fi
    done
    echo ""
    echo "Bridges restarted. Open welcome.html and click any wizard card."
    read -p "Press Enter to close..."
fi
START_EOF
chmod +x "$START_CMD"



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
