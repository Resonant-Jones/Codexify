# OAuth callback logging: isolated options and operational decisions

This is a preparation document, not an applied ingress change or a managed-edge
proof. No live traffic, provider credentials, tunnel registrations or logging
configuration were changed. Keep real OAuth consent blocked until the selected
path is proven across every actual sink.

## Established source boundary

Previously captured cloudflared 2026.8.3 source shows
`connection/quic_connection.go::runStream` recording `request.Dest` on an error.
`proxy/logger.go::logHTTPRequest` records headers and formats the request URL at
debug level. A callback code/state can therefore enter a log before Guardian's
sanitizer or nginx can affect it. Preserving non-debug operation removes one
exposure path; it does not remove the error-path destination field. Local stderr
scrubbing does not establish protection for management/tail streams.

Source anchors:
- https://github.com/cloudflare/cloudflared/blob/2026.8.3/connection/quic_connection.go
- https://github.com/cloudflare/cloudflared/blob/2026.8.3/proxy/logger.go

The existing repository patches omit request/query/Referer from nginx access
records, suppress request errors on the public virtual server, retain unrelated
startup/internal diagnostics, and sanitize backend callback queries. Their
isolated tests are necessary but do not cover a preceding tunnel or managed edge.
The repository Edge Worker is not established as the actual callback ingress.

## Concrete choices

| Option | Required proof before use | Tradeoff / decision owner |
| --- | --- | --- |
| Verified upstream tunnel version or narrow source redaction before log fan-out | Inventory all URL/header/error sinks; omit query, fragment, userinfo, headers and raw nested errors before every writer; test error and debug paths plus management/tail output in a disposable tunnel | Preferred source-level boundary if available; operator must accept the version/build, update provenance and rollback. A custom binary carries maintenance and supply-chain obligations. No patched binary is supplied or deployed by this task. |
| Dedicated callback ingress that does not traverse the unsafe logger | Prove DNS/TLS/routing, callback session/nonce/origin behavior, no raw URL/body/header recording at each edge/origin sink, and existing callback semantics | Changes topology and possibly registrations. Requires explicit operator selection and a bounded design review; not an implicit workaround. |
| Disable affected request diagnostics at their source, across every sink | Prove suppression before fan-out including management/tail and nested errors; retain safe status/timing/request-ID metrics and process health | Loss of request-error diagnostics must be explicitly accepted. Raising the ordinary local log level or filtering only stdout is insufficient evidence. |

Do not move code/state into a header or POST body as a cosmetic log workaround:
provider support, browser binding, error logging and other sinks would require
separate proof. Do not strip the query before OAuth consumes it. Do not select
HTTP/2 instead of QUIC solely to evade the observed line without auditing that
transport's complete error paths.

## Managed-edge visibility gate

Earlier read-only metadata found no configured Logpush jobs but could not read
retention settings (401/code 10000). That establishes incomplete visibility, not
zero retention. An authorized logging owner must inventory effective HTTP
request logs, Access audit/request logs, WAF/security events, Instant Logs,
Workers observability/tails, tunnel management streams and any third-party sink.
For each, record whether enabled, fields collected, query/header/body handling,
retention and the evidence establishing omission or suppression. No account
privilege escalation is requested or performed here.

## Disposable acceptance matrix

Reuse the readiness sentinel plan with unique synthetic values for `code`,
`state`, unknown/encoded names, `error_description`, Referer, Cookie and
Authorization. Test normal callback refusal, missing nonce, upstream refusal,
disconnect/reset, malformed and oversized input. Capture only disposable logs.
Assert zero raw and encoded sentinels in every sink, including nested exception
strings and management/tail output. Assert the synthetic origin receives the
unchanged query, and retains safe request ID, status, method, path and timing.

Use no real tokens, users, provider egress, live fault injection or production
log export. A missing sink or unavailable inspection permission is a failed
qualification gate. This matrix is a plan; current tests exercise application
sanitizers and prepared config only, not a live tunnel or managed-edge sinks.
