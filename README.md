# Agentic Marketing Mastermind

The SearchAtlas MCP gives Claude direct access to **620+ tools** for SEO, content, GBP, PPC, authority building, and AI visibility. This repo gives you everything you need to use them — custom commands, ready-to-paste prompts, and a per-client filesystem convention.

You'll be running a real SearchAtlas workflow from Claude in about 10 minutes.

---

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io/) is the standard that lets Claude call external tools directly. The SearchAtlas MCP is a hosted service at `mcp.searchatlas.com` — your laptop talks to it, it talks to the SearchAtlas platform. You don't run anything yourself; you just authorize it once.

---

## Step 1 — Clone the repo

```bash
git clone https://github.com/search-atlas-group/amm-toolkit.git
cd amm-toolkit
```

You now have every command, prompt, and doc on your machine.

---

## Step 2 — Connect SearchAtlas to your Claude client

Pick whichever client you use. You only need one. Both end up with the same MCP wired in.

### Option A — Claude Desktop

1. Open the Claude Desktop config file:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
2. Add this entry (merge with anything already there):
   ```json
   {
     "mcpServers": {
       "searchatlas": {
         "type": "http",
         "url": "https://mcp.searchatlas.com/mcp"
       }
     }
   }
   ```
3. Restart Claude Desktop.
4. In a new chat, ask: *"List my SearchAtlas projects."* The first request opens a browser tab — sign into SearchAtlas, click **Authorize**. Token refresh is automatic from there.

### Option B — Claude Code (terminal CLI)

```bash
claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
```

Then to make the slash commands work, drop them into Claude Code's commands folder. The commands are organized into subfolders by tier — Claude Code reads `~/.claude/commands/` flat, so we copy them all into one place:

```bash
mkdir -p ~/.claude/commands
find commands -name '*.md' -not -name 'README.md' -exec cp {} ~/.claude/commands/ \;
```

First time you run a SearchAtlas tool in chat, a browser tab opens for OAuth. Sign in, approve, done.

---

## Step 3 — Run your first workflow

### Claude Desktop

Open [docs/CLAUDE_DESKTOP_PROMPTS.md](docs/CLAUDE_DESKTOP_PROMPTS.md), find the prompt you want (we'd start with `/my-account` or `/scout`), copy it, paste into a new Claude Desktop chat, fill in `{domain}` with any domain you have access to in SearchAtlas (e.g. `apple.com`), send.

### Claude Code

```
/my-account
/scout apple.com
/business-report apple.com
```

Every command is real — it calls SA tools, returns real data, saves real files to `clients/<slug>/`. Full command catalog: [docs/SLASH_COMMANDS.md](docs/SLASH_COMMANDS.md).

---

## What's in the box

| | |
|---|---|
| **20+ custom commands** | Account overview, diagnostic scout, deep dives, full workflows for SEO / GBP / PPC / content / PR / LLM visibility — see [docs/SLASH_COMMANDS.md](docs/SLASH_COMMANDS.md) |
| **Claude Desktop prompts** | Copy-paste equivalents for every command — see [docs/CLAUDE_DESKTOP_PROMPTS.md](docs/CLAUDE_DESKTOP_PROMPTS.md) |
| **Per-client filesystem** | `clients/<slug>/` holds each client's `CLAUDE.md` (lean session context) and `brand-profile.md` (full profile, two-way synced with SA) |
| **Workflow templates** | YAML pipelines you can run unattended — see [docs/WORKFLOWS.md](docs/WORKFLOWS.md) |

---

## Going further

Once you're comfortable with the basics, the toolkit has heavier machinery for agency-scale operation — a Mission Control web UI with three wizards (onboarding, build a site, rebuild a site), send-integrations for Slack / Discord / email / Circle, the 19 Summit-shot plays, and a per-client filesystem convention.

→ **[POWER-USER.md](POWER-USER.md)** has the full walkthrough, including an automated installer that sets all of it up for you.

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

To pull the latest commands, prompts, and docs:

```bash
cd amm-toolkit
git pull origin main
```

If you're a Claude Code user, also refresh your installed commands:

```bash
find commands -name '*.md' -not -name 'README.md' -exec cp {} ~/.claude/commands/ \;
```

(Power users: see [POWER-USER.md](POWER-USER.md) — there's a SessionStart hook that does this automatically.)

---

## License

MIT — see [LICENSE](LICENSE)
