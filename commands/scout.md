# /scout

Run-first diagnostic. Take a domain, pull the essentials from SearchAtlas across every pillar, and return a prioritized action plan tied to specific commands.

**`/scout` is read-only.** It does not engage OTTO projects, does not create brand vaults, does not deploy schemas, does not generate content. It diagnoses and recommends. The only writes it performs are:
1. Creates a **SearchAtlas Report Builder** report (default template, client-shareable)
2. Saves a **local self-contained HTML** record to `clients/{client-slug}/scout/{date}/index.html`

Other commands (`/onboard-client`, `/summit-shot`, `/run-*`) are what take action.

---

## Instructions

### Phase 1: Identify Target

Ask the user:
> Which domain do you want to scout? (paste a URL, or type `list` to pick from your account)

If they type `list`:
- `project_management` → `list_otto_projects` (empty params)
- Display as numbered menu, member picks a number

Capture: `domain`, `client_slug` (suggest from domain — e.g., `coastaldental.com` → `coastal-dental`), and `project_id` if one already exists.

### Phase 2: Existence Check (no creation)

Check what already exists for this domain — do **not** create anything:

- `project_management` → `find_project_by_hostname` (`hostname: <domain>`) → `project_id` or null
- `brand_vault` → `list_brand_vaults` (filter by domain) → `brand_vault_uuid` or null
- `gbp_locations_crud` → `list_locations` (filter by domain or business name) → `location_id` or null
- `business_crud` → `list_businesses` (filter by domain) → `business_id` or null
- `visibility` → `list_brands` (filter by domain) → `brand_id` or null

Mark each as `exists` or `missing`. If everything is `missing`, this is a brand-new domain — `/scout` will report that and recommend `/onboard-client`. **Do not engage anything.**

### Phase 3: Parallel Discovery

Run all groups that have a corresponding ID. Skip cleanly if the resource doesn't exist.

**Group A — OTTO & SEO Health** (only if `project_id` exists)
- `project_management` → `get_otto_project_details` → health score, page count, issue count, deployment status
- `seo_analysis` → `get_holistic_seo_pillar_scores` → Technical · Content · Authority · UX (0-100)
- `audit_management` → `list_audits` → most recent audit run date + status

**Group B — Site Explorer** (works on any domain, no project required)
- `organic` → `get_organic_keywords` (limit 100) → top kws, count, avg position
- `organic` → `get_organic_competitors` (limit 5) → top competitor domains
- `analysis` → `get_position_distribution` → counts in pos 1-3 / 4-10 / 11-20 / 21+
- `backlinks` → `get_site_backlinks` (limit 50) → backlink count
- `backlinks` → `get_site_referring_domains` (limit 25) → referring domains, top by DA

**Group C — Brand Vault** (only if `brand_vault_uuid` exists)
- `brand_vault` → `retrieve_brand_vault_details` → completeness check (description, logo, colors)
- `brand_vault` → `list_voice_profiles` → is there an active voice profile?
- `brand_vault` → `get_knowledge_graph` → is the KG populated?

**Group D — GBP** (only if `location_id` exists)
- `gbp_locations_crud` → `get_location_stats` → views, clicks, calls (last 30d)
- `gbp_locations_crud` → `list_reviews` → review count, avg rating, reply rate

**Group E — PPC** (only if `business_id` exists)
- `campaign` → `list_campaigns_with_metrics` → active campaigns, monthly spend, CTR

**Group F — LLM Visibility** (only if `brand_id` exists)
- `visibility` → `get_brand_overview` → mention count, share-of-voice
- `sentiment` → `get_sentiment_overview` → positive/neutral/negative split

Run groups in parallel. Each group should fail-soft — if one tool errors, mark that data point unavailable and continue.

### Phase 4: Score Each Pillar

| Pillar | ✅ Healthy | ⚠️ Needs Work | ❌ Missing |
|--------|-----------|---------------|-------------|
| OTTO SEO | health ≥ 70, issues < 25 | health 50–69 OR issues 25–60 | no project OR health < 50 |
| Brand Vault | exists, voice profile active, KG populated | exists but missing voice OR KG | no vault |
| Content | 30+ articles OR pillar score ≥ 70 | 5–29 articles OR pillar 50–69 | < 5 articles OR pillar < 50 |
| Authority | pillar ≥ 70, 25+ ref domains | pillar 50–69 OR 10–24 ref domains | pillar < 50 OR < 10 ref domains |
| Site Explorer | 5+ kws in pos 1-3 | 1–4 kws in pos 1-3 | 0 kws in pos 1-3 |
| GBP | location connected, reply rate ≥ 80% | connected but reply rate < 80% | no location |
| PPC | campaigns running with positive ROAS | campaigns running, no clear ROAS | no campaigns |
| LLM Visibility | monitored, SoV ≥ 30% | monitored, SoV < 30% | not monitored |

### Phase 5: Build Action Plan

Apply this rubric in order (top items take priority):

| Diagnostic finding | Recommended shot |
|---|---|
| No brand vault | `/onboard-client` |
| Brand vault exists, no active voice profile | `/summit-shot 1` (Brand Vault Setup) |
| No OTTO project | `/onboard-client` (full setup) |
| OTTO health < 70 OR open issues > 25 | `/run-seo` (monthly maintenance) |
| Authority < 40 OR < 25 referring domains | `/summit-shot 9` (PR Blast) → then `10` (Cloudstack) |
| Content < 50 OR no topical map | `/summit-shot 5` (Topical Map) → `7` (Blog Article) |
| < 5 keywords in pos 1-3 | `/summit-shot 5` (Topical Map) |
| GBP missing | `/summit-shot 8` (GBP Optimize) |
| LLM Visibility not monitored | `/summit-shot 4` (LLM Visibility Setup) |
| LLM mentions exist, SoV < 30% | `/summit-shot 17–19` (Day 5 deep dive) |
| Strong organic but no paid | `/summit-shot 14` (Branded Google Ads draft) |

Generate the top 4–6 priorities. Don't dump all 11 — pick what's most leveraged.

### Phase 6: Render Chat Output

```
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
  {keyword}                    pos {N}    {volume}/mo
  {keyword}                    pos {N}    {volume}/mo

━━ Top Competitors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {competitor_domain}          {N} shared kws
  {competitor_domain}          {N} shared kws

━━ Recommended Shots ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. {finding}                 → run /{command}
  2. {finding}                 → run /{command}
  3. {finding}                 → run /{command}
  4. {finding}                 → run /{command}

📄 Internal record:    clients/{slug}/scout/{date}/index.html
🔗 Client report:      {SA Report Builder URL or "manual create — see report builder"}

  Want me to kick off step 1 now? (yes / pick a number / no)
```

### Phase 7: Create SearchAtlas Report Builder Report

Build a client-shareable report in SA Report Builder using a default template.

**Steps:**
1. Schema discovery — call the report builder tool with empty params `{}` to find the correct create operation. Visible read-only tools include `rb_list_reports`, `rb_get_report_details`, `rb_list_reports_paginated`. The create tool may surface as `rb_create_report`, `rb_save_report`, or appear under a different prefix — discover the correct name at runtime, do not assume.
2. Default template fields:
   - Title: `{Client Name} — Scout Report ({date})`
   - Domain: `{domain}`
   - Sections to include: OTTO health, pillar scores, top keywords, top competitors, GBP stats (if applicable), LLM visibility (if applicable)
   - Audience: client-shareable (no internal-only "next shots" recommendations — those stay in the local HTML)
3. Capture the returned report URL or report ID and surface it in the chat output.

**If no create tool is available** via the MCP at this time:
- Skip silently — do not error.
- In chat output, replace the report URL with: `🔗 Client report: create manually in SA Report Builder using inputs from the local HTML`
- Continue with the local HTML save (Phase 8) regardless.

### Phase 8: Save Local Self-Contained HTML

Path: `clients/{client_slug}/scout/{YYYY-MM-DD-HHmm}/index.html`

If the `clients/{client_slug}/` folder doesn't exist yet, create it (this matches the `/onboard-client` convention; later if the user runs `/onboard-client`, that command will populate `CLAUDE.md` and `brand-profile.md` in the same folder).

**HTML requirements:**
- **Self-contained** — inline CSS, no external assets except web fonts via Google Fonts (optional, with system fallback). User can open the file directly in a browser, email it as an attachment, or commit it to git.
- **Internal-only** — this is the marketer's working doc, not the client's deliverable. Include the "Recommended Shots" section with command names. The SA Report Builder report (Phase 7) is what gets shared with the client.
- **Copy-paste friendly** — keyword lists, competitor domains, command names should all be copy-paste targets.

**HTML structure (sections in order):**
1. Header — domain, scout date, client slug
2. At-a-glance pillar status grid (7 pillars, ✅/⚠️/❌)
3. Pillar score bars (Technical, Content, Authority, UX) with the 0-100 score
4. Top 10 organic keywords (table: keyword, position, volume, URL)
5. Top 5 competitors (table: domain, shared keywords, gap keywords)
6. Backlink summary (count, top 10 referring domains by DA)
7. GBP snapshot (if applicable: views, clicks, reviews, rating, reply rate)
8. LLM visibility snapshot (if applicable: SoV, sentiment, top mentions)
9. **Recommended Shots** — numbered priority list, each item has:
   - Finding (one line)
   - Why it matters (one line)
   - Command to run (`/summit-shot 9`, `/run-seo`, etc.)
10. Notes section — empty `<textarea>` or comment block where the marketer can add context after running shots
11. Footer — "Generated by Agentic Marketing Mastermind toolkit · run again with `/scout {domain}`"

**Style:**
- Dark or light, Apple-ish minimalism (per repo design language). NOT neon SaaS purple — keep it readable, clean, neutral.
- Monospace for command names and IDs.
- System fonts: `system-ui, -apple-system, sans-serif` for body; `ui-monospace, "SF Mono", Menlo, monospace` for code.

After writing the file, print the absolute path in chat so the user can open it: `open clients/{slug}/scout/{date}/index.html`

### Phase 9: Hand-Off

If the user replies `yes` or picks a number from the priority list, invoke that command immediately with the domain pre-filled. Otherwise, exit.

---

## Output Format

Use the chat block in Phase 6 verbatim. Keep it dense, scannable, monospace-friendly.

Status emoji legend:
- ✅ healthy
- ⚠️ needs work
- ❌ missing
- ➖ not applicable (e.g., service-area business with no PPC need)

Score bar style: `████████░░` (filled blocks for score/10, rounded down).

---

## Golden Rules

- **Read-only.** No engaging projects, no creating brand vaults, no deploying anything. The only writes are the SA Report Builder report and the local HTML.
- **Skip cleanly.** If a resource doesn't exist (no GBP, no PPC, no LLM brand), mark the pillar `not set up` and continue. Never block.
- **Always discover IDs from the domain** — never hardcode. Resolve via `find_project_by_hostname`, `list_brand_vaults`, etc.
- **Schema discovery on first use** — if any tool errors, call with `{}` to get the schema, then retry. Especially important for the Report Builder create tool, which may not match the names of the visible read tools.
- **Tie every recommendation to a command.** No "improve content" — say "run `/summit-shot 5` (Topical Map) to expand coverage."
- **Pick top 4–6 priorities, not all 11.** Quality over quantity.
- **The SA Report Builder report is client-facing** (no `/summit-shot` command names — that's an internal artifact). The local HTML is internal-facing (full priority list with commands).
- **One run, three artifacts**: chat output, SA report (if create tool available), local HTML. Always all three (or two, if SA create unavailable).
