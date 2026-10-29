# Private Preview browser-rendered read-state badge proof

Date: 2026-10-29

Evaluated serving revision: `c8e72ef8677d6c3a2ac9d7637f5d1d0d3adffa77` (published `origin/main` at
proof time). Serving source root:
`/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261029`, a clean detached
worktree of published `main`, named by the Private Preview `serving-source` pin.

Live database head: `3a91d7c4e8b2`.

Browser: Google Chrome `156.0.0.0` (`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36`), viewport 1340×914 at
devicePixelRatio 1, `en-US`, on a macOS Darwin 27.2.0 (arm64) host. Origin exercised:
`http://127.0.0.1:8081`, the Private Preview origin.

Accounts: two synthetic accounts on the reserved `example.invalid` domain, claimed as
`@badgeproof-a` and `@badgeproof-b`, provisioned through the documented
`private_preview_provision` path with usernames claimed through `PUT /api/profile/social-identity`.
Session tokens and passwords were held in mode-600 files outside the repository and were never
printed.

Release posture remains `HOLD`. This receipt qualifies one browser-rendered surface of an already
deployed feature. It does not qualify the product.

## What this receipt establishes

The unread badge is **rendered by the real frontend in a real browser against the running Private
Preview**, and it agrees with the API and the database.

This closes the one gap left open by
[the deployment and live read-state qualification](./2026-10-29-private-preview-read-state-live-deployment-proof.md),
which proved the API and storage layers and explicitly recorded that "the unread badge was not
verified in a browser".

## Preconditions observed before the proof

| Check | Result |
| --- | --- |
| Serving worktree `HEAD` | `c8e72ef86` |
| `serving-source` pin | the serving worktree above |
| Backend `/app/guardian` mount source | the serving worktree |
| Live `alembic_version` | `3a91d7c4e8b2` |
| `GET http://127.0.0.1:8081/health` | 200 |
| Served supported profile | `v1-whooshd-deepseek-web`, mounted with `direct_messages` |

The profile content served during this proof was the profile as of the evaluated serving revision.
A concurrent executor had unrelated edits in flight to all five supported profiles in a separate
branch; those edits were not deployed, and this proof's result does not depend on profile content
beyond `direct_messages` being mounted — which the rendered Inbox establishes directly.

## The setup

Twelve of twelve setup checks passed over HTTP against the running service: both accounts logged
in and claimed their usernames, A discovered B by username, A sent a contact request, B received
and accepted it, A held a relationship, A opened a conversation, A sent three messages, and B's
conversation projection reported `unread_count = 3`.

B's Inbox therefore contained two conversations: the acceptance thread with one unread message,
and the new conversation with three.

## What the browser rendered

The People surface was opened in Chrome. The Inbox tab listed both conversations. The DOM was read
directly rather than inferred from a screenshot:

```text
[data-testid="conversation-unread-badge"]  ->  text "3", aria-label "3 unread messages", visible
[data-testid="conversation-unread-badge"]  ->  text "1", aria-label "1 unread message",  visible
```

The launcher button carried the aggregate:

```text
button[aria-label="People (4 unread messages)"]  ->  text "4"
```

`4` is the sum of the two per-conversation counts, so the launcher total and the row badges are
derived from the same projection and agree with the API.

## What the browser did

Opening the three-unread conversation advanced the reader's own cursor, and the badge cleared:

```text
after opening:
  badges in the conversation list DOM : 0   (the list is replaced by the open conversation)
  launcher                            : "People (1 unread message)"
```

The remaining one unread message belongs to the other conversation and was correctly left
alone — opening a conversation advances only the reader's own cursor, never a neighbour's.

## API and database confirmation

Eight of eight checks confirmed the browser's effect against the API and the database:

| Check | Result |
| --- | --- |
| The browser's read advanced B's `unread_count` to 0 | PASS — `status=200 unread_count=0` |
| The other conversation still showed 1 unread | PASS — counts `[0, 1]` |
| A observed no read state for B | PASS — no `read_cursor`, `last_read_message_id`, or receipt key |
| A still saw 0 unread for their own sent messages | PASS |
| A cursor row exists for the opened conversation | PASS |
| The cursor is owned by the recipient | PASS — owner `badgeproof-b` |
| The sender owns no cursor row | PASS — 0 rows |
| No unread-counter table exists | PASS — 0 tables matching `%unread%` |

```text
conversation_id                          cursor_owner   last_read_message_id
22f0a24df45e433892930d55cdf436d4        badgeproof-b    68b530fa8b0049fbb529e7f5efce7169
```

## Cleanup, and the hazard it documents

The two synthetic accounts were removed and the Preview allowlist restored. The reset was
**account-scoped**: every delete was bounded to the resolved profile ids of the two proof
accounts.

This matters because the earlier reset procedure used for the API-level proof contained an
unscoped

```sql
delete from direct_message_read_cursors;
```

The live Preview is multi-account, and that statement would also have erased every other
account's durable read position — including the operator's own cursor, which is the only durable
record of how far a participant has read. The unscoped statement was caught before execution and
replaced with account-bounded deletes. **This was a prevented data-integrity incident, not
observed data loss.**

The scoped reset produced these counts, and the non-target counts did not move. The "before" column
is the state while the two proof accounts existed; the "after" column is the state once they were
removed:

| Table | Before cleanup | After cleanup |
| --- | --- | --- |
| `direct_message_read_cursors` | 2 | 1 |
| `message_requests` | 8 | 7 |
| `direct_messages` | 15 | 11 |
| `direct_message_conversations` | 6 | 4 |
| `direct_message_relationships` | 8 | 7 |
| `direct_message_relationship_participants` | 16 | 14 |
| `direct_message_consents` | 1 | 0 |
| `user_profiles` | 8 | 6 |
| `users` | 13 | 11 |

The single surviving cursor row belongs to `resonant-jones` and was preserved with its
`last_read_message_id` unchanged. The final counts match the documented pre-proof baseline
(11 messages, 4 conversations, 7 relationships, 14 participants).

`CODEXIFY_PREVIEW_APPROVED_EMAILS` was restored from a pre-change copy; the restored
`.env.private-preview` is byte-identical to that copy
(sha256 `8e40ff0cd6cb053a2d76ff3aef84888d89a1a63cefe283d1d5b151b61a3bbccb`), the allowlist is
back to 13 entries with no proof account present, and the backend was recreated on the restored
allowlist. Both proof accounts now return 401 from `/api/auth/login`.

The account-bounded reset is now a reusable operator script:
[`scripts/ops/private_preview_account_scoped_reset.sh`](../../../../scripts/ops/private_preview_account_scoped_reset.sh).
It refuses to run without explicit account identifiers, refuses to run without `--confirm`, bounds
every delete to the resolved scope, and fails if any non-target row count moves.

## What this receipt does not establish

- **The badge is proven in one browser only.** Chrome 156 on macOS. Firefox, Safari, and the
  other Chromium channel remain unverified.
- **The consent HTTP surface was not exercised**, because the Preview profile quarantines `iddb`.
  Storage-layer enforcement remains proven; endpoint behaviour remains unproven.
- **The product is not qualified.** The supported-Compose qualification remains open, and a
  healthy Private Preview is not that qualification.
- **No crash-durability claim** is made.
- **The floating conversation window was not separately exercised.** The launcher total and the
  Inbox row badge were observed; no other surface was asserted.
- **No claim is made about any other account's badge.** All read-state observations are scoped to
  the two synthetic accounts.

## Release and ADR posture

No ADR change. ADR-097 (existing DM consent), ADR-102 (Saved Widget identity/revision boundary),
ADR-103 (participant-local read state) and ADR-104 are unchanged. This proof exercises the
contracts those ADRs define; it does not alter them.

## Reproduction

```sh
# 1. accounts on the reserved domain (allowlist change is temporary and restored)
python -m guardian.cli.private_preview_provision --email badgeproof.a@example.invalid
python -m guardian.cli.private_preview_provision --email badgeproof.b@example.invalid

# 2. drive the relationship, conversation and messages over HTTP
#    (see .scratch/badge_setup.py in the operator's working copy)

# 3. open the Private Preview in a browser as the recipient and read the badge

# 4. remove the accounts, account-scoped
bash scripts/ops/private_preview_account_scoped_reset.sh \
     --username badgeproof-a --username badgeproof-b --confirm
```
