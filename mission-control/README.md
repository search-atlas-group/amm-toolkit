# Mission Control

You're in the engine room. This folder holds the heavier machinery — the installer, the always-on supervisor daemon, the three web wizards, and the bridge restart helpers. Most of it auto-configures when you run [`setup.sh`](setup.sh) (or its shim at the repo root).

If you're new to the toolkit, start with the [README at the repo root](../README.md) — you don't need anything in here to use the slash commands or Claude Desktop prompts.

---

## What's here

| Path | Role |
|---|---|
| [`setup.sh`](setup.sh) | The full Mac installer. Writes LaunchAgents, installs slash commands, optionally wires send-integrations. The shim at repo root forwards here. |
| [`Start Bridges.command`](Start%20Bridges.command) | macOS fallback: double-click to restart bridges when the supervisor is unreachable. Setup also drops a copy on your Desktop. |
| [`Start Bridges.bat`](Start%20Bridges.bat) | Windows equivalent — `schtasks /End` then `/Run` for each registered task. |
| `tools/` | The Python services Mission Control depends on (see below). |

---

## tools/ — local services

Four FastAPI services back the welcome page wizards.

| Service | Port | Lifecycle | Source |
|---|---|---|---|
| `supervisor/` | 8764 | Always-on (KeepAlive=true, ~15 MB RAM) | [`tools/supervisor/server.py`](tools/supervisor/server.py) |
| `command-center/` | 8865 | Idle-shutdown 5 min | [`tools/command-center/server.py`](tools/command-center/server.py) |
| `website-build/` | 8866 | Idle-shutdown 5 min | [`tools/website-build/server.py`](tools/website-build/server.py) |
| `website-rebuild/` | 8867 | Idle-shutdown 5 min | [`tools/website-rebuild/server.py`](tools/website-rebuild/server.py) |

Plus utilities that don't run as bridges:
- `tools/security/` — repo security scanner UI (the backend powers `/security-scan`)
- `tools/guardian/` — AMM Guardian dashboard

---

## How it boots

```
You click a wizard card in welcome.html
      │
      ▼
welcome.html pings supervisor at localhost:8764
      │
      ▼ if target bridge is asleep
supervisor runs `launchctl kickstart` (Mac) or `schtasks /Run` (Windows)
      │
      ▼
bridge starts, runs auth probe against SearchAtlas MCP
      │
      ▼
wizard begins; welcome.html sends /api/heartbeat every 60s to keep the bridge alive
```

When you close the wizard tab, heartbeat stops. Bridge idle-shuts down after 5 min of silence. Any Claude subprocess the bridge spawned is **detached** — it keeps running to completion regardless of the tab. Files land in `clients/<slug>/`.

---

## When to actually look in here

| You need to… | Go to |
|---|---|
| Reinstall everything | run [`bash setup.sh`](setup.sh) from the repo root (the shim) |
| Debug a wizard | tail `/tmp/amm-<service>.err` and `/tmp/amm-<service>-audit.log` |
| Understand the supervisor's wake logic | read [`tools/supervisor/server.py`](tools/supervisor/server.py) — well-commented |
| Restart bridges by hand | double-click `SearchAtlas Mission Control.command` (Mac) or `.bat` (Windows) on your Desktop |
| Add a new wizard | follow the pattern in `tools/command-center/` — FastAPI server, `index.html`, `run.sh`, `requirements.txt` |

---

## Power-user docs

Full architecture, troubleshooting matrix, and platform-parity notes are in [`../POWER-USER.md`](../POWER-USER.md).
