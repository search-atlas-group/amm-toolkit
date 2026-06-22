---
name: my-account
description: Account overview — lists all OTTO projects, brand vaults, GBP locations, PPC campaigns, content artifacts, and AI visibility projects across the user's SearchAtlas account, with quota summary.
---

# /searchatlas:my-account

Show a complete overview of the user's SearchAtlas account — all businesses, projects, campaigns, and GBP locations.

## Instructions

Follow this discovery flow in order. Use the SearchAtlas MCP tools.

### Step 1: OTTO Projects
Call `otto_list_projects`.
Collect: project name, domain, health score, page count, issue count.

### Step 2: Brand Vaults
Call `bv_list`.
Collect: vault name, domain, voice profile status.

### Step 3: GBP Locations
Call `gbp_list_locations`.
Collect: location name, address, verification status, connected status.

### Step 4: PPC Businesses
Call `ppc_list_businesses`.
Collect: business name, domain, product count, campaign count.

### Step 5: PPC Campaigns
For each business found, call `ppc_list_campaigns` (with metrics).
Collect: campaign name, status, budget, impressions, clicks, cost.

### Step 6: Content
There is no count tool — call `cg_list_articles` and count the returned items.
Collect: total articles, by status (draft, published, scheduled).

### Step 7: OTTO Quota
Call `get_quota`.
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
