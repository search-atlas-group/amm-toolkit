"""
Website Rebuild Wizard — local server that bridges the web UI to Claude Code.

The wizard collects every operator decision needed for `/rebuild-website`
(scout output, SA asset inheritance choices, page rebuild map, NEW page
approvals, brand strategy, design style, hosting mode, pre-launch baseline
intent) and ships the whole bundle here. This server compiles the bundle
into a single self-contained prompt and spawns `claude -p` so Claude can
run the rebuild end-to-end without interactive questions.

Stream parsing mirrors the Command Center bridge: raw MCP tool names are
mapped to friendly process labels before being forwarded to the browser,
and internal/noisy tools are filtered out entirely.
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
        if (cur / "commands" / "rebuild-website.md").exists():
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
    # Keyword tracking
    "krt_create_project":           "Setting up keyword tracking",
    "krt_add_keywords":             "Adding target keywords",
    "krt_bulk_add_keywords":        "Adding target keywords",
    "krt_refresh_rankings":         "Pulling current rankings",
    "krt_get_rankings":             "Capturing pre-launch rank snapshot",
    # Content
    "cg_create_topical_map":        "Building topical map",
    "cg_search_topical_maps":       "Looking up topical maps",
    "cg_topic_suggestions":         "Generating topic ideas",
    "cg_generate_complete_article": "Generating page copy",
    "cg_dkn_generate_article":      "Generating article from knowledge graph",
    "cg_create_brand_vault":        "Creating brand vault",
    "cg_get_brand_vault_details":   "Loading brand vault",
    "cg_run_content_grader":        "Grading content quality",
    # OTTO
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
    # Indexer
    "indexer_submit_batch":         "Submitting URLs to Google",
    # GSC
    "gsc_get_keyword_performance":  "Pulling GSC keyword baseline",
    "gsc_get_page_performance":     "Pulling GSC page baseline",
    # Website Studio
    "ws_create_project":            "Scaffolding Website Studio project",
    "ws_publish_project":           "Publishing to Website Studio",
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


app = FastAPI(title="Website Rebuild Wizard", version="1.0")
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
    old_style = payload.get("oldStyle") or "unknown"
    scout_html_pages = payload.get("scoutHtmlPages") or []
    hosting_mode = payload.get("hostingMode") or "external"
    link_preservation = payload.get("linkPreservation") or {}
    pre_launch_baseline = payload.get("preLaunchBaseline") or {}

    # Asset action labels
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
    L.append("Before doing anything else, call `mcp__searchatlas__cg_list_brand_vaults` with empty params `{}` as an authentication probe.")
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

    # ── Phase 1 — SA asset inheritance ───────────────────────────────────────
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

    # ── Phase 2 — Old → New page map ─────────────────────────────────────────
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
    if link_preservation:
        L.append(f"(Wizard already ran a synthetic preview — anchors for {len(link_preservation.get('anchorByUrl') or {})} pages, link graph nodes {(link_preservation.get('linkGraph') or {}).get('nodes', 0)}. Confirm real numbers via the MCP tools above.)")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 2.3 — Market evidence for NEW page candidates ──────────────────
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

    # ── Phase 2.5 — Per-page approval (already locked in wizard) ─────────────
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

    # ── Phase 3 — Redesign preferences ───────────────────────────────────────
    L.append("## Phase 3 — Redesign preferences")
    L.append("")
    L.append(f"Old style: `{old_style}` · New style: `{new_style or '(operator must pick — bail with error)'}`.")
    if new_style and new_style == old_style:
        L.append("**Note**: operator picked the same style as the old site — confirm in summary this is a rebuild not a content refresh, but proceed anyway.")
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

    # ── Phase 4 — Brand strategy refresh ─────────────────────────────────────
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

    # ── Phase 4.5 — Pre-rebuild gate (the wizard IS the gate) ────────────────
    L.append("## Phase 4.5 — Pre-rebuild gate")
    L.append("")
    L.append("Operator already approved the HITL summary in the wizard before this run started. Do NOT re-prompt — proceed straight to execution. Log one line summarizing the locked decisions for the operator's record.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 5 — Rebuild execution ──────────────────────────────────────────
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

    # ── Phase 6 — Pre-launch baseline ────────────────────────────────────────
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

    # ── Phase 6.5 — Migration launch ─────────────────────────────────────────
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
    L.append("**Important**: after `ws_publish_project` returns, capture the live WS URL (typically `{slug}.ws.searchatlas.com` or whatever the MCP returns) and surface it in the summary. The custom domain status depends on hosting mode.")
    L.append("")
    L.append("---")
    L.append("")

    # ── Phase 7 — Before / After summary ─────────────────────────────────────
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


PHASE_RE = re.compile(r"^##\s+Phase\s+[\d\.]+\s*[—\-:]\s*(.+)$", re.IGNORECASE)
BIZ_LINE_RE = re.compile(r"(?:business name|business is|client(?:'s)? name|domain)\s*[:\-]?\s*\*?\*?([A-Z][A-Za-z0-9&'\.\- ]{2,60?})\*?\*?", re.IGNORECASE)


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


@app.post("/api/rebuild")
async def rebuild(request: Request):
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
    port = int(os.environ.get("PORT", 8767))
    print(f"\n  Website Rebuild Wizard")
    print(f"  → http://localhost:{port}\n")
    print(f"  Toolkit root: {TOOLKIT_ROOT}")
    print(f"  Claude CLI:   {shutil.which('claude') or '(not found)'}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
