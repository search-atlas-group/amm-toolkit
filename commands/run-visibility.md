---
name: run-visibility
description: AI visibility audit — brand mentions across ChatGPT, Claude, Gemini, Perplexity; sentiment, share of voice, and citation tracking via SearchAtlas's LLM Visibility tool.
---

# /searchatlas:run-visibility

Run an LLM visibility and sentiment audit — track how a brand appears in AI-generated responses.

## Instructions

### Step 1: Collect Info

Ask the user for:
1. **Brand name** — exact name as LLMs would reference it
2. **Domain** — primary website
3. **Competitors** — 2–5 competitor brand names
4. **Prompts to simulate** — questions an ideal customer would ask an AI (e.g., "Best dentist in Miami", "Who does Botox in Cape Coral?")
5. **Topics to track** — sentiment categories (e.g., "pricing", "quality", "customer service")

### Step 2: Execute Workflow

1. **Brand overview** — `visibility` → `get_brand_overview` with brand + domain
2. **Visibility trend** — `visibility` → `get_visibility_trend`
3. **Competitor ranking** — `visibility` → `get_competitor_visibility_rank` + `get_competitor_share_of_voice`
4. **Sentiment** — `sentiment` → `get_sentiment_overview` + `get_sentiment_trend` by topic
5. **Prompt simulation** — `prompt_simulator` → `submit_prompts` with the user's prompts, then poll `check_ps_status` until complete, then `get_ps_responses` + `get_ps_summary` + `get_ps_visibility`
6. **SERP analysis** — `analysis` → `get_serp_features` + `get_position_distribution` + `get_historical_trends`
7. **Export (optional)** — `project_management` → `work_summary_export` if the user has an OTTO project

### Step 3: Recommendations

Based on the data, provide 3–5 actionable recommendations:
- Which prompts mention the brand vs competitors
- Sentiment gaps to address
- Content opportunities from SERP analysis
- Keywords where competitors outrank

### Final Step: Save Workflow Log

After completing all steps, write a workflow log to:

`${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{client_slug}/workflows/visibility-{YYYY-MM-DD}.md`

The log should include:
- Brand name, domain, and client slug
- Date/time of run
- AI visibility score and rank vs competitors
- Share of voice breakdown (brand vs each competitor)
- Sentiment summary (positive / neutral / negative percentages)
- Prompt simulation results (mentions in N/M prompts)
- Top 3–5 recommendations
- Steps failed with error details

After writing the file, print the path in chat so the user can open it.

## Output Format

```
✅ {brand_name} — LLM Visibility Report

👁️ AI Visibility   {score}% brand presence · #{rank} vs competitors
📈 Trend           {direction} over last {N} months
🏆 Share of Voice  {brand}: {X}% · {competitor_1}: {Y}% · {competitor_2}: {Z}%
💬 Sentiment       {positive}% positive · {neutral}% neutral · {negative}% negative
🤖 Prompt Sims     mentioned in {M}/{N} prompts tested
📊 SERP            {N} features captured · avg position {X}

💡 Recommendations
1. {recommendation}
2. {recommendation}
3. {recommendation}

📄 Workflow log: ${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}/{slug}/workflows/visibility-{YYYY-MM-DD}.md
```

## Golden Rules

- Prompt simulation is async — poll with 5–10 second intervals
- Submit all prompts in a single batch for efficiency
- Competitor names must match how LLMs reference them
