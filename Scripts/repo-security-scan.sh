#!/usr/bin/env bash
# repo-security-scan.sh — Comprehensive repo security scanner
# Usage: bash repo-security-scan.sh <repo_url> [--output /path/to/output] [--quick] [--deep]
# Requires: git, docker (optional), trivy, semgrep, gitleaks, trufflehog, jq
# Install tools: brew install trivy gitleaks trufflehog semgrep jq

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Argument Parsing ──────────────────────────────────────────────────────────
REPO_URL="${1:-}"
OUTPUT_DIR="/tmp/security-scan-results"
QUICK_MODE=false
DEEP_MODE=false

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: $0 <repo_url_or_local_path> [--output /path] [--quick] [--deep]"
  exit 1
fi

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --quick)  QUICK_MODE=true; shift ;;
    --deep)   DEEP_MODE=true; shift ;;
    *) shift ;;
  esac
done

mkdir -p "$OUTPUT_DIR"
REPORT_JSON="$OUTPUT_DIR/security-report.json"
SCAN_LOG="$OUTPUT_DIR/scan.log"
# Clear stale outputs from previous runs so a failure can't surface old data
rm -f "$REPORT_JSON" "$OUTPUT_DIR/report.json" "$SCAN_LOG" \
      "$OUTPUT_DIR/suspicious-patterns.txt" \
      "$OUTPUT_DIR/gitleaks.json" "$OUTPUT_DIR/trufflehog.json" \
      "$OUTPUT_DIR/semgrep.json" "$OUTPUT_DIR/trivy.json" \
      "$OUTPUT_DIR/npm-audit.json" "$OUTPUT_DIR/pip-audit.json" 2>/dev/null || true

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo -e "${CYAN}[scan]${RESET} $*" | tee -a "$SCAN_LOG"; }
warn() { echo -e "${YELLOW}[warn]${RESET} $*" | tee -a "$SCAN_LOG"; }
ok()   { echo -e "${GREEN}[ok]${RESET}   $*" | tee -a "$SCAN_LOG"; }
fail() { echo -e "${RED}[fail]${RESET} $*" | tee -a "$SCAN_LOG"; }

tool_available() { command -v "$1" &>/dev/null; }

# ── Setup Temp Directory ──────────────────────────────────────────────────────
SCAN_TARGET=$(mktemp -d /tmp/repo-scan-XXXXXX)
REPO_NAME=$(basename "$REPO_URL" .git)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

trap 'log "Cleaning up temp clone..."; rm -rf "$SCAN_TARGET"' EXIT

log "Starting security scan for: $REPO_URL"
log "Output directory: $OUTPUT_DIR"
log "Timestamp: $TIMESTAMP"

# ── Initialize report structure ───────────────────────────────────────────────
FINDINGS="[]"
RISK_SCORE=0
SECRETS_GITLEAKS=0
SECRETS_TRUFFLEHOG=0
DEPS_CRITICAL=0
DEPS_HIGH=0
SAST_CRITICAL=0
SAST_HIGH=0
PATTERNS_FOUND=0

add_finding() {
  local severity="$1" title="$2" file="$3" detail="$4" score="$5"
  RISK_SCORE=$((RISK_SCORE + score))
  FINDINGS=$(echo "$FINDINGS" | jq --arg s "$severity" --arg t "$title" \
    --arg f "$file" --arg d "$detail" \
    '. += [{"severity":$s,"title":$t,"file":$f,"detail":$d}]')
}

# ── Step 1: Clone ─────────────────────────────────────────────────────────────
log "Cloning repository..."

if [[ "$REPO_URL" == /* || "$REPO_URL" == ./* || "$REPO_URL" == ~/* ]]; then
  # Local path — copy instead
  cp -r "$REPO_URL/." "$SCAN_TARGET/"
  BRANCH=$(git -C "$SCAN_TARGET" branch --show-current 2>/dev/null || echo "unknown")
  COMMIT=$(git -C "$SCAN_TARGET" rev-parse --short HEAD 2>/dev/null || echo "unknown")
else
  if $DEEP_MODE; then
    git clone --depth=0 "$REPO_URL" "$SCAN_TARGET" 2>>"$SCAN_LOG" || {
      fail "Failed to clone repository"; exit 1
    }
  else
    git clone --depth=50 "$REPO_URL" "$SCAN_TARGET" 2>>"$SCAN_LOG" || {
      fail "Failed to clone repository"; exit 1
    }
  fi
  BRANCH=$(git -C "$SCAN_TARGET" branch --show-current 2>/dev/null || echo "main")
  COMMIT=$(git -C "$SCAN_TARGET" rev-parse --short HEAD 2>/dev/null || echo "unknown")
fi

ok "Cloned: $REPO_NAME @ $BRANCH ($COMMIT)"

# ── Step 2: Detect Languages / Package Managers ───────────────────────────────
HAS_NODE=false; HAS_PYTHON=false; HAS_RUBY=false; HAS_GO=false; HAS_RUST=false

[[ -f "$SCAN_TARGET/package.json" ]] && HAS_NODE=true
[[ -f "$SCAN_TARGET/requirements.txt" || -f "$SCAN_TARGET/pyproject.toml" || -f "$SCAN_TARGET/setup.py" ]] && HAS_PYTHON=true
[[ -f "$SCAN_TARGET/Gemfile" ]] && HAS_RUBY=true
[[ -f "$SCAN_TARGET/go.mod" ]] && HAS_GO=true
[[ -f "$SCAN_TARGET/Cargo.toml" ]] && HAS_RUST=true

log "Detected: node=$HAS_NODE python=$HAS_PYTHON ruby=$HAS_RUBY go=$HAS_GO rust=$HAS_RUST"

# ── Step 3: Dangerous Install Hooks ──────────────────────────────────────────
log "Checking install hooks..."

if $HAS_NODE && [[ -f "$SCAN_TARGET/package.json" ]]; then
  HOOKS=$(jq -r '(.scripts // {}) | to_entries | .[] | select(.key | test("^(pre|post)install$|^prepare$|^prepack$")) | "\(.key): \(.value)"' "$SCAN_TARGET/package.json" 2>/dev/null || true)
  if [[ -n "$HOOKS" ]]; then
    while IFS= read -r hook; do
      warn "Install hook found: $hook"
      # Check if hook makes network calls
      if echo "$hook" | grep -qiE "curl|wget|fetch|http|socket|download"; then
        add_finding "CRITICAL" "Install hook makes network call" "package.json" "$hook" 20
      else
        add_finding "MEDIUM" "Install hook present" "package.json" "$hook" 10
      fi
    done <<< "$HOOKS"
  fi
fi

if $HAS_PYTHON && [[ -f "$SCAN_TARGET/setup.py" ]]; then
  if grep -q "cmdclass\|build_ext\|install\|develop" "$SCAN_TARGET/setup.py" 2>/dev/null; then
    SUSPICIOUS=$(grep -n "cmdclass\|subprocess\|os\.system\|exec\|eval" "$SCAN_TARGET/setup.py" 2>/dev/null | head -5 || true)
    if [[ -n "$SUSPICIOUS" ]]; then
      add_finding "HIGH" "setup.py contains command execution in install hooks" "setup.py" "$SUSPICIOUS" 15
    fi
  fi
fi

# ── Step 4: Secrets Detection — Gitleaks ─────────────────────────────────────
if tool_available gitleaks; then
  log "Running Gitleaks (current state)..."
  GITLEAKS_OUT="$OUTPUT_DIR/gitleaks.json"
  gitleaks detect \
    --source "$SCAN_TARGET" \
    --report-format json \
    --report-path "$GITLEAKS_OUT" \
    --no-git \
    2>>"$SCAN_LOG" || true

  if [[ -f "$GITLEAKS_OUT" ]]; then
    SECRETS_GITLEAKS=$(jq 'length' "$GITLEAKS_OUT" 2>/dev/null || echo 0)
    if [[ "$SECRETS_GITLEAKS" -gt 0 ]]; then
      fail "Gitleaks found $SECRETS_GITLEAKS secret(s)"
      jq -r '.[] | "  \(.RuleID) in \(.File):\(.StartLine)"' "$GITLEAKS_OUT" | head -10 | tee -a "$SCAN_LOG"
      RISK_SCORE=$((RISK_SCORE + SECRETS_GITLEAKS * 40))
    else
      ok "Gitleaks: clean"
    fi
  fi
else
  warn "gitleaks not installed — skipping (install: brew install gitleaks)"
fi

# ── Step 5: Secrets Detection — TruffleHog (git history) ─────────────────────
if ! $QUICK_MODE && tool_available trufflehog; then
  log "Running TruffleHog (git history)..."
  TRUFFLEHOG_OUT="$OUTPUT_DIR/trufflehog.json"
  trufflehog git "file://$SCAN_TARGET" \
    --json \
    --no-update \
    2>>"$SCAN_LOG" > "$TRUFFLEHOG_OUT" || true

  if [[ -f "$TRUFFLEHOG_OUT" && -s "$TRUFFLEHOG_OUT" ]]; then
    SECRETS_TRUFFLEHOG=$(grep -c '"SourceMetadata"' "$TRUFFLEHOG_OUT" 2>/dev/null || echo 0)
    if [[ "$SECRETS_TRUFFLEHOG" -gt 0 ]]; then
      fail "TruffleHog found $SECRETS_TRUFFLEHOG potential secret(s) in git history"
      RISK_SCORE=$((RISK_SCORE + SECRETS_TRUFFLEHOG * 40))
      add_finding "CRITICAL" "Secrets found in git history" "git history" \
        "TruffleHog detected $SECRETS_TRUFFLEHOG items — see $TRUFFLEHOG_OUT" 0
    else
      ok "TruffleHog: clean"
    fi
  fi
else
  [[ "$QUICK_MODE" == true ]] && log "TruffleHog: skipped (quick mode)"
  tool_available trufflehog || warn "trufflehog not installed (install: brew install trufflehog)"
fi

# ── Step 6: SAST — Semgrep ───────────────────────────────────────────────────
if tool_available semgrep; then
  log "Running Semgrep SAST..."
  SEMGREP_OUT="$OUTPUT_DIR/semgrep.json"
  semgrep scan \
    --config "p/security-audit" \
    --config "p/secrets" \
    --config "p/supply-chain" \
    --json \
    --output "$SEMGREP_OUT" \
    "$SCAN_TARGET" \
    2>>"$SCAN_LOG" || true

  if [[ -f "$SEMGREP_OUT" ]]; then
    SAST_CRITICAL=$(jq '[.results[] | select(.extra.severity == "ERROR")] | length' "$SEMGREP_OUT" 2>/dev/null || echo 0)
    SAST_HIGH=$(jq '[.results[] | select(.extra.severity == "WARNING")] | length' "$SEMGREP_OUT" 2>/dev/null || echo 0)
    TOTAL_SAST=$((SAST_CRITICAL + SAST_HIGH))
    if [[ "$TOTAL_SAST" -gt 0 ]]; then
      fail "Semgrep: $SAST_CRITICAL critical, $SAST_HIGH high findings"
      RISK_SCORE=$((RISK_SCORE + SAST_CRITICAL * 15 + SAST_HIGH * 8))
    else
      ok "Semgrep: clean"
    fi
  fi
else
  warn "semgrep not installed (install: brew install semgrep)"
fi

# ── Step 7: Dependency Audit — Trivy ─────────────────────────────────────────
if tool_available trivy; then
  log "Running Trivy dependency/filesystem scan..."
  TRIVY_OUT="$OUTPUT_DIR/trivy.json"
  trivy fs \
    --format json \
    --output "$TRIVY_OUT" \
    --scanners vuln,secret,misconfig \
    --severity CRITICAL,HIGH,MEDIUM \
    "$SCAN_TARGET" \
    2>>"$SCAN_LOG" || true

  if [[ -f "$TRIVY_OUT" ]]; then
    DEPS_CRITICAL=$(jq '[.. | objects | .Vulnerabilities? // [] | .[] | select(.Severity == "CRITICAL")] | length' "$TRIVY_OUT" 2>/dev/null || echo 0)
    DEPS_HIGH=$(jq '[.. | objects | .Vulnerabilities? // [] | .[] | select(.Severity == "HIGH")] | length' "$TRIVY_OUT" 2>/dev/null || echo 0)
    if [[ "$((DEPS_CRITICAL + DEPS_HIGH))" -gt 0 ]]; then
      fail "Trivy: $DEPS_CRITICAL critical CVEs, $DEPS_HIGH high CVEs in dependencies"
      RISK_SCORE=$((RISK_SCORE + DEPS_CRITICAL * 15 + DEPS_HIGH * 8))
    else
      ok "Trivy: no critical/high CVEs"
    fi
  fi
else
  warn "trivy not installed (install: brew install trivy)"
fi

# ── Step 8: Package-Manager Native Audits ────────────────────────────────────
if $HAS_NODE && tool_available npm; then
  log "Running npm audit..."
  NPM_OUT="$OUTPUT_DIR/npm-audit.json"
  (cd "$SCAN_TARGET" && npm audit --json 2>/dev/null > "$NPM_OUT") || true
  if [[ -f "$NPM_OUT" ]]; then
    NPM_CRIT=$(jq '.metadata.vulnerabilities.critical // 0' "$NPM_OUT" 2>/dev/null || echo 0)
    NPM_HIGH=$(jq '.metadata.vulnerabilities.high // 0' "$NPM_OUT" 2>/dev/null || echo 0)
    [[ "$NPM_CRIT" -gt 0 ]] && { fail "npm audit: $NPM_CRIT critical"; RISK_SCORE=$((RISK_SCORE + NPM_CRIT * 15)); }
    [[ "$NPM_HIGH" -gt 0 ]] && { warn "npm audit: $NPM_HIGH high"; RISK_SCORE=$((RISK_SCORE + NPM_HIGH * 8)); }
    [[ "$NPM_CRIT" -eq 0 && "$NPM_HIGH" -eq 0 ]] && ok "npm audit: clean"
  fi
fi

if $HAS_PYTHON && tool_available pip-audit; then
  log "Running pip-audit..."
  PIP_OUT="$OUTPUT_DIR/pip-audit.json"
  pip-audit --path "$SCAN_TARGET" --format json -o "$PIP_OUT" 2>>"$SCAN_LOG" || true
fi

# ── Step 9: Custom Malware Pattern Scan ──────────────────────────────────────
# Patterns are tight to avoid false positives. The strong signal is the COMBO,
# not the lone keyword — we require malware shape, not just suspicious words.
log "Scanning for suspicious code patterns..."

# Single quotes so `\` stays literal — bash doesn't pre-process the regex.
# `|` is grep -E alternation. `\|` would be a LITERAL pipe (NOT what we want).
PATTERNS_LABELS=(
  "Reverse shell / C2 callback"
  "Obfuscated code (chained eval/atob)"
  "Crypto miner signatures"
  "Clipboard hijacker (wallet swap)"
  "SSH key exfiltration"
  "Hardcoded cloud credentials"
  "DNS tunneling"
)
PATTERNS=(
  'bash -i[[:space:]]+[^"]*>&[^"]*[[:space:]]0>&1|nc -e[[:space:]]+/bin/(ba)?sh|/dev/tcp/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+|python[[:space:]]+-c[[:space:]]+["'\''][^"'\'']*socket\.socket[^"'\'']*connect|perl[[:space:]]+-e[[:space:]]+["'\''][^"'\'']*Socket[^"'\'']*connect'
  'eval[[:space:]]*\([[:space:]]*base64_decode[[:space:]]*\(|eval[[:space:]]*\([[:space:]]*atob[[:space:]]*\(|String\.fromCharCode\([[:space:]]*[0-9]+([[:space:]]*,[[:space:]]*[0-9]+){9,}'
  'stratum\+(tcp|ssl)://|pool\.minexmr|pool\.supportxmr|xmrig[[:space:]]+--|cryptonight[_-]|coinhive\.com'
  '(pyperclip\.(copy|paste)|navigator\.clipboard|pbcopy|xclip)[^\n]*(0x[a-fA-F0-9]{40}|walletAddress|btcAddress|ethAddress|bitcoin_address)'
  '(cat|tar|cp|scp|base64)[[:space:]]+[^|]*\.ssh/(id_(rsa|dsa|ecdsa|ed25519)|authorized_keys)|StrictHostKeyChecking=no[[:space:]]+[^|]*[A-Za-z0-9.-]+@[A-Za-z0-9.-]+'
  'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|sk_live_[0-9a-zA-Z]{24,}|xox[bp]-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{24}'
  'socket\.gethostbyname\([^)]*\.(encode|decode)\(|dnspython[^\n]*resolve[^\n]*\.encode\(|nslookup[[:space:]]+\$\([^)]*encode'
)

PATTERN_FINDINGS=""
SELF_BASENAME=$(basename "${BASH_SOURCE[0]}")

for i in "${!PATTERNS[@]}"; do
  PATTERN="${PATTERNS[$i]}"
  LABEL="${PATTERNS_LABELS[$i]}"
  MATCHES=$(grep -rEn "$PATTERN" "$SCAN_TARGET" \
    --include="*.py" --include="*.js" --include="*.ts" --include="*.mjs" --include="*.cjs" \
    --include="*.sh" --include="*.bash" --include="*.zsh" \
    --include="*.rb" --include="*.php" --include="*.pl" \
    --exclude-dir=".git" \
    --exclude-dir="node_modules" \
    --exclude-dir=".venv" --exclude-dir="venv" --exclude-dir="env" \
    --exclude-dir="__pycache__" --exclude-dir=".pytest_cache" \
    --exclude-dir=".next" --exclude-dir="dist" --exclude-dir="build" --exclude-dir=".cache" \
    --exclude-dir="vendor" --exclude-dir="target" \
    --exclude="$SELF_BASENAME" \
    --exclude="repo-security-scan.sh" --exclude="install-security-tools.sh" \
    2>/dev/null | head -5 || true)
  if [[ -n "$MATCHES" ]]; then
    PATTERN_FINDINGS+="[$LABEL]"$'\n'"$MATCHES"$'\n\n'
    PATTERNS_FOUND=$((PATTERNS_FOUND + 1))
    RISK_SCORE=$((RISK_SCORE + 30))
    fail "Suspicious pattern: $LABEL"
    echo "$MATCHES" | head -3 | tee -a "$SCAN_LOG"
    add_finding "HIGH" "$LABEL" "see suspicious-patterns.txt" \
      "$(echo "$MATCHES" | head -1)" 0
  fi
done

if [[ -n "$PATTERN_FINDINGS" ]]; then
  echo "$PATTERN_FINDINGS" > "$OUTPUT_DIR/suspicious-patterns.txt"
fi

# ── Step 10: Binary / Unusual File Detection ─────────────────────────────────
# Only match actual compiled binaries — ELF / Mach-O / PE32 / DOS executables.
# Do NOT match text scripts that `file` describes as "executable" (Python, Ruby,
# Perl shebang scripts), or static assets like images and fonts.
log "Checking for embedded binaries and unusual files..."

BINARIES=$(find "$SCAN_TARGET" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  -not -path "*/.venv/*" -not -path "*/venv/*" -not -path "*/env/*" \
  -not -path "*/__pycache__/*" -not -path "*/.pytest_cache/*" \
  -not -path "*/.next/*" -not -path "*/dist/*" -not -path "*/build/*" -not -path "*/.cache/*" \
  -not -path "*/vendor/*" -not -path "*/target/*" \
  -not -name "*.png" -not -name "*.jpg" -not -name "*.jpeg" -not -name "*.gif" \
  -not -name "*.ico" -not -name "*.svg" -not -name "*.webp" -not -name "*.avif" \
  -not -name "*.woff" -not -name "*.woff2" -not -name "*.ttf" -not -name "*.eot" -not -name "*.otf" \
  -not -name "*.pdf" -not -name "*.mp4" -not -name "*.mp3" -not -name "*.zip" -not -name "*.gz" \
  -not -name "*.pyc" -not -name "*.pyo" \
  -type f -exec file {} \; 2>/dev/null \
  | grep -E ": (ELF |Mach-O |PE32|MS Windows executable|DOS executable|MS-DOS executable)" \
  | head -10 || true)

if [[ -n "$BINARIES" ]]; then
  fail "Embedded compiled binaries found:"
  echo "$BINARIES" | tee -a "$SCAN_LOG"
  BINARY_COUNT=$(echo "$BINARIES" | wc -l | tr -d ' ')
  add_finding "HIGH" "Embedded compiled binaries" "repository" \
    "$BINARY_COUNT compiled binary files found outside expected asset locations" 20
  RISK_SCORE=$((RISK_SCORE + BINARY_COUNT * 20))
fi

# ── Step 11: .env / Secret File Check ────────────────────────────────────────
# Skip example/sample/template files — those are documentation, not secrets.
# Skip public keys (*.pub). For .env, only flag forms that are not clearly example files.
log "Checking for committed secret files..."

SECRET_FILES=$(find "$SCAN_TARGET" \
  -not -path "*/.git/*" \
  -not -path "*/node_modules/*" \
  -not -path "*/.venv/*" -not -path "*/venv/*" \
  -not -path "*/__pycache__/*" \
  \( \
    -name ".env" -o -name ".env.local" -o -name ".env.production" \
    -o -name ".env.staging" -o -name ".env.development" -o -name ".env.prod" \
    -o -name "id_rsa" -o -name "id_dsa" -o -name "id_ecdsa" -o -name "id_ed25519" \
    -o -name "*.pem" -o -name "*.pfx" -o -name "*.p12" -o -name "*.jks" \
    -o -name "credentials.json" -o -name "service-account*.json" \
    -o -name "secrets.yaml" -o -name "secrets.yml" \
  \) \
  ! -name "*.example" ! -name "*.sample" ! -name "*.template" ! -name "*.tmpl" \
  ! -name "*.pub" \
  2>/dev/null | head -10 || true)

if [[ -n "$SECRET_FILES" ]]; then
  while IFS= read -r f; do
    # Only flag a .pem/.key file as CRITICAL if it actually looks like a private key.
    if [[ "$f" == *.pem || "$f" == *.key ]]; then
      if head -3 "$f" 2>/dev/null | grep -qE "BEGIN (RSA |EC |DSA |OPENSSH |ENCRYPTED |)PRIVATE KEY"; then
        fail "Secret file committed: $f"
        add_finding "CRITICAL" "Private key in repository" "$f" \
          "File starts with PRIVATE KEY header" 40
      fi
    else
      fail "Secret file committed: $f"
      add_finding "CRITICAL" "Secret file in repository" "$f" \
        "Likely contains credentials" 40
    fi
  done <<< "$SECRET_FILES"
fi

# ── Step 12: Compute Verdict ──────────────────────────────────────────────────
# Thresholds match the frontend's scoreToVerdict() so a score from either side
# maps to the same label. Labels: CLEAN / CARE / QUARANTINE / REJECT.
if   [[ "$RISK_SCORE" -ge 61 ]]; then VERDICT="REJECT"
elif [[ "$RISK_SCORE" -ge 31 ]]; then VERDICT="QUARANTINE"
elif [[ "$RISK_SCORE" -ge 16 ]]; then VERDICT="CARE"
else                                   VERDICT="CLEAN"
fi

# ── Step 13: Write JSON Report ────────────────────────────────────────────────
cat > "$REPORT_JSON" <<EOF
{
  "meta": {
    "repo_url": "$REPO_URL",
    "repo_name": "$REPO_NAME",
    "branch": "$BRANCH",
    "commit": "$COMMIT",
    "timestamp": "$TIMESTAMP",
    "quick_mode": $QUICK_MODE,
    "deep_mode": $DEEP_MODE
  },
  "verdict": "$VERDICT",
  "risk_score": $RISK_SCORE,
  "summary": {
    "secrets_gitleaks": $SECRETS_GITLEAKS,
    "secrets_trufflehog": $SECRETS_TRUFFLEHOG,
    "sast_critical": $SAST_CRITICAL,
    "sast_high": $SAST_HIGH,
    "deps_critical": $DEPS_CRITICAL,
    "deps_high": $DEPS_HIGH,
    "suspicious_patterns": $PATTERNS_FOUND
  },
  "findings": $FINDINGS,
  "scan_log": "$SCAN_LOG",
  "tool_outputs": {
    "gitleaks": "$OUTPUT_DIR/gitleaks.json",
    "trufflehog": "$OUTPUT_DIR/trufflehog.json",
    "semgrep": "$OUTPUT_DIR/semgrep.json",
    "trivy": "$OUTPUT_DIR/trivy.json",
    "npm_audit": "$OUTPUT_DIR/npm-audit.json",
    "suspicious_patterns": "$OUTPUT_DIR/suspicious-patterns.txt"
  }
}
EOF

# ── Final Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  SCAN COMPLETE: $REPO_NAME${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

case "$VERDICT" in
  "CLEAN")      echo -e "  Verdict:     ${GREEN}✅ CLEAN — Safe to Use${RESET}" ;;
  "CARE")       echo -e "  Verdict:     ${YELLOW}⚠️  USE WITH CARE${RESET}" ;;
  "QUARANTINE") echo -e "  Verdict:     ${YELLOW}🔶 DO NOT RUN YET${RESET}" ;;
  "REJECT")     echo -e "  Verdict:     ${RED}❌ DO NOT INSTALL${RESET}" ;;
esac

echo -e "  Risk Score:  ${BOLD}$RISK_SCORE / 100${RESET}"
echo ""
echo -e "  Secrets:     Gitleaks: $SECRETS_GITLEAKS | TruffleHog: $SECRETS_TRUFFLEHOG"
echo -e "  SAST:        Critical: $SAST_CRITICAL | High: $SAST_HIGH"
echo -e "  Deps:        Critical CVEs: $DEPS_CRITICAL | High: $DEPS_HIGH"
echo -e "  Patterns:    $PATTERNS_FOUND suspicious pattern(s) found"
echo ""
echo -e "  Full report: ${CYAN}$REPORT_JSON${RESET}"
echo ""
