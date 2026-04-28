# What's New

Latest additions and updates to the Agentic Marketing Mastermind toolkit.

---

<!-- AMM Guardian adds entries here automatically. Newest at top. -->

## 2026-04-28 — Security Scanner

Every installation now includes a built-in repository security scanner. Before cloning any third-party tool, plugin, or library, you can scan it for threats.

### Three Ways to Scan

**1. Claude Code (deepest analysis)**
```
/security-scan https://github.com/owner/repo
```
Claude runs a 4-tier analysis — GitHub metadata, secrets detection, CVE checks, SAST rules — and gives a plain-English verdict with a risk score.

**2. Browser Quick Check** (`projects/security/index.html`)
Open the scanner UI in any browser. Paste a GitHub URL and get an instant read using the public GitHub API — no auth, no server needed. Checks repo age, star count, hook files, and README red flags. Best for a fast first look before committing to a full scan.

**3. Full Local Scan** (deepest, offline-capable)
```bash
python3 projects/security/server.py
```
Then open the scanner UI and select **Full Local Scan**. Streams real-time output from `repo-security-scan.sh` — clones the repo into an isolated temp directory, runs `gitleaks`, `semgrep`, `trivy`, and behavioral checks, then cleans up. Results appear line-by-line as they arrive.

### Risk Calculator
The browser scan auto-populates the risk calculator with findings. Flip toggles to add or remove signals — the composite risk score updates in real time.

### What Gets Scanned
- Repository metadata (age, stars, fork status)
- Exposed secrets and credentials (`gitleaks`)
- Dependency vulnerabilities (`trivy`)
- SAST rules (`semgrep` ruleset)
- Suspicious install hooks, obfuscated code, outbound network calls

### Installed Automatically
The scanner files live in `projects/security/`. `setup.sh` stamps your workspace path into the UI at install time so local scan paths resolve correctly. No extra setup needed.

See [guides/security-scan-guide.md](guides/security-scan-guide.md) for full details.

---

## 2026-04-23 — Setup Overhaul + Integration Wizard

### One-Command Quickstart (Mac + Windows)
Getting started is now a single paste into your terminal. The quickstart scripts handle everything — no manual installs, no configuration files.

**macOS:**
```bash
/bin/bash -c "$(curl -fsSL https://forge.internal.searchatlas.com/search-atlas-group/agentic-marketing-mastermind/amm-toolkit/-/raw/main/Scripts/quickstart-mac.sh)"
```

**Windows (PowerShell as Admin):**
```powershell
irm https://forge.internal.searchatlas.com/search-atlas-group/agentic-marketing-mastermind/amm-toolkit/-/raw/main/Scripts/quickstart-windows.ps1 | iex
```

What it does:
- Creates your agency workspace folder (`~/YourAgency-AMM/`)
- Detects your coding environment and recommends the best one already installed
- Installs Git, Node.js, and Claude Code automatically if missing
- Clones this toolkit and installs all slash commands
- Connects the SearchAtlas MCP

### Workspace-First Structure
Every member now gets a named workspace root with a clear layout:
```
~/YourAgency-AMM/
├── AMM-SA/       ← this toolkit
└── clients/      ← one folder per client
```
Claude Code reads a `CLAUDE.md` file at the workspace root, so it understands your setup from the first message.

### IDE Selection
The quickstart detects which coding environments you have installed and recommends one. Cursor, Warp, Windsurf, VS Code, and iTerm2 are all supported. If you haven't installed one yet, it offers a download link.

### `/setup-integrations` — New Command
Connect your existing tools to Claude Code in a guided wizard. Supports:
- **HubSpot** — contacts, deals, pipeline
- **ClickUp** — tasks, lists, time tracking
- **Linear** — issues, projects, cycles
- **Notion** — pages, databases, workspace search
- **Slack** — channels, messages, search
- **Gmail + Google Calendar** — email and scheduling
- **GitHub** — repos, issues, pull requests

Run it inside Claude Code anytime: `/setup-integrations`

### Example Client Plans
The `plans/examples/` folder now has three filled-in YAML examples showing what a real plan looks like after running a workflow — including IDs, step results, and output summaries.

### `/onboard-client` — Full Brand Vault Integration

The onboarding wizard now supports two paths:

**Path A — Existing client in SearchAtlas:** Runs 4 parallel brand vault calls to pull everything automatically — name, domain, phone, address, hours, colors, logo, brand voice, knowledge graph entities, competitors, and all linked IDs (OTTO, GBP, PPC). Displays a confirmation block before creating any files.

**Path B — New client:** Guided 17-field form, then immediately pushes all data into a new brand vault — business info, contact details, voice profile, and knowledge graph seeded from day one.

Both paths end with the same two-file client structure:
- `clients/{slug}/CLAUDE.md` — session context (IDs, services, brand voice)
- `clients/{slug}/brand-profile.md` — full brand data synced with SA

### `/sync-client` — New Command

Two-way sync between a client's local `brand-profile.md` and their SearchAtlas brand vault. Three modes:

- **Push** — update SA with local edits
- **Pull** — refresh local file with latest SA data
- **Both** — full sync (pull first to avoid overwriting SA changes, then push local additions)

Always shows a diff before writing anything.

### Auto-Sync on Every Session

Client `CLAUDE.md` files now include an Auto-Sync block. At session start, Claude silently runs a 4-call brand vault pull and updates `brand-profile.md` if anything changed in SA. At session end, it diffs the file and pushes any changed fields back to SA using the correct update tool for each section.

---

## How to Update

Pull the latest toolkit version:
```bash
git -C ~/YourWorkspace/AMM-SA pull origin INT
bash ~/YourWorkspace/AMM-SA/setup.sh
```
