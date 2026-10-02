# Private Preview Messaging Request Implementation and Proof

Updated: 2026-10-02. Branch: `feature/user-messaging-and-discovery`.
Governing decision: [ADR-097](./adr/097-private-preview-message-requests-and-consent.md).
This ledger distinguishes completed prerequisites from the full goal. It is
not a release admission or live runtime proof.

## Source reconciliation

Feature branch fast-forwarded from `529f9e709` to local main
`62ae93c3ef8a9febd4022e7b9988e2574132f66d`. Fetched origin/main was
`d384fe74ea50ca6493cf5842e5990c62bfbfc07e`, already an ancestor of local main.
No user files were dirty. No push, merge to main or deployment performed.

## Prerequisite-ordered tasks

1. **Storage and decision:** ADR-097, canonical lifecycle/consent tokens,
   additive migration, honest historical backfill, request/attempt/consent/
   suppression/local-history tables. Implemented; focused tests pass.
2. **Consent service and API:** transactional acceptance; original authorship;
   canonical pair locking; directional pending/idempotency/reverse initiation;
   decline/withdraw/expiry; recipient-controlled suppression; bounded rate;
   local history cleanup; accepted conversation/message gates. Implemented;
   73 focused backend tests pass. Independent-connection Postgres races pass.
3. **People/Inbox:** claim username, discovery, intro composition, incoming/
   outgoing requests, actions, history/retention, refresh, accepted conversation
   entry using the existing UI. Pending.
4. **Support posture:** enable Private Preview, retain Friends & Family support,
   exclude default Beta; align profile tests/comments/current truth/contract.
   Pending until consent seam is ready.
5. **Automated and live proof:** cover all requirements below, then supported
   Private Preview two-account flow with independent durable readbacks.
   Pending. Storage evidence is not a concurrency or runtime claim.

## Requirement audit

| Requirement | Evidence/status |
| --- | --- |
| Same-node authenticated human messaging; preserved hierarchy | Existing domain retained; new API proof pending |
| Deliberate mutable username, stable Profile_ID; username-only discovery | Existing tests pass; Preview username UI proof pending |
| No email/private owner identity in peer results; address via Node+Profile | Existing tests pass; request privacy proof pending |
| Claimed username required for username discovery/initiation, not historic use | Service/UI enforcement pending |
| Private Preview and Friends & Family enabled, default Beta unavailable | Preview change pending |
| Durable separate request lifecycle and provenance | Additive schema and canonical tokens tested; transitions pending |
| One pending per direction; duplicate logical attempts | DB constraints tested; service/race proof pending |
| Reverse initiation produces deterministic accepted transition | Attempt storage supports lineage; service/race proof pending |
| Recipient-only accept; atomic state/consent/conversation/first message | Materialization constraints tested; transaction/auth proof pending |
| Original sender authorship; honest creation vs materialization time | Schema separates times; service proof pending |
| No extra Contact/trust/project/Guardian/retrieval/memory/federation grants | No new authority added by storage; negative execution proof pending |
| Recipient-only decline; separate suppression; generic sender errors | Suppression storage tested; service/UI proof pending |
| Recipient re-initiation clears their directional suppression | Service proof pending |
| Sender-only withdrawal, no materialization or pair deletion | Service proof pending |
| 30-day expiry is durable transition | Deadline/transition schema tested; lifecycle proof pending |
| Account history retained by default; active list excludes terminal requests | Service/UI proof pending |
| Opt-in local cleanup leaves shared truth/other view/messages intact | Local visibility storage tested; service/UI proof pending |
| Authenticated bounded discovery/requests; rate bound/no existence leaks | Existing discovery tests pass; request proof pending |
| Historical IDs/provenance/placement/order/idempotency remain usable | Additive migration preserves rows; gate/runtime proof pending |
| No fabricated historical requests or neutral-pair consent | Migration test passes |
| Neutral relationship permitted, direct conversation/message bypass denied | Gate proof pending |
| Account ownership to Profile/Relationship/Conversation/Message enforcement | Existing routes pass; new request/auth proof pending |
| Existing People/Inbox extended; no realtime implication or added non-goals | UI pending |
| Narrow architecture decision, ADR-044 remains Proposed | ADR-097 recorded; doctrine registration added |
| Supported Private Preview live two-account proof, third party denied | Pending; no live proof claimed |

## Completed validation

- `python -m pytest tests/routes/test_message_request_storage.py tests/routes/test_direct_messages.py -q`: 51 passed.
- Storage proof executes the actual additive Alembic migration against SQLite,
  checks ORM/schema columns, database rejection constraints, historical-only
  backfill and downgrade preservation. It does **not** prove Postgres locks,
  concurrent service behavior, the supported runtime or route enablement.
- `python scripts/validate_docs.py`: passed.

## Final runtime proof checklist

Both accounts sign in and deliberately claim usernames on one supported node;
A discovers B; A sends one note; B opens/refreshes People and accepts; exactly
one Conversation and one first Message authored by A; both exchange ordinary
messages and independently read durable history. A third account receives no
relationship/conversation existence or content. Default Beta exposes no
messaging capability. Record runtime configuration and evidence separately
from automated assertions. Do not expose credentials or private account IDs.

## Consent API prerequisite validation

- `python -m pytest tests/routes/test_message_requests.py tests/routes/test_message_request_storage.py tests/routes/test_direct_messages.py -q`: 73 passed.
- `TEST_DATABASE_URL=<disposable loopback Postgres> python -m pytest tests/migration/test_message_request_postgres.py -q`: 1 passed against PostgreSQL 15. The test upgrades the complete real migration chain, checks historical backfill/continuation, races four duplicate initiations and four acceptance calls on independent connections, races opposite-direction initiations, and verifies downgrade preserves historical messages. No skips.
- The database was an isolated disposable container, not the user Preview database. This is PostgreSQL service/migration evidence, not authenticated supported-runtime/browser proof.
- Profile budget locks use Postgres `FOR NO KEY UPDATE` to allow foreign-key `KEY SHARE` checks during opposite-direction initiation. Pair locks serialize consent.
