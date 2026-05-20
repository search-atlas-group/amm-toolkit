"""
AMM Mission Control supervisor — the tiny always-on daemon that wakes bridges
on demand.

Why this exists
---------------
The three bridge servers (command-center 8765, website-build 8766,
website-rebuild 8767) idle-shutdown after ~5 min of inactivity. When the user
clicks a wizard card in welcome.html, the bridge may be dead. Browsers can't
call `launchctl` directly, so this supervisor sits on port 8764 with one job:
receive a POST and run `launchctl kickstart` to bring the requested bridge up.

Resource footprint: ~15 MB resident, zero CPU when idle. This is the only
process that lingers after a workshop session.

Endpoints
---------
- GET  /api/health           — `{"ok": true}` so welcome.html can verify presence
- POST /wake/{bridge_name}   — `launchctl kickstart -k gui/$UID/com.searchatlas.amm-<name>`
                                Accepted names: command-center, website-build, website-rebuild
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


VALID_BRIDGES = {"command-center", "website-build", "website-rebuild"}
BRIDGE_PORTS = {
    "command-center":  8865,
    "website-build":   8866,
    "website-rebuild": 8867,
}


def _port_listening(port: int) -> bool:
    """True iff something is listening on localhost:<port>. We use a raw
    socket probe (not HTTP) so we don't get fooled by a bridge whose
    /api/health blocks on `claude mcp list` during cold-start."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False

app = FastAPI(title="AMM Mission Control Supervisor", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "amm-supervisor", "valid_bridges": sorted(VALID_BRIDGES)}


@app.post("/wake/{bridge}")
async def wake(bridge: str) -> dict:
    if bridge not in VALID_BRIDGES:
        return JSONResponse({"error": "unknown_bridge", "valid": sorted(VALID_BRIDGES)}, status_code=400)

    # IDEMPOTENCY: if a bridge is already listening on its port, leave it alone.
    # The previous version used `kickstart -k` which kills-then-restarts, so
    # every click of a wizard card killed the bridge the user was about to use.
    port = BRIDGE_PORTS.get(bridge)
    if port and _port_listening(port):
        return {"ok": True, "bridge": bridge, "via": "already_listening", "port": port}

    launchctl = shutil.which("launchctl") or "/bin/launchctl"
    label = f"com.searchatlas.amm-{bridge}"
    target = f"gui/{os.getuid()}/{label}"

    # `kickstart` (without -k) only starts the service if it isn't running.
    try:
        proc = subprocess.run(
            [launchctl, "kickstart", target],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return {"ok": True, "bridge": bridge, "via": "kickstart"}

        # Fallback: kickstart can fail with "service not loaded". Try bootstrap.
        plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if plist.exists():
            boot = subprocess.run(
                [launchctl, "bootstrap", f"gui/{os.getuid()}", str(plist)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if boot.returncode == 0:
                # Bootstrap with RunAtLoad=true also starts the job; no need to
                # kickstart -k (which would kill it again).
                return {"ok": True, "bridge": bridge, "via": "bootstrap"}
            return JSONResponse(
                {"error": "bootstrap_failed", "rc": boot.returncode, "stderr": boot.stderr[:300]},
                status_code=500,
            )

        return JSONResponse(
            {"error": "plist_missing", "expected": str(plist)},
            status_code=500,
        )

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "launchctl_timeout"}, status_code=504)
    except Exception as exc:
        return JSONResponse({"error": f"launchctl_failed: {exc}"}, status_code=500)


def _check_port_or_die(port: int, service: str) -> None:
    """Probe-bind 0.0.0.0:port before uvicorn starts. Catches the macOS quirk
    where *:port and localhost:port can both bind, which would otherwise
    cause welcome.html's /api/health pings to fail intermittently."""
    import socket as _socket, subprocess as _sp, sys as _sys
    probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    probe.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    try:
        probe.bind(("0.0.0.0", port))
        return
    except OSError:
        pass
    finally:
        probe.close()
    holder = ""
    lsof = shutil.which("lsof")
    if lsof:
        try:
            out = _sp.run([lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                          capture_output=True, text=True, timeout=2)
            for line in out.stdout.splitlines():
                if line and not line.startswith("COMMAND"):
                    parts = line.split()
                    if len(parts) >= 2:
                        holder = f"{parts[0]} (PID {parts[1]})"
                        break
        except Exception:
            pass
    _sys.stderr.write(f"\n  ✗  {service} cannot bind port {port}\n")
    if holder:
        _sys.stderr.write(f"      Held by: {holder}\n")
    _sys.stderr.write(f"      Free it:  lsof -ti:{port} | xargs kill\n\n")
    _sys.exit(1)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8764))
    _check_port_or_die(port, "AMM Mission Control supervisor")
    print(f"\n  AMM Mission Control supervisor")
    print(f"  → http://localhost:{port}")
    print(f"  Manages: {sorted(VALID_BRIDGES)}\n")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
