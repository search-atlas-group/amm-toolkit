# Website Rebuild Wizard

A local web UI for the `/rebuild-website` slash command.

Consumes the scout output for a domain, walks the operator through every rebuild decision (asset inheritance, page rebuild map, NEW page approvals, brand strategy refresh, new design style, hosting mode), runs the pre-rebuild HITL gate, then hands the locked decision bundle to Claude Code so the rebuild + migration + before/after summary happen end-to-end without a single re-prompt.

12 steps. No interactive questions during execution.

---

## What runs under the hood

When you click **Approve · start rebuild** at the pre-rebuild gate, the server compiles every operator decision into one self-contained prompt and spawns `claude -p`. Claude:

1. Inherits the SA assets per your `use / edit / add / reject_fresh / create / skip` decisions (OTTO, Brand Vault, GBP, PPC, LLM Visibility)
2. Executes the page rebuild map — Keep+redesign, Keep+rewrite, Merge, Delete (with 301s), New (greenfield from approved topic gaps)
3. Fires link-equity preservation in parallel for every high-Authority Keep page (`se_get_anchor_text`, `se_get_referring_domains`, `se_get_link_network_graph`)
4. Builds the rebuild in Website Studio per the locked design style, generates schema, deploys schema
5. Captures the pre-launch baseline (`krt_get_rankings`, `gsc_get_keyword_performance`, `gsc_get_page_performance`)
6. Publishes via `ws_publish_project`, applies the redirect map, activates instant indexing, batch-submits new URLs
7. Surfaces both the WS live URL and the custom domain (with DNS-cutover status based on hosting mode)
8. Returns the Before / After upgrade summary

---

## Prerequisites

- **Python 3.10+** — `python3 --version`
- **Claude Code CLI** — install from <https://claude.com/code>
- **SearchAtlas MCP configured** — from the toolkit root:
  ```bash
  claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp
  ```
  First call will trigger OAuth.
- **A scout output file for the target domain** — run `/scout <domain>` first if you don't already have one. The wizard ingests scout's HTML / JSON / Markdown export as the source of truth.

---

## Run

```bash
bash run.sh
```

The script:
1. Verifies Python, Claude CLI, and SA MCP
2. Creates a `.venv` and installs FastAPI + Uvicorn (first run only)
3. Starts the server on `http://localhost:8767`
4. Opens your browser

To use a different port: `PORT=9100 bash run.sh`.

---

## Architecture

```
┌─────────────────────┐    POST /api/rebuild       ┌────────────────┐
│  Browser            │ ─────────────────────────▶│  server.py     │
│  12-step wizard     │                            │  FastAPI       │
│  + activity feed    │   ◀── SSE stream  ─────── │  spawns:        │
└─────────────────────┘                            │  claude -p ...  │
                                                   └────────┬────────┘
                                                            │
                                  ┌─────────────────────────┼─────────────────────────┐
                                  ▼                         ▼                         ▼
                            ┌──────────┐            ┌──────────────┐         ┌──────────────────┐
                            │ SE / OTTO│            │ Website      │         │ KRT / GSC /      │
                            │ link +   │            │ Studio       │         │ indexer batch    │
                            │ schema   │            │ build +      │         │ submit + sitemap │
                            │ MCP      │            │ publish MCP  │         │ MCP              │
                            └──────────┘            └──────────────┘         └──────────────────┘
```

The wizard handles every operator decision before the bridge is ever called. Once the operator approves the HITL gate, the server compiles a single prompt with all decisions baked in, then streams Claude's progress back as SSE events that render in the activity feed (replacing the old simulated build/migration animations).

---

## Files

```
website-rebuild/
├── index.html         # 12-step wizard UI + live SSE activity feed
├── server.py          # FastAPI bridge to Claude Code
├── requirements.txt   # FastAPI + Uvicorn
├── run.sh             # one-command launch
└── README.md          # this file
```

---

## Endpoints

`GET /api/health` — returns `{ claude_available, searchatlas_mcp_configured, toolkit_root }`. Used by the header strip's green/yellow/red dot (polled every 30s).

`POST /api/rebuild` — accepts the full wizard payload: `{ domain, scoutFile, assetDecisions, pageMap, newPageDecisions, brandStrategy, oldStyle, newStyle, scoutHtmlPages, hostingMode, linkPreservation, preLaunchBaseline }`. Returns `text/event-stream` with `phase | note | work | done | biz | error | complete` events.

`POST /api/preview-prompt` — same payload, returns `{ prompt }` without executing. Useful for tweaking the prompt template.

---

## Wizard step map

| Step | What | Why it matters |
|---|---|---|
| 1 | Target + scout output | Domain + scout file with freshness check (stale > 30d → confirm or re-run scout) |
| 2 | SA asset inheritance | Parallel detect across OTTO / BV / GBP / PPC / LLMV; operator picks `use / edit / add / reject_fresh / create / skip` per asset |
| 3 | Old → new page map | Every page gets `keep_redesign / keep_rewrite / merge / delete / new`; merge targets + redirect destinations locked here |
| 4 | NEW page approval | Walk every NEW (topic-gap) page: approve / reject / edit; rejected pages drop out of the rebuild |
| 5 | Brand strategy refresh | Skipped if BV `use`; otherwise voice + pillars + differentiation pushed to refine prompt |
| 6 | New design style | 6 archetypes (Modern Minimal, Editorial, Bento, Glassmorphism, Brutalist, Warm Organic); same-style warning if = old |
| 7 | Scout HTML pages (optional) | Drop scout's exported HTML for direct content lift on Keep+redesign |
| 8 | Pre-rebuild HITL gate | Every locked decision on one screen — only path to execution |
| 9 | Rebuild execution | Live activity feed streams Claude's progress |
| 10 | Pre-launch baseline | KRT + GSC snapshots captured (server populates `state.preLaunchBaseline` from SSE events) |
| 11 | Migration launch | Live activity feed continues; `ws_publish_project`, redirects, instant indexing, batch submit |
| 12 | Before / After upgrade | Side-by-side summary + both URLs (WS live + custom domain w/ DNS status) |

---

## Debugging

**Preview the prompt** (without running):

```bash
curl -X POST http://localhost:8767/api/preview-prompt \
  -H "Content-Type: application/json" \
  -d '{"domain":"example.com","newStyle":"bento","hostingMode":"external","pageMap":[]}'
```

**Watch raw stream-json from Claude** (skip the server, run it yourself):

```bash
cd /path/to/toolkit
claude -p --output-format stream-json --verbose "Run /rebuild-website for example.com end-to-end with scout output already ingested."
```

**`SearchAtlas MCP not configured`** in the header — run `claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp` from the toolkit root, then refresh.

**Stream cuts off mid-rebuild** — closing the browser tab kills the SSE connection but the underlying `claude -p` subprocess will keep running until it finishes. Reload to see the final state from the artifacts on disk.

**Wizard state persists** — the wizard saves to `localStorage` under `amm-website-rebuild-wizard-v1`. Hit **Start fresh** in the header to clear and start over.
