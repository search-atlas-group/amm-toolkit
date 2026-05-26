#!/bin/bash
# Legacy SessionStart hook — replaced by the SearchAtlas Toolkit plugin.
#
# This file remains in the repo so any user who still has the cloned-repo
# install gets a nudge to migrate. Once they run Scripts/migrate-to-plugin.sh,
# this hook is removed from their settings.json (by the migration script)
# and the nudge stops appearing.

REPO_DIR="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"

echo "📦 SearchAtlas Toolkit v2 available as a plugin."
echo "   Run: cd $REPO_DIR && ./Scripts/migrate-to-plugin.sh"
echo "   (One shell command — moves data, installs plugin, cleans up.)"

exit 0
