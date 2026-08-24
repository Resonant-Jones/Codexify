# Backend startup-failure receipt

## Result

**PASS — Codexify now emits one bounded, secret-safe startup-failure receipt
for an unhandled backend application-lifespan startup exception, then re-raises
the original exception.**

This is observability instrumentation only. It neither retries nor diagnoses
the canonical Tester failure recorded at
`8831fd2f1b77163279b15f4ca5892c8a24f6f75c`; no canonical runtime was started
for this task.

## Scope and boundary

- **Source prerequisite:** `8831fd2f1b77163279b15f4ca5892c8a24f6f75c`
  (`Diagnose tester fresh Chroma startup`), verified in `HEAD` ancestry.
- **Startup prerequisite:** `9f263fa2fdb9fa2efa884d23be22022377e6d6ee`,
  verified in `HEAD` ancestry.
- **Branch:** `codex/diagnose-tester-fresh-chroma-failure`.
- **Owner:** `guardian/guardian_api.py`.
- **Instrumentation point:** `app_lifespan`, which wraps the existing
  `_app_lifespan_body` context manager at its `__aenter__` boundary.

`guardian/main.py` is a deprecated, separate FastAPI application and is not
the supported backend entrypoint. `backend/scripts/docker/run_backend.py`
executes Uvicorn with `guardian.guardian_api:app`, whose `FastAPI(lifespan=...)`
owner is therefore the correct outermost application-startup seam.

The wrapper catches only an exception raised while the existing lifespan body
enters. It emits one receipt and re-raises the same exception object. Exceptions
from the yielded runtime/shutdown path continue through the original context
manager semantics without a startup receipt.

## Receipt contract

Each receipt is one JSON object on the backend stderr/container-log stream,
preceded by:

```text
CODEXIFY_STARTUP_FAILURE_RECEIPT
```

The stable values are:

| Field | Value / bound |
| --- | --- |
| `schema_version` | `codexify.backend-startup-failure.v1` |
| `event` | `backend_startup_failure` |
| `startup_phase` | `application_lifespan` |
| `message_redacted` | at most 1,024 UTF-8 bytes |
| `message_sha256` | SHA-256 of the pre-redaction UTF-8 exception message |
| `exception_type` | fully qualified `<module>.<class>` identity |
| `exception_module` | bounded module identity |
| `exception_chain` | cause first, otherwise context; at most 8 entries |
| `frames` | code path/function/line only; at most 16 frames closest to the failure |
| entire serialized JSON object | at most 16 KiB |

Every variable string is bounded. If a field, chain, frame list, or defensive
serialization reduction truncates evidence, the receipt includes
`"truncated": true`. No source text, frame locals, globals, arguments, or raw
traceback text is captured.

The writer uses stderr directly only after this dedicated sanitizer has built
the receipt; it does not weaken or bypass the process-wide general logging
redaction for ordinary log records. This ensures the structured receipt remains
discoverable in `docker logs` without permitting arbitrary dynamic log content.

## Secret safety

The receipt hashes the original message for correlation but never emits that
message directly. Its conservative message sanitizer redacts representative:

- `Authorization: Bearer` and free-text bearer values;
- JWT-shaped tokens and `sk-...` API keys;
- `password`, `passwd`, `secret`, `token`, `api_key`, and `apikey`
  assignments;
- `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, and `DATABASE_URL` assignments; and
- URI userinfo, including Postgres and HTTP credential-bearing URLs.

The receipt deliberately excludes environment dumps, provider/model selection,
API keys, database or Redis URLs, user/thread/message identifiers, request
payloads, Chroma content, and any durable receipt database/queue/file.

## Failure semantics and automated proof

`tests/core/test_startup_failure_receipt.py` provides 14 focused tests:

1. Redaction fixtures cover bearer, JWT, `sk-`, API-key, password, Postgres
   URL, HTTP URL, and OpenAI/DeepSeek environment-assignment shapes. Each
   verifies the synthetic secret is absent from rendered receipt output while
   `message_sha256` remains the original-message fingerprint.
2. A nested synthetic exception verifies schema, parseable UTC timestamp,
   fully qualified outer and causal-chain identity, bounded redacted messages,
   and frames containing only path/function/line metadata.
3. A synthetic lifespan-entry failure emits exactly one prefixed JSON receipt
   and re-raises the original `SyntheticStartupError`.
4. A successful lifespan path produces no receipt and preserves normal startup,
   runtime, and shutdown order.
5. A forced receipt-emitter failure produces only the fixed
   `CODEXIFY_STARTUP_FAILURE_RECEIPT_EMISSION_FAILED` fallback and still
   re-raises the original startup exception.
6. An application-level test replaces only the private lifespan body and proves
   the real `guardian.guardian_api.app_lifespan` wrapper emits one receipt.

No test starts Docker, the canonical backend, a worker, or an external model.

## Runtime and authority boundaries

- No canonical backend retry occurred.
- `worker-chat` and Watchdog were not started.
- Canonical partial Chroma and both preservation generations were untouched.
- No chat, model, DeepSeek, cloud, or Watchdog execution occurred.
- No Postgres, Redis, configuration, dependency, provider-routing, or Chroma
  behavior changed.

## ADR impact

**No new ADR — diagnostic log evidence only; existing startup, persistence, and
provider authority remain preserved.** The work aligns with ADR-067's governed
derived-store posture and ADR-074's provider/model authority boundary without
changing either contract.

## Validation

- `.venv/bin/python -m pytest -v tests/core/test_startup_failure_receipt.py
  tests/core/test_supported_profile_provider.py
  tests/core/test_supported_profile_startup.py` — **28 passed**.
- The new receipt module and its focused test pass Ruff and isort checks; the
  receipt module, `guardian/guardian_api.py`, and focused test compile with
  `py_compile`.
- `python3 scripts/validate_docs.py` and `git diff --check` pass.
- Full Ruff/isort checks of the delegated owner remain blocked by its
  pre-existing baseline: the prerequisite revision already had 78 Ruff
  findings and an isort import-order diff in `guardian/guardian_api.py`. This
  narrow observability slice adds no new owner finding and does not broaden
  into unrelated cleanup.

These checks prove instrumentation behavior only, not backend health or a
repair for the prior canonical failure.

## Deferred next slice

Perform exactly one canonical Tester backend startup attempt with the structured
startup-failure receipt enabled; if startup fails, capture and classify that
receipt without retrying, and if startup succeeds, stop after backend health
readiness without starting `worker-chat` or performing inference.
