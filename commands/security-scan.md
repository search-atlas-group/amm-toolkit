# /security-scan

Scan any Git repository for security risks before running it on your machine.

Works immediately — even if you have zero tools installed. Gets more thorough as better tools become available. Always produces a plain-English verdict.

---

## Instructions

### Step 0: Greet and Parse Input

If the user ran `/security-scan` with no argument, respond:

> Paste the GitHub (or GitLab, Bitbucket) URL of the repo you want to scan.
> Example: `https://github.com/owner/repo-name`
>
> You can also pass a short form: `owner/repo`
> Or a folder already on your computer: `/Users/you/Downloads/some-folder`

Once you have a URL or path, extract `{repo_url}`, `{repo_owner}`, `{repo_name}`.

Then say (in plain English, no jargon):
> I'm going to check this repo for anything dangerous before you run it.
> This works in layers — I'll start right now and add more thorough checks as we go.

---

### Step 1: Detect What Tools Are Available

Run this silently:
```bash
TIER=0
command -v git    &>/dev/null && TIER=1
command -v trivy  &>/dev/null && command -v gitleaks &>/dev/null && TIER=2
command -v docker &>/dev/null && docker info &>/dev/null 2>&1 && TIER=3
echo "SCAN_TIER=$TIER"
```

Tell the user their current tier in a single friendly line:

| Tier | Message |
|------|---------|
| 0 | "Starting with AI-only analysis — no extra tools needed. I'll read the code directly." |
| 1 | "Basic scanning available. For deeper checks, I can install a few free security tools." |
| 2 | "Full security scan available (CVE database, secret detection, code analysis)." |
| 3 | "Full scan + isolated sandbox available. Best possible coverage." |

If Tier is 0 or 1, ask:
> Want me to install the free security tools now? It takes about 2 minutes and makes this scan much more thorough. (They won't interfere with anything on your computer.)
>
> Type **yes** to install, or **skip** to continue with what we have.

If yes → run Step 1b. If skip → continue with current tier.

---

### Step 1b: Auto-Install Security Tools (if user agrees)

Explain what you're doing before each step:

```
Installing security tools...

Step 1/3 — Homebrew (the app store for developer tools)
```
```bash
if ! command -v brew &>/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
```

```
Step 2/3 — Security scanners (trivy, gitleaks, semgrep, trufflehog)
```
```bash
brew install trivy gitleaks trufflehog semgrep jq 2>&1 | grep -E "Installing|✓|Error" | head -20
```

```
Step 3/3 — Python security tools
```
```bash
pip3 install --quiet bandit pip-audit 2>/dev/null || true
```

After install, re-run the tier detection and confirm:
> Done! Security tools installed. Running a full scan now.

---

### Step 2: Surface Check (Always runs — no tools needed)

Before cloning anything, look at the repo's public information from GitHub.

```bash
# Get metadata — works for any public GitHub repo
curl -s "https://api.github.com/repos/{repo_owner}/{repo_name}" 2>/dev/null | jq '{
  created_days_ago: (((now - (.created_at | fromdateiso8601)) / 86400) | floor),
  stars: .stargazers_count,
  forks: .forks_count,
  size_kb: .size,
  language: .language,
  pushed_at: .pushed_at,
  open_issues: .open_issues_count,
  archived: .archived
}' 2>/dev/null || echo "Private repo or GitHub API unavailable — skipping metadata"
```

**Red flags to flag for the user in plain English:**
- Created less than 7 days ago with 0 stars → "This repo is brand new with no community. Be cautious."
- Size over 100MB for a typical library → "Unusually large. Could contain hidden files."
- Archived but still being shared → "This project is officially abandoned."

Then fetch and scan dangerous files using the GitHub API (no clone needed):
```bash
# Check package.json for dangerous install hooks
curl -s "https://api.github.com/repos/{repo_owner}/{repo_name}/contents/package.json" \
  | jq -r '.content' | base64 -d 2>/dev/null \
  | jq -r '(.scripts // {}) | to_entries[] | select(.key | test("install|prepare|prepack")) | "\(.key): \(.value)"' 2>/dev/null

# Check for .env files committed (should never be there)
curl -s "https://api.github.com/repos/{repo_owner}/{repo_name}/contents/.env" \
  | jq -r '.name' 2>/dev/null | grep -q "\.env" && echo "WARNING: .env file is committed to this repo"

# List CI workflow files
curl -s "https://api.github.com/repos/{repo_owner}/{repo_name}/contents/.github/workflows" \
  | jq -r '.[].name' 2>/dev/null | head -10
```

Narrate every finding in plain English. Examples:
- "The install script runs a network command. This means the moment you install it, it contacts a remote server. That could be fine (like downloading a file) or dangerous (sending your data somewhere)."
- "Found a .env file in the repository. This file often contains passwords and API keys. Whoever published this may have accidentally leaked their credentials."
- "No install hooks found. The code doesn't try to run anything automatically when you install it. Good."

---

### Step 3: Clone and Static Scan

#### If Tier 0 (AI only):

Clone to a temporary directory and read the code directly:
```bash
mkdir -p /tmp/security-scan-ai
git clone --depth=1 "{repo_url}" /tmp/security-scan-ai/{repo_name} 2>&1 | tail -3
```

Then use Read and Bash tools to inspect the code yourself. Look for:

**Pattern 1 — Reverse shells and remote control:**
```bash
grep -rn "bash -i\|/dev/tcp/\|nc -e\|ncat\|mkfifo" /tmp/security-scan-ai/{repo_name} \
  --include="*.sh" --include="*.py" --include="*.js" --exclude-dir=".git" 2>/dev/null | head -10
```
Plain English: "Checking for code that would give a remote hacker control of your computer..."

**Pattern 2 — Obfuscated/hidden code:**
```bash
grep -rn "eval(base64\|eval(atob\|fromCharCode\|\\\\x[0-9a-fA-F]\\{2\\}\\{8,\\}" \
  /tmp/security-scan-ai/{repo_name} --include="*.js" --include="*.py" --exclude-dir=".git" --exclude-dir="node_modules" 2>/dev/null | head -10
```
Plain English: "Checking for code that's been scrambled to hide what it does..."

**Pattern 3 — Crypto miners:**
```bash
grep -rni "stratum+tcp\|coinhive\|xmrig\|cryptonight\|monero" \
  /tmp/security-scan-ai/{repo_name} --exclude-dir=".git" 2>/dev/null | head -5
```
Plain English: "Checking if this secretly uses your computer to mine cryptocurrency..."

**Pattern 4 — Credential theft:**
```bash
grep -rn "\.ssh/id_rsa\|os\.environ.*http\|clipboard\|pyperclip" \
  /tmp/security-scan-ai/{repo_name} --include="*.py" --include="*.js" --exclude-dir=".git" 2>/dev/null | head -10
```
Plain English: "Checking for code that reads your saved passwords or SSH keys..."

**Pattern 5 — Embedded executables:**
```bash
find /tmp/security-scan-ai/{repo_name} -not -path "*/.git/*" -type f \
  \( -name "*.exe" -o -name "*.dll" -o -name "*.so" -o -name "*.dylib" \) 2>/dev/null | head -10
file /tmp/security-scan-ai/{repo_name}/**/* 2>/dev/null | grep -i "ELF\|Mach-O\|PE32" | grep -v ".git" | head -10
```
Plain English: "Checking for hidden programs disguised as text files..."

After running all patterns, use your own judgment to read 3–5 flagged files and confirm whether findings are real or false positives.

#### If Tier 2+ (automated tools available):

Run the scanner script:
```bash
AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
bash "$AMM_ROOT/scripts/repo-security-scan.sh" "{repo_url}" \
  --output /tmp/security-scan-results/
```

Read `/tmp/security-scan-results/report.json` and narrate each finding in plain English.

---

### Step 4: Sandbox Test (Optional — for MEDIUM risk and above)

#### If Docker is available (Tier 3):
```bash
AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
bash "$AMM_ROOT/scripts/repo-sandbox.sh" "{repo_url}" \
  --timeout 90 --network none
```

Plain English explanation to offer user:
> This will put the code in a sealed-off bubble on your computer — like a quarantine room — and watch what it tries to do when it runs. The bubble has no internet access and can't touch your real files. After 90 seconds, the bubble is deleted.

#### If Docker is NOT available (macOS native sandbox):
```bash
AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
bash "$AMM_ROOT/scripts/mac-sandbox-run.sh" "{repo_url}"
```

Plain English explanation:
> Your Mac has a built-in security feature that can run code in a locked-down zone with no internet access. I'll use that instead of Docker. No installation needed.

After sandbox runs, narrate what you saw:
- "The code tried to contact 3 external servers. In an isolated test with no internet, it gave up and kept running normally."
- "No unexpected behavior. The code installed cleanly and didn't try to do anything unusual."
- "The code immediately tried to write a file to a path outside its folder. This is suspicious."

---

### Step 5: Risk Score and Verdict

Compute a plain-English risk score. DO NOT use jargon. Explain each point deducted.

Show a summary table like this — adapt the findings, don't show empty rows:

```
What I checked                           Result
──────────────────────────────────────────────────────────
Repo age and reputation                  ✅  Established (3 years, 12k stars)
Dangerous install hooks                  ✅  None found
Passwords or keys in the code            ✅  Clean
Malicious code patterns                  ⚠️  1 suspicious eval() — likely minified JS
Known security vulnerabilities           ⚠️  2 outdated dependencies (not critical)
Hidden programs                          ✅  None
Sandbox behavior                         ✅  Normal (no network calls, no file writes)
──────────────────────────────────────────────────────────
Overall risk score                       18 / 100
```

**Verdict:**
- 0–15:  **SAFE TO USE** — No significant issues found.
- 16–30: **USE WITH CARE** — Minor concerns. Read the details below before installing.
- 31–60: **DO NOT RUN YET** — Real concerns found. Get a second opinion from your team.
- 61+:   **DO NOT INSTALL** — Active threat. Delete and report.

State the verdict in a single large, clear sentence:

> **This repo appears safe to use.** One minor concern (outdated dependency) is worth noting, but it doesn't affect your security. Safe to install.

or:

> **Do not install this repo on your computer.** It contains code that attempts to contact a remote server during installation. This is a red flag that needs investigation before you proceed.

---

### Step 6: What To Do Next

Always end with a concrete action list:

**If SAFE TO USE:**
```
What to do:
  ✅  You can clone and install this repo normally.
  ✅  Keep dependencies updated (run: npm update / pip install --upgrade)
  □   If something feels off later, run /security-scan again on the folder.
```

**If USE WITH CARE:**
```
What to do:
  □   Read the specific concerns above before installing.
  □   If you're unsure, share this report with your tech team.
  □   You can install it, but update the flagged dependencies first.
```

**If DO NOT RUN YET:**
```
What to do:
  □   Do NOT install this yet.
  □   Share this report with your team or a developer you trust.
  □   Consider reporting the issue to the repo's maintainer.
  □   If you need to test it urgently, ask me to run it in a sandbox.
```

**If DO NOT INSTALL:**
```
What to do:
  □   Delete any copy of this repo on your computer immediately.
  □   If you already ran it: change any passwords you used recently.
  □   Report the repo using the "Report repository" button on GitHub.
  □   If this is work-related: notify your IT or security team now.
```

---

### Step 7: Save Report

```bash
AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
mkdir -p "$AMM_ROOT/Security/scans/"
REPORT_FILE="$AMM_ROOT/Security/scans/{repo_name}-$(date +%Y-%m-%d).md"
```

Tell the user: "I've saved a full report to: `Security/scans/{repo_name}-{date}.md` — you can share that file with your team or clients."

Offer to share via `/send-slack` or `/send-email` if integrations are configured.

---

## Flags

| Flag | What it does |
|------|-------------|
| `--quick` | Skip the sandbox, run only static checks. Done in under 2 minutes. |
| `--sandbox` | Force sandbox even if the initial scan looks clean. |
| `--share` | Automatically send the report to your default Slack channel when done. |
| `--no-install` | Skip the tool installation offer and work with what's available. |

## Important Behavior Rules

- **Never use security jargon without explaining it.** Every technical term gets a plain-English translation in parentheses.
- **Never block the user.** If a tool isn't installed and the user said skip, continue anyway.
- **Never fabricate findings.** If you can't check something, say "I wasn't able to check X."
- **Always give a verdict.** Even for Tier 0 AI-only scans, commit to a clear recommendation.
- **Clean up.** Delete `/tmp/security-scan-ai/` and `/tmp/security-scan-results/` after the report is saved.
