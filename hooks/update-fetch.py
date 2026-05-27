#!/usr/bin/env python3
"""Fetch the latest plugin version from a raw URL and cache it. Best-effort:
any failure exits silently. Run detached/in the background by the SessionStart
hook so startup never blocks on the network.

Usage: update-fetch.py <raw_plugin_json_url> <cache_path>
"""
import json
import sys
import time
import urllib.request


def main():
    if len(sys.argv) < 3:
        return
    url, cache = sys.argv[1], sys.argv[2]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "searchatlas-plugin"})
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = str(data.get("version", "")).strip()
        if latest:
            with open(cache, "w") as f:
                json.dump({"latest": latest, "checked_at": int(time.time())}, f)
    except Exception:
        pass


if __name__ == "__main__":
    main()
