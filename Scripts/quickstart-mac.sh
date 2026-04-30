#!/usr/bin/env bash
# Agentic Marketing Mastermind — macOS Quick Start
# Creates your workspace, installs all prerequisites, and launches Claude Code.
#
# Usage (copy-paste into Terminal):
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"

set -e

REPO_URL="https://github.com/search-atlas-group/amm-toolkit.git"
QUICKSTART_URL="https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
step() { echo -e "\n  ${CYAN}[$1]${NC} $2"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
info() { echo -e "  $1"; }
hr()   { echo "  ─────────────────────────────────────────────────────"; }

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║    Agentic Marketing Mastermind — macOS Setup       ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
echo "  This sets up your full agentic workspace from scratch."
echo "  Estimated time: 5–10 minutes. You'll only need to do this once."
echo ""

# ── Preflight: Xcode (must pass before any prompts) ──────────────────────────
# Check this first so the script never exits mid-questionnaire.
if ! xcode-select -p &>/dev/null; then
  hr
  warn "Xcode Command Line Tools not found — installing..."
  xcode-select --install 2>/dev/null || true
  echo ""
  echo "  A macOS dialog just opened — click Install and wait for it to finish."
  echo "  Then re-run this script:"
  echo ""
  echo "  /bin/bash -c \"\$(curl -fsSL $QUICKSTART_URL)\""
  echo ""
  exit 0
fi
ok "Xcode Command Line Tools"
echo ""

# ── Workspace detection / naming ─────────────────────────────────────────────
hr
echo ""

# Scan Desktop for any existing AMM workspace (has CLAUDE.md + amm-toolkit/ inside)
EXISTING=()
for dir in "$HOME/Desktop"/*/; do
  [[ -f "${dir}CLAUDE.md" && -d "${dir}amm-toolkit" ]] && EXISTING+=("${dir%/}")
done

if [[ ${#EXISTING[@]} -eq 1 ]]; then
  WORKSPACE_DIR="${EXISTING[0]}"
  WORKSPACE_NAME="$(basename "$WORKSPACE_DIR")"
  ok "Found existing workspace: $WORKSPACE_DIR"
  echo "  Updating it instead of creating a new one."
elif [[ ${#EXISTING[@]} -gt 1 ]]; then
  echo -e "  ${BOLD}Multiple workspaces found — pick one to update:${NC}"
  echo ""
  for i in "${!EXISTING[@]}"; do
    echo "  $((i+1)). ${EXISTING[$i]}"
  done
  echo ""
  echo -n "  Enter number (Enter for 1): "
  read -r WS_NUM </dev/tty
  WS_NUM="${WS_NUM:-1}"
  if ! [[ "$WS_NUM" =~ ^[0-9]+$ ]] || (( WS_NUM < 1 || WS_NUM > ${#EXISTING[@]} )); then
    WS_NUM=1
  fi
  WORKSPACE_DIR="${EXISTING[$((WS_NUM-1))]}"
  WORKSPACE_NAME="$(basename "$WORKSPACE_DIR")"
  ok "Using: $WORKSPACE_DIR"
else
  echo -e "  ${BOLD}Name your workspace${NC}"
  echo ""
  echo "  This is the root folder where everything lives."
  echo "  Name it after your agency so it's easy to find."
  echo ""
  echo "  Examples:  CoastalMedia-AMM  |  SunriseAgency-AI  |  AMM-Workspace"
  echo ""
  echo -n "  Workspace name (Enter for 'AMM-Workspace'): "
  read -r WORKSPACE_NAME </dev/tty
  WORKSPACE_NAME="${WORKSPACE_NAME:-AMM-Workspace}"
  WORKSPACE_DIR="$HOME/Desktop/$WORKSPACE_NAME"
  ok "Workspace → $WORKSPACE_DIR"
fi

REPO_DIR="$WORKSPACE_DIR/amm-toolkit"

# Create the workspace folder immediately so it appears on Desktop right away
mkdir -p "$WORKSPACE_DIR/clients" "$WORKSPACE_DIR/memory"
ok "Folder created: $WORKSPACE_DIR"
echo ""

# ── IDE / Terminal Selection ──────────────────────────────────────────────────
hr
echo ""
echo -e "  ${BOLD}Choose your coding environment${NC}"
echo ""
echo "  You only need one. We'll detect what you already have"
echo "  and suggest it — or you can pick a different one to download."
echo ""

IDE_NAMES=("Cursor" "Warp" "VS Code" "Windsurf" "iTerm2" "Terminal (built-in)")
IDE_URLS=("https://cursor.com" "https://www.warp.dev" "https://code.visualstudio.com" "https://windsurf.com" "https://iterm2.com" "")
IDE_OPEN_CMDS=('cursor "$WORKSPACE_DIR"' 'open -a Warp "$WORKSPACE_DIR"' 'code "$WORKSPACE_DIR"' 'windsurf "$WORKSPACE_DIR"' 'open -a iTerm "$WORKSPACE_DIR"' '')
IDE_STATUS=()

for i in "${!IDE_NAMES[@]}"; do
  case "${IDE_NAMES[$i]}" in
    "Cursor")
      ([[ -d "/Applications/Cursor.app" ]] || command -v cursor &>/dev/null) && IDE_STATUS[$i]="ready" || IDE_STATUS[$i]="not installed"
      ;;
    "Warp")
      [[ -d "/Applications/Warp.app" ]] && IDE_STATUS[$i]="ready" || IDE_STATUS[$i]="not installed"
      ;;
    "VS Code")
      ([[ -d "/Applications/Visual Studio Code.app" ]] || command -v code &>/dev/null) && IDE_STATUS[$i]="ready" || IDE_STATUS[$i]="not installed"
      ;;
    "Windsurf")
      ([[ -d "/Applications/Windsurf.app" ]] || command -v windsurf &>/dev/null) && IDE_STATUS[$i]="ready" || IDE_STATUS[$i]="not installed"
      ;;
    "iTerm2")
      [[ -d "/Applications/iTerm.app" ]] && IDE_STATUS[$i]="ready" || IDE_STATUS[$i]="not installed"
      ;;
    "Terminal (built-in)")
      IDE_STATUS[$i]="ready"
      ;;
  esac
done

REC_IDX=5
REC_NAME="Terminal (built-in)"
for i in 0 1 2 3 4; do
  if [[ "${IDE_STATUS[$i]}" == "ready" ]]; then
    REC_IDX=$i
    REC_NAME="${IDE_NAMES[$i]}"
    break
  fi
done

if [[ "$REC_NAME" == "Terminal (built-in)" ]]; then
  echo "  You don't have a dedicated coding environment installed yet."
  echo "  We recommend Cursor — it's built for AI-assisted work."
  echo "  Enter 1 to download it, or pick any option from the list."
else
  echo -e "  We found ${BOLD}$REC_NAME${NC} on your Mac — that's a solid choice."
  echo "  Press Enter to use it, or pick something else from the list below."
fi

echo ""

for i in "${!IDE_NAMES[@]}"; do
  name="${IDE_NAMES[$i]}"
  status="${IDE_STATUS[$i]}"
  num="$((i+1))"
  label="$(printf '%-22s' "$name")"
  if [[ "$i" == "$REC_IDX" && "$status" == "ready" ]]; then
    echo -e "  $num. ${label} ${GREEN}✓ installed${NC}  ← recommended"
  elif [[ "$status" == "ready" ]]; then
    echo -e "  $num. ${label} ${GREEN}✓ installed${NC}"
  else
    echo -e "  $num. ${label} ${DIM}— not installed${NC}"
  fi
done

echo ""
echo -n "  Enter number (Enter for $REC_NAME): "
read -r IDE_NUM </dev/tty
IDE_NUM="${IDE_NUM:-$((REC_IDX+1))}"

if ! [[ "$IDE_NUM" =~ ^[0-9]+$ ]] || (( IDE_NUM < 1 || IDE_NUM > ${#IDE_NAMES[@]} )); then
  IDE_NUM=$((REC_IDX+1))
fi

IDX=$((IDE_NUM - 1))
IDE_NAME="${IDE_NAMES[$IDX]}"
IDE_STATUS_CHOSEN="${IDE_STATUS[$IDX]}"
IDE_URL="${IDE_URLS[$IDX]}"
IDE_OPEN_CMD="${IDE_OPEN_CMDS[$IDX]}"
IDE_NOT_INSTALLED=0

echo ""

if [[ "$IDE_STATUS_CHOSEN" == "not installed" ]]; then
  IDE_NOT_INSTALLED=1
  echo -e "  ${YELLOW}⚠${NC}  $IDE_NAME is not installed yet."
  echo ""
  echo "  Download: $IDE_URL"
  echo ""
  echo -n "  Open the download page now? (y/n): "
  read -r OPEN_DL </dev/tty
  if [[ "$OPEN_DL" == "y" || "$OPEN_DL" == "Y" ]]; then
    open "$IDE_URL" 2>/dev/null || true
    echo ""
    info "Download page opened. Install $IDE_NAME, then come back here."
    info "Setup will continue and finish — you can open your workspace"
    info "in $IDE_NAME afterwards."
  fi
  IDE_OPEN_CMD=""
else
  ok "Using: $IDE_NAME"
fi

echo ""
hr

# ── Step 1: Node.js via nvm ───────────────────────────────────────────────────
# nvm installs via curl — no massive git clone, no sudo required.
step "1/3" "Node.js"

MIN_NODE_MAJOR=18

node_ok() {
  command -v node &>/dev/null || return 1
  local m; m=$(node --version | tr -d 'v' | cut -d. -f1)
  [[ "$m" -ge "$MIN_NODE_MAJOR" ]]
}

NVM_DIR="$HOME/.nvm"

if node_ok; then
  ok "Node $(node --version) · npm $(npm --version)"
else
  warn "Node.js not found — installing via nvm..."
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  export NVM_DIR="$NVM_DIR"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  nvm install --lts
  nvm use --lts
  # Persist nvm in shell profile
  SHELL_PROFILE="$HOME/.zprofile"
  [[ "$SHELL" == *"bash"* ]] && SHELL_PROFILE="$HOME/.bash_profile"
  grep -q 'NVM_DIR' "$SHELL_PROFILE" 2>/dev/null || cat >> "$SHELL_PROFILE" <<'NVM_PROFILE'

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
NVM_PROFILE
  ok "Node $(node --version) · npm $(npm --version)"
fi

# ── Step 3: Claude Code ───────────────────────────────────────────────────────
step "2/3" "Claude Code"

if command -v claude &>/dev/null; then
  ok "Already installed — $(claude --version 2>/dev/null | head -1)"
else
  info "Installing via npm..."
  npm install -g @anthropic-ai/claude-code
  ok "Installed — $(claude --version 2>/dev/null | head -1)"
fi

# ── Step 4: Workspace + amm-toolkit Toolkit ───────────────────────────────────────
step "3/3" "Setting up workspace"

if [[ -d "$REPO_DIR" ]]; then
  info "Toolkit already present — pulling latest..."
  git -C "$REPO_DIR" pull origin main 2>/dev/null || true
else
  info "Cloning amm-toolkit toolkit..."
  git clone -b main "$REPO_URL" "$REPO_DIR"
fi
ok "amm-toolkit toolkit ready"

# ── CLAUDE.md ─────────────────────────────────────────────────────────────────
if [[ ! -f "$WORKSPACE_DIR/CLAUDE.md" ]]; then
  cat > "$WORKSPACE_DIR/CLAUDE.md" <<CLAUDEMD
# $WORKSPACE_NAME — Agentic Marketing Workspace

## Session Start (every session, no exceptions)
1. Read \`memory/MEMORY.md\` — reload all active rules and client context
2. Confirm which client you are working on before touching any files
3. Run \`/my-account\` if you need a fresh view of the SearchAtlas account

## Working Directory Check
If you are not running from inside the \`$WORKSPACE_NAME\` workspace folder,
stop and tell the user: "It looks like Claude is running from the wrong folder.
Open your IDE from $WORKSPACE_NAME/ and restart the session."
Never work from the system home directory or any folder outside this workspace.

## My Agency
<!-- Fill in: agency name, niche, location, team size -->

## My Clients
<!-- One line per client once onboarded — e.g.:
- Acme Roofing (acme-roofing/) — local SEO, GBP, monthly retainer
- Coastal Dental (coastal-dental/) — PPC + content, active campaign
-->

## My Integrations
- SearchAtlas — SEO, GBP, PPC, content, authority building
<!-- Add yours after /setup-integrations:
- Slack webhook: SLACK_WEBHOOK_URL in .env
- Email (Resend): RESEND_API_KEY in .env
- Discord: DISCORD_WEBHOOK_URL in .env
-->

## Session Rules
- \`/clear\` between every client — never carry one client's context into another
- \`/compact\` when responses slow down (or proactively at ~70% context)
- Save new learnings to \`memory/\` before closing a session
- Never paste API keys into the chat — they live in \`.env\` only
- Confirm before creating campaigns, publishing content, or sending messages

## Multi-Machine Note
MCP connections are machine-specific and do not sync between computers.
If you set up a second machine, run the quickstart again on that machine —
your files sync but your MCP config does not carry over automatically.

## Workspace Layout
- \`amm-toolkit/\`     — toolkit: slash commands, workflows, scripts (do not edit)
- \`clients/\`   — one subfolder per client with brief.md + assets/
- \`memory/\`    — persistent notes Claude reads and writes across sessions
- \`.env\`        — API keys and webhook URLs (never committed to git)
CLAUDEMD
  info "Created: $WORKSPACE_DIR/CLAUDE.md"
fi

# ── memory/MEMORY.md ──────────────────────────────────────────────────────────
if [[ ! -f "$WORKSPACE_DIR/memory/MEMORY.md" ]]; then
  cat > "$WORKSPACE_DIR/memory/MEMORY.md" <<MEMORYMD
# Memory Index

> Claude reads this file at the start of every session.
> Keep this file under 150 lines — link to separate files for detail.

## How to add a memory
Save a .md file in this folder and add a one-line link below.
Format: \`- [Title](filename.md) — one-line description\`

## Active Rules
<!-- Claude adds feedback and learned rules here -->

## Client Notes
<!-- One entry per client once you start building context
- [Acme Roofing](acme-roofing.md) — niche: residential, top keyword: roof repair Phoenix
-->

## Tool Notes
<!-- SearchAtlas gotchas, integration quirks, API patterns -->

## Open Items
<!-- Follow-ups, pending tasks, questions for next session -->
MEMORYMD
  info "Created: $WORKSPACE_DIR/memory/MEMORY.md"
fi

# ── .env scaffold ─────────────────────────────────────────────────────────────
if [[ ! -f "$WORKSPACE_DIR/.env" ]]; then
  cat > "$WORKSPACE_DIR/.env" <<ENVFILE
# Agentic Marketing Workspace — Environment Variables
# Fill in what you use. Never commit this file.

# ── Communication integrations ────────────────────────────────────────────────
SLACK_WEBHOOK_URL=
DISCORD_WEBHOOK_URL=
RESEND_API_KEY=
EMAIL_FROM=

# ── Circle ────────────────────────────────────────────────────────────────────
CIRCLE_API_KEY=
CIRCLE_COMMUNITY_ID=

# ── Optional CRM / PM integrations ───────────────────────────────────────────
# (fill after running /setup-integrations)
ENVFILE
  info "Created: $WORKSPACE_DIR/.env"
fi

# ── .gitignore ────────────────────────────────────────────────────────────────
if [[ ! -f "$WORKSPACE_DIR/.gitignore" ]]; then
  cat > "$WORKSPACE_DIR/.gitignore" <<GITIGNORE
.env
.env.*
!.env.example
clients/*/assets/
memory/sessions/
*.log
.DS_Store
Thumbs.db
GITIGNORE
  info "Created: $WORKSPACE_DIR/.gitignore"
fi

cd "$REPO_DIR"
bash setup.sh

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
hr
echo ""
echo -e "  ${BOLD}Your workspace is ready.${NC}"
echo ""
echo "  $WORKSPACE_DIR/"
echo "  ├── amm-toolkit/       ← toolkit (slash commands, workflows)"
echo "  ├── clients/      ← one folder per client"
echo "  ├── memory/       ← Claude's persistent notes"
echo "  ├── CLAUDE.md     ← your session rules and client list"
echo "  └── .env          ← API keys (fill in after /setup-integrations)"
echo ""
hr
echo ""

if [[ "$IDE_NOT_INSTALLED" == "1" ]]; then
  echo "  Once $IDE_NAME is installed, open your workspace with:"
  echo ""
  echo -e "    ${BOLD}${IDE_OPEN_CMDS[$IDX]}${NC}    (or drag the folder into the app)"
  echo ""
  echo "  Then in the integrated terminal, run:"
  echo ""
  echo -e "    ${BOLD}claude${NC}"
elif [[ "$IDE_NAME" == "Terminal (built-in)" ]]; then
  echo "  Opening a new Terminal window inside your workspace..."
  osascript -e "tell application \"Terminal\"
    activate
    do script \"cd '$WORKSPACE_DIR' && echo '✓ You are inside your workspace. Now run: claude' && claude\"
  end tell" 2>/dev/null || true
elif [[ -n "$IDE_OPEN_CMD" ]]; then
  echo "  Opening $IDE_NAME at your workspace..."
  eval "$IDE_OPEN_CMD" 2>/dev/null || true
  echo ""
  echo "  In $IDE_NAME, open the integrated terminal and run:"
  echo ""
  echo -e "    ${BOLD}claude${NC}"
else
  echo ""
  echo -e "  ${YELLOW}⚠  IMPORTANT: you must cd into your workspace first.${NC}"
  echo "  Running claude from the wrong folder creates files in the wrong place."
  echo ""
  echo -e "    ${BOLD}cd ~/Desktop/$WORKSPACE_NAME${NC}"
  echo -e "    ${BOLD}claude${NC}"
fi

echo ""
echo "  ─────────────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Important: first-time permission prompt${NC}"
echo ""
echo "  Claude Code may show a permission warning on first launch."
echo "  This is expected. When prompted, choose:"
echo -e "    ${BOLD}Yes, allow for this session${NC}  (or the equivalent option)"
echo ""
echo "  Or launch with permissions pre-approved (recommended for beginners):"
echo ""
echo -e "    ${BOLD}claude --dangerously-skip-permissions${NC}"
echo ""
echo "  ─────────────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Once Claude Code opens — here's what to do first:${NC}"
echo ""
echo -e "  ${BOLD}Step 1${NC} — Authorize SearchAtlas (first time only)"
echo ""
echo -e "    ${BOLD}/my-account${NC}"
echo ""
echo "  This connects your SearchAtlas account. A browser tab will open"
echo "  asking you to log in and approve access. Do that, then come back."
echo ""
echo "  ─────────────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Step 2${NC} — Add your first client"
echo ""
echo -e "    ${BOLD}/onboard-client${NC}"
echo ""
echo "  This walks you through setting up your first client:"
echo "  their domain, brand voice, SEO project, and GBP profile."
echo "  Takes about 5 minutes. Do one client to start."
echo ""
echo "  ─────────────────────────────────────────────────────"
echo ""
echo -e "  ${BOLD}Step 3${NC} — Run your first workflow"
echo ""
echo -e "    ${BOLD}/run-seo${NC}       — monthly SEO maintenance"
echo -e "    ${BOLD}/business-report${NC}  — full client audit"
echo -e "    ${BOLD}/run-gbp${NC}       — Google Business Profile optimization"
echo ""
hr
echo ""
