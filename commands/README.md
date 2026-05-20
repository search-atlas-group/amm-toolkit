# Commands

Every slash command, organized by tier. Open any folder to see the full prompt spec for each command.

Claude Code reads `~/.claude/commands/` **flat** — to install these, copy every `.md` into that folder:

```bash
find commands -name '*.md' -not -name 'README.md' -exec cp {} ~/.claude/commands/ \;
```

The setup helpers ([`setup.sh`](../setup.sh), [`Scripts/install-mcp.sh`](../Scripts/install-mcp.sh)) do this automatically.

For Claude Desktop equivalents (copy-paste prompts), see [`docs/CLAUDE_DESKTOP_PROMPTS.md`](../docs/CLAUDE_DESKTOP_PROMPTS.md).

---

## [essentials/](essentials/) — Tier 1

The starting four. Run these on any client, anytime — they answer "what's going on?"

| Command | Spec | What it does |
|---|---|---|
| `/help` | [help.md](essentials/help.md) | List every available command |
| `/my-account` | [my-account.md](essentials/my-account.md) | Overview of every business, project, vault, location, campaign, content total, quota |
| `/scout {domain}` | [essentials/scout.md](essentials/scout.md) | Read-only diagnostic across all pillars → prioritized action plan + Report Builder report + local HTML |
| `/business-report {domain}` | [business-report.md](essentials/business-report.md) | Full deep-dive on a single business across every pillar |

---

## [workflows/](workflows/) — Tier 2

Each `/run-*` maps to a YAML pipeline in [`../workflows/`](../workflows/). Same steps, runnable from chat.

| Command | What it does |
|---|---|
| `/run-seo` | SEO onboarding or monthly maintenance (pillar scores, recommendations, schema deploys, indexing) |
| `/run-gbp` | Google Business Profile — optimization (first-time) or monthly (reviews, posts, performance) |
| `/run-ppc` | PPC campaign build + launch — business, products, keywords, ads, validation, send to Google Ads |
| `/run-content` | Topical map → 3 articles generated → graded → ready for publish |
| `/run-pr` | Press release write + distribute + cloud stack + digital PR outreach + backlink monitoring |
| `/run-visibility` | AI/LLM visibility audit — share of voice, sentiment trend, citations, competitor rank |

---

## [clients/](clients/) — Tier 2

Client lifecycle.

| Command | What it does |
|---|---|
| `/onboard-client` | Guided new-client setup — brand vault, OTTO project, GBP, PPC, AI visibility. Creates `clients/<slug>/`. |
| `/sync-client` | Two-way sync between local `brand-profile.md` and the SearchAtlas brand vault |
| `/summit-shot {N}` | Atomic single-play executor — 19 plays from the May Summit. Bounded scope (1 article, 1 PR, drafts). |

---

## [sharing/](sharing/) — Tier 2

Post results to your team's channels. Requires `/setup-integrations` first (or manual `.env`).

| Command | What it does |
|---|---|
| `/send-slack` | Post to Slack via incoming webhook (supports multiple named channels) |
| `/send-discord` | Post to Discord via webhook |
| `/send-email` | Send via Resend API (free: 100/day) |
| `/send-circle` | Post to a Circle community space |

---

## [advanced/](advanced/) — Tier 3

Heavier operations. Most have a [Mission Control](../mission-control/) web wizard equivalent.

| Command | What it does |
|---|---|
| `/build-website` | Greenfield site build — domain + a few fields → planned, designed, built, launched on Website Studio |
| `/rebuild-website` | Redesign existing site — consumes `/scout` output, page-by-page with link-equity preservation |
| `/setup-integrations` | One-time wizard to wire up Slack / Discord / email / Circle webhooks into `.env` |
| `/security-scan {url}` | 4-tier analysis (metadata, secrets, CVEs, SAST) before cloning or running unfamiliar repos |

---

## Conventions

- **`/clear` between clients** — context bleed is the #1 source of wrong-client mistakes
- **`/compact` when responses slow down** — proactively around 70% context
- **`/help` if you forget a command name** — lists everything
- **Schema discovery first** — if a tool behaves oddly, ask Claude to call it with empty params `{}` for the real schema
- **Confirm before destructive actions** — creating campaigns, publishing content, sending messages

Intent routing rubric (what to run when someone asks a vague question): [`../docs/INTENT_MAPPING.md`](../docs/INTENT_MAPPING.md).
