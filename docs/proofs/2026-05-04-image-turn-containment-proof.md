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
