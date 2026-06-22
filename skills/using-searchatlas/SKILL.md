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
3. **Poll async tasks.** Many operations return a task ID. Poll with `verify_task_status` (5–10s between polls), continue until `status = SUCCESS`.
4. **Verify tool names via schema discovery.** Tools are flat, per-operation (e.g. `otto_list_projects`, `bv_list`). If a tool behaves unexpectedly or isn't found, list the available SearchAtlas tools and verify the exact name via schema discovery.
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

| Tool family | "domain" param | "ID" param |
|---|---|---|
| `bv_*` (CRUD) | — | `brand_vault_uuid` |
| `bv_*` (read-only) | `hostname` (accepted as `identifier`) | — |
| `se_*` (Site Explorer) | `site_id` (from `se_list_sites`) | `site_id` |
| `se_get_holistic_seo_scores` | `domain` | — |
| `gbp_*` | — | `location_id` (integer) |
| `ppc_*` | — | `business_id`; account ops need `google_ads_account_id` + `google_ads_client_id` |
| `otto_*` | `project_identifier` (UUID or hostname) | `project_identifier` |

**Tip:** OTTO tools accept either a project UUID or a hostname as `project_identifier`; resolve a hostname to a UUID first with `otto_find_project_by_hostname` when an op requires the UUID. Brand-vault read tools also resolve a hostname to a UUID for you.

## 5. Account Discovery Flow

When a user asks about their account, gather in this order, then present a clean summary with counts and key metrics:
1. OTTO projects (`otto_list_projects`) · 2. Brand vaults (`bv_list`) · 3. GBP locations (`gbp_list_locations`) · 4. PPC (`ppc_list_businesses`, then `ppc_list_campaigns`) · 5. Content (`cg_list_articles`) · 6. LLM visibility (`llmv_list_projects`).

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
| "their keywords" / "what do they rank for" | `se_get_organic` (view='keywords') |
| "backlinks" | `se_get_links` |
| "SEO health" / "pillar scores" | `se_get_holistic_seo_scores` |
| "GBP profile" | `gbp_get_location` |
| "GBP stats / performance" | `gbp_get_location_metrics` (view='stats') |
| "brand vault / voice" | `bv_get_details` |
| "articles / content status" | `cg_get_article_summary` / `cg_list_articles` |
| "PPC / ad performance" | `ppc_list_campaigns` |
| "AI visibility / LLM mentions" | `llmv_get_overview` (view='brand') |
| "competitors" | `se_get_organic` (view='competitors') |
| "quota / how much left" | `get_quota` |

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
