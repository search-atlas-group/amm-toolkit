# /sync-client [client-slug]

Two-way sync between a client's local `brand-profile.md` and their SearchAtlas brand vault.

Run this whenever:
- You've edited `brand-profile.md` manually and want SA to reflect those changes
- You've updated the brand vault in the SA dashboard and want local files to reflect it
- You've uploaded new transcripts or assets and want them pushed to SA
- You want to do a full refresh after a long gap

## Instructions

### Step 1: Identify the Client

If `client-slug` was passed as an argument, use it. Otherwise:
1. List the folders in `clients/` (excluding `_template`)
2. Ask member to pick which client to sync

### Step 2: Load Client Data

Read from `clients/{slug}/brand-profile.md`:
- Extract the Brand Vault UUID and Hostname from the Sync section at the bottom
- Note the timestamps: `Last pulled from SA` and `Last pushed to SA`

### Step 3: Choose Sync Direction

```
What would you like to do?

1. ⬆️  Push  — Update SearchAtlas brand vault with local changes from brand-profile.md
2. ⬇️  Pull  — Refresh local brand-profile.md with latest data from SearchAtlas
3. 🔄  Both  — Full sync: pull SA data first, then push any local additions on top

Which option? (1 / 2 / 3)
```

---

## Push (Local → SearchAtlas)

Read `brand-profile.md` and push each section to SA using the correct tool:

### Push Map

| Section | Fields | SA Tool | Params |
|---------|--------|---------|--------|
| Business | Name, description, industry, logo URL, brand colors | `brand_vault` → `update_brand_vault` | `brand_vault_uuid` |
| Contact & Location | Phone, email, address, city, state, zip, hours, service areas | `brand_vault` → `update_brand_vault_business_info` | `brand_vault_uuid` |
| Brand Voice | Tone, writing style, example phrases, avoid list | `brand_vault` → `update_refine_prompt` | `hostname` |
| Knowledge Graph | Key entities, topic clusters, competitor domains | `brand_vault` → `update_knowledge_graph` | `hostname` |
| Transcripts & Assets | Any content listed under "Content Transcripts & Assets" | `brand_vault` → `update_refine_prompt` (append) | `hostname` |

### Push Steps

1. **Show a diff first** — summarize what's changing:
   ```
   Ready to push these changes to SearchAtlas:

   ✏️  Description  updated (120 → 145 chars)
   📞  Phone        added: (305) 555-0182
   🔊  Voice        tone updated to "Authoritative & Warm"
   🧠  Entities     added: "dental implants", "sedation dentistry"
   📄  Transcripts  1 new content sample added

   Push these to SearchAtlas? (yes / cancel)
   ```

2. **Execute pushes in order:**
   - `update_brand_vault` → business + brand data
   - `update_brand_vault_business_info` → contact + location
   - `update_refine_prompt` → voice + transcripts
   - `update_knowledge_graph` → entities + topics

3. **Confirm each write** — verify SA returned success before moving to the next call

4. **Update sync timestamp** — write `Last pushed to SA: [ISO datetime]` to the Sync section of `brand-profile.md`

---

## Pull (SearchAtlas → Local)

Fetch fresh data from SA and update `brand-profile.md`.

### Pull Steps

1. Run 4 parallel calls:
   - `brand_vault` → `retrieve_brand_vault_details` (brand_vault_uuid)
   - `brand_vault` → `get_brand_vault_business_info` (brand_vault_uuid)
   - `brand_vault` → `get_knowledge_graph` (hostname)
   - `brand_vault` → `list_voice_profiles` (hostname)

2. **Show a diff first** — what changed in SA since last pull:
   ```
   SA has newer data than your local brand-profile.md:

   📝  Description  changed in SA
   🔊  Voice        new profile available: "Educational & Empathetic"
   🧠  Entities     SA added: "cosmetic dentistry", "teeth whitening"

   Update local brand-profile.md? (yes / cancel)
   ```

3. **Update brand-profile.md** with all new values — preserve any local-only notes that aren't in SA

4. **Update sync timestamp** — write `Last pulled from SA: [ISO datetime]`

---

## Both (Full Sync)

Run Pull first, then Push:

1. Pull SA → local (update `brand-profile.md` with any SA changes)
2. Ask member if there are additional local edits they want to push
3. Push local → SA (push any fields that differ from what was just pulled)
4. Update both timestamps

This prevents overwriting SA changes with stale local data.

---

## Transcript & Asset Upload

When member adds content to the "Content Transcripts & Assets" section of `brand-profile.md` (or pastes content directly), push it to SA as brand voice training material:

```
I see new content in your Transcripts & Assets section.
Push this to the SearchAtlas brand vault to improve content generation? (yes / skip)
```

If yes:
- `brand_vault` → `update_refine_prompt` with the new content appended as context
- Confirm write success

---

## Summary

```
✅ {Client Name} — Sync Complete

⬆️  Pushed 4 fields to SearchAtlas brand vault
⬇️  Pulled 2 updated fields from SearchAtlas
📄  1 transcript pushed to brand vault
🕐  Last synced: [datetime]
```

## Golden Rules

- **Diff before writing** — always show what will change before any push
- **Pull before push in full sync** — never overwrite SA changes with stale local data
- **Confirm writes** — verify SA returns success on every update call
- **Update timestamps** — always write the sync datetime back to brand-profile.md
- **Preserve local notes** — pull updates brand data fields but never deletes the Notes or Plans sections
- **Schema discovery** — call any tool with `{}` before first use if schema is uncertain
