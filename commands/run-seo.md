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

1. **Create OTTO project** — `project_management` → `engage_otto_project` with the client's domain, then `verify_otto_installation`
2. **Create site audit** — `audit_management` → `create_audit` with the project ID
3. **Get pillar scores** — `seo_analysis` → `get_holistic_seo_pillar_scores` for Technical, Content, Authority, UX
4. **Create brand vault** — `brand_vault` → `create_brand_vault` with domain + client name, then set voice profile
5. **Keyword research** — `keyword_research` → `create_keyword_research_project` with pillar keyword + location
6. **Topical map** — `topical_maps` → `create_topical_map` from pillar keyword
7. **Generate articles** — `content_generation` → run the 4-step article workflow for each title from the topical map:
   - `create_content_instance` → `start_information_retrieval` → poll → `start_headings_outline` → poll → `generate_complete_article`

Ask the user for: domain, client name, pillar keyword, target location, pillar URL, number of articles (default: 4).

### Monthly Maintenance

Load `workflows/monthly-seo.yaml` and execute:

1. **Issues overview** — `project_management` → `get_otto_project_details` + `manual_reprocess_autopilot`
2. **Apply suggestions** — `suggestion_management` → `edit_suggestions_bulk` (apply all approved)
3. **Deploy schemas** — `schema_markup` → `list_domain_level_schemas` + `deploy_domain_level_schema`
4. **Fix indexing** — `indexing_management` → check sitemaps + submit URLs for indexing
5. **Expand topical map** — `topical_maps` → `create_topical_map` with this month's keyword
6. **Generate articles** — 4-step workflow per article
7. **Grade content** — `article_management` → `run_content_grader` on existing articles

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
