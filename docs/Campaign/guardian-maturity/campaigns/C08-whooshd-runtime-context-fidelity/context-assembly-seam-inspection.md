# C08-T004a Context Assembly Seam Inspection

## Scope

This is an inspection artifact only. It does **not** prove context delivery, system identity delivery, or add tests. It does not change runtime behavior. It maps the assembly chain from chat task to provider-call boundary for C08-T004b to write focused proof tests.

## Assembly Chain Map

| Step | Function | File | Line | Input | Output | Context | System Identity |
|------|----------|------|------|-------|--------|---------|-----------------|
| 1. Chat route | `chat.py` routes | `guardian/routes/chat.py` | — | HTTP request | Chat task enqueued | Not yet | Not yet |
| 2. Worker entry | `chat_worker.py` | `guardian/workers/chat_worker.py` | — | Task from queue | Calls completion service | Not yet | Not yet |
| 3. Completion service | `_execute_completion_attempt()` | `guardian/core/chat_completion_service.py` | 335 | Chat task | Provider call | Constructed here | Constructed here |
| 4. Message assembly | `_build_messages_for_llm_compat()` | `guardian/core/chat_completion_service.py` | 391 | Chat task + user_id | Messages list for provider | **Inserted** via `build_context_system_message()` | **Inserted** via persona/profile |
| 5. Context injection | `build_context_system_message()` | `guardian/core/chat_completion_service.py` | 469 | Context bundle dict | System message string or None | **Primary seam** — context → system message | N/A |
| 6. Provider resolution | `resolve_provider_for_model()` | `guardian/core/provider_registry.py` | — | Model ID | Provider name | N/A | Carries model identity |
| 7. Provider dispatch | `ai_router` | `guardian/core/ai_router.py` | — | Messages + provider | Completion result | N/A | N/A |

## Critical Function Notes

### `_build_messages_for_llm_compat()` (line 391)

Called by `_execute_completion_attempt`. Assembles the final messages array for the provider. Accepts `user_id`, memory preselection parameters. Returns `(messages, model_id, provider_name, completion_kwargs, context_bundle)`. This is the **primary payload boundary** for C08-T004b proof.

### `build_context_system_message()` (line 469)

Takes a context bundle dict. Returns a system message string or None. This is where retrieval/workspace context becomes a system message. Key questions for C08-T004b: does this function's output appear in the final messages? Is it called for Whoosh'd/local paths?

### `_execute_completion_attempt()` (line 335)

Orchestrates the full completion flow. Calls `_build_messages_for_llm_compat()`, then dispatches to provider via `ai_router`. Accepts `provider` parameter. The provider is resolved earlier via `resolve_provider_for_model()`.

### Provider resolution chain

`first_enabled_provider()` → `resolve_provider_for_model()` → `normalize_provider()` → `default_model_for_provider()`. The chain resolves model ID to provider. Whoosh'd is not explicitly in the `llm_catalog.py` provider list (C08-T001 finding). The local provider path is `LOCAL_PROVIDER_VENDOR` which gates Whoosh'd sidecar activation.

## Whoosh'd/Local Lane Map

| Element | Status | Notes |
|---------|--------|-------|
| Local provider selection | Via `LOCAL_PROVIDER_VENDOR` config | Gated in `whooshd_sidecar.py:is_whooshd_configured` |
| Whoosh'd representation | `whooshd_sidecar.py` sidecar provider | Not directly in `llm_catalog.py` |
| Model identity in payload | Provided via `_build_messages_for_llm_compat()` return | `model_id` field in return tuple |
| Context bundle path | `build_context_system_message()` → `_build_messages_for_llm_compat()` | Must verify for Whoosh'd path |
| System identity path | Persona/profile → system prompt builder → `_build_messages_for_llm_compat()` | Must verify for Whoosh'd path |
| Cloud fallback | Not at this seam — provider selection is upstream | Local-only posture set before `ai_router` dispatch |

## Candidate C08-T004b Proof Seam

### Target

Patch `_build_messages_for_llm_compat()` to capture its return tuple without executing real completion. The return is `(messages, model_id, provider, completion_kwargs, context_bundle)`. This is the smallest seam that captures both context and system identity in the final provider-call payload.

### Test file

`tests/core/test_whooshd_context_bundle_system_identity_delivery.py`

### Assertions needed

- Messages list contains system message from context bundle
- Messages list contains system message from persona/profile identity
- Messages list preserves user message order
- Messages list preserves thread history
- `model_id` carries selected model identity, not display label
- `provider` carries provider name
- Context bundle is not None when retrieval succeeded
- Context bundle is None or empty when retrieval produced nothing
- No real daemon, network, process, Redis, Postgres

### Required fixtures

- Fake `ChatCompletionTask` with deterministic properties
- Fake context bundle dict with known content
- Monkeypatched persona/profile resolution returning known system identity

### Risks

- Over-mocking could hide actual provider dispatch differences between Whoosh'd and cloud paths
- The `_build_messages_for_llm_compat()` function signature is complex (11 parameters with dynamic kwargs) — test may need careful kwargs injection
- Context bundle may be None for non-retrieval completions — need to distinguish Whoosh'd path specifically

## Boundary Table

| Boundary | Status |
|----------|--------|
| Assembly seam inspection ≠ context delivery proof | Explicit |
| Context delivery proof ≠ live model availability | Explicit |
| Context delivery proof ≠ operator diagnostics | Explicit |
| Context delivery proof ≠ execution authority | Explicit |
| System prompt presence ≠ durable identity mutation | Explicit |
| Endpoint health proof ≠ context fidelity proof | Explicit |
| Model inventory proof ≠ context fidelity proof | Explicit |
| Provider-call payload proof ≠ release support | Explicit |

## Gap Register

| Gap | Evidence | Blast Radius | Proposed Task |
|-----|----------|-------------|---------------|
| Whoosh'd not in `llm_catalog.py` | C08-T001 audit | Provider dispatch may skip Whoosh'd | C08-T004b must verify local provider lane |
| Context bundle may be None | `build_context_system_message()` returns None for empty input | Context silently absent | C08-T004b must test empty context case |
| System identity injection path for Whoosh'd unverified | No Whoosh'd-specific path found | System identity may not reach local provider | C08-T004b must verify |

## Risk Register

| Risk | Evidence | Mitigation |
|------|----------|------------|
| Over-mocking hides Whoosh'd-specific dispatch differences | `ai_router` abstracts provider dispatch | C08-T004b must use local provider lane or Whoosh'd-specific fixture |
| Context bundle assembly changed in future commits | `chat_completion_service.py` is 4966 lines | C08-T004b tests must be deterministic and narrow |
| Provider resolution may not trigger Whoosh'd sidecar for local completions | `whooshd_sidecar.py` gated on `LOCAL_PROVIDER_VENDOR` | C08-T004b must verify local provider path |

## C08-T004 Split Plan

1. `C08-T004a: Inspect chat completion context assembly seams` ← THIS TASK
2. `C08-T004b: Prove Whoosh'd context bundle and system identity delivery` — focused tests at `_build_messages_for_llm_compat()` boundary, capture messages/model_id/context
3. `C08-T004c: Close Whoosh'd context fidelity proof` — validation + governance closeout

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C08-T004b: Prove Whoosh'd context bundle and system identity delivery`
