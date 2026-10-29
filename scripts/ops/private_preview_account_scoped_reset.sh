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
#   2. Every DELETE is bounded to the resolved profile ids of those accounts.
#   3. It refuses to run without --confirm.
#   4. It counts, for every affected table, the rows that belong to the target
#      accounts AND the rows that do not, before and after. It then fails if
#      any non-target count moved. A reset that touched another account's rows
#      is a failure, not a warning.
#   5. It fails if target rows survive the reset.
#
# Usage:
#   bash scripts/ops/private_preview_account_scoped_reset.sh \
#        --username badgeproof-a --username badgeproof-b --confirm
#
#   bash scripts/ops/private_preview_account_scoped_reset.sh \
#        --email badgeproof.a@example.invalid --email badgeproof.b@example.invalid --confirm
#
# Dry run (the default when --confirm is absent): prints the plan and the
# counts, and changes nothing.

SCRIPT_VERSION="1"
PROJECT_NAME="${CODEXIFY_PRIVATE_PREVIEW_PROJECT_NAME:-codexify_private_preview}"

DB_CONTAINER="${PROJECT_NAME}-db-1"
DB_SQL_USER="${CODEXIFY_PREVIEW_DB_USER:-codexify}"
DB_SQL_NAME="${CODEXIFY_PREVIEW_DB_NAME:-Codexify}"

USERNAMES=()
EMAILS=()
CONFIRM=0

usage() {
  sed -n '2,34p' "$0"
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

if [[ "$CONFIRM" != "1" ]]; then
  MODE="DRY RUN"
else
  MODE="APPLY"
fi

psql_query() {
  # NOTE: no here-strings or heredocs. The Codexify agent sandbox denies
  # creating the temporary files bash uses to back them, so SQL is piped.
  # -q matters: psql echoes the command tag of a CREATE TABLE AS SELECT as
  # "SELECT <n>", which would otherwise be parsed as part of the result row.
  printf '%s\n' "$1" | docker exec -i "${DB_CONTAINER}" sh -lc \
    "exec psql -v ON_ERROR_STOP=1 -U '$DB_SQL_USER' -d '$DB_SQL_NAME' -AtXq"
}

# Split a pipe-delimited row into named fields without a here-string.
SPLIT_FIELDS=()
split_row() {
  local row="$1"
  local old_ifs="$IFS"
  IFS='|'
  set -- $row
  IFS="$old_ifs"
  SPLIT_FIELDS=("$@")
}

if ! docker ps --format '{{.Names}}' | grep -qx "${DB_CONTAINER}"; then
  echo "FATAL: database container not running: ${DB_CONTAINER}" >&2
  exit 1
fi

if [[ ${#USERNAMES[@]} -gt 0 ]]; then
  scope_expr="p.username in ($(printf "'%s'," "${USERNAMES[@]}" | sed 's/,$//'))"
  scope_kind="username"
else
  scope_expr="u.email in ($(printf "'%s'," "${EMAILS[@]}" | sed 's/,$//'))"
  scope_kind="email"
fi

TARGET_PROFILES="$(psql_query "
select coalesce(string_agg(quote_literal(p.profile_id::text), ','), '')
  from user_profiles p
  join users u on u.id = p.user_id
 where ${scope_expr};")"

if [[ -z "$TARGET_PROFILES" ]]; then
  echo "FATAL: no profile matched the given ${scope_kind}." >&2
  echo "Nothing to clean; leaving the database untouched." >&2
  exit 1
fi

# The scope is expressed only through these temp tables. No statement below
# deletes a row outside them.
SCOPE_SQL="
create temp table reset_profiles as
  select profile_id, user_id from user_profiles where profile_id in (${TARGET_PROFILES});
create temp table reset_rels as
  select distinct relationship_id
    from direct_message_relationship_participants
   where profile_id in (select profile_id from reset_profiles);
create temp table reset_convs as
  select c.id from direct_message_conversations c
   where c.relationship_id in (select relationship_id from reset_rels)
      or c.created_by_profile_id in (select profile_id from reset_profiles);
create temp table reset_reqs as
  select id from message_requests
   where sender_profile_id in (select profile_id from reset_profiles)
      or recipient_profile_id in (select profile_id from reset_profiles);
"

# For every affected table: how many rows belong to the target, and how many do
# not. The second number must not move.
COUNTS_SQL="${SCOPE_SQL}
select concat_ws('|',
  (select count(*) from direct_message_read_cursors where profile_id in (select profile_id from reset_profiles)),
  (select count(*) from direct_message_read_cursors where profile_id not in (select profile_id from reset_profiles)),
  (select count(*) from message_requests where id in (select id from reset_reqs)),
  (select count(*) from message_requests where id not in (select id from reset_reqs)),
  (select count(*) from direct_messages where conversation_id in (select id from reset_convs)),
  (select count(*) from direct_messages where conversation_id not in (select id from reset_convs)),
  (select count(*) from direct_message_conversations where id in (select id from reset_convs)),
  (select count(*) from direct_message_conversations where id not in (select id from reset_convs)),
  (select count(*) from direct_message_relationships where id in (select relationship_id from reset_rels)),
  (select count(*) from direct_message_relationships where id not in (select relationship_id from reset_rels)),
  (select count(*) from direct_message_relationship_participants where relationship_id not in (select relationship_id from reset_rels)),
  (select count(*) from direct_message_consents where relationship_id not in (select relationship_id from reset_rels)),
  (select count(*) from user_profiles where profile_id not in (select profile_id from reset_profiles)),
  (select count(*) from users where id not in (select user_id from reset_profiles))
);"

echo "== Codexify Private Preview account-scoped reset =="
echo "mode        : ${MODE}"
echo "project     : ${PROJECT_NAME}"
echo "scope by    : ${scope_kind}"
echo "profiles    : ${TARGET_PROFILES}"
echo

split_row "$(psql_query "$COUNTS_SQL")"
T_CUR="${SPLIT_FIELDS[0]}"  O_CUR="${SPLIT_FIELDS[1]}"
T_REQ="${SPLIT_FIELDS[2]}"  O_REQ="${SPLIT_FIELDS[3]}"
T_MSG="${SPLIT_FIELDS[4]}"  O_MSG="${SPLIT_FIELDS[5]}"
T_CONV="${SPLIT_FIELDS[6]}" O_CONV="${SPLIT_FIELDS[7]}"
T_REL="${SPLIT_FIELDS[8]}"  O_REL="${SPLIT_FIELDS[9]}"
O_PART="${SPLIT_FIELDS[10]}" O_CONS="${SPLIT_FIELDS[11]}"
O_PROF="${SPLIT_FIELDS[12]}" O_USERS="${SPLIT_FIELDS[13]}"

echo "before: target  cursors=${T_CUR} requests=${T_REQ} messages=${T_MSG} conversations=${T_CONV} relationships=${T_REL}"
echo "        non-target cursors=${O_CUR} requests=${O_REQ} messages=${O_MSG} conversations=${O_CONV}"
echo "                 relationships=${O_REL} participants=${O_PART} consents=${O_CONS}"
echo "                 profiles=${O_PROF} users=${O_USERS}"
echo

if [[ "$CONFIRM" != "1" ]]; then
  echo "Dry run only. Re-run with --confirm to apply."
  exit 0
fi

RESET_SQL="${SCOPE_SQL}
begin;

delete from direct_message_read_cursors
 where profile_id in (select profile_id from reset_profiles);

update message_requests
   set state = 'declined', first_message_id = null, conversation_id = null
 where id in (select id from reset_reqs);

delete from message_request_attempts
 where request_id in (select id from reset_reqs);

delete from message_request_visibility
 where request_id in (select id from reset_reqs);

delete from direct_message_consents
 where relationship_id in (select relationship_id from reset_rels);

delete from direct_messages
 where conversation_id in (select id from reset_convs);

delete from direct_message_conversation_placements
 where conversation_id in (select id from reset_convs);

delete from message_requests
 where id in (select id from reset_reqs);

delete from direct_message_conversations
 where id in (select id from reset_convs);

delete from direct_message_relationship_participants
 where relationship_id in (select relationship_id from reset_rels);

delete from direct_message_relationships
 where id in (select relationship_id from reset_rels);

delete from user_settings
 where user_id in (select profile_id from reset_profiles);

delete from user_profiles
 where profile_id in (select profile_id from reset_profiles);

delete from users
 where id in (select user_id from reset_profiles);

commit;
"

psql_query "$RESET_SQL" >/dev/null

split_row "$(psql_query "$COUNTS_SQL")"
T_CUR2="${SPLIT_FIELDS[0]}"  O_CUR2="${SPLIT_FIELDS[1]}"
T_REQ2="${SPLIT_FIELDS[2]}"  O_REQ2="${SPLIT_FIELDS[3]}"
T_MSG2="${SPLIT_FIELDS[4]}"  O_MSG2="${SPLIT_FIELDS[5]}"
T_CONV2="${SPLIT_FIELDS[6]}" O_CONV2="${SPLIT_FIELDS[7]}"
T_REL2="${SPLIT_FIELDS[8]}"  O_REL2="${SPLIT_FIELDS[9]}"
O_PART2="${SPLIT_FIELDS[10]}" O_CONS2="${SPLIT_FIELDS[11]}"
O_PROF2="${SPLIT_FIELDS[12]}" O_USERS2="${SPLIT_FIELDS[13]}"

echo "after : target  cursors=${T_CUR2} requests=${T_REQ2} messages=${T_MSG2} conversations=${T_CONV2} relationships=${T_REL2}"
echo "        non-target cursors=${O_CUR2} requests=${O_REQ2} messages=${O_MSG2} conversations=${O_CONV2}"
echo "                 relationships=${O_REL2} participants=${O_PART2} consents=${O_CONS2}"
echo "                 profiles=${O_PROF2} users=${O_USERS2}"
echo

failed=0
check_preserved() {
  local label="$1" before="$2" after="$3"
  if [[ "$before" == "$after" ]]; then
    printf '  OK       %-24s preserved (%s)\n' "$label" "$after"
  else
    printf '  FAIL     %-24s changed: %s -> %s\n' "$label" "$before" "$after" >&2
    failed=1
  fi
}

echo "non-target preservation:"
check_preserved "read cursors"        "$O_CUR"   "$O_CUR2"
check_preserved "message requests"    "$O_REQ"   "$O_REQ2"
check_preserved "messages"            "$O_MSG"   "$O_MSG2"
check_preserved "conversations"       "$O_CONV"  "$O_CONV2"
check_preserved "relationships"       "$O_REL"   "$O_REL2"
check_preserved "relationship parts"  "$O_PART"  "$O_PART2"
check_preserved "consents"            "$O_CONS"  "$O_CONS2"
check_preserved "user profiles"       "$O_PROF"  "$O_PROF2"
check_preserved "users"               "$O_USERS" "$O_USERS2"

echo
echo "target removal:"
TARGET_LABELS=("read cursors" "message requests" "messages" "conversations" "relationships")
TARGET_BEFORE=("$T_CUR" "$T_REQ" "$T_MSG" "$T_CONV" "$T_REL")
TARGET_AFTER=("$T_CUR2" "$T_REQ2" "$T_MSG2" "$T_CONV2" "$T_REL2")
for i in "${!TARGET_LABELS[@]}"; do
  if [[ "${TARGET_AFTER[$i]}" == "0" ]]; then
    printf '  OK       %-24s removed (was %s)\n' "${TARGET_LABELS[$i]}" "${TARGET_BEFORE[$i]}"
  else
    printf '  FAIL     %-24s remains: %s\n' "${TARGET_LABELS[$i]}" "${TARGET_AFTER[$i]}" >&2
    failed=1
  fi
done

if [[ "$failed" != "0" ]]; then
  echo
  echo "RESULT: FAILED — the reset was not confined to the named accounts." >&2
  exit 1
fi

echo
echo "RESULT: scoped reset complete; no non-target rows were touched."
