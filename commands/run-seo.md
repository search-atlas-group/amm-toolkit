---
name: run-seo
description: Monthly SEO workflow using SearchAtlas's holistic SEO scoring, OTTO recommendations, content health checks, indexer status, and keyword tracking — covers both new client onboarding and ongoing monthly maintenance.
---

# /searchatlas:run-seo

Execute an SEO workflow — either new client onboarding or monthly maintenance.

## Instructions

### Step 1: Choose Mode

Ask the user:
> Is this a **new client onboarding** or **monthly maintenance** for an existing client?

### New Client Onboarding

Load `workflows/seo-onboarding.yaml` and execute:

1. **Create OTTO project** — `otto_set_engagement` with the client's domain, then `otto_check_installation`
2. **Create site audit** — `otto_create_audit` with the project ID
3. **Get pillar scores** — `se_get_holistic_seo_scores` for Technical, Content, Authority, UX
4. **Create brand vault** — `bv_create` with domain + client name, then set voice profile
5. **Keyword research** — `se_create_keyword_research` with pillar keyword + location
6. **Topical map** — `cg_create_topical_map` from pillar keyword
7. **Generate articles** — run the 4-step article workflow for each title from the topical map:
   - `cg_create_content_instance` → `cg_start_information_retrieval` → poll → `cg_start_headings_outline` → poll → `cg_generate_complete_article`

Ask the user for: domain, client name, pillar keyword, target location, pillar URL, number of articles (default: 4).

### Monthly Maintenance

Load `workflows/monthly-seo.yaml` and execute:

1. **Issues overview** — `otto_get_project_details` + `otto_manual_reprocess_autopilot`
2. **Apply suggestions** — `otto_edit_suggestions_bulk` (apply all approved)
3. **Deploy schemas** — `otto_list_schemas` + `otto_deploy_schema`
4. **Fix indexing** — `otto_manage_indexing_sitemaps` to check sitemaps + `otto_select_urls_for_indexing` to submit URLs for indexing
5. **Expand topical map** — `cg_create_topical_map` with this month's keyword
6. **Generate articles** — 4-step workflow per article
7. **Grade content** — `cg_run_content_grader` on existing articles

Ask the user for: OTTO project ID (or domain to look it up), monthly keyword, articles to generate, articles to grade.

### Final Step: Save Workflow Log

After completing all steps, write a workflow log to:

`${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/workflows/seo-{YYYY-MM-DD}.md`

The log should include:
- Mode (onboarding or monthly maintenance)
- Domain and client slug
- Date/time of run
- Steps completed with results (counts, links where available)
- Steps failed with error details
- Articles generated (titles, content project IDs)
- Next recommended action

After writing the file, print the path in chat so the user can open it.

## Output Format

```
✅ {client} — {mode} · {period}

{emoji} {Step Name}  {result}  [View →](url)
...

{total} actions completed · {failed} failed

📄 Workflow log: ${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/workflows/seo-{YYYY-MM-DD}.md
```

## Golden Rules

- Always discover the project ID first — never hardcode it
- Poll async tasks (audit creation, article generation) with 5–10 second intervals
- Confirm before applying bulk suggestions or deploying schemas
