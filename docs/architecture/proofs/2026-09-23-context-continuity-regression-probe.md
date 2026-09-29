# Context continuity regression probe — 2026-09-23

## Scope and evidence posture

Architecture-impact investigation only. No runtime, test, migration, ADR, current-state, frontend, or live-data repair was authorized. This report distinguishes a reproduced code-path defect from the three user-observed symptoms, which were not replayed in their originating private-preview account. `proven-code-path`, `proven-test`, `proven-live-runtime`, `documented-contract`, `working-theory`, and `unknown` have the meanings in the Axis Node contract.

## Evaluated identity and authority

- Repository: `/Volumes/Dev_SSD/Codexify-main`; branch `main`; starting HEAD `1206e2be6d17d509df1b5d1e6254a5f840f0cca6` (`2026-09-23 09:24:26 -0400`, `Remove inaccurate 2026-09-23 development log`). `git status --short --branch --untracked-files=all` showed `## main...origin/main` and no dirty paths at capture. No push was performed.
- Read-only local runtime census: running Compose project `codexify` from `docker-compose.yml` plus `docker-compose.whooshd-smoke.yml`, containers created 2026-09-22 about 13:02 Eastern. This is a Whoosh'd smoke stack, **not** the named `v1-local-core-web-mcp` qualification or the private preview where the symptoms were reported. Backend image digest from Docker inspect: `sha256:e66c2726e4b191b2302943ee8aafc9337a47d809a72cca2161111106fb6f868d`; deployed application commit could not be proven. Source directories are bind-mounted, so image identity alone cannot establish source revision. Database Alembic revision `a8d4c2f6b1e9`. Read-only counts: 14 threads, five uploaded documents (all `ready`), two thread-document links, five project-document links, zero account-import jobs, zero threads with more than 50 messages, and zero thread/Project canonical-owner mismatches. No account-import worker was in `docker compose ps`; Compose declares one in `docker-compose.yml`. These counts describe only this local smoke database, not private preview or the user's account.
- `docs/architecture/00-current-state.md` leaves fresh current-tip supported-Compose and browser/import qualification open. `docs/architecture/flows.md` and `docs/architecture/account-export-restore-contract.md` describe assembly and import contracts; they are not live proof. ADR-081 makes `projects.user_id` sole Project ownership authority; `chat_threads.user_id` independently owns a thread. ADR-084 defines UMS, but does not itself prove runtime recall integration. No ADR is changed here.

## Boundary map

The completion service takes `task.max_context or 50`, calls `chatlog_db.list_messages(thread_id, limit=limit, offset=0)`, splits history from the latest turn, then renders those messages into `messages_for_llm` (`guardian/core/chat_completion_service.py:5039-5119, 5559-5560`). Postgres `list_messages` orders ascending by creation time and applies `LIMIT ... OFFSET 0` (`guardian/core/pgdb.py:1572-1606`). Thus the completion loader reads the **oldest** 50 messages, not the newest 50. If the task targets a later message by ID, latest-turn splitting can reject it as missing; without that ID it can select a stale turn. This is a deterministic code-path defect conditional on a thread exceeding the limit, not a live reproduction of the user's symptom. `git blame` ties the bounded completion read to `2f87bf9b26` (2026-02-25) and the current call shape to `6d1b527737` (2026-07-20); the ascending Postgres ordering predates UMS and is present in `6e74d504f`. The defensible introducing seam for the **combination** is `2f87bf9b26`, subject to a future deterministic probe on both sides of that commit. No known-good runtime endpoint was established; no bisect was run.

`ContextBroker.assemble()` also fetches `n_messages=6` through `_fetch_messages`, whose Postgres fallback calls the same ascending `list_messages` (`guardian/context/broker.py:975-1032, 1124-1136, 1951-1988`). The broker stores those in `bundle["messages"]`; the completion service separately builds provider conversation history from its own 50-message read. Broker recent-message presence is therefore not proof that the provider receives the intended latest history. Broker retrieval errors can become empty lists. Semantic and memory retrieval are scope- and depth-dependent; `conversation` source mode suppresses scoped docs and memory, and memory search runs only at `deep`/`diagnostic` (`guardian/context/broker.py:1340-1363, 1471-1537`).

For documents, an uploaded row must match the context user, be undeleted, be `ready`, and be found through an enabled Project link or a thread link before the broker emits a scoped excerpt (`guardian/context/broker.py:2000-2070, 3140-3459`). Selected `bundle.docs` becomes a system context message through `_build_document_context_message` (`guardian/core/chat_completion_service.py:4702-4775, 5338-5340`), then is appended to provider-ready messages. A browser tile is a separate path: `GuardianChat.tsx:3375-3400, 3661-3733` fetches document content by ID and serializes a tile/content block into the user message; `guardian/core/chat_attachments.py:39-160` renders that block for inference. That path does not itself create a `thread_documents` or `project_document_links` row. A visible tile, a durable link, broker selection, and provider input are four distinct facts.

For account import, `frontend/src/lib/api.ts:1037-1049` sends repeated `files`/`relative_paths` multipart parts; `guardian/routes/migration.py:105-171` validates and stages a batch. `guardian/services/openai_account_import.py:368-557` persists staging and enqueues finalization. `guardian/workers/account_import_worker.py:154-272` materializes staged files and calls the OpenAI or Anthropic canonical importer. `backend/rag/openai_export_conversation_import.py:360-550, 740-820` handles source inventory, canonical writes, account-scoped Project selection/creation, and `embedding_mode="defer"`. The worker records source/commit counts; zero committed entities without an explicit duplicate outcome is a terminal failure under the account-import contract. Transport acceptance is not materialization, and canonical rows are not automatically cross-thread retrieval evidence.

## Track 1 — prior conversation/history visibility

| Field | Result |
| --- | --- |
| Symptom | User reports ordinary Guardian chat succeeds while prior interactions are not recalled. Originating thread/account and exact expected earlier fact were not supplied or replayed. |
| Expected behavior | Recent messages from the active owned thread enter the completion input; governed semantic/memory recall may add eligible prior evidence under the selected source/depth policy. |
| Data exists? | `unknown` for the reported account; local smoke stack has 14 threads, with no thread over 50 messages. |
| Ownership valid? | `unknown` for reported thread; local aggregate showed zero thread/Project canonical-owner mismatches. |
| Linkage valid? | `unknown` for reported active thread/Project. |
| Indexed/searchable? | `unknown`; no source-specific index query against the reported data. |
| Selected by retrieval? | `unknown`; no executed trace for the reported turn. |
| Injected into executed context? | `unknown` for reported turn. |
| Present in provider input? | `unknown` for reported turn. Source shows messages returned by the completion loader are appended. |
| Last proven-good boundary | For the conditional >50-message defect, durable messages can exist in Postgres; this was established by code, not a live long-thread readback. For the reported symptom: only ordinary provider execution is user-observed. |
| First failed boundary | Conditional defect: Postgres-to-completion history window (`oldest 50`). Reported symptom: `not localized`; cross-thread recall is a separate policy/retrieval question. |
| Suspect commit/range | `2f87bf9b26` for the conditional window defect; introducing commit for the reported symptom `not established`. |
| Evidence posture | `proven-code-path` for conditional window defect; `unknown` for reported runtime boundary. |
| Root-cause confidence | High for the conditional ordering error; insufficient evidence that it explains the user's observed prior-interaction failure. |

Cross-check still required on the affected account: count messages per chosen thread; compare earliest/latest IDs and event times with completion `max_context`, target-turn ID, active user, `chat_threads.user_id`, `chat_threads.project_id`, canonical `projects.user_id`, source mode/depth, broker retrieval trace, executed bundle, and redacted provider-ready role/count/hash evidence. Do not infer cross-thread memory from same-thread history. No real conversation content is needed.

## Track 2 — explicit document attachment visibility

| Field | Result |
| --- | --- |
| Symptom | User reports a visible Guardian document attachment while the model says no document was provided. No matching request, document ID, or terminal task was available. |
| Expected behavior | A selected document is either serialized with readable content into the authored user message, or enters context through an owned, ready, linked document selected by the broker. |
| Data exists? | `unknown` for reported document; local smoke stack has five uploaded rows. |
| Ownership valid? | `unknown` for reported document; local aggregate owner mismatch check covered threads/Projects only. |
| Linkage valid? | `unknown`; tile state is not a durable link. |
| Indexed/searchable? | `unknown` for reported document; all five local smoke uploaded rows are `ready`, which does not prove searchability or injection. |
| Selected by retrieval? | `unknown` for reported completion. |
| Injected into executed context? | `unknown` for reported completion. |
| Present in provider input? | `unknown` for reported completion. |
| Last proven-good boundary | User-observed UI tile. For the local code path, tile serialization and ready/link gates are identifiable, but no matching runtime request was observed. |
| First failed boundary | `not localized`; could be tile-to-request serialization, missing durable link, owner/scope/ready gate, broker selection, or later injection. |
| Suspect commit/range | `not established`. Tile-to-inline-content path dates to `60bf174a54`; later document artifact repair `f3afc2bf2` is a comparison candidate, not a culprit. |
| Evidence posture | `proven-code-path` for the two distinct paths; `unknown` for the reported failure. |
| Root-cause confidence | Insufficient to classify the screenshot-class failure as presentation, persistence, indexing, retrieval, injection, or provider-envelope failure. |

The next bounded probe must capture tile ID and request envelope, uploaded row `id/user_id/project_id/thread_id/embedding_status`, thread and Project links, active thread/Project and source mode, broker selected document IDs, sanitized executed bundle, and redacted provider message structure. A synthetic sentinel in a disposable supported runtime is appropriate; no real document text belongs in this report. The local smoke row counts cannot identify the user's attachment.

## Track 3 — imported conversation-history availability

| Field | Result |
| --- | --- |
| Symptom | User reports conversation-history import no longer functions as expected. No affected job ID/status or source manifest was available. |
| Expected behavior | Valid multipart acceptance → durable staging → queued worker → canonical owned Project/thread/message writes with provenance → separately governed indexing/retrieval eligibility → selection/injection when policy allows. |
| Data exists? | `unknown` in affected private preview; local smoke stack has zero import jobs. |
| Ownership valid? | `unknown` for affected import; importer code scopes Project selection to `user_id`, but durable affected rows were not inspected. |
| Linkage valid? | `unknown` for affected canonical Project/thread/message rows. |
| Indexed/searchable? | `unknown`; worker calls importer with `embedding_mode="defer"`, so completion of canonical import does not itself prove semantic searchability. |
| Selected by retrieval? | `unknown`. |
| Injected into executed context? | `unknown`. |
| Present in provider input? | `unknown`. |
| Last proven-good boundary | Historical 2026-09-02 private-preview proof recorded valid direct multipart replay durably staging 25/25 files, while the failing Safari request arrived without parseable required fields. It did not prove current staging/materialization/retrieval. Current local smoke stack has no import job. |
| First failed boundary | Historical Safari instance: browser/request multipart envelope before route validation. Current reported import symptom: `not localized`; no affected job readback. |
| Suspect commit/range | Safari browser seam includes `e0ef786651` (FormData client/route introduction); exact introducing commit `not established`. Downstream current failure commit `not established`. |
| Evidence posture | `proven-live-runtime` for the dated historical transport proof only; `proven-code-path` for current lifecycle; `unknown` for the current reported job. |
| Root-cause confidence | Safari transport failure was previously localized. Whether the current complaint is that failure, an absent worker, staging/materialization issue, ownership/provenance issue, or retrieval failure remains unproven. |

The prior Safari `422` proof is `docs/architecture/proofs/2026-09-02-account-import-422-reproduction-proof.md` at HEAD `1a15805b5873305a4d179cdd5add4cb314ce1669`, in private preview. Its valid-body replay proves FastAPI can accept a proper envelope on that deployment, while the Safari failure occurred before valid route fields. Do not merge this historical transport classification with downstream import symptoms. The currently running smoke Compose stack lacks a running `worker-account-import`, but is not the affected private-preview profile; this is a profile observation, not a cause assigned to private preview.

## Ownership, UMS, and regression relationship

The relevant account boundary is browser/authenticated request → Guardian route → Postgres owner/scope, then worker → derived vector store/provider. `projects.user_id` is canonical; the importer proxy explicitly passes `user_id` on Project creation, and linked-document retrieval compares document `user_id` with the context user. The smoke census found no thread/Project owner mismatch but does not audit private preview or document ownership. Imported source IDs are preserved in thread/message metadata by the canonical importer; the current task did not inspect affected provenance rows. Vector visibility is derived state, never ownership authority.

UMS classification: **undetermined**. The inspected completion and broker modules still call legacy `MemoryOSRetriever`, memory store, and verified Personal Facts; the inspected import worker calls the canonical conversation importer. No direct `memory_records`/UMS read or write edge was found in those paths. Recent UMS commits (`4d2de549e`, `4c3d6c57e`, `a67b28def`, `e21887fb4`, `adc98bd6c`, `852320869`) do not, by proximity alone, establish causation. The conditional oldest-window defect predates UMS. A deployed UMS-side effect or scope migration affecting the reported private-preview data is not ruled out by this code read.

Overall classification: **insufficient evidence to unify them**. One older conditional history-window defect is proven in code; a separate historical Safari transport failure was proven in private preview; the visible-document symptom is not localized. They are different seams, and there is no matching executed trace or durable affected-account readback proving a shared cause.

## Validation and limits

Commands were run from repository root. `pytest -v tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py` was attempted as part of the exact combined command below; bare `pytest` failed at collection because the shell Python lacked `fastapi`, so `.venv/bin/python -m pytest` was used.

- `pytest -v tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py tests/core/test_chat_completion_service_attachments.py tests/routes/test_thread_documents.py tests/workers/test_account_import_worker.py` — **not collected** (`ModuleNotFoundError: fastapi` in bare environment).
- `.venv/bin/python -m pytest -v tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py tests/core/test_chat_completion_service_attachments.py tests/routes/test_thread_documents.py tests/workers/test_account_import_worker.py` — **failed: 11 failed, 66 passed**. Ten `test_chat_source_mode.py` cases expected HTTP 200 and received 503; one `test_thread_documents.py` assertion expected four fields but the returned uploaded-document projection also carried `embedding_status` and `embedding_error`. `test_chat_profile_trace.py` (34 tests), attachment tests (2), and account-import-worker tests (9) passed within that run. The route failures were not repaired or conflated with the user's symptoms.
- `.venv/bin/python -m pytest -q tests/core/test_context_broker_depth.py tests/core/test_context_broker_source_mode.py tests/migration/test_openai_export_conversation_import.py` — **passed: 67 tests**. This proves only the exercised static/test paths.
- `rg -n "account.?import|multipart|uploaded_documents|thread_documents|project_document_links|ContextBroker|attachment" tests guardian frontend/src` — discovery completed; focused modules above were selected from its results.
- Read-only Docker `compose ps`, `inspect`, `config --services`, and `psql` transaction (`BEGIN READ ONLY`) provided the local smoke identity and aggregate counts above. No synthetic upload/completion was run, no provider-ready payload was captured, and no private-preview account was accessed. Thus no current symptom is `proven-live-runtime` here.

## Deferred follow-up candidates

1. Reproduce the >50-message completion window with a synthetic owned thread in a disposable supported runtime; capture durable IDs, target-turn ID, provider-ready role/count/sentinel evidence, and compare a defensible pre/post `2f87bf9b26` state before a repair task.
2. Reproduce a synthetic document tile through request, durable row/link/readiness, broker selection, executed bundle, and provider-ready messages on the affected profile. Classify any first failed seam before changing UI or retrieval code.
3. Read one affected private-preview import job by ID using bounded metadata only: request status, staged count/bytes, worker presence, source summary, committed canonical counts, owner/Project/thread/provenance, derived index state, and completion trace. Separate Safari transport from downstream failures. Any repair of live data requires a separate authorized preservation task.

Documentation follow-through: `00-current-state.md` already labels browser/import and current-tip qualification as open; no release claim update was justified. No accepted ADR change was demonstrated; **No ADR impact**. Canonical ownership was preserved, no data was repaired, no scope was changed, and no release claim was widened. Recommended Axis KB addition after future proof: document the difference between browser document tiles, durable document links, ready-only broker excerpts, and provider input.
