#!/bin/bash
# SearchAtlas Toolkit — one-shot migration from cloned-repo install to plugin.
# Idempotent. SA_TOOLKIT_TEST_MODE=1 skips git pull + interactive prompt.

set -e

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

# Step 1: git pull (skip in test mode)
if [ "$TEST_MODE" != "1" ] && [ -d "$REPO_DIR/.git" ]; then
  echo "→ Pulling latest from origin..."
  (cd "$REPO_DIR" && git pull --ff-only) || echo "⚠️  git pull failed — continuing with current state."
fi

# Step 2: Move client data
if [ -d "$REPO_DIR/clients" ]; then
  echo "→ Moving client data to $SA_CLIENTS_DIR..."
  mkdir -p "$SA_CLIENTS_DIR"
  for client_dir in "$REPO_DIR/clients"/*/; do
    [ -d "$client_dir" ] || continue
    slug=$(basename "$client_dir")
    target="$SA_CLIENTS_DIR/$slug"
    mkdir -p "$target" "$target/scouts" "$target/reports" "$target/workflows" "$target/shots"

    # Top-level canonical files
    for f in brand-profile.md notes.md CLAUDE.md; do
      [ -f "$client_dir$f" ] && [ ! -f "$target/$f" ] && mv "$client_dir$f" "$target/$f"
    done

    # Reshape accumulating artifacts
    for pattern in "scout-*.html" "scout-*.md"; do
      for f in "$client_dir"$pattern; do
        [ -f "$f" ] || continue
        [ -f "$target/scouts/$(basename "$f")" ] || mv "$f" "$target/scouts/"
      done
    done
    for pattern in "business-report-*.md" "report-*.md"; do
      for f in "$client_dir"$pattern; do
        [ -f "$f" ] || continue
        [ -f "$target/reports/$(basename "$f")" ] || mv "$f" "$target/reports/"
      done
    done

    # Anything else still at top level → legacy/
    mkdir -p "$target/legacy"
    for f in "$client_dir"*; do
      [ -e "$f" ] || continue
      [ -d "$f" ] && continue
      [ -f "$target/legacy/$(basename "$f")" ] || mv "$f" "$target/legacy/" 2>/dev/null || true
    done

    # Pre-existing subdirectories
    for sub in scouts scout reports workflows shots; do
      if [ -d "$client_dir/$sub" ]; then
        target_sub="$target/$sub"
        [ "$sub" = "scout" ] && target_sub="$target/scouts"
        mkdir -p "$target_sub"
        for f in "$client_dir/$sub"/*; do
          [ -e "$f" ] || continue
          [ -e "$target_sub/$(basename "$f")" ] || mv "$f" "$target_sub/" 2>/dev/null || true
        done
        rmdir "$client_dir/$sub" 2>/dev/null || true
      fi
    done

    rmdir "$client_dir" 2>/dev/null || true
    # Clean up empty subfolders we created speculatively
    for sub in scouts reports workflows shots legacy; do
      rmdir "$target/$sub" 2>/dev/null || true
    done
  done
fi

# Step 3: Remove legacy slash commands
echo "→ Removing legacy slash commands..."
LEGACY=(
  scout business-report help my-account onboard-client sync-client summit-shot
  run-seo run-gbp run-ppc run-content run-pr run-visibility
  send-slack send-discord send-email send-circle
  setup-integrations build-website rebuild-website security-scan
)
for cmd in "${LEGACY[@]}"; do
  [ -f "$COMMANDS_DIR/$cmd.md" ] && rm "$COMMANDS_DIR/$cmd.md"
done

# Step 4: Remove legacy auto-update hook from settings.json
if [ -f "$SETTINGS" ]; then
  echo "→ Removing legacy auto-update hook from settings.json..."
  TMP=$(mktemp)
  jq '
    if .hooks then
      .hooks |= map(select((.command // "" | tostring | contains("auto-update-hook")) | not))
    else . end
    | if (.hooks // []) | length == 0 then del(.hooks) else . end
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
fi

# Step 5: Add extraKnownMarketplaces + enabledPlugins (OBJECTS, not arrays)
echo "→ Registering plugin in settings.json..."
mkdir -p "$CLAUDE_DIR"
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
    + { "searchatlas@searchatlas": true }
  )
' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"

echo
echo "✅ Migration complete."
echo
echo "Next: open Claude Code. It will prompt you to install searchatlas."
echo "After approval, all /searchatlas:* commands are available."
echo

if [ "$TEST_MODE" != "1" ]; then
  printf "Delete the cloned %s/ now? (Keep it if you use mission-control) [y/N] " "$REPO_DIR"
  read -r ans
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    if [ -d "$REPO_DIR/mission-control" ]; then
      echo "Moving mission-control/ to $HOME/searchatlas-mission-control/..."
      mv "$REPO_DIR/mission-control" "$HOME/searchatlas-mission-control"
    fi
    rm -rf "$REPO_DIR"
    echo "Cloned repo removed."
  fi
fi
