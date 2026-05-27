#!/usr/bin/env bash
# release.sh — one-command release for the SearchAtlas plugin.
#
# Because marketplace.json tracks the `main` branch (not a pinned tag), a release
# is just: bump plugin.json version → commit → push to the github remote. Users on
# auto-update pick it up at next Claude Code startup; others run
# `/plugin marketplace update searchatlas && /plugin update searchatlas`.
#
# Usage:  Scripts/release.sh <version>     e.g.  Scripts/release.sh 2.3.0
#         Scripts/release.sh <version> --tag   also create + push a vX.Y.Z tag
#
# Pre-req: add your release notes to CHANGELOG.md under a "## [<version>]" heading
# BEFORE running — the script refuses to release if that heading is missing.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-}"
WANT_TAG="${2:-}"

if [ -z "$VERSION" ]; then
  echo "usage: Scripts/release.sh <version> [--tag]" >&2
  exit 1
fi
if ! printf '%s' "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "error: version must be semver (e.g. 2.3.0), got: $VERSION" >&2
  exit 1
fi

# 1. Require a CHANGELOG entry for this version.
if ! grep -q "^## \[$VERSION\]" CHANGELOG.md; then
  echo "error: CHANGELOG.md has no '## [$VERSION]' section — add release notes first." >&2
  exit 1
fi

# 2. Bump the version in plugin.json (the single source of truth now).
python3 - "$VERSION" <<'PY'
import json, sys
v = sys.argv[1]
p = ".claude-plugin/plugin.json"
d = json.load(open(p))
d["version"] = v
json.dump(d, open(p, "w"), indent=2)
open(p, "a").write("\n")
print(f"plugin.json version -> {v}")
PY

# 3. Validate before committing.
if command -v claude >/dev/null 2>&1; then
  claude plugin validate . >/dev/null && echo "validate: OK"
fi

# 4. Commit + push to the github remote (never origin — see reference_amm_toolkit_git).
git add .claude-plugin/plugin.json CHANGELOG.md
git commit -m "release: v$VERSION"
git push github main

# 5. Optional tag (distribution tracks main, so tags are for humans/GitHub Releases only).
if [ "$WANT_TAG" = "--tag" ]; then
  git tag -a "v$VERSION" -m "v$VERSION"
  git push github "v$VERSION"
  echo "tagged + pushed v$VERSION"
fi

echo "released v$VERSION → github/main"
