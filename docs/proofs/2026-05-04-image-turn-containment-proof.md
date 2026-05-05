# 2026-05-04 Image Turn Containment Proof

## Scope
Live supported-path proof attempt for image-turn containment on the local Docker Compose stack. This run checked whether an image turn in one thread would avoid contamination from:
- a prior assistant vision refusal in another thread
- a prior assistant vision refusal in the same thread
- ordinary retrieval widening beyond the active thread
- the operator-visible RAG trace/debug payload

This document records the live evidence exactly as observed. It does not claim release readiness.

## Environment
- Branch: `codex/add-vision-capability-validation`
- HEAD: `65385db781f6f7f523661df09dafe19406dcdf0b`
- Runtime path: local Docker Compose (`docker-compose.runtime.yml`)
- Services started: `backend`, `db`, `frontend`, `neo4j`, `redis`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, `worker-warmup`
- Supported profile posture: healthy local runtime on the live stack
- Provider selected in health: `local`
- Runtime model selected in health: `library2/ministral-3:8b`
- Requested completion model: `medgemma:4b-it-q8_0`
- Model actually resolved in the completion payload: `library2/ministral-3:8b`

## Commits Under Proof
- `d4510c6f providers: validate image turns against vision capability`
- `a0a2925a providers: preserve local caption fallback for image turns`
- `2df245ec context: enforce thread-first retrieval boundaries`
- `65385db diagnostics: expose retrieval provenance and suppression reasons`

## Exact Commands
```bash
docker compose -f docker-compose.runtime.yml ps
docker compose -f docker-compose.runtime.yml exec backend python - <<'PY'
# GET /health
# GET /health/chat
# GET /api/health/llm
# GET /api/llm/catalog
PY
docker compose -f docker-compose.runtime.yml exec backend python - <<'PY'
# Create Thread A and Thread B
# Seed Thread A refusal
# Seed Thread B refusal
# Upload image to Thread B
# Post image turn to Thread B
# POST /api/chat/5/complete
PY
docker compose -f docker-compose.runtime.yml exec backend python - <<'PY'
# GET /api/chat/5/messages
# GET /api/chat/debug/rag-trace/5/latest
# GET /api/chat/debug/evals/5/latest
PY
docker compose -f docker-compose.runtime.yml exec db psql -U codexify -d Codexify -c "SELECT ... FROM events_outbox ..."
git diff --check
```

## Health And Supported-Profile Evidence
- `GET /health` returned:
  - `status: ok`
  - `service: core`
- `GET /health/chat` returned a healthy chat runtime:
  - `ok: true`
  - `status: healthy`
  - `redis: ok`
  - `worker.status: fresh`
  - `queue.depth: 0`
  - `completion_service.ok: true`
  - `provider: local`
  - `model: library2/ministral-3:8b`
  - `provider_runtime.models[0].supports_vision: false`
- `GET /api/health/llm` returned `status: ok` / `status: online` with the same local provider/model posture.
- The supported runtime was healthy, but the active local model on this run was the non-vision `library2/ministral-3:8b`.

## Fixture Setup
### Thread A refusal source
- Thread A id: `4`
- User seed message id: `17`
  - content: `Thread A setup: please inspect the image.`
- Assistant refusal message id: `18`
  - content: `I can't view the image.`

### Thread B image turn
- Thread B id: `5`
- Same-thread refusal seed message id: `20`
  - content: `I can't view the image.`
- Image-turn user message id: `21`
  - content included the supported attachment markers:
    - `<!-- cfy-media:image:ec94fdd9-f767-4e7e-aa8e-ff768289e376 -->`
    - `<!-- cfy-media-src:/media/images/20260504-c3aa7880--image-turn-proof-b5b6adddd47b45ad875147378836322c.png?sig=... -->`
    - `<!-- cfy-media-name:image-turn-proof-b5b6adddd47b45ad875147378836322c.png -->`
  - file upload was performed through `POST /api/media/upload/image`

## Completion Execution Evidence
- Request endpoint: `POST /api/chat/5/complete`
- Request body included:
  - `provider: local`
  - `model: medgemma:4b-it-q8_0`
  - `depth_mode: normal`
  - `source_mode: project`
  - `turn_id: 00b1722b-d912-45cf-88b2-b17a1b5d8a88`
- Completion task id: `06e82d16-02f8-4695-8f07-a775b348956e`
- Completion-persisted assistant message id: `22`
- Final model actually resolved in the live payload:
  - `library2/ministral-3:8b`
- Final provider actually resolved in the live payload:
  - `local`
- Provider capability lane observed in the live payload:
  - no `image_routing_path` was surfaced in the durable completion event row for this thread
- Assistant response:
  - did not repeat `I can't view the image.`
  - instead described a portrait-like scene that does not match the uploaded 1x1 PNG

## Retrieval/RAG Trace Evidence
- `GET /api/chat/debug/rag-trace/5/latest` returned an empty public trace shell:
  - `documents: []`
  - `graph: []`
  - no surfaced `retrieval_policy`
  - no surfaced `retrieval_provenance`
  - no surfaced `retrieval_suppression`
- `GET /api/chat/debug/evals/5/latest` returned a trace snapshot with:
  - `trace_snapshot.task_id: 06e82d16-02f8-4695-8f07-a775b348956e`
  - `trace_snapshot.trace.documents`: four semantically retrieved snippets
  - `trace_snapshot.trace.retrieval_plan.retrieval_needed: true`
  - `trace_snapshot.trace.retrieval_plan.allow_global_fallback: false`
  - `trace_snapshot.trace.widen_reason: insufficient_thread_hits`
  - `trace_snapshot.trace.effective_policy.source_mode: project`
  - `trace_snapshot.trace.retrieval_target: latest_turn`
  - no surfaced `retrieval_policy`
  - no surfaced `retrieval_suppression`
  - no surfaced `retrieval_provenance`
- The durable `events_outbox` row for this task also showed:
  - `payload_summary.final_model: library2/ministral-3:8b`
  - `payload_summary.image_routing_path: null`
  - `payload_summary.retrieval_policy: null`
  - `payload_summary.retrieval_provenance: null`
  - `payload_summary.retrieval_suppression: null`
- Thread A refusal text did not appear in the assistant output or in the trace snippets I captured.
- However, because the live trace payload did not surface the provenance/suppression fields required by the proof contract, I cannot claim machine-readable proof that Thread A was excluded from Thread B context.

## Result
FAIL

## Limitations
- The live runtime was healthy, but the completion payload on this run resolved to `library2/ministral-3:8b`, not the requested `medgemma:4b-it-q8_0`.
- The public rag-trace endpoint was empty for the completed proof thread.
- The durable trace snapshot existed in `events_outbox`, but it did not expose the required `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, or `image_routing_path` fields for this run.
- The assistant response did not echo the seeded refusal, but the trace payload did not provide enough provenance to prove containment conclusively.
- `pnpm test` was not rerun in this proof attempt; prior validation in this checkout has already been blocked by unresolved Vitest resolution in the frontend workspace.
- This document is not a durable forensic record. It is a live proof attempt on the current runtime only.

## Follow-Up Recommendations
1. Rebuild and rerun the local runtime from the current checkout so the live services reflect the current trace/provenance contract.
2. Re-run the same two-thread image proof and verify that the completion payload now includes `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, and `image_routing_path`.
3. Confirm why the completion request resolved to `library2/ministral-3:8b` instead of the requested local vision-capable model override.
4. Once the runtime is refreshed, repeat the proof and only then claim containment on the live path.
5. The current branch now promotes completion and eval snapshot metadata into the live trace route; rerun the proof against refreshed services to confirm the operator-visible payload now includes `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, `image_routing_path`, and model-selection fields on the supported path.

## Rerun — 2026-05-04 after live trace promotion

### Result
FAIL

### Environment
- branch: `codex/add-vision-capability-validation`
- HEAD: `6b95af99b35bc5761a6f7569b32ea555848ffc3c`
- runtime path: `/Volumes/Dev_SSD/Codexify-main`
- services refreshed: `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, `worker-warmup`
- requested provider/model: `local` / `medgemma:4b-it-q8_0`
- resolved provider/model: `local` / `library2/ministral-3:8b`

### Exact Commands
```sh
docker compose up -d --build backend worker-chat worker-chat-embed worker-document-embed worker-voice worker-warmup
docker compose up -d --no-deps backend worker-chat worker-chat-embed worker-document-embed worker-voice worker-warmup
docker compose exec -T backend python - <<'PY'
# health checks, thread A/B setup, image upload, completion, trace fetch
PY
docker compose exec -T backend python - <<'PY'
# task-events inspection
PY
```

### Health And Supported-Profile Evidence
- `GET /health` returned `200` with `status: ok`.
- `GET /health/chat` returned `200` with:
  - `status: healthy`
  - `provider: local`
  - `model: library2/ministral-3:8b`
  - `provider_runtime.models[0].supports_vision: false`
- `GET /api/health/llm` returned `200` with `status: ok` / `status: online`.
- `GET /api/llm/catalog` returned a live catalog that included the local nonvision model plus vision-capable local models such as `medgemma:4b-it-q8_0`.

### Fixture Setup
- Thread A refusal source:
  - Thread A id: `6`
  - user message id: `23`
  - assistant refusal message id: `24`
  - assistant content: `I can't view the image.`
- Thread B image turn:
  - Thread B id: `7`
  - image upload id: `c6a89d26-8854-4117-a580-8bf6eafc6af9`
  - image upload result: `POST /api/media/upload/image` returned a signed `src_url`
  - user message id: `25`
  - user content included the supported `cfy-media` attachment markers

### Completion Execution Evidence
- Request endpoint: `POST /api/chat/7/complete`
- Request body included:
  - `provider: local`
  - `model: medgemma:4b-it-q8_0`
  - `depth_mode: normal`
  - `source_mode: project`
  - `turn_id: 4f7aa578-3eda-4ca6-92f5-cedb45cf482b`
- Task id: `dd96dc0e-269c-4e6c-9533-61cd115343d8`
- Assistant message id: `26`
- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `library2/ministral-3:8b`
- Image-routing path: not surfaced in the live task/event/debug payloads for this run

### Live RAG Trace Evidence
- `GET /api/chat/debug/rag-trace/7/latest` returned an empty public shell:
  - `documents: []`
  - `graph: []`
  - `model_mode: cloud`
  - `widen_reason: none`
  - no surfaced `retrieval_policy`
  - no surfaced `retrieval_provenance`
  - no surfaced `retrieval_suppression`
  - no surfaced `image_routing_path`
- `GET /api/chat/debug/evals/7/latest` returned a trace snapshot whose `payload_summary` and `metadata` exposed:
  - `requested_model: medgemma:4b-it-q8_0`
  - `final_model: library2/ministral-3:8b`
  - `selection_source: LOCAL_CHAT_MODEL`
  - `policy_reason: LOCAL_CHAT_MODEL`
  - `retrieval_summary.retrieval_query: Attached image: image-containment-proof.png ...`
  - `retrieval_provenance: null`
- The `task.completed` event stream exposed the same model-selection truth:
  - `attempted_model: medgemma:4b-it-q8_0`
  - `final_model: library2/ministral-3:8b`
  - `selection_source: LOCAL_CHAT_MODEL`
  - `retrieval_provenance: null`
- Thread A refusal text did not appear in Thread B messages.
- The assistant response on Thread B was a refusal-like answer, but the live trace still did not provide machine-readable evidence that this came from supported image routing rather than model behavior.

### Result Interpretation
- Containment is still not machine-readably proven on the live supported path.
- The proof did not establish image interpretation fidelity.
- The live path now exposes requested/final model-selection truth in eval/task metadata, but the public rag-trace endpoint still did not surface the promoted retrieval policy, provenance, suppression, or image-routing fields.

### Limitations
- RAG trace remains transient and not a durable forensic store.
- The live debug trace route still returned an empty shell for this thread.
- The completion path still resolved the requested vision-capable override to `library2/ministral-3:8b`.
- The task-event and eval surfaces showed model-selection truth, but not the retrieval provenance/suppression fields required for a containment PASS.
- The backend refresh required `docker compose up -d --no-deps ...` after the migrator failed, so the refresh step itself is an environmental blocker worth tracking separately.

### Follow-Up Recommendations
1. Fix the remaining live trace promotion gap so `GET /api/chat/debug/rag-trace/{thread_id}/latest` surfaces the same completion and retrieval truth already visible in eval/task metadata.
2. Confirm whether the image turn is still being routed through the nonvision local model because of policy selection or an unresolved adapter path.
3. Rerun the same proof only after the live trace route exposes `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, and `image_routing_path` for the supported path.

### Remediation Note
- Live follow-up verification showed the worker did persist an `eval_trace_snapshots` row for thread `21`, and `GET /api/chat/debug/evals/21/latest` plus `GET /api/chat/debug/rag-trace/21/latest` both returned the snapshot once the completion had settled.
- That means the remaining failure mode was proof timing, not a missing persistence path.
- The proof is ready to rerun against a fresh completion thread if the goal is to re-capture the containment evidence with the now-visible snapshot lane.

## Rerun — after 65a2e12e model substitution truth fix

### Result
FAIL

### Environment
- branch: `codex/add-vision-capability-validation`
- HEAD: `65a2e12e9689dff0695931309038a06e80f83b50`
- runtime path: `/Volumes/Dev_SSD/Codexify-main`
- services refreshed: `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, `worker-warmup`

### Health Evidence Summary
- `GET /health` returned `200` with `status: ok`.
- `GET /health/chat` returned `200` with:
  - `status: healthy`
  - `provider: local`
  - `model: library2/ministral-3:8b`
  - `provider_runtime.models[0].supports_vision: false`
- `GET /api/health/llm` returned `200` with `status: ok` / `status: online`.
- `GET /api/llm/catalog` returned the live local catalog, including `medgemma:4b-it-q8_0` as a vision-capable model.

### Thread Setup
- Thread A id: `20`
- Thread A user message id: `47`
- Thread A assistant refusal message id: `48`
- Thread A assistant content: `I can't view the image.`
- Thread B id: `21`
- Thread B user image message id: `49`
- Thread B assistant message id: `50`

### Model-Selection Evidence
- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `library2/ministral-3:8b`
- Selection source: `LOCAL_CHAT_MODEL`
- Fallback reason: `null` in the assistant message metadata
- Model resolution message: `requested model 'medgemma:4b-it-q8_0' was overridden by configured local chat model 'library2/ministral-3:8b' from LOCAL_CHAT_MODEL`
- The task-event / assistant metadata path does explain the substitution machine-readably, but the live response still routed to the configured local default model.

### Image-Routing Evidence
- Image payload evidence:
  - reused uploaded image id `fdea58f2-5ea9-43fc-8fe7-1f3ed0f3542e`
  - `src_url`: `/media/images/20260505-64abf93f--image-containment-proof.png?sig=SSoRblzU5_l32SImrU6HvSSAFcrXGNhgYj3kNYuFhZc`
  - message content included the supported attachment markers:
    - `<!-- cfy-media:image:fdea58f2-5ea9-43fc-8fe7-1f3ed0f3542e -->`
    - `<!-- cfy-media-src:/media/images/20260505-64abf93f--image-containment-proof.png?sig=SSoRblzU5_l32SImrU6HvSSAFcrXGNhgYj3kNYuFhZc -->`
    - `<!-- cfy-media-name:image-containment-proof.png -->`
- Image routing path: not surfaced in the live task/event/debug payloads for this run
- Capability lane: the live health/catalog posture still showed the active resolved model as non-vision local, even though the requested model was vision-capable

### RAG/Debug Trace Evidence
- `GET /api/chat/debug/rag-trace/21/latest` returned an empty public shell:
  - `documents: []`
  - `graph: []`
  - `trace_unavailable_reason: trace_source_unavailable`
  - no surfaced `retrieval_policy`
  - no surfaced `retrieval_provenance`
  - no surfaced `retrieval_suppression`
  - no surfaced `image_routing_path`
- `GET /api/chat/debug/evals/21/latest` returned no `trace_snapshot`.
- The completed message metadata and payload_summary did expose:
  - `requested_model: medgemma:4b-it-q8_0`
  - `final_model: library2/ministral-3:8b`
  - `selection_source: LOCAL_CHAT_MODEL`
  - `model_resolution.message` with the substitution reason above
- `assistant_vision_refusal_on_image_turn` did not appear in the live debug trace payload for this run.
- Thread A refusal text did not appear in Thread B messages.
- Thread A refusal text was therefore not visibly leaked into Thread B output, but the live debug trace still did not expose enough provenance/suppression data to prove containment machine-readably.

### Result Interpretation
- Containment is not machine-readably proven on the live supported path.
- The model substitution is explained through `selection_source`, `policy_reason`, and `model_resolution.message`, but `fallback_reason` remained null in the assistant message metadata.
- Image interpretation fidelity was not established because the assistant response remained refusal-like while the public trace surface stayed empty.

### Limitations
- RAG trace remains transient and is not a durable forensic store.
- The live debug trace route still returned an empty shell for this thread, so the required containment fields were still missing.
- The live runtime still resolved the requested vision-capable override to `library2/ministral-3:8b`.
- The task-event and assistant metadata surfaces now explain the substitution, but the public rag-trace route still did not surface `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, or `image_routing_path`.
- `pnpm test` was not rerun; the known Vitest resolution issue remains a separate blocker.
- The Compose migrator blocker remains a separate environmental issue and was not addressed here.

### Follow-Up Recommendations
1. Fix the live debug trace promotion path so the supported rag-trace endpoint returns the same completion and retrieval truth already visible in task-event and assistant metadata.
2. Decide whether the live image-turn path should honor the requested vision-capable local override or continue to substitute `LOCAL_CHAT_MODEL`, and keep that choice machine-readable in the public trace.
3. Rerun the proof only after the public trace exposes `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, and `image_routing_path` for the supported path.

### Remediation Note
- The live runtime blocker that produced the previous failed rerun was a context-assembly `NameError` at `_normalize_source_mode`; the completion service now calls the imported `normalize_source_mode` helper directly.
- The local model-selection path now emits a machine-readable substitution reason when strict local-only policy overrides an explicit requested model in favor of `LOCAL_CHAT_MODEL`.
- The trace/debug route and the promoted eval snapshot shape remain unchanged by this task; the proof should be rerun against a refreshed runtime so the updated completion path can repopulate the live trace lanes.
- This task makes the live image-turn containment proof ready to rerun, but it does not convert the earlier FAIL sections into PASS.

### Remediation Note
- The live trace blocker was the route reading the wrong eval snapshot shape; the backend now promotes `trace`, `payload_summary`, `retrieval_summary`, and `metadata` from the latest persisted eval snapshot into the public debug RAG trace surface.
- The model-selection truth is already machine-readable in the live task/eval lanes as requested versus final model plus `selection_source` and `policy_reason`; the route now mirrors that truth when the snapshot exists.
- This task makes the containment proof ready to rerun on the live supported path, but it does not rewrite the earlier FAIL result and it does not resolve the separate Compose migrator issue.

## Rerun — after eab3c69b live trace row-shape fix

### Result
FAIL

### Health Evidence Summary
- `GET /health` returned `200` with `status: ok`.
- `GET /health/chat` returned `200` with `status: healthy`.
- `GET /api/health/llm` returned `200` with `status: ok` / `status: online`.
- `GET /api/llm/catalog` returned the live supported catalog, including the local nonvision model and vision-capable local models such as `medgemma:4b-it-q8_0`.

### Environment
- branch: `codex/add-vision-capability-validation`
- HEAD: `eab3c69b35885320f4746d937753f55218e759eb`
- runtime path: `/Volumes/Dev_SSD/Codexify-main`
- services refreshed: `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`, `worker-voice`, `worker-warmup`
- requested provider/model: `local` / `medgemma:4b-it-q8_0`
- resolved provider/model: `local` / `library2/ministral-3:8b`

### Exact Commands
```sh
docker compose up -d --no-deps --force-recreate backend worker-chat worker-chat-embed worker-document-embed worker-voice worker-warmup
docker compose exec -T backend python - <<'PY'
# health checks, Thread A refusal seed, Thread B image upload, completion, trace fetch
PY
docker compose exec -T backend python - <<'PY'
# task-event and eval snapshot inspection
PY
```

### Fixture Setup
- Thread A refusal source:
  - Thread A id: `16`
  - user message id: `39`
  - assistant refusal message id: `40`
  - assistant content: `I can't view the image.`
- Thread B image turn:
  - Thread B id: `17`
  - user message id: `41`
  - image upload id: `fdea58f2-5ea9-43fc-8fe7-1f3ed0f3542e`
  - image upload result: `POST /api/media/upload/image` returned a signed `src_url`
  - user message id: `42`
  - user content included the supported `cfy-media` attachment markers

### Completion Execution Evidence
- Request endpoint: `POST /api/chat/17/complete`
- Request body included:
  - `provider: local`
  - `model: medgemma:4b-it-q8_0`
  - `depth_mode: normal`
  - `source_mode: project`
  - `turn_id: 00472bf4-699c-4965-b1c9-c7005a38690b`
- Task id: `7d8bd5b5-130e-4997-af91-e72611cf82d6`
- Assistant message id: `43`
- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `library2/ministral-3:8b`
- Image-routing path: `null` in the live task/event and debug payloads for this run

### Live RAG Trace Evidence
- `GET /api/chat/debug/rag-trace/17/latest` returned `200` and now promoted the real eval snapshot row shape, but it still did not surface the containment fields required for a PASS:
  - no surfaced `retrieval_policy`
  - no surfaced `retrieval_provenance`
  - no surfaced `retrieval_suppression`
  - no surfaced `image_routing_path`
- The route did expose model-selection truth in the promoted payload:
  - `requested_model: medgemma:4b-it-q8_0`
  - `final_model: library2/ministral-3:8b`
  - `selection_source: LOCAL_CHAT_MODEL`
  - `policy_reason: LOCAL_CHAT_MODEL`
- `GET /api/chat/debug/evals/17/latest` returned the same requested/final model-selection truth and showed:
  - `retrieval_summary.retrieval_query: Attached image: image-containment-proof.png ...`
  - `retrieval_provenance: null`
- The `task.completed` event lane for the same task also carried model-selection truth:
  - `attempted_model: medgemma:4b-it-q8_0`
  - `final_model: library2/ministral-3:8b`
  - `selection_source: LOCAL_CHAT_MODEL`
- Thread A refusal text did not appear in Thread B messages.
- The assistant response on Thread B was refusal-like, but the live trace still did not provide machine-readable evidence that this came from supported image routing rather than model behavior.

### Result Interpretation
- Containment is still not machine-readably proven on the live supported path.
- The proof did not establish image interpretation fidelity.
- The live path now exposes requested/final model-selection truth in eval/task metadata, but the public rag-trace endpoint still did not surface the promoted retrieval policy, provenance, suppression, or image-routing fields.

### Limitations
- RAG trace remains transient and is not a durable forensic store.
- The live debug trace route still lacked the required containment fields for this thread.
- The completion path still resolved the requested vision-capable override to `library2/ministral-3:8b`.
- The task-event and eval surfaces showed model-selection truth, but not the retrieval provenance/suppression fields required for a containment PASS.
- The backend refresh required `docker compose up -d --no-deps ...` after the migrator failure, so the refresh step itself remains an environmental blocker worth tracking separately.

### Follow-Up Recommendations
1. Fix the remaining live trace promotion gap so `GET /api/chat/debug/rag-trace/{thread_id}/latest` surfaces the same completion and retrieval truth already visible in eval/task metadata.
2. Confirm whether the image turn is still being routed through the nonvision local model because of policy selection or an unresolved adapter path.
3. Rerun the same proof only after the live trace route exposes `retrieval_policy`, `retrieval_provenance`, `retrieval_suppression`, and `image_routing_path` for the supported path.
