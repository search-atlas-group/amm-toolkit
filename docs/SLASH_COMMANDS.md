# Slash Commands

Every command that ships with the toolkit, organized by purpose. They run in Claude Code (`/scout`, `/run-seo`, etc.). For Claude Desktop equivalents, see [CLAUDE_DESKTOP_PROMPTS.md](CLAUDE_DESKTOP_PROMPTS.md).

The full spec for any command lives in [`commands/<tier>/<name>.md`](../commands/) — open it to see phases, inputs, outputs, and the SA tools each step calls.

---

## Start here

| Command | What it does |
|---|---|
| [`/help`](../commands/essentials/help.md) | List every available command |
| [`/my-account`](../commands/essentials/my-account.md) | Overview of every business, OTTO project, brand vault, GBP location, campaign, content total, and quota in your SearchAtlas account |
| [`/setup-integrations`](../commands/advanced/setup-integrations.md) | One-time wizard to wire up Slack / Discord / email / Circle webhooks into `.env` |

---

## Diagnose + plan

| Command | What it does |
|---|---|
| [`/scout {domain}`](../commands/essentials/scout.md) | **Read-only** diagnostic across all 8 pillars → prioritized action plan + SA Report Builder report + self-contained local HTML at `clients/{slug}/scout/{date}/index.html` |
| [`/business-report {domain}`](../commands/essentials/business-report.md) | Full deep-dive on a single business: OTTO, brand vault, content, Site Explorer, GBP, PPC, AI visibility |

Use `/scout` first on any new domain — it tells you which other commands to run.

---

## Onboard + sync clients

| Command | What it does |
|---|---|
| [`/onboard-client`](../commands/clients/onboard-client.md) | Guided new-client setup: brand vault, OTTO project, GBP, PPC, AI visibility — creates `clients/<slug>/CLAUDE.md` + `brand-profile.md` |
| [`/sync-client`](../commands/clients/sync-client.md) | Two-way sync between local `brand-profile.md` and the SearchAtlas brand vault. Pushes local edits, pulls SA changes, surfaces conflicts. |

---

## Run a workflow

Each maps to a `workflows/*.yaml` template — same steps the YAML defines, just from chat.

| Command | What it does |
|---|---|
| [`/run-seo`](../commands/workflows/run-seo.md) | SEO onboarding or monthly maintenance — pillar scores, recommendations, schema deploys, indexing |
| [`/run-gbp`](../commands/workflows/run-gbp.md) | Google Business Profile: optimization (first-time) or monthly (reviews, posts, performance) |
| [`/run-ppc`](../commands/workflows/run-ppc.md) | PPC campaign build + launch — business, products, keywords, ads, validation, send to Google Ads |
| [`/run-content`](../commands/workflows/run-content.md) | Topical map → 3 articles generated → graded → ready for publish |
| [`/run-pr`](../commands/workflows/run-pr.md) | Press release write + distribute + cloud stack + digital PR outreach + backlink monitoring |
| [`/run-visibility`](../commands/workflows/run-visibility.md) | AI/LLM visibility audit: share of voice, sentiment trend, citations, competitor rank |

---

## One-shot plays — `/summit-shot`

[`/summit-shot {N}`](../commands/clients/summit-shot.md) — Atomic single-play executor. 19 plays from the May Summit. Each is bounded (1 article, 1 PR, drafts not auto-deploys). Pair with `/scout` — scout says *what to run*, summit-shot *runs it*.

| # | Play | Use when |
|---|---|---|
| 1 | Brand Vault Setup | Vault exists but voice profile inactive |
| 4 | LLM Visibility Setup | Not monitoring AI visibility yet |
| 5 | Topical Map | Content plan missing; < 5 keywords ranking pos 1-3 |
| 7 | Blog Article | Have map, need next article |
| 8 | GBP Optimize | GBP missing or underutilized |
| 9 | PR Blast | Authority pillar < 40 or < 25 referring domains |
| 10 | Cloudstack | Stacking authority signals after a PR |
| 14 | Branded Google Ads (draft) | Strong organic, no paid presence yet |
| 17–19 | Day-5 LLM deep dive | Brand monitored but share of voice < 30% |

Full play list and rubric in [`commands/clients/summit-shot.md`](../commands/clients/summit-shot.md).

---

## Website build + rebuild

Same workflows as the Mission Control web wizards, runnable from chat.

| Command | What it does |
|---|---|
| [`/build-website`](../commands/advanced/build-website.md) | Greenfield site build — domain + a few fields → planned, designed, built, launched on Website Studio |
| [`/rebuild-website`](../commands/advanced/rebuild-website.md) | Redesign an existing site — consumes `/scout` output, executes page-by-page with link-equity preservation |

For the web UI versions, see [POWER-USER.md § Mission Control](../POWER-USER.md#mission-control--web-wizards).

---

## Share results

Each command takes the most recent workflow output and sends it. Requires `/setup-integrations` first (or manual `.env` config).

| Command | What it does |
|---|---|
| [`/send-slack`](../commands/sharing/send-slack.md) | Post to a Slack channel via incoming webhook. Supports multiple named channels via `SLACK_WEBHOOK_<NAME>` env vars. |
| [`/send-discord`](../commands/sharing/send-discord.md) | Post to a Discord channel via webhook |
| [`/send-email`](../commands/sharing/send-email.md) | Send via Resend (free: 100/day). Requires `RESEND_API_KEY` + `EMAIL_FROM`. |
| [`/send-circle`](../commands/sharing/send-circle.md) | Post to a Circle community space via API v2 |

---

## Security

| Command | What it does |
|---|---|
| [`/security-scan <github-url>`](../commands/advanced/security-scan.md) | 4-tier analysis (metadata, secrets, CVEs, SAST) + optional behavioral sandbox → plain-English verdict before you clone or run anything |

Walkthrough: [guides/security-scan-guide.md](../guides/security-scan-guide.md).

---

## Conventions

- **Run `/clear` between clients** — context bleed across clients is the #1 source of wrong-client mistakes.
- **`/compact` when responses slow down** — or proactively around 70% context.
- **Use `/help` if you forget a command name** — it lists everything.
- **Schema discovery first** — if a command behaves oddly, ask Claude to call the underlying tool with empty params (`{}`) to see the real API schema.
- **Confirm before destructive actions** — creating campaigns, publishing content, sending messages. Commands surface these for approval by default.

For the full intent-routing rubric (what slash command runs when someone asks a vague question), see [INTENT_MAPPING.md](INTENT_MAPPING.md).
