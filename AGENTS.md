# AGENTS.md

This repo ships as a Claude Code plugin: **`searchatlas`**.

## Runtime instructions (for plugin users)

The plugin's runtime guidance — intent routing, golden rules for the SearchAtlas MCP, parameter reference, account-discovery flow, and the command surface — lives in the **`using-searchatlas` skill**:

- [`skills/using-searchatlas/SKILL.md`](skills/using-searchatlas/SKILL.md)

It loads automatically when a user works on SearchAtlas tasks. (Root-level `AGENTS.md` / `CLAUDE.md` are **not** loaded from an installed plugin — only skills are — which is why that content lives in the skill, not here.)

## For contributors working on the toolkit itself

- [`skills/using-searchatlas/SKILL.md`](skills/using-searchatlas/SKILL.md) — the runtime brain; edit this to change routing/golden rules
- [`docs/superpowers/specs/2026-05-26-searchatlas-toolkit-plugin-design.md`](docs/superpowers/specs/2026-05-26-searchatlas-toolkit-plugin-design.md) — design rationale
- [`docs/superpowers/plans/2026-05-26-searchatlas-toolkit-plugin.md`](docs/superpowers/plans/2026-05-26-searchatlas-toolkit-plugin.md) — implementation plan
- [`docs/superpowers/marketplace-submission.md`](docs/superpowers/marketplace-submission.md) — community + official marketplace submission guide

## For users

See [`README.md`](README.md) for install + usage.
