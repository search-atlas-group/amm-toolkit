"""
Website Build Wizard — local server that bridges the web UI to Claude Code.

Each wizard step that needs real data calls a small, single-purpose `claude -p`
subprocess. The Claude CLI spawned here only has permission to call SearchAtlas
MCP tools — never WebFetch, Edit, or Bash for these step endpoints. That keeps
the contract narrow: the JSON we return is a direct projection of real MCP
`tool_use` / `tool_result` blocks that Claude emitted.

Endpoints
---------
- POST /api/auth-probe       — JSON. Spawns Claude with empty payload, asks it to
                                call `cg_list_brand_vaults({})` once. Returns
                                `{"authenticated": bool, "error": "..." | None}`.

- POST /api/detect-assets    — JSON. Payload `{ "domain": ... }`. Asks Claude to
                                run `cg_list_brand_vaults` + `gbp_list_locations`
                                filtered by domain and return a single JSON line.

- POST /api/pull-bv          — JSON. Payload `{ "brand_vault_uuid", "hostname" }`.
                                Pulls bv_get_details + bv_get_business_info +
                                bv_list_voice_profiles + bv_get_knowledge_graph.

- POST /api/create-bv        — JSON. Payload = operator-confirmed fields.
                                Calls bv_create then bv_update_business_info,
                                bv_update, bv_update_knowledge_graph.

- POST /api/research-market  — SSE. Payload = domain + industry + target keywords
                                + known competitors + services + location.
                                Streams the two-wave research and emits a final
                                `result` event with the proposed sitemap.

- POST /api/build            — SSE. Original end-to-end build endpoint
                                (unchanged behaviour, runs `/build-website`).

- POST /api/preview-prompt   — JSON. Echoes the assembled build-website prompt.

- GET  /api/health           — JSON. Claude CLI + SA MCP availability.

Guardrails (applied to every wizard endpoint)
---------------------------------------------
- The Claude subprocess is asked to call SPECIFIC SA MCP tools — and is told to
  emit `<<<RESULT>>>{json}<<<END>>>` exactly once with the merged real data.
- If the output contains forbidden tokens (`{pending}`, `{uuid}`, `simulated`,
  `would normally`) → HTTP 502 `{"error": "fabricated_data"}`.
- If ZERO `tool_use` blocks were emitted but tools were required → HTTP 502
  `{"error": "no_tool_calls_made"}`.
- If any MCP call returns auth / 401 / unauthorized errors → HTTP 401
  `{"error": "authentication_required"}`.
- All requests + responses are appended to `/tmp/amm-website-build-audit.log`.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


HERE = Path(__file__).resolve().parent
AUDIT_LOG = Path("/tmp/amm-website-build-audit.log")


# ── Lifecycle: heartbeat + PID-aware idle shutdown ───────────────────────────
# See command-center/server.py for the full design. Bridge stays alive while:
#   - The welcome.html (or wizard) tab is open (heartbeats every 60s)
#   - A Claude subprocess we spawned is still running
#   - An SSE stream is open
# After IDLE_TIMEOUT_S with none of the above, the bridge exits cleanly.
IDLE_TIMEOUT_S = 300
IDLE_CHECK_INTERVAL_S = 30
_last_heartbeat: float = time.monotonic()
_active_jobs: set[int] = set()
_active_streams: int = 0


def _bump_heartbeat() -> None:
    global _last_heartbeat
    _last_heartbeat = time.monotonic()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _reap_dead_jobs() -> None:
    dead = [pid for pid in _active_jobs if not _pid_alive(pid)]
    for pid in dead:
        _active_jobs.discard(pid)


async def _idle_watcher() -> None:
    while True:
        await asyncio.sleep(IDLE_CHECK_INTERVAL_S)
        _reap_dead_jobs()
        idle_age = time.monotonic() - _last_heartbeat
        if (
            idle_age > IDLE_TIMEOUT_S
            and not _active_jobs
            and _active_streams == 0
        ):
            print(
                f"[idle-shutdown] no activity for {idle_age:.0f}s — exiting",
                flush=True,
            )
            os.kill(os.getpid(), signal.SIGTERM)
            return


def find_toolkit_root(start: Path) -> Path:
    cur = start
    for _ in range(6):
        if (cur / "commands" / "build-website.md").exists():
            return cur
        cur = cur.parent
    return start.parent


TOOLKIT_ROOT = find_toolkit_root(HERE)


# ── Audit log ────────────────────────────────────────────────────────────────


def audit(event: str, payload: Any) -> None:
    """Append a JSON line to the audit log. Best-effort, never raises."""
    try:
        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "payload": payload,
        }
        with AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except Exception:
        pass


# ── Tool labels (used by the SSE build endpoint) ─────────────────────────────


TOOL_LABELS: dict[str, str] = {
    "WebFetch":      "Reading the website",
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
    "gbp_search_places":            "Searching Google for the business",
    "gbp_list_unconnected_locations": "Looking up Google Business listings",
    "gbp_list_locations":           "Listing connected GBP locations",
    "gbp_get_location":             "Loading the GBP profile",
    "gbp_get_location_stats":       "Reading GBP performance",
    "gbp_get_location_recommendations": "Generating GBP recommendations",
    "gbp_generate_location_recommendations": "Generating GBP recommendations",
    "gbp_get_business_categories":  "Matching GBP categories",
    "gbp_list_categories":          "Pulling GBP category taxonomy",
    "gbp_list_attributes":          "Reading GBP attributes",
    "gbp_upsert_attributes":        "Saving GBP attributes",
    "gbp_upsert_standard_services": "Saving GBP services",
    "gbp_update_location":          "Updating the GBP profile",
    "gbp_suggest_description":      "Drafting GBP description",
    "gbp_create_audit_report_external": "Auditing the GBP profile",
    "gbp_get_audit_report":         "Loading GBP audit",
    "se_get_holistic_seo_scores":   "Scoring holistic SEO pillars",
    "se_get_organic_keywords":      "Analyzing organic keywords",
    "se_get_organic_competitors":   "Identifying organic competitors",
    "se_get_backlinks":             "Sampling backlink profile",
    "se_get_referring_domains":     "Mapping referring domains",
    "se_get_serp_overview":         "Mapping who ranks today",
    "se_get_serp_features":         "Reading SERP features",
    "se_get_indexed_pages":         "Mirroring competitor page structures",
    "se_analyze_keyword_gap":       "Analyzing keyword gaps",
    "se_create_keyword_research":   "Setting up keyword research",
    "se_create_project":            "Creating the Site Explorer project",
    "se_lookup_keyword":            "Validating target keywords",
    "krt_create_project":           "Setting up keyword tracking",
    "krt_add_keywords":             "Adding target keywords",
    "krt_bulk_add_keywords":        "Adding target keywords",
    "krt_refresh_rankings":         "Pulling current rankings",
    "cg_create_topical_map":        "Building topical map",
    "cg_search_topical_maps":       "Looking up topical maps",
    "cg_topic_suggestions":         "Pulling knowledge-graph topics",
    "cg_generate_complete_article": "Generating first article",
    "cg_dkn_generate_article":      "Generating article from knowledge graph",
    "cg_create_brand_vault":        "Creating brand vault",
    "cg_get_brand_vault_details":   "Loading brand vault",
    "cg_run_content_grader":        "Grading content quality",
    "cg_list_brand_vaults":         "Checking for an existing brand vault",
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
    "otto_generate_page_schema":    "Generating schema markup",
    "otto_deploy_page_schema":      "Deploying schema",
    "otto_show_quota":              "Checking your quota",
    "otto_get_quota":               "Checking your quota",
    "otto_get_task_status":         "Checking task status",
    "otto_update_knowledge_graph":  "Updating knowledge graph",
    "indexer_submit_batch":         "Submitting URLs to Google",
    "indexer_check_status":         "Checking indexing status",
    "ws_create_project":            "Scaffolding Website Studio project",
    "ws_publish_project":           "Publishing to Website Studio",
    "ws_get_project":               "Verifying Website Studio state",
    "ws_ensure_containers_running": "Starting Website Studio build environment",
    "ws_list_projects":             "Listing Website Studio projects",
    "llmv_get_brand_overview":      "Reading brand presence in LLMs",
    "kg_validate_completeness":     "Validating knowledge graph completeness",
    "get_balance":                  "Checking your balance",
    "show_otto_quota":              "Checking your quota",
}

SILENT_TOOLS = {
    "Read", "Skill", "ToolSearch", "TodoWrite", "Glob", "Grep",
    "ListMcpResourcesTool", "ReadMcpResourceTool",
    "ExitPlanMode", "EnterPlanMode",
    "TaskCreate", "TaskList", "TaskUpdate", "TaskGet", "TaskOutput", "TaskStop",
}


def short_tool_name(raw: str) -> str:
    if not raw:
        return ""
    if raw.startswith("mcp__"):
        parts = raw.split("__")
        if len(parts) >= 3:
            return parts[-1]
    return raw


def friendly_label(tool_name: str, tool_input: dict) -> str | None:
    short = short_tool_name(tool_name)
    if tool_name in SILENT_TOOLS or short in SILENT_TOOLS:
        return None
    if short in TOOL_LABELS:
        return TOOL_LABELS[short]
    if tool_name == "Bash":
        return None
    if tool_name == "WebFetch":
        url = (tool_input.get("url") or "").strip()
        if url:
            host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            return f"Reading {host}"
        return TOOL_LABELS["WebFetch"]
    if tool_name in ("Edit", "Write"):
        return None
    return None


# ── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(title="Website Build Wizard", version="2.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _start_idle_watcher() -> None:
    _bump_heartbeat()
    asyncio.create_task(_idle_watcher())


@app.get("/")
async def root():
    return FileResponse(HERE / "index.html")


@app.post("/api/heartbeat")
async def heartbeat():
    """Browser tab pings this every ~60s while the wizard or welcome.html is
    open. Stops idle-shutdown from firing while a user is around."""
    _bump_heartbeat()
    return {
        "ok": True,
        "active_jobs": len(_active_jobs),
        "active_streams": _active_streams,
        "idle_timeout_s": IDLE_TIMEOUT_S,
    }


@app.get("/api/ping")
async def ping():
    """Cheap liveness probe — /api/health blocks on `claude mcp list` for up to
    30 s on cold start. welcome.html uses this instead for fast UP detection."""
    _bump_heartbeat()
    return {"ok": True, "bridge": "website-build"}


# ── Health (cached) ──────────────────────────────────────────────────────────


_mcp_cache: dict = {"checked_at": 0.0, "sa_configured": False}
_MCP_CACHE_TTL_OK = 300
_MCP_CACHE_TTL_FAIL = 10  # HIGH-6: never trap operator in a 5-minute false negative.


async def _check_sa_mcp_configured(claude_path: str) -> bool:
    now = time.monotonic()
    elapsed = now - _mcp_cache["checked_at"]
    cached_ok = bool(_mcp_cache.get("sa_configured"))
    if cached_ok and elapsed < _MCP_CACHE_TTL_OK:
        return True
    if (not cached_ok) and elapsed < _MCP_CACHE_TTL_FAIL:
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            claude_path, "mcp", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        text = (stdout or b"").decode("utf-8", errors="replace").lower()
        ok = (
            "mcp.searchatlas.com" in text
            or "searchatlas" in text
            or "search atlas" in text
            or "search-atlas" in text
            or "search_atlas" in text
        )
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


# ── Domain helpers ───────────────────────────────────────────────────────────


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


# ── Subprocess runner: spawn `claude -p`, collect every tool_use / tool_result,
# extract the operator-supplied <<<RESULT>>>{json}<<<END>>> block ────────────


MCP_NAMESPACE_HINT = (
    "IMPORTANT — Search Atlas MCP namespace. SA tools are exposed under one of two\n"
    "namespace prefixes depending on how the user installed the connector:\n"
    "  - `mcp__searchatlas__<tool>`               (manual `claude mcp add` install)\n"
    "  - `mcp__claude_ai_Search_Atlas__<tool>`    (claude.ai connector install)\n"
    "If a referenced tool name isn't directly available in your tool set,\n"
    "call `ToolSearch` with the query `select:mcp__claude_ai_Search_Atlas__<tool>`\n"
    "to load its schema, then call the loaded tool. Use whichever variant works.\n"
    "Either namespace produces an identical response shape.\n"
    "\n"
)

RESULT_BLOCK_RE = re.compile(r"<<<RESULT>>>(.*?)<<<END>>>", re.DOTALL)
FORBIDDEN_TOKENS = (
    "{pending}", "{uuid}", "would normally", "simulated",
    "i would call", "i'll call", "in a real run",
)
AUTH_ERROR_RE = re.compile(
    r"(not authenticated|unauthorized|401|connector\s*not\s*authenticated|"
    r"oauth|please\s+authenticate|sign\s+in\s+to|authentication\s+required|"
    r"authorize.*searchatlas)",
    re.IGNORECASE,
)


class ClaudeRunResult:
    __slots__ = (
        "raw_lines", "stdout_text", "stderr_text", "tool_calls",
        "tool_results", "rc", "timeout", "result_blob"
    )

    def __init__(self) -> None:
        self.raw_lines: list[str] = []
        self.stdout_text: str = ""
        self.stderr_text: str = ""
        self.tool_calls: list[dict] = []  # [{name, input}]
        self.tool_results: list[dict] = []  # [{tool_use_id, content_text, is_error}]
        self.rc: int = -1
        self.timeout: bool = False
        self.result_blob: dict | None = None


async def run_claude_step(
    prompt: str,
    *,
    timeout_s: float = 60.0,
    expect_tools: bool = True,
    required_tool_substrings: list[str] | None = None,
) -> ClaudeRunResult:
    """Spawn `claude -p` with stream-json output, collect all tool activity,
    and parse the operator's <<<RESULT>>>{json}<<<END>>> block out of the
    final assistant text."""
    out = ClaudeRunResult()
    claude_path = shutil.which("claude")
    if not claude_path:
        out.stderr_text = "claude CLI not found on PATH"
        return out

    cmd = [
        claude_path, "-p",
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
    except Exception as exc:
        out.stderr_text = f"failed to spawn claude: {exc}"
        return out

    _active_jobs.add(proc.pid)
    _bump_heartbeat()
    text_chunks: list[str] = []

    async def _read_stream() -> None:
        assert proc.stdout is not None
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            out.raw_lines.append(line)
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            mtype = data.get("type")
            if mtype == "assistant":
                msg = data.get("message", {}) or {}
                for block in msg.get("content", []) or []:
                    btype = block.get("type")
                    if btype == "text":
                        text_chunks.append(block.get("text") or "")
                    elif btype == "tool_use":
                        out.tool_calls.append({
                            "id": block.get("id"),
                            "name": block.get("name", ""),
                            "input": block.get("input") or {},
                        })
            elif mtype == "user":
                msg = data.get("message", {}) or {}
                for block in msg.get("content", []) or []:
                    if block.get("type") == "tool_result":
                        content = block.get("content", "")
                        if isinstance(content, list):
                            content_text = " ".join(
                                c.get("text", "") for c in content
                                if isinstance(c, dict)
                            )
                        else:
                            content_text = str(content)
                        out.tool_results.append({
                            "tool_use_id": block.get("tool_use_id"),
                            "content_text": content_text,
                            "is_error": bool(block.get("is_error")),
                        })

    try:
        await asyncio.wait_for(_read_stream(), timeout=timeout_s)
        out.rc = await proc.wait()
    except asyncio.TimeoutError:
        out.timeout = True
        try:
            proc.kill()
        except Exception:
            pass
        try:
            await proc.wait()
        except Exception:
            pass
    finally:
        _active_jobs.discard(proc.pid)

    if proc.stderr is not None:
        try:
            err = await proc.stderr.read()
            out.stderr_text = err.decode("utf-8", errors="replace")
        except Exception:
            pass

    out.stdout_text = "\n".join(text_chunks)

    # Extract <<<RESULT>>>{json}<<<END>>>
    m = RESULT_BLOCK_RE.search(out.stdout_text)
    if m:
        blob_text = m.group(1).strip()
        # Tolerate fenced code wrappers
        blob_text = re.sub(r"^```(?:json)?\s*", "", blob_text)
        blob_text = re.sub(r"\s*```$", "", blob_text)
        try:
            out.result_blob = json.loads(blob_text)
        except json.JSONDecodeError:
            out.result_blob = None

    return out


_STRONG_AUTH_PATTERNS = re.compile(
    r"(\b401\b|not\s+authenticated|connector\s*not\s*authenticated|oauth\s+required)",
    re.IGNORECASE,
)


def _has_auth_error(run: ClaudeRunResult) -> bool:
    # Auth error if any tool_result contains an auth-shaped string AND is_error
    for tr in run.tool_results:
        if tr.get("is_error") and AUTH_ERROR_RE.search(tr.get("content_text", "")):
            return True
    # Or if the assistant text itself surfaces auth failure
    if AUTH_ERROR_RE.search(run.stdout_text or ""):
        # Strong auth patterns (401 / "not authenticated" / "connector not
        # authenticated" / "OAuth required") are unambiguous — no keyword
        # qualifier required.
        if _STRONG_AUTH_PATTERNS.search(run.stdout_text):
            return True
        # Weaker auth-shaped strings still require an SA/MCP/BV keyword to
        # avoid false positives on unrelated narration.
        if re.search(r"(searchatlas|mcp|brand\s*vault)", run.stdout_text, re.I):
            return True
    return False


def _contains_forbidden_token(run: ClaudeRunResult) -> str | None:
    text = (run.stdout_text or "").lower()
    for tok in FORBIDDEN_TOKENS:
        if tok in text:
            return tok
    return None


def _called_required_tools(run: ClaudeRunResult, required: list[str]) -> bool:
    names = [short_tool_name(t.get("name", "")) for t in run.tool_calls]
    return all(any(req in n for n in names) for req in required)


# ── /api/auth-probe ──────────────────────────────────────────────────────────


AUTH_PROBE_PROMPT = """You are a non-interactive auth probe for the SearchAtlas MCP connector.

Call exactly ONE Search Atlas MCP tool, with empty parameters, then emit the
result block. The Search Atlas MCP may be exposed under any of these
namespace prefixes — use whichever variant is available in this session:

  - mcp__searchatlas__cg_list_brand_vaults
  - mcp__claude_ai_Search_Atlas__cg_list_brand_vaults

Input: {}

If you cannot find ANY variant of `cg_list_brand_vaults` in your available
tools, you MUST first call `ToolSearch` with the query
`select:mcp__claude_ai_Search_Atlas__cg_list_brand_vaults` to load its schema,
then immediately call the loaded tool. This is acceptable.

After the SA tool returns, emit on its own line, with no prefix:

<<<RESULT>>>{"authenticated": <true|false>, "tool_called": "cg_list_brand_vaults", "error": "<short message or empty>"}<<<END>>>

Rules:
- If the tool returns ANY result (even an empty list) → authenticated: true, error: "".
- If the tool returns an authentication / OAuth / 401 / "not authenticated" / "unauthorized" / "connector not authenticated" error → authenticated: false, error: <the error message, single line, < 240 chars>.
- Do NOT invent or simulate a response. The probe is invalid unless the real SA tool was invoked.
- After emitting the RESULT block, stop. Do not continue.
- Do not call WebFetch, Read, Bash, Edit, or any tool other than ToolSearch (to load) and the SA cg_list_brand_vaults tool.
"""


@app.post("/api/auth-probe")
async def auth_probe(request: Request):
    rid = uuid.uuid4().hex[:8]
    audit("auth-probe:request", {"rid": rid})

    # Fast path: if `claude mcp list` doesn't show searchatlas, no need to spawn
    # a 60-second subprocess just to discover the connector is missing.
    claude_path = shutil.which("claude")
    if claude_path:
        sa_configured = await _check_sa_mcp_configured(claude_path)
        if not sa_configured:
            audit("auth-probe:short-circuit", {"rid": rid, "reason": "mcp_not_configured"})
            return JSONResponse(
                {"authenticated": False, "error": "searchatlas_mcp_not_configured"},
                status_code=200,
            )

    try:
        run = await run_claude_step(
            AUTH_PROBE_PROMPT,
            timeout_s=45.0,
            expect_tools=True,
            required_tool_substrings=["cg_list_brand_vaults"],
        )
    except Exception as exc:
        audit("auth-probe:exception", {"rid": rid, "err": str(exc)})
        return JSONResponse({"authenticated": False, "error": f"server_error: {exc}"}, status_code=500)

    audit("auth-probe:tool_calls", {
        "rid": rid,
        "tool_calls": [t.get("name") for t in run.tool_calls],
        "tool_results_n": len(run.tool_results),
        "rc": run.rc,
        "timeout": run.timeout,
        "result_blob": run.result_blob,
    })

    if run.timeout:
        # Treat as not-authenticated rather than a hard 504 — the modal will
        # show a friendly retry path and the wizard stays operable.
        return JSONResponse(
            {"authenticated": False, "error": "timeout — probe took too long"},
            status_code=200,
        )

    # No tool calls at all → cannot trust the answer
    if not run.tool_calls:
        return JSONResponse(
            {"authenticated": False, "error": "no_tool_calls_made"},
            status_code=200,
        )

    # We require the model to have called cg_list_brand_vaults via ANY namespace.
    # If it only called ToolSearch (deferred-tool loader) and never reached the
    # SA tool, fall through to the result_blob, which the model populates with
    # the error message — that's still authoritative for our auth verdict.
    called_sa_bv = _called_required_tools(run, ["cg_list_brand_vaults"])
    blob = run.result_blob or {}

    if not called_sa_bv:
        # Trust the result blob if the model honestly reported that the tool
        # wasn't available in this environment. That's the same outcome as
        # "MCP not configured" from the user's perspective.
        err = (blob.get("error") or "").strip()
        if err:
            return JSONResponse(
                {"authenticated": False, "error": err},
                status_code=200,
            )
        audit("auth-probe:wrong-tool", {
            "rid": rid,
            "tool_calls": [t.get("name") for t in run.tool_calls],
        })
        return JSONResponse(
            {"authenticated": False, "error": "wrong_tool_called"},
            status_code=502,
        )

    if _has_auth_error(run):
        return JSONResponse(
            {"authenticated": False, "error": "authentication_required"},
            status_code=200,
        )

    # Inspect the result blob the model emitted
    authed = bool(blob.get("authenticated"))
    if authed:
        return {"authenticated": True, "error": None}

    err = (blob.get("error") or "").strip() or "unknown"
    return {"authenticated": False, "error": err}


# ── /api/detect-assets ───────────────────────────────────────────────────────


def detect_assets_prompt(domain: str, business: str, location: str) -> str:
    return f"""{MCP_NAMESPACE_HINT}You are a non-interactive SearchAtlas asset detector. Do not narrate.

Domain: {domain}
Business hint: {business or "(unknown)"}
Location hint: {location or "(unknown)"}

Fire BOTH tools in parallel (single tool batch):

  1. mcp__searchatlas__cg_list_brand_vaults  with input filtering by the hostname `{domain}`
     (try {{ "search": "{domain}" }} or {{ "domain": "{domain}" }} — whichever the schema accepts).
  2. mcp__searchatlas__gbp_list_locations    with input filtering by `{domain}` and/or `{business}`
     (try {{ "search": "{business or domain}" }} or {{ "domain": "{domain}" }} — whichever is accepted).

Then emit exactly one result block. Use ONLY real values returned by the tools — never invent UUIDs.

<<<RESULT>>>
{{
  "bv":  {{ "found": <true|false>, "uuid": "<real uuid or empty>", "name": "<real name or empty>" }},
  "gbp": {{ "found": <true|false>, "location_id": "<real id or empty>", "name": "<real name or empty>" }}
}}
<<<END>>>

Rules:
- If a tool returns an authentication error, emit `<<<RESULT>>>{{"error":"authentication_required"}}<<<END>>>` and stop.
- If either list is empty for this domain → found: false, ids empty.
- Match is case-insensitive against hostname or business name.
- Do not invent. Do not say "would normally". Do not include unrelated entries.
"""


@app.post("/api/detect-assets")
async def detect_assets(request: Request):
    rid = uuid.uuid4().hex[:8]
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    domain = domain_clean(payload.get("domain") or "")
    business = (payload.get("business") or "").strip()
    location = (payload.get("location") or "").strip()
    if not domain:
        return JSONResponse({"error": "domain is required"}, status_code=400)

    audit("detect-assets:request", {"rid": rid, "domain": domain, "business": business})

    # Fast path: if SA MCP isn't configured, this call would just sit. Block.
    claude_path = shutil.which("claude")
    if claude_path:
        sa_configured = await _check_sa_mcp_configured(claude_path)
        if not sa_configured:
            audit("detect-assets:short-circuit", {"rid": rid, "reason": "mcp_not_configured"})
            return JSONResponse(
                {"error": "authentication_required", "detail": "searchatlas_mcp_not_configured"},
                status_code=401,
            )

    prompt = detect_assets_prompt(domain, business, location)
    run = await run_claude_step(prompt, timeout_s=90.0, expect_tools=True)

    audit("detect-assets:run", {
        "rid": rid,
        "tool_calls": [t.get("name") for t in run.tool_calls],
        "rc": run.rc,
        "timeout": run.timeout,
        "result_blob": run.result_blob,
    })

    if run.timeout:
        return JSONResponse({"error": "timeout"}, status_code=504)

    if _has_auth_error(run):
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    if not run.tool_calls:
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)

    forbidden = _contains_forbidden_token(run)
    if forbidden:
        return JSONResponse({"error": "fabricated_data", "token": forbidden}, status_code=502)

    blob = run.result_blob
    if not isinstance(blob, dict):
        return JSONResponse({"error": "no_result_block"}, status_code=502)

    if blob.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    # Normalize shape
    bv = blob.get("bv") or {}
    gbp = blob.get("gbp") or {}
    out = {
        "bv": {
            "found": bool(bv.get("found")),
            "uuid": str(bv.get("uuid") or "").strip(),
            "name": str(bv.get("name") or "").strip(),
        },
        "gbp": {
            "found": bool(gbp.get("found")),
            "location_id": str(gbp.get("location_id") or "").strip(),
            "name": str(gbp.get("name") or "").strip(),
        },
    }
    return out


# ── /api/pull-bv ─────────────────────────────────────────────────────────────


def pull_bv_prompt(bv_uuid: str, hostname: str) -> str:
    return f"""{MCP_NAMESPACE_HINT}You are a non-interactive SearchAtlas Brand Vault pull. Do not narrate.

Brand Vault UUID: {bv_uuid}
Hostname: {hostname}

Fire all FOUR tools in parallel (single tool batch):

  1. mcp__searchatlas__bv_get_details             input: {{ "uuid": "{bv_uuid}" }}
  2. mcp__searchatlas__bv_get_business_info       input: {{ "uuid": "{bv_uuid}" }}
  3. mcp__searchatlas__bv_list_voice_profiles     input: {{ "hostname": "{hostname}" }}
  4. mcp__searchatlas__bv_get_knowledge_graph     input: {{ "uuid": "{bv_uuid}" }}

Then emit exactly one result block with the real values returned:

<<<RESULT>>>
{{
  "details":         <tool 1 raw response, JSON object or null on error>,
  "business_info":   <tool 2 raw response, JSON object or null on error>,
  "voice_profiles":  <tool 3 raw response, JSON array  or [] on error>,
  "knowledge_graph": <tool 4 raw response, JSON object or null on error>
}}
<<<END>>>

Rules:
- If any call returns an authentication error, emit `<<<RESULT>>>{{"error":"authentication_required"}}<<<END>>>` and stop.
- Do not invent values. Pass through exactly what each MCP tool returned.
"""


@app.post("/api/pull-bv")
async def pull_bv(request: Request):
    rid = uuid.uuid4().hex[:8]
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    bv_uuid = (payload.get("brand_vault_uuid") or "").strip()
    hostname = domain_clean(payload.get("hostname") or "")
    if not bv_uuid:
        return JSONResponse({"error": "brand_vault_uuid is required"}, status_code=400)

    audit("pull-bv:request", {"rid": rid, "bv_uuid": bv_uuid, "hostname": hostname})

    claude_path = shutil.which("claude")
    if claude_path:
        sa_configured = await _check_sa_mcp_configured(claude_path)
        if not sa_configured:
            audit("pull-bv:short-circuit", {"rid": rid, "reason": "mcp_not_configured"})
            return JSONResponse(
                {"error": "authentication_required", "detail": "searchatlas_mcp_not_configured"},
                status_code=401,
            )

    prompt = pull_bv_prompt(bv_uuid, hostname)
    run = await run_claude_step(prompt, timeout_s=90.0, expect_tools=True)

    audit("pull-bv:run", {
        "rid": rid,
        "tool_calls": [t.get("name") for t in run.tool_calls],
        "rc": run.rc,
        "timeout": run.timeout,
        "result_blob_keys": list((run.result_blob or {}).keys()) if isinstance(run.result_blob, dict) else None,
    })

    if run.timeout:
        return JSONResponse({"error": "timeout"}, status_code=504)
    if _has_auth_error(run):
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    if not run.tool_calls:
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)
    forbidden = _contains_forbidden_token(run)
    if forbidden:
        return JSONResponse({"error": "fabricated_data", "token": forbidden}, status_code=502)

    blob = run.result_blob
    if not isinstance(blob, dict):
        return JSONResponse({"error": "no_result_block"}, status_code=502)
    if blob.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    return blob


# ── /api/create-bv ───────────────────────────────────────────────────────────


def create_bv_prompt(payload: dict) -> str:
    payload_json = json.dumps(payload, indent=2)
    return f"""{MCP_NAMESPACE_HINT}You are a non-interactive SearchAtlas Brand Vault writer. Do not narrate.

Operator-confirmed fields:
```json
{payload_json}
```

Perform these tool calls in order (each call must wait on the prior's response):

  1. mcp__searchatlas__bv_create
       input: {{ "domain": "<from payload.domain>", "name": "<from payload.business_name>" }}
       → capture the returned brand_vault_uuid.

  2. mcp__searchatlas__bv_update_business_info
       input: {{ "uuid": "<uuid from step 1>", "business_name": ..., "industry": ..., "phone": ..., "address": ..., "hours": ..., "service_areas": ... }}
       (populate from payload — omit empty fields, do not invent).

  3. mcp__searchatlas__bv_update
       input: {{ "uuid": "<uuid>", "primary_color": ..., "secondary_color": ..., "voice_tone": ..., "voice_style": ..., "voice_avoid": ... }}
       (only set fields that are present in the payload).

  4. mcp__searchatlas__bv_update_knowledge_graph
       input: {{ "uuid": "<uuid>", "entities": [...], "competitors": [...] }}
       (only set fields that are present in the payload).

Then emit exactly one result block:

<<<RESULT>>>
{{
  "success": true,
  "uuid": "<real uuid from bv_create>",
  "steps_completed": ["bv_create", "bv_update_business_info", "bv_update", "bv_update_knowledge_graph"],
  "errors": []
}}
<<<END>>>

Rules:
- If bv_create fails or returns no uuid, emit `<<<RESULT>>>{{"success": false, "error": "<message>"}}<<<END>>>` and stop.
- If any later step fails, include the failure in `errors` and still report success: true if bv_create succeeded.
- If an auth error is returned by any call, emit `<<<RESULT>>>{{"error":"authentication_required"}}<<<END>>>` and stop.
- Do not invent the UUID. Use only what bv_create returned.
"""


@app.post("/api/create-bv")
async def create_bv(request: Request):
    rid = uuid.uuid4().hex[:8]
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    if not (payload.get("domain") or "").strip():
        return JSONResponse({"error": "domain is required"}, status_code=400)
    if not (payload.get("business_name") or "").strip():
        return JSONResponse({"error": "business_name is required"}, status_code=400)

    audit("create-bv:request", {"rid": rid, "payload": payload})

    claude_path = shutil.which("claude")
    if claude_path:
        sa_configured = await _check_sa_mcp_configured(claude_path)
        if not sa_configured:
            audit("create-bv:short-circuit", {"rid": rid, "reason": "mcp_not_configured"})
            return JSONResponse(
                {"error": "authentication_required", "detail": "searchatlas_mcp_not_configured"},
                status_code=401,
            )

    prompt = create_bv_prompt(payload)
    run = await run_claude_step(prompt, timeout_s=120.0, expect_tools=True)

    audit("create-bv:run", {
        "rid": rid,
        "tool_calls": [t.get("name") for t in run.tool_calls],
        "rc": run.rc,
        "timeout": run.timeout,
        "result_blob": run.result_blob,
    })

    if run.timeout:
        return JSONResponse({"error": "timeout"}, status_code=504)
    if _has_auth_error(run):
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    if not run.tool_calls:
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)
    forbidden = _contains_forbidden_token(run)
    if forbidden:
        return JSONResponse({"error": "fabricated_data", "token": forbidden}, status_code=502)

    blob = run.result_blob
    if not isinstance(blob, dict):
        return JSONResponse({"error": "no_result_block"}, status_code=502)
    if blob.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    if not blob.get("success"):
        return JSONResponse(
            {"error": blob.get("error") or "create_failed", "detail": blob},
            status_code=502,
        )

    if not blob.get("uuid"):
        return JSONResponse({"error": "no_uuid_returned"}, status_code=502)
    return blob


# ── /api/research-market (SSE) ───────────────────────────────────────────────


def research_market_prompt(payload: dict) -> str:
    payload_json = json.dumps(payload, indent=2)
    return f"""{MCP_NAMESPACE_HINT}You are a non-interactive SearchAtlas market-research runner. Do not pause for input.

Operator inputs:
```json
{payload_json}
```

Run TWO parallel waves of SA MCP tools, then synthesize a proposed sitemap.

### Wave 1 (fire all five tools in a SINGLE tool batch)

For each target keyword in `payload.target_keywords` (or, if empty, infer 3 seed keywords from services × location × industry):

  - mcp__searchatlas__se_lookup_keyword       → volume + intent + difficulty
  - mcp__searchatlas__se_get_serp_overview    → who ranks today
  - mcp__searchatlas__se_get_serp_features    → which SERP features

Also fire ONCE in the same batch:

  - mcp__searchatlas__gbp_list_categories            → category taxonomy
  - mcp__searchatlas__se_get_organic_competitors per keyword → discovered competitors

Merge auto-discovered competitors with `payload.known_competitors`, cap at 5.

### Wave 2 (fire all four tools in a SINGLE tool batch, after Wave 1 returns)

  - mcp__searchatlas__se_get_indexed_pages per competitor → real page structures
  - mcp__searchatlas__se_analyze_keyword_gap between competitors → unclaimed territory
  - mcp__searchatlas__cg_create_topical_map seeded with the Wave 1 keyword data
  - mcp__searchatlas__cg_topic_suggestions (no BV uuid required — use `domain` if needed)

### Synthesis

Combine: competitor_pages ∪ gap_clusters ∪ topical_map ∪ topic_suggestions ∪ operator services ∪ location.

Produce a sitemap of 8–14 pages spread across these tiers:
- `core`        — homepage, about, contact, services overview (always include all four)
- `service`     — one per item in payload.services, capped at 8
- `location`    — only if payload.location is set; one geo-targeted page
- `landing`     — 1–2 gap-driven landing pages from se_analyze_keyword_gap
- `compliance`  — privacy policy, terms of service (always include both)

Each page object MUST have these fields. Use real values from the tool responses — never invent numbers:
```
{{
  "slug": "/services/dental-implants",
  "title": "Dental Implants",
  "tier": "service",
  "pageType": "Service detail",
  "h1": "Dental Implants",
  "schema": "Service",
  "oneline": "<one-sentence rationale grounded in evidence>",
  "keywords": [{{ "kw": "...", "vol": <int or null>, "intent": "...", "difficulty": <int or null> }}, ...],
  "competitorEvidence": {{ "count": <int>, "examples": ["...", "..."] }},
  "serpFeatures": ["Local Pack", "People Also Ask"],
  "contentGap": "<grounded sentence from se_analyze_keyword_gap or empty>",
  "sections": ["Hero", "What to expect", "Pricing", "FAQ", "CTA"],
  "ctas": ["Book a visit", "Call now"],
  "evidence": {{
    "kw_total_volume": <int sum or null>,
    "intent": "...",
    "competitor_count": <int>,
    "serp_features": ["..."],
    "gap_score": <number or null>,
    "source": "<tool name that produced this>"
  }}
}}
```

If a field is unknown from the tool responses, use `null` or an empty string — NEVER invent volumes, competitor URLs, or KD values.

Finally emit exactly one result block:

<<<RESULT>>>
{{
  "proposedPages": [ <page object>, ... ],
  "competitorSet": ["competitor1.com", "competitor2.com", ...],
  "keywordEvidence": [
    {{ "kw": "...", "vol": <int or null>, "intent": "...", "difficulty": <int or null>, "source": "se_lookup_keyword" }}
  ],
  "waves": {{
    "wave1": ["se_lookup_keyword", "se_get_serp_overview", "gbp_list_categories", "se_get_organic_competitors", "se_get_serp_features"],
    "wave2": ["se_get_indexed_pages", "se_analyze_keyword_gap", "cg_create_topical_map", "cg_topic_suggestions"]
  }}
}}
<<<END>>>

Rules:
- If any tool returns an auth error, emit `<<<RESULT>>>{{"error":"authentication_required"}}<<<END>>>` and stop.
- Do NOT invent UUIDs. Do NOT invent traffic volumes. Do NOT invent competitor URLs.
- Do NOT use the phrase "would normally" or "simulated" — fail loudly instead.
- After the RESULT block, stop.
"""


async def _sse_event(obj: dict) -> bytes:
    return f"data: {json.dumps(obj, default=str)}\n\n".encode()


async def research_market_stream(payload: dict) -> AsyncIterator[bytes]:
    rid = uuid.uuid4().hex[:8]
    audit("research-market:request", {"rid": rid, "payload": payload})

    yield await _sse_event({"type": "phase", "label": "Market research"})
    yield await _sse_event({"type": "note", "label": "Spawning Claude with SearchAtlas MCP"})

    claude_path = shutil.which("claude")
    if not claude_path:
        yield await _sse_event({"type": "error", "message": "claude CLI not found on PATH"})
        return

    sa_configured = await _check_sa_mcp_configured(claude_path)
    if not sa_configured:
        audit("research-market:short-circuit", {"rid": rid, "reason": "mcp_not_configured"})
        yield await _sse_event({"type": "error", "message": "authentication_required"})
        return

    prompt = research_market_prompt(payload)
    cmd = [
        claude_path, "-p",
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
    except Exception as exc:
        yield await _sse_event({"type": "error", "message": f"spawn_failed: {exc}"})
        return

    _active_jobs.add(proc.pid)
    global _active_streams
    _active_streams += 1
    _bump_heartbeat()

    assert proc.stdout is not None

    text_chunks: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    auth_err = False
    started = time.monotonic()
    TIMEOUT_S = 180.0

    try:
        while True:
            try:
                line_bytes = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=max(1.0, TIMEOUT_S - (time.monotonic() - started)),
                )
            except asyncio.TimeoutError:
                yield await _sse_event({"type": "error", "message": "timeout"})
                try:
                    proc.kill()
                except Exception:
                    pass
                return
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            mtype = data.get("type")
            if mtype == "assistant":
                msg = data.get("message", {}) or {}
                for block in msg.get("content", []) or []:
                    btype = block.get("type")
                    if btype == "text":
                        text_chunks.append(block.get("text") or "")
                    elif btype == "tool_use":
                        tname = block.get("name", "")
                        tinput = block.get("input") or {}
                        tool_calls.append({"name": tname, "input": tinput})
                        label = friendly_label(tname, tinput) or short_tool_name(tname)
                        yield await _sse_event({"type": "work", "label": label})
            elif mtype == "user":
                msg = data.get("message", {}) or {}
                for block in msg.get("content", []) or []:
                    if block.get("type") == "tool_result":
                        content = block.get("content", "")
                        if isinstance(content, list):
                            ctext = " ".join(
                                c.get("text", "") for c in content
                                if isinstance(c, dict)
                            )
                        else:
                            ctext = str(content)
                        is_err = bool(block.get("is_error"))
                        tool_results.append({"is_error": is_err, "content_text": ctext})
                        if is_err and AUTH_ERROR_RE.search(ctext):
                            auth_err = True
                        yield await _sse_event({
                            "type": "done" if not is_err else "error",
                            "label": "Step complete" if not is_err else (ctext[:200] if ctext else "Tool error"),
                        })
            elif mtype == "result":
                pass

        rc = await proc.wait()
    except Exception as exc:
        yield await _sse_event({"type": "error", "message": f"stream_error: {exc}"})
        return
    finally:
        _active_jobs.discard(proc.pid)
        _active_streams -= 1

    audit("research-market:summary", {
        "rid": rid,
        "tool_calls": [t.get("name") for t in tool_calls],
        "rc": rc,
        "auth_err": auth_err,
    })

    if auth_err:
        yield await _sse_event({"type": "error", "message": "authentication_required"})
        return

    full_text = "\n".join(text_chunks)
    low = full_text.lower()
    for tok in FORBIDDEN_TOKENS:
        if tok in low:
            yield await _sse_event({"type": "error", "message": f"fabricated_data:{tok}"})
            return

    if not tool_calls:
        yield await _sse_event({"type": "error", "message": "no_tool_calls_made"})
        return

    m = RESULT_BLOCK_RE.search(full_text)
    if not m:
        yield await _sse_event({"type": "error", "message": "no_result_block"})
        return

    blob_text = m.group(1).strip()
    blob_text = re.sub(r"^```(?:json)?\s*", "", blob_text)
    blob_text = re.sub(r"\s*```$", "", blob_text)
    try:
        blob = json.loads(blob_text)
    except json.JSONDecodeError as exc:
        yield await _sse_event({"type": "error", "message": f"bad_result_json: {exc}"})
        return

    if isinstance(blob, dict) and blob.get("error") == "authentication_required":
        yield await _sse_event({"type": "error", "message": "authentication_required"})
        return

    pages = (blob.get("proposedPages") or []) if isinstance(blob, dict) else []
    if not isinstance(pages, list) or not pages:
        yield await _sse_event({"type": "error", "message": "no_pages_proposed"})
        return

    audit("research-market:result", {"rid": rid, "page_count": len(pages)})

    yield await _sse_event({
        "type": "result",
        "data": {
            "proposedPages": pages,
            "competitorSet": blob.get("competitorSet") or [],
            "keywordEvidence": blob.get("keywordEvidence") or [],
            "waves": blob.get("waves") or {},
        },
    })
    yield await _sse_event({"type": "complete"})


@app.post("/api/research-market")
async def research_market(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    if not (payload.get("domain") or "").strip():
        return JSONResponse({"error": "domain is required"}, status_code=400)
    return StreamingResponse(
        research_market_stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── /api/build (original end-to-end build) ───────────────────────────────────


def _bullet_list(items, prefix: str = "- ") -> list[str]:
    return [f"{prefix}{item}" for item in items if item]


def build_prompt(payload: dict) -> str:
    domain = domain_clean(payload.get("domain") or "")
    slug = domain_to_slug(domain)
    business = (payload.get("business") or "").strip()
    location = (payload.get("location") or "").strip()
    services = payload.get("services") or []
    tier = (payload.get("tier") or "").strip()
    materials = payload.get("materials") or []
    target_market = payload.get("targetMarket") or {}
    sitemap = payload.get("sitemap") or {}
    proposed_pages = sitemap.get("proposedPages") or []
    page_decisions = payload.get("pageDecisions") or {}
    archetype = (payload.get("archetype") or "").strip()
    asset_decisions = payload.get("assetDecisions") or {}
    bv_prefill = payload.get("bvPrefill") or None
    bv_fields = payload.get("bvFields") or None
    detect = payload.get("detect") or {}

    industry_t1 = (target_market.get("industryTier1") or "").strip()
    industry_t2 = (target_market.get("industryTier2") or "").strip()
    target_keywords = target_market.get("targetKeywords") or []
    known_competitors = target_market.get("knownCompetitors") or []

    L: list[str] = []
    L.append(MCP_NAMESPACE_HINT.rstrip())
    L.append("")
    L.append("# /build-website · automated run from Website Build Wizard")
    L.append("")
    L.append("Run the `/build-website` slash command end-to-end with the data below.")
    L.append("**Skip the path picker, skip Phase 0 (domain identification) — domain provided.**")
    L.append("**Do NOT ask any interactive questions.** All required data is provided here.")
    L.append(f"Use slug `{slug}` for the local project folder.")
    L.append("")
    L.append("**CRITICAL — FAIL HARD ON AUTHENTICATION ERRORS.**")
    L.append("Before doing anything else, call `mcp__searchatlas__cg_list_brand_vaults` with empty params `{}` as an authentication probe.")
    L.append("")
    L.append("If that probe (or ANY subsequent `mcp__searchatlas__*` call) returns an authentication / OAuth / `not authenticated` / `unauthorized` / `401` / `connector not authenticated` error:")
    L.append("")
    L.append("1. IMMEDIATELY emit exactly this on its own line: `## Phase ERROR — AUTHENTICATION REQUIRED`")
    L.append("2. Then emit one paragraph: `Search Atlas MCP is not authenticated in this Claude Code session. Open Claude.ai, run /mcp, and complete the OAuth flow for the SearchAtlas connector. Then re-run this build.`")
    L.append("3. EXIT immediately. Do NOT continue with subsequent phases.")
    L.append("")
    L.append("**HARD RULES — NEVER violate:**")
    L.append("- NEVER fabricate UUIDs, project IDs, Website Studio URLs, or any data that should come from a real MCP call. If you don't have it from a successful tool response, omit the line.")
    L.append("- NEVER say `Build complete`, `Site is live`, `Published to Website Studio`, or equivalent unless `mcp__searchatlas__ws_publish_project` actually returned a URL in this run.")
    L.append("- NEVER `proceed with local artifacts` as a fallback for failed MCP calls. The user does NOT want a fake run.")
    L.append("- If the auth probe succeeds, proceed normally with the phases below using real MCP calls only.")
    L.append("")
    L.append("Output formatting rules — important for the UI:")
    L.append("- Begin every phase with: `## Phase N — name` (use the friendly names listed below)")
    L.append("- Keep narration tight: short sentences, plain English")
    L.append("- Don't print raw tool names; the UI auto-friendlies them")
    L.append("- After major milestones, drop a short fact line (e.g. `Brand vault created — uuid d3a…`)")
    L.append("- Don't print individual file paths. The UI will summarize them.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 1 ──
    L.append("## Phase 1 — Identify target")
    L.append("")
    L.append(f"- Domain: `{domain}`")
    if business:
        L.append(f"- Business: **{business}**" + (f", {location}" if location else ""))
    if services:
        L.append(f"- Services: {', '.join(services)}")
    L.append(f"- Local slug: `{slug}`")
    L.append("")
    L.append("Greenfield build. No existing site to crawl beyond the domain itself.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 2 ──
    L.append("## Phase 2 — Quick existence check")
    L.append("")
    L.append("Run these two SA lookups in parallel:")
    L.append("- `cg_list_brand_vaults` — filter by domain. If exists, capture `brand_vault_uuid`.")
    L.append("- `gbp_list_locations` — filter by business name + location. If exists, capture `gbp_location_id`.")
    L.append("")
    L.append("Do not check OTTO, PPC, LLM Visibility — `/run-seo` provisions those after the site is live.")
    if detect:
        bv_status = "found" if (detect.get("bv") or {}).get("found") else "missing"
        gbp_status = "found" if (detect.get("gbp") or {}).get("found") else "missing"
        L.append("")
        L.append(f"Operator-side detection earlier showed: BV={bv_status}, GBP={gbp_status}. Confirm against live SA.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 3 ──
    L.append("## Phase 3 — Operator materials")
    L.append("")
    if materials:
        L.append(f"Operator dropped {len(materials)} materials. Save them under `inputs/` with a `inputs/manifest.json` and use them for BV pre-fill.")
        L.append("")
        for m in materials:
            fmt = m.get("format") or "text"
            label = m.get("label") or "(unlabeled)"
            meta = m.get("meta") or ""
            extracted = m.get("extractedColor")
            line = f"- **{fmt}** · {label}"
            if meta:
                line += f" ({meta})"
            if extracted:
                line += f" · extracted color `{extracted}`"
            L.append(line)
        L.append("")
        L.append("Per format:")
        L.append("- Images → use vision to extract dominant colors, OCR text, visual style. Push primary color to BV.")
        L.append("- Text → parse for voice cues, messaging pillars, words to use/avoid.")
        L.append("- Links → fetch each via WebFetch; extract title, meta description, services, voice cues.")
        L.append("- Video → save and note transcription as a follow-up.")
    else:
        L.append("(No materials dropped — proceed with crawled data + operator inputs only.)")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 4 ──
    L.append("## Phase 4 — Brand vault")
    L.append("")
    L.append("If BV exists from Phase 2, pull all 4 surfaces in parallel: `bv_get_details`, `bv_get_business_info`, `bv_get_knowledge_graph`, `bv_list_voice_profiles`.")
    L.append("")
    L.append("If BV is missing, auto-create and populate from the crawl + operator materials:")
    L.append("- `bv_create` — create empty vault")
    L.append("- `bv_update_business_info` — populate name, industry, location, phone, hours from crawl + materials")
    L.append("- `bv_update` — colors (from logo) + voice (from text materials)")
    L.append("- `bv_update_knowledge_graph` — entities + competitors (operator-provided + auto-discovered)")
    L.append("- `bv_upload_image` — upload any logo dropped by operator")
    L.append("")
    if bv_prefill and bv_prefill.get("fields"):
        L.append("**Operator-side BV pre-fill already done (use these values, save back to the live vault):**")
        for f in bv_prefill["fields"]:
            key = f.get("label") or f.get("key") or ""
            val = f.get("value") or ""
            status = f.get("status") or ""
            src = f.get("source") or ""
            marker = "✅" if status == "ok" else ("🟨" if status == "partial" else "❌")
            L.append(f"- {marker} **{key}**: {val}" + (f" _(source: {src})_" if src else ""))
        L.append("")
    if bv_fields:
        L.append("**Operator-confirmed BV fields (from wizard step 5):**")
        for k, v in bv_fields.items():
            if isinstance(v, list):
                v = ", ".join(map(str, v))
            L.append(f"- {k}: {v}")
        L.append("")
    if asset_decisions:
        L.append("**Operator decisions on existing assets:**")
        for key, decision in asset_decisions.items():
            action = (decision or {}).get("action")
            if not action:
                continue
            L.append(f"- {key}: {action}")
            edits = (decision or {}).get("edits") or {}
            for ek, ev in edits.items():
                if ev:
                    L.append(f"  - edit `{ek}`: {ev}")
        L.append("")
    L.append("After populating, state the brand vault UUID in one short line.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 5 ──
    L.append("## Phase 5 — Budget tier")
    L.append("")
    if tier:
        L.append(f"Budget tier: **{tier}**. Persist to `budget-tier.json`. Used by `/run-seo` later — not by this workflow.")
    else:
        L.append("No tier specified — default to Growth and flag in pre-build review.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 6 ──
    L.append("## Phase 6 — Brand strategy")
    L.append("")
    L.append("Synthesize `brand-strategy.md` from BV fields + operator materials + competitor crawl + logo color cues.")
    L.append("Edits flow back to BV via `bv_update`. Don't print the full content — just confirm the file exists.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 7 ──
    L.append("## Phase 7 — Market-evidence research")
    L.append("")
    L.append("**Note:** the wizard already ran the two-wave research before kicking off the build, and the per-page approvals below are LOCKED. You should still confirm coverage by running:")
    L.append("- `krt_create_project` for the domain")
    L.append("- `krt_bulk_add_keywords` with the validated target KWs (listed in Phase 8 below)")
    L.append("")
    L.append("### Target seeds (from operator)")
    L.append(f"- Industry tier 1: **{industry_t1 or '(not specified — infer from services)'}**")
    L.append(f"- Industry tier 2 (GBP leaf): **{industry_t2 or '(not specified — infer)'}**")
    if target_keywords:
        L.append(f"- Target keywords: {', '.join(target_keywords)}")
    else:
        L.append("- Target keywords: (operator skipped — auto-derive from services × location × industry)")
    if known_competitors:
        L.append(f"- Known competitors: {', '.join(known_competitors)}")
    else:
        L.append("- Known competitors: (none — discover via `se_get_organic_competitors`)")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 8 ──
    L.append("## Phase 8 — Page queue (operator pre-approved)")
    L.append("")
    L.append("**Operator already walked every proposed page in the wizard.** Do NOT re-run the walkthrough.")
    L.append("Below is the locked queue. Write it directly to `page-build-queue.csv`.")
    L.append("")
    approved_pages: list[dict] = []
    rejected_pages: list[dict] = []
    edited_pages: list[tuple[dict, dict]] = []
    for p in proposed_pages:
        slug_p = p.get("slug") or ""
        dec = (page_decisions.get(slug_p) or {}).get("decision") or "(no decision)"
        if dec == "approve":
            approved_pages.append(p)
        elif dec == "edit":
            edited_pages.append((p, (page_decisions.get(slug_p) or {}).get("edits") or {}))
        elif dec == "reject":
            rejected_pages.append(p)
    L.append(f"- Approved: **{len(approved_pages)}**")
    L.append(f"- Edited (approved-with-changes): **{len(edited_pages)}**")
    L.append(f"- Rejected: **{len(rejected_pages)}**")
    L.append("")

    if approved_pages or edited_pages:
        L.append("### Pages to build")
        for p in approved_pages:
            title = p.get("title") or p.get("slug") or ""
            slug_p = p.get("slug") or ""
            tier_p = p.get("tier") or ""
            kws = p.get("keywords") or []
            kw_str = ", ".join(k.get("kw", "") for k in kws if isinstance(k, dict))[:200]
            schema = p.get("schema") or "WebPage"
            L.append(f"- `{slug_p}` · **{title}** · _{tier_p}_ · schema `{schema}`" + (f" · kw: {kw_str}" if kw_str else ""))
        for p, edits in edited_pages:
            title = edits.get("title") or p.get("title") or p.get("slug") or ""
            slug_p = p.get("slug") or ""
            tier_p = p.get("tier") or ""
            schema = p.get("schema") or "WebPage"
            L.append(f"- `{slug_p}` · **{title}** · _{tier_p}_ · schema `{schema}` · _operator-edited_")
            if edits.get("keywords"):
                L.append(f"  - keywords: {edits['keywords'][:200]}")
            if edits.get("sections"):
                sec = edits["sections"].replace("\n", " · ")[:200]
                L.append(f"  - sections: {sec}")
        L.append("")

    if rejected_pages:
        L.append("### Pages to drop (do NOT build)")
        for p in rejected_pages:
            L.append(f"- `{p.get('slug')}` — {p.get('title')}")
        L.append("")
    L.append("---")
    L.append("")

    # ── Phase 9 ──
    L.append("## Phase 9 — Design style")
    L.append("")
    if archetype:
        L.append(f"Operator chose: **{archetype}**.")
    else:
        L.append("No archetype chosen — default to `modern_minimal`.")
    L.append("")
    L.append("Push to BV + WS:")
    L.append("- `bv_update` with `design_style` + derived color tokens")
    L.append("- `ws_create_project` will use this style as the rendering template")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 10 ──
    L.append("## Phase 10 — Content + copy")
    L.append("")
    L.append("For each row in `page-build-queue.csv`, generate copy in parallel batches:")
    L.append("- `cg_dkn_generate_article` (page + brand voice + KW targets) → copy block")
    L.append("- `cg_run_content_grader` → score against KW + readability")
    L.append("- Save to `copy/[slug].md`")
    L.append("")
    L.append("Also produce `image-list.md` — which images each page needs.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 11 ──
    L.append("## Phase 11 — Build + push to Website Studio")
    L.append("")
    L.append("BV completeness check first: `bv_get_business_info`, `bv_list_voice_profiles`, `bv_get_knowledge_graph`, `bv_get_details`. Optional: `kg_validate_completeness`.")
    L.append("")
    L.append("Then scaffold Website Studio:")
    L.append("- `ws_create_project` with `domain`, `business_name`, `brand_vault_uuid`, `design_style`")
    L.append("- `ws_ensure_containers_running` — make sure build infra is ready")
    L.append("")
    L.append("Build loop (per approved page):")
    L.append("1. Load brand-strategy + style guide + `copy/[slug].md`")
    L.append("2. Generate page HTML using the approved components + copy")
    L.append("3. Push to WS via `ws_create_project` (homepage on first iteration) then per-page push for service / location / landing / compliance pages")
    L.append("4. Upload page images via `bv_upload_image` + WS asset references")
    L.append("5. For each service / local / landing page: generate schema via `otto_generate_page_schema` and deploy with `otto_deploy_page_schema`")
    L.append("6. Verify the page renders via `ws_get_project`")
    L.append("")
    L.append("Service / location pages with shared structure can be batched (Claude generates from template loop programmatically).")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 12 ──
    L.append("## Phase 12 — Publish + handoff")
    L.append("")
    L.append("Final pre-publish sweep — all pages render in WS preview.")
    L.append("Then publish:")
    L.append("- `ws_publish_project` (project_id) → returns the WS-hosted URL — use EXACTLY what the tool returns; do NOT guess a URL pattern.")
    L.append("- `otto_activate_instant_indexing` for the domain")
    L.append("- `indexer_submit_batch` with the approved page URLs → push to Google")
    L.append("- Emit DNS cutover instructions for the operator's custom domain")
    L.append("")
    L.append("End with a completion block — but ONLY if `ws_publish_project` actually returned a URL in this run:")
    L.append("```")
    L.append("Site is live on Website Studio")
    L.append("")
    L.append("Live now:       <URL returned by ws_publish_project — do NOT template it, do NOT guess>")
    L.append(f"Custom domain:  https://{domain} (pending DNS cutover)")
    L.append("")
    L.append("What's next:")
    L.append(f"  /run-seo {domain}   — provisions OTTO, LLM Visibility, GBP, and sizes ongoing cadence")
    L.append("```")
    L.append("**CRITICAL**: NEVER print a URL that wasn't returned by `ws_publish_project`. If that tool was not called or returned no URL, OMIT the completion block entirely — just emit a brief `## Phase ERROR — PUBLISH INCOMPLETE` line with the real reason. NEVER invent `{slug}.ws.searchatlas.com` or any other URL pattern.")
    L.append("")
    L.append("Then write `clients/{slug}/CLAUDE.md` and `clients/{slug}/brand-profile.md` from the templates. Don't print the full contents — just confirm both files exist.")
    L.append("")
    L.append("Begin now.")

    return "\n".join(L)


# ── Stream parser → friendly UI events (used by /api/build) ──────────────────


PHASE_RE = re.compile(r"^##\s+Phase\s+\d+\s*[—\-:]\s*(.+)$", re.IGNORECASE)

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
                    m = PHASE_RE.match(ln)
                    if m:
                        events.append({"type": "phase", "label": m.group(1).strip()})
                        continue
                    if ln in ("---", "***", "===") or ln.startswith("#"):
                        continue
                    if not _state["biz_seen"]:
                        bm = re.search(
                            r"(?:business\s+(?:name|is)\s*[:\-]?\s*|\bfound\s*[:\-]?\s*)\*?\*?([A-Z][A-Za-z0-9&'\.\- ]{2,80}?)\*?\*?(?:\s+in\s+|\s*[\.,]|$)",
                            ln,
                        )
                        if bm:
                            name = bm.group(1).strip().strip(".,")
                            if 3 <= len(name) <= 80:
                                _state["biz_seen"] = True
                                events.append({"type": "biz", "name": name})
                    if len(ln) > 200:
                        ln = ln[:197] + "…"
                    events.append({"type": "note", "label": ln})
            elif btype == "tool_use":
                tool_name = block.get("name", "tool")
                tool_input = block.get("input", {}) or {}
                tool_use_id = block.get("id") or ""
                if tool_name in ("Write", "Edit"):
                    if not _state["workspace_announced"]:
                        _state["workspace_announced"] = True
                        events.append({"type": "work", "label": "Creating your workspace"})
                    # Track for tool_result correlation
                    _state.setdefault("tool_use_index", {})[tool_use_id] = {
                        "name": tool_name, "is_sa": False,
                    }
                    continue
                label = friendly_label(tool_name, tool_input)
                # Detect ws_publish_project (CRIT-1): record the call so we know to
                # look for its return URL in a subsequent tool_result.
                is_publish_call = (
                    "ws_publish_project" in tool_name.lower()
                )
                short = short_tool_name(tool_name)
                is_sa = (
                    tool_name.startswith("mcp__searchatlas__")
                    or tool_name.startswith("mcp__claude_ai_Search_Atlas__")
                    or short in TOOL_LABELS
                )
                _state.setdefault("tool_use_index", {})[tool_use_id] = {
                    "name": tool_name, "is_sa": is_sa, "is_publish": is_publish_call,
                }
                if is_publish_call:
                    _state["publish_call_seen"] = True
                if label:
                    events.append({"type": "work", "label": label})
        return events

    if msg_type == "user":
        message = data.get("message", {})
        for block in message.get("content", []):
            if block.get("type") == "tool_result":
                tool_use_id = block.get("tool_use_id") or ""
                is_error_flag = bool(block.get("is_error", False))
                content = block.get("content", "")
                if isinstance(content, list):
                    text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                else:
                    text = str(content)
                idx = _state.get("tool_use_index", {}).get(tool_use_id, {})
                is_sa = bool(idx.get("is_sa"))
                is_publish = bool(idx.get("is_publish"))

                # Auth-error detection on tool_result (CRIT-1 + B-B guard).
                # We check EITHER an explicit is_error flag OR auth-shaped text
                # — some SA tool responses surface "Not authenticated" / "OAuth
                # required" in the body of a non-error response, and we must
                # still treat that as an auth failure (not a successful call).
                low = (text or "").lower()
                auth_keywords = (
                    "not authenticated", "connector not authenticated",
                    "unauthorized", " 401", "401 ", "authentication required",
                    "oauth required", "please authenticate", "sign in to continue",
                )
                # Only consider auth-keyword-only matches on SA tool results
                # (avoids false positives on Bash output etc. that may contain
                # the word "unauthorized" in unrelated narration).
                auth_hit = any(k in low for k in auth_keywords)
                if (is_error_flag and auth_hit) or (is_sa and auth_hit):
                    events.append({
                        "type": "error",
                        "message": "Search Atlas MCP authentication required. Open claude.ai → /mcp → SearchAtlas → complete OAuth. Then re-run the build.",
                        "auth_required": True,
                    })
                    _state["fatal_error"] = True
                    return events

                # Generic tool_result error.
                if is_error_flag:
                    events.append({
                        "type": "error",
                        "message": (text or "Tool returned an error")[:280],
                    })
                    return events

                # Capture real ws_publish URL if the publish call succeeded
                # (CRIT-1, CRIT-2). The wizard MUST NOT fabricate a URL.
                if is_publish and not is_error_flag:
                    url = _extract_url_from_text(text)
                    if url:
                        _state["publish_url"] = url
                        _state["publish_succeeded"] = True
                        events.append({
                            "type": "ws_published",
                            "url": url,
                            "label": f"Site published · {url}",
                        })
                    else:
                        _state["publish_call_returned_without_url"] = True

                # Only emit "Step complete" for real SA MCP tool results
                # (MED-2). Silent built-ins (Read/TodoWrite/Skill) never get
                # a green checkmark; they were never user-meaningful.
                if is_sa and text:
                    events.append({"type": "done", "label": "Step complete"})
        return events

    if msg_type == "result":
        # CRIT-1: a `result` event from Claude does NOT mean the build succeeded.
        # Only emit `complete` if ws_publish_project actually returned a URL.
        # Otherwise emit `incomplete` so the UI knows not to render the live-site block.
        if _state.get("fatal_error"):
            # Already emitted; nothing more to do.
            return events
        if _state.get("publish_succeeded") and _state.get("publish_url"):
            events.append({"type": "complete"})
        else:
            reason = (
                "ws_publish_project did not return a URL"
                if _state.get("publish_call_returned_without_url")
                else "Build ended before ws_publish_project was called"
            )
            events.append({
                "type": "incomplete",
                "message": reason,
            })
        return events

    return events


_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
# B-C: Only accept URLs whose hostname looks like a real Website Studio
# publish target. We refuse to extract documentation links, error-page
# URLs, or other unrelated URLs that could appear in a tool_result body.
_WS_URL_HOST_RE = re.compile(
    r"https?://[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)*\.(?:searchatlas\.com|ws\.searchatlas\.com)(?:/|$)",
    re.IGNORECASE,
)


def _is_ws_publish_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    return bool(_WS_URL_HOST_RE.match(url))


def _extract_url_from_text(text: str) -> str | None:
    if not text:
        return None
    # Try JSON shape first: {"url": "..."} or {"site_url": "..."} etc.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for k in ("url", "site_url", "live_url", "preview_url", "publish_url", "published_url"):
                v = obj.get(k)
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    # Prefer URLs that look like a WS-hosted target. If the
                    # explicit key gave us a URL with the right host, return it.
                    if _is_ws_publish_url(v):
                        return v
    except (json.JSONDecodeError, ValueError):
        pass
    # Fall back: first http(s) URL that matches the WS-host shape. We refuse
    # to accept arbitrary URLs (e.g. docs, error links) as a publish result.
    for m in _URL_RE.finditer(text):
        candidate = m.group(0).rstrip(".,);]")
        if _is_ws_publish_url(candidate):
            return candidate
    return None


async def _build_runner(prompt: str, queue: asyncio.Queue) -> None:
    """Spawn the long-running website-build Claude session as a detached task.
    Survives client disconnect — the user can close the wizard tab and Claude
    will still run to completion. PID is tracked in _active_jobs so the idle
    watcher never kills the bridge while a build is in flight."""

    async def put(evt: dict) -> None:
        try:
            queue.put_nowait(evt)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(evt)
            except Exception:
                pass

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
        await put({"type": "error", "message": "claude CLI not found on PATH"})
        await put({"__sentinel__": True})
        return
    except Exception as exc:
        await put({"type": "error", "message": f"Failed to spawn Claude: {exc}"})
        await put({"__sentinel__": True})
        return

    _active_jobs.add(proc.pid)
    try:
        assert proc.stdout is not None
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            _bump_heartbeat()
            line = line_bytes.decode("utf-8", errors="replace")
            for evt in parse_claude_event(line):
                await put(evt)

        rc = await proc.wait()
        if rc != 0:
            stderr_b = (await proc.stderr.read()) if proc.stderr else b""
            stderr = stderr_b.decode("utf-8", errors="replace")
            await put({"type": "error", "message": f"Claude exited {rc}. {stderr[:300]}"})
        # On rc == 0 the parse_claude_event `result` branch already emitted
        # either `complete` or `incomplete`.
    finally:
        _active_jobs.discard(proc.pid)
        await put({"__sentinel__": True})


async def stream_claude(prompt: str) -> AsyncIterator[bytes]:
    global _active_streams
    reset_run_state()
    _bump_heartbeat()

    async def emit(obj: dict) -> bytes:
        return f"data: {json.dumps(obj)}\n\n".encode()

    yield await emit({"type": "phase", "label": "Setup"})
    yield await emit({"type": "note", "label": f"Working from {TOOLKIT_ROOT.name}"})

    queue: asyncio.Queue = asyncio.Queue(maxsize=512)
    runner = asyncio.create_task(_build_runner(prompt, queue))
    _active_streams += 1
    try:
        while True:
            evt = await queue.get()
            if isinstance(evt, dict) and evt.get("__sentinel__"):
                break
            yield await emit(evt)
    finally:
        _active_streams -= 1
        # Intentionally do NOT cancel runner — let the build run to completion
        # even if the browser tab closed. PID stays in _active_jobs so the
        # idle watcher protects the bridge until Claude finishes.
        del runner


@app.post("/api/build")
async def build(request: Request):
    payload = await request.json()
    if not domain_clean(payload.get("domain") or ""):
        return JSONResponse({"error": "domain is required"}, status_code=400)

    # CRIT-1 guard: refuse to spawn the build if SA MCP isn't configured.
    # Returning 401 instead of streaming fake-success events.
    claude_path = shutil.which("claude")
    if not claude_path:
        return JSONResponse(
            {"error": "claude_cli_not_found"},
            status_code=503,
        )
    sa_ok = await _check_sa_mcp_configured(claude_path)
    if not sa_ok:
        return JSONResponse(
            {
                "error": "authentication_required",
                "detail": "searchatlas_mcp_not_configured",
                "message": "Open claude.ai → /mcp → SearchAtlas → complete OAuth, then re-run the build.",
            },
            status_code=401,
        )

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


@app.post("/api/shutdown")
async def shutdown(request: Request):
    """Manual stop — only called by the explicit 'Stop Mission Control' button.
    Tab close does NOT trigger this anymore (see welcome.html). Idle-shutdown
    handles unattended cleanup after IDLE_TIMEOUT_S of no signal."""

    async def _exit_soon():
        await asyncio.sleep(0.2)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_exit_soon())
    return {"ok": True, "message": "shutting down"}


# ── Entrypoint ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8766))
    print(f"\n  Website Build Wizard")
    print(f"  → http://localhost:{port}\n")
    print(f"  Toolkit root: {TOOLKIT_ROOT}")
    print(f"  Claude CLI:   {shutil.which('claude') or '(not found)'}")
    print(f"  Audit log:    {AUDIT_LOG}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
