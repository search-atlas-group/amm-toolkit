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

# Install LaunchAgents for the supervisor + 3 Mission Control bridges. The
# supervisor is always-on (KeepAlive=true, ~15 MB, zero CPU when idle) and
# wakes bridges on demand from welcome.html. The bridges idle-shutdown after
# ~5 min of inactivity (KeepAlive=false) — welcome.html keeps them alive
# with a 60 s heartbeat while a wizard tab is open.
install_mission_control_bridges() {
  if [[ "$OS" != "Darwin" ]]; then
    info "Mission Control bridges skipped (LaunchAgents are macOS-only)"
    return 1
  fi

  local toolkit="$TOOLKIT_INSTALL_DIR"
  local agents_dir="$HOME_DIR/Library/LaunchAgents"
  mkdir -p "$agents_dir"

  # Capture the user's actual PATH so LaunchAgents can find tools installed
  # via nvm (~/.nvm/versions/node/.../bin), pyenv, asdf, custom locations, etc.
  # Append the standard system locations as a fallback safety net so the
  # plist always has the basics even if the user's shell PATH is minimal.
  local user_path="${PATH}:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
  # XML-escape any & or < that might appear in PATH (rare but possible)
  user_path="${user_path//&/&amp;}"
  user_path="${user_path//</&lt;}"

  local installed=0
  # name:port:keepalive — supervisor stays up always so welcome.html can
  # always reach it on 8764; bridges idle-shutdown.
  for entry in \
      "supervisor:8764:true" \
      "command-center:8865:false" \
      "website-build:8866:false" \
      "website-rebuild:8867:false"; do
    local name="${entry%%:*}"
    local rest="${entry#*:}"
    local port="${rest%:*}"
    local keepalive="${rest##*:}"
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
        <string>$user_path</string>
        <key>HOME</key>
        <string>$HOME_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <$keepalive/>
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
    ok "Mission Control running (Supervisor:8764, Onboard:8865, Build:8866, Rebuild:8867)"
  fi

  # Drop the manual-restart helper. We can't trust `launchctl load`'s exit
  # code — it returns 0 when the plist registers, even if the bridge process
  # crashes on boot (e.g. claude CLI missing from launchd's PATH). So the
  # script must actually CURL the health endpoint to know if the bridge is
  # really listening. If launchd boot fails, fall back to nohup so the user
  # at least gets a running bridge for the session.
  local start_cmd="$toolkit/Start Bridges.command"
  cat > "$start_cmd" <<'STARTCMD'
#!/usr/bin/env bash
# Double-click to restart the Mission Control bridges.
TOOLKIT="$HOME/.searchatlas/toolkit"
UID_NUM=$(id -u)
ANY_FAIL=0

wait_for_port() {
    local port="$1"
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if curl -s -o /dev/null -m 1 "http://localhost:$port/api/health" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    return 1
}

restart_one() {
    local name="$1" port="$2"
    local label="com.searchatlas.amm-$name"
    local plist="$HOME/Library/LaunchAgents/$label.plist"
    local run_sh="$TOOLKIT/tools/$name/run.sh"

    # 1) Idempotency: if a bridge is already serving traffic on the port,
    # leave it alone. The user's restart click should be a no-op when the
    # bridges are already up — racing them just creates the address-in-use
    # crash we used to see.
    if curl -s -o /dev/null -m 1 "http://localhost:$port/api/health" 2>/dev/null; then
        echo "  ✓  $name already running on port $port"
        return 0
    fi

    # 2) Tear down launchd-managed instances + any stray pids on the port.
    launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || \
        launchctl unload "$plist" 2>/dev/null || true
    local pids
    pids=$(lsof -t -iTCP:$port -sTCP:LISTEN 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi

    # 3) Actively wait for the port to be free before bootstrapping a new
    # instance — kill -9 returns instantly but the kernel takes a moment
    # to release the port (TIME_WAIT). Without this, launchctl bootstrap
    # fires while the old socket is still bound and the new uvicorn dies
    # with "address already in use".
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        if ! lsof -i TCP:$port -sTCP:LISTEN >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done

    # 4) Boot via launchd (preferred — survives login).
    if [ -f "$plist" ]; then
        launchctl bootstrap "gui/$UID_NUM" "$plist" 2>/dev/null || \
            launchctl load "$plist" 2>/dev/null || true
    fi
    if wait_for_port "$port"; then
        echo "  ✓  $name listening on port $port"
        return 0
    fi

    # 5) Fallback: launchd didn't give us a listening port. Run the bridge
    # directly via nohup so the user gets a working session even if their
    # launchd PATH is missing claude or python deps.
    if [ -f "$run_sh" ]; then
        echo "  …  $name launchd boot failed, falling back to direct launch"
        ( NO_BROWSER=1 PORT=$port nohup bash "$run_sh" \
            > "/tmp/amm-$name.log" 2> "/tmp/amm-$name.err" < /dev/null & )
        if wait_for_port "$port"; then
            echo "  ✓  $name listening on port $port (direct launch)"
            return 0
        fi
    fi

    echo "  ✗  $name failed to start — check /tmp/amm-$name.err"
    return 1
}

restart_one supervisor       8764 || ANY_FAIL=1
restart_one command-center   8865 || ANY_FAIL=1
restart_one website-build    8866 || ANY_FAIL=1
restart_one website-rebuild  8867 || ANY_FAIL=1

echo
if [ $ANY_FAIL -eq 0 ]; then
    echo "All bridges running. Refresh welcome.html, then click any wizard card."
else
    echo "Some bridges failed to start. Inspect the .err files in /tmp/ for details."
fi
read -p "Press Enter to close..."
STARTCMD
  chmod +x "$start_cmd"

  # Drop a copy on the Desktop where users can actually find it. The toolkit
  # install lives in a hidden ~/.searchatlas/ dir; Desktop is the one place
  # every user knows how to reach. Use cp (not symlink) so the Desktop copy
  # survives even if the user nukes ~/.searchatlas/. Idempotent: re-running
  # the installer just overwrites the Desktop copy.
  local desktop_dir="$HOME_DIR/Desktop"
  if [ -d "$desktop_dir" ]; then
    local desktop_cmd="$desktop_dir/SearchAtlas Mission Control.command"
    if cp "$start_cmd" "$desktop_cmd" 2>/dev/null; then
      chmod +x "$desktop_cmd" 2>/dev/null || true
      ok "Restart helper on Desktop: SearchAtlas Mission Control.command"
    fi
  fi
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
