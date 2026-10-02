# Private Preview Messaging Request Implementation and Proof

Updated: 2026-10-02. Branch: `feature/user-messaging-and-discovery`.
Governing decision: [ADR-097](./adr/097-private-preview-message-requests-and-consent.md).
This ledger records scoped automated and live evidence. It does not qualify
Guardian participation, providers, federation, or the broader release.

## Source reconciliation and atomic tasks

The feature branch fast-forwarded from `529f9e709` to local main
`62ae93c3ef8a9febd4022e7b9988e2574132f66d`. Fetched origin/main was
`d384fe74ea50ca6493cf5842e5990c62bfbfc07e`, already an ancestor of local main.
Initial worktree was clean. No push, merge to main, or user deployment occurred.

1. Storage/decision: `f92558406`; ADR-097, canonical tokens, additive schema,
   honest historical consent backfill and participant-local history projection.
2. Consent service/API: `be1922678`; transactional materialization, authorization,
   idempotency, suppression, expiry, rate bounds and direct API consent gates.
3. People/Inbox and support posture: deliberate username, discovery, introductory
   request, actions, history, explicit refresh and existing conversation entry;
   Private Preview enabled, Friends & Family retained, default Beta unavailable.
4. Final proof: focused automated suite, independent-connection PostgreSQL races,
   real authenticated two-browser Preview exchange and independent durable
   readback, third-party denial and real default Beta exclusion, detailed below.

## Requirement audit

Test names below are in `tests/routes/test_message_requests.py` unless another
file is named. UI evidence is in the Inbox/MessageRequestPanel and client tests.

| Requirement | Evidence |
| --- | --- |
| Preserved same-node hierarchy and account authority | `test_discover_request_accept_converse_and_durable_readback`, live readback |
| Deliberate mutable username, stable Profile_ID, no email derivation | `test_direct_messages.py`: claim/rename/unset tests; both live browser claims |
| Username-only discovery, safe social fields, Node+Profile destination | `test_direct_messages.py`: search/privacy/nonlocal tests; live A searches B |
| Username required only for discovery/initiation, historical continuity | `test_username_initiation_gate_and_existing_conversation_continuity` |
| Preview/Friends & Family enabled; default Beta unavailable | Manifest/route tests; both real profile health and default route 404 checks |
| Separate durable lifecycle and provenance; canonical tokens | Storage migration/schema/token tests and lifecycle route tests |
| One pending per direction and sender-scoped logical replay | `test_duplicate_attempt_and_pending_direction`; storage unique constraints; PostgreSQL race |
| Deterministic reverse consent with original note first | Reverse initiation test; concurrent independent PostgreSQL connections |
| Recipient-only acceptance; atomic consent/placements/first message | Actor-boundary, rollback and acceptance tests; PostgreSQL acceptance race |
| Exactly once original sender note, honest chronology | Acceptance retry test; real PostgreSQL query verifies one first message and distinct times |
| No Contact, Project, Guardian, retrieval, memory or federation authority | `test_same_node_auth_and_no_unrelated_mutation`, forbidden dependency test; live two null project placements |
| Recipient-only decline, distinct suppression, generic sender failure | Decline/suppression and actor-boundary tests; UI action tests |
| Recipient re-initiation restores normal request flow | Decline/suppression recipient re-initiation test |
| Sender-only withdraw; never materializes; neutral pair retained | Withdrawal and actor-boundary tests; UI action tests |
| Durable 30-day expiry; ended rows leave active list | Parameterized expiry/history tests |
| Default retained history; own opt-in cleanup only | History/local retention/accepted-message preservation tests; UI history tests |
| Authentication, bounded discovery/rate; no identity injection | Hour/day budget, request validation, actor/nonparticipant tests; live missing auth 401 |
| Historical IDs, placement, chronology and idempotency preserved | Actual SQLite and full-chain PostgreSQL migration/backfill/downgrade; existing DM regression tests |
| No fabricated old requests or consent from neutral pairs | Storage backfill test; neutral relationship bypass test |
| Direct conversation and ordinary-message bypass denied | Neutral conversation bypass and forged conversation-without-consent message tests |
| No existence leaks; same-node and nonlocal enforcement | Actor/nonparticipant/same-node route tests; live third-party empty lists and 404 |
| Existing Inbox extended, explicit refresh, no realtime claims | Six UI regression files; two real browser sessions |
| Narrow ADR; ADR-044 remains Proposed | Accepted ADR-097, index and token doctrine registration |

## Automated evidence

- Backend: `python -m pytest tests/core/test_supported_profile.py tests/ops/test_source_compose_supported_profile_contract.py tests/routes/test_direct_messages.py tests/routes/test_message_requests.py tests/routes/test_message_request_storage.py -q`: 106 passed.
- UI: `pnpm test run components/direct-messages/__tests__/DirectMessageInbox.test.tsx components/direct-messages/__tests__/MessageRequestPanel.test.tsx lib/__tests__/direct-messages.test.ts features/contacts/FloatingConversation.test.tsx features/contacts/ContactsWindow.test.tsx features/onboarding/__tests__/Onboarding.test.tsx`: six files, 69 passed.
- PostgreSQL 15: `TEST_DATABASE_URL=<disposable loopback database> python -m pytest tests/migration/test_message_request_postgres.py -q`: one passed, no skip. Full migration chain and historical continuation; four duplicate initiations, four accepts and opposite-direction initiation on independent connections; downgrade preserves historical messages.
- Production frontend `pnpm build`: passed, existing chunk-size warning.
- Scoped source formatting passed using Prettier 3.6.2 with `--no-config` because repository configuration is a Git LFS pointer.
- Full typecheck is not proven: this checkout has no frontend typecheck script or local tsc. A focused compiler check found existing transitive runtimeTokens/slashCommands/ReactDOM type errors; no changed messaging-file error. These unrelated errors were not changed.
- Documentation validation, DLG source-hash validation and `git diff --check` are part of scoped closeout. Pre-existing README link warnings do not establish runtime failure.

## Live supported-profile evidence

Proof used a fresh, disposable Compose project `codexify_message_request_proof_dda8`,
canonical base Compose plus Private Preview overlay and the canonical runtime image
built from this branch. Source/config mounts were read-only; all writable data was
isolated. Real PostgreSQL, Redis, auth sessions, full migrations and production
frontend were used. The task override served the built frontend through nginx,
mounted the existing local embedding model read-only, and exposed only loopback
`127.0.0.1:18089`. This was not the user's deployment or personal account data.

1. Separate real browser sessions signed in Accounts A/B and deliberately claimed
   `proof-alice` / `proof-bob` on node `node-7f77c21ff3f34778b6e1e8ee916d3d43`.
2. A searched `proof-bob`, selected the safe social result and sent one introductory
   note. No ordinary conversation existed before consent.
3. B refreshed requests, saw A's note and accepted through Inbox.
4. B sent an ordinary reply; A reopened Inbox, read it and sent a reply. B reopened
   the conversation and read all three messages. No realtime delivery was claimed.
5. Independent authenticated HTTP sessions for both accounts returned identical
   three-message durable history. Missing auth returned 401.
6. Independent PostgreSQL readback found accepted request
   `477ee5aec4904935a73321c51dad7a35`, one conversation
   `bc4deedcaebd4557b321da5ec28a782e`, exactly one introductory message
   `72ba0227dc2447a98a64e49673de592d` authored by original Profile A, and three total
   messages. Request creation `22:43:03.020084Z` and materialization/acceptance
   `22:43:19.945583Z` remained distinct. Consent source was `accepted_request`;
   two local placements had no Project grant.
7. A third real authenticated account returned empty relationship/conversation
   lists and 404 for relationship conversations, direct conversation and messages.
8. Preview `/health` reported `v1-whooshd-deepseek-web`, valid, no mismatches and
   `direct_messages` mounted. Its existing cloud-lane release hold remained;
   this proof does not qualify provider execution or broad release readiness.
9. Sequential real default Beta startup reported `v1-local-core-web-mcp`, valid,
   no mismatches and no `direct_messages` mount. Operator-authenticated discovery,
   relationship, request and social-identity URLs all returned 404.

Private evidence and disposable credentials stayed outside Git in
`/private/tmp/dda8-message-runtime`; safe PostgreSQL/API/profile records were
retained there. Browser artifacts were moved there before committing. An initial
concurrent Beta startup exhausted the proof VM memory and terminated the task's
Preview backend; only that task-owned backend was recovered, and the final Beta
check ran sequentially. No user containers or data were modified.

## Limits and follow-through

Same-node human messaging is proven for this branch's isolated Preview runtime.
The user's live Preview was not upgraded, and no request was sent to the colleague.
Both real participants must claim usernames after deployment; email search remains
outside this username-discovery slice. Guardian invocation, Lenses, Project sharing,
Contacts, federation, attachments and realtime remain outside this decision.
No additional KB expansion is required for this bounded slice; ADR-097, the Direct
Messaging Contract, current state and this evidence ledger provide the entrypoints.
