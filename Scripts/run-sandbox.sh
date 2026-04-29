#!/usr/bin/env bash
# run-sandbox.sh — Executes inside the Docker container to install and observe a repo
# Outputs structured behavioral signals prefixed with FILE_WRITE:, PROCESS:, NETWORK:

set -uo pipefail

REPO_URL="${REPO_URL:-}"
TIMEOUT="${TIMEOUT:-120}"

if [[ -z "$REPO_URL" ]]; then
  echo "ERROR: REPO_URL not set"
  exit 1
fi

REPO_NAME=$(basename "$REPO_URL" .git)
WORK_DIR="/tmp/sandbox-target"
mkdir -p "$WORK_DIR"

log_event() { echo "[$(date -u +%H:%M:%S)] $*"; }

log_event "=== SANDBOX START ==="
log_event "Repo: $REPO_URL"
log_event "Timeout: ${TIMEOUT}s"
log_event "User: $(whoami)"
log_event "Network: $(cat /proc/net/dev 2>/dev/null | head -3 || echo 'none')"

# ── Clone ─────────────────────────────────────────────────────────────────────
log_event "=== CLONING ==="
timeout "$TIMEOUT" git clone --depth=1 "$REPO_URL" "$WORK_DIR" 2>&1 || {
  log_event "CLONE FAILED or timed out"
  exit 1
}

log_event "Clone complete. Contents:"
find "$WORK_DIR" -maxdepth 2 -not -path "*/.git/*" | head -40

# ── Language Detection ────────────────────────────────────────────────────────
cd "$WORK_DIR"

log_event "=== INSTALL PHASE ==="

# Monitor file system changes by recording pre-install state
find /tmp /home/scanner -maxdepth 3 2>/dev/null > /tmp/before-install.txt || true

# ── Node.js ───────────────────────────────────────────────────────────────────
if [[ -f "package.json" ]]; then
  log_event "Detected: Node.js project"
  log_event "package.json scripts:"
  jq '.scripts // {}' package.json 2>/dev/null || true

  log_event "Running: npm install (dry-run first)"
  timeout 30 npm install --dry-run 2>&1 | head -30 || true

  log_event "Running: npm install"
  timeout 60 npm install --ignore-scripts 2>&1 | tail -20 || {
    log_event "npm install failed or timed out"
  }

  # Now try WITH scripts to observe behavior
  log_event "Running: npm install WITH scripts (behavioral observation)"
  timeout 30 npm install 2>&1 | tail -20 || {
    log_event "npm install (with scripts) failed or timed out"
  }
fi

# ── Python ────────────────────────────────────────────────────────────────────
if [[ -f "requirements.txt" || -f "setup.py" || -f "pyproject.toml" ]]; then
  log_event "Detected: Python project"
  python3 -m venv /tmp/venv 2>/dev/null || true
  source /tmp/venv/bin/activate 2>/dev/null || true

  if [[ -f "requirements.txt" ]]; then
    timeout 60 pip install -r requirements.txt --quiet 2>&1 | tail -10 || true
  fi

  if [[ -f "setup.py" ]]; then
    log_event "setup.py detected — observing install"
    timeout 60 python3 setup.py install --dry-run 2>&1 | head -30 || true
  fi
fi

# ── Post-install filesystem diff ──────────────────────────────────────────────
log_event "=== FILE SYSTEM DIFF ==="
find /tmp /home/scanner -maxdepth 3 2>/dev/null > /tmp/after-install.txt || true
NEW_FILES=$(diff /tmp/before-install.txt /tmp/after-install.txt 2>/dev/null | grep "^>" | sed 's/^> //' || true)

if [[ -n "$NEW_FILES" ]]; then
  while IFS= read -r f; do
    echo "FILE_WRITE:$f"
  done <<< "$NEW_FILES"
else
  log_event "No unexpected file writes detected"
fi

# ── Network probes ────────────────────────────────────────────────────────────
log_event "=== NETWORK ACTIVITY CHECK ==="
# In --network none mode, any connection attempt will error immediately
# We try common exfil targets to see if the code tries to reach them
for HOST in "169.254.169.254" "metadata.google.internal" "checkip.amazonaws.com"; do
  RESULT=$(timeout 2 curl -s --max-time 1 "http://$HOST" 2>&1 | head -1 || echo "blocked/timeout")
  echo "NETWORK:$HOST → $RESULT"
done

# ── Process list ──────────────────────────────────────────────────────────────
log_event "=== RUNNING PROCESSES ==="
ps aux 2>/dev/null | grep -v "^\(scanner\|root\)" | tail -20 | while IFS= read -r line; do
  echo "PROCESS:$line"
done

log_event "=== SANDBOX END ==="
