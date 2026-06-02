# Provider Tokenization Containment Review

## Scope

This is a containment review for commit
`ffff2f30788e326fa43e5d4594c686e603833a87`, which canonicalized provider
failure-kind and transport-classification values used by the primary Guardian
chat completion path.

This post-repair update records that the original `HOLD` verdict was superseded
by the registry/catalog repair commit
`e500ac1ec80e28290111e35b9c5cb596c4284a96`.

This review artifact update does not change runtime behavior, provider timeout
policy, provider availability policy, catalog visibility semantics, frontend
behavior, database schema, migrations, Obsidian retrieval/indexing behavior,
supported profile posture, or release posture.

## Repository Safety

Original review context:

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- Reviewed tokenization commit:
  `ffff2f30788e326fa43e5d4594c686e603833a87`

Post-repair update context:

- Repair commit:
  `e500ac1ec80e28290111e35b9c5cb596c4284a96`
- Current local checkout also contains the repair as the current branch tip.
- Dirty/untracked files before this update: this review artifact only.
- This task edited only
  `docs/audits/chat/2026-05-30-provider-tokenization-containment-review.md`.

Recent commit surface verification:

- `ffff2f30788e326fa43e5d4594c686e603833a87` touched protocol-token,
  provider/router, health, worker, and focused test surfaces.
- The original tokenization commit did not touch provider registry or catalog
  files.
- `e500ac1ec80e28290111e35b9c5cb596c4284a96` repaired registry/catalog
  validation by touching:
  - `guardian/core/provider_registry.py`
  - `guardian/tests/core/test_provider_registry.py`
  - `tests/routes/test_llm_catalog.py`
- No vault files, raw note text, real vault paths, supported profiles, frontend
  files, database models, migrations, or release-truth docs were edited by this
  review update.

## Reviewed Change Surface

Files touched by the tokenization commit:

- `guardian/core/ai_router.py`
- `guardian/protocol_tokens.py`
- `guardian/routes/health.py`
- `guardian/workers/chat_worker.py`
- `tests/contracts/test_protocol_tokens.py`
- `tests/core/test_ai_router.py`
- `tests/workers/test_chat_worker_first_token_timing.py`

Token domains added:

- `GuardianProviderFailureKind`
- `GUARDIAN_PROVIDER_FAILURE_KINDS`
- `GuardianProviderTransportClassification`
- `GUARDIAN_PROVIDER_TRANSPORT_CLASSIFICATIONS`

Registry/catalog follow-through from the repair commit:

- Provider registry now uses canonical `GuardianProviderFailureKind` values for
  model-index timeout and transport failure metadata.
- Provider-registry and catalog tests assert canonical provider failure-kind
  values where those values are surfaced.
- Supported-profile environment leakage is isolated in the registry/catalog
  tests so explicit test `Settings` objects are not accidentally converted into
  supported-profile validation tests.

## Post-Repair Update

Historical context: the initial containment review verdict was `HOLD` because
required provider-registry and catalog validation failed. That HOLD finding is
now superseded by repair commit
`e500ac1ec80e28290111e35b9c5cb596c4284a96`.

Root cause:

- Ambient supported-profile environment state leaked into provider registry and
  LLM catalog tests.
- Those tests intentionally mutate explicit `Settings` objects to exercise
  registry/catalog policy scenarios, but the leaked supported-profile gate
  rejected or filtered the route before the intended assertions ran.

Repair:

- Isolated `CODEXIFY_SUPPORTED_PROFILE` in the affected registry/catalog tests.
- Replaced raw registry/catalog-adjacent provider failure-kind assertions and
  writes with canonical `GuardianProviderFailureKind` token values.

Result:

- `guardian/tests/core/test_provider_registry.py` now passes.
- `tests/routes/test_llm_catalog.py` now passes.
- No runtime provider policy, availability policy, catalog visibility policy,
  timeout duration, retry/fallback behavior, or release posture changed.

## Token Domain Review

Added token domains and expected values:

- `GuardianProviderFailureKind.PROVIDER_TIMEOUT = "provider_timeout"`
- `GuardianProviderFailureKind.TRANSPORT_ERROR = "transport_error"`
- `GuardianProviderFailureKind.REQUEST_ERROR = "request_error"`
- `GuardianProviderTransportClassification.TIMEOUT = "timeout"`
- `GuardianProviderTransportClassification.CONNECTION_REFUSED =
  "connection_refused"`
- `GuardianProviderTransportClassification.DNS_ERROR = "dns_error"`
- `GuardianProviderTransportClassification.REQUEST_ERROR = "request_error"`

Frozenset exports are present:

- `GUARDIAN_PROVIDER_FAILURE_KINDS`
- `GUARDIAN_PROVIDER_TRANSPORT_CLASSIFICATIONS`

Protocol token tests lock the expected enum values and frozenset contents in
`tests/contracts/test_protocol_tokens.py`.

The tokenization is now extended through the primary provider/chat path and the
registry/catalog-adjacent failure-kind surfaces. Remaining prose, variable
names, non-contract text, and contract-test expected literal values are
acceptable.

## Provider Registry Review

Provider registry behavior did not change as provider policy. The registry
continues to own provider authorization, availability, capability, disabled
reason, local-provider policy, cloud-provider policy, egress policy, and support
claim boundaries.

The repair only:

- isolates ambient supported-profile env in tests that supply explicit
  `Settings`
- replaces model-index timeout/transport failure-kind literals with canonical
  provider failure-kind token values
- updates tests to assert those canonical values

No provider availability or support claim was widened.

## Catalog Surface Review

`/api/llm/catalog` output semantics did not widen.

No repair changed:

- catalog visibility
- hidden provider behavior
- disabled state behavior
- provider metadata shape
- provider support claims

Catalog tests now prove the same catalog behavior under isolated test
configuration and canonical failure-kind assertions.

## Health and Operator Truth Review

Health semantics did not drift.

- `/health/chat` remains queue/worker truth and does not prove a specific
  completion attempt will finish.
- `/api/health/llm` remains provider/runtime truth and does not prove
  per-message completion or first-token delivery.
- A green health surface still must not be interpreted as eventual completion.

Provider posture still requires reading supported profile, catalog, health,
task events, logs, and persisted assistant rows together.

## Worker and AI Router Review

Provider first-token timeout classification remains preserved:

- AI router classifies provider request timeouts as `provider_timeout` with
  transport classification `timeout`.
- Worker failure metadata derives timeout runtime status from canonical
  transport/failure metadata.
- `task.failed` still carries provider timeout metadata after
  `AWAITING_FIRST_TOKEN`.

Transcript integrity remains intact:

- Provider timeout does not persist fake assistant output.
- Provider timeout does not fabricate `first_token_at`.
- First output and first token remain separate evidence surfaces.

## Metadata-Key Decision Review

`failed_after_state` remains a stable JSON key. Its values are lifecycle-state
evidence, currently derived from `TaskLifecycleState`.

`provider_request_started` remains a stable JSON boolean key.

`first_output_observed` remains a stable JSON boolean key.

No broad metadata-key registry was introduced. A metadata-key registry is not
required before the next phase unless the repo decides to formalize task-event
metadata schemas beyond value-domain tokens.

## Normal Behavior Preservation

Normal behavior remains preserved in validation:

- non-streaming AI router/provider paths
- streaming provider paths
- provider timeout path
- first-token timeout task metadata
- health endpoint behavior
- provider registry validation
- catalog route validation
- Obsidian/source-mode/context-directive behavior

No known current validation failures remain for the reviewed proof surface.

## Real-Vault Safety

This review update did not run real-vault indexing and did not call
`/api/obsidian/index`.

This review update did not inspect, print, summarize, or commit vault contents.

No vault files were committed by the tokenization or registry/catalog repair
commits. The prior scoped proof and rollback artifacts remain intact.

## Findings

### High

None.

### Medium

None.

### Low

None.

### Non-blocking follow-ups

- Frontend timeout-versus-offline presentation audit remains open.
- Synthetic slow-provider or warmup proof remains open.
- Retry/replay linkage proof remains open.
- Metadata-key registry proposal is not needed now, but could be revisited if
  task-event metadata schemas become formal API contracts.

## Required Fixes Before Next Phase

None.

## Recommended Follow-Up Tasks

1. Audit frontend request-state presentation for provider timeout versus
   offline.
2. Run a synthetic slow-provider/warmup proof without real-vault expansion.
3. Add retry/replay linkage proof for timeout followed by later completion.
4. Consider a metadata-key registry only if task-event metadata becomes a
   formal schema.

## Validation

Post-repair validation:

- `./.venv/bin/pytest -v guardian/tests/core/test_provider_registry.py` -
  passed, 17 tests.
- `./.venv/bin/pytest -v tests/routes/test_llm_catalog.py` - passed, 15 tests.
- `./.venv/bin/pytest -v tests/contracts/test_protocol_tokens.py` - passed, 24
  tests.
- `./.venv/bin/pytest -v tests/core/test_ai_router.py` - passed, 17 tests.
- `./.venv/bin/pytest -v tests/workers/test_chat_worker_first_token_timing.py`
  - passed, 5 tests.
- `./.venv/bin/pytest -v tests/routes/test_health_endpoints.py` - passed, 9
  tests.
- Required chat context/source/Obsidian adjacent tests - passed.
- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

Validation interpretation:

- Registry/catalog failures were caused by test-environment leakage, not
  provider policy drift.
- Canonical provider failure-kind usage now reaches registry/catalog-adjacent
  failure-kind surfaces.
- No runtime proof or release-support widening is implied by this docs update.

## Final Verdict

`PASS WITH FOLLOW-UPS`

The tokenization and registry/catalog follow-through are contained. Provider
failure-kind tokenization now covers the primary provider/chat path and the
registry/catalog-adjacent failure-kind surfaces. Health semantics, provider
availability policy, catalog visibility, timeout policy, transcript integrity,
Obsidian retrieval semantics, and local-first beta posture remain unchanged.
