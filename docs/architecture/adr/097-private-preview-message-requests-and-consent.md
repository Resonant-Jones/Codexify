# ADR-097: Private Preview Message Requests and Consent

- Status: Accepted
- Date: 2026-10-02
- Human authorization: Resonant Jones's messaging goal and attached `goal-objective.md` for this task.
- Governing anchors: ADR-079, ADR-080, Direct Messaging Contract, canonical token doctrine, account ownership and supported-profile governance.
- ADR-044 remains Proposed; this decision reuses only its explicit lifecycle principle.

## Decision

Add a durable MessageRequest for same-node human Profiles. Preserve
`Node_ID -> Profile_ID -> Relationship_ID -> Conversation_ID -> Message_ID`.
A Relationship remains the neutral unordered pair. It may be resolved before
consent, and never means Contact, friendship, trust or permission.

Acceptance is the boundary for initiating ordinary Conversations and sending
Messages. An owned Profile and Relationship participant authority are still
required. Only a recipient accepts/declines; only a sender withdraws.
Canonical request states are `pending`, `accepted`, `declined`, `withdrawn`,
`expired`, registered in `guardian.messaging.tokens`. Pending expires after
30 days as a durable transition, including when an account returns later.
The transition time for expiry records its deadline, not the next read time.

## Identity, privacy and solicitation

Username is a deliberate mutable node-scoped discovery alias. Claimed username
is required for username discovery/request initiation, not Profile existence
or continuing established Conversations. Addressing uses Node_ID + Profile_ID.
Email and internal account identifiers remain private. These APIs authenticate
through account ownership; model/prompt logic cannot authorize messaging.

Requests have one nonblank plain-text note (maximum 32,000 characters) and a
required sender-scoped idempotency key. At most one pending attempt exists per
sender -> recipient direction, enforced by a partial unique index. A modest
sender budget of 10 new attempts/hour and 50/day prevents trivial solicitation
spam. Existing attempt retries do not consume a new budget.

Decline records separate durable directional solicitation suppression owned
by the recipient. A sender sees only a generic inability to initiate, never
private suppression/moderation policy. Recipient re-initiation explicitly
clears their prior suppression and can establish consent. This is not a full
blocking/muting system.

## Transaction and race discipline

Lock the neutral pair row to serialize both directions. For initiation,
lock the sender Profile first to serialize its rate/idempotency budget, then
lock the pair. A reverse initiation against a pending request is affirmative
consent: accept the original request, retaining its original sender and note
as the first Message. Preserve the reverse initiator's note as the second
human Message and bind their idempotency key to the same accepted request.
No second pending request is created. Repeated keys with different payloads
fail; simultaneous different keys in the same pending direction reuse the
pending request only when the note matches.

Acceptance commits request state, consent provenance, initial Conversation,
participant-local placements and introductory Message together. Original
request creation time remains on the request; materialized Message time is
acceptance time. Unique materialization pointers and pair locking prevent
retry/race duplication. Withdrawal/expiry/decline cannot materialize a note.
Accepted pair consent permits later distinct Conversations using the existing
API; neutral Relationship existence alone permits none.

## History and compatibility

Postgres owns shared request truth, attempt idempotency, consent and suppression.
Participant-local visibility and account preferences are separate tables.
Default retain; opt-in automatic history cleanup hides declined/withdrawn/
expired entries only for that account. It never deletes canonical audit
lineage, another account's history, an accepted Conversation or a Message.
Explicit archive uses the same local visibility boundary.

Migration backfills consent only for pairs that already have Conversations,
with source `historical_conversation` and their earliest creation time.
It creates no synthetic historical MessageRequests. Existing IDs, origin,
placement, ordering, sender authorship and message idempotency remain intact.
New consent has source `accepted_request` and actual request lineage.

## Authority and support boundary

Acceptance grants ordinary human direct messaging only. It grants no Contact,
trust, Project membership, Thread/KB access, Guardian invocation/retrieval,
memory, disclosure, federation, Lens, attachment or realtime authority.
The service creates no inference, embeddings or Guardian work.

Private Preview (`v1-whooshd-deepseek-web`) will enable `direct_messages` once
the complete consent seam is implemented and proved. Friends & Family remains
enabled where already supported; default/public Beta remains unavailable.
Opening/refreshing People/Inbox provides delivery visibility in this slice.
This decision authorizes implementation; it does not assert runtime completion.

## Proof and completion

Implement in prerequisite order: schema/tokens -> consent service/API ->
People/Inbox -> supported-profile posture -> automated and two-account runtime
proof. Test directional uniqueness, reverse initiation, retry/races, atomic
rollback, actor authority, expiry/local history, historical compatibility,
privacy and route gating. Record test evidence separately from live supported
Private Preview proof. Guardian/project/federation and public Beta remain
outside this decision.
