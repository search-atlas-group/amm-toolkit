#!/usr/bin/env bash
# install-security-tools.sh — Install security scanning tools for /security-scan
# Designed for users with no prior developer tool knowledge.
# Safe to run multiple times — skips anything already installed.

set -uo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✓${RESET}  $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET}  $*"; }
fail() { echo -e "${RED}  ✗${RESET}  $*"; }
info() { echo -e "${DIM}     $*${RESET}"; }
step() { echo -e "\n${CYAN}  [$1]${RESET} $2"; }
hr()   { echo "  ──────────────────────────────────────────────────────"; }

clear

echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   Security Scan — Tool Installer                    ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
echo "  This installs four free security tools onto your Mac."
echo "  They run entirely on your computer — nothing is sent online."
echo "  Takes about 2 minutes. You only need to do this once."
echo ""
hr
echo ""

# ── Confirm before proceeding ─────────────────────────────────────────────────
read -p "  Ready to install? (Press Enter to continue, Ctrl+C to cancel) " -r
echo ""

# ── Step 1: Homebrew ──────────────────────────────────────────────────────────
step "1/4" "Homebrew — the app store for developer tools"
info "Homebrew lets you install and manage developer tools from a single place."
info "If you already have it, this step takes 1 second."
echo ""

if command -v brew &>/dev/null; then
  ok "Homebrew already installed ($(brew --version | head -1))"
else
  info "Installing Homebrew..."
  info "You may be asked for your Mac password — this is normal."
  echo ""
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Add brew to PATH on Apple Silicon
  if [[ -f "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile" 2>/dev/null || true
  fi

  if command -v brew &>/dev/null; then
    ok "Homebrew installed"
  else
    fail "Homebrew install failed"
    echo ""
    echo "  Try opening a new Terminal window and running this script again."
    echo "  If it keeps failing, visit: https://brew.sh"
    exit 1
  fi
fi

# ── Step 2: jq ───────────────────────────────────────────────────────────────
step "2/4" "jq — reads structured data (needed by the scanner)"
info "A small utility that helps read JSON data. Required for the scanner to work."

if command -v jq &>/dev/null; then
  ok "jq already installed"
else
  brew install jq 2>&1 | grep -E "^==>|✓|Error" | head -5
  command -v jq &>/dev/null && ok "jq installed" || warn "jq install failed (non-critical)"
fi

# ── Step 3: Security scanners ─────────────────────────────────────────────────
step "3/4" "Security scanners — the actual scanning engines"
echo ""

declare -A TOOL_DESC=(
  ["trivy"]="checks your code libraries against a database of known security holes"
  ["gitleaks"]="scans for accidentally committed passwords and API keys"
  ["trufflehog"]="digs through the full history of the repo for secrets that may have been deleted but are recoverable"
  ["semgrep"]="reads code looking for patterns that security experts know are dangerous"
)

for tool in trivy gitleaks trufflehog semgrep; do
  if command -v "$tool" &>/dev/null; then
    ok "$tool — already installed"
  else
    info "Installing $tool (${TOOL_DESC[$tool]})..."
    brew install "$tool" 2>&1 | grep -E "^==>|installed|Error" | tail -2
    if command -v "$tool" &>/dev/null; then
      ok "$tool installed"
    else
      warn "$tool install failed — scans will work but with reduced coverage"
    fi
  fi
done

# ── Step 4: Python tools ──────────────────────────────────────────────────────
step "4/4" "Python security tools (for Python repos)"
info "Only matters if you're scanning Python projects."

if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
  PIP=$(command -v pip3 2>/dev/null || command -v pip)
  for tool in bandit pip-audit; do
    if command -v "$tool" &>/dev/null; then
      ok "$tool — already installed"
    else
      "$PIP" install --quiet "$tool" 2>/dev/null && ok "$tool installed" || warn "$tool install failed (non-critical)"
    fi
  done
else
  warn "Python pip not found — skipping Python-specific tools"
  info "If you scan Python projects later, run: pip3 install bandit pip-audit"
fi

# ── chmod scripts ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/repo-security-scan.sh" \
         "$SCRIPT_DIR/repo-sandbox.sh" \
         "$SCRIPT_DIR/run-sandbox.sh" \
         "$SCRIPT_DIR/mac-sandbox-run.sh" \
         2>/dev/null || true

# ── Optional: Pre-build Docker image ─────────────────────────────────────────
echo ""
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  info "Docker detected — pre-building scanner image for faster first scan..."
  if [[ -f "$SCRIPT_DIR/Dockerfile.scanner" ]]; then
    docker build --quiet -t "repo-scanner:latest" -f "$SCRIPT_DIR/Dockerfile.scanner" "$SCRIPT_DIR" \
      2>&1 | tail -1 && ok "Docker scanner image ready" || warn "Docker image build failed (sandbox will build on first use)"
  fi
else
  info "Docker not installed — sandbox will use macOS built-in security (sandbox-exec) instead."
  info "That's completely fine. No Docker is needed for the sandbox to work."
fi

# ── Final summary ─────────────────────────────────────────────────────────────
echo ""
hr
echo ""
echo -e "  ${BOLD}All done!${RESET} Security tools are ready."
echo ""
echo "  How to scan a repo:"
echo ""
echo -e "  ${CYAN}  /security-scan https://github.com/owner/repo${RESET}"
echo ""
echo "  Or paste a local folder path:"
echo ""
echo -e "  ${CYAN}  /security-scan ~/Downloads/some-folder${RESET}"
echo ""
info "Questions? Read: guides/security-scan-guide.md"
echo ""
