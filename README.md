# Agentic Marketing Mastermind

The SearchAtlas MCP gives Claude direct access to **620+ tools** for SEO, content, GBP, PPC, authority building, and AI visibility. This repo wires it into Claude Code (as slash commands) and Claude Desktop (as ready-to-paste prompts).

You'll be running a real SearchAtlas workflow from Claude in about 10 minutes.

---

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io/) is the standard that lets Claude call external tools directly. The SearchAtlas MCP is a hosted service at `mcp.searchatlas.com` — your laptop talks to it, it talks to the SearchAtlas platform. You don't run anything yourself; you just authorize it once.

---

## Get started — one command

Paste into Terminal (macOS) or PowerShell-as-Admin (Windows):

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex
```

The installer detects what you have (Claude Code, Claude Desktop, Cursor, Windsurf) and wires up each automatically. If Claude Code is installed, it also drops every slash command into `~/.claude/commands/` so they work the first time you open Claude.

---

## First run — authorize SearchAtlas

Open your client (Claude Code or Claude Desktop) and ask:

> "List my SearchAtlas projects"

A browser tab opens for OAuth. Sign in, click **Authorize**. That's it — your token refreshes automatically from here.

If the OAuth tab doesn't open: see [docs/MCP_SETUP.md](docs/MCP_SETUP.md).

---

## Your first workflow

### If you have Claude Code (terminal CLI)

Type a slash command in chat:

```
/my-account
/scout coastaldental.com
/business-report coastaldental.com
```

Every command is real — it calls SA tools, returns real data, saves real files to `clients/<slug>/`. See the full list: [docs/SLASH_COMMANDS.md](docs/SLASH_COMMANDS.md).

### If you have Claude Desktop only (no slash commands)

Slash commands aren't a Desktop feature — but every workflow has a copy-paste prompt that does the same thing:

→ [docs/CLAUDE_DESKTOP_PROMPTS.md](docs/CLAUDE_DESKTOP_PROMPTS.md)

Open the doc, find the workflow you want (`/scout`, `/business-report`, `/run-seo`, etc.), copy the prompt, paste it into a new Claude Desktop chat, fill in your client's domain, send.

---

## What's in the box

| | |
|---|---|
| **20+ slash commands** | Account overview, diagnostic scout, deep dives, full workflows for SEO / GBP / PPC / content / PR / LLM visibility |
| **Claude Desktop prompts** | Copy-paste equivalents for every slash command, output-faithful |
| **Workflow templates** | YAML pipelines you can run unattended ([docs/WORKFLOWS.md](docs/WORKFLOWS.md)) |
| **Send integrations** | Post results to Slack, Discord, email (Resend), or Circle |
| **Mission Control wizards** | Optional web UI for onboarding clients and building/rebuilding websites — see [POWER-USER.md](POWER-USER.md) |

---

## Going further

For agencies and operators who want the full stack — web wizards, background builds, workflow automation, send integrations, the 19 Summit-shot plays, supervisor architecture — read:

→ **[POWER-USER.md](POWER-USER.md)**

For everything you can call from chat:

→ **[docs/SLASH_COMMANDS.md](docs/SLASH_COMMANDS.md)**

---

## Need help?

| Problem | Where to look |
|---|---|
| OAuth tab didn't open / "Unauthorized" errors | [docs/MCP_SETUP.md](docs/MCP_SETUP.md) |
| Don't know which tool to call for a given task | [docs/INTENT_MAPPING.md](docs/INTENT_MAPPING.md) |
| Windows-specific issues (WSL, networking) | [guides/windows-claude-code-setup.md](guides/windows-claude-code-setup.md) |
| Want to understand best practices for the MCP | [docs/GOLDEN_RULES.md](docs/GOLDEN_RULES.md) |
| Want a guided tour of every SA tool | [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md) |
| Just want to scan a repo before running it | `/security-scan <github-url>` — see [guides/security-scan-guide.md](guides/security-scan-guide.md) |

---

## Updating

```bash
curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
```

The installer is idempotent — re-running it updates your commands and MCP config to the latest.

---

## License

MIT — see [LICENSE](LICENSE)
