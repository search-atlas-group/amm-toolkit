#!/usr/bin/env bash
# Agentic Marketing Mastermind — Interactive Setup Wizard
# Configures the SearchAtlas MCP (OAuth) and optional communication channels.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

echo ""
echo "  Agentic Marketing Mastermind — Setup Wizard"
echo "  ============================================"
echo ""

# ── Prerequisites ────────────────────────────────────────────────────────────

echo "[1/3] Checking prerequisites..."

if ! command -v claude &>/dev/null; then
  echo "  ERROR: Claude Code CLI not found."
  echo "  Install it first: https://claude.ai/code"
  exit 1
fi

if ! command -v python3 &>/dev/null && ! command -v jq &>/dev/null; then
  echo "  WARN: Neither python3 nor jq found — .env writing may be limited."
fi

echo "  Claude Code: $(claude --version 2>/dev/null | head -1 || echo 'installed')"
echo ""

# ── Step 1: SearchAtlas MCP (OAuth) ──────────────────────────────────────────

echo "[2/3] Configuring SearchAtlas MCP server..."
echo ""
echo "  This adds the SearchAtlas MCP to your Claude Code installation."
echo "  Authentication is handled via OAuth — no API key required."
echo ""

# Check if already configured
if claude mcp list 2>/dev/null | grep -q "searchatlas"; then
  echo "  SearchAtlas MCP is already configured."
  read -p "  Re-add it? (y/n): " READD
  if [[ "$READD" == "y" || "$READD" == "Y" ]]; then
    claude mcp remove searchatlas 2>/dev/null || true
    claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp
    echo "  Configured: searchatlas → https://mcp.searchatlas.com/mcp"
  fi
else
  claude mcp add searchatlas --transport http https://mcp.searchatlas.com/mcp
  echo "  Configured: searchatlas → https://mcp.searchatlas.com/mcp"
fi

echo ""
echo "  NOTE: The first time you use a SearchAtlas tool in Claude Code,"
echo "  you'll be prompted to authorize via OAuth (your SearchAtlas login)."
echo ""

# ── Step 2: Communication Channels (optional) ────────────────────────────────

echo "[3/3] Communication channels (optional)"
echo "  Where do you share results with clients?"
echo "  [1] Slack     — webhook URL per channel"
echo "  [2] Discord   — webhook URL"
echo "  [3] Email     — Resend API key"
echo "  [4] Circle    — API key + community ID"
echo "  [s] Skip for now"
echo ""

read -p "  Select (comma-separated, e.g. 1,3): " CHANNEL_SELECTION
echo ""

SLACK_WEBHOOK_URL=""
SLACK_EXTRA_WEBHOOKS=""
DISCORD_WEBHOOK_URL=""
RESEND_API_KEY=""
EMAIL_FROM=""
CIRCLE_API_KEY=""
CIRCLE_COMMUNITY_ID=""

if [[ "$CHANNEL_SELECTION" != "s" && -n "$CHANNEL_SELECTION" ]]; then
  IFS=',' read -ra SELECTIONS <<< "$CHANNEL_SELECTION"
  for sel in "${SELECTIONS[@]}"; do
    sel=$(echo "$sel" | tr -d ' ')
    case "$sel" in
      1)
        echo "  Slack:"
        read -p "    Channel name (e.g. client-reports): " SLACK_CHANNEL_NAME
        read -p "    Webhook URL: " SLACK_WEBHOOK_URL
        SLACK_EXTRA_WEBHOOKS=""
        while true; do
          read -p "    Add another Slack channel? (y/n): " ADD_MORE
          if [[ "$ADD_MORE" == "y" || "$ADD_MORE" == "Y" ]]; then
            read -p "    Channel name: " EXTRA_NAME
            read -p "    Webhook URL: " EXTRA_URL
            EXTRA_NAME_UPPER=$(echo "$EXTRA_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
            SLACK_EXTRA_WEBHOOKS="${SLACK_EXTRA_WEBHOOKS}SLACK_WEBHOOK_${EXTRA_NAME_UPPER}=${EXTRA_URL}\n"
          else
            break
          fi
        done
        echo ""
        ;;
      2)
        echo "  Discord:"
        echo "    Create a webhook at: Server Settings → Integrations → Webhooks"
        read -p "    Webhook URL: " DISCORD_WEBHOOK_URL
        echo ""
        ;;
      3)
        echo "  Email (Resend):"
        echo "    Sign up at: https://resend.com → API Keys"
        read -p "    API key: " RESEND_API_KEY
        read -p "    Default \"from\" address: " EMAIL_FROM
        echo ""
        ;;
      4)
        echo "  Circle:"
        echo "    Get your key at: https://app.circle.so → Settings → API"
        read -p "    API Key: " CIRCLE_API_KEY
        if [[ -n "${CIRCLE_API_KEY:-}" ]]; then
          read -p "    Community ID: " CIRCLE_COMMUNITY_ID
        fi
        echo ""
        ;;
    esac
  done
fi

# ── Write .env ───────────────────────────────────────────────────────────────

HAS_COMMS=false
for v in "$SLACK_WEBHOOK_URL" "$DISCORD_WEBHOOK_URL" "$RESEND_API_KEY" "$CIRCLE_API_KEY"; do
  [[ -n "$v" ]] && HAS_COMMS=true && break
done

if [[ "$HAS_COMMS" == "true" ]]; then
  echo "Writing .env..."

  cat > "$ENV_FILE" <<EOF
# Agentic Marketing Mastermind — Environment Variables
# DO NOT COMMIT this file.

# Slack Integration (optional)
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
EOF

  if [[ -n "${SLACK_EXTRA_WEBHOOKS:-}" ]]; then
    echo -e "$SLACK_EXTRA_WEBHOOKS" >> "$ENV_FILE"
  fi

  cat >> "$ENV_FILE" <<EOF

# Discord Integration (optional)
DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL:-}

# Email Integration — Resend (optional)
RESEND_API_KEY=${RESEND_API_KEY:-}
EMAIL_FROM=${EMAIL_FROM:-}

# Circle Community Integration (optional)
CIRCLE_API_KEY=${CIRCLE_API_KEY:-}
CIRCLE_COMMUNITY_ID=${CIRCLE_COMMUNITY_ID:-}
EOF

  chmod 600 "$ENV_FILE"
  echo "  Created $ENV_FILE (permissions: 600)"

  if [[ -f "$PROJECT_DIR/.gitignore" ]]; then
    if ! grep -q "^\.env$" "$PROJECT_DIR/.gitignore" 2>/dev/null; then
      echo ".env" >> "$PROJECT_DIR/.gitignore"
    fi
  fi
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "  ============================================"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Verify:  bash scripts/verify-setup.sh"
echo "    2. Open Claude Code in this directory"
echo "    3. Try:     /my-account  (will trigger OAuth on first use)"
echo "  ============================================"
