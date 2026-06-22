# Intent → Tool Mapping Reference

> Quick reference card for mapping natural language intent to SearchAtlas MCP tools.
> Use this to route user requests to the correct workflow template.

---

## Keyword → Tool Table

| User says… | Primary Tools | Workflow Template |
|------------|--------------|-------------------|
| "audit", "site health", "issues", "crawl" | `otto_create_audit`, `se_get_holistic_seo_scores` | A or B |
| "new client", "onboard", "set up project" | `otto_list_projects` / `otto_get_project_details` / `otto_set_engagement`, full onboarding flow | **A — New Client SEO Onboarding** |
| "sync client", "push to brand vault", "pull from SA", "update brand profile", "brand vault out of date" | `bv_*` (push/pull) | `/sync-client` |
| "monthly", "maintenance", "recurring SEO" | `otto_edit_suggestions_bulk`, `otto_list_schemas` / `otto_deploy_schema` | **B — Monthly SEO Maintenance** |
| "brand vault", "brand voice", "brand profile", "brand" | `bv_*` | A (step 4) |
| "topical map", "content strategy", "content plan", "content calendar" | `cg_create_topical_map` / `cg_search_topical_maps` | A (step 6) or B (step 5) |
| "content", "blog", "article", "write", "generate article" | `cg_create_topical_map` → `cg_*` | A/B content steps |
| "content grader", "grade article", "optimize article" | `cg_run_content_grader` | B (step 7) |
| "publish", "WordPress", "CMS" | `cg_push_article` | B (step 7+) |
| "GBP optimization", "fix GBP profile", "Google Business" | `gbp_get_location_recommendations`, `gbp_manage_categories`, `gbp_upsert_services`, `gbp_manage_attributes` | **C — GBP Profile Optimization** |
| "GBP posts", "post schedule", "social posts" | `gbp_bulk_generate_posts`, `gbp_update_posting_settings`, `gbp_list_posts` | **D — GBP Monthly Recurring** |
| "reviews", "reply reviews", "review responses" | `gbp_list_reviews` | D (step 1) |
| "GBP stats", "GBP performance", "profile analytics" | `gbp_get_location_metrics` (view=`stats`) | D (step 5) |
| "PPC", "ads", "campaign", "Google Ads", "paid search" | `ppc_list_businesses`, `ppc_list_products`, `ppc_list_campaigns` | **E — PPC Campaign Launch** |
| "landing page", "website", "web page" | `ws_*` | E (step 7, optional) |
| "local SEO", "heatmap", "map pack", "local rankings" | `local_seo_heatmaps_*` | Standalone |
| "press release", "PR distribution" | `pr_*` | **F — Authority Building** |
| "cloud stack", "cloud network" | `cs_*` | F (steps 3–4) |
| "backlinks", "link building", "outreach", "digital PR" | `dpr_*`, `se_get_links` | F (steps 5–6) |
| "LLM", "AI visibility", "ChatGPT mentions", "AI search" | `llmv_get_overview`, `llmv_submit_prompts` | **G — LLM Visibility & Reporting** |
| "sentiment", "brand sentiment" | `llmv_get_sentiment_trend` | G (step 2) |
| "schema", "structured data", "schema markup" | `otto_list_schemas` / `otto_deploy_schema` | B (step 3) |
| "indexing", "index now", "IndexNow", "sitemap" | `otto_manage_indexing_sitemaps` / `otto_select_urls_for_indexing` | B (step 4) |
| "keywords", "keyword research", "keyword list" | `se_create_keyword_research` / `se_keyword_research_projects` | A (step 5) |
| "SERP", "rankings", "position distribution" | `se_get_analysis` / `se_get_organic` | G (step 4) |
| "report", "summary", "export", "Google Sheet" | `otto_export_work_summary` | G (step 5) |
| "SEO issues", "website issues", "recommendations" | `otto_generate_bulk_recommendations` / `otto_get_project_issues` | Standalone |

---

## Tool → Dashboard Link Patterns

| Tool | Dashboard URL Pattern |
|------|-----------------------|
| `otto_*` | `https://dashboard.searchatlas.com/otto/` |
| `otto_create_audit` / `otto_get_site_audit` | `https://dashboard.searchatlas.com/otto/site-audit/` |
| `bv_*` | `https://dashboard.searchatlas.com/brand-vault/` |
| `cg_create_topical_map` / `cg_search_topical_maps` | `https://dashboard.searchatlas.com/content/topical-maps/` |
| `cg_*` (articles) | `https://dashboard.searchatlas.com/content/articles/` |
| `gbp_*` | `https://dashboard.searchatlas.com/gbp/` |
| `local_seo_heatmaps_*` | `https://dashboard.searchatlas.com/local-seo/` |
| `ppc_*` | `https://dashboard.searchatlas.com/otto-ppc/` |
| `pr_*` | `https://dashboard.searchatlas.com/press-releases/` |
| `cs_*` | `https://dashboard.searchatlas.com/cloud-stacks/` |
| `dpr_*` | `https://dashboard.searchatlas.com/digital-pr/` |
| `llmv_*` | `https://dashboard.searchatlas.com/llm-visibility/` |
| `se_*` | `https://dashboard.searchatlas.com/site-explorer/` |
| `ws_*` | `https://dashboard.searchatlas.com/website-studio/` |

---

## Deprecated Tools

| Deprecated | Replacement | Reason |
|-----------|-------------|--------|
| `OTTO_Knowledge_Graph` | `bv_*` (`bv_get_knowledge_graph`) | All KG ops now in Brand Vault |
| `OTTO_Project_Management` | `otto_*` (`otto_list_projects` / `otto_get_project_details`) | Now flat per-operation tools |
| `OTTO_Audit_Management` | `otto_create_audit` / `otto_get_site_audit` | Now flat per-operation tools |
| `OTTO_Suggestion_Management` | `otto_edit_suggestions_bulk` / `otto_edit_suggestion` | Now flat per-operation tools |
| `OTTO_Schema_Markup` | `otto_list_schemas` / `otto_deploy_schema` | Now flat per-operation tools |
| `OTTO_Indexing_Management` | `otto_manage_indexing_sitemaps` / `otto_select_urls_for_indexing` | Now flat per-operation tools |
| `OTTO_Recrawl_Management` | `otto_trigger_recrawl` | Now flat per-operation tools |
| `OTTO_Image_Upload` | `otto_upload_image` | Now flat per-operation tools |
| `OTTO_Quota_Management` | `get_quota` | Now a flat tool (note: NOT `otto_get_quota`) |
| `BrandVaultTools` | `bv_*` | Now flat per-operation tools |
| `Site_Explorer_*` | `se_*` (`se_get_organic`, `se_get_links`, `se_get_analysis`, `se_get_adwords`, `se_keyword_research_projects`, `se_get_brand_signals`, `se_get_holistic_seo_scores`) | Now flat per-operation tools |
| `Content_Generation_Tool` | `cg_*` | Now flat per-operation tools |
| `Article_Management_Tools` | `cg_*` | Now flat per-operation tools |
| `Content_Retrieval_Tools` | `cg_*` (`cg_list_articles`) | Now flat per-operation tools |
| `Content_Publication_Tools` | `cg_push_article` | Now flat per-operation tools |
| `Topical_Maps_Tools` | `cg_create_topical_map` / `cg_search_topical_maps` | Now flat per-operation tools |
| `Visibility_Analysis_Tools` | `llmv_*` (`llmv_get_overview`) | Now flat per-operation tools |
| `Sentiment_Analysis_Tools` | `llmv_get_sentiment_trend` | Now flat per-operation tools |
| `Query_Management_Tools` | `llmv_list_queries` / `llmv_add_queries` | Now flat per-operation tools |
| `Prompt_Simulator_Tools` | `llmv_submit_prompts` / `llmv_get_ps_analysis` | Now flat per-operation tools |
| `otto_ppc_business_crud` | `ppc_list_businesses` / `ppc_*` | Now flat per-operation tools |
| `otto_ppc_product_crud` | `ppc_list_products` / `ppc_*` | Now flat per-operation tools |
| `otto_ppc_product_mgmt` | `ppc_*` (product tools) | Now flat per-operation tools |
| `otto_ppc_campaign` | `ppc_list_campaigns` / `ppc_*` | Now flat per-operation tools |
| `otto_ppc_task` | `verify_task_status` | Now a flat polling tool |
| `otto_ppc_ads_account_crud` | `ppc_list_accounts` / `ppc_*` | Now flat per-operation tools |
| `otto_ppc_ads_account_mgmt` | `ppc_*` (account tools) | Now flat per-operation tools |
| `gbp_stats` | `gbp_get_location_metrics` (view=`stats`) | Now a flat tool |

---

## Multi-Intent Routing

When user intent spans multiple tools, chain workflows in this priority order:

1. **Infrastructure first:** OTTO project, audit, indexing, schema
2. **Brand/content foundation:** Brand vault, topical map
3. **Content execution:** Article generation, grading, publishing
4. **Promotion:** Press release, cloud stack, digital PR
5. **Local/GBP:** GBP optimization, posts, reviews
6. **Paid:** PPC campaign setup
7. **Reporting:** LLM visibility, analytics, exports

---

## Ambiguous Intent Resolution

| Ambiguous phrase | Ask user | Possible routes |
|-----------------|----------|----------------|
| "content" | "Do you mean creating new articles or optimizing existing ones?" | New → `cg_create_topical_map` + `cg_*` / Existing → `cg_*` |
| "set up GBP" | "Is this a first-time setup or monthly optimization?" | First time → C (full optimization) / Monthly → D (recurring) |
| "campaign" | "PPC ads campaign or digital PR outreach campaign?" | PPC → E / Outreach → F |
| "report" | "SEO summary report or LLM visibility report?" | SEO → `otto_export_work_summary` / LLM → G |
| "issues" | "OTTO project issues or detailed SEO analysis?" | OTTO → `otto_get_project_issues` / Detailed → `otto_generate_bulk_recommendations` |
