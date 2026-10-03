# Chat terminal final-model projection proof

Date: 2026-10-03. Evaluated code: active Goal branch at `5c6774213` plus the
uncommitted worker projection repair. Authority: ordinary-chat reliability Goal
and Development Operator Level 0. Classification: architecture-impact,
`AUTHORIZED_IMPLEMENTATION`; no provider-selection or acceptance semantics
changed. The supported-Compose release qualification remains `HOLD`.

## Atomic Task Spec

Ensure the successful worker result carries the already-resolved top-level
`final_provider` and `final_model` values consumed by the `task.completed`
event. Preserve the existing `provider` / `model` aliases and nested
`model_selection`. Do not infer or select a different provider or model. Prove
the failure with a focused regression, then prove the raw terminal event agrees
with durable assistant metadata on the retained supported-Compose stack.

Governing sources: ADR-001 (acceptance remains distinct from completion),
ADR-003 (message and request identities stay distinct), ADR-038 (transport
observation stays distinct from execution), ADR-074 (provider/model authority),
ADR-087 (accepted task deadline), ADR-091 (durable attempt binding), and the
Chat Runtime Contract. The repair adds no state or token and does not alter the
request, task, turn, message, queue, fallback, or retry semantics.

## Causal seam and repair

`_run_chat_completion_task_compat` already resolves `final_provider` and
`final_model`, uses them in durable assistant metadata and nested
`model_selection`, and returns `provider` / `model` aliases. The top-level
`final_provider` / `final_model` keys were omitted from its result dictionary.
The worker's successful terminal-event projection reads those missing keys,
which produced nulls even though the selected model and persisted metadata were
correct.

The result dictionary now includes the two resolved final values. The existing
lifecycle test asserts that each terminal field equals its alias and the exact
test selection. Before the fix, that test failed with `final_provider=None` and
`provider=local`.

## Validation

The focused worker tests passed in the cached dependency image:

```text
docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  -v /Volumes/Dev_SSD/offload/codex/worktrees/7d94/Codexify-main:/app:ro \
  -w /app -e PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint python codexify-chat-proof:f09156952 -m pytest -q -p no:cacheprovider \
  tests/workers/test_chat_worker_lifecycle_events.py \
  tests/workers/test_chat_worker_streaming_chunks.py \
  tests/test_chat_worker_turn_integrity.py
```

Result: 11 passed. The new terminal-field assertion failed before the result
projection change and passed after it.

## Retained-stack ordinary turn

Project: `codexify_chat_proof_f091_20261002`, API `127.0.0.1:18888`. Before
the worker restart, the chat queue was empty, no turn-lock keys existed, the
chat worker heartbeat was fresh, the chat health endpoint was healthy, and the
PostgreSQL active-application query returned zero. The stack uses retained data
and a cached dependency image. Only the private chat-worker source overlay was
updated and only `worker-chat` was restarted. The mounted worker hash matched
the edited worktree file. Afterward, health was healthy, the heartbeat was
fresh, and the queue and lock set were empty. The original source overlay was
restored and the worker restarted back to its original mounted hash after the
probe.

One normal API user turn completed:

| Evidence | Result |
| --- | --- |
| Thread / user / assistant | `28` / `64` / `65` |
| Request / task / turn | `req_e7d8f531a4f24903a593bc9f79606413` / `879ab453-77f3-46ea-a807-0581aa0f4b09` / `89805a77-749a-44b7-9591-5afdfd56120c` |
| Terminal event | `task.completed` |
| Raw event final selection | `final_provider=local`, `final_model=local-chat` |
| Event aliases and nested selection | `provider=local`, `model=local-chat`; nested final selection agrees, source `LOCAL_CHAT_MODEL` |
| Durable assistant metadata | Request ID and both final values match the event; nested model selection agrees |
| Assistant content | Exactly one assistant row contained the unique requested marker |
| Attempt binding | Request, task, thread, and turn IDs matched; `completed_message_id` remained null |
| Post-turn queue / turn locks | Queue depth `0`; no turn-lock keys |

This is a retained-stack source-overlay proof, not a clean-volume or fresh-image
qualification. It does not prove browser UI consumption of the repaired event,
durable attempt completion-message linking, restart recovery, graceful
shutdown, cancellation/retry behavior, or the full supported-Compose gate.
Current-main integration and full requalification remain open.
