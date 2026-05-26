# Changelog

All notable changes to the SearchAtlas Toolkit plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
