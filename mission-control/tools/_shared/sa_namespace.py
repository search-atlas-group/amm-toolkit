"""SearchAtlas MCP namespace discovery.

Resolves the actual ``mcp__<name>__`` prefix for SearchAtlas tools regardless
of whether the user installed the connector via ``claude mcp add`` or as a
claude.ai web connector.

Two-stage discovery:
  1. CLI fast path — parse ``claude mcp list --json``, find a server whose URL
     contains ``mcp.searchatlas.com``, return its name.
  2. Model probe fallback — spawn ``claude -p`` with a tiny prompt asking
     Claude to find any tool whose function name is ``cg_list_brand_vaults``,
     return its full namespaced name, strip the suffix to get the prefix.

Stage 2 catches claude.ai web connectors, which are invisible to
``claude mcp list``.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Optional


# ── Cache ────────────────────────────────────────────────────────────────────
# Process-local. Successful results live for the wizard process lifetime;
# failed results expire after 10 s so the user can retry without restarting.

_NS_CACHE: dict = {"value": None, "failed_at": 0.0}
_FAILURE_TTL_S = 10.0

_CLI_LIST_TIMEOUT_S = 10.0
_PROBE_TIMEOUT_S = 20.0
_PROBE_TOOL_NAME = "cg_list_brand_vaults"

_SA_URL_FRAGMENT = "mcp.searchatlas.com"

_NS_PREFIX_RE = re.compile(r"^mcp__[A-Za-z0-9_]+__$")
_NS_BLOCK_RE = re.compile(r"<<<NS>>>(.+?)<<<END>>>", re.DOTALL)

_PROBE_PROMPT = """You have MCP tools available. Find any tool whose function name is exactly `cg_list_brand_vaults`. The namespace prefix is unknown — it may be `mcp__searchatlas__`, `mcp__claude_ai_Search_Atlas__`, `mcp__claude_ai_SA_MCP__`, `mcp__atlas__`, or anything else. We don't know what the user named their SearchAtlas connector.

If you find a matching tool, emit exactly one line, with no other text:

<<<NS>>>full_namespaced_tool_name<<<END>>>

If no such tool exists in your available tools, emit:

<<<NS>>>NONE<<<END>>>

Do not call any tool. Do not respond with anything except the block.
"""


async def check_sa_via_cli(claude_path: str) -> Optional[str]:
    """Stage 1 — return the namespace prefix from ``claude mcp list --json``,
    or None if SearchAtlas is not registered there. Never raises.

    Handles older ``claude`` CLI versions that don't support ``--json`` by
    falling through silently — Stage 2 takes over in that case.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            claude_path, "mcp", "list", "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=_CLI_LIST_TIMEOUT_S
        )
    except Exception:
        return None

    text = (stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    # JSON shape varies across CLI versions; handle dict-with-servers and
    # flat list.
    servers = None
    if isinstance(data, dict):
        servers = data.get("servers") or data.get("mcpServers")
        if servers is None and all(isinstance(v, dict) for v in data.values()):
            # Some versions emit ``{"server_name": {...}, ...}``.
            servers = [{"name": k, **v} for k, v in data.items()]
    elif isinstance(data, list):
        servers = data

    if not isinstance(servers, list):
        return None

    for entry in servers:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        url_fields = (
            entry.get("url"),
            entry.get("httpUrl"),
            entry.get("endpoint"),
        )
        url_blob = " ".join(str(u or "") for u in url_fields).lower()
        if _SA_URL_FRAGMENT in url_blob and name:
            prefix = f"mcp__{name}__"
            # Defensive: only return if it looks like a valid identifier.
            if _NS_PREFIX_RE.match(prefix):
                return prefix
    return None


async def _discover_via_model_probe(claude_path: str, cwd: str) -> Optional[str]:
    """Stage 2 — spawn ``claude -p`` with the probe prompt and parse the
    namespace from its response. Returns None on timeout or unparseable
    output. Never raises.

    Required because claude.ai web connectors are invisible to
    ``claude mcp list`` but visible to the spawned model.
    """
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            claude_path, "-p",
            "--output-format", "stream-json",
            "--verbose",
            _PROBE_PROMPT,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=_PROBE_TIMEOUT_S
        )
    except asyncio.TimeoutError:
        if proc is not None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        return None
    except Exception:
        return None

    text = (stdout or b"").decode("utf-8", errors="replace")

    # stream-json: one JSON object per line. Concatenate all assistant text
    # blocks, then regex the marker out of the combined blob.
    text_chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("type") != "assistant":
            continue
        msg = data.get("message", {}) or {}
        for block in msg.get("content", []) or []:
            if block.get("type") == "text":
                text_chunks.append(block.get("text") or "")

    blob = "".join(text_chunks)
    match = _NS_BLOCK_RE.search(blob)
    if not match:
        return None

    full_name = match.group(1).strip()
    if full_name == "NONE":
        return None
    if not full_name.endswith(_PROBE_TOOL_NAME):
        return None
    prefix = full_name[: -len(_PROBE_TOOL_NAME)]
    if not _NS_PREFIX_RE.match(prefix):
        return None
    return prefix


async def discover_sa_namespace(claude_path: str, cwd: str) -> Optional[str]:
    """Public entry point. Returns a namespace prefix like
    ``mcp__searchatlas__`` or None if SearchAtlas can't be found.

    Caches successful results for the process lifetime, failed results
    for 10 s so a user can fix their setup and click Retry without waiting
    on a fresh full discovery cycle.
    """
    cached = _NS_CACHE["value"]
    if cached:
        return cached

    failed_at = _NS_CACHE["failed_at"]
    if failed_at and (time.monotonic() - failed_at) < _FAILURE_TTL_S:
        return None

    ns = await check_sa_via_cli(claude_path)
    if ns is None:
        ns = await _discover_via_model_probe(claude_path, cwd)

    if ns:
        _NS_CACHE["value"] = ns
        _NS_CACHE["failed_at"] = 0.0
    else:
        _NS_CACHE["failed_at"] = time.monotonic()
    return ns


def render_prompt(template: str, sa_ns: Optional[str]) -> str:
    """Substitute ``{SA_NS}`` in the template with the discovered prefix.

    If sa_ns is None (discovery failed), substitute with an empty string —
    the spawned Claude will then see naked tool names like
    ``cg_list_brand_vaults`` and can still find them via ToolSearch (or fail
    explicitly, which the caller handles via the structured auth-probe
    response). Idempotent.
    """
    return template.replace("{SA_NS}", sa_ns or "")


def reset_cache_for_tests() -> None:
    """Test/dev hook — clear the cache between manual probes."""
    _NS_CACHE["value"] = None
    _NS_CACHE["failed_at"] = 0.0
