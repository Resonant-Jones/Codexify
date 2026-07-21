# Codexify Content and Credential Logging Contract

Status: implemented on `main` by CWC-004. This is an operational logging
contract; it does not change provider selection, fallback, event payloads,
transcript persistence, attachment persistence, or control-metadata handling.

## Boundary

Codexify operational logs may contain bounded metadata only:

- task, request, run, thread, turn, message, and event IDs;
- provider, model, queue, status/status code, endpoint kind, and transport
  classification;
- failure class, exception type, timeout class, duration, and bounded counts;
- content-presence booleans and character/item/byte counts;
- endpoint identity with URL userinfo, query, and fragment removed.

They must not contain user prompts, assistant output, retrieved or attachment
contents, tool arguments or output bodies, raw provider request/response
bodies, authorization headers, API keys, bearer tokens, cookies, session
secrets, or credential-bearing paths.

`guardian/utils/log_safety.py` installs a process-wide `LogRecord` boundary from
`guardian/__init__.py`. It sanitizes records before console, file, test, or
third-party handlers see them. `ScrubFormatter` remains a last-mile defense
for rendered output and continues the existing credential-path scrub.

Exception records retain the exception type and a bounded failure class, such
as `timeout`, `connection`, `http`, `parse`, `authorization`, `validation`, or
`runtime`. Exception messages, tracebacks, response bodies, URLs with query
secrets, and interpolated argument values are not emitted.

## Discovery inventory and classification

| Surface | Relevant findings | Classification after CWC-004 |
| --- | --- | --- |
| `guardian/workers/chat_worker.py` | Worker lifecycle, task/turn/message correlation, persistence and audio diagnostics | IDs, provider/model, status, counts, booleans, and failure classes are safe metadata. The former `raw_output` log is now output length/presence only. |
| `guardian/core/chat_completion_service.py` | Completion diagnostics, retrieval summaries, prompt/context assembly failures, attachment inference failures | Retrieval is summarized by bounded counts; assistant length is metadata; exception interpolation is sanitized. No prompt or retrieved text is logged. |
| `guardian/core/ai_router.py` | Local/Groq/OpenAI-compatible/DeepSeek/Alibaba/MiniMax request and HTTP failure paths | Request logs contain provider/model/endpoint identity, status, transport, failure kind, and attempt count. Provider detail/body strings remain runtime error data but do not reach logs. |
| `guardian/providers/local_ollama.py` and provider clients | Invalid streamed provider frames and response parsing | Raw frame logging was replaced with frame length/presence metadata. Provider response text is returned to the caller but never logged. |
| `guardian/connectors/github.py`, `guardian/routes/connectors.py`, and Drive auth | Connector identity, document counts, sync failures, OAuth/service-account paths | Owner/repo and counts are bounded metadata. Document bodies, sync results, tokens, and credential paths are not logged. |
| `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/queue/turn_lock.py`, and queued workers | Redis/dequeue failures, malformed payloads, retry/terminal visibility | Task IDs, queue/event types, retry counts, and failure classes remain. Payloads, exception messages, and content-bearing fields are sanitized. |
| `guardian/command_bus/loopback_http_adapter.py`, `guardian/runtime/tools/*`, and WebSocket RPC | Policy warnings, scheduler failures, command/tool execution, RPC failures | Decision/status metadata remains; headers, body, query, tool arguments, results, and exception bodies do not reach logs. |
| HTTP and exception logging | `guardian/server/app.py` console/file handlers and all installed handlers | Records are sanitized before handlers; rendered output receives a second scrub. `exc_info` is reduced to exception type/failure class. |

## Classification vocabulary

- **Safe metadata:** stable IDs, bounded enumerations, status codes, timing,
  counts, booleans, provider/model identifiers, and sanitized endpoint identity.
- **Content-bearing:** prompts, generated text, document/retrieval text,
  attachment data, raw response/request bodies, tool args/results, and free-form
  payloads. These are summarized or removed.
- **Credential-bearing:** authorization headers, bearer/API/session material,
  cookies, secrets, and credential file paths. These are removed or represented
  only by a presence boolean.
- **Potentially unsafe through exception interpolation:** any `exc`, `err`,
  `detail`, `response`, `body`, `payload`, or validation error. These are
  represented by type/classification/count metadata; log level does not exempt
  debug records.
- **Intentionally security-redacted:** the `LogRecord` boundary, the
  `ScrubFormatter`, provider error extraction used for runtime responses, and
  source-level bounded log statements.

## Proof and limits

`tests/security/test_content_credential_logging.py` uses sentinel values to
prove absence of assistant text, user prompts, provider bodies, credentials and
authorization material, tool args/output, exception messages, and terminal
output while preserving task/request/turn correlation and failure metadata.

This is code-path and captured-log proof for the exercised Codexify Python
process. It is not proof about historical logs, external reverse proxies,
container runtimes, log collectors, Whoosh'd internals, or uninspected future
processes. No release claim is widened by this contract.
