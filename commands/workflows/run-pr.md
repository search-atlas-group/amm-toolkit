# /run-pr

Create and distribute press releases, build cloud stacks, and set up digital PR outreach.

## Instructions

### Step 1: Choose Components

Ask the user which authority building components they want:
- [ ] **Press Release** — write + distribute to news networks
- [ ] **Cloud Stack** — create + publish a cloud stack for link building
- [ ] **Digital PR** — set up an outreach campaign to earn editorial links

### Press Release Workflow

1. Ask for: client name, topic/headline, angle (expansion, award, launch, etc.), target keywords
2. **Create press release** — `press_release_content` → `create` with client + topic
3. **Write content** — `press_release_content` → `write_press_release` with the angle and keywords
4. **Check distribution options** — `press_release_distribution` → `get_press_release_categories`
5. **Distribute** — `press_release_distribution` → `publish_press_release` with chosen network (standard/premium/elite)

**Confirm before distribution** — show the press release content and distribution cost.

### Cloud Stack Workflow

1. Ask for: anchor text, target URL (page to point links to)
2. **List templates** — `cloud_stack_content` → `list_templates`
3. **Create cloud stack** — `cloud_stack_content` → `create` with client info + template
4. **Check providers** — `cloud_stack_distribution` → `get_cloud_stack_providers`
5. **Build** — `cloud_stack_distribution` → `build_cloud_stack`
6. **Publish** — `cloud_stack_distribution` → `publish_cloud_stack`

### Digital PR Workflow

1. Ask for: outreach topic, target publications (optional)
2. **Create campaign** — `digital_pr_campaign_service` → `create_campaign`
3. **Set up email template** — `digital_pr_template_service` → `create` or `list` existing templates
4. **Activate** — `digital_pr_campaign_service` → `toggle_campaign` (active: true)

### Optional: Monitor Backlinks

After distribution:
- `backlinks` → `get_site_backlinks` (filter: new)
- `backlinks` → `get_site_referring_domains`

## Output Format

```
✅ {client} — Authority Building · {period}

📰 Press Release   written + distributed ({network})       View →
☁️ Cloud Stack     built + published · {N} properties      View →
📧 Digital PR      outreach campaign live · {N} targets    View →
🔗 Backlinks       {N} new backlinks detected              View →

{total} actions completed · {failed} failed
```

## Golden Rules

- Press release distribution costs credits — always confirm before publishing
- Cloud stack building is async — poll for completion
- Digital PR campaigns send real emails — confirm recipient list before activating
