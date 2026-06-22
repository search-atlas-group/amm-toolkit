---
name: business-report
description: Single-business deep dive — pulls OTTO project data, brand vault, Site Explorer, GBP, PPC, and LLM visibility from SearchAtlas, then presents a structured report with actionable recommendations and saves a markdown record to the client's reports folder.
---

# /searchatlas:business-report

Generate a deep-dive report on a single business/domain across all SearchAtlas products.

## Instructions

### Step 1: Identify the Business

Ask the user which business or domain they want to report on. If unclear, run `/searchatlas:my-account` first to list all businesses.

### Step 2: Gather Data

Run these in parallel where possible:

**OTTO SEO**
- `otto_find_project_by_hostname` (get project by domain)
- `otto_get_project_details` (health score, pages, issues)
- `se_get_holistic_seo_scores` (Technical, Content, Authority, UX)

**Brand Vault**
- `bv_list` (filter by domain)
- `bv_get_details` (view='overview')

**Content**
- `cg_list_articles` (articles for this domain)
- `cg_get_article_summary`

**Site Explorer**
- `se_get_organic` (view='keywords') (top keywords, count)
- `se_get_organic` (view='competitors') (competitor domains)
- `se_get_links` (backlink count, top referring domains)
- `se_get_analysis` (view='positions')
- `se_get_analysis` (view='serp_features')

**GBP (if applicable)**
- `gbp_list_locations` (filter by domain/name)
- `gbp_get_location_metrics` (view='stats')

**PPC (if applicable)**
- `ppc_list_businesses` (filter by domain)
- `ppc_list_campaigns` (with metrics)

**LLM Visibility (if configured)**
- `llmv_get_overview`
- `llmv_get_overview` (view='sentiment')

### Step 3: Present Report

```
📊 Business Report: {domain}

🏗️ OTTO SEO
   Health: {score}/100 · Pages: {N} · Issues: {N}
   Pillars: Tech {X} · Content {X} · Authority {X} · UX {X}

🏷️ Brand Vault
   Status: {active/none} · Voice: {profile} · KG: {status}

✍️ Content
   {total} articles · {published} published · Avg score: {X}

🔍 Site Explorer
   Organic keywords: {N} · Avg position: {X}
   Backlinks: {N} · Referring domains: {N}
   Top competitors: {list}

📍 GBP (if applicable)
   {location_name} · {reviews} reviews · {avg_rating}★
   Views: {N}/mo · Clicks: {N}/mo

💰 PPC (if applicable)
   {N} campaigns · ${spend}/mo · {clicks} clicks · ${cpc} avg CPC

👁️ LLM Visibility (if applicable)
   Brand presence: {score}% · Sentiment: {positive}% positive

💡 Recommendations
   1. {actionable recommendation}
   2. {actionable recommendation}
   3. {actionable recommendation}
```

### Step 4: Save Local Report

After presenting in chat, save a markdown copy of the report:

Path: `${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/reports/{YYYY-MM-DD}.md`

SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"

Create the `${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/reports/` folder if it doesn't exist.

The markdown file should contain the full report from Step 3 above, plus:
- The run timestamp
- A pointer to run `/searchatlas:scout {domain}` for a deeper diagnostic
- A pointer to run `/searchatlas:summit-shot` to act on the top recommendation

Print the absolute path after saving so the user can open it directly.
