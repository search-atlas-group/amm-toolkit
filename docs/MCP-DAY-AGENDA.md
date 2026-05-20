# MCP Day — Attendee Agenda

> Hands-on workshop: get the SearchAtlas MCP wired into your AI client and run your first real workflow.

---

## Before you arrive — 5 minutes of pre-flight

**Bring a laptop. macOS or Windows both work.** No SearchAtlas account yet? Sign up at [searchatlas.com](https://searchatlas.com) — free trial is enough for the day.

**If you can, run the installer before the session** so we spend our time on workflows, not waiting on `npm install`.

**macOS** — paste into Terminal:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"
```

**Windows** — paste into PowerShell (run as Administrator):
```powershell
irm https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-windows.ps1 | iex
```

**Already have Claude Desktop / Cursor / Windsurf and only want MCP + slash commands?** Use the lighter installer:
```bash
curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
```

It auto-detects every MCP-capable client on your machine and writes the right config for each. Idempotent — safe to re-run.

---

## Step 1 — Authorize SearchAtlas (first run only)

Open Claude Code in your workspace (`claude` from terminal), then run:

```
/my-account
```

A browser tab opens asking you to sign into SearchAtlas and approve access. That's it — Claude Code manages token refresh from here.

📎 Reference: [docs/MCP_SETUP.md](MCP_SETUP.md)

---

## Step 2 — The welcome page + Mission Control wizards

After install, your browser opens `welcome.html`. Three wizard cards are live:

| Card | What it does | Time |
|---|---|---|
| **Onboard a client** | Pull brand vault → write `clients/{slug}/` → optionally launch SEO/GBP/content playbooks | 5–10 min |
| **Build a website** | Generate a multi-page client site from brand vault + your brief | 10–20 min |
| **Rebuild a website** | Recreate an existing site in SA Website Studio with editable HTML | 10–20 min |

Click a card. Nothing else to install — the supervisor auto-wakes bridges in the background.

📎 Reference: [README.md](../README.md), [WHATS-NEW.md](../WHATS-NEW.md)

---

## Step 3 — Your first workflow from the chat

Slash commands run the same playbooks as the wizards, but from the Claude Code chat. Start with these:

| Command | What it does |
|---|---|
| `/my-account` | List every business, OTTO project, brand vault, GBP location, campaign |
| `/scout {domain}` | Read-only diagnostic across all pillars → prioritized action plan |
| `/business-report {domain}` | Full deep dive on a single client |
| `/onboard-client` | Guided new-client setup (manual or brand-vault pull) |
| `/run-seo` | SEO onboarding or monthly maintenance workflow |
| `/run-gbp` | Google Business Profile optimization |
| `/run-content` | Generate articles from a topical map |
| `/help` | List every command |

📎 Reference: [CLAUDE.md](../CLAUDE.md) (intent routing), [docs/INTENT_MAPPING.md](INTENT_MAPPING.md)

---

## Step 4 — Hands-on time

Pick one of your real clients (or use the demo domain we'll provide) and walk through:

1. `/scout {their-domain}` — get the diagnostic
2. Pick one finding from the action plan
3. Run the workflow that addresses it (`/run-seo`, `/run-gbp`, `/run-content`, etc.)
4. `/send-slack` or `/send-email` the result to a colleague

We'll circulate while you work — flag anyone who's stuck.

---

## Step 5 — Send and share

The toolkit ships with four send integrations. They're optional but worth wiring up:

```bash
/setup-integrations
```

Fills in `.env` for Slack, Discord, Resend (email), Circle. Each command (`/send-slack`, `/send-discord`, `/send-email`, `/send-circle`) becomes a one-liner you can chain after any workflow.

📎 Reference: [README.md § Share Results](../README.md#share-results)

---

## Resources

| | |
|---|---|
| Toolkit repo | [github.com/search-atlas-group/amm-toolkit](https://github.com/search-atlas-group/amm-toolkit) |
| MCP endpoint | `https://mcp.searchatlas.com/mcp` (620+ tools, OAuth 2.1) |
| MCP setup guide | [docs/MCP_SETUP.md](MCP_SETUP.md) |
| Tool reference | [docs/TOOL_REFERENCE.md](TOOL_REFERENCE.md) |
| Workflow guide | [docs/WORKFLOWS.md](WORKFLOWS.md) |
| Golden rules | [docs/GOLDEN_RULES.md](GOLDEN_RULES.md) |
| Intent mapping | [docs/INTENT_MAPPING.md](INTENT_MAPPING.md) |
| Windows specifics | [guides/windows-claude-code-setup.md](../guides/windows-claude-code-setup.md) |
| Security scanner | [guides/security-scan-guide.md](../guides/security-scan-guide.md) |
| What's new | [WHATS-NEW.md](../WHATS-NEW.md) |

### Using Claude Desktop instead of Claude Code?

The MCP works the same — `install-mcp.sh` writes Desktop's config automatically. You won't get slash commands or the Mission Control wizards (those are Claude Code features), but you get the same 620+ SearchAtlas tools. Copy-paste prompts that map to each slash command live in [docs/CLAUDE_DESKTOP_PROMPTS.md](CLAUDE_DESKTOP_PROMPTS.md).

---

## Troubleshooting on the day

| Symptom | Fix |
|---|---|
| `/my-account` fails with "Unauthorized" | Restart Claude Code, run any SA command, re-approve OAuth |
| Wizard card spinner never completes | Double-click `SearchAtlas Mission Control.command` on your Desktop |
| Welcome page never finds bridges | Same fix as above — the supervisor needs to be running on 8764 |
| `claude: command not found` after install | Open a new terminal window (PATH didn't reload in the current one) |
| Windows: `fetch failed` on first MCP call | See [guides/windows-claude-code-setup.md](../guides/windows-claude-code-setup.md) — WSL networking fix |

Internal team — full troubleshooting matrix in the support doc shared separately.

---

## After the workshop

- Run one workflow per real client per week — that's where the toolkit pays for itself
- Star + watch the repo: [github.com/search-atlas-group/amm-toolkit](https://github.com/search-atlas-group/amm-toolkit)
- Re-run the installer anytime to pick up new commands: same one-liner from the top of this doc
