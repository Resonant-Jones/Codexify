# Imported-history provider-context probe — 2026-09-23

## Result and boundary

**The retained local completion path did not inject imported evidence.** One new General thread submitted one `personal_knowledge` + `normal` completion. Guardian accepted and executed the task, invoked local Whoosh'd, and persisted an assistant reply. Its live retrieval trace reported zero semantic hits and `retrieval_injected=false`. A capture at the worker's actual `requests.post()` boundary showed that neither imported sentinel was present in the provider-ready messages. The persisted reply did not contain the assistant sentinel.

The first observed failure is **semantic retrieval inside `worker-chat`**, before provider-ready context assembly. This does not reverse the preceding proof that the backend's `ContextBroker.assemble()` selected the imported messages from the same user's other Project. The two calls used different vector-store views. It does not prove the cause of the private-preview symptom or qualify a release.

## Evaluated runtime and source

- Source: `/Volumes/Dev_SSD/Codexify-main`, clean `main` at `a68f4a2a09f9248b554fa7d27b505d5da71c4792` before this proof artifact. Database revision `a8d4c2f6b1e9`.
- Retained Compose project: `codexify_account_import_ui_probe_20260923`. Inputs: `docker-compose.yml`, `docker-compose.whooshd-smoke.yml`, `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`, plus a probe-only `/private/tmp/codexify-import-retrieval-probe-provider-20260923/compose.capture.override.yml` that mounted a receipt hook into `worker-chat`. The hook wrapped the local `requests.post()` call, recorded only structural request metadata and sentinel-presence booleans, then delegated the request unchanged. It stored no raw prompt, retrieved text, answer, or credential.
- Local provider route: `http://host.docker.internal:8000/v1/chat/completions`, logical model `local-chat`, streaming; Whoosh'd health and model-list preflight succeeded. Cloud provider routing remained disabled. No private-preview service or data was used.
- Imported source remained thread 1 in Imports Project 2, owner `local`, `origin_system=openai`. Canonical imported messages 1 and 2 remained `ready`, with unchanged source message IDs. The previous [retrieval eligibility proof](2026-09-23-imported-history-retrieval-eligibility-proof.md) had found both in the backend's Chroma search and selected both in an empty General thread via `personal_knowledge` + `normal`; `project` + `normal` excluded both.

## One correlated completion

The normal message API created native General thread 3 (`Axis Imported Completion Probe`, Project 1, owner `local`, `origin_system=codexify`) and user message 3. Its question referred to the imported assistant sentinel but did **not** include either exact sentinel token. The completion API accepted exactly one request with `source_mode=personal_knowledge`, `depth_mode=normal`, and provider `local`:

| Correlation | Value |
| --- | --- |
| Task | `7976ba4e-cd9e-4838-b941-72fceb3f6e51` |
| Request | `req_3e8af9bf0442465e9239205325984d12` |
| Turn | `4ffed0f0-366a-43b0-b35a-126076e07a56` |
| Attempt | `attempt_f74cc8f151fe466dac0d50eac4a6d015` |

Before `worker-chat` started, a non-destructive Redis `LRANGE` showed exactly that `chat_completion` task on `codexify:queue:chat`, tied to thread 3 and latest user message 3, with the requested source/depth and owner. The worker consumed it. Its bounded log reported `semantic=0`, then assistant-message persistence and task completion. PostgreSQL `eval_trace_snapshots` linked the same task/request to thread 3, user message 3, and assistant message 4:

| Trace field | Observed |
| --- | --- |
| Source / depth / Project | `personal_knowledge` / `normal` / General Project 1 |
| Widening | `explicit_personal_knowledge`, `same_user_only` |
| Retrieval | executed; `retrieval_no_candidates` |
| Semantic count / injection | `0` / `false` |
| Provider-ready message count | `2` |
| Completion truth | accepted, attempted, executed, completed |

The hook's pre-dispatch receipt used the exact task, request, and attempt IDs above. It saw one system message and one user message, model `local-chat`, `stream=true`, and **assistant sentinel absent from both**. It also found the imported user sentinel absent. Its response-header receipt recorded HTTP 200 from Whoosh'd with the same request ID. The worker then persisted assistant message 4 in thread 3, owner `local`. Read-only SQL found the assistant sentinel neither as the entire answer nor anywhere within it. Answer quality is secondary here: the outbound payload had already failed the evidence-injection condition.

## Vector-store split at the failing boundary

`docker inspect` of the running containers showed the backend bound `/Volumes/Dev_SSD/Codexify-main/.chroma` to `/app/.chroma`. The resolved `worker-chat` mounts had **no** `/app/.chroma` bind. Both containers resolved the configured Chroma path to `/app/.chroma`, but read-only SQLite counts at that path differed: backend 12 embedding records, worker 1. The worker's path existed inside its container image/writable layer, so a simple path-exists check would have missed the split.

This topology difference is a concrete explanation for why direct broker selection in the backend did not carry into the worker completion. No mount was added or production configuration repaired during this diagnostic, so a corrected-topology completion remains unproven. The precise next task is to align the chat worker's configured vector-store mount with the backend and chat-embedding worker, then run a fresh one-thread completion with the same trace and outbound-payload receipt. Treat that as a configuration correction requiring its own scoped validation; do not infer provider injection from broker selection alone.

## Validation and limits

| Check | Result | Evidence posture |
| --- | --- | --- |
| Read-only SQL for canonical thread/messages, Alembic revision, and trace snapshot | Imported rows still `ready`; thread 3/user message 3 and assistant message 4 persisted; task/request IDs matched | `proven-live-runtime` in retained isolated DB |
| Non-destructive Redis queue read before worker start | One matching completion task, correct source/depth/owner/thread/message | `proven-live-runtime` queue observation |
| Worker log and instrumented local outbound `requests.post()` receipt | Zero semantic hits; sentinel absent from the actual two-message provider request; local HTTP 200 | `proven-live-runtime` for this executed attempt |
| Container mount inspection and read-only Chroma SQLite counts | Backend has shared host mount and 12 records; worker lacks that mount and sees 1 record | Runtime topology observation |

No source, test, retrieval policy, ADR, imported row, import job, vector record, or release-truth file was edited. This is a diagnostic proof artifact only; no automated code test applies. The capture hook was temporary and outside Git. After observation, only the isolated project's worker, backend, Redis, and PostgreSQL services were stopped; its containers and volumes were retained. The observed answer cannot be counted as imported-history recall. The prior cross-Project scope negative control remains valid for the backend path, but was not repeated through this failed worker completion.

**ADR impact:** none. ADR-004, ADR-060, ADR-067, and ADR-081 remain governing boundaries; this probe does not change their contracts. `docs/architecture/00-current-state.md` and release claims remain unchanged. **Documentation follow-through:** this artifact only.
