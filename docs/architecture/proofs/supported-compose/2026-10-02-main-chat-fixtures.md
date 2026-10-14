# Current-main chat fixture alignment

Date: 2026-10-02. Baseline: `56c980914142e2affba76d755c30fa20fb8bccb6`.
Classification: standard, authorized fixture correction under the active ordinary
chat Goal and Codex Development Operator Level 0. Production behavior unchanged.

## Evidence and change

The preceding cancellation proof independently reproduced six neighboring
provider-resolution failures with both baseline and repaired worker loops.
Two synthetic routing cases reached ambient egress policy instead of their
synthetic catalog; four accepted-Persona cases used a positional-only boolean
lock stub that rejected the current `turn_id` acceptance argument.

The routing fixture now explicitly owns its synthetic provider/model catalog
and disables env-file loading for its Settings instance. The unavailable-model
case supplies canonical explicit-selection metadata, asserts no degraded fallback,
and asserts no ContextBroker construction. These mocks prove routing under a
controlled catalog, not live inventory or production egress enforcement.

The Persona acceptance fixture now returns acquired and renewed canonical lock
envelopes. It explicitly controls create/mark durable-attempt seams because the
fixture's fake chat database proves Persona snapshot behavior rather than attempt
persistence. The production acceptance function still captures and serializes the
selection. Independent acceptance/attempt/deadline suites remain in validation.

No source policy was relaxed. No production, schema, token, provider, queue,
identity, persistence, ADR, or release claim changed.

## Validation

From repository root:

```sh
PYTHONPATH=. /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q \
  guardian/tests/workers/test_chat_worker_provider_resolution.py \
  guardian/tests/test_persona_profile_runtime.py \
  tests/workers/test_chat_worker_explicit_model_authority.py \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/core/test_chat_completion_attempt_persistence.py \
  tests/tasks/test_chat_completion_deadline.py
```

Result: **79 passed**, exit 0. `git diff --check`: passed.
External artifacts:
`/private/tmp/codexify-main-chat-fixtures-56c980914-20261002/results.xml`
and `results.log` in the same directory.

The independent exact-model tests exercise production local resolution with a
synthetic inventory and require unavailable explicit models to fail before
execution, persistence, or fallback while releasing the owned lock. Acceptance
and attempt tests cover ordering/failure semantics with controlled dependencies.
These are test proofs, not actual PostgreSQL or supported-Compose qualification.

## Closeout limits

Files: the two fixture suites and this receipt. ADR impact: none.
Documentation follow-through: this receipt only; current-state HOLD unchanged.
The full ordinary-chat Goal remains active. Fresh current-tip provider/browser,
PostgreSQL, retrieval-scope, terminal/recovery, deadline, and restart evidence
remain required. No push or remote publication is implied.

KB recommendation: fixture failures must be compared against current acceptance
interfaces and separated from production policy defects before changing policy.
