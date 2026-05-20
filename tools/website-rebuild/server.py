"""
Website Rebuild Wizard — local server that bridges the web UI to Claude Code
backed by REAL Search Atlas MCP calls.

This server has TWO modes:

1. The full /api/rebuild SSE stream that fires `/rebuild-website` end-to-end.
2. Per-step bridges (auth-probe, parse-scout, asset-inheritance, link-
   preservation, new-page-evidence, pre-launch-baseline) that the wizard
   calls as the operator walks through Steps 1-10. Each bridge spawns
   `claude -p` with a tightly-scoped prompt that MUST execute specific
   Search Atlas MCP tools, captures the tool_use + tool_result events
   coming back over stream-json, parses the real responses, and returns
   structured JSON to the frontend.

HARD GUARDRAILS shared across every bridge:
- If the Claude session never emits ANY `mcp__searchatlas__*` tool_use,
  the bridge returns 502 `{"error": "no_tool_calls_made"}`.
- If ANY tool_result text contains an auth/OAuth/401 signal, the bridge
  returns 401 `{"error": "authentication_required"}`.
- All requests + responses (sans payloads) are appended to
  `/tmp/amm-website-rebuild-audit.log` with an ISO timestamp.
- Timeouts: 60s "fast" probes, 180s "heavy" research probes. Past the
  budget → 504.
- NEVER synthesizes data. Missing > fake. Frontend renders "—".
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


HERE = Path(__file__).resolve().parent
AUDIT_LOG = Path("/tmp/amm-website-rebuild-audit.log")


def find_toolkit_root(start: Path) -> Path:
    cur = start
    for _ in range(6):
        if (cur / "commands" / "rebuild-website.md").exists():
            return cur
        cur = cur.parent
    return start.parent


TOOLKIT_ROOT = find_toolkit_root(HERE)


# ── Friendly process labels ──────────────────────────────────────────────────
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
    "cg_list_brand_vaults": "Looking up brand vaults",
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
    "gbp_list_categories":          "Listing GBP categories",
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
    "se_get_referring_domains":     "Mapping referring domains to protect",
    "se_get_serp_overview":         "Reading SERP overview",
    "se_create_keyword_research":   "Setting up keyword research",
    "se_create_project":            "Creating the Site Explorer project",
    "se_lookup_keyword":            "Looking up keyword",
    "se_get_anchor_text":           "Reading anchor text for high-Authority pages",
    "se_get_link_network_graph":    "Mapping internal link network",
    "se_get_indexed_pages":         "Mirroring competitor page structures",
    "se_analyze_keyword_gap":       "Analyzing keyword gaps",
    "se_get_serp_features":         "Reading SERP features",
    "krt_create_project":           "Setting up keyword tracking",
    "krt_add_keywords":             "Adding target keywords",
    "krt_bulk_add_keywords":        "Adding target keywords",
    "krt_refresh_rankings":         "Pulling current rankings",
    "krt_get_rankings":             "Capturing pre-launch rank snapshot",
    "krt_list_projects":            "Listing keyword tracking projects",
    "cg_create_topical_map":        "Building topical map",
    "cg_search_topical_maps":       "Looking up topical maps",
    "cg_topic_suggestions":         "Generating topic ideas",
    "cg_generate_complete_article": "Generating page copy",
    "cg_dkn_generate_article":      "Generating article from knowledge graph",
    "cg_create_brand_vault":        "Creating brand vault",
    "cg_get_brand_vault_details":   "Loading brand vault",
    "cg_run_content_grader":        "Grading content quality",
    "otto_list_projects":           "Checking for an existing OTTO project",
    "otto_find_project_by_hostname":"Finding existing OTTO project",
    "otto_get_project_details":     "Loading OTTO project",
    "otto_create_audit":            "Creating the SEO audit",
    "otto_get_site_audit":          "Reading the SEO audit",
    "otto_engage_project":          "Engaging OTTO automation",
    "otto_get_project_issues_summary": "Reading site issues",
    "otto_get_issues_by_type":      "Loading OTTO issue clusters",
    "otto_generate_bulk_recommendations": "Generating SEO recommendations",
    "otto_activate_instant_indexing":  "Activating instant indexing",
    "otto_select_urls_for_indexing":   "Selecting URLs for indexing",
    "otto_generate_page_schema":    "Generating schema markup",
    "otto_deploy_page_schema":      "Deploying schema",
    "otto_show_quota":              "Checking your quota",
    "otto_get_quota":               "Checking your quota",
    "otto_update_knowledge_graph":  "Updating knowledge graph",
    "indexer_submit_batch":         "Submitting URLs to Google",
    "gsc_get_keyword_performance":  "Pulling GSC keyword baseline",
    "gsc_get_page_performance":     "Pulling GSC page baseline",
    "gsc_get_sites":                "Listing Search Console sites",
    "ws_create_project":            "Scaffolding Website Studio project",
    "ws_publish_project":           "Publishing to Website Studio",
    "ppc_create_business":          "Setting up PPC business",
    "ppc_list_businesses":          "Looking up PPC business",
    "ppc_discover_products":        "Discovering products to advertise",
    "ppc_bulk_create_keyword_clusters": "Building keyword clusters",
    "ppc_bulk_create_ad_contents":  "Generating ad copy",
    "ppc_get_business":             "Loading PPC business",
    "pr_create":                    "Drafting press release",
    "pr_publish":                   "Publishing press release",
    "dpr_create_campaign":          "Setting up digital PR campaign",
    "dpr_list_opportunities":       "Finding outreach opportunities",
    "llmv_create_project":          "Setting up LLM visibility tracking",
    "llmv_submit_prompts":          "Querying LLMs",
    "llmv_get_brand_overview":      "Reading brand presence in LLMs",
    "llmv_get_visibility_trend":    "Reading visibility trend",
    "llmv_add_topic":               "Adding tracking topic",
    "llmv_add_query":               "Adding tracking query",
    "llmv_list_projects":           "Listing LLM Visibility projects",
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


# ── Audit log ────────────────────────────────────────────────────────────────


def audit(action: str, payload: dict | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    line = {"ts": ts, "action": action}
    if payload:
        # Keep audit lines compact — only top-level keys + small values
        safe: dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                safe[k] = v if not (isinstance(v, str) and len(v) > 200) else (v[:200] + "…")
            elif isinstance(v, (list, dict)):
                safe[k] = f"<{type(v).__name__}({len(v)})>"
            else:
                safe[k] = f"<{type(v).__name__}>"
        line["payload"] = safe
    try:
        with AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    except Exception:
        pass  # never let audit failure break the request


# ── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(title="Website Rebuild Wizard", version="2.0")
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
        # The local install may expose the SA MCP under any of these names —
        # all should count as "configured".
        ok = (
            ("mcp.searchatlas.com" in text)
            or ("searchatlas" in text)
            or ("search atlas" in text)
            or ("search-atlas" in text)
            or ("search_atlas" in text)
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


# ── Helpers ──────────────────────────────────────────────────────────────────


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


# ── Auth-signal detection ────────────────────────────────────────────────────


AUTH_ERROR_PATTERNS = [
    "not authenticated",
    "not_authenticated",
    "unauthenticated",
    "unauthorized",
    "401",
    "oauth",
    "connector not authenticated",
    "authentication required",
    "authentication_required",
    "please authenticate",
    "invalid_grant",
    "token expired",
    "token_expired",
    "expired token",
    "invalid token",
    "invalid_token",
    "auth failed",
    "auth_failed",
    "permission denied",
    "forbidden",
]


def is_auth_error(text: str) -> bool:
    if not text:
        return False
    low = text.lower()[:1000]
    return any(p in low for p in AUTH_ERROR_PATTERNS)


# ── Claude session runner ────────────────────────────────────────────────────


async def run_claude_session(
    prompt: str,
    *,
    timeout_sec: int = 60,
    allowed_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Spawn `claude -p` with the given prompt, capture stream-json output,
    and return a structured result:

        {
            "rc": int,
            "stderr": str,
            "tool_calls": [ {"name": str, "input": dict, "result_text": str} ],
            "assistant_text": str,
            "auth_error": bool,
            "timed_out": bool,
        }
    """
    claude_path = shutil.which("claude")
    if not claude_path:
        return {
            "rc": -1, "stderr": "claude CLI not found on PATH",
            "tool_calls": [], "assistant_text": "",
            "auth_error": False, "timed_out": False,
        }

    cmd = [claude_path, "-p", "--output-format", "stream-json", "--verbose"]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    cmd.append(prompt)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(TOOLKIT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as exc:
        return {
            "rc": -1, "stderr": f"spawn failed: {exc}",
            "tool_calls": [], "assistant_text": "",
            "auth_error": False, "timed_out": False,
        }

    tool_calls: list[dict] = []
    pending_by_id: dict[str, dict] = {}
    assistant_text_parts: list[str] = []
    auth_error = False
    timed_out = False

    async def _read_stdout():
        nonlocal auth_error
        assert proc.stdout is not None
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg_type = evt.get("type")
            if msg_type == "assistant":
                msg = evt.get("message", {})
                for block in msg.get("content", []) or []:
                    btype = block.get("type")
                    if btype == "text":
                        txt = block.get("text") or ""
                        if txt:
                            assistant_text_parts.append(txt)
                    elif btype == "tool_use":
                        tool_id = block.get("id") or ""
                        rec = {
                            "id": tool_id,
                            "name": block.get("name", ""),
                            "input": block.get("input") or {},
                            "result_text": "",
                            "result_is_error": False,
                        }
                        if tool_id:
                            pending_by_id[tool_id] = rec
                        tool_calls.append(rec)
            elif msg_type == "user":
                msg = evt.get("message", {})
                for block in msg.get("content", []) or []:
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id") or ""
                        content = block.get("content", "")
                        is_error = bool(block.get("is_error"))
                        if isinstance(content, list):
                            text = "\n".join(
                                (c.get("text") or "") for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            )
                        else:
                            text = str(content)
                        rec = pending_by_id.get(tool_use_id)
                        if rec is not None:
                            rec["result_text"] = text
                            rec["result_is_error"] = is_error
                        if is_auth_error(text):
                            auth_error = True

    try:
        await asyncio.wait_for(_read_stdout(), timeout=timeout_sec)
        rc = await asyncio.wait_for(proc.wait(), timeout=10)
    except asyncio.TimeoutError:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        rc = -1

    stderr = ""
    try:
        if proc.stderr is not None:
            stderr_bytes = await asyncio.wait_for(proc.stderr.read(), timeout=2)
            stderr = stderr_bytes.decode("utf-8", errors="replace")
    except Exception:
        pass

    return {
        "rc": rc,
        "stderr": stderr,
        "tool_calls": tool_calls,
        "assistant_text": "".join(assistant_text_parts),
        "auth_error": auth_error,
        "timed_out": timed_out,
    }


def is_sa_tool(name: str) -> bool:
    """Detect any Search Atlas MCP call regardless of which namespace prefix
    the local Claude install uses (`mcp__searchatlas__*`, `mcp__claude_ai_Search_Atlas__*`, etc.)."""
    if not name:
        return False
    low = name.lower()
    return ("searchatlas" in low) or ("search_atlas" in low) or ("search-atlas" in low)


def filter_sa_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Only the tool calls that hit Search Atlas MCP."""
    return [tc for tc in tool_calls if is_sa_tool(tc.get("name", ""))]


# Map a bare SA tool name (e.g. "cg_list_brand_vaults") to the full prefixed
# names the local Claude install might expose. We pass ALL candidates to
# --allowedTools so whichever namespace is connected can actually fire.
SA_NAMESPACE_PREFIXES = [
    "mcp__searchatlas__",
    "mcp__claude_ai_Search_Atlas__",
]


def sa_allowed_variants(tool_short_names: list[str]) -> list[str]:
    out: list[str] = []
    for short in tool_short_names:
        for pref in SA_NAMESPACE_PREFIXES:
            out.append(pref + short)
    return out


def extract_json_from_text(text: str) -> Any | None:
    """Pull the largest JSON object/array out of a chunk of text. Lossy by
    design — many MCP responses are JSON-as-a-string."""
    if not text:
        return None
    text = text.strip()
    # Try direct first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try fenced
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try greedy brace match
    for opener, closer in (("{", "}"), ("[", "]")):
        i = text.find(opener)
        j = text.rfind(closer)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:
                continue
    return None


# ════════════════════════════════════════════════════════════════════════════
# /api/auth-probe — auth gatekeeper
# ════════════════════════════════════════════════════════════════════════════


@app.post("/api/auth-probe")
async def auth_probe(request: Request):
    """Call cg_list_brand_vaults with empty params. If it succeeds (or returns
    a normal "no vaults" payload), authentication is good. Any auth-style
    error → authenticated=false."""
    audit("auth-probe.request")
    prompt = (
        "Call the Search Atlas MCP tool `cg_list_brand_vaults` with empty params `{}` "
        "as an authentication probe. The tool will be exposed under one of these prefixed names — "
        "use whichever variant is available:\n"
        "  - `mcp__searchatlas__cg_list_brand_vaults`\n"
        "  - `mcp__claude_ai_Search_Atlas__cg_list_brand_vaults`\n\n"
        "RULES:\n"
        "- Call cg_list_brand_vaults exactly once via whichever Search Atlas namespace is connected.\n"
        "- Do NOT call WebFetch, Read, Bash, or any other tool.\n"
        "- After the call returns, say nothing else. Stop.\n"
    )
    res = await run_claude_session(
        prompt,
        timeout_sec=120,
        allowed_tools=sa_allowed_variants(["cg_list_brand_vaults"]),
    )

    if res["timed_out"]:
        audit("auth-probe.timeout")
        return JSONResponse({"error": "probe_timeout"}, status_code=504)

    sa_calls = filter_sa_tool_calls(res["tool_calls"])
    if not sa_calls:
        audit("auth-probe.no_tool_calls", {"rc": res["rc"], "stderr_len": len(res["stderr"])})
        return JSONResponse(
            {
                "authenticated": False,
                "error": "no_tool_calls_made",
                "detail": "Auth probe did not invoke the Search Atlas MCP. Open Claude.ai → /mcp and connect the SearchAtlas connector.",
            },
            status_code=502,
        )

    if res["auth_error"]:
        audit("auth-probe.auth_error")
        return JSONResponse(
            {
                "authenticated": False,
                "error": "authentication_required",
                "detail": "Search Atlas MCP returned an authentication error. Open Claude.ai → /mcp and re-authenticate the SearchAtlas connector.",
            },
            status_code=401,
        )

    audit("auth-probe.ok", {"calls": len(sa_calls)})
    return {"authenticated": True, "tool_calls": len(sa_calls)}


# ════════════════════════════════════════════════════════════════════════════
# /api/parse-scout — server-side scout output parser (no MCP needed)
# ════════════════════════════════════════════════════════════════════════════


SCOUT_REQUIRED_MARKERS = [
    # At least one of these must appear to consider this a real scout file.
    "scout_run_date",
    "scout-run-date",
    "Phase 1 — Pre-Scout Verification",
    "Phase 2 — OTTO",
    "Phase 3 — Site Map",
    "Site inventory",
    "OTTO pillar",
    "Content gaps",
    "Top issues",
]


def _looks_like_scout(text: str) -> bool:
    if not text or len(text) < 200:
        return False
    low = text.lower()
    return any(m.lower() in low for m in SCOUT_REQUIRED_MARKERS)


def _extract_scout_run_date(text: str) -> str | None:
    m = re.search(r"scout_run_date\s*:\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?", text, re.I)
    if m: return m.group(1)
    m = re.search(r'<meta\s+name=["\']scout[-_]run[-_]date["\']\s+content=["\']([^"\']+)["\']', text, re.I)
    if m: return m.group(1)
    m = re.search(r'"scout_run_date"\s*:\s*"([^"]+)"', text, re.I)
    if m: return m.group(1)
    return None


def _extract_pages(text: str) -> list[dict]:
    """Pull page inventory from scout output. Supports JSON arrays, markdown
    tables, and plain URL lists."""
    pages: list[dict] = []
    # 1) Try direct JSON page list
    j = extract_json_from_text(text)
    if isinstance(j, dict):
        for key in ("pages", "site_inventory", "siteInventory", "inventory", "urls"):
            arr = j.get(key)
            if isinstance(arr, list):
                for p in arr:
                    if isinstance(p, dict):
                        pages.append(_normalize_page_dict(p))
                if pages:
                    return pages
    if isinstance(j, list):
        for p in j:
            if isinstance(p, dict) and (p.get("url") or p.get("path")):
                pages.append(_normalize_page_dict(p))
        if pages:
            return pages
    # 2) Try markdown table rows: | /path | Title | score | authority | traffic |
    for m in re.finditer(
        r"^\|\s*(/[^\s|]+)\s*\|\s*([^|\n]+?)\s*\|\s*(\d+)?\s*\|\s*(\d+)?\s*\|\s*(\d+)?\s*\|",
        text, re.MULTILINE,
    ):
        url, title, cs, auth, tr = m.groups()
        pages.append({
            "url": url.strip(),
            "title": (title or "").strip(),
            "contentScore": int(cs) if cs else 0,
            "authority": int(auth) if auth else 0,
            "traffic": int(tr) if tr else 0,
            "lastModified": "",
        })
    if pages:
        return pages
    # 3) Plain URL list as a fallback
    seen = set()
    for m in re.finditer(r"(?:^|\s)((?:https?://[^\s)]+)|(/[A-Za-z0-9_\-/]+))", text):
        u = m.group(1).rstrip("),.;:")
        if u.startswith("http"):
            try:
                from urllib.parse import urlparse
                u = urlparse(u).path or "/"
            except Exception:
                continue
        if u and u not in seen and len(u) < 200:
            seen.add(u)
            pages.append({"url": u, "title": "", "contentScore": 0, "authority": 0, "traffic": 0, "lastModified": ""})
        if len(pages) >= 500:
            break
    return pages


def _normalize_page_dict(p: dict) -> dict:
    url = p.get("url") or p.get("path") or "/"
    return {
        "url": str(url),
        "title": str(p.get("title") or p.get("name") or ""),
        "contentScore": int(p.get("contentScore") or p.get("content_score") or 0),
        "authority": int(p.get("authority") or p.get("authority_score") or 0),
        "traffic": int(p.get("traffic") or p.get("monthly_traffic") or 0),
        "lastModified": str(p.get("lastModified") or p.get("last_modified") or ""),
    }


def _extract_otto_pillars(text: str) -> dict:
    pillars = {}
    for label in ("Technical", "Content", "Authority", "UX"):
        m = re.search(rf"{label}[^:\n0-9]*[:\s]+(\d{{1,3}})", text)
        if m:
            try:
                v = int(m.group(1))
                if 0 <= v <= 100:
                    pillars[label.lower()] = v
            except Exception:
                pass
    return pillars


def _extract_keywords(text: str) -> list[dict]:
    out = []
    # Markdown table rows: | keyword | pos | vol |
    for m in re.finditer(
        r"^\|\s*([A-Za-z0-9][^|\n]{1,80}?)\s*\|\s*(\d{1,3})\s*\|\s*(\d+)?",
        text, re.MULTILINE,
    ):
        kw, pos, vol = m.groups()
        kw = kw.strip()
        if not kw or kw.lower() in ("keyword", "kw"):
            continue
        out.append({"keyword": kw, "position": int(pos), "volume": int(vol) if vol else None})
        if len(out) >= 200:
            break
    return out


def _extract_gaps(text: str) -> list[dict]:
    gaps = []
    # Look for an explicit "Content gaps" section
    m = re.search(r"(?:Content gaps|Topic gaps|content_gaps)[^\n]*\n+(.+?)(?:\n##|\n---|\Z)", text, re.DOTALL | re.I)
    if not m:
        return gaps
    block = m.group(1)
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ", "• ")):
            gaps.append({"title": line.lstrip("-*• ").strip()})
        elif re.match(r"^\d+[\.)]\s", line):
            gaps.append({"title": re.sub(r"^\d+[\.)]\s+", "", line).strip()})
        if len(gaps) >= 50:
            break
    return gaps


def _extract_issues(text: str) -> list[str]:
    issues = []
    m = re.search(r"(?:Top issues|top_issues|Issues)[^\n]*\n+(.+?)(?:\n##|\n---|\Z)", text, re.DOTALL | re.I)
    if not m:
        return issues
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ", "• ")):
            issues.append(line.lstrip("-*• ").strip())
        if len(issues) >= 50:
            break
    return issues


def _extract_backlinks(text: str) -> dict:
    out = {}
    m = re.search(r"referring[_ ]domains[^\d]*(\d{1,7})", text, re.I)
    if m:
        out["referring_domains"] = int(m.group(1))
    m = re.search(r"total[_ ]backlinks[^\d]*(\d{1,9})", text, re.I)
    if m:
        out["total_backlinks"] = int(m.group(1))
    return out


@app.post("/api/parse-scout")
async def parse_scout(request: Request):
    """Parse scout output content (or a file path) into structured JSON.
    This endpoint does NOT call MCP — it's pure parsing. Required so the
    wizard can apply real auto-classification heuristics over REAL scout
    inventory rather than synthetic data."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    audit("parse-scout.request", {"hasContent": bool(payload.get("scoutContent")), "hasPath": bool(payload.get("scoutPath"))})

    content = payload.get("scoutContent") or ""
    path = payload.get("scoutPath") or ""

    if path and not content:
        try:
            p = Path(path).expanduser()
            if not p.exists() or not p.is_file():
                audit("parse-scout.bad_path", {"path": path})
                return JSONResponse({"error": "scout_file_not_found", "path": path}, status_code=400)
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            audit("parse-scout.read_error", {"err": str(exc)})
            return JSONResponse({"error": "scout_file_read_error", "detail": str(exc)}, status_code=400)

    if not content or not _looks_like_scout(content):
        audit("parse-scout.invalid")
        return JSONResponse(
            {"error": "invalid_scout", "detail": "Content does not look like a scout output (missing expected sections). Re-run /scout for this domain and drop the produced file."},
            status_code=400,
        )

    parsed = {
        "scoutRunDate": _extract_scout_run_date(content),
        "pages": _extract_pages(content),
        "ottoPillars": _extract_otto_pillars(content),
        "keywords": _extract_keywords(content),
        "contentGaps": _extract_gaps(content),
        "topIssues": _extract_issues(content),
        "backlinks": _extract_backlinks(content),
    }
    audit("parse-scout.ok", {"pages": len(parsed["pages"]), "gaps": len(parsed["contentGaps"]), "kw": len(parsed["keywords"])})
    return parsed


# ════════════════════════════════════════════════════════════════════════════
# /api/asset-inheritance — real per-asset parallel pull
# ════════════════════════════════════════════════════════════════════════════


def _domain_matches(field_val: str, domain: str) -> bool:
    if not isinstance(field_val, str) or not domain:
        return False
    fv = field_val.lower().strip().replace("https://", "").replace("http://", "").rstrip("/")
    fv = fv[4:] if fv.startswith("www.") else fv
    d = domain.lower().strip()
    d = d[4:] if d.startswith("www.") else d
    return fv == d


def _find_asset_by_domain(rjson: Any, domain: str, id_keys: tuple) -> dict | None:
    """Return {"id": <str>, "domain": <str>} only when a parsed JSON object
    contains an item whose own domain/website/hostname field equals `domain`
    AND that item carries a real ID under one of `id_keys`. Returns None
    otherwise. NEVER falls back to substring matching the raw response."""
    if not isinstance(rjson, (dict, list)):
        return None
    # Normalize to a list of candidate items
    items: list = []
    if isinstance(rjson, list):
        items = [x for x in rjson if isinstance(x, dict)]
    else:
        # Try common envelope shapes
        for key in ("results", "items", "data", "vaults", "locations", "businesses", "projects"):
            v = rjson.get(key)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break
        if not items and any(k in rjson for k in id_keys):
            items = [rjson]
    for item in items:
        # Check the per-item domain field
        domain_field = None
        for dk in ("domain", "website", "hostname", "url", "site_url"):
            if dk in item and _domain_matches(item.get(dk) or "", domain):
                domain_field = item.get(dk)
                break
        if not domain_field:
            continue
        # Require a real ID on this object
        for ik in id_keys:
            if item.get(ik):
                return {"id": item[ik], "domain": domain_field}
    return None


def _build_asset_inheritance_prompt(domain: str) -> str:
    return f"""# Asset inheritance probe for `{domain}`

Run these Search Atlas MCP calls IN PARALLEL and return a single JSON object with the merged result. Do not narrate. Do not call any non-SearchAtlas tool.

The Search Atlas MCP is exposed under one of these namespace prefixes — use whichever variant is available in this session:
- `mcp__searchatlas__<tool>`
- `mcp__claude_ai_Search_Atlas__<tool>`

Required calls (fire each exactly once, in parallel):

1. `otto_find_project_by_hostname` with hostname=`{domain}`
2. `cg_list_brand_vaults` with `{{}}` (then filter the response for vaults whose domain matches `{domain}` — case-insensitive, with or without www.)
3. `gbp_list_locations` with `{{}}` (then filter for locations whose website matches `{domain}`)
4. `ppc_list_businesses` with `{{}}` (then filter for businesses whose domain matches `{domain}`)
5. `llmv_list_projects` with `{{}}` (then filter for projects whose domain matches `{domain}`)

If OTTO returns a project, ALSO immediately fire:
6. `otto_get_issues_by_type` for that project_id, in parallel with the rest.

After all responses arrive, emit ONE final assistant message containing ONLY a JSON object with this exact shape (use `null` for missing data, NEVER fabricate IDs or fields):

```json
{{
  "otto":  {{"found": <bool>, "project_id": <str or null>, "project_name": <str or null>, "url": <str or null>, "issue_clusters": <object or null>}},
  "bv":    {{"found": <bool>, "vault_id": <str or null>, "vault_name": <str or null>, "domain": <str or null>}},
  "gbp":   {{"found": <bool>, "location_id": <str or null>, "name": <str or null>, "city": <str or null>}},
  "ppc":   {{"found": <bool>, "business_id": <str or null>, "name": <str or null>}},
  "llmv":  {{"found": <bool>, "project_id": <str or null>, "project_name": <str or null>}}
}}
```

Hard rules:
- If a call returns an authentication / OAuth / 401 / `not authenticated` error, emit ONLY `{{"error":"authentication_required"}}` and stop.
- If a call fails for any other reason, set that asset's `found: false` and leave the IDs `null` — do NOT make up data.
- Never claim found:true unless the actual MCP response contained matching data."""


@app.post("/api/asset-inheritance")
async def asset_inheritance(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    domain = domain_clean(payload.get("domain") or "")
    if not domain:
        return JSONResponse({"error": "domain_required"}, status_code=400)
    audit("asset-inheritance.request", {"domain": domain})

    prompt = _build_asset_inheritance_prompt(domain)
    allowed = sa_allowed_variants([
        "otto_find_project_by_hostname",
        "cg_list_brand_vaults",
        "gbp_list_locations",
        "ppc_list_businesses",
        "llmv_list_projects",
        "otto_get_issues_by_type",
    ])
    res = await run_claude_session(prompt, timeout_sec=240, allowed_tools=allowed)

    if res["timed_out"]:
        audit("asset-inheritance.timeout", {"domain": domain})
        return JSONResponse({"error": "probe_timeout"}, status_code=504)

    if res["auth_error"]:
        audit("asset-inheritance.auth_error", {"domain": domain})
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    sa_calls = filter_sa_tool_calls(res["tool_calls"])
    if not sa_calls:
        audit("asset-inheritance.no_tool_calls", {"domain": domain})
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)

    merged = extract_json_from_text(res["assistant_text"])
    if not isinstance(merged, dict):
        # Try to synthesize from individual tool_call results (still REAL data)
        merged = {"otto": {"found": False}, "bv": {"found": False}, "gbp": {"found": False}, "ppc": {"found": False}, "llmv": {"found": False}}
        for tc in sa_calls:
            name = short_tool_name(tc["name"])
            rtext = tc.get("result_text") or ""
            if not rtext or tc.get("result_is_error"):
                continue
            rjson = extract_json_from_text(rtext)
            if name == "otto_find_project_by_hostname" and isinstance(rjson, dict):
                pid = rjson.get("project_id") or rjson.get("id") or rjson.get("uuid")
                if pid:
                    merged["otto"] = {
                        "found": True, "project_id": str(pid),
                        "project_name": rjson.get("name"),
                        "url": rjson.get("url"),
                    }
            elif name == "cg_list_brand_vaults":
                # Only found when a real BV object matches the searched domain AND has an ID.
                bv_match = _find_asset_by_domain(rjson, domain, ("vault_id", "id", "uuid"))
                if bv_match:
                    merged["bv"] = {"found": True, "vault_id": str(bv_match["id"]), "domain": bv_match.get("domain")}
            elif name == "gbp_list_locations":
                gbp_match = _find_asset_by_domain(rjson, domain, ("location_id", "id", "uuid"))
                if gbp_match:
                    merged["gbp"] = {"found": True, "location_id": str(gbp_match["id"]), "domain": gbp_match.get("domain")}
            elif name == "ppc_list_businesses":
                ppc_match = _find_asset_by_domain(rjson, domain, ("business_id", "id", "uuid"))
                if ppc_match:
                    merged["ppc"] = {"found": True, "business_id": str(ppc_match["id"]), "domain": ppc_match.get("domain")}
            elif name == "llmv_list_projects":
                llmv_match = _find_asset_by_domain(rjson, domain, ("project_id", "id", "uuid"))
                if llmv_match:
                    merged["llmv"] = {"found": True, "project_id": str(llmv_match["id"]), "domain": llmv_match.get("domain")}
            elif name == "otto_get_issues_by_type" and isinstance(rjson, dict):
                merged.setdefault("otto", {})["issue_clusters"] = rjson

    # Detect if Claude emitted the error shape
    if isinstance(merged, dict) and merged.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    audit("asset-inheritance.ok", {"domain": domain, "calls": len(sa_calls)})
    return {"domain": domain, "result": merged, "tool_calls": len(sa_calls)}


# ════════════════════════════════════════════════════════════════════════════
# /api/link-preservation — real anchor + referring-domain capture
# ════════════════════════════════════════════════════════════════════════════


def _build_link_preservation_prompt(domain: str, urls: list[str]) -> str:
    url_lines = "\n".join(f"- `{u}`" for u in urls[:30])
    return f"""# Link equity preservation probe for `{domain}`

The Search Atlas MCP is exposed under one of these namespace prefixes — use whichever is connected:
- `mcp__searchatlas__<tool>`
- `mcp__claude_ai_Search_Atlas__<tool>`

For EACH of the high-Authority Keep URLs below, fire IN PARALLEL:
- `se_get_anchor_text` for that URL
- `se_get_referring_domains` for that URL

ALSO fire once (in parallel with the rest):
- `se_get_link_network_graph` for `{domain}`

URLs to protect:
{url_lines}

Hard rules:
- Use ONLY the three Search Atlas tools above. No WebFetch, no Bash, no Read.
- If a call returns an authentication error, emit ONLY `{{"error":"authentication_required"}}` and stop.

After all responses arrive, emit ONE final assistant message containing ONLY a JSON object with this exact shape (omit / set null for missing data — NEVER fabricate):

```json
{{
  "anchorByUrl": {{ "<url>": {{"sample": ["anchor1", "anchor2", "..."], "count": <int>}} }},
  "refDomainsByUrl": {{ "<url>": {{"sample": ["domain1.com", "domain2.com"], "count": <int>}} }},
  "linkGraph": {{"nodes": <int>, "edges": <int>}}
}}
```"""


@app.post("/api/link-preservation")
async def link_preservation(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    domain = domain_clean(payload.get("domain") or "")
    high_auth = payload.get("highAuthorityPages") or []
    urls = [(p.get("url") or "").strip() for p in high_auth if isinstance(p, dict) and p.get("url")]
    urls = [u for u in urls if u][:30]
    if not domain:
        return JSONResponse({"error": "domain_required"}, status_code=400)
    if not urls:
        audit("link-preservation.empty")
        return {"domain": domain, "result": {"anchorByUrl": {}, "refDomainsByUrl": {}, "linkGraph": {"nodes": 0, "edges": 0}}, "tool_calls": 0}
    audit("link-preservation.request", {"domain": domain, "urls": len(urls)})

    prompt = _build_link_preservation_prompt(domain, urls)
    allowed = sa_allowed_variants([
        "se_get_anchor_text",
        "se_get_referring_domains",
        "se_get_link_network_graph",
    ])
    res = await run_claude_session(prompt, timeout_sec=180, allowed_tools=allowed)

    if res["timed_out"]:
        audit("link-preservation.timeout", {"domain": domain})
        return JSONResponse({"error": "probe_timeout"}, status_code=504)
    if res["auth_error"]:
        audit("link-preservation.auth_error", {"domain": domain})
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    sa_calls = filter_sa_tool_calls(res["tool_calls"])
    if not sa_calls:
        audit("link-preservation.no_tool_calls", {"domain": domain})
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)

    parsed = extract_json_from_text(res["assistant_text"])
    if isinstance(parsed, dict) and parsed.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    if not isinstance(parsed, dict) or not parsed:
        # Tool calls ran but Claude never emitted a parseable JSON envelope —
        # do NOT fabricate an empty success envelope.
        audit("link-preservation.no_parseable_result", {"domain": domain, "calls": len(sa_calls)})
        return JSONResponse(
            {"error": "no_parseable_result", "tool_calls": [short_tool_name(tc["name"]) for tc in sa_calls]},
            status_code=502,
        )
    audit("link-preservation.ok", {"domain": domain, "calls": len(sa_calls)})
    return {"domain": domain, "result": parsed, "tool_calls": len(sa_calls)}


# ════════════════════════════════════════════════════════════════════════════
# /api/pre-launch-baseline — real KRT + GSC snapshot
# ════════════════════════════════════════════════════════════════════════════


def _build_pre_launch_prompt(domain: str, tracked: list[str]) -> str:
    tracked_lines = "\n".join(f"- `{k}`" for k in (tracked or [])[:80]) or "- (no operator-supplied keywords — use whatever KRT has for the project)"
    return f"""# Pre-launch baseline capture for `{domain}`

Capture the CURRENT (pre-launch) state of the old domain so the rebuild can later compute a delta.

The Search Atlas MCP is exposed under one of these namespace prefixes — use whichever is connected:
- `mcp__searchatlas__<tool>`
- `mcp__claude_ai_Search_Atlas__<tool>`

Required calls (fire in parallel):
1. `krt_list_projects` with `{{}}` → find the KRT project matching `{domain}`.
2. `krt_get_rankings` for that project_id (28-day window) → tracked-keyword positions.
3. `gsc_get_sites` to find the GSC site property that matches `{domain}`.
4. `gsc_get_keyword_performance` for that site, 28-day window.
5. `gsc_get_page_performance` for that site, 28-day window.

Operator-supplied keywords to also track (if not already in KRT):
{tracked_lines}

Hard rules:
- Use ONLY the five Search Atlas tools listed. No WebFetch, no Read, no Bash.
- If a call returns an authentication error, emit ONLY `{{"error":"authentication_required"}}` and stop.

After all responses arrive, emit ONE final assistant message containing ONLY a JSON object with this exact shape (use `null` / `[]` for missing data, NEVER fabricate numbers):

```json
{{
  "krtSnapshot": {{
    "project_id": <str or null>,
    "trackedKeywords": <int>,
    "topKeywords": [ {{"keyword": <str>, "position": <int>, "volume": <int or null>}} ]
  }},
  "gscKeywords": {{ "window": "28d", "totalKeywords": <int>, "totalClicks": <int>, "totalImpressions": <int> }},
  "gscPages":    {{ "window": "28d", "totalPages": <int>, "totalClicks": <int>, "totalImpressions": <int> }}
}}
```"""


@app.post("/api/pre-launch-baseline")
async def pre_launch_baseline(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    domain = domain_clean(payload.get("domain") or "")
    if not domain:
        return JSONResponse({"error": "domain_required"}, status_code=400)
    tracked = payload.get("trackedKeywords") or []
    audit("pre-launch-baseline.request", {"domain": domain, "kw": len(tracked)})

    prompt = _build_pre_launch_prompt(domain, tracked)
    allowed = sa_allowed_variants([
        "krt_list_projects",
        "krt_get_rankings",
        "gsc_get_sites",
        "gsc_get_keyword_performance",
        "gsc_get_page_performance",
    ])
    res = await run_claude_session(prompt, timeout_sec=180, allowed_tools=allowed)

    if res["timed_out"]:
        audit("pre-launch-baseline.timeout", {"domain": domain})
        return JSONResponse({"error": "probe_timeout"}, status_code=504)
    if res["auth_error"]:
        audit("pre-launch-baseline.auth_error", {"domain": domain})
        return JSONResponse({"error": "authentication_required"}, status_code=401)

    sa_calls = filter_sa_tool_calls(res["tool_calls"])
    if not sa_calls:
        audit("pre-launch-baseline.no_tool_calls", {"domain": domain})
        return JSONResponse({"error": "no_tool_calls_made"}, status_code=502)

    parsed = extract_json_from_text(res["assistant_text"])
    if isinstance(parsed, dict) and parsed.get("error") == "authentication_required":
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    if not isinstance(parsed, dict) or not parsed:
        # Tool calls ran but no parseable JSON came back — fail honestly.
        audit("pre-launch-baseline.no_parseable_result", {"domain": domain, "calls": len(sa_calls)})
        return JSONResponse(
            {"error": "no_parseable_result", "tool_calls": [short_tool_name(tc["name"]) for tc in sa_calls]},
            status_code=502,
        )
    audit("pre-launch-baseline.ok", {"domain": domain, "calls": len(sa_calls)})
    return {"domain": domain, "result": parsed, "tool_calls": len(sa_calls)}


# ════════════════════════════════════════════════════════════════════════════
# /api/new-page-evidence — SSE per-candidate research
# ════════════════════════════════════════════════════════════════════════════


def _build_new_page_evidence_prompt(domain: str, candidates: list[dict], competitors: list[str]) -> str:
    cand_lines = []
    for c in candidates:
        slug = c.get("slug") or "(unnamed)"
        kw = c.get("targetKw") or c.get("title") or slug
        cand_lines.append(f"- slug=`{slug}` · primary_kw=`{kw}`")
    comp_lines = "\n".join(f"- `{c}`" for c in (competitors or [])[:10]) or "- (no competitors supplied — discover via se_get_organic_competitors first)"

    return f"""# NEW page evidence research for `{domain}`

The Search Atlas MCP is exposed under one of these namespace prefixes — use whichever is connected:
- `mcp__searchatlas__<tool>`
- `mcp__claude_ai_Search_Atlas__<tool>`

For each NEW page candidate below, fire IN PARALLEL:
1. `se_lookup_keyword` for its primary_kw (volume + difficulty + intent)
2. `se_get_serp_overview` for that primary_kw (who ranks, page types)
3. `se_get_indexed_pages` for the top 3 competitor URLs from that SERP
4. `se_get_serp_features` for that primary_kw (SERP features to target)
5. `cg_topic_suggestions` for the primary_kw (subtopics + adjacent terms)

Candidates:
{chr(10).join(cand_lines)}

Known competitors (use these when possible):
{comp_lines}

Hard rules:
- Use ONLY the five Search Atlas tools listed. No WebFetch, no Read, no Bash.
- If a call returns an authentication error, emit ONLY `{{"error":"authentication_required"}}` and stop.

After all responses arrive, emit ONE final assistant message containing ONLY a JSON object keyed by slug with this exact shape (use `null` / `[]` for missing data, NEVER fabricate):

```json
{{
  "<slug>": {{
    "primaryKw": <str>,
    "volume": <int or null>,
    "difficulty": <int or null>,
    "intent": <str or null>,
    "serpType": <str or null>,
    "competitorEvidence": {{"count": <int>, "examples": [<str>, ...]}},
    "serpFeatures": [<str>, ...],
    "subtopics": [<str>, ...]
  }}
}}
```"""


@app.post("/api/new-page-evidence")
async def new_page_evidence(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    candidates = payload.get("newPageCandidates") or []
    if not isinstance(candidates, list) or not candidates:
        return JSONResponse({"error": "no_candidates"}, status_code=400)
    domain = domain_clean(payload.get("domain") or "")
    competitors = payload.get("competitors") or []
    audit("new-page-evidence.request", {"domain": domain, "candidates": len(candidates)})

    prompt = _build_new_page_evidence_prompt(domain, candidates[:8], competitors)
    allowed = sa_allowed_variants([
        "se_lookup_keyword",
        "se_get_serp_overview",
        "se_get_indexed_pages",
        "se_get_serp_features",
        "cg_topic_suggestions",
        "se_get_organic_competitors",
    ])

    async def event_stream():
        async def emit(obj):
            return f"data: {json.dumps(obj)}\n\n".encode()

        yield await emit({"type": "phase", "label": "Researching NEW pages"})

        claude_path = shutil.which("claude")
        if not claude_path:
            yield await emit({"type": "error", "message": "claude CLI not found"})
            return

        cmd = [
            claude_path, "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--allowedTools", ",".join(allowed),
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
            yield await emit({"type": "error", "message": f"spawn failed: {exc}"})
            return

        assistant_text_parts: list[str] = []
        tool_call_count = 0
        sa_call_count = 0
        auth_error_seen = False

        assert proc.stdout is not None
        start = time.monotonic()
        try:
            while True:
                if time.monotonic() - start > 180:
                    try: proc.kill()
                    except Exception: pass
                    yield await emit({"type": "error", "message": "probe_timeout"})
                    return
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = data.get("type")
                if t == "assistant":
                    for block in data.get("message", {}).get("content", []) or []:
                        bt = block.get("type")
                        if bt == "text":
                            txt = block.get("text") or ""
                            if txt:
                                assistant_text_parts.append(txt)
                        elif bt == "tool_use":
                            tool_call_count += 1
                            name = block.get("name") or ""
                            if is_sa_tool(name):
                                sa_call_count += 1
                            label = friendly_label(name, block.get("input") or {})
                            if label:
                                yield await emit({"type": "work", "label": label})
                elif t == "user":
                    for block in data.get("message", {}).get("content", []) or []:
                        if block.get("type") == "tool_result":
                            content = block.get("content", "")
                            if isinstance(content, list):
                                text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                            else:
                                text = str(content)
                            if is_auth_error(text):
                                auth_error_seen = True
                            elif block.get("is_error", False):
                                snippet = (text or "").strip().replace("\n", " ")[:200]
                                yield await emit({"type": "error", "message": f"Tool returned an error: {snippet}" if snippet else "Tool returned an error"})
                            else:
                                yield await emit({"type": "done", "label": "Step complete"})
                elif t == "result":
                    pass

            await proc.wait()
        except Exception as exc:
            yield await emit({"type": "error", "message": f"stream error: {exc}"})
            return

        if auth_error_seen:
            audit("new-page-evidence.auth_error", {"domain": domain})
            yield await emit({"type": "error", "message": "authentication_required"})
            return
        if sa_call_count == 0:
            audit("new-page-evidence.no_tool_calls", {"domain": domain})
            yield await emit({"type": "error", "message": "no_tool_calls_made"})
            return

        merged = extract_json_from_text("".join(assistant_text_parts)) or {}
        audit("new-page-evidence.ok", {"domain": domain, "calls": sa_call_count})
        yield await emit({"type": "result", "evidence": merged, "tool_calls": sa_call_count})
        yield await emit({"type": "complete"})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ════════════════════════════════════════════════════════════════════════════
# /api/rebuild — full SSE prompt that fires /rebuild-website end-to-end
# ════════════════════════════════════════════════════════════════════════════


def _action_count(page_map: list, action: str) -> int:
    return sum(1 for p in page_map if p.get("action") == action)


def build_prompt(payload: dict) -> str:
    domain = domain_clean(payload.get("domain") or "")
    slug = domain_to_slug(domain)
    scout_file = (payload.get("scoutFile") or {}) or {}
    scout_name = scout_file.get("name") or "scout-output.html"
    scout_run_date = scout_file.get("parsedDateISO") or "unknown"

    asset_decisions: dict = payload.get("assetDecisions") or {}
    page_map: list = payload.get("pageMap") or []
    new_page_decisions: dict = payload.get("newPageDecisions") or {}
    brand_strategy: dict = payload.get("brandStrategy") or {}
    new_style = payload.get("newStyle") or ""
    scout_html_pages = payload.get("scoutHtmlPages") or []
    hosting_mode = payload.get("hostingMode") or "external"
    link_preservation = payload.get("linkPreservation") or {}

    ACTION_LABEL = {
        "use": "Use as-is", "edit": "Edit", "add": "Add data",
        "reject_fresh": "Reject + start fresh", "create": "Create", "skip": "Skip",
    }
    ASSET_NAMES = {
        "otto": "OTTO project", "bv": "Brand Vault", "gbp": "GBP location",
        "ppc": "PPC business", "llmv": "LLM Visibility",
    }

    keep_redesign_pages = [p for p in page_map if p.get("action") == "keep_redesign"]
    keep_rewrite_pages = [p for p in page_map if p.get("action") == "keep_rewrite"]
    merge_pages = [p for p in page_map if p.get("action") == "merge"]
    delete_pages = [p for p in page_map if p.get("action") == "delete"]
    new_pages = [p for p in page_map if p.get("action") == "new"]

    approved_new = [s for s, d in new_page_decisions.items() if (d or {}).get("decision") in ("approve", "edit")]
    rejected_new = [s for s, d in new_page_decisions.items() if (d or {}).get("decision") == "reject"]

    L: list[str] = []
    L.append("# /rebuild-website · automated run from Website Rebuild Wizard")
    L.append("")
    L.append("Run the `/rebuild-website` slash command end-to-end with the data below.")
    L.append(f"Scout output file: `{scout_name}` (already parsed in the wizard — run date `{scout_run_date}`).")
    L.append(f"Domain: `{domain}` · client slug: `{slug}`.")
    L.append("**Do NOT ask any interactive questions.** All operator decisions are provided below.")
    L.append("**Skip Phase 0** (target identification + scout ingest) — the wizard already did it.")
    L.append("")
    L.append("**CRITICAL — FAIL HARD ON AUTHENTICATION ERRORS.**")
    L.append("Before doing anything else, call `cg_list_brand_vaults` (under either `mcp__searchatlas__` or `mcp__claude_ai_Search_Atlas__` — use whichever namespace is connected) with empty params `{}` as an authentication probe.")
    L.append("")
    L.append("If that probe (or ANY subsequent `mcp__searchatlas__*` call) returns an authentication / OAuth / `not authenticated` / `unauthorized` / `401` / `connector not authenticated` error:")
    L.append("")
    L.append("1. IMMEDIATELY emit exactly this on its own line: `## Phase ERROR — AUTHENTICATION REQUIRED`")
    L.append("2. Then emit one paragraph: `Search Atlas MCP is not authenticated in this Claude Code session. Open Claude.ai, run /mcp, and complete the OAuth flow for the SearchAtlas connector. Then re-run this rebuild.`")
    L.append("3. EXIT immediately. Do NOT continue with subsequent phases.")
    L.append("")
    L.append("**HARD RULES — NEVER violate:**")
    L.append("- NEVER fabricate UUIDs, project IDs, Website Studio URLs, or any data that should come from a real MCP call.")
    L.append("- NEVER say `Build complete`, `Migration complete`, `Site is live`, `Published to Website Studio`, or equivalent unless `mcp__searchatlas__ws_publish_project` actually returned a URL in this run.")
    L.append("- NEVER `proceed with local artifacts` as a fallback for failed MCP calls. The user wants either a real rebuild or a clear error.")
    L.append("- If the auth probe succeeds, proceed normally with the phases below using real MCP calls only.")
    L.append("")
    L.append("Output formatting rules — important for the UI:")
    L.append("- Begin every phase with a heading on its own line: `## Phase N — name`.")
    L.append("- Keep narration tight: short sentences, plain English, no jargon, no raw command names.")
    L.append("- After major milestones, drop a short fact line (e.g. `Schema deployed — 12 pages.`).")
    L.append("- Don't print individual file paths. The UI summarizes them.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 1 — SA asset inheritance")
    L.append("")
    L.append("Operator decisions per asset (already locked — apply them, do not re-prompt):")
    for key, name in ASSET_NAMES.items():
        dec = (asset_decisions.get(key) or {})
        action = dec.get("action") or "use"
        line = f"- **{name}** — {ACTION_LABEL.get(action, action)}"
        edits = dec.get("edits") or {}
        if action == "edit" and edits:
            edit_summary = ", ".join(f"{k}={v}" for k, v in edits.items() if v)
            if edit_summary:
                line += f" · edits: {edit_summary[:240]}"
        L.append(line)
    L.append("")
    L.append("Then fire in parallel for OTTO issue clusters:")
    L.append("- `otto_find_project_by_hostname` for the domain → load the existing project (or note absence).")
    L.append("- `otto_get_issues_by_type` once a project is loaded → group issues into thin-content / schema / orphan / linking buckets.")
    L.append("Apply each operator action: `use` = no MCP write; `edit` = push the operator's edits via the appropriate `bv_update*` / `otto_update_*` / `gbp_update*` / `llmv_*` / PPC tool; `reject_fresh` = scaffold a new asset alongside the old one and route the rebuild at the new one; `add` = additive write only; `create` = fresh from scratch; `skip` = leave untouched.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 2 — Old → new page map")
    L.append("")
    L.append(f"Total pages: {len(page_map)}. Keep+redesign: {len(keep_redesign_pages)} · Keep+rewrite: {len(keep_rewrite_pages)} · Merge: {len(merge_pages)} · Delete: {len(delete_pages)} · New: {len(new_pages)}.")
    L.append("")
    L.append("Per-URL operator decisions (already locked — execute, do not re-classify):")
    for p in page_map:
        if p.get("isGap"):
            L.append(f"- `(NEW)` {p.get('slug') or p.get('title', '')} → action=new · {p.get('title', '')}")
            continue
        url = p.get("url") or "/"
        title = p.get("title") or ""
        action = p.get("action") or "keep_redesign"
        extra = ""
        if action == "merge" and p.get("mergeInto"):
            extra = f" → merge into `{p['mergeInto']}`"
        if action == "delete" and p.get("redirectTo"):
            extra = f" → 301 to `{p['redirectTo']}`"
        L.append(f"- `{url}` · action={action}{extra} · {title}")
    L.append("")
    L.append("Fire link-equity preservation in parallel for every high-Authority Keep page:")
    L.append("- `se_get_anchor_text` per high-Authority Keep URL → capture inbound anchors.")
    L.append("- `se_get_referring_domains` per high-Authority Keep URL → snapshot referring domains to protect through redirects.")
    L.append("- `se_get_link_network_graph` once for the domain → build the internal-link graph for remap planning.")
    if link_preservation and link_preservation.get("anchorByUrl"):
        L.append(f"(Wizard already captured a preview via /api/link-preservation — anchors for {len(link_preservation.get('anchorByUrl') or {})} pages, link graph nodes {(link_preservation.get('linkGraph') or {}).get('nodes', 0)}. Confirm and extend via the MCP tools above.)")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 2.3 — NEW page market evidence")
    L.append("")
    if not new_pages:
        L.append("No NEW page candidates in the map — skip this phase.")
    else:
        L.append("For each NEW page candidate below, fire in parallel:")
        L.append("- `se_lookup_keyword` for the primary target keyword (volume + difficulty).")
        L.append("- `se_get_serp_overview` for that keyword (who ranks, page types).")
        L.append("- `se_get_indexed_pages` for the top 3 competitor URLs (mirror their structure).")
        L.append("- `se_get_serp_features` (SERP features to target — LOCAL_PACK, PAA, IMAGE_PACK, etc.).")
        L.append("- `cg_topic_suggestions` to flesh out subtopics.")
        L.append("- `se_analyze_keyword_gap` against the top 2-3 organic competitors to surface adjacent terms.")
        L.append("")
        L.append("NEW page candidates:")
        for p in new_pages:
            L.append(f"- `{p.get('slug') or '(unnamed)'}` · {p.get('title', '')} · tier={p.get('tier', 'service')}")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 2.5 — Per-page approval (already locked in wizard)")
    L.append("")
    L.append("The operator walked every NEW page in the wizard. Decisions are FINAL — do not re-prompt.")
    if approved_new:
        L.append(f"Approved NEW pages ({len(approved_new)}):")
        for s in approved_new:
            edits = (new_page_decisions.get(s) or {}).get("edits") or {}
            edit_str = ""
            if edits:
                pieces = []
                if edits.get("title"): pieces.append(f"title='{edits['title']}'")
                if edits.get("keywords"): pieces.append("keywords edited")
                if edits.get("sections"): pieces.append("sections edited")
                if pieces:
                    edit_str = " · " + ", ".join(pieces)
            L.append(f"- `{s}`{edit_str}")
    else:
        L.append("Approved NEW pages: (none)")
    if rejected_new:
        L.append(f"Rejected NEW pages ({len(rejected_new)}): " + ", ".join(f"`{s}`" for s in rejected_new))
    L.append("")
    L.append("Build topical map for the approved set:")
    L.append("- `cg_create_topical_map` for the domain with the approved NEW page slugs as primary topics.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 3 — Redesign preferences")
    L.append("")
    L.append(f"New style: `{new_style or '(operator must pick — bail with error)'}`.")
    if scout_html_pages:
        L.append(f"Operator dropped {len(scout_html_pages)} scout HTML export(s) — extract content blocks and reusable sections from these for Keep+redesign pages.")
        for f in scout_html_pages[:10]:
            name = f.get("filename") if isinstance(f, dict) else str(f)
            L.append(f"- `{name}`")
    else:
        L.append("No scout HTML exports provided — Keep+redesign falls back to scout's text inventory.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 4 — Brand strategy refresh")
    L.append("")
    bv_action = (asset_decisions.get("bv") or {}).get("action") or "use"
    if bv_action == "use":
        L.append("Brand Vault is being used as-is — strategy inherited, skip refresh.")
    else:
        voice = brand_strategy.get("voice") or ""
        pillars = brand_strategy.get("pillars") or ""
        diff = brand_strategy.get("differentiation") or ""
        L.append("Operator-supplied brand strategy:")
        L.append(f"- Voice / tone: {voice or '(operator left blank — derive from BV edits + scout)'}")
        if pillars:
            L.append("- Messaging pillars:")
            for line in pillars.splitlines():
                line = line.strip()
                if line:
                    L.append(f"  - {line}")
        if diff:
            L.append(f"- Differentiation: {diff}")
        L.append("Push voice + pillars + differentiation to the Brand Vault via `update_refine_prompt` and `bv_update_knowledge_graph` before the rebuild proceeds.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 4.5 — Pre-rebuild gate")
    L.append("")
    L.append("Operator already approved the HITL summary in the wizard before this run started. Do NOT re-prompt — proceed straight to execution. Log one line summarizing the locked decisions for the operator's record.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 5 — Rebuild execution")
    L.append("")
    L.append("Execute the rebuild via Website Studio:")
    L.append(f"- `ws_create_project` (or load existing) for `{slug}` under domain `{domain}` with the new style `{new_style or 'modern_minimal'}`.")
    L.append("- For each Keep+redesign page: load old content (from scout HTML if provided, else scout text inventory), wrap in the new style components.")
    L.append("- For each Keep+rewrite page: regenerate copy with `cg_dkn_generate_article` using the brand vault voice profile.")
    L.append("- For each Merge target: pull old sources, fold into the merge target page.")
    L.append("- For each NEW (approved) page: greenfield generation via `cg_dkn_generate_article` using the market evidence from Phase 2.3.")
    L.append("- Build the redirect map: every Delete URL maps to its `redirectTo`; every Merge URL maps to its `mergeInto`.")
    L.append("- Remap every internal link in the new build so nothing links to a Deleted/Merged URL.")
    L.append("- QA pass: link checker, schema presence, no 404s in the new build.")
    L.append("- Generate JSON-LD schema per page via `otto_generate_page_schema`, then deploy via `otto_deploy_page_schema`.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 6 — Pre-launch baseline capture")
    L.append("")
    L.append("Before the cutover, snapshot the current state so Phase 7 can compute the delta:")
    L.append("- `krt_get_rankings` for the active KRT project → tracked-keyword positions (against the OLD site).")
    L.append("- `gsc_get_keyword_performance` 28-day window (against the OLD site).")
    L.append("- `gsc_get_page_performance` 28-day window (against the OLD site).")
    L.append("Store all three snapshots in the rebuild artifacts directory — the post-launch verification depends on them.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 6.5 — Migration launch")
    L.append("")
    L.append(f"Hosting mode: **{hosting_mode}**.")
    if hosting_mode == "ws":
        L.append("In-place Website Studio replacement — no DNS cutover needed. The custom domain serves the new version once published.")
    else:
        L.append("External hosting — DNS cutover required. The Website Studio URL resolves immediately; custom domain pending operator DNS pointing.")
    L.append("Steps:")
    L.append("- Snapshot the old site one more time (final export — safety net).")
    L.append("- `ws_publish_project` to push the new build live.")
    L.append("- Apply the redirect map via Website Studio redirect rules.")
    L.append("- Verify SSL provisioned.")
    L.append("- `otto_activate_instant_indexing` for the project.")
    L.append("- `indexer_submit_batch` with every URL in the new build.")
    L.append("- Post-deploy sweep: sample 50 URLs from scout's inventory, confirm each resolves (200 / 301).")
    L.append("- Submit updated sitemap to Search Console.")
    L.append("- 24h post-launch: re-run `krt_get_rankings` to verify no critical positions dropped; flag any losses immediately.")
    L.append("**Important**: after `ws_publish_project` returns, surface the LIVE URL exactly as the MCP returned it — do not template it from the slug, do not guess a format, do not append `.ws.searchatlas.com`. Use whatever URL `ws_publish_project` returned.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Phase 7 — Before / After upgrade summary")
    L.append("")
    L.append("Compose the upgrade summary using data already on disk (no extra MCP calls needed):")
    L.append("- Total pages before/after; thin-content count before/after; orphan pages before/after.")
    L.append("- Content gaps closed (count of approved NEW pages).")
    L.append("- Schema coverage before/after.")
    L.append("- Design style change.")
    L.append("- Link equity protected (count of high-Authority Keep URLs whose anchors + ref-domains were captured).")
    L.append("- Indexing posture (instant indexing ON, batch-submitted URLs).")
    L.append("- Tracked keywords (count locked, delta deferred to `/run-seo`).")
    L.append("")
    L.append("End with a short summary block:")
    L.append("- Domain")
    L.append("- Pages in new site")
    L.append("- WS live URL (and custom domain status — pending DNS or live)")
    L.append("- Approved NEW pages count")
    L.append("- Redirects deployed")
    L.append("- Schema coverage")
    L.append("- Next step: monthly `/run-seo` cadence picks up from here.")
    L.append("")
    L.append("Begin now.")

    return "\n".join(L)


# ── Stream parser → friendly UI events ───────────────────────────────────────


PHASE_RE = re.compile(r"^##\s+Phase\s+[\d\.A-Z]+\s*[—\-:]\s*(.+)$", re.IGNORECASE)


_state: dict = {"workspace_announced": False, "biz_seen": False}


def reset_run_state() -> None:
    _state["workspace_announced"] = False
    _state["biz_seen"] = False
    _state["tool_use_index"] = {}
    _state["publish_call_seen"] = False
    _state["publish_succeeded"] = False
    _state["publish_url"] = None
    _state["publish_call_returned_without_url"] = False
    _state["fatal_error"] = False


# WS URL extractor — only accept searchatlas.com hosts; refuse arbitrary URLs.
_RB_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_RB_WS_URL_HOST_RE = re.compile(
    r"https?://[a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)*\.(?:searchatlas\.com|ws\.searchatlas\.com)(?:/|$)",
    re.IGNORECASE,
)


def _rb_is_ws_publish_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    return bool(_RB_WS_URL_HOST_RE.match(url))


def _rb_extract_url_from_text(text: str) -> str | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for k in ("url", "site_url", "live_url", "preview_url", "publish_url", "published_url"):
                v = obj.get(k)
                if isinstance(v, str) and v.startswith(("http://", "https://")) and _rb_is_ws_publish_url(v):
                    return v
    except (json.JSONDecodeError, ValueError):
        pass
    for m in _RB_URL_RE.finditer(text):
        candidate = m.group(0).rstrip(".,);]")
        if _rb_is_ws_publish_url(candidate):
            return candidate
    return None


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
                    _state.setdefault("tool_use_index", {})[tool_use_id] = {
                        "name": tool_name, "is_publish": False,
                    }
                    continue
                # Track ws_publish_project calls so we can pair them with their
                # tool_result and emit a ws_published event carrying the real URL.
                is_publish_call = "ws_publish_project" in tool_name.lower()
                _state.setdefault("tool_use_index", {})[tool_use_id] = {
                    "name": tool_name, "is_publish": is_publish_call,
                }
                if is_publish_call:
                    _state["publish_call_seen"] = True
                label = friendly_label(tool_name, tool_input)
                if label:
                    events.append({"type": "work", "label": label})
        return events

    if msg_type == "user":
        message = data.get("message", {})
        for block in message.get("content", []):
            if block.get("type") == "tool_result":
                tool_use_id = block.get("tool_use_id") or ""
                idx = _state.get("tool_use_index", {}).get(tool_use_id, {})
                is_publish = bool(idx.get("is_publish"))
                content = block.get("content", "")
                if isinstance(content, list):
                    text = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                else:
                    text = str(content)
                if text and is_auth_error(text):
                    events.append({"type": "error", "message": "authentication_required"})
                    _state["fatal_error"] = True
                elif block.get("is_error", False):
                    snippet = (text or "").strip().replace("\n", " ")[:200]
                    events.append({"type": "error", "message": f"Tool returned an error: {snippet}" if snippet else "Tool returned an error"})
                    if is_publish:
                        _state["publish_call_returned_without_url"] = True
                elif text:
                    # Capture REAL ws_publish_project URL only — refuse synthesized URLs.
                    if is_publish:
                        url = _rb_extract_url_from_text(text)
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
                    events.append({"type": "done", "label": "Step complete"})
        return events

    if msg_type == "result":
        # Same gate as build wizard: only emit `complete` if a real
        # ws_publish_project URL landed. Otherwise the migration is not
        # confirmed live — emit `incomplete` so the UI doesn't show
        # "site published" without a real URL.
        if _state.get("fatal_error"):
            return events
        if _state.get("publish_call_seen"):
            if _state.get("publish_succeeded") and _state.get("publish_url"):
                events.append({"type": "complete"})
            else:
                reason = (
                    "ws_publish_project did not return a recognizable WS URL"
                    if _state.get("publish_call_returned_without_url")
                    else "ws_publish_project did not return a URL"
                )
                events.append({"type": "incomplete", "message": reason})
        else:
            # Some rebuild flows (Before/After summary only) don't publish.
            # Emit a soft `complete` for those — the operator will see it as
            # the planning artifact finishing, not a publish.
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
    # Note: on rc == 0 we deliberately do NOT emit an unconditional `complete`.
    # parse_claude_event's `result` branch already emits either `complete`
    # (when ws_publish_project really returned a URL, or when no publish was
    # required) or `incomplete` (when publish was attempted but no URL came
    # back). Emitting an unconditional success here would let a Claude run
    # that never published fall through to "Site is live" in the UI.


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/api/rebuild")
async def rebuild(request: Request):
    payload = await request.json()
    if not domain_clean(payload.get("domain") or ""):
        return JSONResponse({"error": "domain is required"}, status_code=400)
    audit("rebuild.request", {"domain": domain_clean(payload.get("domain") or "")})
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
    import os
    import signal

    async def _exit_soon():
        await asyncio.sleep(0.2)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_exit_soon())
    return {"ok": True, "message": "shutting down"}


# ── Entrypoint ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8767))
    print(f"\n  Website Rebuild Wizard")
    print(f"  → http://localhost:{port}\n")
    print(f"  Toolkit root: {TOOLKIT_ROOT}")
    print(f"  Claude CLI:   {shutil.which('claude') or '(not found)'}")
    print(f"  Audit log:    {AUDIT_LOG}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
