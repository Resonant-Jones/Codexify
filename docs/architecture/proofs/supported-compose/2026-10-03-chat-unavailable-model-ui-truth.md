# Unavailable explicit model failure and UI truth proof

Date: 2026-10-03. Evaluated code: active Goal branch commit
`de14be8199b4feb919f09aa7071b75c284139a80`. Classification:
`PROOF_REQUIRED`; no source behavior changed. Current-main integration and
complete supported-Compose qualification remain open.

## Atomic Task Spec

On the retained supported Compose profile, accept an ordinary user turn that
explicitly requests a model absent from the local runtime inventory. Require
the accepted attempt to fail without model execution, fallback, or assistant
message persistence. Verify its event and durable receipt identities, then
reload the chat UI and confirm the transcript and operator-visible terminal
state agree with the durable outcome.

## Preconditions and isolation

Project: `codexify_chat_branch_proof_896387ad2`; API `127.0.0.1:18889`; Vite
served the active checkout at `http://localhost:5181`. `/health` returned
HTTP 200 with the `v1-local-core-web-mcp` profile valid, local provider
selected, and no cloud-capable configuration. The local runtime health
reported `local` / `local-chat` online.

Before the test, the chat queue was empty and no canonical `turn_lock:*` keys
existed. The unrelated eval and system queues contained 19 and 1 entries. No
services were stopped or restarted. After the test, the chat queue remained
empty, no turn lock existed, the eval/system queue lengths remained 19/1, and
the backend/worker containers remained running (backend healthy).

## Accepted attempt and terminal evidence

The test created a disposable thread and authored prompt requesting the exact
marker `UNAVAILABLE_MODEL_TRUTH_20261003`. It submitted explicit provider
`local` and model `codexify_goal_unavailable_20261003`.

| Evidence | Result |
| --- | --- |
| Thread / authored message | `22` / `41` |
| Request / task / turn | `req_7be0ec2bbf7e46b4987256e71660db6c` / `d6a6e940-988d-4f66-9a3c-3c106c9889e3` / `1a0c14e2-fae2-4e69-aace-46c145540680` |
| Acceptance | `accepted` |
| Durable receipt | `task.failed`, `completed_message_id=null`, reason `durable_terminal_outcome_recorded`; all four identities matched |
| Raw task event | `task.failed` identified the requested model as unavailable; the runtime advertised only `local-chat` |
| Execution truth | `accepted=true`, `attempted=false`, `fallback_attempted=false`, `executed=false`, `completed=false`; no visible output |
| Durable transcript | One authored user message, zero assistant messages |

The task's terminal error payload was a JSON-encoded string nested in the event
`error` field. It contained the explicit requested model, configured source
`requested_model`, inventory source `whooshd:/v1/models`, advertised model
`local-chat`, and the false execution/fallback fields above.

## Browser reload projection

After the failed attempt terminalized, the browser opened `/chat/22`. It first
showed the route's history-loading state, then the authored prompt and the
status “1 earlier response task failed.” Reloading the same route reproduced
that prompt and failed-attempt status without creating another user message or
completion attempt. No assistant reply or false success appeared.

This confirms the durable receipt's coarse terminal kind is enough for the
current UI to show a truthful failure after reload. The detailed rejection
diagnostic was present in the Redis terminal event, while the durable receipt
retains only terminal kind and identity. If Redis event evidence expires, the
specific rejection reason is not recoverable from that receipt; retaining
diagnostic detail would require a separately authorized durable-lifecycle
change.

## Limits

This is branch-local proof of explicit-model rejection, no fallback, durable
failure identity, and browser reload projection. The test did not stop or
restart services and does not establish graceful shutdown, active-worker-loss
recovery, cancellation/retry, a full supported-Compose qualification, or
current-main behavior. Release readiness remains `HOLD`.
