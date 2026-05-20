# /business-report

Generate a deep-dive report on a single business/domain across all SearchAtlas products.

## Instructions

### Step 1: Identify the Business

Ask the user which business or domain they want to report on. If unclear, run `/my-account` first to list all businesses.

### Step 2: Gather Data

Run these in parallel where possible:

**OTTO SEO**
- `project_management` → `find_project_by_hostname` (get project by domain)
- `project_management` → `get_otto_project_details` (health score, pages, issues)
- `seo_analysis` → `get_holistic_seo_pillar_scores` (Technical, Content, Authority, UX)

**Brand Vault**
- `brand_vault` → `list_brand_vaults` (filter by domain)
- `brand_vault` → `get_brand_vault_overview`

**Content**
- `content_retrieval` → `get_project_articles` (articles for this domain)
- `content_retrieval` → `get_article_summary`

**Site Explorer**
- `organic` → `get_organic_keywords` (top keywords, count)
- `organic` → `get_organic_competitors` (competitor domains)
- `backlinks` → `get_site_backlinks` (backlink count, top referring domains)
- `analysis` → `get_position_distribution`
- `analysis` → `get_serp_features`

**GBP (if applicable)**
- `gbp_locations_crud` → `list_locations` (filter by domain/name)
- `gbp_locations_crud` → `get_location_stats`

**PPC (if applicable)**
- `business_crud` → `list` (filter by domain)
- `campaign` → `list_campaigns_with_metrics`

**LLM Visibility (if configured)**
- `visibility` → `get_brand_overview`
- `sentiment` → `get_sentiment_overview`

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
