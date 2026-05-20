#!/usr/bin/env bash
# Double-click ONLY if welcome.html reports the supervisor is unreachable.
#
# Normal flow: welcome.html auto-wakes bridges via the supervisor on 8764.
# This is the fallback for when even the supervisor isn't running.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR")"
UID_NUM=$(id -u)

restart_one() {
    local name="$1" port="$2"
    local label="com.searchatlas.amm-$name"
    local plist="$HOME/Library/LaunchAgents/$label.plist"

    if curl -s -o /dev/null -m 1 "http://localhost:$port/api/health" 2>/dev/null; then
        echo "  ✓  $name already running on port $port"
        return 0
    fi

    if [ ! -f "$plist" ]; then
        echo "  ✗  $name plist missing at $plist — re-run setup.sh"
        return 1
    fi

    launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
    sleep 1
    launchctl bootstrap "gui/$UID_NUM" "$plist" || true

    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
        if curl -s -o /dev/null -m 1 "http://localhost:$port/api/health" 2>/dev/null; then
            echo "  ✓  $name listening on port $port"
            return 0
        fi
        sleep 1
    done
    echo "  ✗  $name failed to start — check /tmp/amm-$name.err"
    return 1
}

restart_one supervisor       8764
restart_one command-center   8865
restart_one website-build    8866
restart_one website-rebuild  8867
echo
echo "Refresh welcome.html, then click any wizard card."
read -p "Press Enter to close..."
