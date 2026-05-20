#!/usr/bin/env bash
# SessionStart hook — auto-updates the toolkit clone to latest main.
#
# Design rules:
# - Silent on success when already up to date (no chat noise per session).
# - Banner only when there's something to tell the user: an update landed,
#   the working tree blocks one, or main has diverged.
# - Never modifies files the user has been editing — skips entirely if the
#   working tree is dirty.
# - Skips if not a git checkout (someone installed via install-mcp.sh tarball).
# - Capped at 3s of network time so session start stays fast.
# - Output is a JSON object on stdout (Claude Code hook contract); empty
#   {} means "no message to surface to the user".
#
# Failure mode philosophy: if anything goes wrong, return {} silently. Auto-
# update should never block or scare a user — they can always pull manually.

set -u

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_DIR" ]; then
  echo '{}'
  exit 0
fi

cd "$REPO_DIR" || { echo '{}'; exit 0; }

# Sanity check: we only auto-update the amm-toolkit repo. If someone has
# this hook live in a different repo (unlikely, but defensive), bail.
if [ ! -f "$REPO_DIR/CLAUDE.md" ] || ! grep -q "Agentic Marketing Mastermind" "$REPO_DIR/CLAUDE.md" 2>/dev/null; then
  echo '{}'
  exit 0
fi

# Don't disturb a dirty working tree — the user is mid-edit. Silent skip.
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo '{}'
  exit 0
fi

# Only update when on main — don't yank power-users off feature branches.
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo '{}'
  exit 0
fi

# Cap network at 3s so session start stays fast on slow links.
timeout 3 git fetch --quiet origin main 2>/dev/null || { echo '{}'; exit 0; }

LOCAL="$(git rev-parse HEAD 2>/dev/null)"
REMOTE="$(git rev-parse origin/main 2>/dev/null)"

if [ -z "$LOCAL" ] || [ -z "$REMOTE" ] || [ "$LOCAL" = "$REMOTE" ]; then
  echo '{}'
  exit 0
fi

# Fast-forward only — if main has diverged locally, surface a banner
# instead of trying to merge.
if git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
  if git pull --ff-only --quiet origin main 2>/dev/null; then
    NEW_SHORT="$(git rev-parse --short HEAD)"
    COUNT="$(git rev-list "${LOCAL}..HEAD" --count 2>/dev/null || echo '?')"
    # Plural agreement without external deps
    if [ "$COUNT" = "1" ]; then
      WORD="commit"
    else
      WORD="commits"
    fi
    MSG="📦 amm-toolkit auto-updated: ${COUNT} new ${WORD} pulled → ${NEW_SHORT}. See WHATS-NEW.md for what changed."
    # JSON-escape the message (only quotes / backslashes need handling)
    ESCAPED_MSG="${MSG//\\/\\\\}"
    ESCAPED_MSG="${ESCAPED_MSG//\"/\\\"}"
    printf '{"systemMessage": "%s"}\n' "$ESCAPED_MSG"
  else
    echo '{}'
  fi
  exit 0
fi

# Diverged — local has commits that aren't on origin. Don't auto-anything;
# surface the conflict so the user can resolve.
echo '{"systemMessage": "⚠️  amm-toolkit: local main has diverged from origin/main. Resolve manually with: git status, then git pull --rebase or git push as appropriate."}'
exit 0
