#!/usr/bin/env bash
set -euo pipefail

# Account-scoped cleanup of live Private Preview direct-message state.
#
# WHY THIS SCRIPT EXISTS
#
# The read-state qualification harnesses create synthetic accounts on the live
# Preview and must remove them afterwards. An unscoped
#   DELETE FROM direct_message_read_cursors
# would also erase every *other* account's durable read position — including a
# real operator's — because the cursor table is shared. That is a
# data-integrity incident against live multi-account state, not a cleanup
# detail. The read cursor is the only durable record of how far a participant
# has read; destroying someone else's is unrecoverable.
#
# THE CONSTRAINTS THIS SCRIPT ENFORCES
#
#   1. It refuses to run without explicit account identifiers.
#   2. Account identifiers are passed to the database as bound literals, never
#      spliced into SQL text, so a crafted identifier cannot widen the scope.
#   3. It refuses unless every requested identifier resolves to exactly one
#      profile with a non-null profile id. An identifier that matches nothing
#      is an error, not a no-op.
#   4. It FAILS CLOSED when a named account shares a relationship or message
#      request with an account that was not named. Deleting one participant's
#      half of a two-party relationship would silently destroy the other
#      participant's messages and read cursor. The decision is made from row
#      counts, so a counterpart without a username cannot hide it.
#   5. Every assertion about rows outside the requested scope runs inside the
#      same transaction as the deletes. A violation raises, the transaction
#      rolls back, and nothing is deleted.
#   6. It refuses to run without --confirm.
#
# The destructive logic and its guards live in
# scripts/ops/private_preview_account_scoped_reset.sql so that the same code
# path is exercised by the regression test.
#
# Usage:
#   bash scripts/ops/private_preview_account_scoped_reset.sh \
#        --username badgeproof-a --username badgeproof-b --confirm
#
#   bash scripts/ops/private_preview_account_scoped_reset.sh \
#        --email badgeproof.a@example.invalid --email badgeproof.b@example.invalid --confirm
#
# Dry run (the default when --confirm is absent): reports the plan and the
# scope, and changes nothing.

SCRIPT_VERSION="2"
PROJECT_NAME="${CODEXIFY_PRIVATE_PREVIEW_PROJECT_NAME:-codexify_private_preview}"

DB_CONTAINER="${CODEXIFY_PREVIEW_DB_CONTAINER:-${PROJECT_NAME}-db-1}"
DB_SQL_USER="${CODEXIFY_PREVIEW_DB_USER:-codexify}"
DB_SQL_NAME="${CODEXIFY_PREVIEW_DB_NAME:-Codexify}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SQL_FILE="${SCRIPT_DIR}/private_preview_account_scoped_reset.sql"

USERNAMES=()
EMAILS=()
CONFIRM=0

usage() {
  sed -n '2,40p' "$0"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username) USERNAMES+=("$2"); shift 2 ;;
    --email) EMAILS+=("$2"); shift 2 ;;
    --confirm) CONFIRM=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage 2 ;;
  esac
done

if [[ ${#USERNAMES[@]} -eq 0 && ${#EMAILS[@]} -eq 0 ]]; then
  echo "FATAL: no account identifiers given." >&2
  echo "This script refuses to run unscoped. Pass --username and/or --email." >&2
  usage 2
fi

if [[ ${#USERNAMES[@]} -gt 0 && ${#EMAILS[@]} -gt 0 ]]; then
  echo "FATAL: pass either --username or --email, not both." >&2
  exit 2
fi

if [[ ${#USERNAMES[@]} -gt 0 ]]; then
  KIND="username"
  IDENTIFIERS=("${USERNAMES[@]}")
else
  KIND="email"
  IDENTIFIERS=("${EMAILS[@]}")
fi

if [[ ! -f "$SQL_FILE" ]]; then
  echo "FATAL: missing SQL core: $SQL_FILE" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${DB_CONTAINER}"; then
  echo "FATAL: database container not running: ${DB_CONTAINER}" >&2
  exit 1
fi

# Encode the identifiers as a JSON array. psql receives this as a bound
# literal (:'accounts'), so it is never interpreted as SQL. Duplicates are
# collapsed, because the resolution guard requires every identifier to match
# exactly one profile.
ACCOUNTS_JSON="$(python3 -c '
import json, sys
print(json.dumps(list(dict.fromkeys(sys.argv[1:]))))
' "${IDENTIFIERS[@]}")"

if [[ "$CONFIRM" == "1" ]]; then
  APPLY=1
  MODE="APPLY"
else
  APPLY=0
  MODE="DRY RUN"
fi

echo "== Codexify Private Preview account-scoped reset =="
echo "mode        : ${MODE}"
echo "project     : ${PROJECT_NAME}"
echo "scope by    : ${KIND}"
echo "accounts    : ${IDENTIFIERS[*]}"
echo

# The SQL core refuses the run when nothing matched, and fails closed on
# shared state. A non-zero exit means nothing was changed.
#
# NOTE: psql is invoked directly as argv, not through a nested `sh -lc`. A
# nested shell re-parses the identifier argument and would mangle any
# identifier containing a quote or a space. Here each -v value is one
# discrete argument and reaches psql byte-for-byte.
set +e
docker exec -i "${DB_CONTAINER}" \
  psql -v ON_ERROR_STOP=1 -U "${DB_SQL_USER}" -d "${DB_SQL_NAME}" -AtXq \
       -v "accounts=${ACCOUNTS_JSON}" -v "kind=${KIND}" -v "apply=${APPLY}" \
       -f - < "$SQL_FILE"
rc=$?
set -e

if [[ "$rc" != "0" ]]; then
  echo
  echo "RESULT: REFUSED (exit ${rc}). No changes were committed." >&2
  exit "$rc"
fi

echo
if [[ "$APPLY" == "1" ]]; then
  echo "RESULT: scoped reset committed. Rows outside the named scope were asserted unchanged."
else
  echo "RESULT: dry run only. Nothing was changed. Re-run with --confirm to apply."
fi
