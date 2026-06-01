# SearchAtlas Toolkit

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                          ·   ✦
 ____                      _        _   _   _      ·
/ ___|  ___  __ _ _ __ ___| |__    / \ | |_| | __ _ ___
\___ \ / _ \/ _` | '__/ __| '_ \  / _ \| __| |/ _` / __|
 ___) |  __/ (_| | | | (__| | | |/ ___ \ |_| | (_| \__ \
|____/ \___|\__,_|_|  \___|_| |_/_/   \_\__|_|\__,_|___/   ✦

  ✦  /\_/\     SEO · GBP · PPC · Content · AI Visibility
    ( o.o )    Powered by the SearchAtlas MCP — auto-connected
     >   <     21 commands ready  ·  /searchatlas:help
    (")_(")              ·   ✦
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> Official command-line toolkit for SearchAtlas — SEO, GBP, PPC, content, and AI visibility, all powered by the SearchAtlas MCP.

> ### 👉 New here? [**Open the visual Quick Start guide →**](https://htmlpreview.github.io/?https://github.com/search-atlas-group/amm-toolkit/blob/main/docs/get-started.html)
> Connect SearchAtlas to **Claude Desktop** (no code) or **Claude Code** in a few minutes — step-by-step, with screenshots-level detail and troubleshooting. No need to read the rest of this page.

For anyone using SearchAtlas to manage SEO, Google Business Profiles, paid ads, content, or AI visibility — solo operators, in-house teams, and agencies alike.

---

## Quickstart

**[→ Full visual setup guide](https://htmlpreview.github.io/?https://github.com/search-atlas-group/amm-toolkit/blob/main/docs/get-started.html)** — step-by-step for both clients, with troubleshooting, updating, and the all-important per-chat connector tip. Best for first-time setup.

The short version:

**Claude Code** — install the plugin, then **restart Claude Code**:

```
/plugin marketplace add https://github.com/search-atlas-group/amm-toolkit.git
/plugin install searchatlas
```

**Claude Desktop, claude.ai, or Cowork** — plugins are Claude Code-only, so add the MCP as a custom connector (Settings → Connectors → Add custom connector):

```
https://mcp.searchatlas.com/mcp
```

The first SearchAtlas tool call prompts a one-time OAuth sign-in (create a free account then if you need one). Updating and troubleshooting are covered in the [guide](https://htmlpreview.github.io/?https://github.com/search-atlas-group/amm-toolkit/blob/main/docs/get-started.html).

---

## What You Get

21 slash commands covering the full SearchAtlas surface. Type `/searchatlas:help` once installed for the live list.

### Diagnostics & Reports
- `/searchatlas:scout` — Read-only diagnostic across SEO, GBP, PPC, content, AI visibility
- `/searchatlas:business-report` — Single-business deep dive (OTTO, brand vault, Site Explorer, GBP, PPC, LLM visibility)
- `/searchatlas:my-account` — Overview of all your SearchAtlas projects, brands, campaigns

### Onboarding & Brand Management
- `/searchatlas:onboard-client` — Guided setup wizard (brand vault import or manual)
- `/searchatlas:sync-client` — Two-way sync between local brand profile and SearchAtlas brand vault

### Marketing Workflows
- `/searchatlas:run-seo` — Monthly SEO audit + recommendations
- `/searchatlas:run-gbp` — GBP optimization workflow
- `/searchatlas:run-ppc` — Google Ads setup and maintenance
- `/searchatlas:run-content` — Content generation via SearchAtlas Content Genius
- `/searchatlas:run-pr` — Press release drafting + distribution via SearchAtlas Press
- `/searchatlas:run-visibility` — AI visibility audit (ChatGPT, Claude, Gemini, Perplexity)
- `/searchatlas:summit-shot` — Execute single high-impact plays from the Summit playbook

### Sharing & Notifications
- `/searchatlas:send-slack`, `/searchatlas:send-discord`, `/searchatlas:send-email`, `/searchatlas:send-circle`

### Setup & Utilities
- `/searchatlas:setup-integrations` — Configure Slack/Discord/Email/Circle webhooks
- `/searchatlas:security-scan` — Scan local setup for exposed secrets
- `/searchatlas:build-website`, `/searchatlas:rebuild-website` — Marketing site generation
- `/searchatlas:help` — Command reference

---

## Your Client Data

Per-client working files live at `~/.searchatlas/clients/{slug}/`:

```
~/.searchatlas/clients/acme-co/
├── brand-profile.md       # canonical client identity (synced with SA brand vault)
├── notes.md               # freeform notes
├── scouts/                # /searchatlas:scout reports
├── reports/               # /searchatlas:business-report outputs
├── workflows/             # /searchatlas:run-* logs
└── shots/                 # /searchatlas:summit-shot executions
```

Want client data on a synced drive (Dropbox, iCloud, etc.)? Set `SA_CLIENTS_DIR=/path/to/your/folder` in your environment.

---

## Integrations (Optional)

The `/searchatlas:send-*` commands need webhooks/keys. Configure once via `/searchatlas:setup-integrations`, or manually in `~/.searchatlas/.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
RESEND_API_KEY=re_...
EMAIL_FROM=you@yourdomain.com
CIRCLE_API_KEY=...
```

---

## Migrating From the Cloned-Repo Toolkit

Already using the cloned-and-scripted version? One command:

```bash
cd /path/to/your/toolkit-public
./Scripts/migrate-to-plugin.sh
```

It moves your client data into `~/.searchatlas/clients/` with the new subfolder layout, removes old commands, removes the auto-update hook, and declares the plugin in your `~/.claude/settings.json`. Next time you open Claude Code, you'll get a one-click trust prompt to finish installing.

If you've already deleted the cloned repo, just run the standard install at the top of this README — the plugin's first-run hook can detect orphaned client data and offer to relocate it.

---

## Companion: Mission Control

`mission-control/` (in this repo) is an optional local web dashboard for the toolkit. It runs alongside Claude Code and is NOT part of the plugin. See [`mission-control/README.md`](mission-control/README.md) for setup if you want it.

---

## Troubleshooting

- **MCP not registered after install** → Restart Claude Code. The plugin's MCP declaration loads on next session start.
- **OAuth flow stuck** → Sign in at https://searchatlas.com first, then retry the command.
- **Commands write to wrong location** → Check `echo $SA_CLIENTS_DIR` — if set, it overrides the default `~/.searchatlas/clients/`.
- **Hook says "MCP not registered"** → Run `claude mcp list` to verify; if `searchatlas` isn't there, reinstall the plugin.

---

## Support

- Issues: https://github.com/search-atlas-group/amm-toolkit/issues
- SearchAtlas help: https://help.searchatlas.com
