# AMM Command Center

A local web UI for the `/onboard-client` slash command.

Four-step wizard, no commands typed:

1. **Domain** — paste the client's website. Claude crawls it for the basics.
2. **Brand voice** — tone, style notes, avoid list.
3. **Knowledge drop** — drag in transcripts, brand decks, photos, sales call notes — anything off-website. Or paste it as text.
4. **Services** — pick which onboarding playbooks to run, hit fire.

Then watch Claude run the full onboarding live in the activity feed.

---

## What runs under the hood

When you click **Onboard client →**, the server builds a single self-contained prompt and spawns `claude -p`. Claude:

1. Crawls the domain to extract business name, industry, contact, address, hours, services
2. Creates the SearchAtlas brand vault and pushes everything (`brand_vault` MCP tools)
3. Layers your brand voice + the knowledge drop into the refine prompt — that's the agency's edge over a website scrape
4. Runs each selected service's onboarding playbook from `workflows/`:

| Service | Playbook |
|---|---|
| SEO | `workflows/seo-onboarding.yaml` |
| Google Business Profile | `workflows/gbp-optimization.yaml` |
| PPC / Google Ads | `workflows/ppc-launch.yaml` |
| Authority / PR | `workflows/authority-building.yaml` |
| LLM Visibility | `workflows/llm-visibility.yaml` |

5. Writes the local files: `clients/<slug>/CLAUDE.md` and `brand-profile.md`
6. Returns the standard Phase 5 summary

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
3. Starts the server on `http://localhost:8765`
4. Opens your browser

To use a different port: `PORT=9000 bash run.sh`.

---

## Architecture

```
┌─────────────────────┐    POST /api/onboard       ┌────────────────┐
│  Browser            │ ─────────────────────────▶│  server.py     │
│  4-step wizard      │                            │  FastAPI       │
└─────────────────────┘   ◀── SSE stream  ─────── │  spawns:        │
                                                   │  claude -p ...  │
                                                   └────────┬────────┘
                                                            │
                                          ┌─────────────────┼──────────────┐
                                          ▼                 ▼              ▼
                                    ┌──────────┐    ┌──────────────┐  ┌──────────────┐
                                    │ WebFetch │    │ SearchAtlas  │  │ workflows/   │
                                    │ (crawl)  │    │ MCP (sync)   │  │ *.yaml       │
                                    └──────────┘    └──────────────┘  └──────────────┘
```

---

## Files

```
command-center/
├── index.html         # 4-step wizard UI (single file, no build step)
├── server.py          # FastAPI bridge to Claude Code
├── requirements.txt   # FastAPI + Uvicorn
├── run.sh             # one-command launch
└── README.md          # this file
```

---

## Endpoints

`GET /api/health` — returns `{ claude_available, searchatlas_mcp_configured, toolkit_root }`. Used by the header strip's green/red dot.

`POST /api/onboard` — accepts `{ domain, tone, readingLevel, styleNotes, avoidList, knowledge, files: [...], svcSeo, svcGbp, svcPpc, svcPr, svcLlm }`. Returns `text/event-stream` with `system | text | tool_use | file_write | error | complete` events.

`POST /api/preview-prompt` — same payload, returns `{ prompt }` without executing. Useful for tweaking the prompt template.

---

## Knowledge-drop file handling

| Type | What happens |
|---|---|
| `.txt`, `.md`, `.csv`, `.json` (<200KB) | Read as text, embedded in the prompt verbatim, pushed to the refine prompt |
| Images (`.png`, `.jpg`, etc.) | Sent as data URLs in the payload; Claude saves to `clients/<slug>/assets/` and uploads to brand vault via `bv_upload_image` once vault UUID is known |
| Larger binaries (PDFs, Word) | Filename and size are listed in the prompt so the agency knows to review manually — not auto-processed |

Drop multiple files at once. Click **✕** on any row to remove before firing.

---

## Debugging

**Preview the prompt** (without running):

```bash
curl -X POST http://localhost:8765/api/preview-prompt \
  -H "Content-Type: application/json" \
  -d '{"domain":"example.com","tone":"Warm & approachable","svcSeo":true}'
```

**Watch raw stream-json from Claude** (skip the server, run it yourself):

```bash
cd /path/to/agentic-mastermind
claude -p --output-format stream-json --verbose "Run /onboard-client for example.com end-to-end. Skip Phase 0 — Path B."
```

**`SearchAtlas MCP not configured`** in the header — run `claude mcp add searchatlas --type http https://mcp.searchatlas.com/mcp` from the toolkit root, then refresh.

**Stream cuts off mid-onboarding** — closing the browser tab kills the SSE connection but the underlying `claude -p` subprocess will keep running until it finishes. Reload to see the final state from the artifacts on disk.
