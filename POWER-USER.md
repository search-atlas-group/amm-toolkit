# Power User Guide

You're past the basics. This doc covers the full Agentic Marketing Mastermind stack — workspace layout, Mission Control wizards, workflow templates, send integrations, the 19 Summit plays, and the internals you'd want if you're operating this at agency scale.

If you haven't run the basic installer yet, start with the [README](README.md).

---

## Full install — clone the repo + workspace

The lightweight installer (`install-mcp.sh`) sets up the MCP + slash commands. Power users want the full clone — it gives you the Mission Control wizards, workflow YAMLs, send integration scripts, the security scanner, and a per-client filesystem.

**macOS:**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"
```

**Windows (PowerShell as Admin):**
```powershell
irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex
```

The quickstart will:
1. Create your agency workspace folder (you pick the name)
2. Ask which IDE you use — Cursor, Warp, VS Code, Windsurf, iTerm, Terminal
3. Install Git and Node.js if missing
4. Install Claude Code via npm (`@anthropic-ai/claude-code`)
5. Clone this toolkit into `~/<YourWorkspace>/amm-toolkit/`
6. Connect the SearchAtlas MCP (OAuth — no API key)
7. Install all slash commands into `~/.claude/commands/`
8. Install the Mission Control LaunchAgents (Mac only — see § below)
9. Open your workspace in your chosen IDE

---

## Workspace layout

```
~/YourWorkspace/
├── amm-toolkit/                  ← this toolkit (do not edit)
│   ├── commands/                 ← slash commands (/run-seo, /business-report, etc.)
│   ├── workflows/                ← YAML workflow templates
│   ├── integrations/             ← Slack, Discord, email, Circle scripts
│   ├── tools/
│   │   ├── supervisor/           ← always-on daemon (port 8764)
│   │   ├── command-center/       ← onboard-client wizard (port 8865)
│   │   ├── website-build/        ← website build wizard (port 8866)
│   │   ├── website-rebuild/      ← website rebuild wizard (port 8867)
│   │   ├── security/             ← repo security scanner
│   │   └── guardian/             ← AMM guardian dashboard
│   ├── guides/                   ← how-to guides
│   ├── docs/                     ← MCP setup, tool reference, slash commands
│   ├── Scripts/                  ← quickstart + setup scripts
│   ├── CLAUDE.md                 ← toolkit context for Claude Code
│   └── WHATS-NEW.md              ← changelog
└── clients/                      ← one folder per client (created by /onboard-client)
    └── your-client/
        ├── CLAUDE.md             ← per-client session context (IDs, brand voice)
        └── brand-profile.md      ← brand data synced with SearchAtlas
```

---

## Mission Control — web wizards

Three browser-based wizards back the most common workflows. They live at `docs/welcome.html` and talk to local FastAPI bridges that spawn `claude -p` subprocesses under the hood.

| Wizard | Port | What it does |
|---|---|---|
| **Onboard a client** | 8865 | Domain → brand voice → knowledge drop → services → fire. Full new-client setup. |
| **Build a website** | 8866 | 11-step greenfield site build, ends with a live Website Studio URL. |
| **Rebuild a website** | 8867 | Page-by-page redesign of an existing site, link-equity preserved, pre-launch baseline captured. |

A fourth service — the **supervisor** on port 8764 — stays running always (~15 MB RAM, idle). When you click a wizard card and its bridge has idle-shutdown, the supervisor wakes it via `launchctl` so you don't have to think about it. Bridges idle-shutdown after 5 minutes of inactivity; the welcome page sends a heartbeat every 60 s to keep them alive while you have it open.

**Tab close is safe.** The bridges spawn Claude as a detached process. Close the wizard tab mid-build and Claude keeps running — files land in `clients/<slug>/` regardless. Reopen `welcome.html` later to check status.

**If something gets stuck:** double-click `SearchAtlas Mission Control.command` on your Desktop (installed by setup). It re-loads any dead LaunchAgent and falls back to direct `nohup` launch if launchd is uncooperative.

For the supervisor architecture, see the [`tools/supervisor/server.py`](tools/supervisor/server.py) header comment.

---

## Workflow templates

YAML pipelines for recurring tasks. Run with `/run-seo`, `/run-gbp`, etc., or feed them to Claude directly.

| Template | Use case |
|---|---|
| [`workflows/seo-onboarding.yaml`](workflows/seo-onboarding.yaml) | Full new-client SEO setup |
| [`workflows/monthly-seo.yaml`](workflows/monthly-seo.yaml) | Monthly maintenance: suggestions, schema, indexing |
| [`workflows/gbp-optimization.yaml`](workflows/gbp-optimization.yaml) | GBP cleanup: recommendations, categories, services |
| [`workflows/gbp-monthly.yaml`](workflows/gbp-monthly.yaml) | GBP maintenance: reviews, posts, automation |
| [`workflows/ppc-launch.yaml`](workflows/ppc-launch.yaml) | PPC campaign: business, products, keywords, campaigns |
| [`workflows/authority-building.yaml`](workflows/authority-building.yaml) | PR + link building: press, cloud stacks, outreach |
| [`workflows/llm-visibility.yaml`](workflows/llm-visibility.yaml) | AI search: visibility, sentiment, SERP |

How they work, depends_on, error handling: [docs/WORKFLOWS.md](docs/WORKFLOWS.md).

---

## Send integrations

The toolkit can post results to Slack, Discord, email, and Circle. One-time setup:

```
/setup-integrations
```

That wizard asks for webhook URLs and API keys, writes them to your workspace's `.env`. Once configured, any workflow output can be piped:

```
/scout coastaldental.com
/send-slack
```

| Integration | Env var | Free-tier limit |
|---|---|---|
| Slack (multi-channel) | `SLACK_WEBHOOK_URL`, `SLACK_WEBHOOK_<NAME>` | Unlimited via webhooks |
| Discord | `DISCORD_WEBHOOK_URL` | Unlimited via webhooks |
| Email (Resend) | `RESEND_API_KEY`, `EMAIL_FROM` | 100/day on free plan |
| Circle | `CIRCLE_API_KEY`, `CIRCLE_COMMUNITY_ID` | Per Circle plan |

Scripts live in [`integrations/`](integrations/). Each is a simple bash file you can read and audit.

---

## The 19 Summit plays — `/summit-shot`

Atomic single-play executor. Each play is intentionally bounded — 1 article, 1 PR, drafts not auto-deploys. Pair with `/scout` (which says *what to run*) for triage-driven execution.

```
/summit-shot 5    # Topical map for a domain
/summit-shot 9    # PR Blast
/summit-shot 17   # LLM visibility deep dive
```

Full play list and rubric in [`commands/summit-shot.md`](commands/summit-shot.md).

The complement: `/scout` outputs a "Recommended Shots" list with the exact play numbers to run.

---

## Security scanner

Before cloning any third-party tool or running an unfamiliar script:

```
/security-scan https://github.com/owner/repo
```

A four-tier analysis runs: GitHub metadata, secrets detection, CVE checks, SAST rules, plus an optional behavioral sandbox. Returns a plain-English verdict.

Three ways to scan:

| Option | How | When |
|---|---|---|
| Browser quick check | Paste URL into `tools/security/` UI | Fast first look |
| Full local scan | `python3 tools/security/server.py` then open UI | Thorough pre-clone |
| Claude Code | `/security-scan <url>` in chat | Deep AI review with full report |

Walkthrough: [guides/security-scan-guide.md](guides/security-scan-guide.md).

---

## Per-client filesystem convention

Every client lives at `clients/<slug>/` with two files Claude always reads:

- **`CLAUDE.md`** — lean session context: client name, IDs (brand_vault_uuid, otto_project_id, etc.), top-3 next moves, notes
- **`brand-profile.md`** — full profile, two-way synced with the SearchAtlas brand vault via `/sync-client`

When you run any client-specific command, Claude reads these first. Stay on one client per chat — `/clear` between clients to avoid cross-contamination.

The directory is gitignored — your client data never accidentally enters the toolkit repo.

---

## Multi-machine note

MCP connections are machine-specific. Your files sync via Dropbox/iCloud/git, but the MCP config in `~/.claude.json` (and `claude_desktop_config.json` for Desktop) lives only on the machine where you ran the installer. Set up each machine separately — re-run the installer, re-authorize OAuth.

---

## Troubleshooting

**Slash command not found**
Re-run the installer. It refreshes `~/.claude/commands/` every time. If still missing: check `~/.claude/commands/` directly — the .md files should be there.

**Mission Control wizard spins forever on first click**
Bridge cold-start can take ~50 s the first time (deps install, MCP probe). Subsequent clicks are instant.

**Wizard hangs mid-build**
`tail /tmp/amm-website-build-audit.log` shows what tool is in flight. Long MCP calls (`cg_create_topical_map`, `ws_publish_project`) can take 1–10 min. Refresh the tab — the build keeps running.

**Bridge port collision** (errno 48 in `/tmp/amm-<name>.err`)
```bash
lsof -nP -iTCP:<port> -sTCP:LISTEN     # find what's squatting on the port
kill -9 <pid>                          # then re-run setup.sh
```

**OAuth keeps failing**
`claude mcp remove searchatlas && claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp` — re-adds cleanly. Restart Claude Code.

For the complete error matrix (60+ failure modes with file:line citations) ask your support contact — it's kept internally with the workshop materials.

---

## What's new

[WHATS-NEW.md](WHATS-NEW.md) is the changelog. Top entry is always the latest shipping change.
