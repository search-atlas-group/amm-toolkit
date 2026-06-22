# Tool Reference

Catalog of the SearchAtlas MCP tools, grouped by area. Tools are **flat and per-operation** — each tool is its own name (e.g. `otto_list_projects`, `bv_list`), prefixed by area (`otto_`, `bv_`, `se_`, `cg_`, `gbp_`, `ppc_`, `pr_`, `cs_`, `dpr_`, `llmv_`, `local_seo_heatmaps_`, `ws_`, `krt_`, `gsc_`, `kg_`, `indexer_`, `dkn_`, `fs_`). Several former dispatcher operations are now folded into a single flat tool that takes a `view`/`action`/`type` parameter (noted inline).

> **Always use schema discovery first.** The names below reflect the current known surface — but the MCP may expose a different or extended set depending on your account and the server version. Before calling any tool, ask Claude to list available SearchAtlas tools, or describe what you want to do and let it route correctly.
>
> **Note on prefixes:** the live tools are exposed as `mcp__<connection>__<flatname>` (the connection prefix varies per user). Use the **bare flat name** (`bv_list`) in prompts — it stays portable.

---

## OTTO SEO (`otto_*`)
Project lifecycle, crawl settings, installation, audits, schema, indexing, suggestions, exports.
- `otto_list_projects` — list all OTTO projects
- `otto_get_project_details` — health score, pages, issues for a project
- `otto_find_project_by_hostname` — look up project by domain
- `otto_set_engagement` — engage (activate deployment) / disengage a project (`engaged: true|false`)
- `otto_set_freeze` — pause/resume automation (`frozen: true|false`)
- `otto_update_crawl_settings` — configure crawl depth, frequency
- `otto_check_installation` — check if the OTTO pixel / Cloudflare worker is installed (`check: pixel|cloudflare`)
- `otto_get_installation_guide` — get installation instructions
- `otto_manual_reprocess_autopilot` — re-run autopilot suggestions
- `otto_export_work_summary` — export work summary to Google Sheet
- `otto_get_project_issues` — project issues summary / by type
- `otto_create_audit` — run a site audit (set `create_otto_project=true` to also create an OTTO project — the only way to create one)
- `otto_get_site_audit` — get audit results
- `otto_trigger_recrawl` — force a fresh crawl
- **Schema:** `otto_list_schemas` / `otto_get_schema_detail` / `otto_generate_page_schema` / `otto_edit_page_schema` / `otto_delete_page_schema` / `otto_deploy_schema`
- **Suggestions:** `otto_edit_suggestion` / `otto_edit_suggestions_bulk` / `otto_delete_suggestion` / `otto_export_suggestions`
- **Indexing:** `otto_manage_custom_indexing_urls` / `otto_delete_custom_indexing_url` / `otto_select_urls_for_indexing` / `otto_manage_indexing_sitemaps` / `otto_modify_indexing_sitemap`
- **Recommendations:** `otto_generate_bulk_recommendations` / `otto_generate_single_recommendation`
- `otto_upload_image` — upload an image for use in OTTO
- `otto_update_refine_prompt` — set custom AI instructions per content type

### Quota (`get_quota`)
- `get_quota` — check usage limits across services (`service: all|otto|cloud_stack|press_release|llm_visibility|indexer`). `get_balance` for Hyperdrive Credits, `get_usage_history` for consumption events.

### Brand Vault (`bv_*`)
Brand vault management + knowledge graph.
- `bv_list` / `bv_create` / `bv_get_details` / `bv_update`
- `bv_archive` / `bv_restore` / `bv_list_archived`
- `bv_get_business_info` / `bv_update_business_info`
- `bv_get_details` (`view='overview'`) / `bv_get_index_status` / `bv_ask`
- `bv_get_knowledge_graph` / `bv_update_knowledge_graph`
- `bv_list_voice_templates` / `bv_select_voice_profile`

---

## Site Explorer (`se_*`)

### Projects
- `se_list_sites` / `se_create_project` / `se_get_details` / `se_delete_project`

### Organic — `se_get_organic` (`view='keywords'|'pages'|'competitors'|'position_changes'|'subdomains'`)
- `view='keywords'` — top ranking keywords
- `view='pages'` — top pages by traffic
- `view='competitors'` — competitor domains
- `view='position_changes'` — ranking movement
- `view='subdomains'` — subdomain breakdown
- `se_get_indexed_pages` — indexed page count

### Backlinks
- `se_get_links` — backlinks, referring domains, outgoing links, anchor-text analysis
- `se_get_educational_backlinks` — .edu / .gov backlink analysis

### Analysis — `se_get_analysis` (`view='trends'|'intent'|'positions'|'serp_features'`)
- `view='trends'` — traffic/ranking trends over time
- `view='intent'` — keyword intent classification
- `view='positions'` — ranking position breakdown
- `view='serp_features'` — featured snippets, PAA, etc.

### AdWords / paid
- `se_get_adwords` — paid keywords, pages, competitors, ad copies, ad history/trend

### Keyword research
- `se_keyword_research_projects` (list) / `se_create_keyword_research` / `se_get_keyword_research_details`
- `se_update_keyword_research` / `se_delete_keyword_research` / `se_get_serp_overview` / `se_lookup_keyword`

### Brand signals
- `se_submit_brand_signals` / `se_get_brand_signals`

### Holistic audit
- `se_get_holistic_seo_scores` — Technical, Content, Authority, UX pillar scores

---

## Content Genius (`cg_*`)

### Generation — the 4-step article workflow
1. `cg_create_content_instance` — create article stub
2. `cg_start_information_retrieval` — research phase (poll with `cg_wait_for_task`)
3. `cg_start_headings_outline` — outline phase (poll with `cg_wait_for_task`)
4. `cg_generate_complete_article` — write the full article

Plus:
- `cg_update_article_headings` — modify outline before generation
- `cg_auto_generate_article` / `cg_generate_article_with_review` — skip manual steps
- `cg_topic_suggestions` — get AI-suggested topics

### Article management
- `cg_get_article_details` / `cg_edit_article_content` / `cg_regenerate_article`
- `cg_run_content_grader` — score article quality
- `cg_update_article_status` / `cg_manage_article_keywords`
- `cg_manage_article_links` / `cg_export_to_google_doc` / `cg_reassign_brand_vault`

### Listing / retrieval — `cg_list_articles`
- `cg_list_articles` — universal finder: filters by status, domain, brand vault, search, tags, score/word ranges, assignee, trash, recent-N-days, and publication status. **There is no count tool** — list and count the returned items.
- `cg_get_article_summary` — summary for a single article

### Publication (WordPress / CMS)
- `cg_get_wordpress_options` / `cg_get_cms_connectors` / `cg_get_cms_form_schema`
- `cg_push_article` — publish/draft/schedule to WordPress or a CMS connector
- `cg_cancel_publication` / `cg_schedule_article_batch` / `cg_get_current_datetime`

### Topical maps
- `cg_create_topical_map` / `cg_search_topical_maps` / `cg_get_topical_map_by_id`

---

## Google Business Profile (`gbp_*`)

### Connection
- `gbp_connect_account` / `gbp_manage_connections`

### Locations
- `gbp_list_locations` / `gbp_get_location` (`view='basic'|'full'`) / `gbp_update_location`
- `gbp_manage_hours` (regular hours / open-closed status) / `gbp_set_special_hours`
- `gbp_get_location_metrics` (`view='stats'` snapshot · `view='performance'` period comparison) / `gbp_set_location_lock`
- `gbp_search_places` — find a Google Business Profile / place_id

### Deployment
- `gbp_bulk_deploy_locations` (push local edits to Google) / `gbp_suggest_description`

### Recommendations
- `gbp_get_location_recommendations` / `gbp_generate_location_recommendations` / `gbp_bulk_apply_recommendations`

### Categories / services / attributes
- `gbp_manage_categories` (`action='add'|'remove'|'replace_primary'`) / `gbp_list_categories`
- `gbp_upsert_services` / `gbp_remove_services` / `gbp_list_services`
- `gbp_manage_attributes` (`action='upsert'|'remove'`) / `gbp_list_attributes`
- `gbp_manage_service_areas`

### Posts
- `gbp_list_posts` / `gbp_get_post` / `gbp_update_post` / `gbp_set_post_status` / `gbp_delete_post`
- `gbp_bulk_generate_posts` / `gbp_bulk_publish_posts` / `gbp_regenerate_post`
- `gbp_update_posting_settings` (cadence/content/approval) / `gbp_get_automated_posting_settings`
- `gbp_manage_posting_social_accounts` (Facebook / Instagram / Twitter / LinkedIn / TikTok)

### Reviews
- `gbp_list_reviews` / `gbp_get_review` / `gbp_update_review_reply` / `gbp_set_review_reply_published`
- `gbp_ai_generate_review_reply` / `gbp_get_review_stats`
- `gbp_get_review_automation_settings` / `gbp_update_review_automation`

### Utility
- `gbp_bulk_import` / `gbp_generate_hash`

---

## Local SEO / Heatmaps (`local_seo_heatmaps_*`)

### Businesses
- `local_seo_heatmaps_list_businesses` / `local_seo_heatmaps_create_business` / `local_seo_heatmaps_get_business`
- `local_seo_heatmaps_delete_business` / `local_seo_heatmaps_recommend_keywords`

### Grids / heatmaps
- `local_seo_heatmaps_setup_grids` / `local_seo_heatmaps_update_grid` / `local_seo_heatmaps_bulk_grids` / `local_seo_heatmaps_preview_grids`
- `local_seo_heatmaps_get_heatmap_details` / `local_seo_heatmaps_get_rank` / `local_seo_heatmaps_export_grid_summary`
- `local_seo_heatmaps_list_available_snapshot_dates` / `local_seo_heatmaps_single_competitor_versus_report`

---

## Press Releases (`pr_*`)
- `pr_list` / `pr_create` / `pr_get` / `pr_write` / `pr_list_content_types` / `pr_delete`
- `pr_get_distribution_status` / `pr_get_publish_options` / `pr_publish` / `pr_attach_image`

Credits/balance: `get_balance` / `get_usage_history` / `purchase_credits`.

---

## Cloud Stacks (`cs_*`)
- `cs_list` / `cs_create` / `cs_get` / `cs_get_status` (via `cs_get`) / `cs_list_templates` / `cs_delete`
- `cs_build` / `cs_publish` / `cs_get_providers`

---

## Digital PR (`dpr_*`)

### Campaigns
- `dpr_list_campaigns` / `dpr_create_campaign` / `dpr_get_campaign` / `dpr_update_campaign` / `dpr_set_campaign_active`
- `dpr_get_settings` / `dpr_update_settings` / `dpr_list_projects`
- `dpr_list_opportunities` / `dpr_toggle_opportunity` / `dpr_schedule_opportunities_bulk`

### Inbox
- `dpr_inbox` / `dpr_get_email_thread` / `dpr_reply_to_email` / `dpr_list_linked_emails`

### Templates
- `dpr_list_templates` / `dpr_create_template` / `dpr_get_template` / `dpr_update_template`

---

## AI Visibility / LLM SEO (`llmv_*`)

### Overview — `llmv_get_overview` (`view='brand'|'trend'|'topics'|'queries'|'sentiment'`)
- `view='brand'` — overall visibility, sentiment, citations
- `view='trend'` — visibility % over time
- `view='topics'` / `view='queries'` — topic/query visibility
- `view='sentiment'` — sentiment breakdown; `llmv_get_sentiment_trend` for the time-series

### Competitors / citations
- `llmv_get_competitor_data` — competitor visibility rank, trend, share of voice
- `llmv_get_citations_overview` / `llmv_get_citations_urls`

### Projects / queries / topics
- `llmv_list_projects` / `llmv_create_project` / `llmv_get_project`
- `llmv_list_queries` / `llmv_add_queries` / `llmv_remove_query`
- `llmv_list_topics` / `llmv_add_topics` / `llmv_remove_topic`

### Prompt simulator
- `llmv_submit_prompts` / `llmv_check_ps_status` / `llmv_list_prompt_analyses` / `llmv_get_ps_analysis`

---

## Website Studio (`ws_*`)
- `ws_list_projects` / `ws_create_project` / `ws_get_project` / `ws_publish_project`
- `ws_ensure_containers_running` / `ws_bulk_send_message` / `ws_get_credit_status` / `ws_ppc_sync`

---

## PPC / Smart Ads (`ppc_*`)

### Accounts
- `ppc_list_accounts` / `ppc_get_account_info` / `ppc_update_account` / `ppc_delete_account` / `ppc_get_customer_ads_accounts`
- `ppc_connect_new_account` / `ppc_sync_from_google` / `ppc_sync_conversion_tracking`

### Businesses
- `ppc_list_businesses` / `ppc_get_business` / `ppc_create_business` / `ppc_update_business` / `ppc_delete_business` / `ppc_validate_business`
- `ppc_generate_form_suggestions` / `ppc_geo_search`

### Campaigns
- `ppc_list_campaigns` — campaigns with metrics
- `ppc_list_campaign_performance` / `ppc_manage_campaign_performance`
- `ppc_send_to_google_ads` / `ppc_import_campaigns` / `ppc_manage_import`

### Products
- `ppc_list_products` / `ppc_get_product` / `ppc_add_product` / `ppc_update_product` / `ppc_generate_product_details`
- `ppc_discover_products` / `ppc_review_products` / `ppc_create_products`
- `ppc_bulk_create_keyword_clusters` / `ppc_bulk_product_action` / `ppc_bulk_create_campaign_budget` / `ppc_bulk_update_remote_status` / `ppc_bulk_validate_landing_pages`

### Tasks / polling
- `verify_task_status` — check async task progress (poll until SUCCESS)

---

## GSC (Google Search Console, `gsc_*`)
- `gsc_get_sites` / `gsc_get_pages` / `gsc_get_page_summary` / `gsc_get_page_keywords`
- `gsc_get_keyword_performance` / `gsc_get_keyword_history` / `gsc_compare_performance` / `gsc_get_site_property_performance`

---

## Summary

Tools are flat, per-operation, and prefixed by area. The main prefixes:

| Area | Prefix |
|------|--------|
| OTTO SEO | `otto_` |
| Brand Vault | `bv_` |
| Site Explorer | `se_` |
| Content Genius | `cg_` |
| Google Business Profile | `gbp_` |
| PPC / Smart Ads | `ppc_` |
| Local SEO / Heatmaps | `local_seo_heatmaps_` |
| Press Releases | `pr_` |
| Cloud Stacks | `cs_` |
| Digital PR | `dpr_` |
| AI / LLM Visibility | `llmv_` |
| Website Studio | `ws_` |
| Keyword Rank Tracker | `krt_` |
| GSC | `gsc_` |
| Knowledge Graph | `kg_` |
| URL Indexer | `indexer_` |
| Quota / balance | `get_quota` / `get_balance` / `get_usage_history` |

Use schema discovery to confirm exact names and parameters — the surface evolves.
