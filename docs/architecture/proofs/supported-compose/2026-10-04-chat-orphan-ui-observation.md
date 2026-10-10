# Durable chat terminal observation in the UI — 2026-10-04

## Authority and scope

Development Operator Level 0, EXECUTE → PROOF. Private Task Spec preceded
implementation, evaluated from repair `cd7be2a5772ae73f0061de3b59d8d639f8481a86`
on `codex/chat-postgres-terminal-deadline-20261003`. The ordinary-chat reliability
Goal and explicit deadline-bound orphan reconciliation authorization govern
this frontend slice. ADR-087/091 and existing attempt/message authority apply;
no ADR, backend schema, deadline policy or runtime token changed.

The parent FAISS snapshot authority implemented earlier remains unchanged; see
[accepted vector deadline proof](./2026-10-04-chat-vector-physical-deadline.md).
This task changes terminal observation and presentation only.

## Behavior and changed surfaces

`ThreadAttemptObservation` keeps serialized authorized receipt reads active for
the current task, even when history has no pending row or that task is outside
the bounded newest-100 window. Each request retains the existing five-second
transport timeout and ten-second polling interval. Unknown evidence never
becomes execution or terminal truth. An absent row keeps observation active;
this does not guarantee recovery of a task permanently outside that window.

Only a same-thread/current-task durable assistant link or a server receipt with
`durable_terminal_outcome_recorded` and failed/cancelled kind can finish the
active UI stream/session and release its local turn lock. Canonical messages
are refreshed first. A completed link takes precedence over stale failure
detail. Failed refresh, Redis-only terminal evidence, invalid identities and
callbacks made stale by authorization/thread/current-task changes do not assign
an outcome or unlock a newer task. Timers and owned requests are cancelled on
identity changes; there is no UI deadline reconstruction or automatic resend.

GuardianChat applies the exact current terminal receipt through the existing
completion session and inference hook. A canonical orphan is presented as an
existing `failed_retryable` state with distinct recovery-deadline wording, not
provider failure or a controlled execution deadline. Generic durable failure
uses existing `failed` presentation without assigning a provider/tool cause.
The optional `durableFailureOnly` flag is local observation provenance only.
Global events, task streams, operator inference snapshots and historical reload
observation preserve this distinction. No worker death time, first output or
completion timing is invented from reconciliation time.

Changed files: `frontend/src/features/chat/GuardianChat.tsx`,
`components/ThreadAttemptObservation.tsx`, `hooks/useInferenceRequestState.ts`,
`requestFailurePresentation.ts`, `frontend/src/types/inference.ts`, the four
neighboring presentation/hook/component/turn-lock test files, and this receipt.
Explicit new user sends continue through the ordinary completion API; server
request/task identity remains authoritative. There is no replay mechanism.

## Validation and evidence limits

Evidence root:
`/private/tmp/codexify-chat-orphan-ui-cd7be2a57-20261004/`.
Task Spec, scratch validation drivers, JUnit/logs, hydrated-file custody and
independent runtime custody are retained. Tests use existing Vitest 3.2.7,
Node and dependency packages. LFS pointers are hydrated only from existing
payloads whose SHA-256 and size match the pointer. No download/install occurred.
Final harness owns its node_modules root, Vite temporary configuration and
cache directories; only package entries link to existing dependencies. The
initial harness used a root dependency symlink; Vite removed its temporary
bundled configuration. That routing was corrected before candidate proof.

Focused command surface, from private scratch `frontend/src`:

```text
node <existing vitest.mjs> run features/chat/__tests__/requestFailurePresentation.test.ts features/chat/__tests__/useInferenceRequestState.test.tsx features/chat/components/__tests__/ThreadAttemptObservation.test.tsx features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx --config <private vitest.config.ts> --maxWorkers=1 --minWorkers=1 --fileParallelism=false --reporter=default --reporter=junit --outputFile.junit=<private XML>
```

The final four suites passed **181 tests**, zero failures/errors/skips.
Coverage includes lost terminal SSE with durable orphan recovery, user-only new
send with a new task, old receipt not releasing that new task, pending/absent
current observation, Redis-only rejection, failed canonical refresh, stale
current-task/authorization callbacks, completion precedence, durable completion
and cancellation controls, orphan code precedence, and no invented timing or
automatic POST. GuardianChat integration uses its actual inference hook with
mock transport, not a native browser or fresh supported-Compose turn.

Initial affected-suite run passed 164 tests. The first new-test run preserved
four fixture failures and 172 passes: a request fixture was outside its describe
scope. Adding the local fixture and resetting the stream fixture repaired the
tests. Subsequent runs passed 178 and 179 tests; final terminal controls passed
181. No product change was made to conceal a test failure.

The scoped ESLint command could not load the repository configuration because
the existing dependency set lacks `eslint-plugin-react`; its stderr is retained.
No lint success or full TypeScript qualification is claimed. `git diff --check`,
`python3 scripts/validate_docs.py` and local receipt-link checks passed.

## Independent preservation and remaining work

Custody matched all **1,138** frozen backend/Guardian runtime source files in the
retained source and both application containers. Retained backend/worker start
instants stayed `2026-10-04T21:47:17.506339553Z` and
`2026-10-04T21:34:16.858728583Z`, restart count zero. Health `ok`, chat queue zero,
turn locks absent, idle heartbeat with positive TTL; evaluation/system queues
34/17 unchanged. Thread 37 messages 70/71, contents and metadata unchanged.
Main stayed `0163521312ef767c0884654e70094ae7b44a5eec` and retained its unrelated
staged dev-log deletion. No application request, migration, service restart or
source refresh was performed.

Retained Compose still uses migration `d4c69e03a712` and earlier source, not the
new recovery candidate. This frontend proof does not qualify deployment,
provider/model generation, real fresh request identity, or runtime orphan
recovery. Unconfirmed admission, permanent window exclusion, remaining SSE
resource bounds and coherent candidate source/schema refresh with fresh
success/failure/loss/retry/restart/shutdown browser proof remain obligations.
Full Goal remains active; release HOLD. No release-truth anchor updated, no
push/merge/deploy/main mutation, and no shared-memory write. Scoped commit hash
is supplied in the Task closeout.
