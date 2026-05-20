# /onboard-client

Guided wizard to onboard a new client into SearchAtlas. Supports two paths: pulling full brand data automatically from an existing SearchAtlas brand vault, or setting up a brand new client from scratch.

All data collected in either path is synced back to the SearchAtlas brand vault — local files and SA stay in sync from day one.

## Instructions

### Phase 0: Choose Onboarding Path

```
How would you like to onboard this client?

1. 🔄  Existing client in SearchAtlas — pull everything from their brand vault automatically
2. ✏️   New client — enter their details and create everything from scratch

Which option? (1 or 2)
```

---

## Path A — Existing Client (Brand Vault Pull)

### A1: Select Client From Account

1. Call `brand_vault` → `list_brand_vaults` with empty params `{}`
2. Display as a numbered list, member picks a number

### A2: Full Brand Vault Pull (4 parallel calls)

| Call | Tool | Params | What It Returns |
|------|------|--------|-----------------|
| 1 | `brand_vault` → `retrieve_brand_vault_details` | `brand_vault_uuid` | Name, domain, logo URL, brand colors, description, assets |
| 2 | `brand_vault` → `get_brand_vault_business_info` | `brand_vault_uuid` | Address, city, state, zip, phone, email, hours, social links |
| 3 | `brand_vault` → `get_knowledge_graph` | `hostname` | Entity graph, topic clusters, competitor entities |
| 4 | `brand_vault` → `list_voice_profiles` | `hostname` | Tone, writing style, example phrases, active voice profile |

### A3: Confirm — Member Reviews and Edits

Show the full confirmation block (see A4 format). Member types "yes" or specifies fields to edit.

**If member edits any field:** push the change back to SA immediately using the correct update tool (see sync map below), then confirm the write succeeded before continuing.

### A4: Confirmation Block

```
Here's everything I pulled from your SearchAtlas brand vault:

━━ Business ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢  Name           Apple Group
🌐  Domain         apple.com
🏷️  Industry       Dental Clinic
📝  Description    [first 120 chars...]
📞  Phone          (305) 555-0182
✉️  Email          hello@apple.com
📍  Address        123 Ocean Blvd, Miami, FL 33101
🕐  Hours          Mon–Fri 8AM–5PM, Sat 9AM–1PM

━━ Brand ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨  Colors         #1A3C6E (primary) · #F5F5F5 (bg)
🖼️  Logo           [URL on file]
🔊  Voice          Professional & Reassuring (active)
✍️  Style          Clear, patient-focused, jargon-free

━━ SEO & Content ━━━━━━━━━━━━━━━━━━━━━━━
🔑  Primary KW     dentist miami fl
🧠  Key entities   [top 5 from knowledge graph]
🏆  Competitors    [top 3 competitor domains]

━━ IDs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗  Brand Vault    [uuid]
🚀  OTTO Project   [project_id or: not configured]
📍  GBP Location   [location_id or: not configured]
💰  PPC Business   [business_id or: not configured]

Does this look right? (yes / edit [field name])
```

### A5: Discover Service IDs (parallel, silent)

- **OTTO Project ID** → `project_management` → `list_otto_projects`, match by domain
- **GBP Location ID** → `gbp_locations_crud` → `list_locations`, match by domain
- **PPC Business ID** → `business_crud` → `list_businesses`, match by domain

→ Skip to **Phase 2: Identify Needs**

---

## Path B — New Client (Manual Setup)

### B1: Collect Client Information

Ask one at a time:

**Business:**
1. Client name
2. Domain (primary website URL)
3. Industry (e.g., Dental Clinic, Home Services, Law Firm)
4. Business description (2–3 sentences: what they do, who they serve, what makes them different)
5. Phone number
6. Email

**Location:**
7. Full address (street, city, state, zip)
8. Service areas (additional cities/regions, if any)
9. Business hours

**Brand:**
10. Brand voice / tone (professional, friendly, authoritative, etc.)
11. Writing style notes (anything Claude should know when writing for this client)

**SEO:**
12. Primary keyword (main pillar keyword)
13. Pillar URL (main page to build content around)
14. Top 2–3 competitor domains

**Assets (optional):**
15. Logo URL (if available)
16. Brand colors (primary hex code, if known)
17. Any existing content to load into brand vault (paste or describe — press Enter to skip)

### B2: Create Brand Vault and Push Everything

After collecting all info, create the brand vault and immediately push all collected data:

**Step 1 — Create vault:**
- `brand_vault` → `create_brand_vault` with name + domain
- Capture the returned `brand_vault_uuid`

**Step 2 — Push business info:**
- `brand_vault` → `update_brand_vault_business_info` with phone, email, address, hours, description

**Step 3 — Push brand data:**
- `brand_vault` → `update_brand_vault` with logo, colors, industry

**Step 4 — Push voice profile:**
- `brand_vault` → `update_refine_prompt` with tone, writing style, style notes

**Step 5 — Seed knowledge graph:**
- `brand_vault` → `update_knowledge_graph` with primary keyword, competitor domains, key service topics

**Step 6 — Push transcripts (if provided):**
- `brand_vault` → `update_refine_prompt` appending any pasted content as brand voice training material

Show progress as each step completes. Confirm SA write succeeded before moving on.

→ Continue to **Phase 2: Identify Needs**

---

## Sync Map — Field → Update Tool

Use this mapping whenever pushing local changes back to SA (Path A edits, Path B creation, or `/sync-client`):

| `brand-profile.md` Section | Fields | SA Tool | Params |
|----------------------------|--------|---------|--------|
| Business | Name, description, industry, logo, colors | `update_brand_vault` | `brand_vault_uuid` |
| Contact & Location | Phone, email, address, city, state, zip, hours | `update_brand_vault_business_info` | `brand_vault_uuid` |
| Brand Voice | Tone, writing style, example phrases, avoid list | `update_refine_prompt` | `hostname` |
| Knowledge Graph | Entities, topic clusters, competitors | `update_knowledge_graph` | `hostname` |
| Transcripts & Assets | Pasted content, uploaded text | `update_refine_prompt` (append) | `hostname` |

---

## Phase 2: Identify Needs

```
Which services does this client need?
(Type numbers separated by commas, e.g. 1,2,4)

1. SEO     — OTTO project, audit, content, indexing
2. GBP     — Google Business Profile optimization
3. PPC     — Google Ads campaigns via Smart Ads
4. Content — Articles, topical maps, brand vault
5. PR      — Press releases, cloud stacks, digital PR
6. LLM     — AI search visibility monitoring
```

## Phase 3: Create Client Files

Create two files in `clients/{client-slug}/`:

**`CLAUDE.md`** — copy from `clients/_template/CLAUDE.md` and fill in all fields:
- Replace all `[Client business name]`, `[example.com]`, etc. with real values
- Fill in all SearchAtlas IDs (Brand Vault ID, OTTO Project ID, GBP Location ID, PPC Business ID)
- Mark active services checkboxes
- Fill in Brand Context (voice + one-line description)
- **Critical:** The Auto-Sync section at the bottom references `Brand Vault ID` and `Domain` — these must be filled in with the real values so the auto-sync runs correctly at every session start/end

**`brand-profile.md`** — copy from `clients/_template/brand-profile.md` and populate all sections with data pulled or collected. Fill in the Sync section:
```
## Sync
- Last pulled from SA: [current ISO datetime]
- Last pushed to SA:   [current ISO datetime]
- Brand Vault UUID:    [real uuid]
- Hostname:            [real domain]
```

Also create `clients/{client-slug}/plans/`

## Phase 4: Execute Setup

**If SEO:** Load `workflows/seo-onboarding.yaml` → execute steps 1–7
**If GBP:** Confirm GBP Location ID → `workflows/gbp-optimization.yaml` → brand description + voice from `brand-profile.md` inform all GBP copy
**If PPC:** Ask for Google Ads account ID and landing pages → `workflows/ppc-launch.yaml`
**If Content:** Brand vault already seeded → keyword research → topical map → articles using active voice profile
**If PR:** `workflows/authority-building.yaml` → ask for press release topic + angle
**If LLM:** `workflows/llm-visibility.yaml` → competitors already in `brand-profile.md`

## Phase 5: Summary

```
✅ {Client Name} — Onboarding Complete · Synced with SearchAtlas

📁  CLAUDE.md         clients/{slug}/CLAUDE.md
📋  Brand Profile     clients/{slug}/brand-profile.md
🔗  Brand Vault       {brand_vault_uuid} ✓ synced
🚀  OTTO Project      {project_id}
📍  GBP Location      {location_id}

{emoji} {Product}  {result summary}  [View →](url)
...

To sync changes later: /sync-client {client-slug}
```

## Golden Rules

- **Always offer both paths** — never assume; ask first
- **Two-way sync always** — any data collected or edited gets pushed back to SA immediately
- **Pull everything on Path A** — all 4 parallel calls, not just business info
- **Two files per client** — CLAUDE.md (lean) + brand-profile.md (full)
- **Use the sync map** — always know which SA tool handles which field
- **Schema discovery** — call tools with `{}` before first use
- **Never hardcode IDs** — discover all IDs via API
- **Confirm writes** — after any push to SA, verify the response confirms success
- **Confirm before destructive actions** — ask before publishing, activating campaigns, deploying GBP
