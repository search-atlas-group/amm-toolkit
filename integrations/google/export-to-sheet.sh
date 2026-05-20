#!/usr/bin/env bash
# Export a client report or workflow result to a Google Sheet via Apps Script web app.
#
# Prerequisites:
#   1. Deploy the Apps Script endpoint (see README.md in this folder)
#   2. Set GOOGLE_SHEETS_WEBHOOK in your .env
#
# Usage:
#   source .env
#   bash integrations/google/export-to-sheet.sh \
#     --sheet-id  "<spreadsheet_id>" \
#     --tab       "<sheet tab name>" \
#     --data      "<JSON string>"
#
# Example:
#   bash integrations/google/export-to-sheet.sh \
#     --sheet-id  "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms" \
#     --tab       "SEO Report" \
#     --data      '[["Client","Domain","Score"],["Apple","apple.com","87"]]'

set -e

WEBHOOK="${GOOGLE_SHEETS_WEBHOOK:?GOOGLE_SHEETS_WEBHOOK is not set. Add it to your .env file.}"
SHEET_ID=""
TAB=""
DATA=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sheet-id) SHEET_ID="$2"; shift 2 ;;
    --tab)      TAB="$2";      shift 2 ;;
    --data)     DATA="$2";     shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$SHEET_ID" ]] && { echo "Error: --sheet-id is required" >&2; exit 1; }
[[ -z "$TAB" ]]      && { echo "Error: --tab is required" >&2; exit 1; }
[[ -z "$DATA" ]]     && { echo "Error: --data is required (JSON array of rows)" >&2; exit 1; }

PAYLOAD=$(printf '{"spreadsheetId":"%s","tab":"%s","rows":%s}' "$SHEET_ID" "$TAB" "$DATA")

RESPONSE=$(curl -s -o /tmp/sheets_response.json -w "%{http_code}" \
  -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

BODY=$(cat /tmp/sheets_response.json 2>/dev/null || echo "")

if [[ "$RESPONSE" =~ ^2 ]]; then
  echo "Exported to Google Sheet (HTTP $RESPONSE)"
  [[ -n "$BODY" ]] && echo "$BODY"
else
  echo "Export failed (HTTP $RESPONSE): $BODY" >&2
  exit 1
fi
