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
