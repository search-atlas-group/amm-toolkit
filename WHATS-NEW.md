# What's New

Latest additions and updates to the Agentic Marketing Mastermind toolkit.

---

<!-- AMM Guardian adds entries here automatically. Newest at top. -->

## 2026-04-27 — Claude Code v2.1.118: Hooks Can Now Call MCP Tools Directly

Claude Code v2.1.118 shipped a change that matters for SA workflows: **hooks can now invoke MCP tools directly**, without a shell script in between. Set `"type": "mcp_tool"` in any hook and point it at a SearchAtlas tool — no bash wrapper needed.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "type": "mcp_tool",
        "server": "searchatlas",
        "tool": "otto_trigger_recrawl",
        "params": {}
      }
    ]
  }
}
```

Other changes in this release:
- `/cost` and `/stats` are merged into `/usage` (both still work as shortcuts)
- Custom themes: create and switch named themes via `/theme`, or hand-edit `~/.claude/themes/`
- Windows: WSL can now inherit Windows-side managed settings via `wslInheritsWindowsSettings`

**To update:** `npm update -g @anthropic-ai/claude-code`

---

## 2026-04-23 — Setup Overhaul + Integration Wizard

### One-Command Quickstart (Mac + Windows)
Getting started is now a single paste into your terminal. The quickstart scripts handle everything — no manual installs, no configuration files.

**macOS:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"
```

**Windows (PowerShell as Admin):**
```powershell
irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex
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
├── amm-toolkit/       ← this toolkit
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
git -C ~/YourWorkspace/amm-toolkit pull origin main
bash ~/YourWorkspace/amm-toolkit/setup.sh
```
