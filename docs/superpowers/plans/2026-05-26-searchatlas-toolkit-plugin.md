# SearchAtlas Toolkit Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the `toolkit-public` repo from a clone-and-script-installed slash command bundle into a Claude Code plugin named `searchatlas-toolkit` that ships commands, a SearchAtlas MCP registration, hooks, and plugin-scoped instructions in one installable unit.

**Architecture:** Single-repo plugin (same repo serves as plugin source AND its own marketplace). All slash commands gain an `sa-` prefix. Client data moves from gitignored `<repo>/clients/` to `~/.searchatlas/clients/` (env-overridable). One SessionStart hook replaces the old auto-update hook. A one-shot migration script moves existing users via `~/.claude/settings.json` auto-install.

**Spec:** `docs/superpowers/specs/2026-05-26-searchatlas-toolkit-plugin-design.md` (read this before starting — it has full design rationale)

**Tech Stack:** Bash 4+ (scripts must work on macOS default Bash 3.2 — use POSIX-compatible idioms), jq (manifest validation), shellcheck (script linting), git (commits + the existing repo state)

---

## Preconditions (Before Starting Task 1)

This plan reads source command files from their current TIERED locations and writes the converted `sa-*.md` versions to a flat `commands/` directory. No prior refactor required.

**Source Command Locations (read from these tiered paths):**

| Tier | Path | Commands |
|---|---|---|
| `essentials` | `commands/essentials/` | `business-report.md`, `help.md`, `my-account.md`, `scout.md` |
| `advanced` | `commands/advanced/` | `build-website.md`, `rebuild-website.md`, `security-scan.md`, `setup-integrations.md` |
| `clients` | `commands/clients/` | `onboard-client.md`, `summit-shot.md`, `sync-client.md` |
| `sharing` | `commands/sharing/` | `send-circle.md`, `send-discord.md`, `send-email.md`, `send-slack.md` |
| `workflows` | `commands/workflows/` | `run-content.md`, `run-gbp.md`, `run-ppc.md`, `run-pr.md`, `run-seo.md`, `run-visibility.md` |

**Destination:** all converted files land at `commands/sa-{name}.md` (flat).

**Cleanup after conversion (covered in Task 24.5):** the tiered subdirectories (`commands/essentials/`, `commands/advanced/`, `commands/clients/`, `commands/sharing/`, `commands/workflows/`) get removed once all `sa-*.md` files are created and tests pass.

**Mission-control caveat for Tasks 22 (build-website) and 23 (rebuild-website):** the existing `commands/advanced/build-website.md` and `commands/advanced/rebuild-website.md` may reference paths under `mission-control/tools/website-build/` and `mission-control/tools/website-rebuild/`. Per the locked-in design (spec §2), mission-control stays outside the plugin. These commands should be rewritten to either (a) work standalone via SearchAtlas MCP tools (preferred), or (b) detect whether mission-control is installed locally and degrade gracefully if not.

Verify before starting:

```bash
ls commands/essentials commands/advanced commands/clients commands/sharing commands/workflows  # all present
git status --short | head -5  # working tree should be reasonably clean
```

---

## File Structure

**Files to create:**
- `.claude-plugin/plugin.json` — plugin manifest (MCP, hooks, asset paths)
- `.claude-plugin/marketplace.json` — single-entry marketplace listing
- `AGENTS.md` — plugin-scoped instructions (replaces user CLAUDE.md modifications)
- `CHANGELOG.md` — plugin release history
- `commands/sa-*.md` × 21 — renamed/prefixed/content-substituted commands
- `hooks/hooks.json` — SessionStart hook registration
- `hooks/ensure-env.sh` — env + MCP auth check (idempotent, fail-open)
- `skills/.gitkeep` — reserved future-skills directory
- `agents/.gitkeep` — reserved future-agents directory
- `scripts/migrate-to-plugin.sh` — one-shot migration for existing users

**Files to modify:**
- `README.md` — rewrite top-level fork (Code/Desktop), update install instructions
- `CLAUDE.md` — slim to a pointer at `AGENTS.md` (since the plugin now ships its own scoped instructions)
- `.gitignore` — ensure `~/.searchatlas/clients/` style paths aren't accidentally captured if user works inside the repo

**Files to delete (after their replacements work):**
- `commands/{name}.md` × 21 — the unprefixed originals (deleted after `sa-*.md` versions are verified)

**Files NOT touched:**
- `workflows/*.yaml` — content unchanged; only path resolution in commands changes
- `integrations/**/*.sh` — content unchanged
- `mission-control/**` — left alone entirely (separate companion piece)
- `Scripts/quickstart-mac.sh`, `Scripts/quickstart-windows.ps1`, `Scripts/repo-security-scan.sh` — updated only as needed for branding/path consistency, but not part of plugin install path anymore

---

## Task 0: Verify Plugin Schema Details Against Current Docs

**Why:** Spec §13 flagged three field-name uncertainties. Before any code is written, resolve them so subsequent tasks use correct values. These are 10-minute lookups, not implementation work.

**Files:** none (research-only task)

- [ ] **Step 1: Verify `plugin.json` manifest schema**

Check current Claude Code plugin documentation for the exact field names in `plugin.json`. Specifically need to confirm:
- The field for MCP server registrations is `mcpServers` (object keyed by server name) or `mcp_servers` or another form
- The field for asset paths uses `commands`, `agents`, `skills`, `hooks` as relative paths or absolute with `${CLAUDE_PLUGIN_ROOT}` interpolation
- Whether `version` follows SemVer strictly

Run: `claude --help` and look at the plugin-related help text, or fetch https://code.claude.com/docs/en/plugins
Expected: a confirmed field-name list to use in Task 2

- [ ] **Step 2: Verify env var name exposed to plugin scripts**

Confirm the exact env var Claude Code exposes to plugin commands and hooks for "the plugin's install dir." The spec assumes `CLAUDE_PLUGIN_ROOT`. If it's different (e.g., `PLUGIN_ROOT`, `CC_PLUGIN_DIR`), update.

Run: same docs check as Step 1
Expected: confirmed env var name

- [ ] **Step 3: Verify `~/.claude/settings.json` auto-install fields**

Confirm the exact JSON schema for declaring a marketplace and an enabled plugin in `~/.claude/settings.json`. Spec assumes:
```json
{
  "extraKnownMarketplaces": [
    { "source": "github", "repo": "search-atlas-group/amm-toolkit" }
  ],
  "enabledPlugins": ["searchatlas-toolkit"]
}
```
Need to confirm field names and that `source: github` resolves correctly.

Run: docs check
Expected: confirmed schema for the migration script

- [ ] **Step 4: Verify command frontmatter format**

Confirm the exact frontmatter fields Claude Code expects in `commands/*.md`. Likely `name` + `description`, possibly `argument-hint` or `model`. Need this to write commands consistently.

Run: docs check or examine an existing official plugin's command file (e.g., `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/brainstorming/SKILL.md` for skills frontmatter; check for plugin command examples)
Expected: confirmed frontmatter field list

- [ ] **Step 5: Document findings**

Write findings to a scratch file `docs/superpowers/plans/.task-0-findings.md` (gitignored — add `docs/superpowers/plans/.task-*-findings.md` to `.gitignore` if not already). Subsequent tasks reference this file for exact field names.

```bash
cat > docs/superpowers/plans/.task-0-findings.md <<'EOF'
# Task 0 Findings

Manifest field for MCP servers: ___
Manifest field for command path: ___
Manifest field for hooks path: ___
Plugin install dir env var: ___
settings.json marketplace field: ___
settings.json enabled plugin field: ___
Command frontmatter fields: ___
EOF
```

No commit yet — this is research scratch only.

---

## Task 1: Create `.claude-plugin/plugin.json`

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Write the manifest validator test**

Create `tests/plugin-manifest.test.sh`:

```bash
#!/bin/bash
set -e
# Plugin manifest must exist, be valid JSON, and have required fields

MANIFEST=".claude-plugin/plugin.json"

[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST missing"; exit 1; }

jq -e '.name == "searchatlas-toolkit"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: name field wrong"; exit 1; }

jq -e '.version | test("^[0-9]+\\.[0-9]+\\.[0-9]+$")' "$MANIFEST" >/dev/null \
  || { echo "FAIL: version not SemVer"; exit 1; }

jq -e '.mcpServers.searchatlas.url == "https://mcp.searchatlas.com/mcp"' "$MANIFEST" >/dev/null \
  || { echo "FAIL: searchatlas MCP not registered correctly"; exit 1; }

echo "PASS: plugin manifest valid"
```

Make executable: `chmod +x tests/plugin-manifest.test.sh`

- [ ] **Step 2: Run test, confirm fail**

```bash
bash tests/plugin-manifest.test.sh
```
Expected: `FAIL: .claude-plugin/plugin.json missing`

- [ ] **Step 3: Create the manifest**

```bash
mkdir -p .claude-plugin
```

Write `.claude-plugin/plugin.json`:

```json
{
  "name": "searchatlas-toolkit",
  "version": "1.0.0",
  "description": "Official SearchAtlas command-line toolkit — SEO, GBP, PPC, content, and AI visibility workflows powered by the SearchAtlas MCP.",
  "author": {
    "name": "SearchAtlas",
    "url": "https://searchatlas.com"
  },
  "homepage": "https://github.com/search-atlas-group/amm-toolkit",
  "license": "MIT",
  "mcpServers": {
    "searchatlas": {
      "type": "http",
      "url": "https://mcp.searchatlas.com/mcp"
    }
  },
  "hooks": "./hooks/hooks.json",
  "commands": "./commands",
  "agents": "./agents",
  "skills": "./skills"
}
```

**Schema notes (verified Task 0):**
- `mcpServers` is camelCase, inline object form is valid for HTTP-type MCPs
- Asset paths use `./` prefix (relative to plugin root), NOT `${CLAUDE_PLUGIN_ROOT}` — that env var is only available inside hook scripts and MCP/LSP configs at runtime, not in manifest path fields
- `commands`, `agents`, `skills`, `hooks` are all recognized fields

- [ ] **Step 4: Run test, confirm pass**

```bash
bash tests/plugin-manifest.test.sh
```
Expected: `PASS: plugin manifest valid`

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json tests/plugin-manifest.test.sh
git commit -m "feat(plugin): add plugin.json manifest with SearchAtlas MCP registration"
```

---

## Task 2: Create `.claude-plugin/marketplace.json`

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Modify: `tests/plugin-manifest.test.sh` (extend to validate marketplace)

- [ ] **Step 1: Extend the test**

Append to `tests/plugin-manifest.test.sh`:

```bash
MARKETPLACE=".claude-plugin/marketplace.json"

[ -f "$MARKETPLACE" ] || { echo "FAIL: $MARKETPLACE missing"; exit 1; }

jq -e '.name == "searchatlas"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace name wrong"; exit 1; }

jq -e '.plugins[0].name == "searchatlas-toolkit"' "$MARKETPLACE" >/dev/null \
  || { echo "FAIL: marketplace plugin name wrong"; exit 1; }

echo "PASS: marketplace manifest valid"
```

- [ ] **Step 2: Run test, confirm fail**

```bash
bash tests/plugin-manifest.test.sh
```
Expected: `FAIL: .claude-plugin/marketplace.json missing`

- [ ] **Step 3: Create the marketplace manifest**

Write `.claude-plugin/marketplace.json`:

```json
{
  "name": "searchatlas",
  "owner": {
    "name": "SearchAtlas",
    "email": "support@searchatlas.com"
  },
  "plugins": [
    {
      "name": "searchatlas-toolkit",
      "description": "Official SearchAtlas command-line toolkit — SEO, GBP, PPC, content, and AI visibility workflows.",
      "source": ".",
      "category": "marketing"
    }
  ]
}
```

**Schema notes (verified Task 0):**
- Owner accepts `name` (required) and `email` (optional). `url` is not a recognized owner field — drop it.
- `source: "."` is the canonical form for "this plugin lives in the same repo as the marketplace manifest"
- Plugin entry recognizes: `name`, `source`, `description`, `version`, `author`, `category`, `tags`, `strict`

- [ ] **Step 4: Run test, confirm pass**

```bash
bash tests/plugin-manifest.test.sh
```
Expected: both PASS lines

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json tests/plugin-manifest.test.sh
git commit -m "feat(plugin): add marketplace.json — single-entry self-hosted marketplace"
```

---

## Task 3: Create Empty `skills/` and `agents/` Directories

**Files:**
- Create: `skills/.gitkeep`
- Create: `agents/.gitkeep`

- [ ] **Step 1: Create directories**

```bash
mkdir -p skills agents
touch skills/.gitkeep agents/.gitkeep
```

- [ ] **Step 2: Verify**

```bash
[ -d skills ] && [ -d agents ] && [ -f skills/.gitkeep ] && [ -f agents/.gitkeep ] \
  && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/.gitkeep agents/.gitkeep
git commit -m "feat(plugin): reserve skills/ and agents/ directories for future expansion"
```

---

## Task 4: Convert First Command (`scout` → `sa-scout`) — Canonical Pattern

**Why this task is special:** This task establishes the conversion pattern that Tasks 5–24 follow. Done carefully, the rest are mechanical.

**Files:**
- Create: `commands/sa-scout.md`
- Delete: `commands/essentials/scout.md` (only after sa-scout.md is verified)
- Create: `tests/command-conversion.test.sh`

- [ ] **Step 1: Inspect the source command**

```bash
cat commands/essentials/scout.md | head -40
```

Note the existing frontmatter (if any) and the body. Look specifically for:
- Any `AMM_ROOT=$(git rev-parse...)` pattern (must be replaced)
- Any `clients/{slug}/...` path references (must be replaced)
- Hardcoded paths or `~/.amm/` references (must be replaced)
- Any reference to `/scout`, `/business-report`, etc. that need updating to `sa-` prefix

- [ ] **Step 2: Write the conversion verification test**

Create `tests/command-conversion.test.sh`:

```bash
#!/bin/bash
set -e
# Verify sa-* command file: exists, has correct frontmatter,
# uses CLAUDE_PLUGIN_ROOT not AMM_ROOT, uses SA_CLIENTS_DIR not bare clients/.

NAME="$1"
FILE="commands/sa-${NAME}.md"

[ -f "$FILE" ] || { echo "FAIL: $FILE missing"; exit 1; }

# Frontmatter has name field
head -10 "$FILE" | grep -q "^name: sa-${NAME}$" \
  || { echo "FAIL: frontmatter name field missing or wrong"; exit 1; }

# Frontmatter has description
head -10 "$FILE" | grep -q "^description: " \
  || { echo "FAIL: frontmatter description missing"; exit 1; }

# No AMM_ROOT references in body
grep -q "AMM_ROOT" "$FILE" \
  && { echo "FAIL: AMM_ROOT still present (should be CLAUDE_PLUGIN_ROOT)"; exit 1; }

# No git-rev-parse path resolution
grep -q "git rev-parse --show-toplevel" "$FILE" \
  && { echo "FAIL: git rev-parse path resolution still present"; exit 1; }

# No bare clients/ references (must use SA_CLIENTS_DIR)
grep -E "^[^#]*\b(cd |mkdir |touch |cat ).*clients/" "$FILE" \
  && { echo "FAIL: bare clients/ path reference (should use SA_CLIENTS_DIR)"; exit 1; }

# Command name references updated to sa- prefix where present
grep -E "^[^#]*\b/(scout|business-report|run-seo|run-gbp|run-ppc|run-content|run-pr|run-visibility|my-account|onboard-client|sync-client|summit-shot|help|send-slack|send-discord|send-email|send-circle|setup-integrations|build-website|rebuild-website|security-scan)\b" "$FILE" \
  && { echo "FAIL: unprefixed command reference found (should be /sa-*)"; exit 1; }

echo "PASS: commands/sa-${NAME}.md converted correctly"
```

Make executable: `chmod +x tests/command-conversion.test.sh`

- [ ] **Step 3: Run test, confirm fail**

```bash
bash tests/command-conversion.test.sh scout
```
Expected: `FAIL: commands/sa-scout.md missing`

- [ ] **Step 4: Create `commands/sa-scout.md`**

Read `commands/essentials/scout.md` end-to-end. Create `commands/sa-scout.md` with:

a. Frontmatter at top:
```markdown
---
name: sa-scout
description: Read-only diagnostic across SEO, GBP, PPC, content, and AI visibility. Uses SearchAtlas's holistic SEO scoring, Site Explorer, GBP audit, and AI visibility tools to give you a full picture and prioritized actions. Creates a SearchAtlas Report Builder report and saves a local HTML record.
---
```

b. Body: copy from source `commands/essentials/scout.md`, applying these substitutions globally:

| Find | Replace |
|---|---|
| `AMM_ROOT=$(git rev-parse --show-toplevel 2>/dev/null \|\| pwd)` | `SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"` |
| `$AMM_ROOT/clients/` | `$SA_CLIENTS_DIR/` |
| `$AMM_ROOT` (other references) | `$CLAUDE_PLUGIN_ROOT` (for plugin assets — workflows, integrations) |
| `clients/{slug}/` (bare) | `$SA_CLIENTS_DIR/{slug}/` |
| `/scout` | `/sa-scout` |
| `/business-report` | `/sa-business-report` |
| `/run-seo` | `/sa-run-seo` |
| `/run-gbp` | `/sa-run-gbp` |
| `/run-ppc` | `/sa-run-ppc` |
| `/run-content` | `/sa-run-content` |
| `/run-pr` | `/sa-run-pr` |
| `/run-visibility` | `/sa-run-visibility` |
| `/my-account` | `/sa-my-account` |
| `/onboard-client` | `/sa-onboard-client` |
| `/sync-client` | `/sa-sync-client` |
| `/summit-shot` | `/sa-summit-shot` |
| `/help` | `/sa-help` |
| `/send-slack` | `/sa-send-slack` |
| `/send-discord` | `/sa-send-discord` |
| `/send-email` | `/sa-send-email` |
| `/send-circle` | `/sa-send-circle` |
| `/setup-integrations` | `/sa-setup-integrations` |
| `/build-website` | `/sa-build-website` |
| `/rebuild-website` | `/sa-rebuild-website` |
| `/security-scan` | `/sa-security-scan` |

c. Additionally: scout writes to a SUBFOLDER (per spec §8). Update its output line(s) to write to `$SA_CLIENTS_DIR/$slug/scouts/{date}.html` (creating the `scouts/` subdir with `mkdir -p` first).

- [ ] **Step 5: Run conversion test, confirm pass**

```bash
bash tests/command-conversion.test.sh scout
```
Expected: `PASS: commands/sa-scout.md converted correctly`

- [ ] **Step 6: Delete original**

```bash
git rm commands/essentials/scout.md
```

- [ ] **Step 7: Commit**

```bash
git add commands/sa-scout.md tests/command-conversion.test.sh
git commit -m "feat(plugin): convert /scout to /sa-scout with plugin-style paths"
```

---

## Tasks 5–24: Convert Remaining 20 Commands

Apply the same pattern as Task 4 to each of the remaining commands. Each follows the identical 4 steps:

1. Read source `commands/{name}.md`
2. Create `commands/sa-{name}.md` with frontmatter (name=`sa-{name}`, description rewritten to name the SearchAtlas capabilities it uses) and body with the find/replace substitutions from Task 4 Step 4b
3. Apply subfolder-output rule from spec §8 where applicable (see table below)
4. Run `bash tests/command-conversion.test.sh {name}`, expect PASS
5. `git rm commands/{name}.md`
6. Commit with message `feat(plugin): convert /{name} to /sa-{name}`

**Subfolder-output mapping** (commands that produce accumulating artifacts must write into a subfolder):

| Command | Subfolder under `$SA_CLIENTS_DIR/$slug/` |
|---|---|
| `sa-scout` (Task 4, already done) | `scouts/` |
| `sa-business-report` | `reports/` |
| `sa-run-seo` | `workflows/` (filename prefix `seo-`) |
| `sa-run-gbp` | `workflows/` (filename prefix `gbp-`) |
| `sa-run-ppc` | `workflows/` (filename prefix `ppc-`) |
| `sa-run-content` | `workflows/` (filename prefix `content-`) |
| `sa-run-pr` | `workflows/` (filename prefix `pr-`) |
| `sa-run-visibility` | `workflows/` (filename prefix `visibility-`) |
| `sa-summit-shot` | `shots/` (filename prefix `play-{NN}-`) |
| All others | Top level (canonical files — `brand-profile.md`, `notes.md`) or no file output |

### Task 5: `business-report` → `sa-business-report`
- [ ] Step 1: Read `commands/essentials/business-report.md`
- [ ] Step 2: Create `commands/sa-business-report.md` (frontmatter: description should name SA capabilities — OTTO project data, brand vault, Site Explorer, GBP, PPC, LLM visibility — and reports/ subfolder output)
- [ ] Step 3: Run `bash tests/command-conversion.test.sh business-report` → PASS
- [ ] Step 4: `git rm commands/essentials/business-report.md`
- [ ] Step 5: Commit `feat(plugin): convert /business-report to /sa-business-report`

### Task 6: `my-account` → `sa-my-account`
- [ ] Step 1: Read `commands/essentials/my-account.md`
- [ ] Step 2: Create `commands/sa-my-account.md` (description: pulls all OTTO projects, brand vaults, GBP locations, PPC campaigns, content, LLM visibility — overview of everything user has in SearchAtlas)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/essentials/my-account.md`
- [ ] Step 5: Commit `feat(plugin): convert /my-account to /sa-my-account`

### Task 7: `help` → `sa-help`
- [ ] Step 1: Read `commands/essentials/help.md`
- [ ] Step 2: Create `commands/sa-help.md`. The command list MUST list all 21 `sa-*` commands with one-line descriptions emphasizing the SA capability each one uses. Also document the `migrate-data` subcommand (used by users without a cloned repo who need to relocate legacy data — see Task 27 for what that script does).
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/essentials/help.md`
- [ ] Step 5: Commit `feat(plugin): convert /help to /sa-help with full plugin surface`

### Task 8: `onboard-client` → `sa-onboard-client`
- [ ] Step 1: Read `commands/clients/onboard-client.md`
- [ ] Step 2: Create `commands/sa-onboard-client.md` (description: guided wizard — pulls SearchAtlas brand vault if it exists, or builds one from manual input). Writes `brand-profile.md` at top level of `$SA_CLIENTS_DIR/$slug/`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/clients/onboard-client.md`
- [ ] Step 5: Commit `feat(plugin): convert /onboard-client to /sa-onboard-client`

### Task 9: `sync-client` → `sa-sync-client`
- [ ] Step 1: Read `commands/clients/sync-client.md`
- [ ] Step 2: Create `commands/sa-sync-client.md` (description: two-way sync between local `brand-profile.md` and SearchAtlas brand vault — push local changes, pull remote updates)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/clients/sync-client.md`
- [ ] Step 5: Commit `feat(plugin): convert /sync-client to /sa-sync-client`

### Task 10: `summit-shot` → `sa-summit-shot`
- [ ] Step 1: Read `commands/clients/summit-shot.md`
- [ ] Step 2: Create `commands/sa-summit-shot.md` (description: atomic single-play executor — 19 plays from the May Summit, bounded by default to 1 article / 1 PR drafts). Writes to `$SA_CLIENTS_DIR/$slug/shots/play-{NN}-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/clients/summit-shot.md`
- [ ] Step 5: Commit `feat(plugin): convert /summit-shot to /sa-summit-shot`

### Task 11: `run-seo` → `sa-run-seo`
- [ ] Step 1: Read `commands/workflows/run-seo.md`
- [ ] Step 2: Create `commands/sa-run-seo.md` (description: monthly SEO workflow — holistic audit, OTTO recommendations, content health, indexing, keyword tracking). Writes log to `$SA_CLIENTS_DIR/$slug/workflows/seo-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-seo.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-seo to /sa-run-seo`

### Task 12: `run-gbp` → `sa-run-gbp`
- [ ] Step 1: Read `commands/workflows/run-gbp.md`
- [ ] Step 2: Create `commands/sa-run-gbp.md` (description: GBP optimization — location audit, posts, reviews automation, citations, photo management). Log to `workflows/gbp-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-gbp.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-gbp to /sa-run-gbp`

### Task 13: `run-ppc` → `sa-run-ppc`
- [ ] Step 1: Read `commands/workflows/run-ppc.md`
- [ ] Step 2: Create `commands/sa-run-ppc.md` (description: PPC campaign setup/maintenance — Google Ads sync, keyword clusters, ad generation, performance review). Log to `workflows/ppc-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-ppc.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-ppc to /sa-run-ppc`

### Task 14: `run-content` → `sa-run-content`
- [ ] Step 1: Read `commands/workflows/run-content.md`
- [ ] Step 2: Create `commands/sa-run-content.md` (description: content generation pipeline — topical maps, article drafting, brand-vault-driven voice, publication scheduling). Log to `workflows/content-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-content.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-content to /sa-run-content`

### Task 15: `run-pr` → `sa-run-pr`
- [ ] Step 1: Read `commands/workflows/run-pr.md`
- [ ] Step 2: Create `commands/sa-run-pr.md` (description: authority building — press release drafting and distribution via SearchAtlas Press platform). Log to `workflows/pr-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-pr.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-pr to /sa-run-pr`

### Task 16: `run-visibility` → `sa-run-visibility`
- [ ] Step 1: Read `commands/workflows/run-visibility.md`
- [ ] Step 2: Create `commands/sa-run-visibility.md` (description: AI visibility audit — brand mentions across ChatGPT, Claude, Gemini, Perplexity; sentiment, share of voice, citation tracking). Log to `workflows/visibility-{date}.md`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/workflows/run-visibility.md`
- [ ] Step 5: Commit `feat(plugin): convert /run-visibility to /sa-run-visibility`

### Task 17: `send-slack` → `sa-send-slack`
- [ ] Step 1: Read `commands/sharing/send-slack.md`
- [ ] Step 2: Create `commands/sa-send-slack.md` (description: post results to Slack via Incoming Webhooks; supports multiple named channels via `SLACK_WEBHOOK_{NAME}` env vars). No subfolder output.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/sharing/send-slack.md`
- [ ] Step 5: Commit `feat(plugin): convert /send-slack to /sa-send-slack`

### Task 18: `send-discord` → `sa-send-discord`
- [ ] Step 1: Read `commands/sharing/send-discord.md`
- [ ] Step 2: Create `commands/sa-send-discord.md` (description: post results to Discord via webhook)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/sharing/send-discord.md`
- [ ] Step 5: Commit `feat(plugin): convert /send-discord to /sa-send-discord`

### Task 19: `send-email` → `sa-send-email`
- [ ] Step 1: Read `commands/sharing/send-email.md`
- [ ] Step 2: Create `commands/sa-send-email.md` (description: email results via Resend API)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/sharing/send-email.md`
- [ ] Step 5: Commit `feat(plugin): convert /send-email to /sa-send-email`

### Task 20: `send-circle` → `sa-send-circle`
- [ ] Step 1: Read `commands/sharing/send-circle.md`
- [ ] Step 2: Create `commands/sa-send-circle.md` (description: post to Circle space via API v2)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/sharing/send-circle.md`
- [ ] Step 5: Commit `feat(plugin): convert /send-circle to /sa-send-circle`

### Task 21: `setup-integrations` → `sa-setup-integrations`
- [ ] Step 1: Read `commands/advanced/setup-integrations.md`
- [ ] Step 2: Create `commands/sa-setup-integrations.md` (description: configure Slack, Discord, Email, Circle integrations — guides through `.env` setup)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/advanced/setup-integrations.md`
- [ ] Step 5: Commit `feat(plugin): convert /setup-integrations to /sa-setup-integrations`

### Task 22: `build-website` → `sa-build-website`
- [ ] Step 1: Read `commands/advanced/build-website.md`
- [ ] Step 2: Create `commands/sa-build-website.md` (description: generate marketing site from brand vault data). Important: this command historically interacted with `mission-control/tools/website-build/` which has been DELETED in the precondition refactor — verify the command body no longer references those paths, or rewrite to use only SA Content Genius / WS tools via MCP.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/advanced/build-website.md`
- [ ] Step 5: Commit `feat(plugin): convert /build-website to /sa-build-website`

### Task 23: `rebuild-website` → `sa-rebuild-website`
- [ ] Step 1: Read `commands/advanced/rebuild-website.md`
- [ ] Step 2: Create `commands/sa-rebuild-website.md` (similar caveat as Task 22 re: deleted `mission-control/tools/website-rebuild/`)
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/advanced/rebuild-website.md`
- [ ] Step 5: Commit `feat(plugin): convert /rebuild-website to /sa-rebuild-website`

### Task 24: `security-scan` → `sa-security-scan`
- [ ] Step 1: Read `commands/advanced/security-scan.md`
- [ ] Step 2: Create `commands/sa-security-scan.md` (description: scan the user's local toolkit setup for exposed secrets, misconfigured webhooks, etc.). Calls `Scripts/repo-security-scan.sh`.
- [ ] Step 3: Test passes
- [ ] Step 4: `git rm commands/advanced/security-scan.md`
- [ ] Step 5: Commit `feat(plugin): convert /security-scan to /sa-security-scan`

---

### Task 24.5: Remove Empty Tiered Subdirectories

**Files:**
- Delete: `commands/essentials/`, `commands/advanced/`, `commands/clients/`, `commands/sharing/`, `commands/workflows/` (all now empty after Tasks 4-24)

- [ ] **Step 1: Verify all subdirs are empty**

```bash
for dir in commands/essentials commands/advanced commands/clients commands/sharing commands/workflows; do
  if [ -n "$(ls -A "$dir" 2>/dev/null)" ]; then
    echo "FAIL: $dir is not empty:"; ls -A "$dir"; exit 1
  fi
done
echo "PASS: all tiered subdirs empty"
```
Expected: `PASS: all tiered subdirs empty`. If any subdir still has files, a command conversion was missed — investigate before proceeding.

- [ ] **Step 2: Remove the empty subdirs**

```bash
rmdir commands/essentials commands/advanced commands/clients commands/sharing commands/workflows
```

- [ ] **Step 3: Verify commands/ is now flat (only sa-*.md files)**

```bash
ls commands/ | head -25
```
Expected: 21 `sa-*.md` files, no subdirectories.

- [ ] **Step 4: Commit**

```bash
git add -A commands/
git commit -m "chore(plugin): remove now-empty tiered command subdirectories"
```

---

## Task 25: Create `hooks/hooks.json` and `hooks/ensure-env.sh`

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/ensure-env.sh`
- Create: `tests/hook.test.sh`

- [ ] **Step 1: Write the hook test**

Create `tests/hook.test.sh`:

```bash
#!/bin/bash
set -e
# Hook script must: exit 0 always, be idempotent, create SA_CLIENTS_DIR

HOOK="hooks/ensure-env.sh"
[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable"; exit 1; }

# Test 1: shellcheck
command -v shellcheck >/dev/null && {
  shellcheck "$HOOK" || { echo "FAIL: shellcheck errors"; exit 1; }
}

# Test 2: hook creates SA_CLIENTS_DIR
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" SA_CLIENTS_DIR="$TMPDIR_TEST/.searchatlas/clients" bash "$HOOK" >/dev/null
[ -d "$TMPDIR_TEST/.searchatlas/clients" ] \
  || { echo "FAIL: hook did not create SA_CLIENTS_DIR"; rm -rf "$TMPDIR_TEST"; exit 1; }
rm -rf "$TMPDIR_TEST"

# Test 3: hook exits 0 even when claude CLI is missing
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" PATH="/usr/bin:/bin" bash "$HOOK" >/dev/null
[ $? -eq 0 ] || { echo "FAIL: hook did not exit 0 with missing claude CLI"; exit 1; }
rm -rf "$TMPDIR_TEST"

# Test 4: hook is idempotent
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" bash "$HOOK" >/dev/null
HOME="$TMPDIR_TEST" bash "$HOOK" >/dev/null  # Second run must also succeed
[ $? -eq 0 ] || { echo "FAIL: hook not idempotent"; exit 1; }
rm -rf "$TMPDIR_TEST"

echo "PASS: hook script behaves correctly"
```

Make executable: `chmod +x tests/hook.test.sh`

- [ ] **Step 2: Run test, confirm fail**

```bash
bash tests/hook.test.sh
```
Expected: `FAIL: hooks/ensure-env.sh not executable`

- [ ] **Step 3: Create hooks/ensure-env.sh**

```bash
mkdir -p hooks
```

Write `hooks/ensure-env.sh`:

```bash
#!/bin/bash
# SearchAtlas Toolkit — SessionStart hook
# Three jobs: ensure client data dir, detect legacy data, check MCP auth.
# Always exit 0 — hooks must not block session start.

set +e  # don't propagate failures

# 1. Ensure client data home exists
SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"
mkdir -p "$SA_CLIENTS_DIR" 2>/dev/null

# 2. Detect legacy ~/.amm/clients and nudge toward migration
if [ -d "$HOME/.amm/clients" ] && [ -z "$(ls -A "$SA_CLIENTS_DIR" 2>/dev/null)" ]; then
  echo "📦 Found legacy ~/.amm/clients/ — run /sa-help migrate-data to move it."
fi

# 3. Verify SearchAtlas MCP is registered (best-effort, never hard-fail)
if command -v claude >/dev/null 2>&1; then
  if ! claude mcp list 2>/dev/null | grep -q "searchatlas"; then
    echo "⚠️  SearchAtlas MCP not registered. Plugin commands will fail until it is."
    echo "   This usually self-heals when the plugin loads — restart Claude Code if needed."
  fi
fi

exit 0
```

Make executable: `chmod +x hooks/ensure-env.sh`

- [ ] **Step 4: Create hooks/hooks.json**

Write `hooks/hooks.json`:

```json
{
  "hooks": [
    {
      "type": "SessionStart",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/ensure-env.sh",
      "timeout_ms": 2000
    }
  ]
}
```

- [ ] **Step 5: Run test, confirm pass**

```bash
bash tests/hook.test.sh
```
Expected: `PASS: hook script behaves correctly`

- [ ] **Step 6: Commit**

```bash
git add hooks/ tests/hook.test.sh
git commit -m "feat(plugin): SessionStart hook for env + MCP auth check"
```

---

## Task 26: Create `AGENTS.md` (Plugin-Scoped Instructions)

**Files:**
- Create: `AGENTS.md`
- Modify: `CLAUDE.md` (slim to a pointer)

- [ ] **Step 1: Read current CLAUDE.md fully**

```bash
cat CLAUDE.md
```

Note all 10 sections — this is the source material for AGENTS.md.

- [ ] **Step 2: Create AGENTS.md**

Write `AGENTS.md` mirroring CLAUDE.md's structure with these specific changes:

a. **Section 1** — reframe from "for digital marketing agencies" to "for anyone using SearchAtlas for SEO, GBP, PPC, content, and AI visibility"
b. **Section 2** — unchanged (MCP endpoint, OAuth, install)
c. **Section 3** — Golden Rules unchanged EXCEPT:
   - Rule 7: replace `AMM_ROOT=$(git rev-parse...)` guidance with `CLAUDE_PLUGIN_ROOT` (plugin assets) + `SA_CLIENTS_DIR` (user data, defaulting to `~/.searchatlas/clients`)
   - Rule 8: update path from `clients/` (in-repo) to `~/.searchatlas/clients/`
d. **Section 4** — Parameter Quick Reference unchanged
e. **Section 5** — Account Discovery unchanged
f. **Section 6** — Intent Routing: every command reference updated from `/scout` → `/sa-scout`, `/business-report` → `/sa-business-report`, etc. (apply Task 4 Step 4b substitution table). Also: add "set up a new project / brand / your own site" phrasings alongside "set up a new client" so non-agency users see themselves.
g. **Section 7** — Workflow Execution Pattern unchanged
h. **Section 8** — replace "Slash Commands" table with the full 21-command plugin surface (`sa-*` names + one-line SA-capability-naming descriptions)
i. **Section 9** — Communication Integrations unchanged
j. **Section 10** — Conventions unchanged

- [ ] **Step 3: Slim CLAUDE.md to a pointer**

Replace `CLAUDE.md` entire contents with:

```markdown
# CLAUDE.md

This repo ships as a Claude Code plugin. Plugin-scoped instructions for
Claude live in `AGENTS.md` and are loaded automatically when the
SearchAtlas Toolkit plugin is active.

For contributors working on the toolkit itself:
- `AGENTS.md` — instructions Claude uses when running plugin commands
- `docs/superpowers/specs/2026-05-26-searchatlas-toolkit-plugin-design.md` — design rationale
- `docs/superpowers/plans/2026-05-26-searchatlas-toolkit-plugin.md` — implementation plan
```

- [ ] **Step 4: Verify AGENTS.md has no stale command references**

```bash
# Confirm no unprefixed command references remain
grep -E "\B/(scout|business-report|run-seo|run-gbp|run-ppc|run-content|run-pr|run-visibility|my-account|onboard-client|sync-client|summit-shot|help|send-slack|send-discord|send-email|send-circle|setup-integrations|build-website|rebuild-website|security-scan)\b" AGENTS.md \
  && { echo "FAIL: unprefixed command reference in AGENTS.md"; exit 1; } \
  || echo "PASS: all command references use sa- prefix"
```
Expected: `PASS: all command references use sa- prefix`

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "feat(plugin): add AGENTS.md with plugin-scoped instructions, slim CLAUDE.md to pointer"
```

---

## Task 27: Create Migration Script (`scripts/migrate-to-plugin.sh`)

**Files:**
- Create: `scripts/migrate-to-plugin.sh`
- Create: `tests/migrate.test.sh`

- [ ] **Step 1: Write migration script tests**

Create `tests/migrate.test.sh`:

```bash
#!/bin/bash
set -e
# Test the migration script in a sandboxed environment.
# We do NOT run the real migration on the developer's machine —
# we set up a fake home + fake cloned repo and run against those.

SCRIPT="scripts/migrate-to-plugin.sh"
[ -f "$SCRIPT" ] || { echo "FAIL: $SCRIPT missing"; exit 1; }

# Sandbox setup
SANDBOX=$(mktemp -d)
FAKE_HOME="$SANDBOX/home"
FAKE_REPO="$SANDBOX/toolkit-public"
mkdir -p "$FAKE_HOME/.claude/commands"
mkdir -p "$FAKE_REPO/clients/acme-co"
mkdir -p "$FAKE_REPO/scripts"
echo '# fake brand profile' > "$FAKE_REPO/clients/acme-co/brand-profile.md"
echo '# fake scout' > "$FAKE_REPO/clients/acme-co/scout-2026-05-20.html"
# Simulate legacy commands installed by old setup.sh
for cmd in scout business-report help my-account onboard-client sync-client summit-shot \
           run-seo run-gbp run-ppc run-content run-pr run-visibility \
           send-slack send-discord send-email send-circle \
           setup-integrations build-website rebuild-website security-scan; do
  echo "# legacy $cmd" > "$FAKE_HOME/.claude/commands/$cmd.md"
done
# Simulate settings.json with auto-update hook
cat > "$FAKE_HOME/.claude/settings.json" <<'EOF'
{
  "hooks": [
    {
      "type": "SessionStart",
      "command": "/path/to/toolkit-public/Scripts/auto-update-hook.sh"
    }
  ]
}
EOF
# Copy the migration script
cp "$SCRIPT" "$FAKE_REPO/scripts/migrate-to-plugin.sh"
chmod +x "$FAKE_REPO/scripts/migrate-to-plugin.sh"

# Run migration with sandbox HOME
HOME="$FAKE_HOME" SA_TOOLKIT_TEST_MODE=1 bash "$FAKE_REPO/scripts/migrate-to-plugin.sh" >/dev/null 2>&1

# Assertion 1: client data moved
[ -f "$FAKE_HOME/.searchatlas/clients/acme-co/brand-profile.md" ] \
  || { echo "FAIL: brand-profile.md not moved"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 2: scout HTML moved into scouts/ subfolder
[ -f "$FAKE_HOME/.searchatlas/clients/acme-co/scouts/scout-2026-05-20.html" ] \
  || { echo "FAIL: scout HTML not reshaped into scouts/ subfolder"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 3: legacy commands removed
for cmd in scout business-report help my-account; do
  [ ! -f "$FAKE_HOME/.claude/commands/$cmd.md" ] \
    || { echo "FAIL: legacy $cmd.md not removed"; rm -rf "$SANDBOX"; exit 1; }
done

# Assertion 4: auto-update hook removed from settings.json
jq -e '.hooks // [] | map(select(.command | tostring | contains("auto-update-hook"))) | length == 0' \
  "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: auto-update hook still in settings.json"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 5: extraKnownMarketplaces.searchatlas added (object, keyed by marketplace name)
jq -e '.extraKnownMarketplaces.searchatlas.source.repo == "search-atlas-group/amm-toolkit"' \
  "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: extraKnownMarketplaces.searchatlas not set correctly"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 6: enabledPlugins["searchatlas-toolkit@searchatlas"] is true
jq -e '.enabledPlugins["searchatlas-toolkit@searchatlas"] == true' \
  "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: searchatlas-toolkit@searchatlas not enabled"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 7: re-running is idempotent (does not corrupt state)
HOME="$FAKE_HOME" SA_TOOLKIT_TEST_MODE=1 bash "$FAKE_REPO/scripts/migrate-to-plugin.sh" >/dev/null 2>&1
jq -e '.enabledPlugins | length == 1' "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: re-running corrupted enabledPlugins"; rm -rf "$SANDBOX"; exit 1; }

rm -rf "$SANDBOX"
echo "PASS: migration script behaves correctly"
```

Make executable: `chmod +x tests/migrate.test.sh`

- [ ] **Step 2: Run test, confirm fail**

```bash
bash tests/migrate.test.sh
```
Expected: `FAIL: scripts/migrate-to-plugin.sh missing`

- [ ] **Step 3: Create the migration script**

```bash
mkdir -p scripts
```

Write `scripts/migrate-to-plugin.sh`:

```bash
#!/bin/bash
# SearchAtlas Toolkit — one-shot migration from cloned-repo install to plugin.
#
# What this does:
#   1. Pull latest repo (so script and manifest are current)
#   2. Move client data from <repo>/clients/ to ~/.searchatlas/clients/
#      with subfolder reshaping (scouts/, reports/, workflows/, shots/)
#   3. Remove legacy slash commands installed by the old setup.sh
#   4. Remove the legacy SessionStart auto-update hook from settings.json
#   5. Add extraKnownMarketplaces + enabledPlugins to settings.json
#
# Idempotent: safe to re-run. Test mode: SA_TOOLKIT_TEST_MODE=1 skips git pull
# and skips interactive prompts.

set -e

# ---------- Setup ----------
SA_CLIENTS_DIR="${SA_CLIENTS_DIR:-$HOME/.searchatlas/clients}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
COMMANDS_DIR="$CLAUDE_DIR/commands"
SETTINGS="$CLAUDE_DIR/settings.json"

TEST_MODE="${SA_TOOLKIT_TEST_MODE:-0}"

echo "📦 SearchAtlas Toolkit migration"
echo "  Source repo:  $REPO_DIR"
echo "  Client data:  $SA_CLIENTS_DIR"
echo

# ---------- Step 1: git pull (skip in test mode) ----------
if [ "$TEST_MODE" != "1" ] && [ -d "$REPO_DIR/.git" ]; then
  echo "→ Pulling latest from origin..."
  (cd "$REPO_DIR" && git pull --ff-only) || {
    echo "⚠️  git pull failed — continuing with current repo state."
  }
fi

# ---------- Step 2: Move client data ----------
if [ -d "$REPO_DIR/clients" ]; then
  echo "→ Moving client data to $SA_CLIENTS_DIR..."
  mkdir -p "$SA_CLIENTS_DIR"

  for client_dir in "$REPO_DIR/clients"/*/; do
    [ -d "$client_dir" ] || continue
    slug=$(basename "$client_dir")
    target="$SA_CLIENTS_DIR/$slug"
    mkdir -p "$target"

    # Move top-level canonical files
    for f in brand-profile.md notes.md; do
      [ -f "$client_dir/$f" ] && [ ! -f "$target/$f" ] && mv "$client_dir/$f" "$target/$f"
    done

    # Reshape accumulating artifacts into subfolders
    mkdir -p "$target/scouts" "$target/reports" "$target/workflows" "$target/shots"
    for f in "$client_dir"scout-*.html "$client_dir"scout-*.md; do
      [ -f "$f" ] || continue
      [ -f "$target/scouts/$(basename "$f")" ] || mv "$f" "$target/scouts/"
    done
    for f in "$client_dir"business-report-*.md "$client_dir"report-*.md; do
      [ -f "$f" ] || continue
      [ -f "$target/reports/$(basename "$f")" ] || mv "$f" "$target/reports/"
    done

    # Move anything left at top level into a "legacy/" folder so nothing is lost
    mkdir -p "$target/legacy"
    for f in "$client_dir"*; do
      [ -e "$f" ] || continue
      [ -d "$f" ] && continue  # subdirectories handled below
      [ -f "$target/legacy/$(basename "$f")" ] || mv "$f" "$target/legacy/" 2>/dev/null || true
    done

    # Move pre-existing subdirectories (reports/, scouts/, etc.) if they exist
    for sub in scouts reports workflows shots; do
      if [ -d "$client_dir/$sub" ]; then
        for f in "$client_dir/$sub"/*; do
          [ -f "$f" ] || continue
          [ -f "$target/$sub/$(basename "$f")" ] || mv "$f" "$target/$sub/" 2>/dev/null || true
        done
      fi
    done

    # Remove empty source dir
    rmdir "$client_dir" 2>/dev/null || true
  done
fi

# ---------- Step 3: Remove legacy slash commands ----------
echo "→ Removing legacy slash commands from $COMMANDS_DIR..."
LEGACY_COMMANDS=(
  scout business-report help my-account onboard-client sync-client summit-shot
  run-seo run-gbp run-ppc run-content run-pr run-visibility
  send-slack send-discord send-email send-circle
  setup-integrations build-website rebuild-website security-scan
)
for cmd in "${LEGACY_COMMANDS[@]}"; do
  [ -f "$COMMANDS_DIR/$cmd.md" ] && rm "$COMMANDS_DIR/$cmd.md"
done

# ---------- Step 4: Remove legacy auto-update hook from settings.json ----------
if [ -f "$SETTINGS" ]; then
  echo "→ Removing legacy auto-update hook from settings.json..."
  TMP=$(mktemp)
  jq '
    if .hooks then
      .hooks |= map(select(
        (.command // "" | tostring | contains("auto-update-hook")) | not
      ))
    else . end
    | if (.hooks // []) | length == 0 then del(.hooks) else . end
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
fi

# ---------- Step 5: Add extraKnownMarketplaces + enabledPlugins ----------
# Schema (per Task 0 verification):
#   extraKnownMarketplaces is an OBJECT, keyed by marketplace name:
#     { "searchatlas": { "source": { "source": "github", "repo": "..." } } }
#   enabledPlugins is an OBJECT, keyed by "plugin-name@marketplace-name":
#     { "searchatlas-toolkit@searchatlas": true }
echo "→ Registering plugin in $SETTINGS..."
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
TMP=$(mktemp)
jq '
  .extraKnownMarketplaces = (
    (.extraKnownMarketplaces // {})
    + {
      "searchatlas": {
        "source": {
          "source": "github",
          "repo": "search-atlas-group/amm-toolkit"
        }
      }
    }
  )
  | .enabledPlugins = (
    (.enabledPlugins // {})
    + { "searchatlas-toolkit@searchatlas": true }
  )
' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"

# ---------- Done ----------
echo
echo "✅ Migration complete."
echo
echo "Next: open Claude Code. It will prompt you to install searchatlas-toolkit."
echo "After approval, all sa-* commands are available."
echo

if [ "$TEST_MODE" != "1" ]; then
  read -p "Delete the cloned $REPO_DIR/ now? (Keep it if you use mission-control) [y/N] " ans
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    if [ -d "$REPO_DIR/mission-control" ]; then
      echo "Keeping mission-control/ — moving it to $HOME/searchatlas-mission-control/"
      mv "$REPO_DIR/mission-control" "$HOME/searchatlas-mission-control"
    fi
    rm -rf "$REPO_DIR"
    echo "Cloned repo removed."
  fi
fi
```

Make executable: `chmod +x scripts/migrate-to-plugin.sh`

- [ ] **Step 4: Run test, confirm pass**

```bash
bash tests/migrate.test.sh
```
Expected: `PASS: migration script behaves correctly`

- [ ] **Step 5: shellcheck the script**

```bash
shellcheck scripts/migrate-to-plugin.sh
```
Expected: clean (no errors). Fix any warnings if they appear.

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-to-plugin.sh tests/migrate.test.sh
git commit -m "feat(plugin): one-shot migration script for existing CLI users"
```

---

## Task 28: Rewrite README.md (Code/Desktop Fork)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README.md**

```bash
cat README.md | head -80
```

Note the existing structure — keep what works, restructure the install section.

- [ ] **Step 2: Replace README.md with new structure**

Write `README.md`:

```markdown
# SearchAtlas Toolkit

> Official command-line toolkit for SearchAtlas — SEO, GBP, PPC, content, and AI visibility, all powered by the SearchAtlas MCP.

For anyone using SearchAtlas to manage SEO, Google Business Profiles, paid ads, content, or AI visibility — solo operators, in-house teams, and agencies alike.

---

## Quickstart

### Using Claude Code? 🟦

```
/plugin marketplace add search-atlas-group/amm-toolkit
/plugin install searchatlas-toolkit
```

That's it. First time you run an `sa-*` command, you'll be prompted to authorize SearchAtlas via OAuth (new to SearchAtlas? You'll be prompted to create a free account during auth).

### Using Claude Desktop or claude.ai? 🟪

Plugins are a Claude Code feature. But the underlying SearchAtlas MCP works in Desktop and on the web — add it as a custom connector:

```
https://mcp.searchatlas.com/mcp
```

You won't get the `sa-*` slash commands (those are Claude Code-only), but you'll get raw access to every SearchAtlas tool and can drive workflows by asking Claude in plain language.

---

## What You Get

21 slash commands covering the full SearchAtlas surface. Type `/sa-help` once installed for the live list, or browse below.

### Diagnostics & Reports
- `/sa-scout` — Read-only diagnostic across SEO, GBP, PPC, content, AI visibility
- `/sa-business-report` — Single-business deep dive
- `/sa-my-account` — Overview of all your SearchAtlas projects, brands, campaigns

### Onboarding & Brand Management
- `/sa-onboard-client` — Guided setup wizard
- `/sa-sync-client` — Two-way sync between local brand profile and SearchAtlas brand vault

### Marketing Workflows
- `/sa-run-seo` — Monthly SEO audit + recommendations
- `/sa-run-gbp` — GBP optimization workflow
- `/sa-run-ppc` — Google Ads setup and maintenance
- `/sa-run-content` — Content generation via SA Content Genius
- `/sa-run-pr` — Press release drafting + distribution
- `/sa-run-visibility` — AI visibility audit (ChatGPT, Claude, Gemini, Perplexity)
- `/sa-summit-shot` — Execute single high-impact plays from the SearchAtlas Summit playbook

### Sharing & Notifications
- `/sa-send-slack`, `/sa-send-discord`, `/sa-send-email`, `/sa-send-circle`

### Setup & Utilities
- `/sa-setup-integrations` — Configure Slack/Discord/Email/Circle webhooks
- `/sa-security-scan` — Scan local setup for exposed secrets
- `/sa-build-website`, `/sa-rebuild-website` — Marketing site generation
- `/sa-help` — Command reference

---

## Your Client Data

Per-client working files live at `~/.searchatlas/clients/{slug}/`:

```
~/.searchatlas/clients/acme-co/
├── brand-profile.md       # canonical client identity
├── notes.md               # freeform notes
├── scouts/                # /sa-scout reports
├── reports/               # /sa-business-report outputs
├── workflows/             # /sa-run-* logs
└── shots/                 # /sa-summit-shot executions
```

Want client data on a synced drive? Set `SA_CLIENTS_DIR=/path/to/your/folder` in your environment.

---

## Integrations (Optional)

The `/sa-send-*` commands need webhooks/keys. Configure once via `/sa-setup-integrations`, or manually in `~/.searchatlas/.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
RESEND_API_KEY=re_...
EMAIL_FROM=you@yourdomain.com
CIRCLE_API_KEY=...
```

---

## Migrating From the Cloned-Repo Toolkit

Already using the cloned-and-scripted version? One command:

```bash
cd /path/to/your/toolkit-public
./scripts/migrate-to-plugin.sh
```

It moves your client data, removes old commands, declares the plugin in your settings. Next time you open Claude Code, you'll get a one-click trust prompt to finish installing.

If you've already deleted the cloned repo, just run the standard install above — the plugin's first-run hook can detect orphaned client data and offer to relocate it.

---

## Companion: Mission Control

`mission-control/` (in this repo) is an optional local web dashboard for the toolkit. It runs alongside Claude Code and is not part of the plugin. See `mission-control/README.md` for setup.

---

## Troubleshooting

- **MCP not registered after install** → Restart Claude Code. The plugin's MCP declaration loads on next session start.
- **OAuth flow stuck** → Sign in at https://searchatlas.com first, then retry the command.
- **Commands write to wrong location** → Check `echo $SA_CLIENTS_DIR` — if set, it overrides the default.
- **Hook says "MCP not registered"** → Run `claude mcp list` to verify; if `searchatlas` isn't there, reinstall the plugin.

## Support

- Issues: https://github.com/search-atlas-group/amm-toolkit/issues
- SearchAtlas help: https://help.searchatlas.com
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): rewrite for plugin install + Code/Desktop fork"
```

---

## Task 29: Create CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write CHANGELOG.md**

```markdown
# Changelog

All notable changes to the SearchAtlas Toolkit plugin.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-26

### Added
- Plugin packaging — install via `/plugin install searchatlas-toolkit`
- SearchAtlas MCP server auto-registered on install (no separate `claude mcp add` step)
- 21 slash commands prefixed `sa-*` (e.g., `/sa-scout`, `/sa-run-seo`)
- Plugin-scoped instructions in `AGENTS.md` (intent routing, golden rules, parameter reference)
- SessionStart hook for client data dir creation and MCP auth check
- `scripts/migrate-to-plugin.sh` — one-shot migration for existing CLI users
- Reserved `skills/` and `agents/` directories for future expansion

### Changed
- Client data location moved from `<repo>/clients/` to `~/.searchatlas/clients/`
- Per-client artifacts organized into `scouts/`, `reports/`, `workflows/`, `shots/` subfolders
- Commands resolve plugin assets via `$CLAUDE_PLUGIN_ROOT` and client data via `$SA_CLIENTS_DIR`

### Removed
- `setup.sh` (replaced by `/plugin install`)
- SessionStart auto-update hook (plugins handle updates via `/plugin update`)
- `POWER-USER.md`, `docs/install.html`, `docs/welcome.html` (folded into README + AGENTS.md)
- `commands/README.md` (replaced by `AGENTS.md` § 8)

### Migration
Existing users on the cloned-repo install: run `./scripts/migrate-to-plugin.sh` from inside your clone. See README "Migrating from the cloned-repo toolkit."
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): initialize v1.0.0 plugin release notes"
```

---

## Task 30: Update Legacy Auto-Update Hook to Emit Migration Nudge

**Why:** Users still on the cloned-and-scripted install have an auto-update hook that runs at every session start, pulling latest. We piggyback on it: the next pull lands a hook update that prints a one-line nudge until migration completes.

**Files:**
- The legacy hook script lives outside this repo's plugin scope, but the hook script source is at `Scripts/auto-update-hook.sh` (per git history — commit `d569cf2`). Need to find where it currently lives.

- [ ] **Step 1: Locate the legacy hook script in repo history**

```bash
git show d569cf2 --stat
```

If `Scripts/auto-update-hook.sh` exists in the precondition state, modify it. If it was deleted in the precondition refactor (per git status `D Scripts/auto-update-hook.sh`), this task becomes simpler — we just SHIP a new replacement that emits the nudge.

- [ ] **Step 2: Create the nudge hook**

If the precondition has already deleted `Scripts/auto-update-hook.sh`, write a new one with ONLY the nudge content. This file is NOT part of the plugin — it lives in the repo so any user who still has a clone and runs `git pull` gets the updated nudge automatically.

Write `Scripts/auto-update-hook.sh`:

```bash
#!/bin/bash
# Legacy SessionStart hook — replaced by the plugin's own hook.
#
# This file remains here only to print a migration nudge to anyone
# who still has the cloned-repo install. Once they run
# scripts/migrate-to-plugin.sh, this hook is removed from settings.json
# and the nudge stops appearing.

REPO_DIR="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"

echo "📦 SearchAtlas Toolkit v2 available as a plugin."
echo "   Run: cd $REPO_DIR && ./scripts/migrate-to-plugin.sh"
echo "   (One shell command — moves data, installs plugin, cleans up.)"

exit 0
```

Make executable: `chmod +x Scripts/auto-update-hook.sh`

- [ ] **Step 3: Commit**

```bash
git add Scripts/auto-update-hook.sh
git commit -m "feat(migration): legacy hook now nudges users to migrate to plugin"
```

---

## Task 31: Final Local Install Verification

**Files:** none (verification-only task — no commits unless a fix is needed)

**Why:** Before tagging v1.0.0, install the plugin from the local repo and verify it loads, MCP registers, and at least one command runs.

- [ ] **Step 1: Install from local repo**

```bash
# Add the local repo as a marketplace for testing
claude --plugin-dir "$(pwd)" 2>&1 | head -5
```

Or, if the local marketplace flow isn't available, push the branch to a test GitHub fork and use:
```
/plugin marketplace add <your-fork>/amm-toolkit#<branch>
/plugin install searchatlas-toolkit
```

- [ ] **Step 2: Verify MCP registered**

In Claude Code:
```
claude mcp list
```
Expected output includes `searchatlas` with URL `https://mcp.searchatlas.com/mcp`.

- [ ] **Step 3: Verify a command loads**

In Claude Code, type `/sa-help`. Expected: command runs, displays the 21-command surface from `commands/sa-help.md`.

- [ ] **Step 4: Verify hook runs**

Restart Claude Code. On session start, the hook should:
- Create `~/.searchatlas/clients/` if missing
- Print nothing if MCP is registered (the hook is fail-open and only speaks when there's an issue)

```bash
ls ~/.searchatlas/clients/  # should exist after first session
```

- [ ] **Step 5: Run a real command end-to-end (smoke test)**

```
/sa-my-account
```

Expected: command discovers your SearchAtlas account, lists OTTO projects / brand vaults / etc. If OAuth flow triggers (first-time auth), complete it.

- [ ] **Step 6: If anything fails**

Diagnose, fix in the relevant earlier task, re-commit. Do NOT proceed to Task 32 until smoke test passes.

---

## Task 32: Tag Release v1.0.0

**Files:** none (git tag only)

- [ ] **Step 1: Run all tests one final time**

```bash
bash tests/plugin-manifest.test.sh
for cmd in scout business-report help my-account onboard-client sync-client summit-shot \
           run-seo run-gbp run-ppc run-content run-pr run-visibility \
           send-slack send-discord send-email send-circle \
           setup-integrations build-website rebuild-website security-scan; do
  bash tests/command-conversion.test.sh "$cmd" || { echo "FAIL on $cmd"; exit 1; }
done
bash tests/hook.test.sh
bash tests/migrate.test.sh
```

Expected: all PASS.

- [ ] **Step 2: Tag the release**

```bash
git tag -a v1.0.0 -m "SearchAtlas Toolkit plugin v1.0.0

First plugin release. Replaces clone-and-script install with
/plugin install searchatlas-toolkit. See CHANGELOG.md for details."
```

- [ ] **Step 3: Push tag**

```bash
git push origin main --tags
```

(Confirm with user before pushing — pushing to main is a shared-state action.)

- [ ] **Step 4: Done**

Plugin is published. Users can now `/plugin marketplace add search-atlas-group/amm-toolkit && /plugin install searchatlas-toolkit`. Existing users can run `./scripts/migrate-to-plugin.sh` from their clone.

---

## Verification Summary

By the end of this plan:

- ✅ `.claude-plugin/plugin.json` declares the plugin with the SearchAtlas MCP, hook path, command/skill/agent asset paths
- ✅ `.claude-plugin/marketplace.json` makes the repo discoverable as a marketplace
- ✅ 21 commands renamed to `sa-*` with frontmatter, env var substitutions, and subfolder output mapping
- ✅ `hooks/ensure-env.sh` creates client data dir + checks MCP auth (fail-open)
- ✅ `AGENTS.md` carries intent routing + golden rules with `sa-*` references
- ✅ `scripts/migrate-to-plugin.sh` migrates existing users in one shell command + one Claude Code click
- ✅ README forks Code (plugin) vs Desktop (MCP-only)
- ✅ CHANGELOG documents v1.0.0
- ✅ Tests cover manifest, command conversion, hook behavior, migration script
- ✅ Local install smoke test passes

## Out of Scope

- Populating `skills/` and `agents/` with content (future v1.x / v2 work)
- Mission-control rework
- Public marketplace submission (manual step when Anthropic enables it)
- Claude Desktop / claude.ai plugin support (not supported by those products)
