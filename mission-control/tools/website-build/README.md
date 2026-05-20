# Website Build Wizard

A local web UI for the `/build-website` slash command.

Eleven-step wizard, no commands typed:

1. **Client basics** — domain, business, location, services
2. **Materials** — drop logos, brand briefs, competitor URLs, voice samples
3. **Budget tier** — sizes the post-launch cadence (`/run-seo` reads this)
4. **Auto-detect** — checks Brand Vault + GBP for prior records; auto-crawl prefill if BV is missing
5. **Brand confirmation** — review BV pull, edit any field, push edits back to SA
6. **Target market** — industry (two-tier) + target keywords + known competitors
7. **Market research** — Wave 1 (5 parallel SA tools) → Wave 2 (4 parallel) → proposed sitemap
8. **Page approval** — operator walks every proposed page, approves/rejects/edits one by one
9. **Design style** — pick 1 of 6 archetypes (Modern Minimal, Editorial, Bento, Glassmorphism, Brutalist, Warm Organic)
10. **Pre-build review** — HITL gate, all captured context on one screen
11. **Build** — Claude runs `/build-website` end-to-end against the SA MCP; site published to Website Studio

Then watch Claude run the full build live in the activity feed.

---

## What runs under the hood

When you click **Approve · start build →**, the server builds a single self-contained prompt and spawns `claude -p`. Claude executes the full `/build-website` phase sequence:

1. **Phase 1** — Identify target (domain provided, slug derived)
2. **Phase 2** — Quick existence check (BV + GBP only)
3. **Phase 3** — Multi-format operator intake (materials manifest)
4. **Phase 4** — Brand vault: use OR auto-create + auto-fill from crawl
5. **Phase 5** — Budget tier persistence
6. **Phase 6** — Brand strategy synthesis (`brand-strategy.md`)
7. **Phase 7** — Market-evidence research (two parallel waves, 9 SA tools)
8. **Phase 8** — Page queue from operator-approved decisions (`page-build-queue.csv`)
9. **Phase 9** — Design style → BV + WS
10. **Phase 10** — Content + copy (`cg_dkn_generate_article` per page)
11. **Phase 11** — Build + push to Website Studio (`ws_create_project`, schema deploy, image upload)
12. **Phase 12** — Publish + handoff (`ws_publish_project`, instant indexing, sitemap submission)

The operator's wizard inputs (services, materials, target market, page decisions, design style) are pre-baked into the prompt so Claude never asks an interactive question.

---

## Prerequisites

- **Python 3.10+** — `python3 --version`
- **Claude Code CLI** — install from <https://claude.com/code>
- **SearchAtlas MCP configured** — from the toolkit root:
  ```bash
  claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
  ```
  First call will trigger OAuth.

---

## Run

```bash
bash run.sh
```

The script:
1. Verifies Python, Claude CLI, and SA MCP
2. Creates a `.venv` and installs FastAPI + Uvicorn (first run only)
3. Starts the server on `http://localhost:8766`
4. Opens your browser

To use a different port: `PORT=9000 bash run.sh`.

---

## Architecture

```
┌─────────────────────┐    POST /api/build         ┌────────────────┐
│  Browser            │ ─────────────────────────▶│  server.py     │
│  11-step wizard     │                            │  FastAPI       │
└─────────────────────┘   ◀── SSE stream  ─────── │  spawns:        │
                                                   │  claude -p ...  │
                                                   └────────┬────────┘
                                                            │
                                          ┌─────────────────┼──────────────┐
                                          ▼                 ▼              ▼
                                    ┌──────────┐    ┌──────────────┐  ┌──────────────┐
                                    │ WebFetch │    │ SearchAtlas  │  │ Website      │
                                    │ (crawl)  │    │ MCP (research│  │ Studio MCP   │
                                    │          │    │ + content)   │  │ (publish)    │
                                    └──────────┘    └──────────────┘  └──────────────┘
```

---

## Files

```
website-build/
├── index.html         # 11-step wizard UI (single file, no build step)
├── server.py          # FastAPI bridge to Claude Code + /build-website prompt builder
├── requirements.txt   # FastAPI + Uvicorn
├── run.sh             # one-command launch
└── README.md          # this file
```

---

## Endpoints

`GET /` — serves the wizard.

`GET /api/health` — returns `{ claude_available, searchatlas_mcp_configured, toolkit_root }`. Used by the header strip's green/red/yellow dot.

`POST /api/build` — accepts the full wizard state payload:
```json
{
  "domain": "...",
  "business": "...",
  "location": "...",
  "services": [...],
  "tier": "...",
  "materials": [...],
  "targetMarket": { "industryTier1", "industryTier2", "targetKeywords", "knownCompetitors" },
  "sitemap": { "proposedPages": [...] },
  "pageDecisions": { "<slug>": { "decision", "edits" } },
  "archetype": "...",
  "assetDecisions": { ... },
  "bvPrefill": { ... }
}
```
Returns `text/event-stream` with `phase | note | work | done | biz | error | complete` events.

`POST /api/preview-prompt` — same payload, returns `{ prompt }` without executing. Useful for tweaking the prompt template.

---

## Debugging

**Preview the prompt** (without running):

```bash
curl -X POST http://localhost:8766/api/preview-prompt \
  -H "Content-Type: application/json" \
  -d '{"domain":"example.com","business":"Example","location":"Austin, TX","services":["Consulting"],"targetMarket":{"industryTier1":"Professional Services","industryTier2":"Marketing Agency"}}'
```

**Watch raw stream-json from Claude** (skip the server, run it yourself):

```bash
cd /path/to/toolkit-root
claude -p --output-format stream-json --verbose "Run /build-website end-to-end for example.com. Skip Phase 0."
```

**`SearchAtlas MCP not configured`** in the header — run `claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp` from the toolkit root, then refresh.

**Stream cuts off mid-build** — closing the browser tab kills the SSE connection but the underlying `claude -p` subprocess will keep running until it finishes. Reload to see the final state from the artifacts on disk.

**Stale wizard state** — the wizard persists to `localStorage` under `amm-website-wizard-v1`. Click **Start fresh** in the header to clear and start over.
