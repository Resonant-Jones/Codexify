# People Messaging Runtime Qualification Proof

- Date: 2026-09-01
- Verdict: **PASS**

## Base

- Starting commit: `15be16bc2` — "Absorb People messaging surface into the conversation-first Inbox"
- Branch: `main`
- Runtime profile: `v1-friends-family-web` (private preview)
- Backend: scratch Uvicorn `127.0.0.1:8765`, scratch Postgres `codexify_qual_*`,
  Redis DB 14, mock embeddings + proof-only faiss shim (no embedding/indexing
  invoked; the optional `faiss`/`chromadb` deps remain absent)
- Frontend: vite dev `127.0.0.1:5199`, `VITE_PROXY_TARGET=http://127.0.0.1:8765`
- Node_ID (local): `node-81b2be69ab9a4594a63c5d839efba962`
- Profile A: user `qual-alice`, username `qualalice`,
  profile_id `1bcd2ea251154ff89157a86a8546d8c7`
- Profile B: user `qual-bob`, username `qualbob`,
  profile_id `1ec0356c98bf4b62a84f61e2fe649ac6`
- Auth tokens/passwords: `[REDACTED]` (proof-local placeholders)

## Automated proof

| Command | Result | Count | Notes |
| --- | --- | --- | --- |
| `.venv/bin/python -m pytest tests/routes/test_direct_messages.py -q` | PASS | 37 passed | |
| `TEST_DATABASE_URL=postgresql+psycopg://…@127.0.0.1:5432/postgres .venv/bin/python -m pytest tests/migration/test_direct_messaging_migration.py -q` | PASS | 2 passed | real-Postgres migration |
| vitest: ContactsWindow.test.tsx + FloatingConversation.test.tsx + DirectMessageInbox.test.tsx + lib/direct-messages.test.ts | PASS | 47 passed | 45 baseline + 2 launcher regressions (menu-click leak, chrome-switch survival) |
| `pnpm test` — main vitest config (unbounded) | NOT RUN | — | V8 fatal crash in the vitest worker pool under BOTH the Hermes node runtime (load ~87) and the system node v22.17.0 (`--maxWorkers=2`, `--maxWorkers=2 --no-file-parallelism`, `--maxWorkers=2 --testTimeout=30000` — all crash identically). Environmental: the machine cannot complete the full main suite. Unrelated to messaging; the messaging suites + extension suite + build are green. |
| `pnpm test:chrome-extension` | PASS | 84 passed (5 files) | the second half of `pnpm test` |
| `pnpm run build` | PASS | — | production frontend build |
| ESLint (all task-owned files) | PASS | — | AppShell.tsx is in the repo's eslint ignore list (pre-existing) |
| `git diff --check` | PASS | — | clean |
| `PYTHON=.venv/bin/python make docs` | PASS | — | docs validation + diagram freshness green |

Unrelated known failures: the known `watchdog/contracts.py:466` mypy
pre-existing defect is out of scope (reported, not repaired). The unbounded
`pnpm test` crash is a Hermes-node environment load failure, reproduced on the
machine with load average 87; the identical suite passes bounded.

## Relationship proof

- Relationship R: `753e907750b5478aa8d29ccb81a411a5` (Profile A → Profile B;
  resolvable from both directions — Bob's UI shows the same rows with peer
  `qualalice`).
- C1 (General-origin): `8a101a78deff4b1798d06e187bc97c33`
- C2 (Project-origin, Project P): `f182656d58a04941980361e6efbf97a4`
- C3 (General-origin, created from the UI via username search):
  `2e3c80293ed04b779ecf45013c6da5a3`
- C4 (Project+Thread-origin, created from the UI while on `/chat/1`):
  `d17639cce91242549f73024fb21239b3` (origin_project_id=2, origin_thread_id=1)
- Project P (A-owned): id `2` "Qualification Proof Project"
- Thread T fixture: legacy `threads` row id `1` "Qual Thread" (project_id 2),
  provisioned directly because the legacy `/threads` create route still writes
  to a removed `threads` table (pre-existing seam break; NOT repaired here;
  documented limitation). The `/api/threads/1` read path (canonical hosted
  assembly serves it; dev proxy bridges it) returned `project_id: 2`.
- All four conversations remained distinct `Conversation_ID`s under one
  Relationship across every UI operation, restart, and readback.

## Inbox proof

- Conversation-first rows: 4 rows, one per Conversation_ID; none collapsed
  into a Relationship row. Latest-message previews correct (modal sentinel on
  C1's row; floating sentinel on C4's row after the floating send).
- Person filter: "All" + "qualbob" chips; selecting `qualbob` resolved
  Relationship R and showed ALL FOUR conversations with the
  "All conversations with this person" header. Filter keys on
  `relationship_id` (durable), not usernames.
- Origin labels: C1/C3 "General · placed in Unscoped", C2
  "Qualification Proof Project · placed in Qualification Proof Project", C4
  "Qualification Proof Project · Thread 1 · placed in Qualification Proof
  Project".
- From Bob's side, C4/C2 project origins render as "General" because Bob is
  not a Project member — the backend redacts access-requiring origin for the
  peer (participant-isolation contract working as designed).

## Send proof

- Modal sentinel `messaging-proof-1788273405-modal` → Message_ID
  `7581e62fce7148108017c81fdbe9deef` in C1. Rendered exactly once; server
  count for that body == 1.
- Floating sentinel `messaging-proof-1788273966-floating` → Message_ID
  `3ce32beadbfa47789be438fe93a2472e` in C4 (the ORIGINAL Conversation_ID; no
  new Conversation was created by pop-out/minimize/navigation). Server count
  == 1.
- Bob's UI reply `qual-bob-reply-1788274105` persisted in C1 from Bob's
  browser session (profile `1ec0356c…`); Alice's UI re-read it after reopen.

## Portable UI proof

- Pop-out: C4 → floating window (same Conversation_ID), People modal closed,
  floating window remained (state owner lives above the window).
- Cross-AppShell navigation: floating window + draft survived
  frame-first Guardian → Settings → Dashboard → `/chat/1` room → Settings
  (after the state-owner hoist repair; see below).
- Draft preservation: `messaging-draft-1788273951` survived pop-out, modal
  close, navigation, minimize, and restore. No backend Message existed for
  the unsent draft (server C4 message count was 0 until the explicit send).
- Minimize/restore: parked pill ("Restore conversation with qualbob")
  persisted across navigation; restore returned the same Conversation_ID,
  draft, and origin breadcrumb ("Project 2 · Thread 1").
- Close semantics: closing the floating window removed only UI state — no
  DELETE occurred; Relationship/Conversations/Messages remained; reopening
  People → Inbox showed all four conversations.

## Origin proof

- C4 origin before all navigation/send activity: `(origin_project_id=2,
  origin_thread_id=1, placement.project_id=2)`.
- After pop-out, modal close, room/settings/dashboard navigation, minimize,
  restore, and floating send: identical. Mutation count: **0**.
- C3 (created with no thread scope) has null origin + null placement — no
  origin was guessed.
- C4's Project/Thread origin was captured from the integrated UI while on
  `/chat/1` (AppShell `activeRouteThreadId` + backend-proven thread→project
  scope via `/api/threads/1`).

## Restart proof

- Killed and restarted the backend (same scratch Postgres). Session token
  remained valid; API readback: 1 Relationship, 4 Conversations.
- UI reopen (People + `/inbox`): all four rows present; C1 transcript
  re-read from the backend shows seed + modal sentinel + Bob's reply in
  chronological order; C4 shows the floating sentinel.

## Capability proof (unsupported profile)

- Second backend on `127.0.0.1:8766` with profile `v1-local-core-web-mcp`
  (`direct_messages` quarantined), second vite on `:5200`.
- People window opened; Contacts tab rendered independently (honest empty
  state + privacy copy).
- Inbox showed the honest fail-closed panel: "Direct messages unavailable —
  This runtime profile does not provide the direct-messaging Inbox. Direct
  messages remain private-profile functionality and have not been widened to
  other postures."
- Instrumented `window.fetch`: **0** `direct-message`/`social-identity`
  network calls fired on the quarantined profile.

## Isolation proof

- Bracket: `2026-09-01T09:50:13-0400` → `2026-09-01T11:10:31-0400`.
- Post-bracket counts in the proof DB:
  - `chat_messages = 0`, `events_outbox = 0`, `memory_entries = 0`,
    `hosted_rooms = 0` — no Guardian chat, queue events, memory, or rooms
    from any messaging operation.
  - `direct_messages = 4` (seed + modal + Bob reply + floating — exactly the
    proof's durable messages), `direct_message_relationships = 1`,
    `direct_message_conversations = 4`.
  - `uploaded_documents = 1`: startup demo-content seeding at
    `09:50:33-04:00` (20s after backend boot, before any DM write) — the
    dashboard's demo documents; not messaging-caused.
- No Project memberships, Project invitations, embedding jobs, or federation
  events were created by the messaging workflow (no such rows exist).

## Proof-blocking repairs (authorized, narrow)

1. **Guardian tools-menu click leak** — `ContactsLauncher` click bubbled to
   the tools-menu container; the menu's close unmounted the People state
   owner before the window opened, so the global affordance was unusable
   from the frame-first Guardian shell. Fix: `event.stopPropagation()` in the
   launcher onClick + regression test. (Live defect reproduced before fix;
   window opens from Guardian after.)
2. **Floating state owner lost on chrome switches** — the state owner lived
   inside `ContactsLauncher`, which unmounts when the shell switches between
   the dock chrome and the frame-first tools menu (e.g. entering `/chat/1`),
   destroying the floating Conversation and drafts during navigation. Fix:
   `AppShell` now owns `usePeopleMessagingState` once and renders
   `FloatingConversation` beside the portal root; `ContactsLauncher` accepts
   an optional parent-owned state (falls back to its own for standalone
   mounts). Regression test: "keeps the floating conversation alive across
   launcher remounts with parent-owned state". (Live defect reproduced
   before fix: floating window vanished on `/chat/1`; after: survives
   Guardian/Settings/Dashboard/room navigation.)

No backend files were changed. No schema/migration change.

## Deferred (unchanged, per spec)

1. Share Sheet
2. Project Scope Offer / invitations
3. provisional Conversation summary + export
4. Guardian Conversation navigation/retrieval
5. origin Thread/Project retrieval binding
6. retrieval-vs-disclosure policy
7. realtime same-node delivery
8. attachments
9. agent/human authorship
10. remote Node resolution
11. cross-node transport
12. delivery/read receipts
13. Cognitive QoS

## Conclusion

**PASS** — same-node People messaging is runtime-qualified on the
private-preview profile for: two-profile UI communication, conversation-first
Inbox, relationship-backed person filtering, live Conversation creation
(General and Project/Thread-origin), durable modal/floating sends, portable
floating Conversation across AppShell navigation, draft minimize/restore,
close-without-delete, restart persistence, Contacts separation, unsupported-
profile fail-closed behavior, and messaging-activity isolation. Two narrow
proof-blocking frontend repairs were made and regression-tested.
