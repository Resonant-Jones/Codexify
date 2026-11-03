-- Guarded, transactional core of the Private Preview account-scoped reset.
--
-- Invoked by scripts/ops/private_preview_account_scoped_reset.sh with:
--   -v accounts='["alice","bob"]'   JSON array of account identifiers
--   -v kind='username' | 'email'    how to resolve them
--   -v apply=1 | 0                  1 performs the reset, 0 reports the plan
--
-- Identifiers arrive only through psql variables and are consumed as bound
-- literals (:'accounts' is quoted by psql), never spliced into SQL text, so a
-- crafted identifier cannot widen the selected scope.
--
-- SAFETY MODEL
--
--   1. RESOLUTION. Every requested identifier must resolve to exactly one
--      profile, and that profile must have a non-null profile id. An
--      identifier that matches nothing, matches more than one profile, or
--      resolves to a profile without an id is refused. Without this, a null
--      profile id would make every "NOT IN (SELECT profile_id ...)" predicate
--      evaluate to NULL rather than TRUE, silently excluding those rows from
--      the preservation snapshot.
--   2. The scope is derived from the resolved profile ids of the named
--      accounts and nothing else.
--   3. FAIL CLOSED on shared state. A relationship or message request that
--      joins a named account to an account that was NOT named is refused
--      before any destructive statement runs. A relationship is a two-party
--      construct: deleting one participant's half of it would silently
--      destroy the other participant's messages and read cursor.
--      The decision uses row counts, never display names, because
--      string_agg ignores NULL inputs and a profile without a username would
--      otherwise hide the shared state entirely.
--   4. Every delete is followed, still inside the same transaction, by an
--      assertion that no row outside the requested scope changed. A violated
--      assertion raises, the transaction rolls back, and nothing is deleted.
--   5. COMMIT is reached only when the guard and every assertion passed.

\set ON_ERROR_STOP on

begin;

-- The apply flag is also visible inside the transaction, so the guard can
-- report in dry-run mode and refuse in apply mode.
set local codexify_reset.apply = :'apply';

-- ---------------------------------------------------------------------------
-- Requested scope
-- ---------------------------------------------------------------------------
create temp table requested_accounts as
  select distinct jsonb_array_elements_text(:'accounts'::jsonb) as value;

create temp table reset_profiles as
  select p.profile_id, p.user_id,
         case :'kind'
           when 'username' then p.username
           when 'email'    then u.email
         end as matched_value
    from user_profiles p
    join users u on u.id = p.user_id
   where case :'kind'
           when 'username' then p.username in (select value from requested_accounts)
           when 'email'    then u.email    in (select value from requested_accounts)
           else false
         end;

-- ---------------------------------------------------------------------------
-- GUARD 1: every requested identifier must resolve to EXACTLY ONE profile.
--
--           The check is per identifier, not on the totals. Usernames are
--           unique per (node_id, username) rather than globally, so one
--           identifier can match two profiles while another matches none; a
--           total-vs-total comparison would let those two errors cancel out
--           and delete the two matched accounts.
-- ---------------------------------------------------------------------------
do $resolve$
declare
  unmatched text;
  ambiguous text;
begin
  select string_agg(coalesce(r.value, '<null>'), ', ' order by coalesce(r.value, '<null>'))
    into unmatched
    from requested_accounts r
   where not exists (
     select 1 from reset_profiles p where p.matched_value = r.value);

  select string_agg(coalesce(r.value, '<null>'), ', ' order by coalesce(r.value, '<null>'))
    into ambiguous
    from requested_accounts r
   where (select count(*) from reset_profiles p where p.matched_value = r.value) > 1;

  if unmatched is not null then
    raise exception
      'REFUSED: requested account(s) matched no profile: [%].', unmatched;
  end if;

  if ambiguous is not null then
    raise exception
      'REFUSED: requested account(s) matched more than one profile (usernames are '
      'unique per node, not globally): [%].', ambiguous;
  end if;

  if exists (select 1 from reset_profiles where profile_id is null) then
    raise exception
      'REFUSED: a matched account has no profile id; the scope cannot be bounded.';
  end if;
end
$resolve$;

create temp table reset_rels as
  select distinct relationship_id
    from direct_message_relationship_participants
   where profile_id in (select profile_id from reset_profiles);

-- Conversations are reached ONLY through their relationship. A conversation
-- is not selected because the target created it: the schema does not require
-- the creator to be a participant of the relationship, so that path could
-- reach a conversation whose other participants are outside the scope and
-- delete their messages. Every application-created conversation has a
-- creator who is a participant, so this loses nothing in practice; a
-- malformed row is simply left alone, and the creator reference is nulled by
-- its own ON DELETE SET NULL foreign key when the target's profile goes.
create temp table reset_convs as
  select c.id
    from direct_message_conversations c
   where c.relationship_id in (select relationship_id from reset_rels);

create temp table reset_reqs as
  select id
    from message_requests
   where sender_profile_id in (select profile_id from reset_profiles)
      or recipient_profile_id in (select profile_id from reset_profiles);

-- ---------------------------------------------------------------------------
-- GUARD 2: refuse when a named account shares state with an unnamed account.
--           The decision is made from row counts, not from display names.
-- ---------------------------------------------------------------------------
do $guard$
declare
  mixed_rels_count bigint;
  mixed_reqs_count bigint;
  mixed_rels text;
  mixed_reqs text;
begin
  select count(*) into mixed_rels_count
    from direct_message_relationship_participants rp
   where rp.relationship_id in (select relationship_id from reset_rels)
     and (rp.profile_id is null
       or rp.profile_id not in (select profile_id from reset_profiles));

  select count(*) into mixed_reqs_count
    from (
      select r.sender_profile_id as profile_id
        from message_requests r where r.id in (select id from reset_reqs)
      union
      select r.recipient_profile_id
        from message_requests r where r.id in (select id from reset_reqs)
    ) x
   where x.profile_id is null
      or x.profile_id not in (select profile_id from reset_profiles);

  if mixed_rels_count > 0 or mixed_reqs_count > 0 then
    -- Labels are diagnostic only; coalesce guarantees a non-null label so
    -- that an unnamed participant is still reported.
    select string_agg(coalesce(p.username, p.profile_id, '<no profile id>'), ', ' order by
             coalesce(p.username, p.profile_id, '<no profile id>'))
      into mixed_rels
      from direct_message_relationship_participants rp
      join user_profiles p on p.profile_id = rp.profile_id
     where rp.relationship_id in (select relationship_id from reset_rels)
       and (rp.profile_id is null
         or rp.profile_id not in (select profile_id from reset_profiles));

    select string_agg(coalesce(p.username, p.profile_id, '<no profile id>'), ', ' order by
             coalesce(p.username, p.profile_id, '<no profile id>'))
      into mixed_reqs
      from (
        select r.sender_profile_id as profile_id
          from message_requests r where r.id in (select id from reset_reqs)
        union
        select r.recipient_profile_id
          from message_requests r where r.id in (select id from reset_reqs)
      ) x
      join user_profiles p on p.profile_id = x.profile_id
     where x.profile_id is null
        or x.profile_id not in (select profile_id from reset_profiles);

    if current_setting('codexify_reset.apply')::int = 1 then
      raise exception
        'REFUSED: named accounts share state with accounts outside the requested scope. '
        'shared relationship participants (%): [%]; shared request counterparties (%): [%]. '
        'Name every participant explicitly, or clear the shared state first.',
        mixed_rels_count, coalesce(mixed_rels, 'none'),
        mixed_reqs_count, coalesce(mixed_reqs, 'none');
    else
      raise notice
        'SHARED STATE DETECTED (dry run): named accounts share state with accounts '
        'outside the requested scope. shared relationship participants (%): [%]; '
        'shared request counterparties (%): [%]. Applying this reset would be REFUSED.',
        mixed_rels_count, coalesce(mixed_rels, 'none'),
        mixed_reqs_count, coalesce(mixed_reqs, 'none');
    end if;
  end if;
end
$guard$;

-- ---------------------------------------------------------------------------
-- Snapshot of everything OUTSIDE the requested scope, taken before any delete.
-- Every predicate is null-safe: a row whose scoping column is NULL is
-- counted as outside the scope rather than silently dropped.
-- ---------------------------------------------------------------------------
create temp table before_counts (label text primary key, value bigint);

insert into before_counts
     select 'read_cursors', count(*) from direct_message_read_cursors
      where profile_id not in (select profile_id from reset_profiles)
 union all select 'message_requests', count(*) from message_requests
      where id not in (select id from reset_reqs)
 union all select 'messages', count(*) from direct_messages
      where conversation_id is null
         or conversation_id not in (select id from reset_convs)
 union all select 'conversations', count(*) from direct_message_conversations
      where id not in (select id from reset_convs)
 union all select 'relationships', count(*) from direct_message_relationships
      where id not in (select relationship_id from reset_rels)
 union all select 'relationship_participants', count(*) from direct_message_relationship_participants
      where relationship_id not in (select relationship_id from reset_rels)
 union all select 'consents', count(*) from direct_message_consents
      where relationship_id not in (select relationship_id from reset_rels)
 union all select 'user_settings', count(*) from user_settings
      where user_id not in (select user_id from reset_profiles)
 union all select 'user_profiles', count(*) from user_profiles
      where profile_id is null
         or profile_id not in (select profile_id from reset_profiles)
 union all select 'users', count(*) from users
      where id not in (select user_id from reset_profiles);

-- ---------------------------------------------------------------------------
-- Destructive statements
-- ---------------------------------------------------------------------------
\if :apply

delete from direct_message_read_cursors
 where profile_id in (select profile_id from reset_profiles);

-- A pending request carries no conversation and no first message. Retiring it
-- to 'declined' must also stamp transitioned_at: ck_message_requests_transition
-- requires a non-null transition time for every non-pending state. The
-- original transition time is preserved for requests that already had one.
update message_requests
   set state = 'declined',
       transitioned_at = coalesce(transitioned_at, now()),
       first_message_id = null,
       conversation_id = null
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

-- user_settings.user_id holds the canonical account id (user_profiles.user_id,
-- which is users.id). It is keyed by the account id and nothing else: also
-- matching the profile id would let a profile id that happens to equal
-- another account's id delete that account's settings.
delete from user_settings
 where user_id in (select user_id from reset_profiles);

delete from user_profiles
 where profile_id in (select profile_id from reset_profiles);

delete from users
 where id in (select user_id from reset_profiles);

\endif

-- ---------------------------------------------------------------------------
-- ASSERTION: nothing outside the requested scope may have changed.
-- Runs inside the same transaction; a failure aborts it and rolls it back.
-- ---------------------------------------------------------------------------
create temp table after_counts (label text primary key, value bigint);

insert into after_counts
     select 'read_cursors', count(*) from direct_message_read_cursors
      where profile_id not in (select profile_id from reset_profiles)
 union all select 'message_requests', count(*) from message_requests
      where id not in (select id from reset_reqs)
 union all select 'messages', count(*) from direct_messages
      where conversation_id is null
         or conversation_id not in (select id from reset_convs)
 union all select 'conversations', count(*) from direct_message_conversations
      where id not in (select id from reset_convs)
 union all select 'relationships', count(*) from direct_message_relationships
      where id not in (select relationship_id from reset_rels)
 union all select 'relationship_participants', count(*) from direct_message_relationship_participants
      where relationship_id not in (select relationship_id from reset_rels)
 union all select 'consents', count(*) from direct_message_consents
      where relationship_id not in (select relationship_id from reset_rels)
 union all select 'user_settings', count(*) from user_settings
      where user_id not in (select user_id from reset_profiles)
 union all select 'user_profiles', count(*) from user_profiles
      where profile_id is null
         or profile_id not in (select profile_id from reset_profiles)
 union all select 'users', count(*) from users
      where id not in (select user_id from reset_profiles);

do $assert$
declare
  drifted text;
begin
  select string_agg(b.label || ' ' || b.value || ' -> ' || a.value, ', ' order by b.label)
    into drifted
    from before_counts b
    join after_counts a using (label)
   where b.value <> a.value;

  if drifted is not null then
    raise exception 'REFUSED: rows outside the requested scope changed: %', drifted;
  end if;
end
$assert$;

commit;
