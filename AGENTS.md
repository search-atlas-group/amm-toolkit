# SearchAtlas Toolkit — Plugin Instructions for Claude

> This file is loaded automatically by Claude Code when the `searchatlas-toolkit` plugin is active. It provides routing rules, golden rules, parameter references, and the full command surface.

---

## 1. What This Plugin Is

The official SearchAtlas command-line toolkit — a Claude Code plugin (`searchatlas-toolkit`) that delivers SEO, GBP, PPC, content, and AI visibility workflows through the SearchAtlas MCP. For anyone using SearchAtlas: solo SEOs managing their own brand, in-house teams handling multiple sites, and agencies managing clients.

No confidential data, no hardcoded keys, no environment-specific paths — everything works on any user's machine after `/plugin install searchatlas-toolkit`.

---

## 2. MCP Server Configuration

**Endpoint:** `https://mcp.searchatlas.com/mcp`

**Auth:** OAuth 2.1 — Claude Code handles the flow automatically. On first use, the user is redirected to authorize via their SearchAtlas account. No API key or manual config needed.

**Install (Claude Code users):** Handled by the plugin manifest — no separate step needed.

**Install (Claude Desktop / claude.ai users — MCP only, no slash commands):**
`claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp`

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
- Use `/sa-my-account` to get the user's current resources before running workflows

### Rule 6: Never Expose Secrets
- API keys come from `.env` or MCP config — never print them
- When sharing results (Slack, Circle), only include public-safe data

### Rule 7: Never Hardcode Paths
The plugin's install location is managed by Claude Code. User data lives separately.

- **Plugin assets** (workflows, integrations, scripts) → resolve via `$CLAUDE_PLUGIN_ROOT` (Claude Code sets this at runtime when invoking hooks and command bodies)
- **User data** (per-client working files) → resolve via `$SA_CLIENTS_DIR`, which defaults to `~/.searchatlas/clients/` and can be overridden via the env var
- **Never** write a literal path like `/Users/anyone/...` or `~/Desktop/anything`

### Rule 8: Keep Client Data Local
The `~/.searchatlas/clients/` directory is for per-client working files (brand profiles, scout reports, notes). Each client gets a slug-named subdirectory. Accumulating artifacts (scout reports, workflow logs, summit-shot executions) go in their own subfolders to keep the top level clean:

- `~/.searchatlas/clients/{slug}/brand-profile.md` — canonical identity, synced with SearchAtlas brand vault
- `~/.searchatlas/clients/{slug}/notes.md` — freeform user notes
- `~/.searchatlas/clients/{slug}/scouts/{date}.html` — `/sa-scout` history
- `~/.searchatlas/clients/{slug}/reports/{date}.md` — `/sa-business-report` outputs
- `~/.searchatlas/clients/{slug}/workflows/{type}-{date}.md` — workflow run logs (`/sa-run-*`)
- `~/.searchatlas/clients/{slug}/shots/play-{NN}-{date}.md` — `/sa-summit-shot` executions

Client data is owned by the user, never by the plugin.

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

When a user mentions a client, domain, project, or their own brand, route to the right command based on how specific they are.

### Broad requests → Run the full command

| User says… | Run |
|------------|-----|
| "scout {client}" / "audit {domain}" / "what does this client need" / "where do we start with {client}" / "diagnostic" | **`/sa-scout`** — read-only diagnostic across all pillars, returns prioritized action plan + creates SA Report Builder report + saves local HTML internal record |
| "run a play" / "summit shot" / "what did we learn at the summit" / "run the topical map play" | **`/sa-summit-shot`** — atomic single-play executor (bounded: 1 article, 1 PR, drafts by default). Use `/sa-summit-shot {N}` for direct play number. |
| "tell me about {client}" / "look at this client / project / brand" / "what do we have for {domain}" / "deep dive" / "full report" | **`/sa-business-report`** — pulls OTTO, brand vault, content, Site Explorer, GBP, PPC, LLM visibility, and gives recommendations |
| "show me my account" / "what clients do I have" / "list everything" | **`/sa-my-account`** — all businesses, projects, campaigns, GBP locations, quota |
| "set up a new client / project / brand / your own site" / "onboard {client}" | **`/sa-onboard-client`** — guided wizard |
| "sync {client} / project" / "push to brand vault" / "pull from SA" / "brand profile out of date" | **`/sa-sync-client`** — two-way brand vault sync |

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
| "run SEO" / "do SEO for {client}" / "monthly maintenance" | **`/sa-run-seo`** |
| "optimize their GBP" / "fix their Google profile" | **`/sa-run-gbp`** |
| "launch ads" / "set up PPC" / "Google Ads campaign" | **`/sa-run-ppc`** |
| "create content" / "write articles" / "build topical map" | **`/sa-run-content`** |
| "press release" / "build authority" / "link building" | **`/sa-run-pr`** |
| "check AI visibility" / "LLM audit" | **`/sa-run-visibility`** |
| "post to Slack" / "share results on Slack" | **`/sa-send-slack`** |
| "post to Discord" / "share on Discord" | **`/sa-send-discord`** |
| "email the report" / "send an email" | **`/sa-send-email`** |
| "post to Circle" | **`/sa-send-circle`** |

**Rule of thumb:** If the user is vague about a client, give them the full picture (`/sa-business-report`). If they ask for something specific, don't flood them with everything — just answer what they asked.

---

## 7. Workflow Execution Pattern

When running a workflow (e.g., `/sa-run-seo`):

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

## 8. Plugin Surface — Slash Commands

All commands live in `commands/` and are loaded automatically when the plugin is active.

### Diagnostics & Reports
| Command | SearchAtlas capabilities used |
|---|---|
| `/sa-scout` | Holistic SEO scoring, Site Explorer, GBP audit, AI visibility (full diagnostic) |
| `/sa-business-report` | OTTO project data, brand vault, Site Explorer, GBP, PPC, LLM visibility |
| `/sa-my-account` | All OTTO projects, brand vaults, GBP locations, PPC campaigns, content, AI visibility |

### Onboarding & Brand Management
| Command | SearchAtlas capabilities used |
|---|---|
| `/sa-onboard-client` | Brand vault creation/import, OTTO project setup, knowledge graph |
| `/sa-sync-client` | Brand vault two-way sync |

### Marketing Workflows
| Command | SearchAtlas capabilities used |
|---|---|
| `/sa-run-seo` | Holistic audit, OTTO recommendations, content health, indexer, keyword tracking |
| `/sa-run-gbp` | Location audit, posts, reviews automation, citations, photo management |
| `/sa-run-ppc` | Google Ads sync, keyword clusters, ad generation, performance review |
| `/sa-run-content` | Content Genius — topical maps, article drafting, brand-vault voice |
| `/sa-run-pr` | Press release drafting + distribution via SearchAtlas Press |
| `/sa-run-visibility` | LLM Visibility — mentions across ChatGPT/Claude/Gemini/Perplexity |
| `/sa-summit-shot` | Atomic single-play executor — 19 plays from the Summit playbook |

### Sharing & Notifications
| Command | Integration |
|---|---|
| `/sa-send-slack` | Slack Incoming Webhooks (multi-channel via `SLACK_WEBHOOK_{NAME}` env vars) |
| `/sa-send-discord` | Discord webhook |
| `/sa-send-email` | Resend REST API |
| `/sa-send-circle` | Circle API v2 |

### Setup & Utilities
| Command | Purpose |
|---|---|
| `/sa-setup-integrations` | Configure Slack/Discord/Email/Circle webhooks in `.env` |
| `/sa-security-scan` | Scan local setup for exposed secrets, misconfigured webhooks |
| `/sa-build-website` | Generate marketing site via SearchAtlas Website Studio |
| `/sa-rebuild-website` | Refresh/regenerate existing website |
| `/sa-help` | Command reference (this listing) |

---

## 9. Communication Integrations

### Slack (multi-channel)
Uses Incoming Webhooks. Supports multiple named channels via env var convention:
- `SLACK_WEBHOOK_URL` — default channel
- `SLACK_WEBHOOK_{NAME}` — named channels (e.g., `SLACK_WEBHOOK_SEO`, `SLACK_WEBHOOK_PPC`)

Script: `$CLAUDE_PLUGIN_ROOT/integrations/slack/send-message.sh`

### Discord
Uses Discord Webhooks. The webhook URL is stored in `.env` as `DISCORD_WEBHOOK_URL`.
Script: `$CLAUDE_PLUGIN_ROOT/integrations/discord/send-message.sh`

### Email (Resend)
Uses the Resend REST API. Free tier: 100 emails/day.
- `RESEND_API_KEY` — API key from resend.com
- `EMAIL_FROM` — sender address (must verify domain, or use `onboarding@resend.dev` for testing)

Script: `$CLAUDE_PLUGIN_ROOT/integrations/email/send-email.sh`

### Circle
Uses Circle API v2. API key stored in `.env` as `CIRCLE_API_KEY`.
Script: `$CLAUDE_PLUGIN_ROOT/integrations/circle/post-to-space.sh`

---

## 10. Important Conventions

- **Never fabricate data** — If a tool call fails, report the failure honestly
- **Always confirm before destructive actions** — Creating campaigns, publishing content, etc.
- **Use the workflow YAML templates** — Don't improvise multi-step processes
- **Keep output clean** — Use emoji + label + count/link format, not verbose paragraphs
- **Respect rate limits** — Space out rapid API calls, use polling for async operations
