"""
Website Build Wizard — local server that bridges the web UI to Claude Code.

Form payload from the wizard is converted into a single self-contained prompt
that runs the `/build-website` slash command end-to-end:

  Phase 1  — Identify target (domain provided, slug derived)
  Phase 2  — Quick existence check (BV + GBP)
  Phase 3  — Multi-format intake (operator-dropped materials)
  Phase 4  — Brand vault use OR auto-create + auto-fill
  Phase 5  — Budget tier
  Phase 6  — Brand strategy synthesis
  Phase 7  — Market-evidence research (2-wave parallel research, 9 SA tools)
  Phase 8  — Per-page approval (pre-approved by operator in the wizard)
  Phase 9  — Design style + push to BV / WS
  Phase 10 — Content + copy per page
  Phase 11 — Build + push to Website Studio
  Phase 12 — Publish + handoff (ws_publish_project, return both URLs)

Stream parsing mirrors the Command Center: raw MCP tool names are mapped to
readable process labels before being forwarded to the browser. Internal tools
(Read, Skill, ToolSearch, TodoWrite) are filtered out entirely.
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
        if (cur / "commands" / "build-website.md").exists():
            return cur
        cur = cur.parent
    return start.parent


TOOLKIT_ROOT = find_toolkit_root(HERE)


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
    "gbp_list_categories":          "Pulling GBP category taxonomy",
    "gbp_list_attributes":          "Reading GBP attributes",
    "gbp_upsert_attributes":        "Saving GBP attributes",
    "gbp_upsert_standard_services": "Saving GBP services",
    "gbp_update_location":          "Updating the GBP profile",
    "gbp_suggest_description":      "Drafting GBP description",
    "gbp_create_audit_report_external": "Auditing the GBP profile",
    "gbp_get_audit_report":         "Loading GBP audit",
    # SEO / Site explorer — including the 9 wave-research tools
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
    # Keyword tracking
    "krt_create_project":           "Setting up keyword tracking",
    "krt_add_keywords":             "Adding target keywords",
    "krt_bulk_add_keywords":        "Adding target keywords",
    "krt_refresh_rankings":         "Pulling current rankings",
    # Content
    "cg_create_topical_map":        "Building topical map",
    "cg_search_topical_maps":       "Looking up topical maps",
    "cg_topic_suggestions":         "Pulling knowledge-graph topics",
    "cg_generate_complete_article": "Generating first article",
    "cg_dkn_generate_article":      "Generating article from knowledge graph",
    "cg_create_brand_vault":        "Creating brand vault",
    "cg_get_brand_vault_details":   "Loading brand vault",
    "cg_run_content_grader":        "Grading content quality",
    "cg_list_brand_vaults":         "Checking for an existing brand vault",
    # OTTO — schema + indexing pieces touched by /build-website
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
    # Indexer
    "indexer_submit_batch":         "Submitting URLs to Google",
    "indexer_check_status":         "Checking indexing status",
    # Website Studio
    "ws_create_project":            "Scaffolding Website Studio project",
    "ws_publish_project":           "Publishing to Website Studio",
    "ws_get_project":               "Verifying Website Studio state",
    "ws_ensure_containers_running": "Starting Website Studio build environment",
    "ws_list_projects":             "Listing Website Studio projects",
    # LLM visibility (referenced in BV auto-crawl)
    "llmv_get_brand_overview":      "Reading brand presence in LLMs",
    # KG validation
    "kg_validate_completeness":     "Validating knowledge graph completeness",
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


app = FastAPI(title="Website Build Wizard", version="1.0")
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
    L.append("- NEVER `proceed with local artifacts` as a fallback for failed MCP calls. The user does NOT want a fake/simulated run.")
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

    # ── Phase 1 — Identify target ──
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

    # ── Phase 2 — Quick existence check (BV + GBP) ──
    L.append("## Phase 2 — Quick existence check")
    L.append("")
    L.append("Run these two SA lookups in parallel:")
    L.append("- `cg_list_brand_vaults` — filter by domain. If exists, capture `brand_vault_uuid`.")
    L.append("- `gbp_list_locations` — filter by business name + location. If exists, capture `gbp_location_id`.")
    L.append("")
    L.append("Do not check OTTO, PPC, LLM Visibility — `/run-seo` provisions those after the site is live.")
    if detect:
        bv_status = detect.get("bv") or "unknown"
        gbp_status = detect.get("gbp") or "unknown"
        L.append("")
        L.append(f"Operator-side detection earlier showed: BV={bv_status}, GBP={gbp_status}. Confirm against live SA.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 3 — Multi-format operator intake ──
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

    # ── Phase 4 — Brand vault use OR auto-create ──
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

    # ── Phase 5 — Budget tier ──
    L.append("## Phase 5 — Budget tier")
    L.append("")
    if tier:
        L.append(f"Budget tier: **{tier}**. Persist to `budget-tier.json`. Used by `/run-seo` later — not by this workflow.")
    else:
        L.append("No tier specified — default to Growth and flag in pre-build review.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 6 — Brand strategy synthesis ──
    L.append("## Phase 6 — Brand strategy")
    L.append("")
    L.append("Synthesize `brand-strategy.md` from BV fields + operator materials + competitor crawl + logo color cues.")
    L.append("Edits flow back to BV via `bv_update`. Don't print the full content — just confirm the file exists.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 7 — Market-evidence research (the two waves) ──
    L.append("## Phase 7 — Market-evidence research")
    L.append("")
    L.append("**This is the wave-based research phase — fire each wave in PARALLEL (single tool batch, not sequential calls).**")
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
    L.append("Push industry → BV `primary_category`; target keywords + competitors → BV knowledge graph (`bv_update_knowledge_graph`).")
    L.append("")
    L.append("### Wave 1 — 5 tools in PARALLEL")
    L.append("Fire all five in one tool batch:")
    L.append("- `se_lookup_keyword` per target KW → volume + intent + difficulty")
    L.append("- `se_get_serp_overview` per target KW → who ranks today")
    L.append("- `gbp_list_categories` → category taxonomy")
    L.append("- `se_get_organic_competitors` per target KW → auto-discovered competitor set")
    L.append("- `se_get_serp_features` per target KW → LOCAL_PACK / FAQ / IMAGE_PACK / etc.")
    L.append("")
    L.append("Merge: `competitor_set = operator_competitors ∪ auto_competitors` (cap at 3–5).")
    L.append("")
    L.append("### Wave 2 — 4 tools in PARALLEL")
    L.append("After Wave 1, fire all four in one tool batch:")
    L.append("- `se_get_indexed_pages` per competitor → real page structures")
    L.append("- `se_analyze_keyword_gap` between competitors → unclaimed keyword territory")
    L.append("- `cg_create_topical_map` seeded with kw_data → content clusters")
    L.append("- `cg_topic_suggestions` with `brand_vault_uuid` → BV-driven topic suggestions")
    L.append("")
    L.append("### Synthesis (no SA calls)")
    L.append("Combine competitor_pages + gap_clusters + topical_map + bv_topics + operator services + location. Produce `proposed-sitemap.json` with per-page evidence (kw_total_volume, intent, competitor_count, serp_features, gap_score, source).")
    L.append("")
    L.append("### Rank tracking")
    L.append("After synthesis: `krt_create_project` for the domain, `krt_bulk_add_keywords` with the validated target KWs.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 8 — Per-page approval (already done by operator) ──
    L.append("## Phase 8 — Page queue (operator pre-approved)")
    L.append("")
    L.append("**Operator already walked every proposed page in the wizard.** Do NOT re-run the walkthrough.")
    L.append("Below is the locked queue. Write it directly to `page-build-queue.csv`.")
    L.append("")
    approved_pages = []
    rejected_pages = []
    edited_pages = []
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

    # ── Phase 9 — Design style ──
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

    # ── Phase 10 — Content + copy ──
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

    # ── Phase 11 — Build + push to Website Studio ──
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

    # ── Phase 12 — Publish + handoff ──
    L.append("## Phase 12 — Publish + handoff")
    L.append("")
    L.append("Final pre-publish sweep — all pages render in WS preview.")
    L.append("Then publish:")
    L.append("- `ws_publish_project` (project_id) → returns the WS-hosted URL (`{slug}.ws.searchatlas.com`)")
    L.append("- `otto_activate_instant_indexing` for the domain")
    L.append("- `indexer_submit_batch` with the approved page URLs → push to Google")
    L.append("- Emit DNS cutover instructions for the operator's custom domain")
    L.append("")
    L.append("End with the standard completion block:")
    L.append("```")
    L.append(f"Site is live on Website Studio")
    L.append("")
    L.append(f"Live now:       https://{slug}.ws.searchatlas.com")
    L.append(f"Custom domain:  https://{domain} (pending DNS cutover)")
    L.append("")
    L.append("What's next:")
    L.append(f"  /run-seo {domain}   — provisions OTTO, LLM Visibility, GBP, and sizes ongoing cadence")
    L.append("```")
    L.append("")
    L.append("Then write `clients/{slug}/CLAUDE.md` and `clients/{slug}/brand-profile.md` from the templates. Don't print the full contents — just confirm both files exist.")
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


@app.post("/api/build")
async def build(request: Request):
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


@app.post("/api/shutdown")
async def shutdown(request: Request):
    """Graceful shutdown — called by welcome.html on tab close or Stop button.
    Returns 200, then exits the process after a short delay so the response flushes."""
    import os
    import signal

    async def _exit_soon():
        await asyncio.sleep(0.2)  # let response flush
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
    print(f"  Claude CLI:   {shutil.which('claude') or '(not found)'}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
