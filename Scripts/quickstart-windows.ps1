# Agentic Marketing Mastermind — Windows Quick Start
# Creates your workspace, installs all prerequisites, and launches Claude Code.
#
# Usage — run in PowerShell as Administrator (Win + X -> Terminal (Admin)):
#   irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex

$ErrorActionPreference = "Stop"

$REPO_URL = "https://github.com/search-atlas-group/amm-toolkit.git"
$GIT_BASH  = "C:\Program Files\Git\bin\bash.exe"

function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Step($n, $msg) { Write-Host "`n  [$n] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "       $msg" }
function Write-Hr()       { Write-Host "  ─────────────────────────────────────────────────────" }
function Write-Fail($msg) { Write-Host "  [X]  $msg" -ForegroundColor Red; exit 1 }

function Update-SessionPath {
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [System.Environment]::GetEnvironmentVariable("Path", "User")
}

Clear-Host
Write-Host ""
Write-Host "  +──────────────────────────────────────────────────────+"
Write-Host "  |    Agentic Marketing Mastermind — Windows Setup     |"
Write-Host "  +──────────────────────────────────────────────────────+"
Write-Host ""
Write-Host "  This sets up your full agentic workspace from scratch."
Write-Host "  Estimated time: 5-10 minutes. You'll only need to do this once."
Write-Host ""

# ── 0a: Workspace Naming ──────────────────────────────────────────────────────
Write-Hr
Write-Host ""
Write-Host "  Step 1 of 2 — Name your workspace" -ForegroundColor White
Write-Host ""
Write-Host "  This is the root folder where everything lives:"
Write-Host "  your toolkit, client folders, and AI memory."
Write-Host "  Name it after your agency so it's easy to find."
Write-Host ""
Write-Host "  Examples:  CoastalMedia-AMM  |  SunriseAgency-AI  |  AMM-Workspace"
Write-Host ""
$WORKSPACE_NAME = Read-Host "  Workspace name (Enter for 'AMM-Workspace')"
if ([string]::IsNullOrWhiteSpace($WORKSPACE_NAME)) { $WORKSPACE_NAME = "AMM-Workspace" }

$WORKSPACE_DIR = "$HOME\$WORKSPACE_NAME"
$REPO_DIR = "$WORKSPACE_DIR\amm-toolkit"

Write-Host ""
Write-Ok "Workspace -> $WORKSPACE_DIR"
Write-Host ""

# ── 0b: IDE / Terminal Selection ──────────────────────────────────────────────
Write-Hr
Write-Host ""
Write-Host "  Step 2 of 2 — Choose your coding environment" -ForegroundColor White
Write-Host ""
Write-Host "  You only need one. We'll detect what you already have"
Write-Host "  and suggest it — or you can pick a different one to download."
Write-Host ""

# Fixed list of supported options (priority order for recommendation)
$IDE_NAMES  = @("Cursor", "Warp", "VS Code", "Windsurf", "PowerShell (stay here)")
$IDE_URLS   = @("https://cursor.com", "https://www.warp.dev", "https://code.visualstudio.com", "https://windsurf.com", "")
$IDE_STATUS = @()

$WarpExe = "$env:LOCALAPPDATA\Programs\Warp\Warp.exe"

# Detect which are installed
for ($i = 0; $i -lt $IDE_NAMES.Count; $i++) {
  switch ($IDE_NAMES[$i]) {
    "Cursor"   { $IDE_STATUS += if (Get-Command cursor -ErrorAction SilentlyContinue) { "ready" } else { "not installed" } }
    "Warp"     { $IDE_STATUS += if (Test-Path $WarpExe) { "ready" } else { "not installed" } }
    "VS Code"  {
      $vsFound = (Get-Command code -ErrorAction SilentlyContinue) -or
                 (Test-Path "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe") -or
                 (Test-Path "C:\Program Files\Microsoft VS Code\Code.exe")
      $IDE_STATUS += if ($vsFound) { "ready" } else { "not installed" }
    }
    "Windsurf" { $IDE_STATUS += if (Get-Command windsurf -ErrorAction SilentlyContinue) { "ready" } else { "not installed" } }
    default    { $IDE_STATUS += "ready" }
  }
}

# Find best already-installed option (priority order, PowerShell is last resort)
$REC_IDX  = $IDE_NAMES.Count - 1
$REC_NAME = "PowerShell (stay here)"
for ($i = 0; $i -lt ($IDE_NAMES.Count - 1); $i++) {
  if ($IDE_STATUS[$i] -eq "ready") {
    $REC_IDX  = $i
    $REC_NAME = $IDE_NAMES[$i]
    break
  }
}

# Contextual intro based on what's found
if ($REC_NAME -eq "PowerShell (stay here)") {
  Write-Host "  You don't have a dedicated coding environment installed yet."
  Write-Host "  We recommend Cursor — it's built for AI-assisted work."
  Write-Host "  Enter 1 to download it, or pick any option from the list."
} else {
  Write-Host "  We found $REC_NAME on your PC — that's a solid choice." -ForegroundColor White
  Write-Host "  Press Enter to use it, or pick something else from the list below."
}

Write-Host ""

# Display all options with status and recommendation marker
for ($i = 0; $i -lt $IDE_NAMES.Count; $i++) {
  $name   = $IDE_NAMES[$i]
  $status = $IDE_STATUS[$i]
  $num    = $i + 1
  $pad    = $name.PadRight(24)
  if ($i -eq $REC_IDX -and $status -eq "ready") {
    Write-Host "  $num. $pad" -NoNewline
    Write-Host "[OK] installed" -NoNewline -ForegroundColor Green
    Write-Host "  <- recommended"
  } elseif ($status -eq "ready") {
    Write-Host "  $num. $pad" -NoNewline
    Write-Host "[OK] installed" -ForegroundColor Green
  } else {
    Write-Host "  $num. $pad— not installed" -ForegroundColor DarkGray
  }
}

Write-Host ""
$IDE_INPUT = Read-Host "  Enter number (Enter for $REC_NAME)"
if ([string]::IsNullOrWhiteSpace($IDE_INPUT)) { $IDE_INPUT = "$($REC_IDX + 1)" }

$IDX = ([int]$IDE_INPUT) - 1
if ($IDX -lt 0 -or $IDX -ge $IDE_NAMES.Count) { $IDX = $REC_IDX }

$IDE_NAME         = $IDE_NAMES[$IDX]
$IDE_STATUS_CHOSEN = $IDE_STATUS[$IDX]
$IDE_URL          = $IDE_URLS[$IDX]
$IDE_NOT_INSTALLED = $false

Write-Host ""

if ($IDE_STATUS_CHOSEN -eq "not installed") {
  $IDE_NOT_INSTALLED = $true
  Write-Host "  [!]  $IDE_NAME is not installed yet." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "  Download: $IDE_URL" -ForegroundColor White
  Write-Host ""
  $openDl = Read-Host "  Open the download page now? (y/n)"
  if ($openDl -eq "y" -or $openDl -eq "Y") {
    Start-Process $IDE_URL
    Write-Host ""
    Write-Info "Download page opened. Install $IDE_NAME, then come back here."
    Write-Info "Setup will continue and finish — you can open your workspace"
    Write-Info "in $IDE_NAME afterwards."
  }
} else {
  Write-Ok "Using: $IDE_NAME"
}

Write-Host ""
Write-Hr

# ── Step 1: Execution Policy ──────────────────────────────────────────────────
Write-Step "1/5" "PowerShell execution policy"

$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {
  Write-Warn "Policy is '$policy' — setting to RemoteSigned..."
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
}
Write-Ok "Execution policy: $(Get-ExecutionPolicy -Scope CurrentUser)"

# ── Step 2: winget ────────────────────────────────────────────────────────────
Write-Step "2/5" "winget (Windows Package Manager)"

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host ""
  Write-Host "  winget is not available on your system." -ForegroundColor Yellow
  Write-Host "  Install 'App Installer' from the Microsoft Store:" -ForegroundColor Yellow
  Write-Host "    https://aka.ms/getwinget" -ForegroundColor White
  Write-Host ""
  Write-Host "  Or install prerequisites manually and re-run:" -ForegroundColor Yellow
  Write-Host "    Node.js : https://nodejs.org  (choose LTS)" -ForegroundColor White
  Write-Host "    Git     : https://git-scm.com/download/win" -ForegroundColor White
  Write-Host ""
  exit 1
}
Write-Ok "winget available"

# ── Version requirements ──────────────────────────────────────────────────────
$MIN_NODE_MAJOR = 18
$MIN_GIT_MINOR  = 30   # 2.30+
$MIN_JAVA_MAJOR = 17

function Test-NodeOk {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return $false }
  $major = [int]((node --version) -replace 'v','').Split('.')[0]
  $major -ge $MIN_NODE_MAJOR
}

function Test-GitOk {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { return $false }
  $parts = ((git --version) -replace 'git version ','').Split('.')
  [int]$parts[0] -gt 2 -or ([int]$parts[0] -eq 2 -and [int]$parts[1] -ge $MIN_GIT_MINOR)
}

function Test-JavaOk {
  if (-not (Get-Command java -ErrorAction SilentlyContinue)) { return $false }
  $out = java -version 2>&1 | Select-Object -First 1
  if ($out -match '"(\d+)\.?(\d*)') {
    $major = [int]$Matches[1]
    if ($major -eq 1) { $major = [int]$Matches[2] }
    return $major -ge $MIN_JAVA_MAJOR
  }
  return $false
}

# ── Step 3: Git + Node.js ─────────────────────────────────────────────────────
Write-Step "3/6" "Git + Node.js"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Warn "Git not found — installing..."
  winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
  Update-SessionPath
} elseif (-not (Test-GitOk)) {
  Write-Warn "Git version is outdated (need 2.$MIN_GIT_MINOR+) — upgrading..."
  winget upgrade -e --id Git.Git --accept-source-agreements --accept-package-agreements
  Update-SessionPath
}
Write-Ok "$(git --version)"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Warn "Node.js not found — installing LTS..."
  winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
  Update-SessionPath
} elseif (-not (Test-NodeOk)) {
  Write-Warn "Node $(node --version) is outdated (need v$MIN_NODE_MAJOR+) — upgrading..."
  winget upgrade -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
  Update-SessionPath
}
Write-Ok "Node $(node --version) - npm $(npm --version)"

# ── Step 4: Java ─────────────────────────────────────────────────────────────
Write-Step "4/6" "Java (JDK $MIN_JAVA_MAJOR+ required)"

if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
  Write-Warn "Not found — installing Microsoft OpenJDK 21..."
  winget install -e --id Microsoft.OpenJDK.21 --accept-source-agreements --accept-package-agreements
  Update-SessionPath
  Write-Ok "Java installed"
} elseif (-not (Test-JavaOk)) {
  Write-Warn "Java version is below $MIN_JAVA_MAJOR — upgrading to OpenJDK 21..."
  winget upgrade -e --id Microsoft.OpenJDK.21 --accept-source-agreements --accept-package-agreements 2>$null
  winget install -e --id Microsoft.OpenJDK.21 --accept-source-agreements --accept-package-agreements 2>$null
  Update-SessionPath
  Write-Ok "Java upgraded"
} else {
  $jver = (java -version 2>&1 | Select-Object -First 1) -replace '.*"(.*)".*','$1'
  Write-Ok "Java $jver — up to date"
}

# ── Step 5: Claude Code ───────────────────────────────────────────────────────
Write-Step "5/6" "Claude Code"

if (Get-Command claude -ErrorAction SilentlyContinue) {
  Write-Ok "Already installed"
} else {
  Write-Info "Installing via npm..."
  npm install -g @anthropic-ai/claude-code
  Update-SessionPath
  Write-Ok "Installed"
}

# ── Step 6: Workspace + amm-toolkit Toolkit ───────────────────────────────────────
Write-Step "6/6" "Creating workspace + installing toolkit"

New-Item -ItemType Directory -Force -Path "$WORKSPACE_DIR\clients" | Out-Null
New-Item -ItemType Directory -Force -Path "$WORKSPACE_DIR\memory"  | Out-Null
Write-Info "Created: $WORKSPACE_DIR\"
Write-Info "Created: $WORKSPACE_DIR\clients\"
Write-Info "Created: $WORKSPACE_DIR\memory\"

if (Test-Path $REPO_DIR) {
  Write-Warn "amm-toolkit already exists — pulling latest..."
  git -C $REPO_DIR pull origin INT 2>$null
} else {
  Write-Info "Cloning amm-toolkit toolkit..."
  git clone -b INT $REPO_URL $REPO_DIR
}
Write-Ok "amm-toolkit toolkit ready"

# ── CLAUDE.md (workspace session contract) ────────────────────────────────────
$claudeMdPath = "$WORKSPACE_DIR\CLAUDE.md"
if (-not (Test-Path $claudeMdPath)) {
  @"
# $WORKSPACE_NAME — Agentic Marketing Workspace

## Session Start (every session, no exceptions)
1. Read ``memory/MEMORY.md`` — reload all active rules and client context
2. Confirm which client you are working on before touching any files
3. Run ``/my-account`` if you need a fresh view of the SearchAtlas account

## Working Directory Check
If you are not running from inside the $WORKSPACE_NAME workspace folder,
stop and tell the user: "It looks like Claude is running from the wrong folder.
Open your IDE from $WORKSPACE_NAME\ and restart the session."
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
- ``/clear`` between every client — never carry one client's context into another
- ``/compact`` when responses slow down (or proactively at ~70% context)
- Save new learnings to ``memory/`` before closing a session
- Never paste API keys into the chat — they live in ``.env`` only
- Confirm before creating campaigns, publishing content, or sending messages

## Multi-Machine Note
MCP connections are machine-specific and do not sync between computers.
If you set up a second machine, run the quickstart again on that machine —
your files sync but your MCP config does not carry over automatically.

## Workspace Layout
- ``amm-toolkit/``     — toolkit: slash commands, workflows, scripts (do not edit)
- ``clients/``   — one subfolder per client with brief.md + assets/
- ``memory/``    — persistent notes Claude reads and writes across sessions
- ``.env``        — API keys and webhook URLs (never committed to git)
"@ | Out-File -FilePath $claudeMdPath -Encoding utf8
  Write-Info "Created: $WORKSPACE_DIR\CLAUDE.md"
}

# ── memory/MEMORY.md (persistent context index) ───────────────────────────────
$memoryPath = "$WORKSPACE_DIR\memory\MEMORY.md"
if (-not (Test-Path $memoryPath)) {
  @"
# Memory Index

> Claude reads this file at the start of every session.
> Keep this file under 150 lines — link to separate files for detail.

## How to add a memory
Save a .md file in this folder and add a one-line link below.
Format: ``- [Title](filename.md) — one-line description``

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
"@ | Out-File -FilePath $memoryPath -Encoding utf8
  Write-Info "Created: $WORKSPACE_DIR\memory\MEMORY.md"
}

# ── .env scaffold (never committed) ──────────────────────────────────────────
$envPath = "$WORKSPACE_DIR\.env"
if (-not (Test-Path $envPath)) {
  @"
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
"@ | Out-File -FilePath $envPath -Encoding utf8
  Write-Info "Created: $WORKSPACE_DIR\.env"
}

# ── .gitignore (protect secrets and local files) ──────────────────────────────
$gitignorePath = "$WORKSPACE_DIR\.gitignore"
if (-not (Test-Path $gitignorePath)) {
  @"
# Secrets — never commit
.env
.env.*
!.env.example

# Client assets stay local (logos, docs, binaries)
clients/*/assets/

# Session logs and OS files
memory/sessions/
*.log
.DS_Store
Thumbs.db
"@ | Out-File -FilePath $gitignorePath -Encoding utf8
  Write-Info "Created: $WORKSPACE_DIR\.gitignore"
}

if (Test-Path $GIT_BASH) {
  Write-Info "Running setup via Git Bash..."
  $unixDir = $REPO_DIR -replace "\\", "/" -replace "^([A-Za-z]):", { "/$($_.Value[0].ToString().ToLower())" }
  & $GIT_BASH -c "cd '$unixDir' && bash setup.sh"
} else {
  Write-Host ""
  Write-Warn "Git Bash not found at expected location."
  Write-Warn "Open Git Bash (search 'Git Bash' in Start) and run:"
  Write-Host "    cd '$REPO_DIR'" -ForegroundColor White
  Write-Host "    bash setup.sh" -ForegroundColor White
}

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Hr
Write-Host ""
Write-Host "  Your workspace is ready." -ForegroundColor White
Write-Host ""
Write-Host "  $WORKSPACE_DIR\"
Write-Host "  ├── amm-toolkit\       <- toolkit (slash commands, workflows)"
Write-Host "  ├── clients\      <- one folder per client"
Write-Host "  ├── memory\       <- Claude's persistent notes"
Write-Host "  ├── CLAUDE.md     <- your session rules and client list"
Write-Host "  └── .env          <- API keys (fill in after /setup-integrations)"
Write-Host ""
Write-Hr
Write-Host ""

if ($IDE_NOT_INSTALLED) {
  Write-Host "  Once $IDE_NAME is installed, open your workspace with:"
  Write-Host ""
  Write-Host "    $IDE_NAME `"$WORKSPACE_DIR`"    (or drag the folder into the app)" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "  Then in the integrated terminal, run:"
  Write-Host ""
  Write-Host "    claude" -ForegroundColor Cyan
} elseif ($IDE_NAME -ne "PowerShell (stay here)" -and -not [string]::IsNullOrWhiteSpace($IDE_URL)) {
  Write-Host "  Opening $IDE_NAME at your workspace..."
  switch ($IDE_NAME) {
    "Cursor"   { cursor $WORKSPACE_DIR }
    "Windsurf" { windsurf $WORKSPACE_DIR }
    "VS Code"  { code $WORKSPACE_DIR }
    "Warp"     { & $WarpExe $WORKSPACE_DIR }
  }
  Write-Host ""
  Write-Host "  In $IDE_NAME, open the integrated terminal and run:" -ForegroundColor White
  Write-Host ""
  Write-Host "    claude" -ForegroundColor Cyan
} else {
  Write-Host "  Run these two commands to start:" -ForegroundColor White
  Write-Host ""
  Write-Host "    cd `"$WORKSPACE_DIR`"" -ForegroundColor Cyan
  Write-Host "    claude" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "  ─────────────────────────────────────────────────────"
Write-Host ""
Write-Host "  Important: first-time permission prompt" -ForegroundColor White
Write-Host ""
Write-Host "  Claude Code may show a permission warning on first launch."
Write-Host "  This is expected. When prompted, choose:"
Write-Host "    Yes, allow for this session  (or the equivalent option)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Or launch with permissions pre-approved (recommended for beginners):"
Write-Host ""
Write-Host "    claude --dangerously-skip-permissions" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────────"
Write-Host ""
Write-Host "  Verify everything works:" -ForegroundColor White
Write-Host ""
Write-Host "  Once Claude Code opens, type:"
Write-Host ""
Write-Host "    /my-account" -ForegroundColor Cyan
Write-Host ""
Write-Host "  You should see your SearchAtlas account summary."
Write-Host "  If you do — you're fully set up. If not, re-run:"
Write-Host ""
Write-Host "    claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp" -ForegroundColor Cyan
Write-Host ""
Write-Hr
Write-Host ""
Write-Host "  Next: /setup-integrations inside Claude Code to connect"
Write-Host "  Slack, Email, Discord, or Circle."
Write-Host ""
