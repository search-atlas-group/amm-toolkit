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
# Use an unquoted heredoc so $SCRIPT_DIR (the cloned-repo path) is interpolated
# into the script at install time. Other shell variables are escaped with \$ so
# they resolve at runtime when the user double-clicks. We can't trust
# `launchctl load`'s exit code — it returns 0 when the plist registers, even
# if the bridge process crashes during boot (e.g. claude CLI missing from
# launchd's PATH). So the script must actually curl the health endpoint to
# know if the bridge is really listening, and fall back to direct nohup
# launch if launchd fails.
cat > "$START_CMD" <<START_EOF
#!/usr/bin/env bash
# Double-click to restart the Mission Control bridges.
TOOLKIT="$SCRIPT_DIR"
UID_NUM=\$(id -u)
ANY_FAIL=0

if [[ "\$(uname -s)" != "Darwin" ]]; then
    echo "This restart helper is macOS-only."
    read -p "Press Enter to close..."
    exit 0
fi

wait_for_port() {
    local port="\$1"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if curl -s -o /dev/null -m 1 "http://localhost:\$port/api/health" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    return 1
}

restart_one() {
    local name="\$1" port="\$2"
    local label="com.searchatlas.amm-\$name"
    local plist="\$HOME/Library/LaunchAgents/\$label.plist"
    local run_sh="\$TOOLKIT/tools/\$name/run.sh"

    # If a bridge is already serving traffic, leave it alone — racing it
    # just causes "address already in use" crashes.
    if curl -s -o /dev/null -m 1 "http://localhost:\$port/api/health" 2>/dev/null; then
        echo "  ✓  \$name already running on port \$port"
        return 0
    fi

    launchctl bootout "gui/\$UID_NUM/\$label" 2>/dev/null || \\
        launchctl unload "\$plist" 2>/dev/null || true
    local pids
    pids=\$(lsof -t -iTCP:\$port -sTCP:LISTEN 2>/dev/null)
    if [ -n "\$pids" ]; then
        echo "\$pids" | xargs kill -9 2>/dev/null || true
    fi

    # Wait for the port to actually free up before bootstrapping a new
    # instance, otherwise the new uvicorn races the old socket release.
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if ! lsof -i TCP:\$port -sTCP:LISTEN >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done

    if [ -f "\$plist" ]; then
        launchctl bootstrap "gui/\$UID_NUM" "\$plist" 2>/dev/null || \\
            launchctl load "\$plist" 2>/dev/null || true
    fi
    if wait_for_port "\$port"; then
        echo "  ✓  \$name listening on port \$port"
        return 0
    fi

    if [ -f "\$run_sh" ]; then
        echo "  …  \$name launchd boot failed, falling back to direct launch"
        ( NO_BROWSER=1 PORT=\$port nohup bash "\$run_sh" \\
            > "/tmp/amm-\$name.log" 2> "/tmp/amm-\$name.err" < /dev/null & )
        if wait_for_port "\$port"; then
            echo "  ✓  \$name listening on port \$port (direct launch)"
            return 0
        fi
    fi

    echo "  ✗  \$name failed to start — check /tmp/amm-\$name.err"
    return 1
}

restart_one command-center 8765 || ANY_FAIL=1
restart_one website-build 8766 || ANY_FAIL=1
restart_one website-rebuild 8767 || ANY_FAIL=1

echo
if [ \$ANY_FAIL -eq 0 ]; then
    echo "All bridges running. Refresh welcome.html, then click any wizard card."
else
    echo "Some bridges failed to start. Inspect the .err files in /tmp/ for details."
fi
read -p "Press Enter to close..."
START_EOF
chmod +x "$START_CMD"

# ── 2f. Drop the restart helper on Desktop so users can find it ──────────────
# The cloned-repo install may live deep in a workspace folder; Desktop is the
# one place every operator can reach. Idempotent — overwrites if re-run.
DESKTOP_CMD="$HOME/Desktop/SearchAtlas Mission Control.command"
if [ -d "$HOME/Desktop" ]; then
    if cp "$START_CMD" "$DESKTOP_CMD" 2>/dev/null; then
        chmod +x "$DESKTOP_CMD" 2>/dev/null || true
        echo "  ✓  Restart helper on Desktop: SearchAtlas Mission Control.command"
    fi
fi


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
