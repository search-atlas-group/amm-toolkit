# Agentic Marketing Mastermind — Claude Code Context

> This file provides context to Claude Code when working in this repository.

---

## 1. What This Repo Is

A public toolkit for digital marketing agencies using SearchAtlas. Users clone this repo, connect their SearchAtlas MCP, and use slash commands to manage clients and execute marketing workflows.

**This is NOT an internal tool.** No confidential data, no hardcoded keys, no internal references.

---

## 2. MCP Server Configuration

**Endpoint:** `https://mcp.searchatlas.com/mcp`

**Auth:** OAuth 2.1 — Claude Code handles the flow automatically. On first use, the user is redirected to authorize via their SearchAtlas account. No API key or manual config needed.

**Install:**
```bash
claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
```

**Protocol:** JSON-RPC 2.0 via Streamable HTTP. The MCP exposes a large set of tools covering SEO, GBP, PPC, content, authority building, LLM visibility, and more. Use schema discovery to find the right tool for any task — do not assume tool names from old documentation.

---

## 3. Golden Rules

### Rule 1: Schema Discovery First
Before calling ANY tool for the first time, send it with empty params `{}` to discover the real schema. Documentation may be outdated — the actual API response shows the correct parameter names, types, and required fields.

```
Example: Call tool with op: "help" and params: {} to see all operations
Then call with the specific op and params: {} to see that operation's schema
```

### Rule 2: Read Error Messages
- **Parameter Validation Error** → Wrong params. The error response contains the correct schema.
- **Internal Server Error** → Backend issue, not your fault. Retry later.
- **401 Unauthorized** → OAuth token expired. Re-authorize when prompted or restart Claude Code.
- **"Tool not found"** → Tool name changed. Run discovery again.

### Rule 3: Poll Async Tasks
Many operations return a task ID instead of immediate results. Poll for completion:
- Use `get_otto_task_status` or `get_otto_ppc_task_status` to check status
- Use `otto_wait` between polls (5-10 second intervals)
- Continue polling until `status = SUCCESS`

### Rule 4: Watch for Tool Name Collisions
Some short tool names map to multiple underlying tools. If a tool behaves unexpectedly:
- Try the full prefixed name (e.g., `otto_project_management` instead of `project_management`)
- Use schema discovery to verify which tool you're actually calling

### Rule 5: Never Hardcode IDs
- Project IDs, location IDs, business IDs — always discover them via API first
- Use `/my-account` to get the user's current resources before running workflows

### Rule 6: Never Expose Secrets
- API keys come from `.env` or MCP config — never print them
- When sharing results (Slack, Circle), only include public-safe data

### Rule 7: Never Hardcode the Workspace Path
The toolkit is cloned to a user-chosen location — never assume a path like `~/Desktop/amm-toolkit` or any absolute path with a username or folder name.

- **Shell scripts** → resolve at runtime: `AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)`
- **Slash commands** (`.md` files in `commands/`) → same `AMM_ROOT` pattern in every bash block
- **HTML / static UI** → use the literal placeholder `__TOOLKIT_PATH__`; `setup.sh` stamps the real path at install time via `sed`
- **Never** write a literal path like `/Users/anyone/...` or `~/Desktop/anything`

---

## 4. Parameter Quick Reference

Parameter names are inconsistent across tools. **Always use schema discovery** (call with `params: {}` first), but here are the most common gotchas:

| Tool Group | Param for "domain" | Param for "ID" |
|------------|-------------------|----------------|
| `brand_vault` (CRUD) | — | `brand_vault_uuid` |
| `brand_vault` (read-only) | `hostname` | — |
| `organic`, `backlinks`, `analysis` | `project_identifier` | `project_identifier` |
| `holistic_audit` | `domain` | — |
| `gbp_locations_crud` | — | `location_id` (integer) |
| `business_crud` | — | `google_ads_account_id` + `google_ads_client_id` (for list) |
| `project_management` | `project_id` (UUID) | `project_id` |

**Known collision:** `project_management` may resolve to content project operations instead of OTTO operations. If you see `list_content_projects` instead of `list_otto_projects`, you've hit the wrong tool. Retry or use alternative discovery paths (brand vault data includes linked OTTO project IDs).

---

## 5. Account Discovery Flow

When a user asks about their account, follow this order:

1. **OTTO Projects** — Call `project_management` → list all projects (domains, health scores)
2. **Brand Vaults** — Call `brand_vault` → list vaults (brand identity, assets)
3. **GBP Locations** — Call `gbp_locations` → list connected locations
4. **PPC Campaigns** — Call `business_crud` → list businesses, then `campaign` → list campaigns
5. **Content** — Call `content` tools to see articles, topical maps
6. **LLM Visibility** — Call `ai_visibility` tools for brand monitoring

Present results as a clean summary with counts and key metrics.

---

## 6. Intent Routing — Match User Request to Command

When a user mentions a client or domain, route to the right command based on how specific they are.

### Broad requests → Run the full command

| User says… | Run |
|------------|-----|
| "tell me about {client}" / "look at this client" / "what do we have for {domain}" / "deep dive" / "full report" | **`/business-report`** — pulls OTTO, brand vault, content, Site Explorer, GBP, PPC, LLM visibility, and gives recommendations |
| "show me my account" / "what clients do I have" / "list everything" | **`/my-account`** — all businesses, projects, campaigns, GBP locations, quota |
| "set up a new client" / "onboard {client}" | **`/onboard-client`** — guided wizard |
| "sync {client}" / "push to brand vault" / "pull from SA" / "brand profile out of date" | **`/sync-client`** — two-way brand vault sync |

### Specific requests → Run only what they ask for

| User says… | Run directly (no full report) |
|------------|-------------------------------|
| "show me their keywords" / "what do they rank for" | `organic` → `get_organic_keywords` |
| "check their backlinks" | `backlinks` → `get_site_backlinks` + `get_site_referring_domains` |
| "SEO health" / "pillar scores" | `holistic_audit` → `get_holistic_seo_pillar_scores` |
| "GBP profile" / "Google Business" | `gbp_locations_crud` → `get_location` |
| "GBP stats" / "GBP performance" | `gbp_locations_crud` → `get_location_stats` |
| "brand vault" / "brand voice" | `brand_vault` → `retrieve_brand_vault_details` |
| "articles" / "content status" | `content_retrieval` → `get_article_summary` or `get_project_articles` |
| "PPC campaigns" / "ad performance" | `campaign` → `list_campaigns_with_metrics` |
| "AI visibility" / "LLM mentions" | `visibility` → `get_brand_overview` |
| "competitors" | `organic` → `get_organic_competitors` |
| "quota" / "how much do I have left" | `quota_management` → `show_otto_quota` |

### Action requests → Run the workflow

| User says… | Run |
|------------|-----|
| "run SEO" / "do SEO for {client}" / "monthly maintenance" | **`/run-seo`** |
| "optimize their GBP" / "fix their Google profile" | **`/run-gbp`** |
| "launch ads" / "set up PPC" / "Google Ads campaign" | **`/run-ppc`** |
| "create content" / "write articles" / "build topical map" | **`/run-content`** |
| "press release" / "build authority" / "link building" | **`/run-pr`** |
| "check AI visibility" / "LLM audit" | **`/run-visibility`** |
| "post to Slack" / "share results on Slack" | **`/send-slack`** |
| "post to Discord" / "share on Discord" | **`/send-discord`** |
| "email the report" / "send an email" | **`/send-email`** |
| "post to Circle" | **`/send-circle`** |

**Rule of thumb:** If the user is vague about a client, give them the full picture (`/business-report`). If they ask for something specific, don't flood them with everything — just answer what they asked.

---

## 7. Workflow Execution Pattern

When running a workflow (e.g., `/run-seo`):

1. **Load the YAML template** from `workflows/`
2. **Ask which business** the user wants to target (use account discovery)
3. **Execute steps in order**, respecting `depends_on` declarations
4. **Report results** at each step with emoji status indicators
5. **Summarize** what was completed, what failed, and next steps

**Output format:**
```
✅  Step Name     Result/count    [View →](link)
⏳  Step Name     In progress...
❌  Step Name     Error: description
```

---

## 8. Slash Commands

All commands live in `commands/` as markdown files. They are installed to `~/.claude/commands/` via `setup.sh`.

| Command | File | Purpose |
|---------|------|---------|
| `/onboard-client` | `commands/onboard-client.md` | Core onboarding wizard (brand vault pull or manual) |
| `/sync-client` | `commands/sync-client.md` | Two-way sync: brand-profile.md ↔ SA brand vault |
| `/my-account` | `commands/my-account.md` | Account overview |
| `/business-report` | `commands/business-report.md` | Single business deep dive |
| `/run-seo` | `commands/run-seo.md` | SEO workflow |
| `/run-gbp` | `commands/run-gbp.md` | GBP workflow |
| `/run-ppc` | `commands/run-ppc.md` | PPC workflow |
| `/run-content` | `commands/run-content.md` | Content generation |
| `/run-pr` | `commands/run-pr.md` | Press releases |
| `/run-visibility` | `commands/run-visibility.md` | LLM visibility |
| `/send-slack` | `commands/send-slack.md` | Slack integration (multi-channel) |
| `/send-discord` | `commands/send-discord.md` | Discord integration |
| `/send-email` | `commands/send-email.md` | Email via Resend |
| `/send-circle` | `commands/send-circle.md` | Circle integration |
| `/help` | `commands/help.md` | Command listing |

---

## 9. Communication Integrations

### Slack (multi-channel)
Uses Incoming Webhooks. Supports multiple named channels via env var convention:
- `SLACK_WEBHOOK_URL` — default channel
- `SLACK_WEBHOOK_{NAME}` — named channels (e.g., `SLACK_WEBHOOK_SEO`, `SLACK_WEBHOOK_PPC`)

Script: `integrations/slack/send-message.sh`

### Discord
Uses Discord Webhooks. The webhook URL is stored in `.env` as `DISCORD_WEBHOOK_URL`.
Script: `integrations/discord/send-message.sh`

### Email (Resend)
Uses the Resend REST API. Free tier: 100 emails/day.
- `RESEND_API_KEY` — API key from resend.com
- `EMAIL_FROM` — sender address (must verify domain, or use `onboarding@resend.dev` for testing)

Script: `integrations/email/send-email.sh`

### Circle
Uses Circle API v2. API key stored in `.env` as `CIRCLE_API_KEY`.
Script: `integrations/circle/post-to-space.sh`

---

## 10. Important Conventions

- **Never fabricate data** — If a tool call fails, report the failure honestly
- **Always confirm before destructive actions** — Creating campaigns, publishing content, etc.
- **Use the workflow YAML templates** — Don't improvise multi-step processes
- **Keep output clean** — Use emoji + label + count/link format, not verbose paragraphs
- **Respect rate limits** — Space out rapid API calls, use polling for async operations
