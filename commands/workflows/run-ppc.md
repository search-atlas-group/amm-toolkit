# /run-ppc

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

1. **Create business** — `business_crud` → `create` with name, type, domain, then `validate_business`
2. **Generate products** — For each landing page URL:
   - `product_crud` → `generate_product_details` (AI extracts product info from the page)
   - `product_crud` → `add_product`
3. **Validate + approve** — `product_mgmt` → `bulk_validate_landing_page_urls` then `bulk_approve_products`
4. **Create keyword clusters** — `product_crud` → `bulk_create_keyword_clusters` (this is an async task — poll with `task` → `get_otto_ppc_task_status`)
5. **Send to Google Ads** — `campaign` → `send_to_google_ads_account` with the Ads account ID and daily budget
6. **Activate campaigns** — `product_mgmt` → `bulk_update_remote_status` set to ENABLED
7. **Create landing pages (optional)** — If requested, use `website_studio_tools` → `create_project`

### Step 3: Confirm Before Activation

**IMPORTANT:** Before steps 5 and 6, show the user what will be sent to Google Ads:
- Campaign names and structure
- Keyword clusters per ad group
- Budget allocation
- Landing page URLs

Only proceed after explicit user confirmation.

## Output Format

```
✅ {business_name} — PPC Campaign Launch

🏢 Business        created + validated                     View →
🛍️ Products        {N} products from landing pages          View →
🔑 Keywords        {N} clusters · {K} total keywords        View →
📤 Google Ads      campaigns sent to account {id}           View →
▶️ Campaigns       activated + running at ${budget}/day     View →

{total} actions completed · {failed} failed
```

## Golden Rules

- Always validate landing page URLs before approving products
- Poll `get_otto_ppc_task_status` after bulk keyword cluster creation — it's async
- Never activate campaigns without user confirmation
- Use `task` → `wait` between poll attempts (5–10 seconds)
