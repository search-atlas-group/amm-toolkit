# /run-content

Generate articles using topical maps and the 4-step content workflow.

## Instructions

### Step 1: Choose Starting Point

Ask the user:
> Do you want to **create a new topical map** or **generate articles from an existing one**?

### Creating a New Topical Map

1. Ask for: keyword, domain, pillar URL
2. Call `topical_maps` → `create_topical_map` with the keyword, domain, and pillar URL
3. Present the generated clusters and article titles
4. Ask which articles to generate (all or specific ones)

### Generating Articles

For each article title, run the **4-step article workflow**:

1. **Create instance** — `content_generation` → `create_content_instance`
   - Pass: article title, topical map ID, brand vault ID (if available)
2. **Information retrieval** — `content_generation` → `start_information_retrieval`
   - Then poll with `poll_information_retrieval` until status = completed
3. **Headings outline** — `content_generation` → `start_headings_outline`
   - Then poll with `poll_headings_outline` until status = completed
4. **Generate article** — `content_generation` → `generate_complete_article`

### Optional: Content Grading

After generation, ask if the user wants to grade the articles:
- `article_management` → `run_content_grader` for each article

### Optional: Publishing

Ask if the user wants to publish:
- **WordPress** — `content_publication` → `publish_wordpress_article`
- **CMS** — `content_publication` → `publish_cms_article`

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
```

## Golden Rules

- Each polling step can take 30–60 seconds — always poll, never assume completion
- Brand vault connection improves article quality — use it when available
- Content grading is separate from generation — run it after all articles are created
- Always show article editor links so the user can review before publishing
