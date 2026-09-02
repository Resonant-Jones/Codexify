# Share Sheet Person-Aware Routing — Runtime Qualification Proof

- Date: 2026-09-01
- Lane: `architecture-impact`
- Task: Add Person Routing to the Codexify Share Sheet
- Base: `15be16bc2` (People messaging runtime-qualified)
- Verdict: **PASS** (one task-discovered posture authorization, below)

## What was proven

The Share affordance is now a person-aware routing sheet. It composes two
existing authority-bearing contracts — the tokenized read-only share-link
contract and the direct-message Conversation routing contract — without
introducing a new authority, a second People state owner, or a second
floating-window manager. Person routing reuses the single global People
messaging state owner (`usePeopleMessagingState`, hoisted to `AppShell`).

## Gate results

| # | Gate | Evidence |
|---|------|----------|
| 1 | Share opens the Sheet (not one-click copy) | Live `/chat/1`: Sheet renders with `Copy Link` + `Send to Person`, honest legibility copy ("sends it in this conversation. Anyone with the link can view it.") |
| 2 | Open + close with no action → zero side effects | Server counts after open/close: `shared_links=0`, no DM writes |
| 3 | Copy Link → one SharedLink row + read-only retrieval | Two UI clicks → two rows; token retrieve returns target `thread 1` read-only |
| 4 | Send to Person → resolve Profile → Relationship → Conversation choice | Live: search `sharebob` → 1 result → relationship resolved → New + 3 existing Conversations listed, each labeled "Existing conversation — its origin and placement are never changed." |
| 5 | Send into existing C1 | DM lands in C1 with the share URL; C1 origin stays `(null, null)`; floating People conversation opens on C1 showing the message |
| 6 | New Conversation under Thread scope | API-orchestrated mirror of `computeOrigin` from `/chat/1`: C3 created with origin `(2,1)`, placement `2`, one message |
| 7 | Peer readback | Bob reads the share-URL message in C1 via his own Conversation read |
| 8 | Partial failure → honest error + retry reuses the SAME link | Live injected mid-flight XHR abort: sheet shows "Share link created, but the message was not sent. Retry Send" with the URL; Retry Send delivers the SAME link (no new `shared_links` row) |
| 9 | Idempotent retry (backend) | Same `client_message_key` replay returns the original `message_id`, `replayed=true`, no duplicate |
| 10 | Unsupported profile fail-closed | noDM runtime (`v1-local-core-web-mcp`, `direct_messages` quarantined): Sheet opens, "Send to Person — Direct messages are unavailable in this profile.", Copy Link usable (creates a link), **zero** DM network calls/writes |
| 11 | Isolation | `chat_messages=0`, `hosted_rooms=0`, sole `uploaded_documents` row = startup demo seed; the only outbox events are `share.created`/`share.accessed` from the pre-existing share route's own observability (existing contract behavior, not Share Sheet side effects) |

## Task-discovered authorization (recorded, operator-approved)

The `share` route label was **quarantined on every supported profile** at
this HEAD — the pre-existing one-click `ShareButton` was live-inert
(`POST /api/share` → 404) everywhere. The operator (2026-09-01) authorized
unblocking on the Dev environment ("Production is on an entirely different
machine"). Posture change applied and pinned by tests:

- `config/supported_profiles/v1-friends-family-web.yaml`: `share` moved from `quarantined` → `enabled`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`: `share` moved from `quarantined` → `enabled`
- `tests/core/test_supported_profile.py`: quarantine pin updated; now asserts `share` is `enabled` on the tester profile

No share-link backend semantics changed. The token-based access model is
unchanged; "Send to Person" is presented as link + private transport, not
recipient-exclusive access.

## Frontend/backed evidence at close

- Focused frontend suites (Share Sheet + ShareButton + share-links + desktop-url + direct-messages): 49 passed
- Backend suites (share links + direct messages + supported-profile posture): green
- Production frontend build: PASS
- ESLint on all task-owned files: clean
- `git diff --check`: clean
- Full frontend suite: run under system node (Hermes node runtime is unstable for the full suite — known environment limitation, see task log)

## Scratch runtime accounting

- Proof DBs `codexify_share_*`, `codexify_share_nodm_*` — dropped
- Redis DB 13 — flushed
- Backends `127.0.0.1:8765` (friends-family) / `:8766` (noDM), vite `:5199` / `:5200` — stopped
- All credentials proof-local placeholders; nothing real preserved
