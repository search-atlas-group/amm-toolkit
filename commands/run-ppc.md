---
name: run-ppc
description: PPC campaign setup and maintenance using SearchAtlas's PPC tools — syncs with Google Ads, builds keyword clusters, generates ad content, launches Smart Ads campaigns, and reviews performance metrics.
---

# /searchatlas:run-ppc

Build and launch a Google Ads PPC campaign using Smart Ads (OTTO PPC).

## Instructions

### Step 1: Collect Campaign Info

Ask the user for:
1. **Business name** — the client's business name
2. **Domain** — primary website
3. **Business type** — what they do (e.g., "aesthetic medicine clinic")
4. **Landing page URLs** — pages to generate ad groups/products from
5. **Target location** — geographic target (e.g., "Cape Coral, FL")
6. **Daily budget** — USD per day (default: $50)
7. **Google Ads account ID** — the Ads account to push campaigns to

### Step 2: Execute Workflow

Load `workflows/ppc-launch.yaml` and execute:

1. **Create business** — `ppc_create_business` with name, type, domain, then `ppc_validate_business`
2. **Generate products** — For each landing page URL:
   - `ppc_generate_product_details` (AI extracts product info from the page)
   - `ppc_add_product`
3. **Validate + approve** — `ppc_bulk_validate_landing_pages` then `ppc_review_products` to approve
4. **Create keyword clusters** — `ppc_bulk_create_keyword_clusters` (this is an async task — poll with `verify_task_status`)
5. **Send to Google Ads** — `ppc_send_to_google_ads` with the Ads account ID and daily budget
6. **Activate campaigns** — `ppc_bulk_update_remote_status` set to ENABLED
7. **Create landing pages (optional)** — If requested, use `ws_create_project`

### Step 3: Confirm Before Activation

**IMPORTANT:** Before steps 5 and 6, show the user what will be sent to Google Ads:
- Campaign names and structure
- Keyword clusters per ad group
- Budget allocation
- Landing page URLs

Only proceed after explicit user confirmation.

### Final Step: Save Workflow Log

After completing all steps, write a workflow log to:

`${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/workflows/ppc-{YYYY-MM-DD}.md`

The log should include:
- Business name, domain, and client slug
- Date/time of run
- Google Ads account ID targeted
- Steps completed with results (counts, IDs where available)
- Steps failed with error details
- Products created (names, landing pages)
- Keyword clusters created (cluster names, keyword counts)
- Daily budget set
- Next recommended action (e.g., check performance in 7 days)

After writing the file, print the path in chat so the user can open it.

## Output Format

```
✅ {business_name} — PPC Campaign Launch

🏢 Business        created + validated                     View →
🛍️ Products        {N} products from landing pages          View →
🔑 Keywords        {N} clusters · {K} total keywords        View →
📤 Google Ads      campaigns sent to account {id}           View →
▶️ Campaigns       activated + running at ${budget}/day     View →

{total} actions completed · {failed} failed

📄 Workflow log: ${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/workflows/ppc-{YYYY-MM-DD}.md
```

## Golden Rules

- Always validate landing page URLs before approving products
- Poll `verify_task_status` after bulk keyword cluster creation — it's async
- Never activate campaigns without user confirmation
- Wait 5–10 seconds between poll attempts
