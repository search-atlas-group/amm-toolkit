#!/bin/bash
set -e
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" 2>/dev/null || exit 1

HOOK="hooks/ensure-env.sh"
[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable"; exit 1; }

# shellcheck if available
if command -v shellcheck >/dev/null; then
  shellcheck "$HOOK" || { echo "FAIL: shellcheck errors"; exit 1; }
fi

# Test 1: hook creates SA_CLIENTS_DIR
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" SA_CLIENTS_DIR="$TMPDIR_TEST/.searchatlas/clients" bash "$HOOK" >/dev/null 2>&1
[ -d "$TMPDIR_TEST/.searchatlas/clients" ] \
  || { echo "FAIL: hook did not create SA_CLIENTS_DIR"; rm -rf "$TMPDIR_TEST"; exit 1; }
rm -rf "$TMPDIR_TEST"

# Test 2: hook exits 0 even when claude CLI is missing
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" PATH="/usr/bin:/bin" bash "$HOOK" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: hook did not exit 0 with missing claude CLI"; exit 1; }
rm -rf "$TMPDIR_TEST"

# Test 3: hook is idempotent
TMPDIR_TEST=$(mktemp -d)
HOME="$TMPDIR_TEST" bash "$HOOK" >/dev/null 2>&1
HOME="$TMPDIR_TEST" bash "$HOOK" >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: hook not idempotent"; exit 1; }
rm -rf "$TMPDIR_TEST"

# Test 4: legacy ~/.amm/clients detection prints nudge
TMPDIR_TEST=$(mktemp -d)
mkdir -p "$TMPDIR_TEST/.amm/clients/example-client"
OUTPUT=$(HOME="$TMPDIR_TEST" bash "$HOOK" 2>&1)
echo "$OUTPUT" | grep -q "legacy" \
  || { echo "FAIL: no legacy nudge when ~/.amm/clients exists"; rm -rf "$TMPDIR_TEST"; exit 1; }
rm -rf "$TMPDIR_TEST"

echo "PASS: hook script behaves correctly"
