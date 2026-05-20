#!/usr/bin/env bash
# Double-click to restart the Mission Control bridges after a manual kill.
# These bridges auto-start on login; this script is the fallback to restart
# them within the same session.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" == "Darwin" ]]; then
    for NAME in command-center website-build website-rebuild; do
        PLIST="$HOME/Library/LaunchAgents/com.searchatlas.amm-$NAME.plist"
        if [ -f "$PLIST" ]; then
            launchctl unload "$PLIST" 2>/dev/null || true
            launchctl load "$PLIST" 2>/dev/null && \
                echo "  ✓  $NAME bridge restarted" || \
                echo "  ✗  $NAME bridge failed to restart"
        fi
    done
    echo ""
    echo "Bridges restarted. Open welcome.html and click any wizard card."
    read -p "Press Enter to close..."
fi
