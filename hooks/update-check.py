#!/usr/bin/env python3
"""Print an "update available" nudge when the cached latest version is newer than
the installed one. Read-only and local (no network) — the cache is refreshed
separately by update-fetch.py. Prints nothing on any error or when up to date,
so the SessionStart hook can append the output unconditionally.

Usage: update-check.py <installed_plugin_json> <latest_cache_json>
"""
import json
import sys


def ver(s):
    try:
        return tuple(int(x) for x in str(s).split(".")[:3])
    except Exception:
        return ()


def main():
    if len(sys.argv) < 3:
        return
    plugin_json, cache = sys.argv[1], sys.argv[2]
    try:
        inst = ver(json.load(open(plugin_json))["version"])
        latest = ver(json.load(open(cache)).get("latest", ""))
    except Exception:
        return
    if inst and latest and latest > inst:
        i = ".".join(map(str, inst))
        l = ".".join(map(str, latest))
        print(
            f"⬆ SearchAtlas v{l} available (you're on v{i}) — "
            "run: /plugin marketplace update searchatlas && /plugin update searchatlas"
        )


if __name__ == "__main__":
    main()
