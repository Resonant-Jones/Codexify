# Private Preview inference metering: observe-only foundation

Status: implemented on a review branch; **not deployed or qualified**.
Date: 2026-11-01. Governing boundaries: ADR-003 (request vs message), ADR-005 (account isolation), ADR-069 (release support), ADR-091 (durable completion attempt); `00-current-state.md` remains release truth.

## Design reconciliation

The 2026-08-31 sketch proposed a generic multi-service ledger, balances, rate rules, dashboard, and DeepSeek-only hook. This narrower implementation instead accounts for successful non-stream provider dispatches in the shared chat attempt path. It uses the canonical `ChatThread.user_id` and existing request/attempt identities; no new customer identity, entitlement, pricing authority, payment surface, or runtime admission policy is introduced.

The DeepSeek adapter already retains the full provider response, including the `usage` envelope when provided. `ProviderResponse.raw_payload` also supports usage extraction for other non-stream providers. Local streaming returns plain text without provider usage and therefore records explicit unavailable usage on a successful terminal attempt. A tool-augmented turn can generate two distinct provider attempts, each recorded independently. Cloud-to-local rescue likewise records its successful attempts independently. Provider calls that throw before returning a response are not captured by this first slice, so totals are **not guaranteed to equal provider invoices**.

## Contract

- Table: `inference_usage_events`, additive Alembic revision `d91e4fa6702b` extending the single head `a3115f64dda8`.
- Identity: canonical `users.id` + persisted `chat_threads.user_id` authorization, `request_id` for authored request correlation, and `provider_attempt_id` for one unique provider execution. A replay with the same account/attempt and same payload is a no-op; a conflicting replay is rejected and logged.
- The ledger has no content fields, IP address, prompt, assistant text, or provider raw response. It stores bounded provider/model identifiers, reported token units, a bounded provider response ID, a payload digest, and recorded time.
- `usage_source`: `provider_reported` only if both input and output counts are valid; `partial` when only some counts exist; `unavailable` otherwise. Missing counts remain NULL, never invented zero.
- `estimated_cost_usd` remains NULL unless complete provider usage and a valid versioned rate quote are available. `cost_source` is either `rate_snapshot_estimate` or `unavailable`. Historical quotes are stored on each event; reporting never reprices them.
- Rate quotes are optional operator-provided JSON through `CODEXIFY_METERING_PRICE_SNAPSHOTS_JSON`, keyed by `provider:model`. Example: `{"deepseek:deepseek-chat":{"version":"operator-2026-11-01","input_usd_per_million":"0.50","output_usd_per_million":"2.00","cached_input_usd_per_million":"0.10"}}`. **These numbers are illustrative, not verified provider prices.** Without a configured quote, usage is recorded but cost remains unavailable. Rates are USD per million tokens; cached input requires an explicit cached-input rate. Do not claim provider billing reconciliation from estimated cost.
- Admin read: `GET /api/admin/metering/inference?account_id=<optional>&limit=100`. Uses the existing account-admin session/role guard, including Preview approval, and is mounted only with the existing admin route posture. Returns per-account counts, observed token totals, estimated cost subtotal, and explicit unpriced/missing-data counts. There is no recipient-facing event or dashboard API.
- Persistence errors are logged separately and do not fail chat. This preserves inference behavior, but means metering completeness requires operational inspection. There is no background retry/reconciliation yet.
- Application code does not expose update/delete methods for events; historical records should be treated as append-only. Database-role INSERT-only grants are **not** installed in this slice; a privileged database operator can still modify rows. Do not claim DB-enforced immutability.

## Proof and limits

Focused tests cover provider payload parsing, partial/missing usage, snapshot price arithmetic, idempotency, cross-account thread mismatch, aggregates, and admin route authorization. These tests are code-level evidence only. A PostgreSQL migration upgrade/downgrade rehearsal and a two-account live Private Preview readback remain required before enabling in Preview. Existing deployed Preview remains at its documented schema head until separately authorized migration.

The next enforcement boundary is **account-scoped costly inference admission**, after canonical session/account resolution but before provider dispatch or queue acceptance, using a Guardian-owned account service entitlement. That control must not disable authentication, thread/history reads, exports, or account access. It needs its own authority decision, explicit admin action/audit, fail-safe behavior, and live tests; none is implemented here.

Deferred: billing, balances, provider invoice reconciliation, failed/streaming partial attempt capture, backfill, automatic suspension, rate-limit verdicts, pricing registry administration, UI dashboard, and other billable service families. Release gate remains HOLD.
