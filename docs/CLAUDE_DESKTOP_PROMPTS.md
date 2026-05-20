# Claude Desktop Prompts

Slash commands are a Claude Code feature. Claude Desktop doesn't have them — but it has the same SearchAtlas MCP, so the same workflows are one paste away.

**How to use this doc:** find the prompt you want, copy it, paste it into Claude Desktop, fill in the placeholders (`{domain}`, `{client}`, etc.), and send. Claude calls the same SA MCP tools the slash command would.

---

## Setup

Run the universal installer once. It auto-detects Claude Desktop and writes the MCP config to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```bash
curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
```

Restart Claude Desktop after installing. First tool call triggers OAuth — sign into SearchAtlas, approve, done.

---

## Account overview (replaces `/my-account`)

```
Give me a complete overview of my SearchAtlas account. Use the SearchAtlas MCP tools and walk through this discovery in order:

1. `project_management` → list_otto_projects — return name, domain, health score, page count, issue count
2. `brand_vault` → list_brand_vaults — return vault name, domain, voice profile status
3. `gbp_locations_crud` → list_locations — return name, address, verification, connected
4. `business_crud` → list — return business name, domain, product count, campaign count
5. For each business, `campaign` → list_campaigns_with_metrics — name, status, budget, impressions, clicks, cost
6. `content_retrieval` → count_articles — total + by status (draft, published, scheduled)
7. `quota_management` → get_otto_quota — sites used/total, AI generation used/total

Present grouped by product with counts and key metrics. Use a table where it helps.
```

---

## Diagnostic + action plan (replaces `/scout {domain}`)

```
I need a read-only diagnostic on {domain}. Don't create anything in SearchAtlas — only diagnose and recommend.

Steps:
1. Check what already exists for this domain:
   - `project_management` → find_project_by_hostname (hostname: {domain})
   - `brand_vault` → list_brand_vaults (filter by domain)
   - `gbp_locations_crud` → list_locations (filter by domain)
   - `business_crud` → list_businesses (filter by domain)
   - `visibility` → list_brands (filter by domain)
   Mark each existing | missing.

2. For each resource that EXISTS, pull current state:
   - OTTO project → holistic SEO pillar scores, issue counts, recent suggestions
   - Brand vault → completeness check
   - GBP → stats, recommendations, reviews summary
   - Backlinks → referring domains, anchor text, recent gains/losses
   - AI visibility → brand overview, share of voice
   - Organic → top keywords, position changes, competitor overlap

3. Return a prioritized action plan: top 5 things to do next, each mapped to the SA tool or workflow that would address it. Rank by impact × effort.

If everything is missing, say "brand-new domain — recommend onboarding first" and stop.
```

---

## Deep dive on one business (replaces `/business-report {domain}`)

```
Pull a complete report on {domain} from SearchAtlas. Cover every pillar:

- OTTO project (health, pages, issues, recent suggestions, deployment status)
- Brand vault (voice profile, business info, knowledge graph)
- Content (article counts by status, topical maps, recent publications)
- Site Explorer (top keywords, competitor overlap, backlinks summary)
- GBP (locations, stats, reviews, posts, recommendations)
- PPC (businesses, campaigns with metrics)
- AI visibility (brand overview, share of voice, sentiment)

For each section: current state, 1-2 noteworthy data points, what's healthy vs what needs attention. End with 3-5 concrete recommendations ranked by impact.
```

---

## New client onboarding (replaces `/onboard-client`)

```
Onboard a new client into SearchAtlas. Their domain is {domain}.

Steps (do all of them, in order, without asking interactive questions):

1. Fetch the homepage + contact + about + services pages. Extract: business name, industry, description, phone, email, address, hours, service areas, brand colors, brand voice cues.

2. `brand_vault` → create_brand_vault with everything you extracted. Save the brand_vault_uuid.

3. `project_management` → create_otto_project for {domain}. Connect GSC if available.

4. `gbp_locations_crud` → search_places to find their Google Business Profile. If found, surface the place_id and walk me through connecting it.

5. `business_crud` → create a PPC business shell (no campaigns yet).

6. `visibility` → create_brand for AI visibility tracking.

7. Summarize what was created with IDs and direct links.

Use clear phase headings like "## Phase 1 — Reading the site", "## Phase 2 — Brand vault", etc. Keep narration short and plain.
```

---

## SEO workflow (replaces `/run-seo {domain}`)

```
Run the SEO workflow for {domain}. This is monthly maintenance — assume the OTTO project already exists.

1. `project_management` → find_project_by_hostname → get project_id
2. `holistic_audit` → get_holistic_seo_pillar_scores → current pillar state
3. `recommendations` → generate_bulk_recommendations for the project
4. Poll with otto_wait until status = SUCCESS
5. `schema` → list_page_schemas → review pending deployments
6. `indexing` → list_indexing_sitemaps → check indexing health, submit any missing URLs
7. `backlinks` → get_site_backlinks summary for the last 30 days

Output: short summary of what changed this month, what's pending review, what needs human attention.
```

---

## GBP optimization (replaces `/run-gbp {domain}`)

```
Optimize the Google Business Profile for {domain}.

1. `gbp_locations_crud` → list_locations, find the one for {domain}, get location_id
2. `gbp_locations_crud` → get_location_recommendations for that location_id
3. Review each recommendation. For low-risk ones (description tightening, missing categories, missing services, missing hours), apply them automatically. For higher-risk ones (address changes, primary category swaps), surface them for my approval.
4. `gbp_posts` → list_posts → check if there's an active posting cadence. If none, suggest an automated posting schedule.
5. `gbp_reviews` → list_reviews → flag any unanswered reviews

Output: what you applied, what's awaiting my approval, what's pending review.
```

---

## Content generation (replaces `/run-content {domain}`)

```
Generate content for {domain}.

1. `project_management` → find_project_by_hostname → get project_id and content project
2. `cg_search_topical_maps` for this project. If none exist, propose 3 topical clusters based on the site's existing pages + keyword research, then create the best one with `cg_create_topical_map`.
3. From the topical map, pick the 3 highest-priority unwritten articles and `cg_dkn_bulk_generate_articles` for them.
4. Poll with `cg_dkn_get_article_status` until generation completes.
5. For each article, run `cg_run_content_grader` and report the score.

Output: 3 article titles, URLs in CG, grade scores, and what to fix before publishing.
```

---

## PPC campaign launch (replaces `/run-ppc {domain}`)

```
Build a PPC campaign for {domain}.

1. `business_crud` → list → find the business for this domain, get business_id (create one if missing)
2. `ppc_check_write_permissions` — confirm we can push to Google Ads
3. `ppc_discover_products` for this business — get product candidates
4. `ppc_review_products` and `ppc_bulk_approve_products` for the good ones
5. `ppc_bulk_create_keyword_clusters` from approved products
6. `ppc_bulk_create_ad_contents` for each cluster
7. `ppc_bulk_validate_landing_pages`
8. Pause before sending to Google Ads — surface the campaign structure to me for final approval, then `ppc_send_to_google_ads`.
```

---

## PR + authority building (replaces `/run-pr {domain}`)

```
Run the press release + authority building workflow for {domain}.

1. `pr_get_categories` and `pr_list_content_types` — pick the best category
2. Draft a press release with `pr_create_and_write` — angle the release around the client's most notable recent win or differentiator
3. `pr_get_distribution_options` — show me distribution tiers and pricing
4. Pause for my approval before `pr_publish`.
5. After publish, set up an outreach campaign with `dpr_create_campaign` for backlink outreach using the press release as the asset.
```

---

## AI visibility audit (replaces `/run-visibility {domain}`)

```
Run an AI/LLM visibility audit for {domain}.

1. `visibility` → list_brands → find or create the brand for this domain
2. `llmv_get_brand_overview` — share of voice, sentiment, mention count
3. `llmv_list_queries` → which prompts trigger mentions of this brand
4. `llmv_get_competitor_share_of_voice` — how we stack up
5. `llmv_get_citations_overview` — which sources LLMs cite when mentioning us
6. `llmv_get_sentiment_trend` — last 30 days

Output: where we stand, where competitors beat us, top 3 things to do to improve.
```

---

## Send results

After any workflow, you can ask Claude Desktop to share the output. The toolkit's send scripts aren't installed for Desktop, but Desktop can call webhooks directly:

```
Post this summary to my Slack workspace. Use the incoming webhook at {SLACK_WEBHOOK_URL}. Format the message with bold headers, bullet points, and any relevant links.
```

For email, use the Resend MCP if you have it installed, or ask Claude to draft an email and you send it manually.

---

## Tips for getting good results in Claude Desktop

- **Be explicit about which MCP to use.** Say "Use the SearchAtlas MCP" in the first message of a thread if you have multiple MCPs configured.
- **One client per thread.** Just like in Claude Code, don't mix clients in the same conversation — context bleeds.
- **Authorize the MCP once.** First tool call opens a browser tab. Approve. Token lives until you sign out of SearchAtlas.
- **Schema discovery still works.** If you're not sure what a tool needs, ask: *"Call `project_management` with empty params and show me the schema."*
- **Save your favorite prompts.** Claude Desktop has Projects — drop these prompts into a Project's instructions and they become reusable.

---

## When you outgrow Desktop prompts

If you're running these workflows daily, the full Claude Code install is faster: slash commands, the Mission Control wizards, send integrations, workflow templates, and a `clients/{slug}/` folder per client.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"
```
