---
name: run-pr
description: Authority building — press release drafting and distribution via SearchAtlas Press platform; backlink acquisition through cloud stacks and digital PR outreach campaigns.
---

# /searchatlas:run-pr

Create and distribute press releases, build cloud stacks, and set up digital PR outreach.

## Instructions

### Step 1: Choose Components

Ask the user which authority building components they want:
- [ ] **Press Release** — write + distribute to news networks
- [ ] **Cloud Stack** — create + publish a cloud stack for link building
- [ ] **Digital PR** — set up an outreach campaign to earn editorial links

### Press Release Workflow

1. Ask for: client name, topic/headline, angle (expansion, award, launch, etc.), target keywords
2. **Create press release** — `pr_create` with client + topic
3. **Write content** — `pr_write` with the angle and keywords
4. **Check distribution options** — `pr_get_publish_options`
5. **Distribute** — `pr_publish` with chosen network (standard/premium/elite)

**Confirm before distribution** — show the press release content and distribution cost.

### Cloud Stack Workflow

1. Ask for: anchor text, target URL (page to point links to)
2. **List templates** — `cs_list_templates`
3. **Create cloud stack** — `cs_create` with client info + template
4. **Check providers** — `cs_get_providers`
5. **Build** — `cs_build`
6. **Publish** — `cs_publish`

### Digital PR Workflow

1. Ask for: outreach topic, target publications (optional)
2. **Create campaign** — `dpr_create_campaign`
3. **Set up email template** — `dpr_create_template` or `dpr_list_templates` for existing templates
4. **Activate** — `dpr_set_campaign_active` (active: true)

### Optional: Monitor Backlinks

After distribution:
- `backlinks` → `get_site_backlinks` (filter: new)
- `backlinks` → `get_site_referring_domains`

### Final Step: Save Workflow Log

After completing all steps, write a workflow log to:

`${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/workflows/pr-{YYYY-MM-DD}.md`

The log should include:
- Client name and slug
- Date/time of run
- Press release title, distribution network, and distribution URL (if applicable)
- Cloud stack anchor text, target URL, and publish status (if applicable)
- Digital PR campaign name and activation status (if applicable)
- New backlinks detected
- Steps failed with error details
- Next recommended action

After writing the file, print the path in chat so the user can open it.

## Output Format

```
✅ {client} — Authority Building · {period}

📰 Press Release   written + distributed ({network})       View →
☁️ Cloud Stack     built + published · {N} properties      View →
📧 Digital PR      outreach campaign live · {N} targets    View →
🔗 Backlinks       {N} new backlinks detected              View →

{total} actions completed · {failed} failed

📄 Workflow log: ${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/workflows/pr-{YYYY-MM-DD}.md
```

## Golden Rules

- Press release distribution costs credits — always confirm before publishing
- Cloud stack building is async — poll for completion
- Digital PR campaigns send real emails — confirm recipient list before activating
