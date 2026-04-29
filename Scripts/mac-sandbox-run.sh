#!/usr/bin/env bash
# mac-sandbox-run.sh — Run a repo in macOS native sandbox (no Docker required)
# Usage: bash mac-sandbox-run.sh <repo_url> [--timeout 90]
#
# This uses sandbox-exec, which is built into every Mac.
# The code runs in a sealed zone: no internet, no access to your real files.
# The zone is deleted after the test.

set -uo pipefail

REPO_URL="${1:-}"
TIMEOUT=90
OUTPUT_DIR="/tmp/sandbox-results"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: $0 <repo_url> [--timeout N]"
  exit 1
fi

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --output)  OUTPUT_DIR="$2"; shift 2 ;;
    *) shift ;;
  esac
done

REPO_NAME=$(basename "$REPO_URL" .git)
WORK_DIR=$(mktemp -d /tmp/sandbox-XXXXXX)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_PROFILE="$SCRIPT_DIR/mac-sandbox.sb"
SANDBOX_LOG="$OUTPUT_DIR/mac-sandbox-output.txt"
SANDBOX_REPORT="$OUTPUT_DIR/mac-sandbox-report.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$OUTPUT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()  { echo -e "${CYAN}[sandbox]${RESET} $*" | tee -a "$SANDBOX_LOG"; }
ok()   { echo -e "${GREEN}[sandbox]${RESET} $*" | tee -a "$SANDBOX_LOG"; }
warn() { echo -e "${YELLOW}[sandbox]${RESET} $*" | tee -a "$SANDBOX_LOG"; }
fail() { echo -e "${RED}[sandbox]${RESET} $*" | tee -a "$SANDBOX_LOG"; }

trap 'rm -rf "$WORK_DIR"' EXIT

# ── Check sandbox-exec availability ──────────────────────────────────────────
if ! command -v sandbox-exec &>/dev/null; then
  fail "sandbox-exec not found. This tool requires macOS 10.5 or later."
  exit 1
fi

log "Using macOS native sandbox (sandbox-exec) — no Docker required"
log "Repo:    $REPO_URL"
log "Timeout: ${TIMEOUT}s"
log "Zone:    $WORK_DIR"

# ── Clone first (outside sandbox, just the code download) ─────────────────────
log "Cloning repository..."
git clone --depth=1 "$REPO_URL" "$WORK_DIR" 2>>"$SANDBOX_LOG" || {
  fail "Clone failed"
  exit 1
}
ok "Cloned. Now running in sandboxed zone..."

# ── Record pre-run state ──────────────────────────────────────────────────────
find /tmp -maxdepth 2 2>/dev/null | sort > /tmp/before-sandbox.txt || true

# ── Determine what to run inside the sandbox ─────────────────────────────────
INSTALL_CMD=""

if [[ -f "$WORK_DIR/package.json" ]]; then
  INSTALL_CMD="cd $WORK_DIR && npm install --ignore-scripts 2>&1; npm install 2>&1"
  log "Detected: Node.js project"
elif [[ -f "$WORK_DIR/requirements.txt" ]]; then
  INSTALL_CMD="cd $WORK_DIR && python3 -m venv /tmp/sandbox-venv && source /tmp/sandbox-venv/bin/activate && pip install -r requirements.txt 2>&1"
  log "Detected: Python project"
elif [[ -f "$WORK_DIR/setup.py" ]]; then
  INSTALL_CMD="cd $WORK_DIR && python3 -m venv /tmp/sandbox-venv && source /tmp/sandbox-venv/bin/activate && python3 setup.py install 2>&1"
  log "Detected: Python package (setup.py)"
elif [[ -f "$WORK_DIR/Gemfile" ]]; then
  INSTALL_CMD="cd $WORK_DIR && bundle install 2>&1"
  log "Detected: Ruby project"
elif [[ -f "$WORK_DIR/Makefile" ]]; then
  INSTALL_CMD="cd $WORK_DIR && make install 2>&1"
  log "Detected: Makefile project"
else
  INSTALL_CMD="ls $WORK_DIR"
  log "No package manager detected — listing contents only"
fi

# ── Run in macOS sandbox ──────────────────────────────────────────────────────
log "Executing in sandbox (network blocked, filesystem restricted)..."
echo "--- SANDBOX START ---" >> "$SANDBOX_LOG"

SANDBOX_EXIT=0
timeout "$TIMEOUT" sandbox-exec \
  -f "$SANDBOX_PROFILE" \
  -D "HOME=$HOME" \
  -D "WORK_DIR=$WORK_DIR" \
  bash -c "$INSTALL_CMD" \
  >> "$SANDBOX_LOG" 2>&1 || SANDBOX_EXIT=$?

echo "--- SANDBOX END (exit: $SANDBOX_EXIT) ---" >> "$SANDBOX_LOG"

# ── Analyze results ───────────────────────────────────────────────────────────
find /tmp -maxdepth 2 2>/dev/null | sort > /tmp/after-sandbox.txt || true
NEW_FILES=$(diff /tmp/before-sandbox.txt /tmp/after-sandbox.txt 2>/dev/null | grep "^>" | sed 's/^> //' \
  | grep -v "^/tmp/sandbox-" | grep -v "before-sandbox\|after-sandbox" || echo "")

# Check for network error messages (means code TRIED to connect but was blocked)
NETWORK_ATTEMPTS=$(grep -iE "ECONNREFUSED|ETIMEDOUT|network unreachable|connection refused|getaddrinfo|DNS|curl|wget|fetch" \
  "$SANDBOX_LOG" 2>/dev/null | grep -v "^--- SANDBOX" | head -10 || echo "")

# Check for permission denied (means code tried to write somewhere blocked)
PERMISSION_DENIALS=$(grep -i "permission denied\|Operation not permitted\|EPERM\|EACCES" \
  "$SANDBOX_LOG" 2>/dev/null | grep -v "^--- SANDBOX" | head -10 || echo "")

SUSPICIOUS=false
SUSPICIOUS_REASONS=()

if [[ -n "$NETWORK_ATTEMPTS" ]]; then
  SUSPICIOUS=true
  SUSPICIOUS_REASONS+=("Attempted network connections (blocked by sandbox)")
fi

if [[ -n "$PERMISSION_DENIALS" ]]; then
  # Only flag if trying to write to sensitive paths
  if echo "$PERMISSION_DENIALS" | grep -qE "\.ssh|\.aws|Documents|Desktop|/usr/|/etc/"; then
    SUSPICIOUS=true
    SUSPICIOUS_REASONS+=("Attempted to write to restricted paths")
  fi
fi

# ── Write report ──────────────────────────────────────────────────────────────
REASONS_JSON=$(printf '%s\n' "${SUSPICIOUS_REASONS[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
NEW_FILES_JSON=$(echo "$NEW_FILES" | jq -R . | jq -s . 2>/dev/null || echo '[]')

cat > "$SANDBOX_REPORT" <<EOF
{
  "meta": {
    "repo_url": "$REPO_URL",
    "repo_name": "$REPO_NAME",
    "timestamp": "$TIMESTAMP",
    "timeout_seconds": $TIMEOUT,
    "sandbox_type": "macos-sandbox-exec",
    "exit_code": $SANDBOX_EXIT
  },
  "behavioral_analysis": {
    "suspicious": $SUSPICIOUS,
    "suspicious_reasons": $REASONS_JSON,
    "network_attempts": $(echo "$NETWORK_ATTEMPTS" | jq -Rs .),
    "permission_denials": $(echo "$PERMISSION_DENIALS" | jq -Rs .),
    "new_files_created": $NEW_FILES_JSON
  },
  "raw_log": "$SANDBOX_LOG"
}
EOF

# ── Print summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  macOS SANDBOX REPORT: $REPO_NAME${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

if $SUSPICIOUS; then
  echo -e "  Behavior:  ${RED}⚠️  SUSPICIOUS${RESET}"
  for reason in "${SUSPICIOUS_REASONS[@]}"; do
    echo -e "             → $reason"
  done
else
  echo -e "  Behavior:  ${GREEN}✅ Normal (no suspicious activity observed)${RESET}"
fi

if [[ -n "$NETWORK_ATTEMPTS" ]]; then
  echo ""
  echo -e "  ${YELLOW}Network calls attempted (all blocked):${RESET}"
  echo "$NETWORK_ATTEMPTS" | head -5 | sed 's/^/    /'
fi

if [[ -n "$NEW_FILES" ]]; then
  FILE_COUNT=$(echo "$NEW_FILES" | grep -c "." || echo 0)
  echo ""
  echo -e "  Files created in /tmp: $FILE_COUNT"
  echo "$NEW_FILES" | head -5 | sed 's/^/    /'
fi

echo ""
echo -e "  Sandbox type:  macOS sandbox-exec (built-in, no Docker needed)"
echo -e "  Exit code:     $SANDBOX_EXIT"
echo -e "  Full log:      ${CYAN}$SANDBOX_LOG${RESET}"
echo -e "  Full report:   ${CYAN}$SANDBOX_REPORT${RESET}"
echo ""
