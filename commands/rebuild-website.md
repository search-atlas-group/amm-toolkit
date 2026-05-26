---
name: rebuild-website
description: Refresh or regenerate an existing website via SearchAtlas Website Studio — consumes scout diagnostic output as source of truth, executes the redesign/migration layer, and publishes the rebuilt site via MCP.
---

# /searchatlas:rebuild-website

End-to-end design execution workflow for **redesigning or replacing an existing website**. Consumes scout's diagnosis output as the source of truth for what exists. Focuses on the design + migration layer — skips re-diagnosing.

> **For brand new sites with no prior presence, use `/searchatlas:build-website` instead.** That command invents content from minimal seed input. This command transforms existing assets per operator-confirmed decisions.

**Premise:** Scout already mapped the site. You have the inventory, OTTO pillar scores, keyword positions, content gaps, and issue list. This command takes that output as input and executes the rebuild.

## Prerequisites

- `searchatlas` MCP server connected
- Scout has been run on this domain (scout output file in hand)
- Clean project directory
- Operator has client consent

## Spec reference

Source of truth: `_brain/projects/amm-mastermind/specs/website-rebuild-spec.md`. This command implements that spec.

---

## Phase 0 — Identify Target + Ingest Scout Output

Ask:

```
Which domain are we rebuilding?
Drop the scout output file (HTML, JSON, or markdown export) for that domain.
```

Capture:
- `domain`
- `scout_output_path`
- `scout_run_date` (parsed from scout output frontmatter)

### Parse scout output

Scout's output typically includes:

| Section | What it gives us |
|---|---|
| Site inventory | Every page scout crawled — URL, title, content type, last-modified |
| OTTO pillar scores | Technical, Content, Authority, UX (0–100 each) |
| Keyword performance | Ranking keywords + positions |
| Content gaps | Topics competitors cover but the site doesn't |
| Top issues | Performance, schema, broken links, thin content |
| Backlink profile | Referring domains, anchor text |
| HTML page exports (if scout included them) | Raw content per page for use in redesign |

Persist parsed structure to `scout-data.json` in project root.

### Validate freshness

If `scout_run_date` > 30 days old:

```
Scout report is N days old. Two options:
  1. Rebuild against this snapshot (faster, but may miss recent changes)
  2. Re-run /searchatlas:scout first (recommended for accuracy)

Pick a number.
```

---

## Phase 1 — SA Asset Inheritance + Operator Control

For a rebuild, all SA assets typically already exist. Pull them in parallel:

| Tool | Captures |
|---|---|
| `mcp__searchatlas__otto_find_project_by_hostname` | OTTO project · pillar scores already in scout output |
| `mcp__searchatlas__cg_list_brand_vaults` | Brand Vault (may need editing for new direction) |
| `mcp__searchatlas__gbp_list_locations` | GBP (usually preserved through rebuild) |
| `mcp__searchatlas__ppc_list_businesses` | PPC if running ads |
| `mcp__searchatlas__llmv_list_projects` | LLMV if tracking |

### OTTO issue clusters (parallel)

After OTTO project is found, pull actionable issue groups:

| Tool | Captures |
|---|---|
| `mcp__searchatlas__otto_get_issues_by_type` | Issue clusters keyed by type (thin content, schema, broken links, performance, etc.) |

Scout gives aggregate pillar scores; this gives per-page actionable tags. Phase 2 default mapping uses these — pages flagged "thin content" are auto-suggested as "Keep + rewrite"; pages flagged "broken links" get prioritized for redesign attention.

Persist to `otto-issues.json`.

### Asset-level operator control

For each found asset, ask:

```
{icon} {asset_name} — {status}

What would you like to do with this one?

  1. Use as-is — proceed with the existing record
  2. Edit — modify specific fields before continuing (changes push back to SA)
  3. Add data — extend without changing existing
  4. Reject + start fresh — preserve existing in SA, scaffold new one alongside

Pick a number.
```

### Per-asset action availability + tool calls

| Asset | Use | Edit | Add data | Reject + fresh |
|---|---|---|---|---|
| OTTO project | ✓ | `mcp__searchatlas__otto_update_crawl_settings` | — | `mcp__searchatlas__otto_create_audit` |
| Brand Vault | ✓ | `mcp__searchatlas__bv_update*` | `mcp__searchatlas__bv_update` (additive) | `mcp__searchatlas__bv_create` |
| GBP location | ✓ | `mcp__searchatlas__gbp_update_location` | `mcp__searchatlas__gbp_add_service_areas` | new init |
| PPC business | ✓ | `mcp__searchatlas__ppc_update_business` | `mcp__searchatlas__ppc_create_products` | `mcp__searchatlas__ppc_create_business` |
| LLM Visibility | ✓ | `mcp__searchatlas__llmv_add_query` | same as Edit | `mcp__searchatlas__llmv_create_project` |

Persist to `asset-decisions.json`.

**For rebuilds, this step is critical.** The existing data is the starting point, but a brand direction change means the old BV voice profile is wrong, or a service line was discontinued, etc. Operator must consciously choose what to inherit.

---

## Phase 2 — Old → New Page Mapping

The rebuild-specific phase. System reads scout's page inventory and asks the operator, per page:

| Action | What it means | Required output |
|---|---|---|
| Keep + redesign | Same URL, new design, same copy | Component remap |
| Keep + rewrite | Same URL, full copy rewrite | New brief + design |
| Merge | Combine with another old page into one new page | Merged brief + redirect |
| Delete | Drop from new site | Redirect target |
| New | Page didn't exist before | Fresh brief (greenfield-style for this row) |

### Suggest a default map

Based on scout's data + pillar scores, system proposes:

- Pages with Authority > 60 → "Keep + redesign" (preserve link equity)
- Pages with Content < 40 → "Keep + rewrite" (low-value content gets refreshed)
- Pages flagged orphan / 0 inbound links → "Delete"
- Content gaps from scout → "New" candidates
- Pages with traffic above threshold → "Keep" (any version)

Present the default map for operator review:

```
PROPOSED REBUILD MAP for {domain}

Existing pages (from scout): {N}
Proposed action per page:

[Keep + redesign]   {N} pages   — preserve link equity, refresh design
[Keep + rewrite]    {N} pages   — refresh both copy and design
[Merge]             {N} → {M}   — combine related thin content
[Delete]            {N} pages   — redirect targets assigned
[New]               {N} pages   — fill content gaps scout identified

Total new site: {N} pages

Type "accept" to use this map, or "adjust [old_url]" to change a specific decision.
```

### Link + anchor preservation (high-Authority Keep pages)

For every row where `action ∈ {Keep + redesign, Keep + rewrite}` AND `authority > 60`, fire SA backlink intelligence so the new H1/title and internal-link plan preserves semantic alignment with what already points at the page:

| Tool | Purpose | Scope |
|---|---|---|
| `mcp__searchatlas__se_get_anchor_text` | Anchor text distribution | Per high-Authority Keep page |
| `mcp__searchatlas__se_get_referring_domains` | Referring domains protecting page equity | Per high-Authority Keep page |
| `mcp__searchatlas__se_get_link_network_graph` | Full-site internal linking pattern | Once, full domain |

Output: `link-preservation.json` keyed by old URL — consumed by Phase 5 internal-link remap.

### Output

- `page-rebuild-map.csv` — old URL · action · new slug · redirect target
- `redirect-map.csv` — final 301 redirect table
- `new-page-queue.csv` — pages needing fresh build (subset of rebuild-map)
- `link-preservation.json` — anchor + referring-domain data for high-Authority Keep pages

---

## Phase 2.3 — Market Evidence Enrichment for NEW Pages

Runs parallel after Phase 2's default page map is built. Fires **only** for rows where `action = New` (the gap candidates scout identified). Scout flagged these as missing content opportunities — this phase pulls fresh market evidence so the Phase 2.5 walkthrough decisions are grounded in current SERP reality.

### Tools (parallel per NEW candidate)

| Tool | Purpose |
|---|---|
| `mcp__searchatlas__se_lookup_keyword` | Volume, intent, difficulty for each candidate target KW |
| `mcp__searchatlas__se_get_serp_overview` | Who currently ranks for the candidate KW |
| `mcp__searchatlas__se_get_indexed_pages` | Per top competitor — what page-type is winning today |
| `mcp__searchatlas__se_get_serp_features` | Current SERP features (LOCAL_PACK, FAQ, IMAGE_PACK) — informs Phase 5 schema |
| `mcp__searchatlas__cg_topic_suggestions` | Brand-Vault-driven validation per candidate |

Output: `new-page-evidence.json` keyed by candidate slug. Feeds Phase 2.5 card content.

---

## Phase 2.5 — Per-Page Approval (NEW pages only)

Walk every `action = New` candidate as a text-only card. **Keep / Rewrite / Merge / Delete stay in the Phase 2 list view** — scout's rankings/traffic data is enough for those. NEW pages get the walkthrough because they have the least existing context.

### Card format (text-only)

```
{tier_badge}  {new_slug}

site/
├── about/
├── services/
│   ├── existing-service-1/
│   └── existing-service-2/
└── {new_slug}/   ← THIS PAGE

One-liner: {what this page is for, plain English}

[Expand] — KW data · Competitor evidence · SERP features · Section outline
```

Expanding pulls from `new-page-evidence.json`:
- **KW data:** target KW · vol · intent · difficulty
- **Competitor evidence:** top 3 ranking page types + structure
- **SERP features:** features detected on the live SERP
- **Section outline:** proposed H1/H2/H3 structure derived from competitor analysis + BV voice

### Per-card actions

- **Approve** — Card locks in; row in `new-page-queue.csv` marked `approved`
- **Reject** — Row removed from queue; tracked separately for post-rebuild content backlog
- **Edit** — Inline edit slug, target KW, section outline, or one-liner; then approve

**Phase 2.5 gates Phase 3** — no design style pick until every NEW row has a decision.

Output: `new-page-queue.csv` updated with operator decisions.

---

## Phase 3 — Redesign Preferences

### 3.1 — What stays, what changes

```
For the redesign, what carries over from the current site?

Logo            (1) Keep   (2) Upload new
Primary color   (1) Keep ({current_hex})   (2) Pick new
Voice/tone      (1) Keep ({current_profile})   (2) Edit voice profile
```

If operator picks "Pick new" or "Upload new," capture the new value and stage a `bv_update` for Phase 1's asset-decision sweep.

### 3.2 — Pick a NEW design style

6 current web design patterns. WS uses the picked style as the rendering template:

| Style | What it looks like | Best for |
|---|---|---|
| **Modern Minimal** | Whitespace, sans-serif, photography-led | Healthcare, finance, professional services |
| **Editorial** | Magazine layouts, oversized type, asymmetric grids | Fashion, hospitality, lifestyle, luxury |
| **Bento Grid** | Card-based modular layouts (Apple-style) | SaaS, tech, modern e-commerce |
| **Glassmorphism** | Frosted-glass panels, layered translucency | Fintech, premium services, AI products |
| **Bold / Brutalist** | High contrast, oversized type, raw aesthetic | Creative agencies, startups, edgy brands |
| **Warm Organic** | Earthy palette, soft rounded shapes, hand-drawn | Wellness, food, sustainable brands |

If operator picks the SAME style as the current site (detected from scout's brand inference):

```
You picked {style} — that's the same as the current site.

Are you sure this is a rebuild, or are you actually after a content refresh?
For content-only updates, /searchatlas:run-content may be the right command instead.

  1. Yes, this is a rebuild — same style, different execution
  2. Switch to /searchatlas:run-content
  3. Pick a different style
```

### 3.3 — Optional: drop scout's HTML for direct feed

```
If scout produced HTML exports of the old pages, drop them here.
We'll extract content blocks, identify reusable sections, and surface
them in the new design for "Keep + redesign" pages.

Skip if you'd rather have us regenerate everything from scratch.
```

System parses dropped HTML, extracts content chunks per page, makes them available as Phase 5 input.

---

## Phase 4 — Brand Strategy Refresh

If operator picked "Use as-is" on BV in Phase 1.2, brand strategy is mostly inherited.

If they picked "Edit" or "Reject + fresh," synthesize new `brand-strategy.md` using:

- Updated BV fields (post-edit)
- Operator-dropped materials (optional)
- Scout's identified content gaps (informs messaging)
- New design design style's voice implications

---

## Phase 4.5 — Pre-Rebuild Gate (HITL)

**No MCP calls.** Single summary block. **Only path into Phase 5.**

```
PRE-REBUILD REVIEW for {domain} — {business_name}

Scout snapshot
  Run date     {scout_run_date} ({N} days ago)
  Pages found  {N}
  Pillar baseline (from scout):
    Technical {N}  Content {N}  Authority {N}  UX {N}

Asset decisions
  OTTO         {action} {· detail}
  Brand Vault  {action} {· detail}
  GBP          {action} {· detail}
  PPC          {action} {· detail}
  LLMV         {action} {· detail}

Page rebuild map
  Keep + redesign        {N}
  Keep + rewrite         {N}
  Merge                  {N} → {M}
  Delete                 {N} (all have redirects mapped)
  New                    {N}
  Total new site:        {N} pages

Design
  Old design style  {current_design style}
  New design style  {new_design style} {CHANGED/SAME}

Migration plan
  Redirect table  {N} entries
  DNS strategy   {cutover_or_in_place}
  Rollback       Website Studio version history · 7-day window

Issues flagged
  {list or "none"}

> Approve rebuild? (yes / edit [section] / cancel)
```

Behavior:
- `yes` → proceed to Phase 5
- `edit [section]` → jump back
- `cancel` → halt; artifacts preserved

---

## Phase 5 — Rebuild Execution

Build loop similar to `/searchatlas:build-website` Phase 5, with rebuild-specific paths.

### Per-page content source

```
For each row in new-page-queue.csv:
  if action == "Keep + redesign":
    - Load old content from scout HTML export
    - Wrap in new components
    - Verify URL unchanged
  if action == "Keep + rewrite":
    - Load old page context (URL, intent, KW)
    - Generate new copy: mcp__searchatlas__cg_dkn_generate_article
    - Wrap in new components
  if action == "Merge":
    - Load content from both old pages
    - Generate consolidated brief
    - Generate new copy
  if action == "New":
    - Standard greenfield generation (same as /searchatlas:build-website)
```

### Internal link remapping

Every internal link in the old site needs to point to one of:
- New URL of the same page (Keep)
- New merged page (Merge)
- Redirect target (Delete)

Apply via the redirect map automatically during build.

### MCP touchpoints

Same pattern as `/searchatlas:build-website` Phase 5 — every new/rewritten/redesigned page lives in Website Studio from the moment it's generated.

| Tool | When |
|---|---|
| `mcp__searchatlas__ws_create_project` | Scaffold the new WS project (separate from the old site's WS state until publish) |
| `mcp__searchatlas__ws_get_project` | Verify state mid-build |
| `mcp__searchatlas__cg_dkn_generate_article` | New + rewrite pages |
| `mcp__searchatlas__bv_upload_image` | New site assets |
| `mcp__searchatlas__otto_get_task_status` | Long-running checks |

### Per-page schema deployment

After each page is generated, deploy structured data so SERPs with features flagged in Phase 2.3 earn the rich-result lift:

| Tool | When |
|---|---|
| `mcp__searchatlas__otto_generate_page_schema` | Per new/rewritten page — generate JSON-LD |
| `mcp__searchatlas__otto_deploy_page_schema` | Per page — deploy to the WS-rendered page |

Schema choice is informed by `new-page-evidence.json` SERP features (LOCAL_PACK → LocalBusiness, FAQ → FAQPage, IMAGE_PACK → ImageObject).

---

## Phase 6 — QA + Migration Pre-Check

QA runs against the new Website Studio preview state (the old site stays live until Phase 6.5 cutover).

| Check | How |
|---|---|
| Every URL in scout's inventory has new page OR redirect | Cross-check `page-rebuild-map.csv` vs `redirect-map.csv` |
| No internal links return 404 in new build | WS crawl against new preview |
| Pillar scores hit or beat scout's baseline (against new WS preview) | Run `holistic_audit` against new preview URL |
| Preserved URLs still rank for tracked keywords | `mcp__searchatlas__se_get_keyword_intent` on top 10 ranking KWs |

### Pre-launch baseline capture

Post-launch ranking deltas can't be measured at T+0 — OTTO and KRT need crawl cycles. What we CAN do is lock a clean baseline against the OLD live site, so the operator's downstream `/searchatlas:run-seo` first-run can compute the actual delta once OTTO re-audits.

| Tool | Purpose | Target |
|---|---|---|
| `mcp__searchatlas__krt_get_rankings` | Pre-launch rank snapshot for every tracked KW | OLD live site |
| `mcp__searchatlas__gsc_get_keyword_performance` | GSC-confirmed KW baseline (impressions, clicks, CTR, position) | OLD live site |
| `mcp__searchatlas__gsc_get_page_performance` | GSC-confirmed per-page baseline | OLD live site |

> **Why no OTTO issues scan against the new WS preview?** The preview isn't part of the OTTO crawl perimeter at publish time — running an issues summary there would return empty or stale data. OTTO's pillar delta is `/searchatlas:run-seo`'s job after the new site has had a 24–48h crawl cycle.

Output: `pre-launch-baseline.json` — baseline locked against the OLD site so the operator's downstream `/searchatlas:run-seo` first-run computes the actual delta once OTTO re-audits.

---

## Phase 6.5 — Migration Launch via Website Studio

```
Final pre-migration check:
  ✅ {N} pages pushed to new WS project
  ✅ {N} redirects mapped and tested
  ✅ Old site snapshot saved for rollback
  ✅ DNS strategy confirmed

Ready to migrate {domain} via Website Studio? (yes / cancel)
```

On `yes`:

1. Snapshot old site (final scout-style export — safety net)
2. Publish new site: `mcp__searchatlas__ws_publish_project` (new project)
3. Apply redirect map via Website Studio's redirect rules
4. DNS cutover (or in-place replacement if Website Studio already hosts)
5. SSL verification (auto by WS)
6. Activate instant indexing — `mcp__searchatlas__otto_activate_instant_indexing` so new + changed URLs don't wait for Google's normal crawl cadence
7. Bulk-submit new URLs — `mcp__searchatlas__indexer_submit_batch` for every URL in `new-page-queue.csv` plus any URL that changed
8. Post-deploy sweep — 50 random URLs from scout's inventory resolve correctly (new page or redirect)
9. Submit updated sitemap to Search Console
10. Verify no critical keyword positions dropped within 24 hours

### Rollback path

- Website Studio version history preserved for 7 days
- Old WS project retained for 30 days
- Redirect rules revertible via WS

### Two URLs at workflow end — both surfaced to the operator

Same URL pattern as `/searchatlas:build-website`: `ws_publish_project` returns the WS-hosted URL immediately. For rebuild specifically, if the EXISTING site was already on Website Studio, this is an in-place replacement — the custom domain stays live and just serves the new version. If the existing site was externally hosted, the operator must cut DNS over to WS just like in greenfield. Surface both URLs at workflow end with the right context.

- **In-place WS replacement (`hostingMode = 'ws'`):** custom domain stays the primary URL (resolves immediately on the new version). WS subdomain shown as a backup.
- **External-hosting cutover (`hostingMode = 'external'`):** WS subdomain is the primary URL (resolves immediately). Custom domain shown with "Pending DNS cutover" until the operator points DNS at Website Studio.

### OTTO tracking script constraint

OTTO tracking on the new site requires the OTTO script. Website Studio publish embeds the SA tracking script automatically for SA-hosted domains — flagged if not detected. For external hosting, operator must install the OTTO script before fresh pillar scores are measurable in `/searchatlas:run-seo`.

---

## Phase 7 — Before / After Upgrade Summary

**Phase 7 is a presentation step, not a tool-firing step.** Post-launch ranking deltas can't be verified at T+0 — OTTO needs 24–48h to re-crawl, KRT needs a SERP refresh, indexer batches need Google to process them. Pretending to measure those at publish time would be theater.

Phase 7 synthesizes data we ALREADY GATHERED across Phases 0–6.5 into a Before / After narrative the operator can hand to the client today.

### Inputs (all already on disk — no MCP calls)

| Artifact | From phase | Used for |
|---|---|---|
| `scout-data.json` | Phase 0 | OLD page count · OLD pillar scores · OLD content gaps · OLD top issues · OLD design style |
| `otto-issues.json` | Phase 1.1a | Actionable issue clusters (thin content, schema, broken links) |
| `link-preservation.json` | Phase 2.2 | Anchor-protected high-Authority pages preserved |
| `new-page-evidence.json` | Phase 2.3 | KW volume + competitor evidence per NEW page |
| `page-rebuild-map.csv` | Phase 2 | Per-page actions taken (keep/rewrite/merge/delete/new) |
| Chosen design style | Phase 3 | New style vs detected old style |
| Schema deployment log | Phase 5 | Schema'd page count |
| Instant indexing batch | Phase 6.5 | Indexing strategy activated + URL count |
| `pre-launch-baseline.json` | Phase 6 | Tracked KW baseline locked against old site |

### Render the Before / After block

Only claim what we can KNOW. Never claim "rankings improved" — that's `/searchatlas:run-seo`'s job after OTTO re-audits.

```
BEFORE                                AFTER
Pages              N                   M
  Thin content     N (from scout)      0  (rewritten or deleted)
  Schema'd         N (from scout)      M of M (all new pages)
  Orphan/0-link    N (from scout)      0  (deleted with redirects)

Content gaps       N identified by scout    N new pages built + operator-approved

Design             {old_style detected}    {new_style picked}  [CHANGED|SAME]

Link equity        N high-Authority pages   N high-Authority pages preserved
                                            with anchor-aware H1s

Top issues         N from scout             Most addressed by new design + schema
                                            (broken links fixed via new internal
                                            link plan; schema deployed; thin
                                            content rewritten)

Pillar baseline    Tech {N}  Content {N}    Re-audit in /searchatlas:run-seo to see delta
                   Authority {N}  UX {N}    (OTTO needs 24-48h crawl cycle)

Indexing           Standard Google crawl    Instant indexing ON
                                            M URLs batch-submitted to Google

Tracked KWs        N tracked                Same KWs tracked — baseline locked
                                            (ranking delta visible in your KRT
                                            dashboard over 24-48h)
```

### Handoff

> Workflow complete. `/searchatlas:run-seo` picks up the monthly cadence from here, and computes the actual ranking delta once OTTO re-audits.

No MCP calls in this phase. Anything that needs T+24h+ (indexing verification, post-launch rank snapshots, OTTO auto-fix sweeps on the new site) lives in the operator's downstream `/searchatlas:run-seo` first-run, not here.

---

## What this command does NOT do

- Re-diagnose the site — scout already did
- Build greenfield pages with no prior context — that's `/searchatlas:build-website`
- Skip Phase 4.5 HITL gate
- Migrate without explicit Phase 6.5 approval
- Auto-publish redirects without operator sign-off

## Operator-facing input summary

1. **Domain**
2. **Scout output file** — drop the HTML/JSON export
3. **Asset decisions** — Use/Edit/Add/Reject per found SA asset
4. **Page rebuild map** — accept default or adjust per page
5. **Redesign preferences** — what stays, what changes
6. **New design design style** (1 of 6)
7. **Approve HITL gate** (yes/edit/cancel)
8. **Approve Web Studio migration** (yes/cancel)

Phase 2.5 adds a per-page walkthrough decision for NEW page candidates — Approve / Reject / Edit per card — but introduces **no new operator inputs**. All new SA tool calls across Phases 1, 2, 2.3, 5, 6, and 6.5 are auto-driven from scout output + the Phase 2 page map. Phase 7 is a presentation step with zero MCP calls.

**Workflow end-state:** site is live + before/after summary rendered. Actual post-launch ranking delta is `/searchatlas:run-seo`'s job — OTTO needs a 24–48h crawl cycle before fresh pillar scores and rank deltas are measurable.

## Related skills + commands

- `/searchatlas:scout` — upstream; produces the diagnosis this command consumes
- `/searchatlas:build-website` — for greenfield (this command's sibling)
- `/searchatlas:run-seo` — ongoing monthly cadence after Phase 7 handoff
- `/searchatlas:run-content` — for content refresh without design rebuild (smaller scope alternative)
- Spec: `_brain/projects/amm-mastermind/specs/website-rebuild-spec.md`
