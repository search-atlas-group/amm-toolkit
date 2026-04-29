#!/usr/bin/env bash
# repo-sandbox.sh — Run a repo in an isolated Docker container and observe behavior
# Usage: bash repo-sandbox.sh <repo_url> [--timeout 60] [--network none|monitor]
# Requires: docker

set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

REPO_URL="${1:-}"
TIMEOUT=120
NETWORK_MODE="none"
OUTPUT_DIR="/tmp/sandbox-results"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: $0 <repo_url> [--timeout N] [--network none|monitor]"
  exit 1
fi

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout)  TIMEOUT="$2"; shift 2 ;;
    --network)  NETWORK_MODE="$2"; shift 2 ;;
    --output)   OUTPUT_DIR="$2"; shift 2 ;;
    *) shift ;;
  esac
done

mkdir -p "$OUTPUT_DIR"
CONTAINER_NAME="security-sandbox-$(date +%s)"
REPO_NAME=$(basename "$REPO_URL" .git)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log()  { echo -e "${CYAN}[sandbox]${RESET} $*"; }
warn() { echo -e "${YELLOW}[sandbox]${RESET} $*"; }
ok()   { echo -e "${GREEN}[sandbox]${RESET} $*"; }
fail() { echo -e "${RED}[sandbox]${RESET} $*"; }

# ── Preflight ─────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  fail "Docker is not installed. Install from https://docs.docker.com/desktop/mac/"
  exit 1
fi

if ! docker info &>/dev/null; then
  fail "Docker daemon is not running. Start Docker Desktop first."
  exit 1
fi

ok "Docker available"

# ── Build Scanner Image ───────────────────────────────────────────────────────
DOCKERFILE_PATH="$(dirname "$0")/Dockerfile.scanner"

if [[ ! -f "$DOCKERFILE_PATH" ]]; then
  fail "Dockerfile.scanner not found at $DOCKERFILE_PATH"
  exit 1
fi

log "Building scanner image (this takes ~60s on first run, cached after)..."
docker build \
  --quiet \
  --tag "repo-scanner:latest" \
  --file "$DOCKERFILE_PATH" \
  "$(dirname "$0")" 2>&1 | tail -3

ok "Scanner image ready"

# ── Network Monitor Container (optional) ─────────────────────────────────────
NETWORK_ARG="--network none"
NET_CONTAINER=""

if [[ "$NETWORK_MODE" == "monitor" ]]; then
  log "Starting network monitor sidecar..."
  # Create a bridge network for monitored access
  docker network create sandbox-net 2>/dev/null || true

  # Run tcpdump sidecar
  NET_CONTAINER="sandbox-net-monitor-$(date +%s)"
  docker run -d \
    --name "$NET_CONTAINER" \
    --network sandbox-net \
    --cap-add NET_ADMIN \
    alpine sh -c "apk add -q tcpdump && tcpdump -i any -nn -q 2>/dev/null" \
    > /dev/null

  NETWORK_ARG="--network sandbox-net"
  warn "Network monitoring active — all outbound connections will be captured"
fi

# ── Run Sandbox Container ─────────────────────────────────────────────────────
log "Launching sandbox: $CONTAINER_NAME"
log "Repo: $REPO_URL"
log "Timeout: ${TIMEOUT}s"
log "Network: $NETWORK_MODE"
echo ""

SANDBOX_OUTPUT="$OUTPUT_DIR/sandbox-output.txt"
SANDBOX_REPORT="$OUTPUT_DIR/sandbox-report.json"

# The sandbox runs:
# 1. Clone the repo
# 2. Detect package manager
# 3. Run install (the most dangerous step)
# 4. Capture all activity
docker run \
  --rm \
  --name "$CONTAINER_NAME" \
  --read-only \
  --tmpfs /tmp:rw,size=256m \
  --tmpfs /home/scanner:rw,size=256m \
  --memory="512m" \
  --memory-swap="512m" \
  --cpus="0.5" \
  --pids-limit 100 \
  --security-opt no-new-privileges \
  --security-opt seccomp=/dev/null \
  --cap-drop ALL \
  $NETWORK_ARG \
  --env REPO_URL="$REPO_URL" \
  --env TIMEOUT="$TIMEOUT" \
  repo-scanner:latest \
  /usr/local/bin/run-sandbox.sh \
  2>&1 | tee "$SANDBOX_OUTPUT" || SANDBOX_EXIT=$?

SANDBOX_EXIT="${SANDBOX_EXIT:-0}"

# ── Collect Network Logs ──────────────────────────────────────────────────────
NETWORK_LOG=""
if [[ -n "$NET_CONTAINER" ]]; then
  log "Collecting network capture..."
  NETWORK_LOG=$(docker logs "$NET_CONTAINER" 2>&1 | grep -v "^$" | head -50 || echo "no network activity")
  docker stop "$NET_CONTAINER" >/dev/null 2>&1 || true
  docker network rm sandbox-net >/dev/null 2>&1 || true
fi

# ── Parse Sandbox Output ──────────────────────────────────────────────────────
# Extract key behavioral signals from captured output
FILES_CREATED=$(grep "FILE_WRITE:" "$SANDBOX_OUTPUT" 2>/dev/null | sed 's/FILE_WRITE://' | head -20 || echo "none")
PROCESSES_SPAWNED=$(grep "PROCESS:" "$SANDBOX_OUTPUT" 2>/dev/null | sed 's/PROCESS://' | head -20 || echo "none")
NETWORK_CALLS=$(grep "NETWORK:" "$SANDBOX_OUTPUT" 2>/dev/null | sed 's/NETWORK://' | head -20 || echo "none")
INSTALL_ERRORS=$(grep -i "error\|failed\|denied" "$SANDBOX_OUTPUT" 2>/dev/null | head -10 || echo "none")

# Detect suspicious behavior in output
SUSPICIOUS=false
SUSPICIOUS_REASONS=""

if echo "$SANDBOX_OUTPUT" | grep -qiE "curl|wget|http|socket|connect"; then
  if [[ "$NETWORK_MODE" == "none" ]]; then
    SUSPICIOUS=true
    SUSPICIOUS_REASONS+="Attempted network calls despite --network none. "
  fi
fi

if echo "$FILES_CREATED" | grep -qE "\.ssh|id_rsa|authorized_keys|/etc/|cron"; then
  SUSPICIOUS=true
  SUSPICIOUS_REASONS+="Attempted to write to sensitive file paths. "
fi

if echo "$PROCESSES_SPAWNED" | grep -qE "bash -i|nc |ncat|python -c|perl -e"; then
  SUSPICIOUS=true
  SUSPICIOUS_REASONS+="Spawned suspicious processes. "
fi

# ── Write Report ──────────────────────────────────────────────────────────────
cat > "$SANDBOX_REPORT" <<EOF
{
  "meta": {
    "repo_url": "$REPO_URL",
    "repo_name": "$REPO_NAME",
    "timestamp": "$TIMESTAMP",
    "timeout_seconds": $TIMEOUT,
    "network_mode": "$NETWORK_MODE",
    "exit_code": $SANDBOX_EXIT
  },
  "behavioral_analysis": {
    "suspicious": $SUSPICIOUS,
    "suspicious_reasons": "$SUSPICIOUS_REASONS",
    "files_created": $(echo "$FILES_CREATED" | jq -Rs .),
    "processes_spawned": $(echo "$PROCESSES_SPAWNED" | jq -Rs .),
    "network_calls": $(echo "$NETWORK_CALLS" | jq -Rs .),
    "network_capture": $(echo "$NETWORK_LOG" | jq -Rs .),
    "install_errors": $(echo "$INSTALL_ERRORS" | jq -Rs .)
  },
  "raw_output": "$SANDBOX_OUTPUT"
}
EOF

# ── Print Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  SANDBOX REPORT: $REPO_NAME${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

if $SUSPICIOUS; then
  echo -e "  Behavior:    ${RED}⚠️  SUSPICIOUS — $SUSPICIOUS_REASONS${RESET}"
else
  echo -e "  Behavior:    ${GREEN}✅ Normal${RESET}"
fi

echo -e "  Network:     $NETWORK_MODE"
echo -e "  Exit code:   $SANDBOX_EXIT"
echo ""
echo -e "  Files written:    $(echo "$FILES_CREATED" | grep -c '^' 2>/dev/null || echo 0) paths"
echo -e "  Processes:        $(echo "$PROCESSES_SPAWNED" | grep -c '^' 2>/dev/null || echo 0) spawned"
echo ""
echo -e "  Full report: ${CYAN}$SANDBOX_REPORT${RESET}"
echo ""
