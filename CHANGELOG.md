# Changelog

All notable changes to the SearchAtlas Toolkit plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.8] — 2026-05-28

### Fixed
- **Wizards: namespace-agnostic SearchAtlas discovery.** The `website-build`, `website-rebuild`, and `command-center` wizards used to hardcode `mcp__searchatlas__*` as the SearchAtlas tool prefix. Users who installed SearchAtlas under a different name — including anyone using the **claude.ai web connector** — got false-negative "SearchAtlas needs authentication" errors even when the connector was correctly installed. Wizards now discover the actual namespace in two stages: parse `claude mcp list --json` (fast path), and fall back to a model probe that handles claude.ai connectors (which don't appear in `mcp list`). Triggered by Don Franklin's report on 2026-05-28.
- **Wizards: toolkit-root detection survives plugin reorgs.** `find_toolkit_root` in three wizards looked for command markers at their pre-plugin paths and silently fell back to the wrong directory (`mission-control/tools/`) when files moved. Now uses `.claude-plugin/plugin.json` as the canonical marker with legacy paths as fallbacks. (Shipped earlier in 2.2.8 as `989683f`.)

### Improved
- **Auth modal now tells the truth.** Instead of always saying "SearchAtlas needs authentication", wizards distinguish four real failure states: `not_installed` (no SA connector found), `oauth_expired` (auth lapsed), `discovery_timeout` (probe slow), `server_offline` (local wizard server is down). Each has distinct copy and an actionable hint.
- **`run.sh` auto-kills stale wizard processes** on the target port before binding. No more `Errno 48: address already in use` from previous zombie runs.
- **New "Stop wizard" button** in each wizard UI. POSTs `/api/shutdown` to cleanly terminate the local server — no more terminal-hunting.
- **Idle-timeout badge** surfaces in each wizard so users understand the wizard auto-stops after 5 min of inactivity.
- **Launch banner** lists all three ways to stop the wizard (Ctrl+C, Stop button, idle).

### Internal
- New `mission-control/tools/_shared/sa_namespace.py` module factored out of duplicated wizard code. All three wizards import from it; future wizards will too.

## [2.2.7] — 2026-05-27

### Fixed
- **Install failed on machines without GitHub SSH keys.** The plugin's source used the `github` shorthand (`{"source":"github","repo":"…"}`), which delegates clone protocol to the user's git config — boxes without SSH keys configured for GitHub were getting "Permission denied (publickey)" errors. Switched to an explicit HTTPS URL source (`{"source":"url","url":"https://github.com/…/.git","ref":"main"}`) so any user can install anonymously with zero auth.
- README quickstart now uses the **explicit HTTPS marketplace URL** for `/plugin marketplace add` (instead of the `owner/repo` shorthand), for the same reason — the shorthand path can also resolve to SSH on some machines.

### Note for users hit by the SSH error
Either reinstall against the new HTTPS-source marketplace:
```
/plugin marketplace remove searchatlas
/plugin marketplace add https://github.com/search-atlas-group/amm-toolkit.git
/plugin install searchatlas
```
…or simply refresh and update if you already added it:
```
/plugin marketplace update searchatlas
/plugin update searchatlas
```

## [2.2.6] — 2026-05-26

### Added
- **"Update available" nudge.** The SessionStart hook now compares your installed version against the latest on `main` and, when you're behind, appends a line to the banner: `⬆ SearchAtlas vX.Y.Z available (you're on vA.B.C) — run: /plugin marketplace update searchatlas && /plugin update searchatlas`. The latest-version cache is refreshed in the background (urllib, 3s timeout, ~24h cache) so startup never blocks. Opt out with `SA_NO_UPDATE_CHECK=1`. Helpers: `hooks/update-check.py` (local compare) and `hooks/update-fetch.py` (background fetch).

## [2.2.5] — 2026-05-26

### Changed
- **Marketplace now tracks the `main` branch instead of a pinned version tag** (`source.ref: "main"`). Releases no longer require editing `marketplace.json` — a version bump + push to `main` is the whole release. This also removes the "ref lags the latest tag → marketplace serves a stale version" failure mode.

### Added
- `Scripts/release.sh` — one-command release: bumps `plugin.json` version, validates, commits, and pushes to `main` (optionally tags). Requires a matching `CHANGELOG.md` entry first.
- README "Staying updated" section, including how to enable marketplace auto-update so future releases land at startup with no manual steps.

### Note for existing users
If you installed before v2.2.5 and aren't seeing updates, your local marketplace clone is cached at an older ref. Refresh it once:
```
/plugin marketplace update searchatlas
/plugin update searchatlas
```
Enabling auto-update for the marketplace (see README) makes this automatic going forward.

## [2.2.4] — 2026-05-26

### Fixed
- **SessionStart banner never fired on install.** `plugin.json` declared `"hooks": "./hooks/hooks.json"`, but Claude Code auto-loads that standard path — the double reference triggered a "Duplicate hooks file detected" error and the hook failed to load entirely. Removed the redundant manifest field; `hooks/hooks.json` is now discovered automatically.

### Added
- Banner art reproduced at the top of `README.md` (renders in monospace on GitHub, matching the in-terminal splash).

## [2.2.3] — 2026-05-26

### Changed
- Splash banner: removed the "Y" from the cat (cleaner face).

## [2.2.2] — 2026-05-26

### Changed
- Splash banner now calls out the bundled SearchAtlas MCP ("Powered by the SearchAtlas MCP — auto-connected").

## [2.2.1] — 2026-05-26

### Changed
- Splash banner: added SearchAtlas star ✦ sparkles around the wordmark.

## [2.2.0] — 2026-05-26

### Added
- Branded SessionStart splash — a figlet `SEARCH ATLAS` wordmark + line-art Voodoo + tagline, shown on first run via the hook's `systemMessage`; a compact one-liner (`✦ SearchAtlas · 21 commands · /searchatlas:help`) on subsequent sessions. Art lives in `hooks/banner.txt` (kept separate from the script to dodge a bash 3.2 heredoc/paren bug). MCP-auth and legacy-data notices fold into the same banner.

## [2.1.1] — 2026-05-26

### Fixed
- README quickstart fork now names Claude Cowork explicitly (MCP-only path, same as Desktop/web) and corrected leftover `sa-*` prose to `/searchatlas:*`
- `commands/help.md` and `Scripts/migrate-to-plugin.sh` — fixed remaining `sa-*` prose references

## [2.1.0] — 2026-05-26

### Added
- **`using-searchatlas` skill** (`skills/using-searchatlas/SKILL.md`) — the plugin's runtime "brain": intent-routing rules, golden rules for the SearchAtlas MCP, parameter quick-reference, account-discovery flow, and conventions. Auto-loads when a user works on SearchAtlas/SEO/marketing tasks.

### Fixed
- **Plugin instructions now actually load for users.** Previously this guidance lived in root `AGENTS.md`, which Claude Code does **not** load from an installed plugin (only skills load). The routing/golden-rules intelligence was inert for end users; it's now delivered via the auto-invoked skill above. `AGENTS.md` is slimmed to a pointer for contributors.

## [2.0.0] — 2026-05-26

### Changed (breaking)
- **Plugin renamed** `searchatlas-toolkit` → `searchatlas`. Install is now `/plugin install searchatlas`. The human-readable name "SearchAtlas Toolkit" is preserved via the `displayName` field.
- **Command prefix dropped.** Commands are no longer named `sa-scout`, `sa-run-seo`, etc. — they're now `scout`, `run-seo`, etc. Because Claude Code namespaces plugin commands by plugin name, the user-facing invocation changes from `/searchatlas-toolkit:sa-scout` to **`/searchatlas:scout`** — the brand is carried once, by the namespace, instead of stuttering.

### Why
The `sa-` prefix was chosen for brand reinforcement, but plugin commands are always invoked through the mandatory `searchatlas:` namespace, which already brands every invocation with the full name. The prefix was redundant (`searchatlas-toolkit:sa-scout`). This release finalizes the naming before any marketplace adoption.

### Migration
Anyone who installed v1.x: uninstall (`/plugin uninstall searchatlas-toolkit`) and reinstall (`/plugin install searchatlas`). Commands change from `/searchatlas-toolkit:sa-<name>` to `/searchatlas:<name>`.

## [1.0.2] — 2026-05-26

### Changed
- `.claude-plugin/marketplace.json` — `source` now uses the canonical GitHub form (`{"source": "github", "repo": "...", "ref": "..."}`) per the docs, replacing the `{"source": "url", ...}` form
- `.claude-plugin/plugin.json` — added `displayName`, `keywords` for discoverability
- `.claude-plugin/marketplace.json` — added per-plugin `tags` and `repository` fields

## [1.0.1] — 2026-05-26

### Fixed
- `.claude-plugin/marketplace.json` — `source` field uses the object form per the schema validator; previously `"source": "."` which failed validation
- `.claude-plugin/marketplace.json` — added required `description` field
- `.claude-plugin/plugin.json` — removed `agents` and `skills` field declarations (empty reserved dirs fail schema validation; `.gitkeep` files retained)
- `hooks/hooks.json` — restructured to the nested form `{"hooks": {"SessionStart": [{"hooks": [{"type": "command", ...}]}]}}`
- `commands/sa-summit-shot.md` — quoted the YAML frontmatter `description` (an unquoted colon-space broke parsing)

These were schema mismatches caught by `claude plugin validate` that would have caused install failures.

## [1.0.0] — 2026-05-26

Initial plugin release (shipped as `searchatlas-toolkit` with `sa-*` prefixed commands; both changed in 2.0.0).

### Added
- Plugin packaging — converted the clone-and-script install into a Claude Code plugin
- SearchAtlas MCP server auto-registered on install (no separate `claude mcp add` step)
- 21 slash commands covering SEO, GBP, PPC, content, AI visibility, sharing, and setup
- Plugin-scoped instructions in `AGENTS.md` (intent routing, golden rules, parameter reference)
- SessionStart hook for client data dir creation and MCP auth check (`hooks/ensure-env.sh`)
- One-shot migration script for existing CLI users (`Scripts/migrate-to-plugin.sh`)
- Reserved `skills/` and `agents/` directories for future expansion
- Self-hosted marketplace via `.claude-plugin/marketplace.json` — the repo is its own marketplace

### Changed
- Client data location moved from `<repo>/clients/` to `~/.searchatlas/clients/` (env-overridable via `SA_CLIENTS_DIR`)
- Per-client artifacts organized into `scouts/`, `reports/`, `workflows/`, `shots/` subfolders
- Commands resolve plugin assets via `$CLAUDE_PLUGIN_ROOT` and client data via `$SA_CLIENTS_DIR`
- Positioning: framed for anyone using SearchAtlas — solo SEOs, in-house teams, agencies — not exclusively agencies

### Removed
- `setup.sh` (replaced by `/plugin install`)
- SessionStart auto-update hook (plugins handle updates via `/plugin update`)
- `POWER-USER.md`, `docs/install.html`, `docs/welcome.html`, `docs/CLAUDE_DESKTOP_PROMPTS.md`, `docs/SLASH_COMMANDS.md`, `commands/README.md` (folded into README + AGENTS.md)

### Migration
Existing users on the cloned-repo install: run `./Scripts/migrate-to-plugin.sh` from inside your clone.
