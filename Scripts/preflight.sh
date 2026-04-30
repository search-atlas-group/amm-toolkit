#!/usr/bin/env bash
# Preflight check — run before setup.sh to verify all prerequisites are installed.
# Members using quickstart-mac.sh / quickstart-windows.ps1 will never hit this.
# This guard catches anyone who clones the repo directly and skips the quickstart.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "  ${RED}✗${NC}  $1"; }

FAILED=0
WARNED=0

MIN_NODE_MAJOR=18
MIN_GIT="2.30"

semver_gte() { [ "$(printf '%s\n' "$1" "$2" | sort -V | head -1)" = "$2" ]; }

QUICKSTART_MAC='  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"'
QUICKSTART_WIN='  irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex'

echo ""
echo "  Checking prerequisites..."
echo ""

# ── Git ───────────────────────────────────────────────────────────────────────
if command -v git &>/dev/null; then
  GIT_VER=$(git --version | awk '{print $3}')
  if semver_gte "$GIT_VER" "$MIN_GIT"; then
    ok "Git — $GIT_VER"
  else
    warn "Git $GIT_VER installed but outdated (need $MIN_GIT+)"
    if [[ "$OSTYPE" == "darwin"* ]]; then
      warn "Upgrade: brew upgrade git"
    else
      warn "Upgrade: winget upgrade Git.Git"
    fi
    WARNED=1
  fi
else
  fail "Git not found"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    warn "Install: brew install git  — or run the one-command quickstart:"
    warn "$QUICKSTART_MAC"
  else
    warn "Install: https://git-scm.com/download/win  — or run the one-command quickstart (PowerShell as Admin):"
    warn "$QUICKSTART_WIN"
  fi
  FAILED=1
fi

# ── Node.js ───────────────────────────────────────────────────────────────────
if command -v node &>/dev/null; then
  NODE_MAJOR=$(node --version | tr -d 'v' | cut -d. -f1)
  if [[ "$NODE_MAJOR" -ge "$MIN_NODE_MAJOR" ]]; then
    ok "Node.js — $(node --version)"
  else
    warn "Node.js $(node --version) installed but outdated (need v$MIN_NODE_MAJOR+)"
    if [[ "$OSTYPE" == "darwin"* ]]; then
      warn "Upgrade: brew upgrade node"
    else
      warn "Upgrade: winget upgrade OpenJS.NodeJS.LTS"
    fi
    WARNED=1
  fi
else
  fail "Node.js not found"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    warn "Install: brew install node  — or run the one-command quickstart:"
    warn "$QUICKSTART_MAC"
  else
    warn "Install: https://nodejs.org (choose LTS)  — or run the one-command quickstart (PowerShell as Admin):"
    warn "$QUICKSTART_WIN"
  fi
  FAILED=1
fi

# ── npm ───────────────────────────────────────────────────────────────────────
if command -v npm &>/dev/null; then
  ok "npm — $(npm --version)"
else
  fail "npm not found (usually installed with Node.js)"
  FAILED=1
fi


# ── Claude Code ───────────────────────────────────────────────────────────────
if command -v claude &>/dev/null; then
  ok "Claude Code CLI — $(claude --version 2>/dev/null | head -1)"
else
  fail "Claude Code not found"
  warn "Install: npm install -g @anthropic-ai/claude-code"
  FAILED=1
fi

echo ""

if [[ "$FAILED" -ne 0 ]]; then
  echo "  One or more prerequisites are missing."
  echo ""
  echo "  Fastest fix — run the one-command quickstart for your platform:"
  echo ""
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"'
  else
    echo "  irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex"
  fi
  echo ""
  exit 1
elif [[ "$WARNED" -ne 0 ]]; then
  echo "  All required tools are installed but some are outdated."
  echo "  Run the upgrade commands above, then re-run this check."
  echo ""
else
  echo "  All prerequisites met. Run: bash setup.sh"
  echo ""
fi
