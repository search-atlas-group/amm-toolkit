"""
AMM Command Center — local server that bridges the web UI to Claude Code.

Form payload from the UI is converted into a single self-contained prompt that:
  1. Asks Claude to crawl the client's domain to extract business basics.
  2. Performs GBP discovery via gbp_search_places using the business name +
     city, picks the listing whose website matches the domain, and adds it
     to SearchAtlas. If ambiguous, notes it in the summary instead of
     blocking.
  3. Layers brand voice + the unified knowledge drop on top.
  4. Runs each selected service's onboarding playbook from workflows/.
  5. Returns the standard Phase 5 summary.

Stream parsing is deliberately friendly: raw `mcp__claude_ai_Search_Atlas__*`
tool names are mapped to readable process labels ("Scoring holistic SEO
pillars…", "Creating brand vault…", "Searching Google Business listings…")
before being forwarded to the browser. Internal tools (Read, Skill,
ToolSearch, TodoWrite) are filtered out entirely.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


HERE = Path(__file__).resolve().parent


def find_toolkit_root(start: Path) -> Path:
    cur = start
    for _ in range(6):
        if (cur / "commands" / "onboard-client.md").exists():
            return cur
        cur = cur.parent
    return start.parent


TOOLKIT_ROOT = find_toolkit_root(HERE)


SERVICE_PLAYBOOKS: dict[str, dict[str, str]] = {
    "svcSeo":     {"label": "SEO",                    "playbook": "workflows/seo-onboarding.yaml"},
    "svcGbp":     {"label": "Google Business Profile","playbook": "workflows/gbp-optimization.yaml"},
    "svcPpc":     {"label": "PPC / Google Ads",       "playbook": "workflows/ppc-launch.yaml"},
    "svcPr":      {"label": "Authority / PR",         "playbook": "workflows/authority-building.yaml"},
    "svcLlm":     {"label": "LLM Visibility",         "playbook": "workflows/llm-visibility.yaml"},
}


# ── Friendly process labels ──────────────────────────────────────────────────
# Map raw tool name (or suffix after mcp__provider__) → human-friendly verb.
# When a tool isn't mapped, it's hidden from the feed entirely so the user
# never sees raw command names.
TOOL_LABELS: dict[str, str] = {
    # Built-in Claude tools we WANT to surface
    "WebFetch":      "Reading the website",
    # SearchAtlas brand vault
    "bv_list":             "Checking for an existing brand vault",
    "bv_create":           "Creating the brand vault",
    "bv_update":           "Saving brand details to the vault",
    "bv_get_details":      "Loading brand vault",
    "bv_get_business_info":"Loading business info",
    "bv_update_business_info": "Saving business info",
    "bv_get_knowledge_graph":  "Loading knowledge graph",
    "bv_update_knowledge_graph": "Building the knowledge graph",
    "bv_list_voice_profiles":  "Checking voice profiles",
    "bv_select_voice_profile": "Activating the voice profile",
    "bv_upload_image":     "Uploading brand asset",
    "bv_list_images":      "Listing brand images",
    "bv_list_sources":     "Listing brand sources",
    "update_refine_prompt":"Training the voice profile",
    "update_brand_vault":  "Saving brand details to the vault",
    "update_knowledge_graph": "Building the knowledge graph",
    "update_brand_vault_business_info": "Saving business info",
    # GBP
    "gbp_search_places":            "Searching Google for the business",
    "gbp_list_unconnected_locations": "Looking up Google Business listings",
    "gbp_list_locations":           "Listing connected GBP locations",
    "gbp_get_location":             "Loading the GBP profile",
    "gbp_get_location_stats":       "Reading GBP performance",
    "gbp_get_location_recommendations": "Generating GBP recommendations",
    "gbp_generate_location_recommendations": "Generating GBP recommendations",
    "gbp_get_business_categories":  "Matching GBP categories",
    "gbp_list_categories":          "Listing GBP categories",
    "gbp_list_attributes":          "Reading GBP attributes",
    "gbp_upsert_attributes":        "Saving GBP attributes",
    "gbp_upsert_standard_services": "Saving GBP services",
    "gbp_update_location":          "Updating the GBP profile",
    "gbp_suggest_description":      "Drafting GBP description",
    "gbp_create_audit_report_external": "Auditing the GBP profile",
    "gbp_get_audit_report":         "Loading GBP audit",
    # SEO / Site explorer
    "se_get_holistic_seo_scores":   "Scoring holistic SEO pillars",
    "se_get_organic_keywords":      "Analyzing organic keywords",
    "se_get_organic_competitors":   "Identifying organic competitors",
    "se_get_backlinks":             "Sampling backlink profile",
    "se_get_referring_domains":     "Mapping referring domains",
    "se_get_serp_overview":         "Reading SERP overview",
    "se_create_keyword_research":   "Setting up keyword research",
    "se_create_project":            "Creating the Site Explorer project",
    "se_lookup_keyword":            "Looking up keyword",
    # Keyword tracking
    "krt_create_project":           "Setting up keyword tracking",
    "krt_add_keywords":             "Adding target keywords",
    "krt_bulk_add_keywords":        "Adding target keywords",
    "krt_refresh_rankings":         "Pulling current rankings",
    # Content
    "cg_create_topical_map":        "Building the topical map",
    "cg_search_topical_maps":       "Looking up topical maps",
    "cg_topic_suggestions":         "Generating topic ideas",
    "cg_generate_complete_article": "Generating first article",
    "cg_dkn_generate_article":      "Generating article from knowledge graph",
    "cg_create_brand_vault":        "Creating brand vault",
    "cg_get_brand_vault_details":   "Loading brand vault",
    "cg_run_content_grader":        "Grading content quality",
    # OTTO
    "otto_list_projects":           "Checking for an existing OTTO project",
    "otto_find_project_by_hostname":"Looking up OTTO project",
    "otto_get_project_details":     "Loading OTTO project",
    "otto_create_audit":            "Creating the SEO audit",
    "otto_get_site_audit":          "Reading the SEO audit",
    "otto_engage_project":          "Engaging OTTO automation",
    "otto_get_project_issues_summary": "Reading site issues",
    "otto_get_issues_by_type":      "Categorizing site issues",
    "otto_generate_bulk_recommendations": "Generating SEO recommendations",
    "otto_activate_instant_indexing":  "Activating instant indexing",
    "otto_select_urls_for_indexing":   "Selecting URLs for indexing",
    "otto_show_quota":              "Checking your quota",
    "otto_get_quota":               "Checking your quota",
    "otto_update_knowledge_graph":  "Updating knowledge graph",
    # PPC
    "ppc_create_business":          "Setting up PPC business",
    "ppc_list_businesses":          "Looking up PPC business",
    "ppc_discover_products":        "Discovering products to advertise",
    "ppc_bulk_create_keyword_clusters": "Building keyword clusters",
    "ppc_bulk_create_ad_contents":  "Generating ad copy",
    "ppc_get_business":             "Loading PPC business",
    # PR / Authority
    "pr_create":                    "Drafting press release",
    "pr_publish":                   "Publishing press release",
    "dpr_create_campaign":          "Setting up digital PR campaign",
    "dpr_list_opportunities":       "Finding outreach opportunities",
    # LLM visibility
    "llmv_create_project":          "Setting up LLM visibility tracking",
    "llmv_submit_prompts":          "Querying LLMs",
    "llmv_get_brand_overview":      "Reading brand presence in LLMs",
    "llmv_get_visibility_trend":    "Reading visibility trend",
    "llmv_add_topic":               "Adding tracking topic",
    "llmv_add_query":               "Adding tracking query",
    # Account / quota
    "get_balance":                  "Checking your balance",
    "show_otto_quota":              "Checking your quota",
}

# Tools we silently skip (internal / noisy)
SILENT_TOOLS = {
    "Read", "Skill", "ToolSearch", "TodoWrite", "Glob", "Grep",
    "ListMcpResourcesTool", "ReadMcpResourceTool",
    "ExitPlanMode", "EnterPlanMode",
    "TaskCreate", "TaskList", "TaskUpdate", "TaskGet", "TaskOutput", "TaskStop",
}


def short_tool_name(raw: str) -> str:
    """Strip 'mcp__provider__' prefix to get the bare tool name."""
    if not raw:
        return ""
    if raw.startswith("mcp__"):
        parts = raw.split("__")
        if len(parts) >= 3:
            return parts[-1]
    return raw


def friendly_label(tool_name: str, tool_input: dict) -> str | None:
    """Returns a friendly label, or None if the tool should be hidden."""
    short = short_tool_name(tool_name)
    if tool_name in SILENT_TOOLS or short in SILENT_TOOLS:
        return None
    if short in TOOL_LABELS:
        return TOOL_LABELS[short]
    if tool_name == "Bash":
        # Hide all bash by default — too noisy. The phase headings cover it.
        return None
    if tool_name == "WebFetch":
        url = (tool_input.get("url") or "").strip()
        if url:
            host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            return f"Reading {host}"
        return TOOL_LABELS["WebFetch"]
    if tool_name == "Edit":
        return None  # covered by file-write rollup
    if tool_name == "Write":
        return None  # covered by file-write rollup
    return None


# ── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(title="AMM Command Center", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return FileResponse(HERE / "index.html")


# ── Health (cached, slow first call) ─────────────────────────────────────────


_mcp_cache: dict = {"checked_at": 0.0, "sa_configured": False}
_MCP_CACHE_TTL = 300


async def _check_sa_mcp_configured(claude_path: str) -> bool:
    now = time.monotonic()
    if now - _mcp_cache["checked_at"] < _MCP_CACHE_TTL:
        return bool(_mcp_cache["sa_configured"])
    try:
        proc = await asyncio.create_subprocess_exec(
            claude_path, "mcp", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        text = (stdout or b"").decode("utf-8", errors="replace").lower()
        ok = "searchatlas" in text
    except Exception:
        ok = False
    _mcp_cache["checked_at"] = now
    _mcp_cache["sa_configured"] = ok
    return ok


@app.get("/api/health")
async def health():
    claude_path = shutil.which("claude")
    sa_configured = False
    if claude_path:
        sa_configured = await _check_sa_mcp_configured(claude_path)
    return {
        "claude_available": bool(claude_path),
        "claude_path": claude_path,
        "searchatlas_mcp_configured": sa_configured,
        "toolkit_root": str(TOOLKIT_ROOT),
    }


# ── Prompt builder ───────────────────────────────────────────────────────────


def domain_clean(raw: str) -> str:
    d = (raw or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0].split("?")[0].split("#")[0]
    return d.strip().rstrip(".")


def domain_to_slug(domain: str) -> str:
    d = domain_clean(domain)
    parts = d.split(".")
    if len(parts) >= 2:
        return re.sub(r"[^a-z0-9-]+", "-", "-".join(parts[:-1])).strip("-") or "client"
    return re.sub(r"[^a-z0-9-]+", "-", d).strip("-") or "client"


def build_prompt(payload: dict) -> str:
    domain = domain_clean(payload.get("domain") or "")
    slug = domain_to_slug(domain)

    selected_services = [
        SERVICE_PLAYBOOKS[k] for k in SERVICE_PLAYBOOKS if payload.get(k)
    ]

    L: list[str] = []
    L.append("# /onboard-client · automated run from AMM Command Center")
    L.append("")
    L.append("Run the `/onboard-client` slash command end-to-end with the data below.")
    L.append("**Skip Phase 0** (path picker) — proceed directly with **Path B (new client)**.")
    L.append(f"Use slug `{slug}` for the local client folder under `clients/{slug}/`.")
    L.append("**Do NOT ask any interactive questions.** All required data is provided here or must be derived by crawling the domain and querying SearchAtlas.")
    L.append("")
    L.append("Output formatting rules — important for the UI:")
    L.append("- Begin every phase with a heading on its own line: `## Phase N — name` (use the friendly names listed below).")
    L.append("- Keep narration tight: short sentences, plain English, no jargon, no command names. The UI auto-friendlies tool calls; you don't need to mention them.")
    L.append("- After major milestones, drop a short fact line (e.g. `Brand vault created — uuid d3a…`).")
    L.append("- Don't print individual file paths. The UI will summarize them.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 1 — Reading the site")
    L.append("")
    L.append(f"Fetch `https://{domain}` (homepage, contact page, about page, services page if present) using WebFetch and extract:")
    L.append("- Business name (legal/trading name as displayed)")
    L.append("- Industry (2–3 word category)")
    L.append("- Description (2–3 sentences — what they do, who they serve, what's different)")
    L.append("- Phone, email, full street address")
    L.append("- Hours, service areas")
    L.append("- Top 3–5 services or product lines")
    L.append("- Brand colors (from CSS / logo / theme — only if obvious)")
    L.append("- Logo URL (largest header image, or favicon as fallback)")
    L.append("")
    L.append("If a field can't be extracted confidently, mark it `(unknown)` and proceed.")
    L.append("After this phase, output one short sentence stating the business name and city you found.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 2 — Creating the brand vault")
    L.append("")
    L.append("Check for an existing brand vault for this domain. If none, create one and immediately push: business info, brand details (colors, industry, description), the voice profile (tone + style + avoid list provided in section 3), and the knowledge graph (services + competitors).")
    L.append("After the vault is created, state its UUID in one short line.")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Phase 3 — Layering off-website intelligence")
    L.append("")

    tone = payload.get("tone") or ""
    reading = payload.get("readingLevel") or ""
    style = payload.get("styleNotes") or ""
    avoid = payload.get("avoidList") or ""
    L.append("### Brand voice")
    L.append(f"- Tone: {tone or 'detect from site copy'}")
    if reading: L.append(f"- Reading level: {reading}")
    if style: L.append(f"- Style notes: {style}")
    if avoid: L.append(f"- Avoid list: {avoid}")
    L.append("")
    L.append("Push tone + style notes + avoid list to the brand vault via `update_refine_prompt`. This is the agency's voice — it's how every article and ad will sound.")
    L.append("")

    knowledge = (payload.get("knowledge") or "").strip()
    files = payload.get("files") or []
    text_files = [f for f in files if f.get("kind") == "text" and f.get("content")]
    image_files = [f for f in files if f.get("kind") == "image"]
    binary_files = [f for f in files if f.get("kind") == "binary"]

    if knowledge or text_files or image_files or binary_files:
        L.append("### Off-website context")
        L.append("Treat this as primary brand training material — push it to the refine prompt and weight it more heavily than the crawled site copy. This is what makes the agency's onboarding different from a website scrape.")
        L.append("")
        if knowledge:
            L.append("```")
            L.append(knowledge)
            L.append("```")
            L.append("")
        for f in text_files:
            L.append(f"**`{f.get('name')}`** ({f.get('size', 0)} bytes)")
            L.append("```")
            content = f.get("content") or ""
            if len(content) > 8000:
                content = content[:8000] + f"\n…(truncated — original was {f.get('size')} bytes)"
            L.append(content)
            L.append("```")
            L.append("")
        if image_files:
            L.append("**Images dropped by the user** — save under `clients/{slug}/assets/` and upload via `bv_upload_image` once the vault UUID is known:")
            for f in image_files:
                L.append(f"- `{f.get('name')}` ({f.get('size', 0)} bytes, {f.get('type', 'image')})")
            L.append("")
        if binary_files:
            L.append("**Binary files dropped (not auto-processed — listed for the agency's reference):**")
            for f in binary_files:
                L.append(f"- `{f.get('name')}` ({f.get('size', 0)} bytes)")
            L.append("")
    else:
        L.append("(No off-website intelligence provided — proceed with crawled site data only.)")
        L.append("")

    L.append("---")
    L.append("")

    if payload.get("svcGbp"):
        L.append("## Phase 4 — Connecting Google Business Profile")
        L.append("")
        L.append("Use `gbp_search_places` with the business name + city extracted in Phase 1. Find the listing whose website matches the domain (compare against `https://{domain}` and the bare hostname). If exactly one match is found, take its place_id and connect it to SearchAtlas via the appropriate brand-vault / GBP linking flow. If multiple plausible matches exist, list them in the summary and proceed without blocking — the agency will confirm in SA. Do not silently skip GBP — it's the most-touched profile.")
        L.append("")
        L.append("After connection, run `gbp_create_audit_report_external` to start the GBP audit.")
        L.append("")
        L.append("---")
        L.append("")

    L.append("## Phase 5 — Running playbooks")
    L.append("")
    if not selected_services:
        L.append("(No services selected — skip this phase.)")
    else:
        L.append("Read each playbook YAML for the exact tool-call sequence — don't improvise. Copy each to `plans/clients/{slug}/{YYYY-MM}.yaml`, fill in client + IDs, and execute steps in order. Mark each step as completed.")
        L.append("")
        for svc in selected_services:
            L.append(f"- **{svc['label']}** → `{svc['playbook']}`")
        L.append("")
        L.append("If a step blocks (e.g. needs a Google Ads account ID we don't have), note it briefly and continue.")
        L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 6 — Finalizing")
    L.append("")
    L.append("Write `clients/{slug}/CLAUDE.md` and `clients/{slug}/brand-profile.md` from the templates. Don't print the full contents — just confirm both files exist.")
    L.append("")
    L.append("End with a short summary block:")
    L.append("- Business name (the one extracted from the site)")
    L.append("- Brand vault UUID")
    L.append("- OTTO project ID (if any)")
    L.append("- GBP location (if connected) — name + city")
    L.append("- Services configured")
    L.append("")
    L.append("Begin now.")

    return "\n".join(L)


# ── Stream parser → friendly UI events ───────────────────────────────────────


PHASE_RE = re.compile(r"^##\s+Phase\s+\d+\s*[—\-:]\s*(.+)$", re.IGNORECASE)
BIZ_LINE_RE = re.compile(r"(?:business name|business is|client(?:'s)? name|onboarding)\s*[:\-]?\s*\*?\*?([A-Z][A-Za-z0-9&'\.\- ]{2,60?})\*?\*?", re.IGNORECASE)


_state: dict = {"workspace_announced": False, "biz_seen": False}


def reset_run_state() -> None:
    _state["workspace_announced"] = False
    _state["biz_seen"] = False


def parse_claude_event(raw_line: str) -> list[dict]:
    raw_line = raw_line.strip()
    if not raw_line:
        return []
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError:
        return []

    events: list[dict] = []
    msg_type = data.get("type")

    if msg_type == "system":
        if data.get("subtype") == "init":
            events.append({"type": "phase", "label": "Engine started"})
        return events

    if msg_type == "assistant":
        message = data.get("message", {})
        for block in message.get("content", []):
            btype = block.get("type")
            if btype == "text":
                text = (block.get("text") or "").strip()
                if not text:
                    continue
                for ln in text.splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    # Detect a "## Phase N — name" line → phase event
                    m = PHASE_RE.match(ln)
                    if m:
                        events.append({"type": "phase", "label": m.group(1).strip()})
                        continue
                    # Skip empty markdown rules
                    if ln in ("---", "***", "===") or ln.startswith("#"):
                        continue
                    # Try to capture business name (first time only)
                    if not _state["biz_seen"]:
                        # Looking for things like: "Found: Coastal Dental Group in Miami"
                        # or "The business is **Coastal Dental Group**"
                        bm = re.search(
                            r"(?:business\s+(?:name|is)\s*[:\-]?\s*|\bfound\s*[:\-]?\s*)\*?\*?([A-Z][A-Za-z0-9&'\.\- ]{2,80}?)\*?\*?(?:\s+in\s+|\s*[\.,]|$)",
                            ln,
                        )
                        if bm:
                            name = bm.group(1).strip().strip(".,")
                            if 3 <= len(name) <= 80:
                                _state["biz_seen"] = True
                                events.append({"type": "biz", "name": name})
                    # Plain assistant narration → "note" item
                    # Cap to a reasonable length
                    if len(ln) > 200:
                        ln = ln[:197] + "…"
                    events.append({"type": "note", "label": ln})
            elif btype == "tool_use":
                tool_name = block.get("name", "tool")
                tool_input = block.get("input", {}) or {}
                # File writes → consolidated workspace event, only once
                if tool_name in ("Write", "Edit"):
                    if not _state["workspace_announced"]:
                        _state["workspace_announced"] = True
                        events.append({"type": "work", "label": "Creating your workspace"})
                    continue
                label = friendly_label(tool_name, tool_input)
                if label:
                    events.append({"type": "work", "label": label})
        return events

    if msg_type == "user":
        message = data.get("message", {})
        for block in message.get("content", []):
            if block.get("type") == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                else:
                    text = str(content)
                # Promote the prior 'work' to 'done' is hard from server-side without state;
                # we instead emit a 'done' event so the feed shows progress.
                if text and "error" not in text.lower()[:200]:
                    events.append({"type": "done", "label": "Step complete"})
                elif text:
                    events.append({"type": "error", "message": text[:200]})
        return events

    if msg_type == "result":
        events.append({"type": "complete"})
        return events

    return events


async def stream_claude(prompt: str) -> AsyncIterator[bytes]:
    reset_run_state()

    async def emit(obj: dict) -> bytes:
        return f"data: {json.dumps(obj)}\n\n".encode()

    yield await emit({"type": "phase", "label": "Setup"})
    yield await emit({"type": "note", "label": f"Working from {TOOLKIT_ROOT.name}"})

    cmd = [
        "claude", "-p",
        "--output-format", "stream-json",
        "--verbose",
        prompt,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(TOOLKIT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        yield await emit({"type": "error", "message": "claude CLI not found on PATH"})
        return
    except Exception as exc:
        yield await emit({"type": "error", "message": f"Failed to spawn Claude: {exc}"})
        return

    assert proc.stdout is not None
    while True:
        line_bytes = await proc.stdout.readline()
        if not line_bytes:
            break
        line = line_bytes.decode("utf-8", errors="replace")
        for evt in parse_claude_event(line):
            yield await emit(evt)

    rc = await proc.wait()
    if rc != 0:
        stderr = (await proc.stderr.read()).decode("utf-8", errors="replace") if proc.stderr else ""
        yield await emit({"type": "error", "message": f"Claude exited {rc}. {stderr[:300]}"})
    else:
        yield await emit({"type": "complete"})


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/api/onboard")
async def onboard(request: Request):
    payload = await request.json()
    if not domain_clean(payload.get("domain") or ""):
        return JSONResponse({"error": "domain is required"}, status_code=400)
    prompt = build_prompt(payload)
    return StreamingResponse(
        stream_claude(prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/preview-prompt")
async def preview_prompt(request: Request):
    payload = await request.json()
    return {"prompt": build_prompt(payload)}


# ── Entrypoint ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    print(f"\n  AMM Command Center")
    print(f"  → http://localhost:{port}\n")
    print(f"  Toolkit root: {TOOLKIT_ROOT}")
    print(f"  Claude CLI:   {shutil.which('claude') or '(not found)'}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
