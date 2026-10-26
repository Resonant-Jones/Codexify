# ADR-103: Recipient-Local Direct Message Read State

**Status:** Accepted

**Date:** 2026-10-26

## Acceptance

Accepted as the durable read-state model for the same-node direct-messaging
domain. This decision adds **recipient-local** read state only. It does not
qualify Private Preview, does not qualify default Beta, and does not change
release posture; release status remains `HOLD`.

## Context

The 2026-10-26 Private Preview qualification proved that same-node messaging
works end to end on the running preview: request, acceptance, reply, reload
persistence, decline, and directional suppression. It also established a
negative fact that matters for the product, not just the proof: **the
direct-messaging surface has no unread indicator and no persisted read
state.** Messages are durable and the conversation projection is durable, but
"has this person read what I sent" is not a thing the product can answer.
A recipient has no in-app signal that a message is waiting, and nothing
persists across a reload or a new session.

The current contract is explicit that this is absent, not merely unimplemented:
`direct_message_relationship_participants` holds "no roles, groups, mute,
read state, or delivery state", and delivery/read receipts are deferred.

The gap is a genuine product gap, not a bug. The People/Inbox surface is
the durable inbox of this product, and an inbox that cannot say what is
unread is not a persistent inbox.

### Why not read receipts

The tempting shortcut is a read receipt: a per-message or per-conversation
"seen by" projection. That is a different product with different authority
semantics, and it is explicitly *not* what this decision accepts.

A read receipt publishes the reader's activity to the sender. It creates a
shared, cross-participant fact about one participant's behavior, which is
exactly the kind of authority expansion the messaging boundary has been
careful to refuse at every step: Relationship membership implies "these two
actors can hold direct conversations", and nothing more. Acceptance grants
only ordinary direct messaging. A receipt would grant the sender standing to
observe the recipient's attention — a new disclosure surface over a
participant's own state, with no consent step of its own, and no way for the
recipient to see or object to it.

The need, however, is narrower and entirely participant-local: *I* need to
know what is waiting for *me*. That is a projection over my own account, not
a fact about you.

### Why a cursor and not a counter

A stored unread counter per conversation would have to be maintained
transactionally on every send, every read, every message deletion, and every
participant-local projection change. It would become a second, derived
authority that can drift from the message store it is supposed to describe,
and it would need backfilling and repair logic forever.

The message store is already the single source of truth for what exists.
Read state only needs to answer "how far have I read?" — and that is
expressible as a cursor into the existing durable, chronologically ordered
message log. Unread count is then *derived* on read, never stored.

## Decision

Codexify adopts **recipient-local read state**: one cursor per reading
profile per conversation, with unread count derived from the durable message
store and that cursor.

### 1. The cursor is participant-local and keyed by the reading profile

A read-cursor row is keyed by `(conversation_id, profile_id)`, where
`profile_id` is the **reading** profile. The row records the id of the last
message that profile has read. It stores no counter, no preview, no body, and
no aggregate.

The other participant can never observe this row. It is not exposed in any
conversation payload, and there is no endpoint that reports another
participant's cursor, its position, or its timing. The only read-state value
any caller ever receives is their **own** `unread_count`.

### 2. Unread count is derived, never stored

A message is unread for a given profile when:

- it was authored by a participant **other than** that profile, and
- it sorts after that profile's cursor in the canonical chronological order
  `(conversation_id, created_at, id)`.

With no cursor, every peer-authored message is unread. A profile's own
messages are never unread for that profile, so sending a message never raises
the sender's own count. The cursor ordering uses the same
`(created_at, id)` ordering as the canonical chronological index and the
transcript, so the cursor and the transcript always agree on which message is
last.

The durable message store remains the single authority for what exists. The
cursor adds no second message store, no counter to drift, and no aggregate to
backfill.

### 3. Marking a conversation read is an explicit action

Reading a conversation's transcript and *marking it read* are two different
operations, and only the second one advances read state.

- **Retrieval is read-only.** Fetching a conversation or its messages never
  advances a cursor. A retry, a prefetch, a link preview, or a future
  speculative fetch must not mark a conversation read without the recipient
  choosing to open it. `GET` is expected to be safe, and it is.
- **Marking read is an explicit mutation.** A dedicated authenticated
  `POST /api/direct-messages/conversations/{conversation_id}/read` advances
  **that participant's** cursor and reports the resulting unread count. It is
  the only operation that advances a read cursor.

The cursor never moves backwards, and repeating the mutation is idempotent.

The mutation carries the caller's **read watermark** — the id of the last
message they actually saw. The cursor advances to exactly that message and
**never past it**. The server never infers the watermark from "the latest
message at POST time": a message that arrived after the caller's transcript
was fetched, but before the POST landed, would be marked read without ever
having been shown. A watermark that is not a message of that conversation is
refused rather than silently ignored, and an absent watermark asserts
"nothing was shown" and advances nothing.

Opening a conversation therefore does two things: it advances the reader's own
cursor through the explicit mutation, and it does so **only** for the reader. A
participant who never opens a conversation keeps their cursor where it was,
and their unread count keeps growing.

### 4. Authorization is unchanged and fail-closed

Participation is authorized through canonical Relationship membership
**before** any cursor write. A non-participant can neither read the
conversation nor advance anybody's cursor; the request is refused exactly as
it was before this decision, and no cursor row is created.

Request acceptance, decline, directional suppression, account isolation, and
conversation authorization are untouched. Read state adds no path around any
of them, and no message may be read or sent that could not be read or sent
before.

### 5. Read state is not a receipt, and not shared relationship state

Explicitly **not** implied by this decision:

- **No sender-visible read receipt.** The sender never learns that the
  recipient read a message, when, or how many times they read it.
- **No read timing, read duration, or attention disclosure** of any kind.
- **No message is marked read without having been shown to the reader.** The
  cursor never advances past the caller's read watermark, so a message that
  arrived after the caller's transcript was fetched stays unread.
- **No shared relationship state.** The cursor is not part of the
  Relationship, the Conversation, or the Message authority model. Two
  participants of the same conversation hold two entirely separate cursors.
- **No cross-node or federated read state.** Read state is same-node and
  profile-local, consistent with the messaging domain's existing boundary.
- **No push, email, or operating-system notification**, and no delivery
  receipt of any kind. Read state says what is waiting inside the product.

### 6. Presentation and refresh are product concerns, not authority

The Inbox shows the caller's own unread count per conversation and clears it
when that caller opens the conversation. The Inbox re-reads the conversation
projection while it is open so a message arriving elsewhere surfaces without a
manual reload, and the durable cursor means the cleared state is recovered
after a reload or a new session. Refreshing unread state never advances a
cursor: only opening a conversation does.

## Consequences

- The People/Inbox surface can answer "what is waiting for me" and keeps
  answering it across reloads and new sessions, because the cursor is durable
  and participant-local.
- A recipient gains a durable, private read position with no new disclosure
  surface toward the other participant.
- Unread counts are always consistent with the durable message store, because
  they are computed from it on every read rather than maintained alongside it.
- The messaging boundary is unchanged: no new authority, no new participant-
  visible fact, and no change to request, decline, suppression, or
  conversation authorization.
- Read state is same-node only, and the deferred items in the direct-messaging
  contract — delivery/read receipts, realtime delivery, attachments, Guardian
  messaging, and cross-node transport — remain deferred.

## Companion contract

`docs/architecture/direct-messaging-contract.md` carries the normative
wording for the read cursor, the unread derivation rule, and the API surface.

## Authority and support boundary

Same-node, recipient-local, and product-internal. This decision does not
qualify Private Preview, does not qualify default Beta, and does not change
release posture. The read-state behavior must be separately exercised in the
running stack before any live Preview claim is made; the implementation is
proven by focused backend, frontend, and migration tests.

## Proof and completion

- `tests/routes/test_direct_message_read_state.py` — unread derivation,
  cursor advancement, repeated reads, new messages after a read, participant
  isolation, and unauthorized access.
- `tests/migration/test_direct_message_read_cursor_migration.py` — real-Postgres
  upgrade, table shape, round-trip, uniqueness per (profile, conversation),
  independent per-participant cursors, and downgrade.
- `frontend/src/components/direct-messages/__tests__/DirectMessageInbox.test.tsx`
  — badge rendering, clearing on open, recovery after reload, refresh while
  open, and the no-cursor-advance-on-refresh invariant.
