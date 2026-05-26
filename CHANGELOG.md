# Changelog

All notable changes to the SearchAtlas Toolkit plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-05-26

### Fixed
- `.claude-plugin/marketplace.json` — `source` field now uses the object form (`{"source": "url", "url": "...", "ref": "..."}`) per Claude Code's schema validator; previously used `"source": "."` which failed validation
- `.claude-plugin/marketplace.json` — added required `description` field
- `.claude-plugin/plugin.json` — removed `agents` and `skills` field declarations (those directories are reserved but empty; declaring empty paths fails schema validation)
- `hooks/hooks.json` — restructured to the nested form `{"hooks": {"SessionStart": [{"hooks": [{"type": "command", ...}]}]}}`; previously used an array which failed validation
- `commands/sa-summit-shot.md` — quoted the YAML frontmatter `description` value (contained a colon-space sequence that broke YAML parsing)

These four schema mismatches were caught by `claude plugin validate` and would have caused install failures. No functional changes to the plugin behavior.

## [1.0.0] — 2026-05-26

### Added
- Plugin packaging — install via `/plugin marketplace add search-atlas-group/amm-toolkit` + `/plugin install searchatlas-toolkit`
- SearchAtlas MCP server auto-registered on install (no separate `claude mcp add` step)
- 21 slash commands prefixed `sa-*` (e.g., `/sa-scout`, `/sa-run-seo`, `/sa-business-report`)
- Plugin-scoped instructions in `AGENTS.md` (intent routing, golden rules, parameter reference)
- SessionStart hook for client data dir creation and MCP auth check (`hooks/ensure-env.sh`)
- One-shot migration script for existing CLI users (`Scripts/migrate-to-plugin.sh`)
- Reserved `skills/` and `agents/` directories for future expansion
- Self-hosted marketplace via `.claude-plugin/marketplace.json` — the repo is its own marketplace

### Changed
- Client data location moved from `<repo>/clients/` to `~/.searchatlas/clients/` (env-overridable via `SA_CLIENTS_DIR`)
- Per-client artifacts organized into `scouts/`, `reports/`, `workflows/`, `shots/` subfolders to keep the top level clean
- Commands resolve plugin assets via `$CLAUDE_PLUGIN_ROOT` (set by Claude Code at runtime) and client data via `$SA_CLIENTS_DIR`
- Positioning: framed for anyone using SearchAtlas — solo SEOs, in-house teams, agencies — not exclusively agencies

### Removed
- `setup.sh` (replaced by `/plugin install`)
- SessionStart auto-update hook (plugins handle updates via `/plugin update`)
- `POWER-USER.md`, `docs/install.html`, `docs/welcome.html`, `docs/CLAUDE_DESKTOP_PROMPTS.md`, `docs/SLASH_COMMANDS.md`, `commands/README.md` (folded into README + AGENTS.md)
- Mission-control deletions of `tools/{security,supervisor,website-build,website-rebuild,guardian}/` (separate concern)

### Migration
Existing users on the cloned-repo install: run `./Scripts/migrate-to-plugin.sh` from inside your clone. See README "Migrating from the cloned-repo toolkit." It moves your client data, removes legacy commands, and declares the plugin in your `~/.claude/settings.json` so Claude Code auto-prompts to install on next launch.
