# /run-gbp

Execute a GBP workflow — either first-time profile optimization or monthly maintenance.

## Instructions

### Step 1: Choose Mode

Ask the user:
> Is this a **first-time optimization** or **monthly maintenance** (reviews, posts, automation)?

### First-Time Optimization

Load `workflows/gbp-optimization.yaml` and execute:

1. **Load location** — `gbp_locations_crud` → `load_location` to sync latest from Google
2. **Get current state** — `gbp_locations_crud` → `get_location` + `get_location_stats`
3. **AI recommendations** — `gbp_locations_recommendations` → `generate_recommendations` then `bulk_apply_recommendations` (apply CHANGE + ADD types, skip DELETE for manual review)
4. **Fix categories** — `gbp_locations_categories_crud` → set primary + additional categories
5. **Add services** — `gbp_locations_services_crud` → add/update services with AI-generated descriptions
6. **Add attributes** — `gbp_locations_attributes_crud` → fill in missing attributes
7. **AI description + deploy** — `gbp_locations_deployment` → `suggest_description` then `deploy_location`

Ask the user for: GBP location ID (or help them find it via `list_locations`), primary category, additional categories, services to add.

### Monthly Maintenance

Load `workflows/gbp-monthly.yaml` and execute:

1. **Review replies** — `gbp_reviews` → `list_reviews` (unanswered) → `ai_generate_review_reply` → `publish_review_reply` for each
2. **Generate posts** — `gbp_posts_generation` → `bulk_generate_posts` + `bulk_create_posts`
3. **Automated posting** — `gbp_posts_automation` → configure + enable automated posting
4. **Publish posts** — `gbp_posts_crud` → `approve_post` + `publish_post` for pending posts
5. **Performance summary** — `gbp_locations_crud` → `get_location_stats`

Ask the user for: GBP location ID, number of posts to generate (default: 8), post type, whether to enable auto-posting.

## Output Format

**Optimization:**
```
✅ {location_name} — GBP Profile Optimization

📍 Location       synced from Google                      View →
🤖 Recommendations {N} applied (CHANGE + ADD)             View →
🏷️ Categories      primary + {N} additional set            View →
🛎️ Services        {N} services added/updated              View →
✅ Attributes      {N} missing attributes added            View →
📝 Description     AI description generated + deployed     View →
```

**Monthly:**
```
✅ {location_name} — GBP Monthly · {period}

⭐ Reviews         {N} replies published                   View →
📢 Posts           {N} posts generated + published         View →
🤖 Auto-posting    enabled · {frequency}                   View →
📊 Performance     {views} views · {clicks} clicks         View →
```

## Golden Rules

- Always `load_location` first to sync the latest state from Google
- Confirm before deploying changes — deployment pushes to Google
- Skip DELETE-type recommendations — they should be reviewed manually
