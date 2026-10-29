# Private Preview Same-Node Direct Messaging — Live End-to-End Proof

- Date: 2026-10-26
- Verdict: **PASS (qualified)** — the complete same-node messaging flow runs on
  the running Private Preview. Two procedure sub-steps are **not applicable**
  because the direct-messaging product has no unread indicator and no persisted
  read state, and one **search-form** observation fails at the serving tip.
- Evidence posture: `proven-live-runtime`
- Scope: same-node only. Cross-node discovery, pairing, and transport are not
  touched. Release status remains `HOLD`; default Beta remains unqualified.

## Base

| Item | Value |
| --- | --- |
| Compose project | `codexify_private_preview` |
| Serving worktree | `/Volumes/Dev_SSD/offload/codex/worktrees/main-reconcile-20261021` |
| Serving branch | detached HEAD (the worktree's serving commit is an ancestor of `main`) |
| Serving commit | `57184dfbe1e3e98a5e03cd5669af1cf574417d04` — "Merge branch 'main' into HEAD" — 2026-10-21 17:43:00 -0400 |
| Compose config | `<worktree>/docker-compose.yml` + `docker-compose.private-preview.yml` + `docker-compose.private-preview-serving.yml`, `--project-directory /Volumes/Dev_SSD/Codexify-main` |
| Env file | `/Volumes/Dev_SSD/Codexify-main/.env.private-preview` |
| Source coupling | `guardian/`, `backend/`, `config/`, `plugins/`, `tests/` are **bind-mounted** from the serving worktree, so the live code is that worktree's files at `57184dfbe` |
| Backend image | `codexify-backend-runtime:latest`, built 2026-10-21T19:27:56Z |
| Browser origin | `http://127.0.0.1:8081` (the only browser-facing local origin) |
| Supported profile | `v1-whooshd-deepseek-web` |
| Node_ID (local) | `node-a1530b7625d2470cb4e3ef34d13652d5` |
| Stack state | `backend` healthy, `frontend`, `private-preview-origin`, `db`, `redis`, and all workers up; `migrator`, `graph-init`, `model-prep`, `private-preview-auth-posture`, `e2e` one-shot jobs exited 0 |

The stack was already running on this tip before the proof: the backend
container's `StartedAt` was `2026-10-23T08:29:29Z` with container id
`426f702f561d…`. The backend was force-recreated three times during the proof
(same project, same three config files) to pick up a temporary allowlist
change; see *Environment changes and restoration*.

## Test accounts

Four synthetic accounts were provisioned for this proof. Every one uses an
RFC 2606 reserved `example.invalid` address, so none can correspond to a real
person. All four are `guest` role, all four hold an `active` deliberately
claimed username, and all four resolved to the **same** Node_ID.

| Role in proof | Email | Username | Profile_ID |
| --- | --- | --- | --- |
| A | `proof-alpha@example.invalid` | `proofalpha` | `7d29b725ad194ef88e52af01820a10b3` |
| B | `proof-beta@example.invalid` | `proofbeta` | `e505e91cecc643d9833ab86ebdef9eff` |
| C | `proof-charlie@example.invalid` | `proofcharlie` | `17914611f1af48ddb29cec63f3cdc109` |
| D | `proof-delta@example.invalid` | `proofdelta` | `5824192aa6e1468c883864b6c99ab14b` |

No existing account, real or synthetic, was reused. No real person's profile
was touched. Account credentials were generated in-process inside the backend
container, never printed, and written only to mode-600 files outside the
repository; the browser sessions were established by injecting an already-minted
session token fetched by the page from a loopback-only broker, so no password,
session token, or activation link appears in this record, in any tool call, or
in any transcript.

## Procedure results

| # | Step | Verdict |
| --- | --- | --- |
| 1 | Serving worktree / branch / commit identified; stack running on that tip | **PASS** |
| 2 | `/health` reports the expected profile; `direct_messages` mounted | **PASS** |
| 3 | A finds C by same-node People search and sends a message request | **PASS** (bare and partial handle) / **FAIL** (`@`-sigil form — see *Search form at the serving tip*) |
| 4 | C sees the request inside Codexify, accepts it, and sends a reply | **PASS** |
| 5 | A sees the reply in the internal conversation | **PASS** |
| 6 | A sends another message; the recipient's side updates | **PASS** for delivery / **NOT APPLICABLE** for an unread indicator |
| 7 | Reload and navigate away and back; messages remain available | **PASS** / **NOT APPLICABLE** for persisted read state |
| 8 | Fresh relationship declined → no accepted conversation; further contact prevented | **PASS** on two independent fresh relationships |

All timestamps are 2026-10-26, EDT (UTC−04:00). The HTTP harness ran
09:45–09:52; the browser sessions ran 09:53–10:01.

## Step 2 — health and mounted route

`GET http://127.0.0.1:8081/health`:

```
profile=v1-whooshd-deepseek-web  valid=True  mismatches=[]  mounted_count=23
direct_messages_mounted=True  share_mounted=False
```

`share` is quarantined at this serving tip, as expected: the share-route
admission and the People-search `@`-sigil fix both landed on `main` **after**
`57184dfbe` and are not in the serving worktree.

## Step 3 — People search and message request

HTTP harness, as A:

| query | hits | usernames |
| --- | --- | --- |
| `proofcharlie` | 1 | `proofcharlie` |
| `proofc` | 1 | `proofcharlie` |
| `@proofcharlie` | **0** | — |

Browser, as A, at `http://127.0.0.1:8081/chat` → People → Find People:

- `@proofcharlie` → the Inbox region rendered the empty state
  **"No profiles match that username."** with zero result rows
  (`emptyStatePresent: true`, `resultRows: []`).
- `proofcharlie` → a result row rendered `proofcharlie` / `@proofcharlie`, and
  the empty state disappeared (`emptyStatePresent: false`).

Selecting the result opened the **Introductory message request** composer —
"Send a message request to proofcharlie", "They must accept before an ordinary
conversation starts." — with the Send button disabled until a note was
entered. Sending produced `request_id=8585adc1014c46ad8f0fc0647579e4a1`,
`state=pending`, `conversation_id=None`, `replayed=False`, and the Inbox
request panel then showed **"To proofcharlie · pending"** with a
"Withdraw request" affordance.

**Discovery did not authorize messaging.** The search result produced a
*request*, not a conversation, exactly as the contract requires.

### Search form at the serving tip — FAIL

The `@`-sigil form returns nothing at the serving tip, in both the API and the
browser UI. This is the reported symptom, reproduced live. The cause is not a
product regression: `main` carries the canonicalization fix
(`service.normalize_search_query`, commit `18eb0c1d2`), but the serving
worktree is pinned at `57184dfbe` from 2026-10-21 and does not include it. The
bare handle and a partial handle both resolve at this tip.

**Operational consequence:** the running Private Preview still exhibits the
People-search miss until the serving worktree is re-reconciled onto a commit
that includes `18eb0c1d2`. This proof does not change the serving pin.

## Step 4 — recipient sees, accepts, and replies

As C, the Inbox message-requests region rendered **"From proofbeta · pending"**,
the note text, "Requested 10/26/2026", and **Accept request** / **Decline
request**. Clicking **Accept request** returned `state=accepted`,
`conversation_id=604b7433c2bc401aa80c8e723387f282`,
`first_message_id=8bcdbdd13add40c4a6aca683b13b81c2`.

The app moved straight into the conversation view, whose transcript contained
exactly one message — the original note, `proof 2026-10-26 beta-to-charlie
browser` at 09:55 AM — confirming the contract rule that the original note
becomes the first Message authored by the original sender. C's reply
(`proof 2026-10-26 charlie-reply browser`, 09:57 AM) was sent from the same
conversation view and appeared immediately in the transcript.

## Step 5 — sender sees the reply

As B, the Inbox conversation row appeared with peer `@proofcharlie` and latest
preview `proof 2026-10-26 charlie-reply browser`. Opening it showed both
messages in chronological order. The HTTP readback for A showed
`message_count=2` with bodies
`['proof 2026-10-26 alpha-to-charlie', 'proof 2026-10-26 charlie-reply']`.

## Step 6 — a second message, and the unread question

A sent `proof 2026-10-26 alpha-second` (API) and `proof 2026-10-26
beta-second browser` (browser). The recipient's Inbox row updated its
latest-message projection to `proof 2026-10-26 beta-second browser`
(`latest_message_id=913e18bf9f6d473db6f528337f3573ee`), and the recipient's
transcript grew to three messages.

**NOT APPLICABLE — the direct-messaging product has no unread indicator and no
persisted read state.** This was checked, not assumed:

- The conversation payload carries no read/unread/seen field
  (`readStateFields: []` on every conversation row read).
- The database has no read-state table and no read/unread column on any
  `direct_message*` table; `direct_message_relationship_participants` holds
  "no roles, groups, mute, read state, or delivery state" per the contract.
- The frontend direct-messaging surface renders only peer label, activity time,
  subtitle, latest-message preview, and origin label on a conversation row.
  There is no badge, count, or "new" marker anywhere in the People/Inbox
  surface.
- The contract and ADR-079/080 defer delivery/read receipts; the 2026-09-01
  qualification proof lists "delivery/read receipts" as deferred.

So "an in-app unread indicator appears" and "the unread count clears" have no
runtime artifact to observe. What the product does provide is a
latest-message preview projection, and that projection is what demonstrably
updated on the recipient's side when a new message arrived. This is recorded as
a **product gap in the procedure's expectation**, not as a live defect.

## Step 7 — reload and navigate away and back

The recipient's page was fully reloaded, then People reopened:

- Both conversation rows were still present with their latest previews intact
  (`proofbeta … proof 2026-10-26 beta-second browser`).
- Reopening the conversation showed all three messages in chronological order
  (`beta-to-charlie browser` 09:55, `charlie-reply browser` 09:57,
  `beta-second browser` 09:58).
- Navigating back out of the conversation and to the list still showed both
  rows.

Messages remain available across reload and navigation.

**NOT APPLICABLE — "the read state remains cleared for B".** With no persisted
read state and no unread badge, there is no read state to remain cleared. The
contract deliberately keeps read state out of the shared model.

## Step 8 — decline and prevented further contact

Two **independent fresh relationships** were used, neither of which had an
accepted conversation or any prior request at the start of its case.

**Fresh pair 1 — C → D.** C's request appeared in D's Inbox as
"From proofcharlie · pending" with Accept / Decline. D clicked **Decline
request**. After the decline:

- D's Inbox showed **0 conversation rows**, and `GET /api/direct-messages/conversations`
  as D returned **0 conversations**.
- The request history for C reads `state=declined`,
  `conversation_id=null`.
- C's second request to D was refused in the UI with
  **"Unable to initiate this message request"** (API: HTTP 400,
  `error=message_request_unavailable`). The request was not created.

**Fresh pair 2 — B → D.** Same shape: request pending, D declined, **0
conversation rows and 0 API conversations** for that pair, and B's follow-up
request refused with HTTP 400 `message_request_unavailable`.

**On "block":** the contract specifies decline-based **directional suppression**
as the mechanism that prevents further contact, and states plainly that "This
does not implement full blocking/muting." Full blocking/muting is deferred
(contract §7, §10). What is proved live is therefore the contract's actual
behavior: a decline creates no accepted conversation, and the declined
sender's further requests are refused with a generic error that does not
disclose the private policy behind the refusal.

## Isolation bracket

Window `2026-10-26 13:40:00Z` → end of proof.

| Table | Rows in window |
| --- | --- |
| `chat_messages` | **0** |
| `events_outbox` | **0** |
| `memory_entries` | 0 (total) |
| `hosted_rooms` | 0 (total) |
| `direct_messages` | 9 |
| `message_requests` | 6 |
| `direct_message_conversations` | 3 |
| `direct_message_consents` | 3 |
| `message_request_suppressions` | 3 |

The messaging flow produced no Guardian chat message, no queued event, no
memory entry, and no hosted room. The three accepted pairs each produced
exactly one consent row, while six relationships exist — consent is distinct
from the neutral relationship, as the contract requires.

## Environment changes and restoration

| Change | Scope | Restored |
| --- | --- | --- |
| `CODEXIFY_PREVIEW_APPROVED_EMAILS` in `.env.private-preview`: four synthetic `example.invalid` addresses appended | untracked operator env file, outside the repository | **Yes** — restored byte-for-byte from a mode-600 pre-proof backup (sha256 `8e40ff0cd6cb053a2d76ff3aef84888d89a1a63cefe283d1d5b151b61a3bbccb`); no `example.invalid` entry remains |
| Backend container force-recreated 3× | same Compose project and same three config files | Final container healthy, profile `v1-whooshd-deepseek-web`, `valid=True`, `mismatches=[]`, 23 mounted routes, `direct_messages` mounted, `share` quarantined |
| Four synthetic `users` + `user_profiles` rows and their messaging rows | preview database | **Left in place as proof evidence.** The accounts can no longer authenticate: login returns HTTP 401 `Invalid username or password`, and a previously issued session token returns HTTP 401 `Private preview requires an approved authenticated email` |
| Loopback token broker on 127.0.0.1:8931 | host process, bound to loopback, serving mode-600 token files | Process stopped after the run |

No product source file, schema, migration, Compose file, Cloudflare
configuration, release posture, or approved real account was modified. Nothing
was deployed and nothing was pushed.

## What this proves

- Two (here four) approved test accounts on the same node complete the real
  direct-messaging flow on the running Private Preview: same-node People
  search by bare and partial handle, a message request, recipient visibility
  of that request inside Codexify, acceptance, reply, sender-side read-back, a
  second message, latest-message projection update on the recipient, and
  message availability across a full page reload and navigation away and back.
- Discovery does not authorize messaging: the search result yields a request
  and the composer states that the recipient must accept first.
- Decline creates no accepted conversation, and the declined sender's further
  requests are refused with a generic, non-disclosing error.
- The messaging flow produced no Guardian chat, event, memory, or room side
  effects.
- `/health` at the serving tip reports the expected profile with
  `direct_messages` mounted and no profile drift.

## What remains unproven

- **Cross-node messaging.** Nothing here says anything about cross-node
  identity discovery, node resolution, pairing, or transport. Discovery is
  same-node by construction. ADR-079/080 keep those deferred.
- **Default Beta qualification.** A passing same-node Private Preview proof
  qualifies neither the default Beta lane nor any public posture. Release
  status stays `HOLD`.
- **Unread indicators and persisted read state.** Not implemented in the
  direct-messaging product; no runtime evidence is possible until they exist.
- **Full blocking/muting.** Not implemented. Only decline-based directional
  suppression is proved.
- **The `@`-sigil People-search fix on the running origin.** Present on
  `main`, absent from the serving tip; the preview still exhibits that miss.
- **Realtime delivery, attachments, Guardian retrieval, share links, and
  Project-scoped messaging** remain deferred or quarantined and were not
  exercised.

## Browser evidence artifacts

Viewport screenshots captured during the browser sessions, held outside the
repository (the authorized-files list for this task is documentation-only):

```
/Users/chriscastillo/.scratch/proof/shot-01-charlie-inbox-after-accept.png
/Users/chriscastillo/.scratch/proof/shot-02-charlie-reply-sent.png
/Users/chriscastillo/.scratch/proof/shot-03-charlie-inbox-new-message.png
/Users/chriscastillo/.scratch/proof/shot-04-charlie-transcript-after-reload.png
/Users/chriscastillo/.scratch/proof/shot-05-charlie-further-contact-blocked.png
```

## ADR impact

**None.** ADR-079/080 govern the messaging boundary and ADR-097 governs
Private Preview request and consent behavior. This task gathered runtime
evidence without changing any contract. The one contract clarification added
alongside this record — the direct-messaging contract's §2a and §6 wording for
username search, already landed on `main` — documents behavior these ADRs
already required; it does not alter them.

## Supporting evidence

- Harness log: `.scratch/proof/evidence.json` (27 recorded observations, 26
  pass / 1 fail — the fail is the `@`-sigil search form documented above).
- Browser sessions were driven through the real Vite-served SPA on the private
  preview origin at `http://127.0.0.1:8081`, not against a stub or a scratch
  runtime.
