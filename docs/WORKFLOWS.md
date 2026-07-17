# Workflows Guide

How workflow templates work and how to use them.

## What Are Workflows?

Workflows are YAML templates that define step-by-step marketing processes. Each workflow chains multiple MCP tool calls in the correct order, handles dependencies, and produces a formatted summary.

They live in the `workflows/` directory.

## Available Workflows

| Template | File | Use Case |
|----------|------|----------|
| SEO Onboarding | `seo-onboarding.yaml` | New client: project, audit, brand vault, keywords, content |
| Monthly SEO | `monthly-seo.yaml` | Existing client: suggestions, schema, indexing, content |
| GBP Optimization | `gbp-optimization.yaml` | First-time GBP profile cleanup |
| GBP Monthly | `gbp-monthly.yaml` | Monthly GBP: reviews, posts, automation |
| PPC Launch | `ppc-launch.yaml` | Google Ads campaign setup and activation |
| Authority Building | `authority-building.yaml` | Press releases, cloud stacks, digital PR |
| LLM Visibility | `llm-visibility.yaml` | AI search monitoring and sentiment analysis |

## Template Structure

Every workflow YAML has the same structure:

```yaml
# Header
template: workflow-name
version: "1.0"
description: "What this workflow does"

# Client info — fill in per client
client: ""
domain: ""
period: ""
status: pending

# IDs — discovered or filled as steps complete
ids:
  project_id: ""
  # ...

# Configuration — workflow-specific settings
config:
  setting_1: ""
  # ...

# Steps — the actual workflow
steps:
  - id: 1
    name: "Step Name"
    tool: tool_name
    operations:
      - op: operation_name
        params:
          key: "{{variable}}"
    output_key: ids.some_id
    status: pending
    depends_on: []

# Results — filled after execution
results: []
```

## Key Concepts

### Variables

Templates use `{{variable}}` syntax for dynamic values:
- `{{domain}}` — client's domain
- `{{ids.project_id}}` — a discovered ID
- `{{config.setting}}` — a configuration value

### Dependencies

Steps declare dependencies with `depends_on`:

```yaml
- id: 3
  depends_on: [1, 2]  # Wait for steps 1 and 2 before running
```

Steps without dependencies can run in parallel.

### Repeat

Steps that iterate over a list use `repeat`:

```yaml
- id: 7
  repeat: "{{config.articles_to_generate}}"
  operations:
    - op: create_content_instance
    # ... runs once per article
```

### Conditions

Optional steps use `condition`:

```yaml
- id: 7
  condition: "{{config.create_landing_pages}}"
  # Only runs if create_landing_pages is true
```

### Output

Steps can store results in two ways:
- `output_key: ids.project_id` — store a single ID for later steps
- `output: variable_name` — store complex output data

## How to Use Workflows

### From Slash Commands

The easiest way — just use the corresponding command:

```
/run-seo        → seo-onboarding.yaml or monthly-seo.yaml
/run-gbp        → gbp-optimization.yaml or gbp-monthly.yaml
/run-ppc        → ppc-launch.yaml
/run-pr         → authority-building.yaml
/run-visibility → llm-visibility.yaml
```

The command will ask you the right questions and fill in the template automatically.

### Manual Execution

1. Copy the template:
   ```bash
   cp workflows/seo-onboarding.yaml acme-corp-2026-03.yaml
   ```

2. Fill in client info, IDs, and config

3. Execute steps in order, following `depends_on` chains

4. Record results in the `results` array

### Creating Client Plans

For ongoing clients, create a plan file per month:

```
plans/
  acme-corp/
    2026-01.yaml  (January — onboarding)
    2026-02.yaml  (February — monthly maintenance)
    2026-03.yaml  (March — monthly + GBP)
```

This gives you a history of all work done per client.

## Output Format Standard

All workflows produce summaries using this format:

```
✅ {Client Name} — {Workflow Name} · {Period}

{emoji}  {Step Label}     {count/result}     [View →](dashboard_url)
{emoji}  {Step Label}     {count/result}     [View →](dashboard_url)
...

{total} actions completed · {failed} failed
```

**Rules:**
- Always use emoji + label + count/outcome + link
- Links must be clickable markdown
- Never show raw UUIDs — use names and dashboard links
- Status line at the bottom always

## Workflow Dependencies (execution order)

```
SEO Onboarding:
  1. Project → 2. Audit → 3. Pillars → 4. Brand Vault → 5. Keywords → 6. Topical Map → 7. Articles
  (4 can run parallel to 5; 7 depends on both 4 and 6)

Monthly SEO:
  1. Issues → 2. Suggestions ─┐
                3. Schemas   ──├→ (parallel after 1)
                4. Indexing  ──┘
  5. Topical Map → 6. Articles
  7. Content Grader (independent)

GBP Optimization:
  1. Load Location → 2. Recommendations → 3. Categories ─┐
                                           4. Services   ──├→ 6. Deploy
                                           5. Attributes ──┘

PPC Launch:
  1. Business → 2. Products → 3. Approve → 4. Keywords → 5. Send to Ads → 6. Activate
  (strictly sequential — each step depends on the previous)

Authority Building:
  1. Press Release → 2. Distribute ──┐
  3. Cloud Stack → 4. Publish      ──├→ 6. Monitor Backlinks
  5. Digital PR Campaign            ──┘

LLM Visibility:
  1. Brand Overview ─┐
  2. Sentiment      ──├→ (all can run in parallel)
  3. Prompt Sims    ──┤
  4. SERP Analysis  ──┘
  5. Export (optional, after all)
```

## Tips

- **Always run `/my-account` first** to discover IDs before starting a workflow
- **Don't skip steps** — later steps depend on output from earlier ones
- **Poll async tasks** — audit creation, content generation, and keyword clustering are all async
- **Save your plan files** — they're a record of all work done for each client
