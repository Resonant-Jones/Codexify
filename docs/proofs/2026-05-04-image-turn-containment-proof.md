# 2026-05-04 Image Turn Containment Proof

## Rerun — after eab3c69b live trace row-shape fix

PASS

### Health evidence

- `GET /health` returned `status: ok` for the core service.
- `GET /health/chat` returned `ok: true`, `provider: local`, `model: gemma4-e4b-hauhau:latest`, and a fresh chat worker heartbeat.
- `GET /api/health/llm` returned `ok: true`.
- `GET /api/llm/catalog` returned 52 cataloged models on the local provider.
- The local catalog includes `gemma4-e4b-hauhau:latest` with `model_kind: vision_chat` and `supports_vision: true`.

### Thread Proof

- Thread A was created and contains the refusal text exactly: `I can't view the image.`
- Thread B was created separately and received an image turn using the canonical attachment markers.
- Thread B completed successfully with assistant output: `An object is secured within a bright, luminous containment field.`
- Requested and final provider/model on Thread B were both `local` / `library2/ministral-3:8b`.

### Trace Evidence

- Thread B emitted `task.completed` and the task event stream was readable.
- The completed payload included a trace with:
  - `documents` populated
  - `graph` empty
  - `retrieval_query_matches_latest_turn: true`
  - `effective_policy` set to the project/local posture
- The latest eval snapshot was available at `GET /api/chat/debug/evals/{thread_b_id}/latest`.
- The eval snapshot included:
  - `trace_snapshot`
  - `retrieval_summary`
  - `assistant_output_text`
  - `payload_summary`
  - `trace`
- The live `GET /api/chat/debug/rag-trace/{thread_b_id}/latest` response remained minimal on this run and exposed:
  - `active_profile_id`
  - `provider_override`
  - `model_override`
  - `model_mode`
  - `source_mode`
  - `widen_reason`
  - `thread_id`
  - `project_id`
- That route did not expose `retrieval_policy`, `retrieval_provenance`, image-routing metadata, or `trace_unavailable_reason` on this run.

### Containment Check

- Thread A refusal text did not appear in Thread B messages, task events, trace, or eval snapshot.
- The live proof therefore machine-readably proves containment across the two threads.

### Result Notes

- This rerun passes on containment evidence.
- The trace fix exposed a live eval snapshot and valid task-event-backed trace row shape.
- The minimal rag-trace route still does not surface retrieval provenance or image-routing metadata on this run; the richer evidence lived in the task payload and eval snapshot instead.

## Remediation note — trace content completeness fix

- The completion and worker paths now populate containment-grade trace fields directly into the completed snapshot, including:
  - `retrieval_policy`
  - `retrieval_provenance`
  - `retrieval_suppression`
  - `retrieval_executed`
  - `retrieval_absence_reason`
  - `image_routing_path`
  - `image_routing_absence_reason`
  - `model_selection`
- The debug rag-trace route can now promote those fields from the persisted snapshot instead of depending on an empty shell.
- The image-turn containment proof is ready to rerun against the refreshed live path.
- This note does not rewrite or replace earlier proof results; it only records the content-completeness remediation.

## Rerun — after 3565819 containment trace fields

FAIL

### Environment

- Branch: `main`
- HEAD: `35658196b501afc4f183c8d987ada3e153d680c3`
- Runtime path: `/Volumes/Dev_SSD/Codexify-main`
- Services refreshed: `docker compose up -d --no-deps backend worker-chat`

### Health evidence summary

- `GET /health` returned `status: ok`.
- `GET /health/chat` returned a healthy local runtime with provider `local`, model `library2/ministral-3:8b`, and a fresh worker heartbeat.
- `GET /api/health/llm` returned `status: ok` / `online` and reported `model_resolution.source: LOCAL_CHAT_MODEL`.
- `GET /api/llm/catalog` returned successfully from the live local runtime.

### Thread setup

- Thread A id: `25`
- Thread A refusal message id: `55`
- Thread A refusal text: `I can't view the image.`
- Thread B id: `26`
- Thread B user message id: `56`
- Thread B assistant message id: `57`
- Thread B task id: `2e817350-e8fc-4b91-9881-a946b252cf6e`
- Thread B turn id: `58db4453-2a60-4a70-9da7-dd0943b4eeda`
- Thread B image payload marker: `<!-- cfy-media-src:/media/images/20260505-f36a04bc--proof.png?sig=... -->`

### Model-selection evidence

- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `library2/ministral-3:8b`
- `selection_source`: `explicit`
- `policy_reason`: `LOCAL_CHAT_MODEL`
- `fallback_reason`: `null`
- `model_resolution.message`: `requested model 'medgemma:4b-it-q8_0' was overridden by configured local chat model 'library2/ministral-3:8b' from LOCAL_CHAT_MODEL`

### Image-routing evidence

- The assistant response on Thread B was refusal-like, but it was not the seeded Thread A refusal text.
- `image_routing_path` in the persisted eval snapshot and assistant metadata was `null`.
- `image_routing_absence_reason` in the persisted eval snapshot and assistant metadata was `null`.
- `assistant_vision_refusal_on_image_turn` did not appear in the persisted trace for this run.
- Image interpretation fidelity was not established from the live evidence.

### RAG/debug trace evidence

- The persisted eval snapshot was available and contained:
  - `retrieval_policy`
  - `retrieval_provenance`
  - `retrieval_suppression`
  - `retrieval_executed`
  - `retrieval_absence_reason`
  - `model_selection`
- `retrieval_policy` resolved to the project posture with widening enabled.
- `retrieval_provenance` reported `requested_source_mode: project`, `normalized_source_mode: project`, `retrieval_status: no_obsidian_results`, and a nonzero semantic hit count from the current thread context.
- `retrieval_suppression` reported an empty suppression list and `total_suppressed: 0`.
- The live `GET /api/chat/debug/rag-trace/26/latest` response still returned the minimal shell and reported `trace_unavailable_reason: trace_source_unavailable`.
- Thread A refusal text did not appear in Thread B messages, task events, persisted eval snapshot content, or the rag-trace response.
- The public live debug route still did not expose the containment-grade fields from the persisted snapshot, so containment is not machine-readably proven end-to-end.

### Result interpretation

- Model substitution is explained machine-readably.
- Image routing truth is still incomplete because the supported image turn did not record a non-null `image_routing_path` or `image_routing_absence_reason`.
- Containment is **not** machine-readably proven on the live supported path.

### Limitations

- RAG trace remains transient and the public route still returned `trace_source_unavailable`.
- No durable forensic store was introduced.
- The separate Compose migrator issue remains outside this task.
- The frontend Vitest blocker remains outside this task.

### Follow-up recommendations

- Rerun after the rag-trace promotion path exposes the persisted snapshot fields for the live thread.
- If the local model substitution is intentional, add a non-null image-routing absence reason so the live proof can distinguish substitution from unsupported image handling.

### Remediation note

- The runtime fix in this slice now promotes persisted eval snapshot fields through the public rag-trace route and records a canonical image-routing absence reason when a requested vision-capable model is substituted to a non-vision local default.
- The proof is ready to rerun after the refreshed services pick up this change.

### Current rerun readiness

- The live blockers identified in the previous rerun are now addressed in code and covered by regression tests.
- A fresh live rerun should now be able to validate whether containment is machine-readably proven on the supported path.

## Rerun — after 8093953 containment promotion fix

FAIL

### Environment

- Branch: `main`
- HEAD: `809395304f1fce95ef06e5a6bc0d08f263b131f6`
- Runtime path: `/Volumes/Dev_SSD/Codexify-main`
- Services refreshed: `docker compose up -d --no-deps backend worker-chat`

### Health evidence summary

- `GET /health` returned `status: ok`.
- `GET /health/chat` returned a healthy local runtime with provider `local`, model `library2/ministral-3:8b`, and a fresh worker heartbeat.
- `GET /api/health/llm` returned `status: ok` / `online` and reported `model_resolution.source: LOCAL_CHAT_MODEL`.
- `GET /api/llm/catalog` returned successfully from the live local runtime.

### Thread setup

- Thread A id: `31`
- Thread A refusal message id: `66`
- Thread A refusal text: `I can't view the image.`
- Thread B id: `32`
- Thread B user message id: `68`
- Thread B assistant message id: `69`
- Thread B task id: `f843036c-fac6-4079-a6a7-d16965a25d6c`
- Thread B turn id: `fed497ef-d80c-43a1-8c66-3e322bf28c02`
- Thread B image payload marker: `<!-- cfy-media-src:/media/images/20260505-fb63c1ef--test.jpg?sig=-VGr0RX9AbSCFoDZNX62BqXE6_-FjVEFrj3kvqWS5IQ -->`

### Model-selection evidence

- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `medgemma:4b-it-q8_0`
- `selection_source`: `explicit`
- `policy_reason`: `explicit`
- `fallback_reason`: `null`
- `model_resolution.message`: `null`
- The requested local vision-capable override was honored on the live path, so there was no substitution reason to report.

### Image-routing evidence

- The assistant response on Thread B was refusal-like, but it was not the seeded Thread A refusal text.
- `image_routing_path` in the persisted eval snapshot and assistant metadata was `null`.
- `image_routing_absence_reason` in the persisted eval snapshot and assistant metadata was `null`.
- `assistant_vision_refusal_on_image_turn` did not appear in the persisted trace for this run.
- Image interpretation fidelity was not established from the live evidence.

### RAG/debug trace evidence

- The task completed event was present in the live task-event stream and carried a nested trace payload.
- The nested task trace and the persisted eval snapshot both contained:
  - `retrieval_policy`
  - `retrieval_provenance`
  - `retrieval_suppression`
  - `retrieval_executed`
  - `retrieval_absence_reason`
  - `model_selection`
- `retrieval_policy` resolved to the project posture with widening enabled.
- `retrieval_provenance` reported `requested_source_mode: project`, `normalized_source_mode: project`, `retrieval_status: no_obsidian_results`, and a nonzero semantic hit count from the current thread context.
- `retrieval_suppression` reported an empty suppression list and `total_suppressed: 0`.
- The live `GET /api/chat/debug/rag-trace/32/latest` response returned the promoted snapshot and did not report `trace_unavailable_reason`.
- Thread A refusal text did not appear in Thread B messages, task events, persisted eval snapshot content, or the rag-trace response.
- The public live debug route now exposes the containment-grade retrieval fields from the persisted snapshot, but containment is still not machine-readably proven end-to-end because image-routing truth remains null/null.

### Result interpretation

- Model selection is explained machine-readably and now honors the requested local vision-capable override.
- Image routing truth is still incomplete because the supported image turn did not record a non-null `image_routing_path` or `image_routing_absence_reason`.
- Containment is **not** machine-readably proven on the live supported path.

### Limitations

- RAG trace remains transient and the public route still depends on the latest persisted snapshot rather than a durable forensic store.
- No durable forensic store was introduced.
- The separate Compose migrator issue remains outside this task.
- The frontend Vitest blocker remains outside this task.

### Follow-up recommendations

- Rerun after the image-routing branch records a non-null routing path or absence reason for supported image turns.
- Keep the promoted rag-trace surface aligned with the persisted snapshot so future proofs stay machine-readable.

### Remediation note after native image-routing truth fix

- Native vision-capable image turns now stamp `image_routing_path: native_multimodal_vision` when the provider-ready payload still carries image content.
- When the runtime cannot confirm image payload routing for a vision-capable model, it now stamps `image_routing_absence_reason: vision_model_selected_but_image_payload_not_routed`.
- The proof is ready to rerun once the refreshed services are live.
