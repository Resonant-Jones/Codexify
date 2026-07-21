# Whoosh'd Control-Plane v1

This is the Codexify-side interpretation of the bounded
`whooshd.control.v1` contract. It is implementation and test documentation,
not proof that a live Whoosh'd daemon has been restarted or that external
collectors sanitize records.

## Boundary

Whoosh'd-owned responses advertise
`X-Whooshd-Contract-Version: whooshd.control.v1`. Codexify parses the canonical
body only when that header is present and exactly supported. The parser reads
machine fields only: `code`, `http_status`, `retryable`, bounded
`retry_after_seconds`, `request_id`, and `category`. Unknown optional v1 fields
are ignored. A missing response header remains the legacy unversioned path.
An explicit mismatched or unsupported-major response header is a bounded
contract failure; Codexify does not route it through legacy fallback.

Codexify sends the same contract header on local inference requests. It does
not forward or classify prompts, generated text, tool values, media, headers,
or raw provider bodies as contract diagnostics.

## Cross-repository error matrix

| Condition / code | HTTP | Retryable | Retry-After | Codexify mapping | Whoosh'd legacy path |
|---|---:|:---:|---:|---|---|
| `invalid_request` | 400 | no | — | request error | unversioned request failure |
| `unsupported_field` | 400 | no | — | request error | unversioned request failure |
| `unsupported_capability` | 422 | no | — | request error | unversioned request failure |
| `contract_version_unsupported` | 400 | no | — | request error | explicit unsupported contract |
| `model_not_found` | 404 | no | — | local model unavailable | unversioned model/HTTP failure |
| `model_unavailable` | 503 | yes | — | transport error | unversioned runtime failure |
| `model_warming` | 425 | yes | 2 seconds bounded | provider HTTP error | unversioned warming/HTTP failure |
| `model_load_failed` | 500 | no | — | provider HTTP error | unversioned internal failure |
| `runtime_unavailable` | 503 | yes | — | transport error | unversioned transport failure |
| `runtime_degraded` | 503 | yes | — | provider HTTP error | unversioned runtime failure |
| `runner_overloaded` | 429 | yes | 2 seconds bounded | provider HTTP error | existing overload handling |
| `queue_full` | 429 | yes | 2 seconds bounded | provider HTTP error | existing overload handling |
| `timeout` | 504 | yes | — | provider timeout | existing timeout handling |
| `cancelled` | 409 | no | — | provider HTTP error | existing cancellation handling |
| `context_overflow` | 422 | no | — | request error | existing admission rejection |
| `upstream_unavailable` | 503 | yes | — | transport error | existing transport failure |
| `upstream_timeout` | 504 | yes | — | provider timeout | existing timeout failure |
| `upstream_protocol_error` | 502 | no | — | provider HTTP error | existing upstream failure |
| `stream_interrupted` | 502 | no | — | provider HTTP error | existing stream failure |
| `malformed_upstream_response` | 502 | no | — | provider HTTP error | existing parse failure |
| `internal_error` | 500 | no | — | provider HTTP error | existing internal failure |

`Retry-After` is available in both the body and HTTP header for warming,
overload, and queue-full errors. Codexify does not automatically retry from
this contract; existing orchestration policy remains authoritative.

On the incoming request side, Whoosh'd preserves missing-header compatibility,
accepts exact v1, and rejects explicit non-v1 values with
`contract_version_unsupported` and HTTP 400. The response still advertises v1;
only a bounded safe version identifier is retained.

## Streaming terminal rule

When Whoosh'd reports a stream failure after visible output, the canonical
error is an SSE error event and a successful `[DONE]` event is not fabricated.
Codexify preserves the established incomplete-stream classification and does
not fall back after visible output. Successful streams retain their existing
terminal behavior.

## Proof boundary

Focused parser and adapter tests prove header/body parsing, code-only
classification, request-ID retention, unknown optional-field tolerance, and
legacy behavior. Current supported-profile and live daemon behavior remain
separate proof surfaces and are not widened by this document.
