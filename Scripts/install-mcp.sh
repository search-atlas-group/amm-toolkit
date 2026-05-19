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
OAUTH_URL="https://app.searchatlas.com/mcp/authorize?client=installer"
WELCOME_URL="https://cdn.jsdelivr.net/gh/search-atlas-group/amm-toolkit@main/docs/welcome.html"
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
  if write_mcp_config "$p" "http"; then ok "Claude Desktop — added SearchAtlas"; fi
}

install_cursor() {
  local p="$HOME_DIR/.cursor/mcp.json"
  [ -d "$HOME_DIR/.cursor" ] || { info "Cursor — not detected, skipped"; return 1; }
  if write_mcp_config "$p" "url-only"; then ok "Cursor — added SearchAtlas"; fi
}

install_windsurf() {
  local p="$HOME_DIR/.codeium/windsurf/mcp_config.json"
  [ -d "$HOME_DIR/.codeium/windsurf" ] || { info "Windsurf — not detected, skipped"; return 1; }
  if write_mcp_config "$p" "serverUrl"; then ok "Windsurf — added SearchAtlas"; fi
}

open_url() {
  local url="$1"
  case "$OS" in
    Darwin) open "$url" >/dev/null 2>&1 ;;
    Linux)  xdg-open "$url" >/dev/null 2>&1 ;;
    *)      return 1 ;;
  esac
}

# Open the welcome page first so it loads in a background tab, then open
# OAuth in a second tab. The OAuth tab gets focus (most recently opened),
# user finishes authorization, then naturally returns to the welcome tab
# as the visual payoff. Works for Claude Code, Claude Desktop, Cursor,
# and Windsurf installs — the welcome tab is the same.
open_browser() {
  if ! open_url "$WELCOME_URL"; then
    warn "Open this URL when you're done: $WELCOME_URL"
  fi
  # Tiny gap so the welcome tab is created first and OAuth lands on top.
  sleep 1
  if ! open_url "$OAUTH_URL"; then
    warn "Open this URL to authorize: $OAUTH_URL"
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

  echo "  $(c_bold 'Opening SearchAtlas welcome + login…')"
  open_browser
  ok "Two browser tabs opened: welcome page + SearchAtlas authorization"
  info "Finish OAuth in the front tab; the welcome page is waiting behind it"
  echo
  echo "  $(c_dim 'Re-run anytime with: curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash')"
  echo
}

main "$@"
