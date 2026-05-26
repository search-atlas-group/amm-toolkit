# SearchAtlas Toolkit — Plugin Conversion Design

**Status:** Draft for review
**Author:** Jonathan Duque (with Claude)
**Date:** 2026-05-26
**Target plugin name:** `searchatlas-toolkit`

---

## 1. Context & Motivation

Today's `toolkit-public` is distributed as a cloneable GitHub repo. Users run `setup.sh` to install slash commands into `~/.claude/commands/`, add the SearchAtlas MCP separately, and store per-client data inside the gitignored `<repo>/clients/` directory. A SessionStart auto-update hook keeps the repo current via `git pull`.

This design converts the toolkit into a Claude Code plugin, replacing the manual install + update mechanism with `/plugin install searchatlas-toolkit`. Three goals drive the conversion:

1. **Easier install and updates** — one command instead of clone + script + hook; native plugin update mechanism replaces the auto-update shim.
2. **Marketplace distribution** — repo doubles as its own marketplace listing, discoverable via `/plugin marketplace add`.
3. **Cleaner separation of toolkit code vs. user data** — toolkit lives at `~/.claude/plugins/searchatlas-toolkit/` (managed by Claude Code); user's client working files move to `~/.searchatlas/clients/` (owned by the user, never touched by plugin updates).

**Positioning shift:** the plugin is framed as the official SearchAtlas command-line toolkit for *anyone* using SearchAtlas for SEO, GBP, PPC, content, or AI visibility — not specifically agencies. Command descriptions reinforce the SearchAtlas capabilities each one draws from, so the command list doubles as a guided tour of the SearchAtlas platform.

**Claude Desktop / claude.ai users are out of scope for the plugin itself** — plugins are a Claude Code (CLI) feature. Desktop users continue to add the MCP as a custom connector and use it without slash commands. The README forks at the top into a CLI path and a Desktop path.

---

## 2. Locked-In Decisions

These were settled during brainstorming and are non-negotiable in the implementation plan:

| Decision | Value |
|---|---|
| Plugin name | `searchatlas-toolkit` |
| Command prefix | `sa-` (e.g., `/sa-scout`, `/sa-run-seo`) |
| Plugin scope | Code only; Desktop users get MCP-only path |
| MCP bundling | MCP server registered in plugin manifest; manual `claude mcp add` documented as Desktop fallback |
| Client data location | `~/.searchatlas/clients/` (env-overridable via `SA_CLIENTS_DIR`) |
| Mission-control | Stays outside the plugin as a separate companion piece |
| Auto-update hook | Removed (plugins handle updates natively) |
| Marketplace structure | Self-hosted; same repo doubles as plugin source + marketplace |

---

## 3. Repository Layout

The repo serves three roles simultaneously: plugin source, marketplace listing, and home of the mission-control companion.

```
toolkit-public/
├── .claude-plugin/
│   ├── plugin.json                # plugin manifest (MCP, hooks, asset paths)
│   └── marketplace.json           # one-entry marketplace pointing at this plugin
├── commands/                      # user-typed slash commands
│   ├── sa-scout.md
│   ├── sa-business-report.md
│   ├── sa-my-account.md
│   ├── sa-onboard-client.md
│   ├── sa-sync-client.md
│   ├── sa-summit-shot.md
│   ├── sa-help.md
│   ├── sa-run-seo.md
│   ├── sa-run-gbp.md
│   ├── sa-run-ppc.md
│   ├── sa-run-content.md
│   ├── sa-run-pr.md
│   ├── sa-run-visibility.md
│   ├── sa-send-slack.md
│   ├── sa-send-discord.md
│   ├── sa-send-email.md
│   └── sa-send-circle.md
├── skills/                        # reserved for future skill layer (empty v1)
│   └── .gitkeep
├── agents/                        # reserved for future specialized agents (empty v1)
│   └── .gitkeep
├── hooks/
│   ├── hooks.json                 # SessionStart hook registration
│   └── ensure-env.sh              # idempotent env + MCP auth check
├── workflows/                     # YAML templates (unchanged from current)
├── integrations/                  # send-*.sh scripts (unchanged from current)
├── scripts/
│   └── migrate-to-plugin.sh       # one-shot migration for existing CLI users
├── AGENTS.md                      # plugin-scoped instructions (intent routing)
├── README.md                      # public-facing install + usage
├── CHANGELOG.md                   # plugin release history
└── mission-control/               # untouched separate companion
```

**Empty `skills/` and `agents/` directories matter now:** the plugin manifest declares these as asset paths up front. When the future skill layer or specialized agents land, they drop into existing wired-up directories — no manifest changes, no migration, no breaking version bump. Commands can already reference future agents/skills by name; they start working the moment those files appear.

---

## 4. Plugin Manifest (`.claude-plugin/plugin.json`)

```json
{
  "name": "searchatlas-toolkit",
  "version": "1.0.0",
  "description": "Official SearchAtlas command-line toolkit — SEO, GBP, PPC, content, and AI visibility workflows powered by the SearchAtlas MCP.",
  "author": {
    "name": "SearchAtlas",
    "url": "https://searchatlas.com"
  },
  "homepage": "https://github.com/searchatlas/amm-toolkit",
  "license": "MIT",

  "mcpServers": {
    "searchatlas": {
      "type": "http",
      "url": "https://mcp.searchatlas.com/mcp"
    }
  },

  "hooks": "${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json",
  "commands": "${CLAUDE_PLUGIN_ROOT}/commands",
  "agents": "${CLAUDE_PLUGIN_ROOT}/agents",
  "skills": "${CLAUDE_PLUGIN_ROOT}/skills"
}
```

**Marketplace manifest (`.claude-plugin/marketplace.json`):**

```json
{
  "name": "searchatlas",
  "owner": {
    "name": "SearchAtlas",
    "url": "https://searchatlas.com"
  },
  "plugins": [
    {
      "name": "searchatlas-toolkit",
      "description": "Official SearchAtlas command-line toolkit",
      "source": ".",
      "category": "marketing"
    }
  ]
}
```

**Install flow for CLI users:**

```
/plugin marketplace add searchatlas/amm-toolkit
/plugin install searchatlas-toolkit
```

The MCP server registration is part of plugin install — users do **not** need to run `claude mcp add searchatlas` separately. On first use of any `sa-*` command (or any MCP tool), Claude Code triggers the OAuth flow to `mcp.searchatlas.com` and the user authorizes via their SearchAtlas account.

---

## 5. Commands

**File naming:** file name equals command name for grep-friendliness (`commands/sa-scout.md` → `/sa-scout`).

**Frontmatter pattern:**

```markdown
---
name: sa-scout
description: Read-only diagnostic across SEO, GBP, PPC, content, and AI visibility. Uses SearchAtlas's holistic SEO scoring, Site Explorer, GBP audit, and AI visibility tools to give you a full picture and prioritized actions. Creates a SA Report Builder report and saves a local HTML record.
---
```

Every command description names the SearchAtlas capabilities it draws from. The command list (in `/sa-help` and the README) functions as both reference and product tour.

**Two find-and-replace edits per command body** (from the existing `commands/*.md` files):

1. `AMM_ROOT=$(git rev-parse --show-toplevel ...)` → `CLAUDE_PLUGIN_ROOT` (set by Claude Code at runtime; points to the plugin's install dir for `workflows/`, `integrations/`, etc.)
2. `clients/{slug}/...` → `${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/...`

**Why two env vars instead of one:** plugin assets (workflows, integrations) and user data have fundamentally different lifecycles. Plugin assets get overwritten on update; user data must never be touched. Two vars keep that boundary explicit in every command body.

**Command-to-subfolder mapping** (each accumulating artifact gets its own subdirectory under the client's data folder):

| Command | Writes to |
|---|---|
| `/sa-scout` | `~/.searchatlas/clients/{slug}/scouts/{date}.html` |
| `/sa-business-report` | `~/.searchatlas/clients/{slug}/reports/{date}.md` |
| `/sa-run-*` (workflows) | `~/.searchatlas/clients/{slug}/workflows/{type}-{date}.md` |
| `/sa-summit-shot` | `~/.searchatlas/clients/{slug}/shots/play-{NN}-{date}.md` |
| `/sa-onboard-client`, `/sa-sync-client` | `~/.searchatlas/clients/{slug}/brand-profile.md` (top level) |

Top level holds only canonical files (`brand-profile.md`, `notes.md`). Everything that accumulates with repeated runs gets a subfolder.

---

## 6. Plugin Instructions (`AGENTS.md`)

The plugin ships its own `AGENTS.md` (loaded automatically when any `sa-*` command runs or when the SearchAtlas MCP is in scope). The user's own `~/.claude/CLAUDE.md` is **never** touched.

**Structure (mirrors today's CLAUDE.md, with substitutions):**

1. **What this plugin is** — official SearchAtlas toolkit for anyone doing SEO/GBP/PPC/content/AI visibility with SearchAtlas.
2. **MCP server** — endpoint, OAuth flow, install (carried over).
3. **Golden Rules** — schema discovery, error reading, polling, name collisions, no hardcoded IDs, no secret exposure. Rule 7 updated for `$CLAUDE_PLUGIN_ROOT` / `$SA_CLIENTS_DIR`. Rule 8 updated for `~/.searchatlas/clients/`.
4. **Parameter Quick Reference** — carried over verbatim.
5. **Account Discovery Flow** — carried over verbatim.
6. **Intent Routing** — same routing logic as today's §6, every command reference updated from `/scout` → `/sa-scout`, etc. Phrasing softened to accommodate non-agency users ("set up a new client / project / brand", "manage your own site or your clients'").
7. **Workflow Execution Pattern** — carried over verbatim.
8. **Plugin Surface** — new table of all `sa-*` commands with one-line descriptions.
9. **Communication Integrations** — Slack, Discord, Email, Circle (carried over).
10. **Conventions** — never fabricate data, confirm before destructive actions, use YAML workflow templates, keep output clean.

**What's intentionally not in AGENTS.md:** anticipatory command suggestions ("based on this conversation, you should probably run /sa-scout"). That's skill-layer territory and belongs in the future `skills/` directory, not the command-layer instructions.

---

## 7. Hooks

**`hooks/hooks.json`** registers a single SessionStart hook:

```json
{
  "hooks": [
    {
      "type": "SessionStart",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/ensure-env.sh",
      "timeout_ms": 2000
    }
  ]
}
```

**`hooks/ensure-env.sh`** does three small jobs, all idempotent, all fail-open (never blocks session start):

```bash
#!/bin/bash
# SessionStart — three jobs: client data dir, legacy detection, MCP auth check.

# 1. Ensure client data home exists
SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"
mkdir -p "$SA_CLIENTS_DIR"

# 2. Detect legacy data locations and nudge toward migration
if [ -d "$HOME/.amm/clients" ] && [ -z "$(ls -A "$SA_CLIENTS_DIR" 2>/dev/null)" ]; then
  echo "📦 Found legacy ~/.amm/clients/ — run /sa-help migrate-data to move it to ~/.searchatlas/clients/"
fi

# 3. Verify SearchAtlas MCP is registered (best-effort, no hard fail)
if ! claude mcp list 2>/dev/null | grep -q "searchatlas"; then
  echo "⚠️  SearchAtlas MCP not registered. Plugin commands will fail until it is."
  echo "   This usually self-heals when the plugin loads — restart Claude Code if needed."
fi

exit 0
```

**Fail-open rationale:** hooks that block session start create terrible UX. This hook only *informs* — never refuses. Worst case, a `sa-*` command fails with a clear error from the underlying tool.

**What we explicitly do NOT add:** no auto-update hook (plugins handle that natively), no telemetry, no analytics.

---

## 8. Client Data Home

**Default location:** `~/.searchatlas/clients/`
**Override mechanism:** `SA_CLIENTS_DIR` environment variable

**Per-client directory structure:**

```
~/.searchatlas/clients/{slug}/
├── brand-profile.md       # canonical identity (synced with SA brand vault)
├── notes.md               # freeform user notes
├── scouts/                # /sa-scout history
│   └── 2026-05-26.html
├── reports/               # /sa-business-report outputs
│   └── 2026-05-26.md
├── workflows/             # /sa-run-* logs
│   └── seo-2026-05-26.md
└── shots/                 # /sa-summit-shot executions
    └── play-03-2026-05-26.md
```

**Principle:** top level holds only canonical files. Anything that accumulates with repeated runs gets its own subfolder. Each command's body is updated once to write into its designated subfolder, with `mkdir -p` ensuring the folder exists on first write.

**Three guarantees this gives:**

- **Default works for everyone:** users who never set `SA_CLIENTS_DIR` get `~/.searchatlas/clients/{slug}/` automatically.
- **Power-user override available:** point `SA_CLIENTS_DIR` at Dropbox/iCloud/a synced folder if they want client data to follow them between machines.
- **Plugin install dir is never written to:** updates can clobber the plugin freely without touching user data.

---

## 9. Documentation Structure

### README.md (top-level user-facing doc)

```
├── Hero: "Official SearchAtlas command-line toolkit"
│   └── One-paragraph: what it is, who it's for (anyone doing SEO with SearchAtlas)
├── Quickstart fork
│   ├── 🟦 Using Claude Code? → Plugin install (3 lines)
│   └── 🟪 Using Claude Desktop or claude.ai? → MCP custom connector (3 lines)
├── What you get
│   ├── Slash commands table (one-line description per /sa-* command)
│   └── Capabilities the toolkit unlocks (SearchAtlas pitch, integrated)
├── First run
│   └── OAuth flow walkthrough
├── Your client data lives at ~/.searchatlas/clients/
│   └── Brief structure explainer + the SA_CLIENTS_DIR override
├── Integrations (Slack, Discord, Email, Circle)
│   └── .env setup, optional
├── Migrating from the cloned-repo toolkit
│   └── (Section 10 below)
├── Companion: mission-control/
│   └── Brief mention, link to its own README
└── Troubleshooting + Support
```

### AGENTS.md

Plugin-scoped instructions (see Section 6). Loaded automatically when plugin is active.

### CHANGELOG.md

Plugin release history. SemVer. Visible to users on `/plugin update`.

### Files removed during this work (already deleted per current git status)

- `POWER-USER.md` (content folded into AGENTS.md)
- `docs/CLAUDE_DESKTOP_PROMPTS.md` (Desktop section in README replaces it)
- `commands/README.md` (plugin-scoped AGENTS.md replaces it)
- `docs/install.html`, `docs/welcome.html` (README handles install)

---

## 10. Migration Path for Existing CLI Users

**Target user experience: one shell command + one click.**

```bash
cd /path/to/your/toolkit-public
./scripts/migrate-to-plugin.sh
```

Next time the user opens Claude Code, they see a trust prompt:

```
SearchAtlas Toolkit plugin requested by your settings.
Trust this marketplace (searchatlas/amm-toolkit) and install? [y/n]
```

They press `y`. Plugin installed, MCP registered, AGENTS.md loaded, commands available.

### What `migrate-to-plugin.sh` does

1. **Pull latest repo** so the script and plugin manifest are current.
2. **Move client data:** `<repo>/clients/*` → `~/.searchatlas/clients/`, reshape into `scouts/`, `reports/`, `workflows/`, `shots/` subfolders. Idempotent — skip files already at destination.
3. **Uninstall legacy commands** from `~/.claude/commands/`. Operates from a hardcoded whitelist of the toolkit's known command filenames (`scout.md`, `business-report.md`, `my-account.md`, `onboard-client.md`, `sync-client.md`, `summit-shot.md`, `help.md`, `run-seo.md`, `run-gbp.md`, `run-ppc.md`, `run-content.md`, `run-pr.md`, `run-visibility.md`, `send-slack.md`, `send-discord.md`, `send-email.md`, `send-circle.md`). Never touches commands the toolkit didn't install, including unrelated user commands or other plugins.
4. **Remove the legacy SessionStart auto-update hook** (the `git pull` shim installed by the old `setup.sh`) from `~/.claude/settings.json`. The plugin's own SessionStart hook from §7 is a separate hook, registered via the plugin's `hooks/hooks.json` — it gets installed automatically when the plugin loads and is not affected by this step.
5. **Add plugin auto-install declarations** to `~/.claude/settings.json` (merge, don't overwrite):
   ```json
   {
     "extraKnownMarketplaces": [
       { "source": "github", "repo": "searchatlas/amm-toolkit" }
     ],
     "enabledPlugins": ["searchatlas-toolkit"]
   }
   ```
6. **Print summary + offer cleanup:** "Migration complete. Open Claude Code — it'll prompt you to install the plugin. Want to delete this toolkit-public/ folder now? (Keep it if you use mission-control.)"

### Discovery path — how existing users learn migration exists

The current SessionStart auto-update hook (already running for everyone with a cloned repo) gets one final update — a polite nudge on every session start until migration completes:

```
📦 SearchAtlas Toolkit v2 available as a plugin.
   Run: cd <your toolkit-public dir> && ./scripts/migrate-to-plugin.sh
   (One-shot migration — moves your data, installs the plugin, cleans up the old setup.)
```

The nudge stops appearing once migration removes the hook itself. No one gets badgered indefinitely.

### For users who deleted the cloned repo before migrating

Fallback path in README:

1. Run standard plugin install: `/plugin marketplace add searchatlas/amm-toolkit` then `/plugin install searchatlas-toolkit`.
2. Plugin's SessionStart hook detects empty `~/.searchatlas/clients/` and offers a `/sa-help migrate-data` command that scans common locations (`~/Desktop`, `~/Documents`, `~/`) for old `toolkit-public/clients/` data and moves it.

---

## 11. Future Expansion (out of scope for v1, but layout-aware)

The v1 layout is designed so each of these can be added without breaking changes:

- **v1.x — Skills layer:** populate `skills/` with model-invoked skills (auto-suggest next action, route ambiguous requests, surface quota/auth issues). Skills activate based on conversation context without the user typing a command.
- **v2 — Specialized agents:** populate `agents/` with subagents (`seo-auditor`, `content-strategist`, `ppc-launcher`, etc.) that workflows can dispatch in parallel.
- **v2.x — Agent-orchestrated workflows:** `/sa-run-seo` dispatches multiple agents concurrently, aggregates results, and presents a unified report.
- **More MCP tools:** as the SearchAtlas MCP grows new tools, no plugin changes are needed — commands rely on schema discovery (Golden Rule 1) to find them.

---

## 12. Out of Scope for v1

- **Claude Desktop plugin support** — Desktop has its own plugin system that only hosts Anthropic-approved offerings; we cannot ship there. Desktop users get MCP-only path via README.
- **Public marketplace listing** — if Anthropic launches a public marketplace, we can submit then. For now, self-hosted.
- **Telemetry / analytics** — not adding.
- **Skills and agents** — directories reserved, contents come later.
- **mission-control rework** — stays as-is, separate companion.

---

## 13. Open Questions / Verification Needed Before Implementation

- **Settings.json auto-install fields** — confirm the exact schema for `extraKnownMarketplaces` and `enabledPlugins` against current Claude Code docs. Sample shown in §10 is based on second-hand description; verify before shipping the migration script.
- **`CLAUDE_PLUGIN_ROOT` env var** — confirm Claude Code exposes this to hook scripts and command bodies, and confirm the exact name. If different, find/replace across all commands.
- **Plugin command frontmatter schema** — confirm exact field names (`name`, `description`) for the latest Claude Code plugin format.
- **Marketplace.json schema** — confirm exact required fields against current docs.

---

## 14. Next Step

After spec review and approval, invoke the `superpowers:writing-plans` skill to produce an implementation plan with discrete steps, file-by-file changes, and verification checkpoints.
