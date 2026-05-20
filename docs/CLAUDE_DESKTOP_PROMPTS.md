# Claude Desktop Prompts

Slash commands are a Claude Code feature. Claude Desktop doesn't have them — but it has the same SearchAtlas MCP, so the same workflows are one paste away.

Every prompt below is **output-faithful** with its slash command: same tool calls, same chat render, same deliverables (HTML reports, brand-profile files, SA Report Builder reports). Where the slash command writes files, the Desktop prompt asks for the same content rendered as a code block you can copy and save manually.

**How to use:** copy a prompt, paste it into Claude Desktop, fill in the placeholders (`{domain}`, `{client_slug}`, etc.), and send.

---

## Setup — one command

The universal installer auto-detects Claude Desktop and writes the MCP config to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```bash
curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/install-mcp.sh | bash
```

Restart Claude Desktop. First tool call triggers OAuth — sign into SearchAtlas, approve, done. No second MCP to install.

---

## Account overview — replaces `/my-account`

```
Use the SearchAtlas MCP to show me a complete account overview. Run these tools in order:

1. `project_management` → list_otto_projects — name, domain, health score, page count, issue count
2. `brand_vault` → list_brand_vaults — name, domain, voice profile status
3. `gbp_locations_crud` → list_locations — name, city/state, verified/unverified, connected
4. `business_crud` → list — business name, domain, product count, campaign count
5. For each business → `campaign` → list_campaigns_with_metrics — name, status, budget, impressions, clicks, cost
6. `content_retrieval` → count_articles — total + by status (draft, published, scheduled)
7. `quota_management` → get_otto_quota — sites used/total, AI generation used/total

Render exactly in this format (replace placeholders with real data):

📊 Your SearchAtlas Account

🏗️ OTTO Projects ({count})
   {domain}  Score: {score}/100  Pages: {N}  Issues: {N}

🏷️ Brand Vaults ({count})
   {name}  Voice: {profile}

📍 GBP Locations ({count})
   {name}  {city, state}  {verified/unverified}

💰 PPC ({business_count} businesses · {campaign_count} campaigns)
   {business} → {N} products · {N} campaigns · ${spend}/mo

✍️ Content
   {total} articles · {published} published · {draft} drafts

📦 Quota
   Sites: {used}/{total} · AI: {used}/{total}
```

---

## Diagnostic — replaces `/scout {domain}`

```
Run a read-only SearchAtlas diagnostic on {domain}. Do NOT engage projects, do NOT create brand vaults, do NOT deploy schemas. Diagnose only. The only writes allowed are: (a) a SearchAtlas Report Builder report (client-shareable) and (b) a self-contained HTML I'll save myself.

PHASE 1 — Identify target
- Capture the domain and propose a client_slug (e.g. coastaldental.com → coastal-dental).

PHASE 2 — Existence check (do not create anything)
For {domain}, look up:
- `project_management` → find_project_by_hostname  → project_id or null
- `brand_vault` → list_brand_vaults (filter by domain) → brand_vault_uuid or null
- `gbp_locations_crud` → list_locations (filter by domain) → location_id or null
- `business_crud` → list_businesses (filter by domain) → business_id or null
- `visibility` → list_brands (filter by domain) → brand_id or null

PHASE 3 — Parallel discovery (only for resources that exist; fail-soft)
- OTTO (project_id) → get_otto_project_details, get_holistic_seo_pillar_scores, list_audits
- Site Explorer (no ID needed) → get_organic_keywords (limit 100), get_organic_competitors (limit 5), get_position_distribution, get_site_backlinks (limit 50), get_site_referring_domains (limit 25)
- Brand Vault (uuid) → retrieve_brand_vault_details, list_voice_profiles, get_knowledge_graph
- GBP (location_id) → get_location_stats, list_reviews
- PPC (business_id) → list_campaigns_with_metrics
- LLM Visibility (brand_id) → get_brand_overview, get_sentiment_overview

PHASE 4 — Score each pillar (✅ Healthy · ⚠️ Needs Work · ❌ Missing) using these thresholds:
- OTTO SEO healthy when health ≥ 70 and issues < 25
- Brand Vault healthy when vault exists, voice profile active, KG populated
- Content healthy when 30+ articles or content pillar ≥ 70
- Authority healthy when authority pillar ≥ 70 and 25+ referring domains
- Site Explorer healthy when 5+ keywords in pos 1–3
- GBP healthy when location connected and reply rate ≥ 80%
- PPC healthy when campaigns running with positive ROAS
- LLM Visibility healthy when monitored and SoV ≥ 30%

PHASE 5 — Action plan (top 4–6 priorities, mapped to commands)
Use this rubric: no brand vault → /onboard-client. OTTO health < 70 or 25+ issues → /run-seo. Authority < 40 or < 25 ref domains → /summit-shot 9 then 10. Content < 50 or no topical map → /summit-shot 5 then 7. GBP missing → /summit-shot 8. LLM not monitored → /summit-shot 4. LLM SoV < 30% → /summit-shot 17–19. Strong organic, no paid → /summit-shot 14.

PHASE 6 — Render chat output exactly in this format:

🎯 Scout Report — {domain}
   Run on {YYYY-MM-DD HH:MM}

━━ Pillar Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️  OTTO SEO        {emoji} {summary}
🏷️  Brand Vault     {emoji} {summary}
✍️  Content         {emoji} {summary}
🔍  Site Explorer   {emoji} {summary}
📍  GBP             {emoji} {summary}
💰  PPC             {emoji} {summary}
👁️  LLM Visibility  {emoji} {summary}

━━ Pillar Scores (Holistic SEO) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Technical    {score}/100   {bar}
  Content      {score}/100   {bar}
  Authority    {score}/100   {bar}
  UX           {score}/100   {bar}

━━ Top Organic Keywords ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {keyword}                    pos {N}    {volume}/mo
  ...

━━ Top Competitors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {competitor_domain}          {N} shared kws
  ...

━━ Recommended Shots ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. {finding}                 → run /{command}
  2. {finding}                 → run /{command}
  ...

📄 Internal record:    clients/{slug}/scout/{date}/index.html
🔗 Client report:      {SA Report Builder URL or "create manually in SA Report Builder using inputs from the local HTML"}

PHASE 7 — Create the client-shareable Report Builder report
Schema-discover the report builder create tool by calling it with `{}` first (the visible read tools are rb_list_reports, rb_get_report_details, rb_list_reports_paginated; the create tool may surface as rb_create_report, rb_save_report, or something else — discover at runtime). Use these defaults:
- Title: "{Client Name} — Scout Report ({date})"
- Domain: {domain}
- Sections: OTTO health, pillar scores, top keywords, top competitors, GBP stats (if applicable), LLM visibility (if applicable)
- Audience: client-shareable. No "next shots" recommendations — those go only in the local HTML.

If no create tool is exposed by the MCP today, skip silently and tell me to create it manually.

PHASE 8 — Render the self-contained internal HTML as an artifact
Produce a single HTML file titled `clients/{slug}/scout/{YYYY-MM-DD-HHmm}/index.html`. Requirements:
- Self-contained: inline CSS, no external assets (web fonts via Google Fonts with system fallback is OK).
- Internal-only: includes the "Recommended Shots" section with command names (this is the marketer's working doc).
- Copy-paste friendly: keyword lists, competitor domains, command names should all be selectable text.

HTML sections in order:
1. Header — domain, scout date, client slug
2. At-a-glance pillar status grid (7 pillars, ✅/⚠️/❌)
3. Pillar score bars (Technical, Content, Authority, UX) with the 0–100 score
4. Top 10 organic keywords (table: keyword, position, volume, URL)
5. Top 5 competitors (table: domain, shared keywords, gap keywords)
6. Backlink summary (count, top 10 referring domains by DA)
7. GBP snapshot (if applicable: views, clicks, reviews, rating, reply rate)
8. LLM visibility snapshot (if applicable: SoV, sentiment, top mentions)
9. Recommended Shots — numbered priority list, each with finding + why it matters + command
10. Notes pointer card — static card pointing to a sibling notes.md (NOT an editable textarea; that state is lost on reload).

Output the HTML inside one ```html code block. I'll save it manually to the path above.
```

---

## Single business deep dive — replaces `/business-report {domain}`

```
Pull a complete deep-dive on {domain} from SearchAtlas. Same data scope as the scout, but the focus is full business state rather than a triage rubric.

Steps:
1. Identify resources: find_project_by_hostname, list_brand_vaults, list_locations, list_businesses, list_brands — collect IDs.
2. Pull current state for each that exists:
   - OTTO project: health, pages, issues, recent suggestions, deployment status
   - Brand vault: voice profile, business info, knowledge graph completeness
   - Content: article counts by status, topical maps, recent publications
   - Site Explorer: top keywords, competitor overlap, backlink/referring-domain summary
   - GBP: locations, stats, reviews, posts, recommendations
   - PPC: businesses, campaigns with metrics
   - AI Visibility: brand overview, share of voice, sentiment
3. For each section: current state, 1–2 noteworthy data points, what's healthy vs what needs attention.
4. End with 3–5 concrete recommendations ranked by impact × effort.

Render the chat output as a clean section-by-section report with table where it helps. Use the same emoji header conventions as the scout (🏗️ OTTO, 🏷️ Brand Vault, ✍️ Content, 🔍 Site Explorer, 📍 GBP, 💰 PPC, 👁️ LLM Visibility). Close with a "Top 3 Next Moves" block, each move mapped to the slash command that would do it.

If you can also render a self-contained HTML version of this report (same sections, internal style) inside a ```html code block, do that. Otherwise the chat render is fine.
```

---

## Onboard a new client — replaces `/onboard-client`

```
Onboard a new client into SearchAtlas. Their domain is {domain}. Run end-to-end without interactive questions.

PHASE 1 — Read the site
Fetch the homepage, contact, about, and services pages. Extract:
- Business name, industry (2–3 words), description (2–3 sentences)
- Phone, email, full street address, hours, service areas
- Brand colors (extract from logo/CSS), brand voice cues (formal/casual, jargon level)

PHASE 2 — Brand vault
`brand_vault` → create_brand_vault with everything extracted. Save brand_vault_uuid.
Then push voice profile, business info, knowledge graph in parallel using the appropriate update tools.

PHASE 3 — OTTO project
`project_management` → create_otto_project for {domain}. Connect GSC if available. Save project_id.

PHASE 4 — GBP
`gbp_locations_crud` → search_places to find the Google Business Profile. If found, surface place_id and instructions to connect it.

PHASE 5 — PPC business shell
`business_crud` → create a business (no campaigns yet). Save business_id.

PHASE 6 — LLM visibility
`visibility` → create_brand for AI visibility tracking. Save brand_id.

PHASE 7 — Generate client files for me to save locally

Output two code blocks, each labeled with the path I should save to.

**Block 1 — `clients/{client_slug}/CLAUDE.md`** (lean session-context file):
- Header with client name + domain
- Identity (business name, industry, location, primary services)
- IDs (brand_vault_uuid, otto_project_id, business_id, brand_id, location_id if any)
- Quick-action commands (top 3 next moves)
- Notes section (empty, for the marketer to fill)

**Block 2 — `clients/{client_slug}/brand-profile.md`** (full populated profile):
- Business info, brand voice, services, target audience, competitors, brand assets, SEO keywords, content themes
- Sync section listing which SA fields map to which markdown sections (so future /sync-client works)

PHASE 8 — Chat summary
Render exactly:

✅ Onboarded — {client_name}

🏷️  Brand Vault     created · {brand_vault_uuid}
🏗️  OTTO            created · {project_id} · GSC: {connected/pending}
📍  GBP             {found place_id / not found — manual search needed}
💰  PPC             business shell · {business_id}
👁️  LLM             monitored · {brand_id}

📁  CLAUDE.md         clients/{slug}/CLAUDE.md
📋  Brand Profile     clients/{slug}/brand-profile.md

Next steps (pick one):
1. /scout {domain}  — read-only diagnostic
2. /run-seo         — kick off SEO monthly maintenance
3. /run-gbp         — optimize GBP profile

Use clear phase headings like "## Phase 1 — Reading the site". Keep narration short, plain English.
```

---

## SEO workflow — replaces `/run-seo {domain}`

```
Run the SearchAtlas SEO workflow for {domain}. This is monthly maintenance — assume the OTTO project already exists.

1. `project_management` → find_project_by_hostname → project_id
2. `holistic_audit` → get_holistic_seo_pillar_scores → current pillar state
3. `recommendations` → generate_bulk_recommendations for the project; poll with otto_wait until status = SUCCESS
4. `schema` → list_page_schemas → review any pending deployments and deploy approved ones
5. `indexing` → list_indexing_sitemaps → check indexing health, submit any missing URLs
6. `backlinks` → get_site_backlinks summary for last 30 days
7. `quota_management` → get_otto_quota → confirm we have headroom for this month

Render chat output exactly in this format:

✅ {client} — SEO Monthly · {period}

🧪  Pillar Scores    T:{N} · C:{N} · A:{N} · UX:{N}        View →
🤖  Recommendations  {N} generated · {M} auto-applied       View →
🏗️  Schema           {N} deployed · {M} pending review      View →
🔗  Indexing         {N} URLs submitted · {M} indexed       View →
📈  Backlinks        +{N} new · -{M} lost (last 30d)        View →

{total} actions completed · {failed} failed

Replace `View →` with the deep link in the SearchAtlas dashboard for each action. Surface anything that needs human review at the bottom.
```

---

## GBP workflow — replaces `/run-gbp {domain}`

```
Optimize the Google Business Profile for {domain}. Two modes: optimization (first-time setup) or monthly (ongoing maintenance). Run optimization by default; pivot to monthly if location_id has been touched in the last 30 days.

1. `gbp_locations_crud` → list_locations → find location_id for {domain}
2. `gbp_locations_crud` → get_location_recommendations → categorize each by risk
3. For LOW-risk recommendations (description tightening, missing categories, missing services, missing hours, missing attributes), apply automatically via the relevant gbp_*_crud update tools.
4. For HIGH-risk recommendations (address changes, primary category swaps), surface for my approval before doing anything.
5. `gbp_posts` → list_posts → if no posting cadence, propose an automated schedule via gbp_automated_posting
6. `gbp_reviews` → list_reviews → flag unanswered reviews

Render chat output as one of these two blocks, depending on mode.

**OPTIMIZATION mode:**

✅ {location_name} — GBP Profile Optimization

📍 Location       synced from Google                      View →
🤖 Recommendations {N} applied (CHANGE + ADD)             View →
🏷️ Categories      primary + {N} additional set            View →
🛎️ Services        {N} services added/updated              View →
✅ Attributes      {N} missing attributes added            View →
📝 Description     AI description generated + deployed     View →

**MONTHLY mode:**

✅ {location_name} — GBP Monthly · {period}

⭐ Reviews         {N} replies published                   View →
📢 Posts           {N} posts generated + published         View →
🤖 Auto-posting    enabled · {frequency}                   View →
📊 Performance     {views} views · {clicks} clicks         View →

Surface anything awaiting my approval at the bottom.
```

---

## Content workflow — replaces `/run-content {domain}`

```
Generate content for {domain}.

1. `project_management` → find_project_by_hostname → project_id; identify or create the content project
2. `content_generation` → cg_search_topical_maps for this project. If none exist, propose 3 topical clusters from the site's existing pages + keyword research, then create the best one with cg_create_topical_map.
3. From the topical map, pick the 3 highest-priority unwritten articles and `content_generation` → cg_dkn_bulk_generate_articles.
4. Poll cg_dkn_get_article_status until generation completes.
5. For each article, run cg_run_content_grader and capture the score.
6. Optionally cg_publish_wordpress_article or cg_publish_cms_article — only if I confirm.

Render chat output exactly in this format:

✅ Content Generation Complete

🗺️ Topical Map     {keyword} · {N} clusters · {M} titles    View →

✍️ Articles Generated:
   1. {title}  Score: {X}/100  [View →](editor_link)
   2. {title}  Score: {X}/100  [View →](editor_link)
   3. {title}  Score: {X}/100  [View →](editor_link)

📊 Avg Score: {X}/100
📤 Published: {N}/{total}

{total} articles created · {failed} failed
```

---

## PPC workflow — replaces `/run-ppc {domain}`

```
Build and launch a PPC campaign for {domain}.

1. `business_crud` → list → find or create the business for this domain
2. `ppc_check_write_permissions` — confirm we can push to Google Ads
3. `ppc_discover_products` — get product candidates from landing pages
4. `ppc_review_products` and `ppc_bulk_approve_products`
5. `ppc_bulk_create_keyword_clusters` from approved products
6. `ppc_bulk_create_ad_contents` per cluster
7. `ppc_bulk_validate_landing_pages`
8. Pause before push — surface campaign structure for my approval, then `ppc_send_to_google_ads`

Render chat output exactly in this format:

✅ {business_name} — PPC Campaign Launch

🏢 Business        created + validated                     View →
🛍️ Products        {N} products from landing pages          View →
🔑 Keywords        {N} clusters · {K} total keywords        View →
📤 Google Ads      campaigns sent to account {id}           View →
▶️ Campaigns       activated + running at ${budget}/day     View →

{total} actions completed · {failed} failed
```

---

## PR + authority workflow — replaces `/run-pr {domain}`

```
Run the press release + authority building workflow for {domain}.

1. `pr_get_categories` and `pr_list_content_types` → pick the best category
2. `pr_create_and_write` — angle the release around the client's most notable recent win or differentiator
3. `pr_get_distribution_options` → show distribution tiers and pricing
4. Pause for my approval before `pr_publish`
5. Cloud stack — discover whether we have a cloud-stack builder under another tool prefix; if found, build + publish
6. `dpr_create_campaign` for backlink outreach using the press release as the asset
7. Monitor `dpr_list_opportunities` for early replies

Render chat output exactly in this format:

✅ {client} — Authority Building · {period}

📰 Press Release   written + distributed ({network})       View →
☁️ Cloud Stack     built + published · {N} properties      View →
📧 Digital PR      outreach campaign live · {N} targets    View →
🔗 Backlinks       {N} new backlinks detected              View →

{total} actions completed · {failed} failed
```

---

## LLM visibility — replaces `/run-visibility {domain}`

```
Run a SearchAtlas LLM Visibility audit for {domain}.

1. `visibility` → list_brands → find or create the brand for {domain}
2. `llmv_get_brand_overview` — share of voice, sentiment, mention count
3. `llmv_list_queries` → which prompts trigger mentions of this brand
4. `llmv_get_competitor_share_of_voice` — how we stack up
5. `llmv_get_citations_overview` — which sources LLMs cite when mentioning us
6. `llmv_get_sentiment_trend` — last 30 days

Render chat output exactly in this format:

✅ {brand_name} — LLM Visibility Report

👁️ AI Visibility   {score}% brand presence · #{rank} vs competitors
📈 Trend           {direction} over last {N} months
🏆 Share of Voice  {brand}: {X}% · {competitor_1}: {Y}% · {competitor_2}: {Z}%
💬 Sentiment       {positive}% positive · {neutral}% neutral · {negative}% negative
🤖 Prompt Sims     mentioned in {M}/{N} prompts tested
📊 SERP            {N} features captured · avg position {X}

💡 Recommendations
1. {recommendation}
2. {recommendation}
3. {recommendation}
```

---

## Sync brand profile ↔ SA — replaces `/sync-client`

```
I have a local `clients/{client_slug}/brand-profile.md` file with brand data. Sync it two ways with my SearchAtlas brand vault {brand_vault_uuid}.

1. Read the markdown file's content (I'll paste it below).
2. Compare each field against what's in SA via `brand_vault` → retrieve_brand_vault_details + retrieve_voice_profile + get_knowledge_graph.
3. For each field, classify as: (a) only in MD, (b) only in SA, (c) different in both, (d) same.
4. For (a) — push MD → SA via the appropriate update tools (bv_update_business_info, bv_update_knowledge_graph, etc.).
5. For (b) — surface the SA-only fields and ask me whether to pull them into MD.
6. For (c) — surface the diff and ask which side wins.
7. After resolving, output the updated brand-profile.md as a fenced code block.

Render chat output exactly:

✅ Sync — {client}

→ Pushed to SA   {N} fields updated
← Pulled from SA {N} fields added to MD
⚖️ Conflicts     {N} resolved · {M} need your input

[paste your brand-profile.md here]
```

---

## Single play — replaces `/summit-shot {N}`

```
Run a single play from the May Summit playbook. The 19 plays are documented in commands/summit-shot.md in the amm-toolkit repo. I want to run play number {N}.

Bounded scope by default:
- 1 article (not bulk)
- 1 press release (not multi-network)
- All drafts (no publishing without my approval)

Print the play name and a one-line scope at the start. Then execute. End with a chat-render summary of what landed, plus the next obvious play to run.

If you don't have the play definitions, ask me to paste in the relevant section of summit-shot.md and proceed.
```

---

## Send results

Slash-command send scripts (`/send-slack`, `/send-discord`, `/send-email`, `/send-circle`) live in `integrations/` and require local `.env` access. Claude Desktop hits webhooks directly:

```
Post this summary to my Slack channel using the incoming webhook at {SLACK_WEBHOOK_URL}. Format with Slack mrkdwn — bold headers, bulleted list, code blocks for URLs.

[paste the chat output from a workflow above]
```

For Discord: same shape, `DISCORD_WEBHOOK_URL`, JSON body with `content` field.

For Resend email: ask Claude to call the Resend HTTP API directly with your `RESEND_API_KEY` and `EMAIL_FROM`.

---

## Tips for Claude Desktop

- **One client per thread.** Same rule as Claude Code — context bleeds otherwise.
- **Be explicit about the MCP** if you have multiple connected. Say "Use the SearchAtlas MCP" in the first message.
- **Authorize once.** First tool call opens a browser tab. Approve. Token stays alive until you sign out of SearchAtlas.
- **Schema discovery still works.** Not sure what a tool needs? Ask: *"Call `project_management` with empty params and show me the schema."*
- **Save your favorite prompts.** Drop them into a Claude Desktop Project's instructions for reuse.
- **Outputs come as code blocks.** Where the slash command would write a file, the Desktop version returns the same content fenced in a ```html or ```markdown block. Copy, save it locally yourself — or just keep it in the chat.

---

## When you outgrow Desktop prompts

If you're running these workflows daily, full Claude Code is faster: slash commands, Mission Control wizards (3 web wizards), send integrations, workflow templates, and a `clients/{slug}/` folder per client.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/search-atlas-group/amm-toolkit/main/Scripts/quickstart-mac.sh)"
```
