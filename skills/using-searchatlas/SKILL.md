---
name: using-searchatlas
description: Foundational routing rules, golden rules, and parameter reference for the SearchAtlas toolkit. Use whenever the user works on SEO, Google Business Profile (GBP), PPC / Google Ads, content generation, AI/LLM visibility, backlinks, brand vaults, OTTO projects, or any SearchAtlas task — to route the request to the right /searchatlas:* command and apply correct MCP usage patterns (schema discovery, async polling, never hardcoding IDs).
user-invocable: false
---

# Using the SearchAtlas Toolkit

This skill loads automatically when the user does SearchAtlas-related work. It tells you how to route their request to the right `/searchatlas:*` command and how to use the SearchAtlas MCP correctly.

## 1. What This Plugin Is

The official SearchAtlas command-line toolkit — SEO, GBP, PPC, content, and AI visibility workflows through the SearchAtlas MCP. For anyone using SearchAtlas: solo SEOs managing their own brand, in-house teams handling multiple sites, and agencies managing clients.

## 2. MCP Server

**Endpoint:** `https://mcp.searchatlas.com/mcp` · **Auth:** OAuth 2.1 (Claude Code handles the flow; user authorizes via their SearchAtlas account on first use). The MCP exposes a large tool set across SEO, GBP, PPC, content, authority building, and LLM visibility. Use schema discovery to find the right tool — do not assume tool names from old documentation.

## 3. Golden Rules

1. **Schema discovery first.** Before calling any tool for the first time, send it with empty params `{}` to discover the real schema. Documentation may be outdated; the API response shows correct param names, types, and required fields.
2. **Read error messages.** Parameter Validation Error → wrong params (the error contains the schema). Internal Server Error → backend, retry later. 401 → OAuth expired, re-authorize. "Tool not found" → name changed, rediscover.
3. **Poll async tasks.** Many operations return a task ID. Poll with `get_otto_task_status` / `get_otto_ppc_task_status`, use `otto_wait` between polls (5–10s), continue until `status = SUCCESS`.
4. **Watch tool-name collisions.** Some short names map to multiple tools. If a tool behaves unexpectedly, try the full prefixed name (e.g. `otto_project_management`) and verify via schema discovery.
5. **Never hardcode IDs.** Discover project/location/business IDs via API first. Use `/searchatlas:my-account` to get the user's current resources before running workflows.
6. **Never expose secrets.** API keys come from `.env` or MCP config — never print them. When sharing results, include only public-safe data.
7. **Never hardcode paths.** Plugin assets (workflows, integrations, scripts) → `$CLAUDE_PLUGIN_ROOT`. User data → `$SA_CLIENTS_DIR` (defaults to `~/.searchatlas/clients/`, env-overridable). Never write a literal path with a username.
8. **Keep client data local.** Per-client working files live under `~/.searchatlas/clients/{slug}/`:
   - `brand-profile.md` — canonical identity, synced with the SearchAtlas brand vault
   - `notes.md` — freeform notes
   - `scouts/{date}.html` — `/searchatlas:scout` history
   - `reports/{date}.md` — `/searchatlas:business-report` outputs
   - `workflows/{type}-{date}.md` — `/searchatlas:run-*` logs
   - `shots/play-{NN}-{date}.md` — `/searchatlas:summit-shot` executions

## 4. Parameter Quick Reference

Param names are inconsistent across tools — **always use schema discovery first**. Common gotchas:

| Tool group | "domain" param | "ID" param |
|---|---|---|
| `brand_vault` (CRUD) | — | `brand_vault_uuid` |
| `brand_vault` (read-only) | `hostname` | — |
| `organic`, `backlinks`, `analysis` | `project_identifier` | `project_identifier` |
| `holistic_audit` | `domain` | — |
| `gbp_locations_crud` | — | `location_id` (integer) |
| `business_crud` | — | `google_ads_account_id` + `google_ads_client_id` |
| `project_management` | `project_id` (UUID) | `project_id` |

**Known collision:** `project_management` may resolve to content-project ops instead of OTTO. If you see `list_content_projects` instead of `list_otto_projects`, you hit the wrong tool — retry or use brand-vault data (it includes linked OTTO project IDs).

## 5. Account Discovery Flow

When a user asks about their account, gather in this order, then present a clean summary with counts and key metrics:
1. OTTO projects (`project_management` → list) · 2. Brand vaults (`brand_vault` → list) · 3. GBP locations (`gbp_locations` → list) · 4. PPC (`business_crud` → list businesses, then `campaign`) · 5. Content (`content` tools) · 6. LLM visibility (`ai_visibility` tools).

## 6. Intent Routing — Match Request to Command

When a user mentions a client, domain, project, or their own brand, route by how specific they are.

**Broad requests → full command:**

| User says… | Run |
|---|---|
| "scout {x}" / "audit {domain}" / "what does this client need" / "diagnostic" / "where do we start" | `/searchatlas:scout` — read-only diagnostic across all pillars, prioritized plan + Report Builder report + local HTML record |
| "run a play" / "summit shot" / "topical map play" | `/searchatlas:summit-shot` — atomic single-play executor (bounded: drafts by default). `/searchatlas:summit-shot {N}` for a direct play number |
| "tell me about {x}" / "look at this client/project/brand" / "deep dive" / "full report" | `/searchatlas:business-report` — OTTO, brand vault, content, Site Explorer, GBP, PPC, LLM visibility + recommendations |
| "show my account" / "what clients do I have" / "list everything" | `/searchatlas:my-account` |
| "set up a new client/project/brand/your own site" / "onboard {x}" | `/searchatlas:onboard-client` |
| "sync {x}" / "push to brand vault" / "pull from SA" / "brand profile out of date" | `/searchatlas:sync-client` |

**Specific requests → run only what they ask** (no full report):

| User says… | Tool path |
|---|---|
| "their keywords" / "what do they rank for" | `organic` → `get_organic_keywords` |
| "backlinks" | `backlinks` → `get_site_backlinks` + `get_site_referring_domains` |
| "SEO health" / "pillar scores" | `holistic_audit` → `get_holistic_seo_pillar_scores` |
| "GBP profile" | `gbp_locations_crud` → `get_location` |
| "GBP stats / performance" | `gbp_locations_crud` → `get_location_stats` |
| "brand vault / voice" | `brand_vault` → `retrieve_brand_vault_details` |
| "articles / content status" | `content_retrieval` → `get_article_summary` / `get_project_articles` |
| "PPC / ad performance" | `campaign` → `list_campaigns_with_metrics` |
| "AI visibility / LLM mentions" | `visibility` → `get_brand_overview` |
| "competitors" | `organic` → `get_organic_competitors` |
| "quota / how much left" | `quota_management` → `show_otto_quota` |

**Action requests → run the workflow:** "run SEO"/"monthly maintenance" → `/searchatlas:run-seo` · "optimize GBP" → `/searchatlas:run-gbp` · "launch ads"/"set up PPC" → `/searchatlas:run-ppc` · "create content"/"topical map" → `/searchatlas:run-content` · "press release"/"build authority" → `/searchatlas:run-pr` · "AI visibility audit" → `/searchatlas:run-visibility` · "post to Slack/Discord" → `/searchatlas:send-slack` / `send-discord` · "email the report" → `/searchatlas:send-email` · "post to Circle" → `/searchatlas:send-circle`.

**Rule of thumb:** vague about a client → give the full picture (`/searchatlas:business-report`). Specific ask → answer only that, don't flood them.

## 7. Workflow Execution Pattern

When running a `/searchatlas:run-*` workflow: load the YAML template from `$CLAUDE_PLUGIN_ROOT/workflows/`, ask which business to target (use account discovery), execute steps in order respecting `depends_on`, report each step with a status emoji, then summarize done/failed/next.

```
✅  Step Name     Result/count    [View →](link)
⏳  Step Name     In progress...
❌  Step Name     Error: description
```

## 8. Communication Integrations

Scripts live under `$CLAUDE_PLUGIN_ROOT/integrations/`. Slack (`SLACK_WEBHOOK_URL` + named `SLACK_WEBHOOK_{NAME}`), Discord (`DISCORD_WEBHOOK_URL`), Email via Resend (`RESEND_API_KEY` + `EMAIL_FROM`), Circle (`CIRCLE_API_KEY`). All optional; configured in `~/.searchatlas/.env` or via `/searchatlas:setup-integrations`.

## 9. Conventions

- **Never fabricate data** — if a tool call fails, report it honestly.
- **Confirm before destructive actions** — creating campaigns, publishing content, etc.
- **Use the workflow YAML templates** — don't improvise multi-step processes.
- **Keep output clean** — emoji + label + count/link, not verbose paragraphs.
- **Respect rate limits** — space out rapid calls, poll for async ops.
