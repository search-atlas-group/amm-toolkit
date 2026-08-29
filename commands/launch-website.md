---
name: launch-website
description: Plan a complete new-site launch — site architecture, per-page SEO briefs with keywords/metadata/schemas/FAQs, and tracking setup — grounded in live SearchAtlas MCP data. Opinionated toward local service businesses with 1-5 physical locations.
---

# /searchatlas:launch-website

Turn discovery inputs (URL, services, locations) into a complete pre-launch plan: site
architecture, per-page briefs with primary + long-tail keywords, metadata, modules, FAQs,
schemas and internal linking — grounded in real Search Atlas data.

> **Note on companion files:** this command's instructions below reference a file tree
> (`spec/master-template-spec.md`, `references/page-types.md`,
> `references/searchatlas-playbook.md`, `references/internal-linking.md`,
> `references/local-seo-layer.md`, `spec/sitemap-rules.md`, `spec/measurement.md`,
> `examples/goswiftpro-fairfax/`, `assets/dashboard-template.html`,
> `qa/tool_manifest.json`, `qa/lint_skill_tools.py`) that is **not included** in this
> flat `commands/` file and does not exist elsewhere in this repo. Most of the operative
> rules are also stated inline in the phase text below — proceed with those. A `Read` of
> any of the paths above will fail; do not block on it, and do not invent the missing
> file's content.

For the web UI version, see [POWER-USER.md § Mission Control](../POWER-USER.md#mission-control--web-wizards) once one exists — today this command has no Mission Control wizard counterpart.

**Scope:** local service businesses with **1–5 physical locations**. Not national
franchises. A franchise's page strategy assumes brand demand an independent does not
have; copying it produces a site that ranks for nothing.

## Two rules that override everything else

1. **Never publish a number you did not pull from a tool.** Ratings, review counts,
   licence numbers, years in business, job counts, awards, competitor metrics. If it is
   not sourced, it does not go in the plan — not as an example, not as a placeholder that
   looks like data.
2. **Never generate a page just because a keyword exists.** Search volume is not a
   publish gate. Evidence is. See Phase 3.

Both exist because the failure mode of this command is a plan that *looks* researched. A
partner cannot tell an invented volume from a real one by reading it.

## Prerequisites

The `searchatlas` MCP server must be connected. If `mcp__searchatlas__*` tools are not
available, stop and tell the user to add it (`https://mcp.searchatlas.com/mcp`).

## Phase 0 — Identify target

> Which domain do you want to plan a launch for? (paste a URL, or type `list` to pick from your account)

`list` → `otto_list_projects`, present a numbered menu.

Capture `domain`, `client_slug`. If the argument hint contains a URL, pre-fill and skip.

## Phase 0.5 — Existence check + pillar scores

Run in parallel. **Discover only — create nothing yet.** Each lookup fails soft.

| Tool | Purpose | Capture |
|---|---|---|
| `otto_find_project_by_hostname` | OTTO project | `otto_project_id` + engagement status |
| `bv_list` (filter by domain) | Brand vault | `brand_vault_uuid` |
| `gbp_list_locations` | GBP locations | **every** `gbp_location_id` — this drives the sitemap |
| `ppc_list_businesses` | PPC business | `ppc_business_id` |
| `llmv_list_projects` | LLM Visibility | `llmv_project_id` |

If `otto_project_id` exists, also pull `se_get_holistic_seo_scores` (Technical · Content ·
Authority · UX, 0–100).

```
🔍 Existence check for {domain}:
   🏗️  OTTO project       {emoji} {exists/missing}  [id]
   🏷️  Brand vault        {emoji} {exists/missing}  [uuid]
   📍  GBP locations      {emoji} {N found}         [ids]
   💰  PPC business       {emoji} {exists/missing}  [id]
   👁️  LLM Visibility     {emoji} {exists/missing}  [id]

   Pillar scores (if OTTO project exists):
   Technical    {N}/100   {bar}
   Content      {N}/100   {bar}
   Authority    {N}/100   {bar}
   UX           {N}/100   {bar}
```

**Pillar scores reorder the Phase 10 playbook:**
- Authority < 40 → front-load PR / Digital PR / Link Listings to month 1
- Content < 50 → topical map + article generation become week-2, not week-4
- Technical < 60 → run `otto_audit_site` **before** the build, not at launch
- UX < 60 → flag in Open Questions as a redesign scope beyond content

## Phase 1 — Brand vault auto-pull, or manual collection

### Path A — vault exists

| Tool | Captures |
|---|---|
| `bv_get_details` | Name, domain, logo, colors, description, business profile |
| `bv_get_sources` | **What the vault was built from** — decides how much to trust it |
| `bv_list_voice_templates` | Tone / style templates |
| `kg_get` or `otto_get_knowledge_graph` | Entities, topic clusters, competitors |

Show the pulled data and ask `yes / edit [field]`. Edits push back via
`bv_update_profile` (business info, name, description, colors) or `bv_update_ai_settings`
(voice). There is one profile-update tool, not a family of field-specific ones.

**Trust grading.** `bv_get_sources` tells you whether a value came from a human, a
document upload, or an auto-crawl of the client's old website. An auto-crawled value is
an input to confirm, not a fact to publish — and the old site is exactly the janky,
out-of-date artifact being replaced.

### Path B — no vault

Collect via `AskUserQuestion`:

**Required:** `business_name` · `domain` · `services` · `primary_location` ·
**`location_count`** (how many physical locations with their own address, 1–5)

**Optional:** `service_areas` · `competitors` · `vertical`

If the site is live, `WebFetch` or `web_scrape` the homepage to pre-fill candidates for
the user to confirm.

Then offer: *"Want me to create a Search Atlas brand vault for {domain} so this data is
reusable?"* → `bv_create`.

### Required-for-publish inputs

These are not optional and the plan says so explicitly when they are missing. Absent
identity/legal/licensing data is a **hard fail**, not a silently omitted block:

- Legal business name, exact NAP per location, licence number(s) + issuing state
- Insurance status, service capability per service line
- Booking/form endpoint, or an explicit "phone only" decision
- Review source (which GBP location each rating is pulled from)

## Phase 2 — Keyword & market research

Check `get_balance` first and surface it.

**Batch, don't loop.** One `se_research_keywords` call takes up to 200 keywords and
returns volume, difficulty and CPC inline. Build the seed list first — services ×
locations, plus `"{service} near me"`, `"{service} cost"`, `"emergency {service}"`,
`"{vertical} {city}"` — then make one call. Use `se_lookup_keyword` for one-off checks.

**Scope the volume.** Both tools take an optional `location_id`. National volume for
"water heater repair" tells you nothing about a Fairfax plumber. Either scope it or label
the number `national` in the plan.

**Intent comes free.** `se_lookup_keyword` returns search intent and related keywords in
the same response. There is no separate intent tool.

**Competitor keyword expansion (optional, gated):** `se_create_project` on a competitor
domain → `se_get_organic` with `views=["competitors","keywords","pages"]`. This creates a
Site Explorer project per domain, so cap at the top 2. Note that a Site Explorer `site_id`
is **not** a keyword-research `project_id`.

Deduplicate, score by volume × intent weight, group by service. Hold as `keyword_bank`.

> **There is no People-Also-Ask endpoint on this MCP.** Do not plan around one. FAQ
> sourcing is handled explicitly in Phase 5.

## Phase 2.5 — Local competitor identification

**`WebSearch` first** — filter out review sites, aggregators, directories and social via
`blocked_domains`. Parse hostnames, dedupe, top 3 distinct per query. Run for the head
term and per location.

Fallbacks: `AskUserQuestion` for 3–5 known competitors → "competitor research deferred"
with a next step. **Never invent a competitor domain, and never state a competitor's DA,
rating or review count unless a tool returned it.**

Keep national franchises in a separate `national` bucket — they are reference, not the
competitive set.

Feeds **Section 3 of the plan: Local Competitive Landscape.**

## Phase 3 — Site architecture

Derive the sitemap from evidence, not from a fixed skeleton:

```
/                                  Home — always
/services/                         Services hub — always
/services/{service-slug}/          One per service the client actually performs
/locations/{city}/                 One per PHYSICAL location (own GBP + address)
/service-areas/                    One page listing every city covered
/emergency/                        Only if the client genuinely dispatches 24/7
/about/  /contact/  /reviews/  /faq/
/blog/  /blog/{post-slug}/
```

**The location rule.** A `/locations/{city}/` page requires a **physical location with its
own GBP listing** — its own address, hours, phone, review stream and `Plumber` `@id`.

A city the business merely covers is a **row on `/service-areas/`** and plain text in the
areas-we-serve band. It does not get a page. It graduates to one only when materially
distinct verified evidence exists: real jobs there, a real response-time commitment, real
local reviews, a genuine service constraint.

Generating 10–20 near-identical city pages by substituting names is scaled content abuse
under Google's spam policies, and in an agency model that repeats across hundreds of
clients it is the single largest risk in the whole product. **Search volume is not a
justification.** If the user pushes for volume-driven city pages, say what the risk is
and let them decide — do not generate them silently.

**Hidden-address locations.** If `gbp_get_location` reports the address is hidden, that
location's page renders a coverage map and **no street address anywhere** — not in the
body, not in the footer, not in schema.

Enrich blog seeds with `cg_topic_suggestions` (cap 5). Recommend `cg_create_topical_map`
natively rather than auto-creating — the UI flow is multi-step and better in-app.

## Phase 4 — Brand voice + Knowledge Graph

Recommend, do not auto-create: `bv_create` (voice questionnaire), `kg_create`
(Organization + one `LocalBusiness`/`Plumber` node **per physical location**). Read back
with `kg_get` and check against the required-entity list.

## Phase 5 — Per-page briefs

Per page: primary keyword · 2 long-tails · metadata · modules · FAQs · schemas · internal
links · **and the template that renders it** (`templates/{name}.html`).

**Metadata.** Title validated by **rendered pixel width**, not character count — a
60-character title of wide glyphs truncates where a 68-character one does not. Title, H1,
canonical and body must agree on **one** primary target. Secondary geographic mentions are
fine; contradiction is the defect.

**FAQs — generate candidates, then validate against volume.** There is no PAA endpoint on
this MCP, and **related keywords are not a substitute** — they return near-duplicate
variants ("plumb near me", "plumber near near me"), not questions. Discovery is
observational; validation is metric-backed:

| Step | Method | Tag |
|---|---|---|
| 1. Generate candidates | Trade knowledge + the questions competitors answer (`WebSearch` the head term, read their FAQ blocks) | — |
| 2. Validate | Batch the candidates through `se_research_keywords` and keep the ones with real volume | `validated` |
| 3. Keep unvalidated but useful | Question a customer genuinely asks that returns no volume | `observed` |
| 4. Company / service-area | Filled from the brand record — licences, hours, trip fees, coverage | `template` |

Every FAQ in the plan carries its tag and, for `validated`, its volume.

**Do not treat a single 0-volume result as proof of no demand.** Cross-check anything
surprising.

Per-page targets: blog post 0–4 · contact 2–3 · home and about 3–5 · hub and location
4–6 · service 4–8. **Stop when the good ones run out** — six sourced questions beat
twelve invented ones. Home and hub pages skew to company and service-area questions;
service pages skew to service questions; location pages skew to coverage questions.

**Headings outlines (gated, generation-class).** `cg_create_content_instance` +
`cg_run_generation_step` + `cg_update_article_headings`, homepage and top 3 service pages
only, **after asking the user** — these cost more than lookups. Everything else: "run
headings natively post-launch."

## Phase 6 — Schema deployment plan

Document the sequence per page; do not auto-deploy:

1. `otto_audit_site` — project ready
2. `otto_set_engagement` — activate
3. `otto_generate_page_schema` per page
4. `otto_deploy_schema` — push live (one tool covers page and sitewide)
5. `otto_list_schemas` — verify

**Honesty rules.** Schema only for content visible and accurate on the page. One
`Plumber` entity per physical location, cross-referenced by `@id` — not one per city name.
Self-serving `aggregateRating` and FAQ rich results are both heavily restricted; treat
`Service` / `FAQPage` / `BreadcrumbList` as machine-readable metadata, not a ranking
tactic, and make no promises about star results.

## Phase 7 — Internal linking map

Output as a table: source → target → anchor → module. Service-area cities that have no
page get **plain text, not links** — this is what makes the doorway-page guard visible in
the markup instead of buried in prose.

## Phase 8 — Local SEO layer

Output a numbered checklist, **per location**. Note that
`local_seo_heatmaps_recommend_keywords` requires a `business_id` from
`local_seo_heatmaps_create_business` — it belongs here, not in Phase 2.

## Phase 9 — Tracking setup

- `krt_create_project` + `krt_add_keywords` — seed with Phase 2 primaries
- `gsc_get_sites` (NATIVE, OAuth) + `otto_manage_gsc_property` to bind it
- `llmv_create_project` + `llmv_add_topics` + `llmv_add_queries` (plural)
- `otto_audit_site` → `otto_set_engagement`
- **Call tracking and attribution.** The phone is the primary channel for a trade; a
  site measuring only the form measures the wrong half. Record the DNI mode and the NAP
  strategy before launch, because tracking numbers and NAP consistency genuinely conflict.
- **Failure monitoring on both channels.** A form that silently stops capturing is
  invisible; so is a tracked number that stops recording, which produces silence that
  looks like a quiet week. Launch-day requirements, not nice-to-haves.

## Phase 10 — Authority / promotional (post-launch)

`pr_create` + `pr_publish` (`pr_get_publish_options` for tiers) · `dpr_create_campaign` ·
`social_hub_create_project` (`social_hub_manage_accounts` for OAuth) · `ll_manage_project`
(`ll_list_publications` to browse).

---

## Output

Write to `<cwd>/clients/<client_slug>/launch-plans/<YYYY-MM-DD>/`.

### `plan.md`

1. Executive summary — business, domain, vertical, **location count**, goals
2. Keyword research summary table — every row carries the tool that produced it
3. Local competitive landscape — top 3 local, blocklist applied, national bucket separate
4. Site architecture — text tree, with the publish gate that justifies each page
5. Per-page briefs — primary kw, long-tails, metadata, modules, sourced FAQs, schemas,
   internal links, **template file**
6. Schema deployment matrix
7. Internal linking map
8. Local SEO action plan — per location
9. Tracking & monitoring setup
10. Search Atlas execution order — each step tagged `[MCP]` / `[NATIVE]` / `[RECOMMENDED]`
11. **Required data not yet supplied** — the hard-fail list from Phase 1
12. Open questions / decisions remaining

Section 11 is the one that makes the plan honest. A plan that does not say what it is
missing reads as complete.

### `dashboard.html`

A self-contained HTML dashboard summarizing the plan. Build it inline from the plan data —
this command ships no `assets/dashboard-template.html`; do not attempt to read one.

### `notes.md`

Decisions made · shots run · surprises / questions · carry-forward.

## Phase 11 — Hand-off

```
✅ Plan ready for {business_name}.

📁  Plan          clients/{slug}/launch-plans/{date}/plan.md
📊  Dashboard     clients/{slug}/launch-plans/{date}/dashboard.html
📝  Notes         clients/{slug}/launch-plans/{date}/notes.md

⚠️  {N} required inputs still missing (plan §11)

What's next?
  1. /searchatlas:run-seo       — OTTO + topical map + first articles
  2. /searchatlas:run-gbp       — optimize GBP per §8
  3. /searchatlas:run-content   — generate articles from topical map seeds
  4. /searchatlas:sync-client   — push keyword bank + competitors + KG to the brand vault
  5. Open the dashboard
```

Invoke the chosen command immediately with inputs pre-filled. Do not re-prompt for data
already collected.

## Out of scope

- Auto-writing page content (use `/searchatlas:run-content` natively)
- Auto-deploying schemas (the plan documents the commands)
- E-commerce, national-scope sites, franchises with >5 locations
- Multi-language / international SEO
