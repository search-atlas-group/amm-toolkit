# /summit-shot

Run a single play taught at the SearchAtlas Summit. One shot at a time. Each play is intentionally bounded — 1 article, 1 PR, drafts (not auto-deploys). For orchestrated end-to-end workflows, use `/run-seo`, `/run-content`, etc. For full agency-grade execution, see the Agentic Marketing Mastermind program.

`/summit-shot` complements `/scout`:
- `/scout` says **what to run**
- `/summit-shot` **runs it**

---

## Instructions

### Phase 1: Pick a Play

If the user invoked `/summit-shot` with a number (e.g., `/summit-shot 9`), skip to Phase 2 with that play.

Otherwise, show the menu:

```
🎯 Summit Shot — pick a play

Day 1 — Foundation
  1.  Brand Vault Setup           Create or refresh vault, voice profile, KG seed
  2.  OTTO Engage                 Engage project, verify install, run first audit
  3.  First Press Release         One branded PR, default distribution
  4.  LLM Visibility Setup        Connect brand, seed queries, first analysis

Day 2 — Content & Local
  5.  Topical Map                 Pillar KW → topical map (map only, no articles)
  6.  Trophy Content              One LLM-optimized trophy piece
  7.  Blog Article                One blog article (4-step content workflow)
  8.  GBP Optimize                Audit + apply quick wins (description, attributes)

Day 3 — Authority
  9.  PR Blast                    One PR + multi-network distribution
  10. Cloudstack                  Build one cloudstack
  11. Guest Post Discovery        Find opportunities (no outreach sent)
  12. Local Citations             Submit to citation networks
  13. LLM Citation Discovery      Find where you're already cited in AI answers

Day 4 — Paid (drafts only)
  14. Branded Google Ads          Create branded campaign (draft, not active)
  15. Core Google Ads             Create core campaign (draft, not active)
  16. PPC Landing Page            Generate one landing page

Day 5 — LLM Visibility Deep Dive
  17. Expand AI Topics            Suggest more topics/questions to track
  18. Refine AI Prompts           Tighten the prompts you're already running
  19. Find Visibility Gaps        Where competitors win in AI but you don't

Pick a number (or type the name):
```

### Phase 2: Resolve Context

Every play needs a target. Ask the user (unless already established by `/scout` hand-off):
> Which client/domain is this for?

Then resolve from the domain:
- `project_id` via `project_management` → `find_project_by_hostname`
- `brand_vault_uuid` via `brand_vault` → `list_brand_vaults` (filter by domain)
- `location_id` via `gbp_locations_crud` → `list_locations` (filter by domain) — only if needed
- `business_id` via `business_crud` → `list_businesses` (filter by domain) — only if needed

If the play needs a resource that doesn't exist (e.g., play 8 GBP Optimize but no GBP location connected), tell the user and exit cleanly:
> ⚠️ This play needs a connected GBP location. Run `/run-gbp` first to connect one.

### Phase 3: Execute the Play

Each play below is intentionally minimal. Confirm before any destructive write (publish, deploy, activate).

---

#### Play 1 — Brand Vault Setup

**Inputs:** domain, client name (if creating new vault)

**Steps:**
1. If `brand_vault_uuid` exists: `brand_vault` → `retrieve_brand_vault_details`. Else: ask user for client name → `brand_vault` → `create_brand_vault`.
2. `brand_vault` → `update_brand_vault_business_info` (ask for any missing fields: phone, email, address, hours)
3. `brand_vault` → `update_refine_prompt` (set voice profile — ask for tone if not on file)
4. `brand_vault` → `update_knowledge_graph` (seed with primary keyword + top 3 competitors — ask if not on file)

**Output:** confirmation of what was set, brand vault UUID, link to view in SA.

---

#### Play 2 — OTTO Engage

**Inputs:** domain

**Steps:**
1. `project_management` → `engage_otto_project` (`hostname: <domain>`)
2. `project_management` → `verify_otto_installation`
3. `audit_management` → `create_audit` (`project_id`)
4. Poll `get_otto_task_status` until SUCCESS (5–10s intervals)
5. `seo_analysis` → `get_holistic_seo_pillar_scores` → display the four pillars

**Output:** project ID, install status, first pillar scores. Suggest `/scout` for a full diagnostic.

---

#### Play 3 — First Press Release

**Inputs:** domain, topic/announcement (1–2 sentences from the user)

**Steps:**
1. `pr_create` (or schema-discover the create tool with `{}`) — title, body draft, target audience
2. Show the draft to the user. Confirm before submitting.
3. On confirm: `pr_publish` with default distribution network.

**Output:** PR ID, distribution status, link to view.

---

#### Play 4 — LLM Visibility Setup

**Inputs:** domain, brand name, top 5 competitor names (suggest from organic competitors if not provided)

**Steps:**
1. `visibility` → `create_brand` (or schema-discover) with brand + domain + competitors
2. Seed initial queries: ask user for 5–10 search queries their customers might type, OR auto-suggest from `organic` → `get_organic_keywords` (top 10 by intent)
3. `visibility` → `submit_prompts` to run first analysis
4. Poll until complete
5. `visibility` → `get_brand_overview` → display SoV, sentiment, top citations

**Output:** brand ID, first SoV reading, link to LLM Visibility dashboard.

---

#### Play 5 — Topical Map

**Inputs:** pillar keyword, target location (city/region or "national")

**Steps:**
1. `topical_maps` → `create_topical_map` with pillar keyword + location
2. Poll until complete
3. Display the map: clusters, sub-topics, suggested article titles

**Output:** topical map ID, full map preview, count of suggested titles. **Does not generate articles.** Recommend `/summit-shot 7` (Blog Article) for one, or `/run-content` for batch.

---

#### Play 6 — Trophy Content

**Inputs:** topic (one trophy piece — long, comprehensive, LLM-optimized)

**Steps:**
1. `content_generation` → `create_content_instance` with topic, mark as "trophy" (long-form, citation-rich)
2. `content_generation` → `start_information_retrieval` → poll until SUCCESS
3. `content_generation` → `start_headings_outline` → poll
4. `content_generation` → `generate_complete_article` with trophy settings (longer word count, more sources, citation hooks for LLMs)
5. Save as draft. **Do not auto-publish.**

**Output:** article ID, draft preview link, recommendation to publish via `/run-content`.

---

#### Play 7 — Blog Article

**Inputs:** article title, target keyword (suggest from topical map if available)

**Steps:**
1. `content_generation` → `create_content_instance` (standard blog)
2. `start_information_retrieval` → poll
3. `start_headings_outline` → poll
4. `generate_complete_article`
5. Save as draft.

**Output:** article ID, preview link.

---

#### Play 8 — GBP Optimize

**Inputs:** `location_id` (must already exist — if not, tell user to run `/run-gbp` first)

**Steps:**
1. `gbp_locations_crud` → `get_location` → current state
2. `gbp_locations_crud` → `get_location_recommendations` → list of suggested fixes
3. Show recommendations to user. Confirm which to apply.
4. On confirm: `gbp_locations_crud` → `bulk_apply_recommendations` (only the ones approved)
5. Optionally: `gbp_locations_crud` → `update_open_info` for description (ask user to review SA-suggested copy first)

**Output:** count of recommendations applied, before/after summary.

---

#### Play 9 — PR Blast

**Inputs:** topic, distribution scope (default: standard network; ask if user wants premium)

**Steps:**
1. `pr_create_and_write` with topic — generates draft
2. Show draft. Confirm.
3. On confirm: `pr_publish` with multi-network distribution
4. Poll `pr_get_distribution_status` and report when live

**Output:** PR ID, list of distribution targets, status.

---

#### Play 10 — Cloudstack

**Inputs:** target URL (the page to point links at), brand name

**Steps:**
1. Schema-discover the cloudstack tool (likely under `otto_*` or a dedicated wildfire/cloud tool — call `{}` to find it)
2. Build one cloudstack with default network
3. Confirm before deploying
4. On confirm: deploy and capture the cloudstack ID

**Output:** cloudstack ID, list of properties created, deployment status.

---

#### Play 11 — Guest Post Discovery

**Inputs:** domain, niche (optional — defaults to detected industry)

**Steps:**
1. Use the digital PR / outreach tools to discover guest post opportunities matching the niche
2. Schema-discover: try `dpr_list_opportunities`, `dpr_create_campaign` with type `guest_post`
3. Return a list of 10–25 opportunities with: domain, DA, contact, topic relevance

**Output:** opportunity list (saved to local HTML or CSV). **Does not send outreach.** Recommend `/run-pr` to run an outreach campaign.

---

#### Play 12 — Local Citations

**Inputs:** `business_info` from brand vault (NAP — name, address, phone)

**Steps:**
1. `gbp_init_citation_draft` → starts a citation draft
2. Auto-fill with NAP from brand vault
3. `gbp_get_available_citation_networks` → show available networks
4. Confirm submission scope
5. `gbp_submit_citation` to selected networks
6. `gbp_list_citation_submissions` → confirm status

**Output:** count of citations submitted, networks used.

---

#### Play 13 — LLM Citation Discovery

**Inputs:** domain, brand name

**Steps:**
1. `visibility` → `get_citations_overview` (or schema-discover)
2. `visibility` → `get_citations_urls` — list of URLs where the brand is cited in AI answers
3. Group by domain, sort by frequency

**Output:** table of citing domains, citation count, sample queries that triggered each citation.

---

#### Play 14 — Branded Google Ads

**Inputs:** `business_id`, brand name, primary URL

**Steps:**
1. `ppc_create_ad_group_manually` (or use the campaign-creation flow)
2. Generate branded ad copy via `ppc_generate_form_suggestions` with type `branded`
3. Show draft (campaign + ad group + ads). Confirm.
4. **Save as draft. Do not activate.** User can review in SA UI and push to Google Ads when ready.

**Output:** campaign ID (draft state), ad copy preview, link to review in SA.

---

#### Play 15 — Core Google Ads

**Inputs:** `business_id`, primary keywords (suggest from organic top kws), landing page URL

**Steps:** Same as Play 14, but with `core` (non-branded) ad copy and target keywords.

**Output:** campaign ID (draft), ad copy preview.

---

#### Play 16 — PPC Landing Page

**Inputs:** target keyword, offer description, brand vault UUID (for tone)

**Steps:**
1. Schema-discover the PPC LP generator (try `cs_create` with template `ppc_lp` or similar)
2. Generate landing page draft
3. Show preview URL
4. **Save as draft. Do not publish.**

**Output:** landing page ID, preview URL, recommendation to review in SA.

---

#### Play 17 — Expand AI Topics

**Inputs:** `brand_id` (from LLM Visibility), domain

**Steps:**
1. `visibility` → `list_topics` → current topics being tracked
2. `visibility` → `list_queries` → current queries
3. Use the brand vault + organic data + `topical_maps` to suggest 10–20 NEW topics/questions worth tracking
4. Show suggestions. Confirm which to add.
5. On confirm: `visibility` → `add_topic` and `add_query` for each approved item.

**Output:** count of topics/queries added, full updated list.

---

#### Play 18 — Refine AI Prompts

**Inputs:** `brand_id`

**Steps:**
1. `visibility` → `list_queries` with current performance data
2. Identify low-performing queries (no brand mention, ambiguous intent, too broad)
3. For each, suggest a tighter rewrite
4. Show before/after table. Confirm replacements.
5. On confirm: `visibility` → `remove_query` (old) + `add_query` (new) per pair.

**Output:** count of prompts refined, before/after summary.

---

#### Play 19 — Find Visibility Gaps

**Inputs:** `brand_id`

**Steps:**
1. `visibility` → `get_competitor_share_of_voice` → competitor SoV per topic
2. `visibility` → `get_competitor_visibility_rank` → competitor rank per query
3. Identify queries where competitors get cited but the brand doesn't
4. Cross-reference with the topical map: are these covered in content? Surface gaps.
5. Tag gaps as: "no content yet" / "content exists but not optimized for AI" / "competitor brand mentioned more"

**Output:** gap report (markdown table). For each gap, suggest the next shot:
- "no content" → `/summit-shot 6` (Trophy Content) on this topic
- "exists but not optimized" → recommend re-grading via `cg_run_content_grader`
- "competitor brand mentioned more" → `/summit-shot 9` (PR Blast) to push brand mentions

---

### Phase 4: Save Run Record

After the play executes, append a one-line record to `clients/{client_slug}/summit-shots.log`:

```
{ISO timestamp} · play {N} · {play_name} · {result_summary}
```

If `clients/{client_slug}/` doesn't exist yet, create the folder first.

### Phase 5: Suggest Next Move

After every play, end with:
```
✅ Play {N} ({play_name}) complete.

Next moves to consider:
  • {related_play_or_command}
  • {related_play_or_command}

Run /scout {domain} to re-check pillar status.
```

---

## Output Format

Per play. Each play returns:
1. Status header (`✅ Play N — {name}`)
2. What was created/changed (1–3 bullets)
3. Resource IDs and SA links
4. Suggested next moves (2–3 options)

Keep it tight. No paragraphs. Bullets or tables.

---

## Golden Rules

- **One shot at a time.** Each play is atomic. Don't chain plays in one invocation. The user runs `/summit-shot` again to run the next one.
- **Bounded scope.** 1 article (not 10), 1 PR (not a campaign), draft (not deployed). Quality matters more than volume at this tier.
- **Confirm before destructive writes.** Publishing PRs, activating ads, deploying schemas — always show a draft and ask `yes/no`.
- **Drafts by default.** Day 4 (paid) plays save as drafts. The user reviews and pushes to Google Ads themselves when ready.
- **Schema discovery on every first call.** Tool names may not match the visible MCP set. Call with `{}` to get the schema, then retry with the correct params.
- **Skip cleanly when prerequisites are missing.** If GBP isn't connected and the user picks Play 8, tell them and exit. Don't auto-engage — that's a `/run-gbp` job.
- **Always log the run.** Append to `clients/{slug}/summit-shots.log` so the user has a paper trail of what was run when.
- **Tie next moves to commands.** Every play ends with 2–3 suggested follow-ups, each pointing to a specific command.
- **No big guns.** This command is the summit takeaway, not the AMM full-stack. If a user wants end-to-end orchestration, they upgrade.
