#!/usr/bin/env bash
# SearchAtlas MCP — universal one-shot installer
#
# Run on any fresh machine — no clone, no cd:
#   curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
#
# Detects every MCP-capable client on the machine (Claude Code, Claude
# Desktop, Cursor, Windsurf), writes the right config for each, then
# opens the SearchAtlas OAuth tab so the first tool call is authenticated.
# Idempotent — safe to re-run.

set -euo pipefail

SERVER_NAME="searchatlas"
ENDPOINT="https://mcp.searchatlas.com/mcp"
# Note: we deliberately do NOT pre-open an OAuth URL here. MCP OAuth uses
# dynamic PKCE state + a localhost callback that only the MCP client can
# generate (Claude Code, Desktop, Cursor, Windsurf each handle it on
# first tool use). Any static OAuth URL we open from a terminal script
# would be a no-op and misleading. The real flow: this installer writes
# configs, the user opens their MCP client, the client triggers OAuth
# with its own dynamic params and a one-click "Authorize" if the user
# is already signed into SearchAtlas.
#
# The welcome page is fetched from the raw GitHub URL and written to a
# local file, then opened with file://. This sidesteps every HTML-hosting
# headache (raw.githubusercontent.com and jsdelivr both serve .html as
# text/plain for anti-abuse; GitHub Pages is org-disabled). Opening from
# disk lets the page's bundler script run normally without proxy
# interference.
WELCOME_RAW_URL="https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/docs/welcome.html"
WELCOME_LOCAL_DIR="${HOME}/.searchatlas"
WELCOME_LOCAL_FILE="${WELCOME_LOCAL_DIR}/welcome.html"

# Toolkit install location. We pull commands, workflows, integrations,
# Scripts, AND tools (Mission Control bridges: command-center, website-build,
# website-rebuild). Command files are patched so their relative bash
# invocations resolve to this hidden install.
TOOLKIT_TARBALL_URL="https://codeload.github.com/search-atlas-group/amm-toolkit/tar.gz/refs/heads/main"
TOOLKIT_INSTALL_DIR="${HOME}/.searchatlas/toolkit"
CLAUDE_COMMANDS_DIR="${HOME}/.claude/commands"

HOME_DIR="${HOME}"
OS="$(uname -s)"

c_dim()   { printf "\033[2m%s\033[0m" "$1"; }
c_bold()  { printf "\033[1m%s\033[0m" "$1"; }
c_green() { printf "\033[32m%s\033[0m" "$1"; }
c_cyan()  { printf "\033[36m%s\033[0m" "$1"; }
c_yellow(){ printf "\033[33m%s\033[0m" "$1"; }

ok()   { printf "  %s %s\n" "$(c_green '✓')" "$1"; }
info() { printf "  %s %s\n" "$(c_cyan '•')" "$1"; }
warn() { printf "  %s %s\n" "$(c_yellow '!')" "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Track which clients we configured so we can print accurate next-step
# instructions at the end (each client's auth UX differs).
HAS_CLAUDE_CODE=0
HAS_CLAUDE_DESKTOP=0
HAS_CURSOR=0
HAS_WINDSURF=0

# ---- Claude Code (CLI) ----
install_claude_code() {
  if ! have claude; then
    info "Claude Code — not detected, skipped"
    return 1
  fi
  if claude mcp add "${SERVER_NAME}" --type http "${ENDPOINT}" >/dev/null 2>&1; then
    ok "Claude Code — added SearchAtlas"
  else
    ok "Claude Code — already configured"
  fi
  HAS_CLAUDE_CODE=1
}

# ---- Claude Desktop ----
claude_desktop_config_path() {
  case "$OS" in
    Darwin) echo "$HOME_DIR/Library/Application Support/Claude/claude_desktop_config.json" ;;
    Linux)  echo "$HOME_DIR/.config/Claude/claude_desktop_config.json" ;;
    *)      echo "" ;;
  esac
}

write_mcp_config() {
  # $1 = config path, $2 = json shape ("http" or "url-only" or "serverUrl")
  local path="$1" shape="$2"
  local dir; dir="$(dirname "$path")"
  [ -d "$dir" ] || return 1
  mkdir -p "$dir"
  if ! have jq; then
    warn "jq not found — install jq or use the npx installer for this client"
    return 1
  fi
  [ -f "$path" ] || echo '{}' > "$path"
  local tmp; tmp="$(mktemp)"
  case "$shape" in
    http)
      jq --arg name "$SERVER_NAME" --arg url "$ENDPOINT" \
        '.mcpServers = (.mcpServers // {}) | .mcpServers[$name] = {"type":"http","url":$url}' \
        "$path" > "$tmp" && mv "$tmp" "$path"
      ;;
    url-only)
      jq --arg name "$SERVER_NAME" --arg url "$ENDPOINT" \
        '.mcpServers = (.mcpServers // {}) | .mcpServers[$name] = {"url":$url}' \
        "$path" > "$tmp" && mv "$tmp" "$path"
      ;;
    serverUrl)
      jq --arg name "$SERVER_NAME" --arg url "$ENDPOINT" \
        '.mcpServers = (.mcpServers // {}) | .mcpServers[$name] = {"serverUrl":$url}' \
        "$path" > "$tmp" && mv "$tmp" "$path"
      ;;
  esac
}

install_claude_desktop() {
  local p; p="$(claude_desktop_config_path)"
  [ -n "$p" ] && [ -d "$(dirname "$p")" ] || { info "Claude Desktop — not detected, skipped"; return 1; }
  if write_mcp_config "$p" "http"; then ok "Claude Desktop — added SearchAtlas"; HAS_CLAUDE_DESKTOP=1; fi
}

install_cursor() {
  local p="$HOME_DIR/.cursor/mcp.json"
  [ -d "$HOME_DIR/.cursor" ] || { info "Cursor — not detected, skipped"; return 1; }
  if write_mcp_config "$p" "url-only"; then ok "Cursor — added SearchAtlas"; HAS_CURSOR=1; fi
}

install_windsurf() {
  local p="$HOME_DIR/.codeium/windsurf/mcp_config.json"
  [ -d "$HOME_DIR/.codeium/windsurf" ] || { info "Windsurf — not detected, skipped"; return 1; }
  if write_mcp_config "$p" "serverUrl"; then ok "Windsurf — added SearchAtlas"; HAS_WINDSURF=1; fi
}

open_url() {
  local url="$1"
  case "$OS" in
    Darwin) open "$url" >/dev/null 2>&1 ;;
    Linux)  xdg-open "$url" >/dev/null 2>&1 ;;
    *)      return 1 ;;
  esac
}

# Download the welcome page to disk, then open the local file in the
# browser — celebrates the install and points the user at the next
# step (open their MCP client, which handles its own OAuth).
fetch_welcome() {
  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi
  mkdir -p "$WELCOME_LOCAL_DIR" 2>/dev/null || return 1
  if curl -fsSL "$WELCOME_RAW_URL" -o "$WELCOME_LOCAL_FILE" 2>/dev/null; then
    return 0
  fi
  return 1
}

open_welcome() {
  if fetch_welcome; then
    open_url "file://${WELCOME_LOCAL_FILE}" || warn "Open this file when you're ready: ${WELCOME_LOCAL_FILE}"
  else
    info "Welcome page download skipped (offline or curl unavailable)"
  fi
}

# Download the lightweight toolkit slices (commands + their bash
# dependencies) and install slash commands into ~/.claude/commands/.
# Each command .md is sed-patched so relative paths like
# "bash integrations/slack/send-message.sh" resolve to the absolute
# install dir. Idempotent — re-running overwrites.
install_toolkit_commands() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
    info "Slash commands skipped (curl or tar unavailable)"
    return 1
  fi

  local tmpdir
  tmpdir="$(mktemp -d 2>/dev/null)" || { warn "Could not create temp dir for toolkit"; return 1; }

  if ! curl -fsSL "$TOOLKIT_TARBALL_URL" -o "$tmpdir/toolkit.tar.gz" 2>/dev/null; then
    warn "Could not download toolkit tarball"
    rm -rf "$tmpdir"
    return 1
  fi

  mkdir -p "$TOOLKIT_INSTALL_DIR" "$CLAUDE_COMMANDS_DIR"

  # Extract only the dirs we need. Strip the top-level "amm-toolkit-main/"
  # so files land directly under TOOLKIT_INSTALL_DIR.
  if ! tar -xzf "$tmpdir/toolkit.tar.gz" -C "$tmpdir" \
        amm-toolkit-main/commands amm-toolkit-main/workflows \
        amm-toolkit-main/integrations amm-toolkit-main/Scripts \
        amm-toolkit-main/tools 2>/dev/null; then
    warn "Could not extract toolkit dirs"
    rm -rf "$tmpdir"
    return 1
  fi

  # Refresh the install dir (cleans up stale files from previous installs).
  for d in commands workflows integrations Scripts tools; do
    rm -rf "$TOOLKIT_INSTALL_DIR/$d"
    mv "$tmpdir/amm-toolkit-main/$d" "$TOOLKIT_INSTALL_DIR/" 2>/dev/null || true
  done
  rm -rf "$tmpdir"

  # Make Scripts/*.sh executable in case any command shells out to them.
  chmod +x "$TOOLKIT_INSTALL_DIR/Scripts/"*.sh 2>/dev/null || true
  chmod +x "$TOOLKIT_INSTALL_DIR/integrations/"**/*.sh 2>/dev/null || true
  chmod +x "$TOOLKIT_INSTALL_DIR/tools/"*/run.sh 2>/dev/null || true

  # Patch each command .md so relative bash invocations and workflow
  # references resolve to the toolkit install dir. Then drop into
  # ~/.claude/commands/. Pattern set covers the actual relative paths
  # used across all commands; safe-no-op for files that don't have them.
  local patched=0
  for md in "$TOOLKIT_INSTALL_DIR/commands"/*.md; do
    [ -f "$md" ] || continue
    local name
    name="$(basename "$md")"
    sed \
      -e "s|bash integrations/|bash ${TOOLKIT_INSTALL_DIR}/integrations/|g" \
      -e "s|bash workflows/|bash ${TOOLKIT_INSTALL_DIR}/workflows/|g" \
      -e "s|bash Scripts/|bash ${TOOLKIT_INSTALL_DIR}/Scripts/|g" \
      -e "s|bash scripts/|bash ${TOOLKIT_INSTALL_DIR}/Scripts/|g" \
      -e "s|\\\$AMM_ROOT|${TOOLKIT_INSTALL_DIR}|g" \
      -e "s|\`workflows/|\`${TOOLKIT_INSTALL_DIR}/workflows/|g" \
      -e "s|\`integrations/|\`${TOOLKIT_INSTALL_DIR}/integrations/|g" \
      "$md" > "$CLAUDE_COMMANDS_DIR/$name" 2>/dev/null
    patched=$((patched+1))
  done

  if [ "$patched" -gt 0 ]; then
    ok "Installed ${patched} slash commands to ~/.claude/commands/"
  else
    warn "No slash commands were patched"
  fi
}

# Install LaunchAgents for the 3 Mission Control bridges so they auto-start
# on login. RunAtLoad=true so they boot immediately; KeepAlive=false so a
# manual kill stays killed until next login (or Start Bridges.command).
install_mission_control_bridges() {
  if [[ "$OS" != "Darwin" ]]; then
    info "Mission Control bridges skipped (LaunchAgents are macOS-only)"
    return 1
  fi

  local toolkit="$TOOLKIT_INSTALL_DIR"
  local agents_dir="$HOME_DIR/Library/LaunchAgents"
  mkdir -p "$agents_dir"

  local installed=0
  for entry in "command-center:8765" "website-build:8766" "website-rebuild:8767"; do
    local name="${entry%%:*}"
    local port="${entry##*:}"
    local label="com.searchatlas.amm-$name"
    local plist="$agents_dir/$label.plist"
    local run_sh="$toolkit/tools/$name/run.sh"

    if [ ! -f "$run_sh" ]; then
      continue
    fi

    launchctl unload "$plist" 2>/dev/null || true

    cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$run_sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>NO_BROWSER</key>
        <string>1</string>
        <key>PORT</key>
        <string>$port</string>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/amm-$name.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/amm-$name.err</string>
</dict>
</plist>
PLIST

    if launchctl load "$plist" 2>/dev/null; then
      installed=$((installed+1))
    fi
  done

  if [ "$installed" -gt 0 ]; then
    ok "Mission Control bridges running (Onboard:8765, Build:8766, Rebuild:8767)"
  fi

  # Drop the manual-restart helper
  local start_cmd="$toolkit/Start Bridges.command"
  cat > "$start_cmd" <<'STARTCMD'
#!/usr/bin/env bash
# Double-click to restart the Mission Control bridges.
for NAME in command-center website-build website-rebuild; do
    PLIST="$HOME/Library/LaunchAgents/com.searchatlas.amm-$NAME.plist"
    if [ -f "$PLIST" ]; then
        launchctl unload "$PLIST" 2>/dev/null || true
        launchctl load "$PLIST" 2>/dev/null && \
            echo "  ✓  $NAME bridge restarted" || \
            echo "  ✗  $NAME bridge failed to restart"
    fi
done
echo
echo "Bridges restarted. Open welcome.html and click any wizard card."
read -p "Press Enter to close..."
STARTCMD
  chmod +x "$start_cmd"
}

main() {
  echo
  echo "  $(c_bold 'SearchAtlas MCP V2') $(c_dim '· one-shot installer')"
  echo "  $(c_dim '620 tools · https://mcp.searchatlas.com')"
  echo
  echo "  $(c_bold 'Detecting MCP clients…')"
  echo

  INSTALLED=0
  install_claude_code   && INSTALLED=$((INSTALLED+1)) || true
  install_claude_desktop && INSTALLED=$((INSTALLED+1)) || true
  install_cursor        && INSTALLED=$((INSTALLED+1)) || true
  install_windsurf      && INSTALLED=$((INSTALLED+1)) || true

  echo
  if [ "$INSTALLED" -eq 0 ]; then
    warn "No MCP-capable clients found."
    info "Install Claude Code, Claude Desktop, Cursor, or Windsurf, then re-run."
    exit 1
  fi

  # Install AMM slash commands (only if Claude Code is present —
  # ~/.claude/commands/ is a Claude Code thing).
  if [ "$HAS_CLAUDE_CODE" -eq 1 ]; then
    echo
    echo "  $(c_bold 'Installing slash commands…')"
    install_toolkit_commands || true
    echo
    echo "  $(c_bold 'Installing Mission Control bridges…')"
    install_mission_control_bridges || true
  fi

  echo
  echo "  $(c_bold 'You are wired up.')"
  open_welcome
  echo
  echo "  $(c_dim 'Re-run anytime with: curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash')"
  echo
}

main "$@"
