#!/bin/bash
set -e
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" 2>/dev/null || exit 1
# Verify a plugin command file is structurally correct.
# Usage: bash tests/command-conversion.test.sh <name>  (e.g. "scout")
# Plugin commands are namespaced as /searchatlas:<name> at invocation.

NAME="$1"
[ -z "$NAME" ] && { echo "FAIL: pass a command name (e.g. scout)"; exit 1; }
FILE="commands/${NAME}.md"

[ -f "$FILE" ] || { echo "FAIL: $FILE missing"; exit 1; }

# Frontmatter: name field matches filename (no sa- prefix)
head -10 "$FILE" | grep -q "^name: ${NAME}$" \
  || { echo "FAIL: frontmatter name field missing or wrong (expected 'name: ${NAME}')"; exit 1; }

# Frontmatter: description field
head -10 "$FILE" | grep -q "^description: " \
  || { echo "FAIL: frontmatter description missing"; exit 1; }

# No AMM_ROOT references
grep -q "AMM_ROOT" "$FILE" \
  && { echo "FAIL: AMM_ROOT still present (should be CLAUDE_PLUGIN_ROOT or SA_CLIENTS_DIR)"; exit 1; }

# No git-rev-parse path resolution
grep -q "git rev-parse --show-toplevel" "$FILE" \
  && { echo "FAIL: git rev-parse path resolution still present"; exit 1; }

# No bare clients/ path references in actionable code lines
grep -E "^[^#>]*\b(cd |mkdir |touch |cat |echo |>|\\\$\\(cd )[^|]*clients/" "$FILE" \
  | grep -v "SA_CLIENTS_DIR" \
  && { echo "FAIL: bare clients/ path reference (must use \$SA_CLIENTS_DIR)"; exit 1; }

# No leftover sa- prefixed references and no bare unprefixed command refs —
# all sibling command references must use the /searchatlas:<name> namespaced form
grep -E "/sa-(scout|business-report|run-seo|run-gbp|run-ppc|run-content|run-pr|run-visibility|my-account|onboard-client|sync-client|summit-shot|help|send-slack|send-discord|send-email|send-circle|setup-integrations|build-website|rebuild-website|security-scan)\b" "$FILE" \
  && { echo "FAIL: leftover /sa-* command reference (should be /searchatlas:*)"; exit 1; }

grep -E "(\`|^|\s)/(scout|business-report|run-seo|run-gbp|run-ppc|run-content|run-pr|run-visibility|my-account|onboard-client|sync-client|summit-shot|help|send-slack|send-discord|send-email|send-circle|setup-integrations|build-website|rebuild-website|security-scan)\b" "$FILE" \
  && { echo "FAIL: unprefixed command reference found (should be /searchatlas:*)"; exit 1; }

echo "PASS: commands/${NAME}.md is structurally correct"
