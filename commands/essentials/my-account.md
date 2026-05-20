# /my-account

Show a complete overview of the user's SearchAtlas account — all businesses, projects, campaigns, and GBP locations.

## Instructions

Follow this discovery flow in order. Use the SearchAtlas MCP tools.

### Step 1: OTTO Projects
Call `project_management` with op `list_otto_projects`.
Collect: project name, domain, health score, page count, issue count.

### Step 2: Brand Vaults
Call `brand_vault` with op `list_brand_vaults`.
Collect: vault name, domain, voice profile status.

### Step 3: GBP Locations
Call `gbp_locations_crud` with op `list_locations`.
Collect: location name, address, verification status, connected status.

### Step 4: PPC Businesses
Call `business_crud` with op `list`.
Collect: business name, domain, product count, campaign count.

### Step 5: PPC Campaigns
For each business found, call `campaign` with op `list_campaigns_with_metrics`.
Collect: campaign name, status, budget, impressions, clicks, cost.

### Step 6: Content
Call `content_retrieval` with op `count_articles`.
Collect: total articles, by status (draft, published, scheduled).

### Step 7: OTTO Quota
Call `quota_management` with op `get_otto_quota`.
Collect: sites used/total, AI generation used/total.

## Output Format

Present a clean summary grouped by product:

```
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
