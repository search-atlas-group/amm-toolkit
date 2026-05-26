#!/bin/bash
set -e
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" 2>/dev/null || exit 1

SCRIPT="Scripts/migrate-to-plugin.sh"
[ -f "$SCRIPT" ] || { echo "FAIL: $SCRIPT missing"; exit 1; }
[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

if command -v shellcheck >/dev/null; then
  shellcheck "$SCRIPT" || { echo "FAIL: shellcheck errors"; exit 1; }
fi

SANDBOX=$(mktemp -d)
FAKE_HOME="$SANDBOX/home"
FAKE_REPO="$SANDBOX/toolkit-public"
mkdir -p "$FAKE_HOME/.claude/commands"
mkdir -p "$FAKE_REPO/clients/acme-co"
mkdir -p "$FAKE_REPO/Scripts"
echo '# fake brand profile' > "$FAKE_REPO/clients/acme-co/brand-profile.md"
echo '# fake scout report' > "$FAKE_REPO/clients/acme-co/scout-2026-05-20.html"
for cmd in scout business-report help my-account onboard-client sync-client summit-shot \
           run-seo run-gbp run-ppc run-content run-pr run-visibility \
           send-slack send-discord send-email send-circle \
           setup-integrations build-website rebuild-website security-scan; do
  echo "# legacy $cmd" > "$FAKE_HOME/.claude/commands/$cmd.md"
done
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
cp "$SCRIPT" "$FAKE_REPO/Scripts/migrate-to-plugin.sh"
chmod +x "$FAKE_REPO/Scripts/migrate-to-plugin.sh"

# Run migration with sandbox HOME
HOME="$FAKE_HOME" SA_TOOLKIT_TEST_MODE=1 bash "$FAKE_REPO/Scripts/migrate-to-plugin.sh" >/dev/null 2>&1

# Assertion 1: client data moved (brand-profile.md at top level of new location)
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

# Assertion 5: extraKnownMarketplaces.searchatlas added (OBJECT keyed by marketplace name)
jq -e '.extraKnownMarketplaces.searchatlas.source.repo == "search-atlas-group/amm-toolkit"' \
  "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: extraKnownMarketplaces.searchatlas not set correctly"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 6: enabledPlugins object includes plugin@marketplace key
jq -e '.enabledPlugins["searchatlas@searchatlas"] == true' \
  "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: searchatlas@searchatlas not enabled"; rm -rf "$SANDBOX"; exit 1; }

# Assertion 7: re-running is idempotent
HOME="$FAKE_HOME" SA_TOOLKIT_TEST_MODE=1 bash "$FAKE_REPO/Scripts/migrate-to-plugin.sh" >/dev/null 2>&1
jq -e '.enabledPlugins | length == 1' "$FAKE_HOME/.claude/settings.json" >/dev/null \
  || { echo "FAIL: re-running corrupted enabledPlugins"; rm -rf "$SANDBOX"; exit 1; }

rm -rf "$SANDBOX"
echo "PASS: migration script behaves correctly"
