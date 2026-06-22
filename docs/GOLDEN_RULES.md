# Golden Rules

Hard-won rules for reliable SearchAtlas MCP tool usage. Follow these to avoid common pitfalls.

---

## Rule 1: Schema Discovery First

**Before calling ANY tool for the first time**, send it with empty params `{}` to discover the real schema.

Documentation may be outdated — the actual API response shows the correct parameter names, types, and required fields.

```
Step 1: Ask Claude to list the available SearchAtlas tools to find the right flat tool
Step 2: Call the tool with empty params {} to see its schema (param names, types, required fields)
```

**Why this matters:** Tool schemas evolve. A parameter named `project_id` in docs might actually be `otto_project_id` in the API. Discovery prevents wasted calls.

---

## Rule 2: Read Error Messages Carefully

Error responses contain the information you need to fix the call:

| Error | What it means | What to do |
|-------|--------------|------------|
| **Parameter Validation Error** | Wrong params | The error response contains the correct schema — read it |
| **Internal Server Error** | Backend issue | Not your fault. Wait and retry |
| **"credentials not provided"** | Auth issue | Check API key in MCP config |
| **"Tool not found"** | Name changed | Run schema discovery again |
| **"404"** | Resource doesn't exist | Verify the ID — discover it via list/search first |

---

## Rule 3: Poll Async Tasks

Many operations return a **task ID** instead of immediate results. You must poll for completion.

**OTTO SEO tasks:**
```
1. Call the operation → receive task_id
2. Call verify_task_status with the task_id
3. If status != SUCCESS, wait 5-10 seconds
4. Repeat steps 2-3 (poll verify_task_status until SUCCESS)
5. Read the result from the task response
```

**OTTO PPC tasks:**
```
1. Call the operation → receive task_id
2. Call verify_task_status with the task_id
3. If not complete, wait 5-10 seconds
4. Repeat (poll verify_task_status until SUCCESS)
```

**Content generation:**
```
1. cg_start_information_retrieval → poll via cg_wait_for_task (until completed)
2. cg_start_headings_outline → poll via cg_wait_for_task (until completed)
3. cg_generate_complete_article
```

**Common mistake:** Assuming an operation completed instantly. Always check the response — if it returns a task ID, you need to poll.

---

## Rule 4: Verify Exact Flat Tool Names

Tools are now **flat and unique per operation** — there is one tool name per action, so the old grouped-dispatcher collisions no longer apply. If a call fails or behaves oddly:

1. Use schema discovery to confirm the exact flat tool name and its params
2. Check the operation actually exists — a typo'd name will return "Tool not found"
3. Pick the precise per-op tool rather than guessing

**Names are now flat & unique** (no more short-name ambiguity):
- Project ops are explicit: `otto_list_projects`, `otto_get_project_details`, etc.
- Press release vs cloud stack are distinct prefixes: `pr_*` vs `cs_*`
- Content ops live under `cg_*` (e.g. `cg_list_articles`, `cg_push_article`)

---

## Rule 5: Never Hardcode IDs

Project IDs, location IDs, business IDs, brand vault IDs — **always discover them via API first.**

```
Bad:  Use project_id: "12345" (hardcoded)
Good: Call otto_list_projects → find the project → use the returned ID
```

IDs can change when resources are recreated, and differ between accounts. Always use the discovery → action pattern.

---

## Rule 6: Never Expose Secrets

- API keys come from `.env` or MCP config — **never print them in output**
- When sharing results (Slack, Circle, reports), only include public-safe data
- Never include raw UUIDs or internal IDs in user-facing output — use names and links instead

---

## Rule 7: Confirm Before Destructive Actions

Some operations have real-world consequences. **Always ask for confirmation before:**

- Publishing content to WordPress/CMS
- Deploying GBP changes (pushes to Google)
- Activating PPC campaigns (starts spending money)
- Distributing press releases (uses credits, can't be undone)
- Sending outreach emails (Digital PR)
- Deleting resources (projects, articles, campaigns)

**Pattern:**
```
Here's what will happen:
- {action description}
- {cost/impact}

Proceed? (yes/no)
```

---

## Rule 8: Follow the Workflow Order

Multi-step workflows have dependencies. Don't skip ahead.

**SEO Onboarding order:**
1. Project → 2. Audit → 3. Pillar scores → 4. Brand vault → 5. Keywords → 6. Topical map → 7. Articles

**PPC Launch order:**
1. Business → 2. Products → 3. Approve → 4. Keywords → 5. Send to Ads → 6. Activate

**Why:** Each step produces IDs and data that later steps need. Skipping steps causes missing data errors.

---

## Rule 9: Use the Dashboard Links

Every tool maps to a dashboard URL. Always include clickable links in output so users can verify results visually.

| Tool Category | Dashboard URL |
|--------------|---------------|
| OTTO SEO | `https://dashboard.searchatlas.com/otto/` |
| Brand Vault | `https://dashboard.searchatlas.com/brand-vault/` |
| Content | `https://dashboard.searchatlas.com/content/articles/` |
| Topical Maps | `https://dashboard.searchatlas.com/content/topical-maps/` |
| GBP | `https://dashboard.searchatlas.com/gbp/` |
| PPC / Smart Ads | `https://dashboard.searchatlas.com/otto-ppc/` |
| Press Releases | `https://dashboard.searchatlas.com/press-releases/` |
| Cloud Stacks | `https://dashboard.searchatlas.com/cloud-stacks/` |
| Digital PR | `https://dashboard.searchatlas.com/digital-pr/` |
| LLM Visibility | `https://dashboard.searchatlas.com/llm-visibility/` |
| Site Explorer | `https://dashboard.searchatlas.com/site-explorer/` |
| Local SEO | `https://dashboard.searchatlas.com/local-seo/` |
| Website Studio | `https://dashboard.searchatlas.com/website-studio/` |

---

## Rule 10: Handle Known Quirks

| Tool | Known Issue | Workaround |
|------|------------|------------|
| `bv_*` | Intermittent auth errors | Retry 2-3 times; if persistent, create vault manually in dashboard |
| GBP `gbp_update_location` / `gbp_bulk_deploy_locations` | Only works on verified locations | Check verification status first via `gbp_get_location` |
| GBP `gbp_get_location_metrics` | Returns empty for new/low-traffic locations | This is normal — stats populate over time after verification |
| Content 4-step workflow | Each poll can take 30-60 seconds | Be patient — don't assume failure if polling takes time |
| Content `cg_list_articles` | Does not filter by domain | Articles aren't domain-tagged. Use `cg_get_article_summary` to inspect, or filter the returned list by status instead |
| PPC `ppc_list_businesses` | Requires `google_ads_account_id` + `google_ads_client_id` | Call `ppc_list_accounts` first, then ask user to select an account |
| PPC `ppc_bulk_create_keyword_clusters` | Async, can take several minutes | Poll `verify_task_status` — don't proceed until complete |
| Flat tool names | Names are now flat & unique per op (no dispatcher collisions) | If a call fails, confirm the exact name via schema discovery — e.g. use `otto_list_projects` directly rather than a grouped name |

---

## Rule 11: Know the Parameter Names

Parameter naming is **inconsistent across tools**. The same concept uses different param names depending on the tool group. Always use schema discovery (Rule 1), but here's a cheat sheet:

### Brand Vault tools
| Operation | Key Parameter | Name |
|-----------|--------------|------|
| `bv_get_details` | vault ID | `brand_vault_uuid` |
| `bv_get_business_info` | vault ID | `brand_vault_uuid` |
| `bv_get_knowledge_graph` | domain | `hostname` |
| `bv_get_details` (view=`overview`) | domain | `hostname` |
| `bv_list_voice_templates` | domain | `hostname` |

**Pattern:** CRUD by UUID → uses `brand_vault_uuid`. Read-only by domain → uses `hostname`.

### Site Explorer tools (`se_get_organic`, `se_get_links`, `se_get_analysis`, `se_get_adwords`)
All use `site_id` (from `se_list_sites`):
```
site_id: "example.com"    # domain works
site_id: "https://..."    # full URL works
site_id: "12345"          # site ID works
```

### GBP tools
All use `location_id` (integer, from `gbp_list_locations`).

### PPC tools
- `ppc_list_businesses` needs `google_ads_account_id` + `google_ads_client_id`
- `ppc_list_products` → uses `business_id`
- `ppc_list_campaigns` → uses `business_id`

### OTTO tools
- Most use `project_id` (the OTTO project UUID)
- `se_get_holistic_seo_scores` uses `domain` (plain domain string)

---

## Rule 12: Use Current Tool Names

Legacy tool names from early MCP versions still appear in some documentation and workflow templates. The API accepts both, but prefer the current names:

| Deprecated Name | Current Name |
|----------------|-------------|
| `BrandVaultTools` | `bv_*` |
| `OTTO_Project_Management` | `otto_*` (`otto_list_projects` / `otto_get_project_details`) |
| `OTTO_Audit_Management` | `otto_create_audit` / `otto_get_site_audit` |
| `OTTO_Knowledge_Graph` | `bv_get_knowledge_graph` |
| `Site_Explorer_Holistic_Audit_Tool` | `se_get_holistic_seo_scores` |
| `Site_Explorer_Keyword_Research_Tool` | `se_create_keyword_research` / `se_keyword_research_projects` |
| `Site_Explorer_Backlinks_Tool` | `se_get_links` |
| `Content_Generation_Tool` | `cg_*` |
| `Topical_Maps_Tools` | `cg_create_topical_map` / `cg_search_topical_maps` |
| `Visibility_Analysis_Tools` | `llmv_*` (`llmv_get_overview`) |
| `Prompt_Simulator_Tools` | `llmv_submit_prompts` / `llmv_get_ps_analysis` |
| `otto_ppc_business_crud` | `ppc_list_businesses` / `ppc_*` |
| `otto_ppc_product_crud` | `ppc_list_products` / `ppc_*` |
| `otto_ppc_campaign` | `ppc_list_campaigns` / `ppc_*` |

See [INTENT_MAPPING.md](INTENT_MAPPING.md) for the full deprecated → current mapping table.
