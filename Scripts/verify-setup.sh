#!/usr/bin/env bash
# Agentic Marketing Mastermind — Setup Verification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

PASS="[PASS]"
FAIL="[FAIL]"
WARN="[WARN]"
errors=0

MIN_NODE_MAJOR=18
MIN_GIT="2.30"
MIN_JAVA_MAJOR=17

semver_gte() { [ "$(printf '%s\n' "$1" "$2" | sort -V | head -1)" = "$2" ]; }

echo "SearchAtlas MCP — Setup Verification"
echo "════════════════════════════════════════"
echo ""

# ── Check 0: Git ─────────────────────────────────────────────────────────────

if ! command -v git &>/dev/null; then
  echo "$FAIL Git: not installed"
  echo "       Fix: brew install git  (or re-run quickstart)"
  errors=$((errors + 1))
elif ! semver_gte "$(git --version | awk '{print $3}')" "$MIN_GIT"; then
  echo "$WARN Git: $(git --version | awk '{print $3}') — outdated (need $MIN_GIT+)"
  echo "       Fix: brew upgrade git"
else
  echo "$PASS Git: $(git --version | awk '{print $3}')"
fi

# ── Check 0b: Node.js ────────────────────────────────────────────────────────

if ! command -v node &>/dev/null; then
  echo "$FAIL Node.js: not installed"
  echo "       Fix: brew install node  (or re-run quickstart)"
  errors=$((errors + 1))
else
  NODE_MAJOR=$(node --version | tr -d 'v' | cut -d. -f1)
  if [[ "$NODE_MAJOR" -lt "$MIN_NODE_MAJOR" ]]; then
    echo "$WARN Node.js: $(node --version) — outdated (need v$MIN_NODE_MAJOR+)"
    echo "       Fix: brew upgrade node"
  else
    echo "$PASS Node.js: $(node --version) · npm $(npm --version)"
  fi
fi

# ── Check 0c: Java ───────────────────────────────────────────────────────────

if ! command -v java &>/dev/null; then
  echo "$FAIL Java: not installed"
  echo "       Fix: brew install openjdk@21  (or re-run quickstart)"
  errors=$((errors + 1))
else
  JAVA_VER=$(java -version 2>&1 | head -1 | awk -F'"' '{print $2}')
  JAVA_MAJOR=$(echo "$JAVA_VER" | cut -d. -f1)
  [[ "$JAVA_MAJOR" == "1" ]] && JAVA_MAJOR=$(echo "$JAVA_VER" | cut -d. -f2)
  if [[ "$JAVA_MAJOR" -lt "$MIN_JAVA_MAJOR" ]]; then
    echo "$WARN Java: $JAVA_VER — outdated (need $MIN_JAVA_MAJOR+)"
    echo "       Fix: brew install openjdk@21"
  else
    echo "$PASS Java: $JAVA_VER"
  fi
fi

# ── Check 1: Claude Code CLI ─────────────────────────────────────────────────

if command -v claude &>/dev/null; then
  VERSION=$(claude --version 2>/dev/null | head -1 || echo "installed")
  echo "$PASS Claude Code CLI: $VERSION"
else
  echo "$FAIL Claude Code CLI not found"
  echo "       Fix: npm install -g @anthropic-ai/claude-code"
  errors=$((errors + 1))
fi

# ── Check 2: SearchAtlas MCP configured ──────────────────────────────────────

if command -v claude &>/dev/null; then
  if claude mcp list 2>/dev/null | grep -q "searchatlas"; then
    echo "$PASS SearchAtlas MCP: configured"
  else
    echo "$FAIL SearchAtlas MCP: not found"
    echo "       Fix: claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp"
    errors=$((errors + 1))
  fi
fi

# ── Check 3: MCP endpoint reachable ─────────────────────────────────────────

if command -v curl &>/dev/null; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://mcp.searchatlas.com/mcp" \
    --connect-timeout 8 2>/dev/null || echo "000")

  if [[ "$HTTP_CODE" == "401" ]]; then
    echo "$PASS MCP endpoint reachable (HTTP 401 = needs OAuth, expected)"
  elif [[ "$HTTP_CODE" == "000" ]]; then
    echo "$WARN MCP endpoint: could not connect (network issue or timeout)"
  else
    echo "$WARN MCP endpoint: HTTP $HTTP_CODE"
  fi
fi

# ── Check 4: Slash commands installed ───────────────────────────────────────

COMMANDS_DST="$HOME/.claude/commands"
EXPECTED_COMMANDS=(my-account business-report onboard-client run-seo run-gbp run-ppc run-content run-pr run-visibility send-slack send-discord send-email send-circle help)
MISSING=0

for cmd in "${EXPECTED_COMMANDS[@]}"; do
  if [[ ! -f "$COMMANDS_DST/$cmd.md" ]]; then
    MISSING=$((MISSING + 1))
  fi
done

if [[ $MISSING -eq 0 ]]; then
  echo "$PASS Slash commands: all ${#EXPECTED_COMMANDS[@]} installed"
else
  echo "$WARN Slash commands: $MISSING missing — run 'bash setup.sh' to install"
fi

# ── Check 5: Optional comms integrations ─────────────────────────────────────

echo ""
echo "Optional integrations:"

if [[ -f "$ENV_FILE" ]]; then
  SLACK_URL=$(grep -E '^SLACK_WEBHOOK_URL=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
  DISCORD_URL=$(grep -E '^DISCORD_WEBHOOK_URL=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
  RESEND_KEY=$(grep -E '^RESEND_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
  CIRCLE_KEY=$(grep -E '^CIRCLE_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)

  [[ -n "${SLACK_URL:-}" ]]   && echo "  $PASS Slack"    || echo "  $WARN Slack: not configured (for /send-slack)"
  [[ -n "${DISCORD_URL:-}" ]] && echo "  $PASS Discord"  || echo "  $WARN Discord: not configured (for /send-discord)"
  [[ -n "${RESEND_KEY:-}" ]]  && echo "  $PASS Email"    || echo "  $WARN Email: not configured (for /send-email)"
  [[ -n "${CIRCLE_KEY:-}" ]]  && echo "  $PASS Circle"   || echo "  $WARN Circle: not configured (for /send-circle)"
else
  echo "  $WARN No .env file — run 'bash scripts/setup-interactive.sh' to configure comms"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
if [[ $errors -eq 0 ]]; then
  echo "All checks passed. Open Claude Code and try /my-account"
else
  echo "$errors check(s) failed. Fix the issues above and re-run."
fi
