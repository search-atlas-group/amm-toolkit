---
name: sa-build-website
description: Generate a brand new marketing website from brand vault data via SearchAtlas Website Studio — guided end-to-end from brand intake through market research, design selection, content generation, and live publish.
---

# /sa-build-website

End-to-end guided workflow to plan, design, build, and launch a **brand new website** using the SearchAtlas toolchain. The operator gives us a domain, a small handful of fields, and (optionally) some brand materials — Claude + SA MCP do the rest. Final launch target: Web Studio.

> **For redesigning or replacing an existing site, use `/sa-rebuild-website` instead.** That command consumes scout's output and focuses on design execution. This command is for greenfield only.

## Data flow — Brand Vault is the single source of truth

```
Operator → Brand Vault → Website Studio → Live site
```

Every operator input (services, location, brand colors, voice notes, dropped logos, design style picked, etc.) gets pushed into the Brand Vault FIRST via the appropriate `bv_*` tool. Then Website Studio reads from BV during page creation. WS never reads operator input directly.

This means:
- Operator types each piece of info once — propagates everywhere via BV
- Two-way sync: WS-side edits push back to BV before publish
- Other commands (`/sa-run-content`, `/sa-run-pr`, `/sa-run-seo`) all read the same BV downstream

**Design principles:** copy-before-design, theme-first approval, small-chunks iteration, page-type tiering, industry aesthetic library.
**Workflow gates:** Pre-Build HITL gate, budget input, multi-format intake, BV auto-crawl when missing, Website Studio MCP for build/publish.

## Prerequisites

- `searchatlas` MCP server connected. If missing, stop and tell the user to add it.
- Clean project directory.
- Operator has client consent if working on a client domain.

---

## Phase 0 — Identify Target

Ask:

> Which domain are we building for? (paste the URL or the domain you've registered for this build)

Capture `domain` and suggest `client_slug`.

---

## Phase 0.5 — Quick Existence Check (BV + GBP only)

For greenfield, we only check the 2 SA assets that exist independent of having a website:

| Tool | Captures |
|---|---|
| `mcp__searchatlas__cg_list_brand_vaults` (filter by domain) | `brand_vault_uuid` if exists |
| `mcp__searchatlas__gbp_list_locations` (filter by domain/name) | `gbp_location_id` if exists |

**Do not check:** OTTO, PPC, LLM Visibility. These require a live crawlable site — `/sa-run-seo` provisions them once the site has had time to be crawled.

Display brief check summary:

```
🏷️  Brand Vault   {emoji} {found / will create}
📍  GBP location  {emoji} {found / handled by /sa-run-seo if missing}
```

---

## Phase 1.0 — Multi-Format Operator Intake

Ask:

```
Drop everything you already have. We'll use it to populate the brand vault
and inform every downstream artifact. Skip if you don't have anything.

Accepted formats: images, text, links, video.
```

Save dropped files under `inputs/` with `inputs/manifest.json`. Per format:

- **Images** — use Claude vision to extract dominant colors, OCR text, visual style. Persist to manifest.
- **Text** — parse for voice cues, messaging pillars, words to use/avoid.
- **Links** — fetch each, extract title, meta description, services mentioned, voice cues.
- **Video** — save the file. Surface that transcription is a later iteration.

---

## Phase 1.1 — Brand Vault: Use OR Auto-create + Auto-fill

### Path A — BV exists

Pull all 4 surfaces in parallel:

| Tool | Captures |
|---|---|
| `mcp__searchatlas__bv_get_details` | Name, domain, logo, colors, description |
| `mcp__searchatlas__bv_get_business_info` | Address, hours, phone, email, service areas, social |
| `mcp__searchatlas__bv_get_knowledge_graph` | Entities, topic clusters, competitor domains |
| `mcp__searchatlas__bv_list_voice_profiles` | Tone, writing style, active voice |

Display confirmation. Operator confirms or edits (edits push back via `bv_update*`).

### Path B — BV missing → auto-create + crawl-populate

**Do not halt.** Auto-crawl, then create + populate:

```
Sources crawled in parallel:
  · inputs/manifest.json (operator materials)
  · WebFetch on domain (in case there's placeholder content)
  · mcp__searchatlas__se_get_organic_competitors → top 2 → WebFetch
  · mcp__searchatlas__llmv_get_brand_overview (if business has any prior LLM mentions)
  · mcp__searchatlas__se_get_organic_keywords (for the business name as branded search)
```

Then:

```
mcp__searchatlas__bv_create                — create empty vault
mcp__searchatlas__bv_update_business_info  — fill from crawl + operator materials
mcp__searchatlas__bv_update                — colors (from logo) + voice (from text)
mcp__searchatlas__bv_update_knowledge_graph — entities + competitors
mcp__searchatlas__bv_upload_image          — upload logo (if dropped)
```

Present pre-fill block:

```
Brand Vault — pre-filled from crawl

✅  Business name      {value}                         [from {source}]
✅  Domain             {domain}                         [explicit]
✅  Industry           {value}                          [from {source}]
✅  Primary location   {value}                          [from {source}]
🟨  Brand colors       {value}                          [from {source}]
🟨  Voice              {value}                          [from {source}]
❌  Target persona     —                                [NEEDS YOU]
❌  Avoid list         —                                [NEEDS YOU]

{N} of {total} fields auto-filled. {gap_count} need your input.

Pick:
  1. Fill the gaps now (recommended)
  2. Proceed — flag gaps in pre-build review
  3. Edit any of the auto-filled fields first
```

For pure greenfield (no operator materials AND no prior business presence anywhere), the auto-crawl produces little. Default to asking 4 manual fields: business name, industry, primary location, target persona one-liner.

---

## Phase 1.2 — Budget Tier

```
What's the client's monthly budget for ongoing marketing services?
(Captured here, used by /sa-run-seo to size the post-launch cadence — PR, cloud
stacks, content frequency. The publish workflow itself doesn't act on this.)

  1. Starter         < $2K / mo
  2. Growth          $2K – $5K / mo
  3. Scale           $5K – $10K / mo
  4. Enterprise      $10K+ / mo (custom-scoped)
  5. Don't know yet  (defaults to Growth; flagged in pre-build summary)
```

Persist to `budget-tier.json`.

---

## Phase 1.3 — Brand Strategy Synthesis

Claude synthesizes `brand-strategy.md` from:

- BV fields (post Phase 1.1)
- Operator-dropped text materials
- Competitor crawl results
- Logo color + visual style cues

Operator reviews. Edits flow back to BV via `bv_update`.

---

## Phase 1.5 — Target Market (added 2026-05-19)

Three new operator inputs that seed Phase 2's market-evidence research. See [[2026-05-19-phase2-market-research-design]] for full design.

### Operator input prompts

```
1. INDUSTRY (required) — Two-tier picker
   Tier 1: Pick broad category (~20 buckets)
   Tier 2: Pick specific GBP leaf category (filtered list)
   Auto-highlights likely tier 1 from your services list.

2. TARGET KEYWORDS (3–5 recommended, optional)
   "What do you want to rank for?"
   Each keyword runs through se_lookup_keyword inline → shows volume + intent + difficulty.
   If you give us fewer than 3 valid keywords, we auto-derive seeds from your services + location + industry.

3. KNOWN COMPETITORS (up to 3, optional)
   "Any competitors you already know about?"
   URLs validated client-side. We merge these with SA-discovered competitors in Phase 2.
```

### Write to BV immediately

| Tool | Captures |
|---|---|
| `mcp__searchatlas__bv_update_business_info` | Industry → BV `primary_category` |
| `mcp__searchatlas__bv_update_knowledge_graph` | Target keywords → BV |
| `mcp__searchatlas__bv_update_knowledge_graph` | Named competitors → BV |

### Auto-derive fallback (no block on sparse input)

If `keywords.length < 3` after operator input:
```
auto_seeds = deriveSeedKeywords(services × location × industry)
state.targetMarket.derivedSeeds = auto_seeds
state.targetMarket.derived = true
```

Surfaces in Phase 4.5 HITL summary so operator sees what was auto-inferred.

---

## Phase 2 — Market-Evidence Research (REWORKED 2026-05-19)

Pure research. No operator interaction. Two parallel waves fire SA tools simultaneously, then synthesis produces the proposed sitemap. ~15–20 seconds total.

### Wave 1 (5 tools, parallel — fire simultaneously)

| Tool | Output |
|---|---|
| `mcp__searchatlas__se_lookup_keyword` (per target KW) | volume + intent + difficulty |
| `mcp__searchatlas__se_get_serp_overview` (per target KW) | who's ranking |
| `mcp__searchatlas__gbp_list_categories` | category taxonomy |
| `mcp__searchatlas__se_get_organic_competitors` (per target KW) | auto-discovered competitor set |
| `mcp__searchatlas__se_get_serp_features` (per target KW) | LOCAL PACK, FAQ, IMAGE PACK, etc. |

Wave 1 → merge: `competitor_set = operator_competitors ∪ auto_competitors` (final 3–5).

### Wave 2 (4 tools, parallel — fire after Wave 1)

| Tool | Output |
|---|---|
| `mcp__searchatlas__se_get_indexed_pages` (per competitor) | real page structures |
| `mcp__searchatlas__se_analyze_keyword_gap` (between competitors) | unclaimed keyword territory |
| `mcp__searchatlas__cg_create_topical_map` (seeded with kw_data) | content clusters |
| `mcp__searchatlas__cg_topic_suggestions` (`brand_vault_uuid`) | topic suggestions from BV |

### Synthesis (no SA calls, just merge)

Combine competitor_pages + gap_clusters + topical_map + bv_topics + operator services + location. Produce proposed page candidates with per-page evidence object:

```json
{
  "slug": "dental-implants",
  "title": "Dental Implants",
  "tier": "service",
  "evidence": {
    "competitor_count": 4,
    "competitors_with_page": ["...", "..."],
    "kw_cluster": [...],
    "kw_total_volume": 2400,
    "intent": "transactional",
    "serp_features": ["LOCAL_PACK", "FAQ"],
    "gap_score": 8,
    "source": ["competitor_pages", "gap_clusters", "operator_services"]
  }
}
```

Output: `proposed-sitemap.json` at project root.

### Streaming UI

Each wave fires `onWaveComplete(N, results)`. Operator sees real-time status:
- *"Wave 1 ✓ · 5 competitors confirmed, 12 target KWs validated"*
- *"Wave 2 ✓ · 67 competitor pages indexed, 14 keyword gaps identified"*
- *"Sitemap proposed · 23 pages across 5 tiers"*

### Rank tracking (after synthesis)

```
mcp__searchatlas__krt_create_project (domain)      — rank tracking project
mcp__searchatlas__krt_bulk_add_keywords (target KWs) — monitor from day 0
```

### Outputs

- `proposed-sitemap.json` — full proposed sitemap with per-page evidence
- `keyword-map.md` — primary + secondary KWs per page
- KRT project provisioned

---

## Phase 2.5 — Per-Page Approval Walkthrough (added 2026-05-19)

Operator walks every proposed page. **Each card is text-only — NO pre-rendered HTML, NO screenshots, NO iframe previews.** WS handles real rendering in Phase 5.

### Per-page card content

**Lean view (default):**
- Sitemap tree map (Unicode tree, showing where this page sits in the structure)
- Page title + tier badge
- One-line summary

**Expanded view (click to deep-dive):**
- Slug + page type rationale
- Target keywords with volume/intent/difficulty
- Competitor evidence (text: "4 of 5 competitors have this — competitor1.com, ...")
- SERP feature names
- Content gap details
- Recommended section outline (H1, hero, sections, CTAs, schema type)

### Operator actions per page

```
For each proposed page:
  Show lean card (instant render — text only)
  Operator picks:
    Approve → page enters final queue
    Reject  → page dropped
    Edit    → modify title / keywords / section outline → then approve
```

### Output

- `page-build-queue.csv` — locked queue of approved pages (drives Phase 3+)

### Gating

Walkthrough is **required**. No bulk-skip. Operator must walk every page before Phase 3 starts.

---

---

## Phase 3 — Design Style Selection

The operator picks 1 of 6 design styles. WS uses it as the rendering template for every page.

| Style | What it looks like | Best for |
|---|---|---|
| **Modern Minimal** | Whitespace, sans-serif, photography-led, monochromatic | Healthcare, finance, professional services |
| **Editorial** | Magazine layouts, oversized type, asymmetric grids | Fashion, hospitality, lifestyle, luxury |
| **Bento Grid** | Card-based modular layouts (Apple-style) | SaaS, tech, modern e-commerce |
| **Glassmorphism** | Frosted-glass panels, layered translucency | Fintech, premium services, AI products |
| **Bold / Brutalist** | High contrast, oversized type, raw aesthetic | Creative agencies, startups, edgy brands |
| **Warm Organic** | Earthy palette, soft rounded shapes, hand-drawn | Wellness, food, sustainable brands |

### Push style choice to BV + WS

```
mcp__searchatlas__bv_update (design_style, derived color tokens) — BV records the style choice
mcp__searchatlas__ws_create_project (..., design_style) — WS uses style as rendering template
```

### Operator edits before publish

After Phase 5 pushes pages into WS, the operator previews and can:
- Adjust any token (color, font, spacing) → changes push back to BV via `bv_update`
- Swap the entire style → re-run Phase 5 against new style
- Override per-page treatments

Nothing is committed until Phase 6.5 publish.

---

## Phase 4 — Content & Copy

For each row in `page-build-queue.csv`:

| Tool | Purpose |
|---|---|
| `mcp__searchatlas__cg_dkn_generate_article` (page + brand voice + KW targets) | Generate copy block |
| `mcp__searchatlas__se_lookup_keyword` (primary KW) | Volume + intent sanity check |
| `mcp__searchatlas__cg_run_content_grader` (article) | Score against KW + readability |

Output: `copy/[slug].md` per page + `image-list.md`.

---

## Phase 4.5 — Pre-Build Gate (HITL)

**No MCP calls.** Read all artifacts produced so far. Assemble single summary block. **Only path into Phase 5.**

```
PRE-BUILD REVIEW for {domain} — {business_name}

Brand
  Domain         {domain}
  Business       {business_name} · {primary_location}
  Voice          {voice}
  Colors         {primary} · {accent}

Budget tier
  {tier_name} ({range})
  → Captured for /sa-run-seo (post-launch cadence sized there, not here)

Site plan
  {N} pages: {core} Core · {service} Service · {location} Location · {landing} Landing · {compliance} Compliance
  KW baseline: 0 (greenfield)

Design
  Archetype       {archetype_name}
  Theme approved  {yes/no}

Copy
  Pages with copy approved   {N} / {total}

Build target
  Stack          Claude generates pages → pushed directly to Website Studio via SA MCP
  Reversible?    Yes — Website Studio preview state · no production publish until Phase 6.5

Issues flagged
  {list or "none"}

> Approve to start the build? (yes / edit [section] / cancel)
```

Behavior:
- `yes` → proceed to Phase 5
- `edit [section]` → jump to phase, apply edit, re-present
- `cancel` → halt; preserve artifacts

---

## Phase 5 — Build & Push to Website Studio

Every page lives in Website Studio from the moment Claude finishes generating it. No external repos, no preview hosts. **WS reads from BV — operator inputs already landed there in earlier phases.**

### Step 1 — Verify BV is complete, then scaffold WS

```
Quick BV completeness check:
  ✅ Business name + location populated         bv_get_business_info
  ✅ Voice profile present                       bv_list_voice_profiles
  ✅ Knowledge graph (entities, competitors)    bv_get_knowledge_graph
  ✅ Brand assets uploaded (logo, etc.)         bv_get_details
  ✅ Design style + color tokens set             bv_get_details
```

Optional: `mcp__searchatlas__kg_validate_completeness` — sanity-check the KG has enough nodes for the build.

Then scaffold WS bound to the populated BV:

| Tool | Purpose |
|---|---|
| `mcp__searchatlas__ws_create_project` (`domain`, `business_name`, `brand_vault_uuid`, `design_style`) | Create the WS project bound to the populated BV |
| `mcp__searchatlas__ws_ensure_containers_running` | Make sure WS build infrastructure is ready |

### Step 2 — Build loop (per page)

```
For each row in page-build-queue.csv:
  1. Load: brand-strategy.md + style-guide.html + copy/[slug].md
  2. Claude generates page HTML using approved components + copy
  3. Push to Website Studio:
       mcp__searchatlas__ws_create_project (homepage on first iteration)
       per-page push for service / location / landing / compliance pages
  4. Upload images: mcp__searchatlas__bv_upload_image + WS asset references
  5. Verify page renders in Website Studio preview (no DNS yet)
  6. Next page
```

Service / location pages with shared structure: Claude generates from template loop programmatically; each push to WS happens in batch.

### MCP touchpoints during build

| Tool | When |
|---|---|
| `mcp__searchatlas__ws_create_project` | Initial scaffold + page additions |
| `mcp__searchatlas__ws_get_project` | Verify state mid-build |
| `mcp__searchatlas__bv_upload_image` | Each final site image — vault holds canonical assets |
| `mcp__searchatlas__otto_get_task_status` | Poll long-running operations |

---

## Phase 6 — QA (against Website Studio preview)

QA runs against the WS preview — same platform that will run live, no environment mismatch.

| Check | How |
|---|---|
| Pages load, no console errors | Open each WS preview URL |
| Mobile breakpoints | 375 / 768 / 1280 — WS viewport inspector |
| Internal links resolve | WS crawl against preview |
| Meta titles + descriptions | Per page in WS settings |
| Image alt text | Per image |
| Lighthouse > 85 | Per page against WS preview URL |
| Schema markup | Service/local pages |

---

## Phase 6.5 — Publish via Website Studio (THE ULTIMATE GOAL)

Everything is already in Website Studio (Phase 5 put it there). This step is the explicit publish + DNS cutover.

```
Final pre-publish check:
  ✅ {N} pages built and pushed to WS
  ✅ WS preview state confirmed
  ✅ Brand Vault locked
  ✅ Sitemap ready for submission

Ready to publish {domain} on Website Studio? (yes / cancel)
```

On `yes`:

```
1. Final pre-publish sweep — confirm all pages render in WS preview
2. Publish: mcp__searchatlas__ws_publish_project (project_id)
3. DNS cutover instructions emitted (operator runs at registrar)
4. SSL provisioning auto-handled by WS
5. Each page verified on production domain
6. Submit sitemap to Search Console + Bing Webmaster Tools
```

This is where the operator promise is delivered: they triggered the command, filled in 8 fields, got a complete live website on Website Studio.

### Two URLs at workflow end — both surfaced to the operator

`ws_publish_project` returns the WS-hosted URL (e.g. `{slug}.ws.searchatlas.com`) which is immediately resolvable. The operator's custom domain requires DNS cutover (the operator points their domain at Website Studio per the instructions emitted at this step) plus SSL auto-provisioning — typically minutes to hours depending on DNS propagation. The workflow surfaces BOTH URLs at completion so the operator can verify the site is live on WS immediately while DNS catches up.

**Workflow complete.** Emit a final block:

```
✅ Site is live on Website Studio

Live now:        https://{slug}.ws.searchatlas.com   ← resolves immediately
Custom domain:   https://{domain}                    ← pending DNS cutover
                 (DNS propagation: minutes to hours; SSL auto-provisions once DNS resolves)

What's next:
  /sa-run-seo {domain}   — provisions OTTO, LLM Visibility, GBP linkage, and
                           sizes the ongoing cadence (cloud stacks, PRs,
                           articles, DPR) against the live, crawled site.
```

The publish workflow ends here. Real post-launch data (pillar scores, LLM tracking, rank tracking deltas) takes hours-to-days of crawl latency — synchronous post-launch provisioning would just create empty projects. `/sa-run-seo` runs that cadence properly against a site that's been live long enough to be crawled.

---

## What this command does NOT do

- Touch an existing site — that's `/sa-rebuild-website`
- Ingest scout output — also `/sa-rebuild-website`
- Inherit OTTO baselines — greenfield has no baseline
- Skip Phase 4.5 HITL gate — hard halt; no override
- Auto-publish to production without Phase 6.5 approval
- Provision OTTO/PPC/LLMV/DPR or run any post-launch SEO cadence (cloud stacks, articles, PRs) — that's `/sa-run-seo`'s job once the site is live and crawled

## Operator-facing input summary

The 8 fields the operator fills in. Everything else is auto-generated:

1. **Domain**
2. **Business name + primary location** (if not in BV)
3. **Services list**
4. **Budget tier** (1 of 5)
5. **Drop materials** (optional)
6. **Design archetype** (1 of 4)
7. **Approve HITL gate** (yes/edit/cancel)
8. **Approve Web Studio launch** (yes/cancel)

## Related skills + commands

- `launch-website` — upstream planning skill; this command can consume its `plan.md` output as a richer Phase 2 seed
- `/sa-onboard-client` — client setup; usually precedes this command
- `/sa-rebuild-website` — for redesigning existing sites
- `/sa-run-seo` — picks up once the site is live and crawled; provisions OTTO/LLMV/PPC and runs the ongoing cadence (cloud stacks, PRs, articles, DPR) sized by `budget-tier.json`
