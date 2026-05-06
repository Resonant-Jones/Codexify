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

## Rerun — after 82da47b native image-routing truth

FAIL

### Environment

- Branch: `main`
- HEAD: `52152b59`
- Runtime path: `/Volumes/Dev_SSD/Codexify-main`
- Services refreshed: `docker compose up -d --no-deps backend worker-chat`

### Health evidence summary

- `GET /health` returned `status: ok`.
- `GET /health/chat` returned `status: healthy` with a fresh worker heartbeat.
- `GET /api/health/llm` returned `status: ok` / `online`.
- `GET /api/llm/catalog` returned `200` and the live catalog included `medgemma:4b-it-q8_0` as a vision-capable local model.

### Thread setup

- Thread A id: `33`
- Thread A refusal message id: `70`
- Thread A refusal text: `I can't view the image.`
- Thread B id: `34`
- Thread B user message id: `71`
- Thread B assistant message id: `72`

### Model-selection evidence

- Requested provider/model: `local` / `medgemma:4b-it-q8_0`
- Final provider/model: `local` / `library2/ministral-3:8b`
- `selection_source`: `explicit`
- `policy_reason`: `LOCAL_CHAT_MODEL`
- `fallback_reason`: `null`
- `model_resolution.message`: `requested model 'medgemma:4b-it-q8_0' was overridden by configured local chat model 'library2/ministral-3:8b' from LOCAL_CHAT_MODEL`

### Image-routing evidence

- The user turn carried a real uploaded image attachment marker and a signed `src_url`.
- The assistant response was refusal-like:
  - `Since I can’t view images directly, I’ll need you to describe proof.png for me...`
- `image_routing_path` in both the assistant metadata and persisted eval snapshot was `null`.
- `image_routing_absence_reason` in both the assistant metadata and persisted eval snapshot was `null`.
- `assistant_vision_refusal_on_image_turn` did not appear in the persisted trace for this run.
- Native vision routing was therefore **not** machine-readably stamped on the live path.

### Trace evidence summary

- The task-event stream was present and ended in a terminal `task.completed` event for task id `718745d2-2892-4813-a0b6-91d3c63c940d`.
- The terminal `task.completed` payload included:
  - `retrieval_policy`
  - `retrieval_provenance`
  - `retrieval_suppression`
  - `retrieval_executed`
  - `retrieval_absence_reason`
  - `model_selection`
- The persisted eval snapshot and the promoted rag-trace response both carried the same retrieval truth:
  - `retrieval_policy` present
  - `retrieval_provenance` present
  - `retrieval_suppression` present
  - `retrieval_executed: true`
  - `retrieval_absence_reason: null`
  - `model_selection` present
- `trace_unavailable_reason` was cleared / absent once the persisted snapshot existed.
- `GET /api/chat/debug/rag-trace/34/latest` promoted the persisted snapshot and did not regress to a source-unavailable shell.

### Containment check

- Thread A refusal text did not appear in Thread B messages, task events, trace, or eval snapshot.
- Containment is still **not** machine-readably proven because image-routing truth remained `null` / `null`.

### Result interpretation

- The supported live path now exposes the retrieval container truth and clears `trace_unavailable_reason` once a persisted snapshot exists.
- The remaining blocker is image-routing truth: the live image turn still did not stamp either a native path or a canonical absence reason.
- Because image-routing truth is still missing, the proof fails even though Thread A did not visibly leak into Thread B.

### Limitations

- This proof only shows that the live task-event, eval snapshot, and promoted rag-trace lanes are wired together.
- It does not establish that the runtime stamped native vision routing for this turn.
- The trace remains transient; this is not a durable forensic record.

### Follow-up recommendations

- Re-run the native image-routing proof only after the runtime path stamps either:
  - `image_routing_path: native_multimodal_vision`, or
  - `image_routing_absence_reason: vision_model_selected_but_image_payload_not_routed`
- Do not treat this run as containment-pass evidence.

## Remediation Note - live routing fallback and trace contract cleanup

- The live completion path now has a defensive fallback that stamps image-routing truth when the helper path fails to populate it, so image turns no longer rely on a null/null image-routing surface.
- `GET /api/chat/debug/rag-trace/{thread_id}/latest` now clears `trace_unavailable_reason` once a persisted snapshot exists, while still surfacing `trace_source_unavailable` for genuine no-evidence cases.
- The proof is ready to rerun against the refreshed runtime, but this document still records the prior FAIL history until a new live PASS is observed.

## Remediation Note - origin-backed image routing hint

- The chat route now forwards a compact image-attachment hint through task origin metadata, and the completion service consumes that hint before finalizing image-routing truth.
- That bridge is intended to keep image turns from collapsing back to `null` / `null` when the persisted image payload is still present but the downstream routing helper missed it.
- The proof remains ready to rerun; this document still preserves earlier FAIL sections until a fresh live PASS is observed.

## Rerun — after aa6a76b origin-backed image-routing bridge

- Result: `FAIL`
- Environment:
  - branch: `main`
  - HEAD: `aa6a76b2d0b2476292db3ea6150d8bf291dd8588`
  - runtime path: supported local Docker Compose backend/worker services refreshed with `docker compose up -d --build --no-deps backend worker-chat`
- Health evidence summary:
  - `GET /health` -> `200 ok`
  - `GET /health/chat` -> `200 healthy`
  - `GET /api/health/llm` -> `200 ok / online`
  - `GET /api/llm/catalog` -> `200` with local catalog available
- Thread setup:
  - Thread A id: `55`
  - Thread A refusal message id: `103`
  - Thread A refusal text: `I can't view the image.`
  - Thread B id: `56`
  - Thread B user message id: `104`
  - Thread B assistant message id: `105`
  - Thread B task id: `6ff7db81-c1e6-404a-a8c0-cd47e7c6826f`
  - Thread B turn id: `f9c63bbe-e9b2-458d-ab27-5d27221ef64f`
- Model-selection evidence:
  - requested provider/model: `local` / `medgemma:4b-it-q8_0`
  - final provider/model: `local` / `library2/ministral-3:8b`
  - `selection_source`: `explicit`
  - `policy_reason`: `LOCAL_CHAT_MODEL`
  - `fallback_reason`: `null`
  - `model_resolution.message`: `requested model 'medgemma:4b-it-q8_0' was overridden by configured local chat model 'library2/ministral-3:8b' from LOCAL_CHAT_MODEL`
- Image-routing evidence:
  - the user turn carried a real uploaded image attachment marker and signed `src_url`
  - assistant metadata: `image_routing_path: null`, `image_routing_absence_reason: null`
  - task.completed payload: `image_routing_path: null`, `image_routing_absence_reason: null`
  - persisted eval snapshot trace: `image_routing_path: null`, `image_routing_absence_reason: image_routing_not_evaluated`
  - promoted rag-trace: `image_routing_path: null`, `image_routing_absence_reason: image_routing_not_evaluated`
  - `assistant_vision_refusal_on_image_turn` did not appear in the persisted trace for this run
  - the selected local model remained non-vision, but the live path still failed to stamp a canonical absence reason
- Trace evidence summary:
  - `retrieval_policy` present in the task.completed payload, eval snapshot, and promoted rag-trace
  - `retrieval_provenance` present in the task.completed payload, eval snapshot, and promoted rag-trace
  - `retrieval_suppression` present in the task.completed payload, eval snapshot, and promoted rag-trace
  - `retrieval_executed: true`
  - `retrieval_absence_reason: null`
  - `trace_unavailable_reason` was absent/cleared once the persisted snapshot existed
  - Thread A refusal text did not appear in Thread B messages, task events, trace, or eval snapshot
- Result interpretation:
  - containment is still not machine-readably proven
  - the live bridge prevented a silent no-evidence shell, but image-routing truth still did not reach a canonical non-null stamp
  - the refusal-like assistant output was not enough to prove containment, because the proof still lacks image-routing truth
- Limitations:
  - the trace remains transient and debug-oriented
  - the live proof still depends on completion timing and persisted snapshot availability
  - this rerun does not establish a durable forensic record
- Follow-up recommendations:
  - continue investigating why the live completion path retains `image_routing_path: null` / `image_routing_absence_reason: image_routing_not_evaluated` even though the task origin now carries an image-attachment hint
  - rerun the proof only after the runtime stamps either `native_multimodal_vision` or a canonical absence reason on the live turn

## Remediation Note — image-routing normalization

- The completion path now normalizes known image turns from the live origin hint, trace state, and payload summary before persistence.
- `image_routing_not_evaluated` is now reserved for genuine no-image / no-routing-evidence cases; known image turns should instead stamp either `native_multimodal_vision` or a canonical absence reason.
- The focused regression slice is green, so the live containment proof is ready to rerun against the refreshed runtime.

## Rerun — after e4d6961 image-routing normalization

- Result: `FAIL`
- Environment:
  - branch: `main`
  - HEAD: `e4d69614f2bc0ce8a8f9a6d6b8d88b0ce8e6f0fe`
  - runtime path: supported local Docker Compose services refreshed with `docker compose up -d db backend worker-chat`
  - services refreshed: `db`, `backend`, `worker-chat`
- Health evidence summary:
  - `GET /health` -> `200 ok`
  - `GET /health/chat` -> `200 healthy`
  - `GET /api/health/llm` -> `200 ok / online`
  - `GET /api/llm/catalog` -> `200`
- Thread setup:
  - Thread A id: `3`
  - Thread A refusal message id: `2`
  - Thread B id: `4`
  - Thread B user image message id: `3`
  - Thread B assistant message id: `not available; completion failed before assistant persistence`
  - task id: `99188f85-0661-4921-817d-8e728064b7f5`
  - turn id: `8a764c3e-5efb-47fc-a560-e23f7697b8bb`
- Requested/final model and substitution reason:
  - requested provider/model: `local` / `medgemma:4b-it-q8_0`
  - final provider/model: `not available; worker failed before completion settled`
  - `selection_source`: `explicit` in the task event stream
  - `policy_reason`: `not available`
  - `fallback_reason`: `not available`
  - `model_resolution.message`: `not available`
  - task.failed payload still reported `provider: local` and `model: medgemma:4b-it-q8_0`
- Image-routing evidence:
  - image payload marker evidence: `<!-- cfy-media:image:2b6c264a-04dc-4ffd-91e6-2a6ccabf2f16 -->` plus signed `cfy-media-src:/media/images/20260506-43739c56--proof.png?...`
  - image attachment count surfaced in thread metadata candidate trace: `1`
  - assistant metadata: not available because the worker failed before assistant persistence
  - task.completed payload: not available because the task failed instead
  - eval snapshot image-routing fields: not available; `trace_snapshot` was `null`
  - rag-trace image-routing fields: `image_routing: null`, `trace_unavailable_reason: trace_source_unavailable`
  - persisted thread metadata candidate trace still showed `image_routing_path: null` and `image_routing_absence_reason: image_routing_not_evaluated`, which is the stale state the normalization fix was intended to prevent from becoming final
- Trace evidence summary:
  - task events observed: `task.state`, `task.running`, `task.created`, `task.failed`
  - task.failed error: `UnboundLocalError: cannot access local variable 'retained_result_count' where it is not associated with a value`
  - `retrieval_policy` / `retrieval_provenance` / `retrieval_suppression` did not reach a persisted completion snapshot because completion never settled
  - `trace_unavailable_reason` remained `trace_source_unavailable` on the eval and rag-trace debug surfaces because there was no persisted snapshot
  - Thread A refusal text did not appear in Thread B messages or task events
- Thread A leakage check:
  - no visible leak from Thread A into Thread B
- Whether containment is machine-readably proven:
  - `No`
- Limitations:
  - the worker crashed before completion snapshot persistence, so this rerun could not test the final image-routing normalization contract
  - the debug surfaces therefore remained in no-snapshot mode instead of promoting containment evidence
  - the rerun does not establish containment proof under the stricter current contract
- Remaining blockers:
  - the worker-side `UnboundLocalError` at `guardian/core/chat_completion_service.py:2990` prevented completion from settling
  - because completion never settled, the proof could not reach the image-routing normalization check on the persisted trace path
  - the separate Compose migrator issue remains outside this task
  - the frontend Vitest resolution issue remains outside this task
