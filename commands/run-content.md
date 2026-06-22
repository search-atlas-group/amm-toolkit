---
name: run-content
description: Content generation pipeline — topical maps, article drafting, brand-vault-driven voice profile, publication scheduling via SearchAtlas Content Genius.
---

# /searchatlas:run-content

Generate articles using topical maps and the 4-step content workflow.

## Instructions

### Step 1: Choose Starting Point

Ask the user:
> Do you want to **create a new topical map** or **generate articles from an existing one**?

### Creating a New Topical Map

1. Ask for: keyword, domain, pillar URL
2. Call `cg_create_topical_map` with the keyword, domain, and pillar URL
3. Present the generated clusters and article titles
4. Ask which articles to generate (all or specific ones)

### Generating Articles

For each article title, run the **4-step article workflow**:

1. **Create instance** — `cg_create_content_instance`
   - Pass: article title, topical map ID, brand vault ID (if available)
2. **Information retrieval** — `cg_start_information_retrieval`
   - Then poll with `cg_wait_for_task` until status = completed
3. **Headings outline** — `cg_start_headings_outline`
   - Then poll with `cg_wait_for_task` until status = completed
4. **Generate article** — `cg_generate_complete_article`

### Optional: Content Grading

After generation, ask if the user wants to grade the articles:
- `cg_run_content_grader` for each article

### Optional: Publishing

Ask if the user wants to publish:
- **WordPress** — `cg_push_article` (WordPress connector)
- **CMS** — `cg_push_article` (CMS connector)

### Final Step: Save Workflow Log

After completing all steps, write a workflow log to:

`${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/workflows/content-{YYYY-MM-DD}.md`

The log should include:
- Domain and client slug
- Date/time of run
- Topical map created (keyword, cluster count, title count)
- Articles generated (titles, content project IDs, scores)
- Articles published (titles, URLs)
- Steps failed with error details
- Next recommended action

After writing the file, print the path in chat so the user can open it.

## Output Format

```
✅ Content Generation Complete

🗺️ Topical Map     {keyword} · {N} clusters · {M} titles    View →

✍️ Articles Generated:
   1. {title}  Score: {X}/100  [View →](editor_link)
   2. {title}  Score: {X}/100  [View →](editor_link)
   ...

📊 Avg Score: {X}/100
📤 Published: {N}/{total}

{total} articles created · {failed} failed

📄 Workflow log: ${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/workflows/content-{YYYY-MM-DD}.md
```

## Golden Rules

- Each polling step can take 30–60 seconds — always poll, never assume completion
- Brand vault connection improves article quality — use it when available
- Content grading is separate from generation — run it after all articles are created
- Always show article editor links so the user can review before publishing
