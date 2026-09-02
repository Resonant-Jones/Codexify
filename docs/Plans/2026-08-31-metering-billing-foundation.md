# Metering, Rate-Limiting, and Billing Foundation — Design Sketch

> **Status:** Design (not yet implemented). Pre-implementation baseline.
> **Goal:** Record billable service consumption per user across every Codexify
> service (inference first; TTS, image, music, coding sandbox, storage,
> embedding, web search later); expose an admin dashboard; enable
> observe-only rate limiting in Phase 1 and enforcement in a later phase;
> keep payments mocked but the accounting real.
> **Grounding:** every seam below was verified against the working tree on
> 2026-08-31 (branch `main`, ahead 0 / behind 0). Verified locations are
> cited inline. **No runtime, schema, ADR, or release-truth file has been
> modified by this document.**
> **Ratio boundary:** this document is a design sketch only. No code,
> migrations, contracts, ADRs, or `docs/architecture/00-current-state.md`
> changes are authorized by authoring this doc.

---

## 0. Why this doc, now

Codexify is multi-tenant, exposed over Tailscale, and has real users
registering with email-shaped handles that are not validated. The deployed
instance is configured with DeepSeek as the inference provider and a small
prepaid balance ($40). Today the operator has zero visibility into:

- who is logged in and when,
- what they are doing,
- which Codexify-owned services they are consuming,
- how much inference has been spent, by whom, on what models,
- whether a user is at or approaching their prepaid balance.

The fix is not "add a dashboard" — it is a **service-agnostic, append-only
usage ledger** with snapshot-priced cost, an aggregation API that powers a
dashboard, and a deliberately phased rate-limiter that begins as
**observe-only** before it ever rejects a request. Payments stay mocked
through Phase 1 — but the accounting surface is real, durable, and
auditable.

## 1. What exists today (honest inventory, verified 2026-08-31)

| Piece | Location | Status |
|---|---|---|
| Canonical `User` model | `guardian/db/models.py:127` | Active; owns `id`, `username`, `email`, `password_hash`, `role` (admin/guest). |
| `AuthenticatedPrincipal` | `guardian/db/models.py:3698` | Active; subject→account mapping. |
| `InferenceProvider` control-plane model | `guardian/db/models.py:2252` | Active; `provider_id`, `enabled`, `priority`, `default_model_id`, `capabilities`, `provider_metadata`. |
| `InferenceProviderRuntime` health model | `guardian/db/models.py:2305` | Active; per-provider health/latency/cooldown. |
| `account_observability/` package | `guardian/account_observability/` | Active; **presence, invites, retention, heartbeat, attribution**. Specifically: "Is this account active?", "When did they register?", "Did they come through an invite?". |
| Auth routes (register / login / logout) | `guardian/routes/auth.py:161,226,270` | Active; session-backed; invite attribution at register. |
| Existing IP-based rate limiter | `guardian/server/app.py:75-99` (`slowapi`) | Active; **IP-keyed**, NOT user-keyed. Returns 429 with no per-user accounting. |
| Provider call site (chat completion) | `guardian/core/chat_completion_service.py`, routed through `guardian/core/ai_router.py` | Active. **No hook today to capture token usage per request.** |
| DeepSeek adapter | `guardian/providers/deepseek_adapter.py` | Active; returns completion but **does not record usage or cost**. |
| Per-service adapter registry | `guardian/providers/` (deepseek, openai, gemini, groq, whooshd, ...) | Active; heterogeneous shape, no shared contract for usage. |

### Two findings that shape the design

1. **No service today records consumption.** A grep for `token_usage`,
   `prompt_tokens`, `total_cost`, `cents_per`, etc. returns zero hits in
   `guardian/providers/`. The DeepSeek adapter does not return
   `usage` blocks; the chat completion service does not persist them; the
   rate limiter is keyed by IP, not user. This is the gap the ledger
   fills.
2. **The `account_observability/` boundary is already defined and
   distinct.** Per its own contract, it owns presence, account activity,
   acquisition, and privacy-bounded analytics — explicitly NOT per-action
   behavioral/event telemetry. Putting meter events there would muddy
   that boundary. **A new `guardian/metering/` package is the right home.**

## 2. Design goals

1. **Service-agnostic.** One ledger, one pricing snapshot, one dashboard.
   Add TTS / image / music / coding sandbox / storage by adding a row
   in `service_catalog` and a per-service unit validator — not a new
   table.
2. **Snapshot-priced at consumption.** Cost is computed from the
   `pricing_version` that was live at the moment the request completed
   and is **persisted with the event**. Never recomputed from today's
   prices when reporting historical spend.
3. **Append-only ledger.** No UPDATE / DELETE on `service_usage_events`.
   Corrections happen via compensating events (negative `usage_units`,
   `metadata={"correction_of": "<event_id>"}`). Auditable by construction.
4. **Phase-1 enforcement is zero.** Phase 1 records consumption and
   powers the dashboard. The rate-limit *evaluator* runs and logs
   "would_block" verdicts; nothing is rejected. Promotion to
   enforcement is a separate gate, with the full ledger behind it so
   the operator can verify the limit is sane before flipping it.
5. **Mocked billing, real accounting.** Phase 1 has no payment
   processor. The balance model is a `user_balance` table seeded by an
   operator script. The dashboard reads it. When a real PSP (Stripe /
   Paddle / LemonSqueezy) is chosen, only the credit/debit adapter
   changes — the ledger does not.
6. **Privacy-bounded.** No prompt text, no completion text, no message
   bodies, no file contents, no IP addresses in the ledger. `user_id`
   is the only PII field. The dashboard aggregates; the event API
   never returns row-level events for non-admins.
7. **Attaches to existing `User.id`**, not a new customer-identity
   database. The User model is the canonical account boundary.

## 3. The boundary that matters: `metering/` vs `account_observability/` vs `billing/`

| Subsystem | Question it answers | Owns |
|---|---|---|
| `account_observability/` | "Is this account active? When did they register? Did they come through an invite?" | Presence sessions, invites, attribution, retention cleanup. **Privacy-bounded analytics for *account-level* activity.** |
| **`metering/` (new)** | "What Codexify-owned resource did this account consume? How many billable units? What did those units cost *us*?" | **Service-agnostic usage ledger**, snapshot pricing, per-service unit validators, aggregation API, observe-only rate-limit evaluator. |
| `billing/` (future, deferred) | "What do we charge them? Did they pay? What are they entitled to consume?" | Payment processor integration (mocked in Phase 1), entitlement/plan model, invoice generation. Out of scope for this design. |

**Metering is NOT billing.** This is the firewall that matters. The ledger
records *what we spent serving the user*. Pricing/margin/billing is a
separate concern that reads the ledger but is not coupled to it.

## 4. Component sketch

```
guardian/metering/
├── __init__.py            # public API: record_usage(...), get_registry()
├── contracts.py           # ServiceType, ServiceUsageEvent, PricingRule,
│                          # UsageUnitSchema (pydantic, extra="forbid")
├── catalog.py             # ServiceCatalog — registry of known services and
│                          #   their unit schemas (validation, not pricing)
├── pricing.py             # PricingRule, PricingTable, snapshot_cost(...)
│                          #   + PricingVersion (immutable per release)
├── ledger.py              # ServiceUsageEventStore — append-only writer
│                          #   and read APIs (admin only)
├── evaluator.py           # RateLimitEvaluator (Phase 1: observe-only)
├── aggregations.py        # user_totals, service_totals, time_buckets
├── tokens.py              # canonical enums (ServiceType, RateLimitDim, etc.)
└── tests/
    ├── test_contracts.py
    ├── test_catalog.py
    ├── test_pricing.py
    ├── test_ledger.py
    ├── test_evaluator.py
    └── test_aggregations.py

guardian/routes/metering_admin.py   # admin-only JSON API
guardian/migrations/versions/<rev>_add_metering_foundation.py
frontend/src/metering/              # React dashboard (read-only, admin-gated)
```

### 4.1 `contracts.py` — canonical types

```python
class ServiceType(str, Enum):
    INFERENCE = "inference"
    TTS = "tts"
    IMAGE_GENERATION = "image_generation"
    MUSIC_GENERATION = "music_generation"
    CODING_SANDBOX = "coding_sandbox"
    CLOUD_STORAGE = "cloud_storage"
    EMBEDDING = "embedding"
    WEB_SEARCH = "web_search"


class UsageUnitSchema(BaseModel):
    """What 'one unit' means for a given service_type.

    Validates the ``usage_units`` payload BEFORE it is persisted.
    Reject arbitrary JSONB — the schema goblin waits there.
    """
    service_type: ServiceType
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...] = ()
    model_config = ConfigDict(extra="forbid")


class ServiceUsageEvent(BaseModel):
    """The append-only ledger row.

    Pydantic for API surface; the SQL row mirrors this exactly.
    """
    id: int                      # bigserial
    user_id: str                 # FK users.id (existing boundary)
    service_type: ServiceType
    provider_id: str | None      # inference_providers.provider_id when applicable
    product_id: str | None       # e.g. "deepseek-chat", "elevenlabs-rachel"
    request_id: str | None       # idempotency key from caller (HTTP X-Request-ID)
    usage_units: dict            # validated by UsageUnitSchema
    estimated_cost_usd: Decimal  # Decimal(12, 6), snapshot at completion
    pricing_version_id: str      # FK pricing_versions.id (immutable)
    started_at: datetime
    completed_at: datetime
    status: Literal["ok", "error", "throttled", "rejected"]
    metadata: dict = {}          # bounded: provider_request_id, error_code, etc.
    recorded_at: datetime        # server-side, when row was written
```

**`metadata` discipline:** allowed keys are bounded by the catalog
(`{"provider_request_id", "error_code", "cache_hit", "streamed", ...}`).
No free-form blobs. Validator rejects unknown keys.

### 4.2 `catalog.py` — service + unit schemas

```python
INFERENCE_UNITS = UsageUnitSchema(
    service_type=ServiceType.INFERENCE,
    required_keys=("input_tokens", "output_tokens"),
    optional_keys=("cached_input_tokens", "reasoning_tokens"),
)
TTS_UNITS = UsageUnitSchema(
    service_type=ServiceType.TTS,
    required_keys=("characters",),
    optional_keys=("ssml_overhead_chars",),
)
IMAGE_UNITS = UsageUnitSchema(
    service_type=ServiceType.IMAGE_GENERATION,
    required_keys=("images",),
    optional_keys=("steps", "resolution"),
)
MUSIC_UNITS = UsageUnitSchema(
    service_type=ServiceType.MUSIC_GENERATION,
    required_keys=("seconds",),
)
CODING_SANDBOX_UNITS = UsageUnitSchema(
    service_type=ServiceType.CODING_SANDBOX,
    required_keys=("seconds",),
    optional_keys=("vcpu_seconds", "memory_mb_seconds"),
)
CLOUD_STORAGE_UNITS = UsageUnitSchema(
    service_type=ServiceType.CLOUD_STORAGE,
    required_keys=("bytes_stored_seconds",),
    optional_keys=("egress_bytes",),
)
EMBEDDING_UNITS = UsageUnitSchema(
    service_type=ServiceType.EMBEDDING,
    required_keys=("input_tokens",),
)
WEB_SEARCH_UNITS = UsageUnitSchema(
    service_type=ServiceType.WEB_SEARCH,
    required_keys=("queries",),
)
```

**Adding a service =** one row in `ServiceCatalog` (DB-backed) + one
`UsageUnitSchema` constant + zero new tables. This is the point of the
generic shape.

### 4.3 `pricing.py` — snapshot pricing

```python
class PricingRule(BaseModel):
    """One (service_type, provider_id, product_id) pricing recipe.

    PricingVersion freezes a set of PricingRule rows under a stable id.
    """
    service_type: ServiceType
    provider_id: str | None
    product_id: str | None       # None = applies to any product of provider
    unit_costs_usd: dict[str, Decimal]   # {"input_tokens": "0.00027", ...}
    fixed_cost_usd: Decimal = Decimal("0")


class PricingVersion(BaseModel):
    pricing_version_id: str      # e.g. "deepseek-v4-2026-08-15"
    effective_at: datetime
    rules: list[PricingRule]
    superseded_by: str | None = None
```

**Snapshot rule:** at ledger-write time, the active `PricingVersion` is
read, the matching rule is selected, and `estimated_cost_usd` is
computed and persisted. The `pricing_version_id` lives on the row
forever. Aggregation reads `estimated_cost_usd` directly — it never
recomputes historical cost against today's prices. If you change prices
tomorrow, last week's spend does not move.

### 4.4 `ledger.py` — append-only writer

```python
def record_usage(
    *,
    user_id: str,
    service_type: ServiceType,
    usage_units: dict,
    provider_id: str | None = None,
    product_id: str | None = None,
    request_id: str | None = None,
    started_at: datetime,
    completed_at: datetime,
    status: Literal["ok", "error", "throttled", "rejected"] = "ok",
    metadata: dict | None = None,
    session: Session,            # caller's session; writer does NOT open its own
) -> ServiceUsageEvent:
    """Validate → snapshot price → insert. Never UPDATE. Never DELETE.

    Raises:
        UsageUnitSchemaError: usage_units violate the service contract.
        PricingRuleMissingError: no PricingRule matches service_type/provider/product.
    """
```

**Concurrency / idempotency:** the writer uses an advisory unique index
on `(user_id, service_type, request_id)` where `request_id` is supplied.
Re-submits are upserted to the same row (still effectively append-only —
the second submission replaces via `ON CONFLICT DO NOTHING` and returns
the existing id). This is the only "duplicate-write" edge case and it
only collapses rows that the caller already identified as the same
request.

### 4.5 `evaluator.py` — observe-only rate-limit evaluator (Phase 1)

```python
@dataclass(frozen=True)
class RateLimitVerdict:
    dimension: RateLimitDimension     # SPEND_USD, TOKENS, REQUESTS, CONCURRENCY
    period: RateLimitPeriod           # ROLLING_1H, DAILY, MONTHLY
    current_value: Decimal
    limit_value: Decimal
    would_block: bool                 # Phase 1: always False in production
    evaluated_at: datetime
    matched_rule_id: str | None       # which RateLimitRule fired


class RateLimitEvaluator:
    def evaluate(
        self,
        *,
        user_id: str,
        service_type: ServiceType,
        projected_cost_usd: Decimal = Decimal("0"),
    ) -> RateLimitVerdict:
        """Phase 1: compute and log 'would_block' verdicts. Never raise."""
```

**Phase-1 contract:** the evaluator reads the ledger, computes the
would-be-block verdict, attaches it to the response as a header
(`X-RateLimit-WouldBlock: spend_usd.rolling_1h`), and always returns
`would_block=False` to the calling route. Promotion to enforcement is a
later gate (§6.3).

### 4.6 `aggregations.py` — what the dashboard reads

```python
def user_totals(
    *,
    user_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    session: Session,
) -> dict[ServiceType, dict[str, Decimal]]:
    """Returns {service_type: {"usage": ..., "cost_usd": ..., "events": ...}}."""

def service_totals(
    *,
    service_type: ServiceType,
    since: datetime | None = None,
    until: datetime | None = None,
    session: Session,
) -> dict[str, dict[str, Decimal]]:
    """Returns {user_id: {"usage": ..., "cost_usd": ..., "events": ...}}."""

def time_buckets(
    *,
    bucket: Literal["hour", "day"],
    since: datetime,
    until: datetime,
    service_type: ServiceType | None = None,
    session: Session,
) -> list[dict]:
    """Returns time-series points for the dashboard's burn-down chart."""
```

All aggregation functions read `estimated_cost_usd` and `usage_units`
directly from the ledger — no recomputation, no double-bookkeeping.

## 5. Database schema (sketch — NOT yet migration-authored)

```sql
-- Append-only ledger. No UPDATE permission in the role grants.
CREATE TABLE service_usage_events (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    service_type        TEXT NOT NULL,
    provider_id         TEXT REFERENCES inference_providers(provider_id)
                            ON DELETE RESTRICT,
    product_id          TEXT,
    request_id          TEXT,                          -- idempotency
    usage_units         JSONB NOT NULL,                -- validated by catalog
    estimated_cost_usd  NUMERIC(12, 6) NOT NULL,
    pricing_version_id  TEXT NOT NULL REFERENCES pricing_versions(id),
    started_at          TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ NOT NULL,
    status              TEXT NOT NULL
        CHECK (status IN ('ok','error','throttled','rejected')),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (completed_at >= started_at),
    CHECK (estimated_cost_usd >= 0)
);

-- Idempotency: same caller request_id for same user/service collapses.
CREATE UNIQUE INDEX uq_service_usage_events_idempotent
    ON service_usage_events (user_id, service_type, request_id)
    WHERE request_id IS NOT NULL;

CREATE INDEX ix_service_usage_events_user_completed
    ON service_usage_events (user_id, completed_at DESC);
CREATE INDEX ix_service_usage_events_service_completed
    ON service_usage_events (service_type, completed_at DESC);
CREATE INDEX ix_service_usage_events_pricing_version
    ON service_usage_events (pricing_version_id);

-- Snapshot pricing — never UPDATE a row, only INSERT a new version.
CREATE TABLE pricing_versions (
    id              TEXT PRIMARY KEY,                  -- e.g. "deepseek-v4-2026-08-15"
    effective_at    TIMESTAMPTZ NOT NULL,
    superseded_by   TEXT REFERENCES pricing_versions(id),
    notes           TEXT
);

CREATE TABLE pricing_rules (
    pricing_version_id  TEXT NOT NULL REFERENCES pricing_versions(id),
    rule_id             TEXT NOT NULL,
    service_type        TEXT NOT NULL,
    provider_id         TEXT,
    product_id          TEXT,
    unit_costs_usd      JSONB NOT NULL,                -- {"input_tokens":"0.00027"}
    fixed_cost_usd      NUMERIC(12, 6) NOT NULL DEFAULT 0,
    PRIMARY KEY (pricing_version_id, rule_id)
);

-- Mocked balance — replaced by PSP integration in a later phase.
CREATE TABLE user_balances (
    user_id          TEXT PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    balance_usd      NUMERIC(12, 6) NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'USD',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (balance_usd >= 0)                          -- never go negative in mock
);

CREATE TABLE rate_limit_rules (
    rule_id          TEXT PRIMARY KEY,
    dimension        TEXT NOT NULL                    -- spend_usd, tokens, requests
        CHECK (dimension IN ('spend_usd','tokens','requests','concurrency')),
    service_type     TEXT,                            -- NULL = applies to all services
    period           TEXT                             -- rolling_1h, daily, monthly
        CHECK (period IN ('rolling_1h','daily','monthly')),
    limit_value      NUMERIC(18, 6) NOT NULL,
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,   -- Phase 1: never enforced
    notes            TEXT
);

-- Append-only ledger of "would_block" verdicts (Phase 1 only).
CREATE TABLE rate_limit_verdicts (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    service_type    TEXT NOT NULL,
    dimension       TEXT NOT NULL,
    period          TEXT NOT NULL,
    current_value   NUMERIC(18, 6) NOT NULL,
    limit_value     NUMERIC(18, 6) NOT NULL,
    would_block     BOOLEAN NOT NULL,
    matched_rule_id TEXT,
    evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_rate_limit_verdicts_user_time
    ON rate_limit_verdicts (user_id, evaluated_at DESC);
```

**RBAC reminder:** the application role granted to the runtime should be
`INSERT`-only on `service_usage_events` and `rate_limit_verdicts` (and
`SELECT` for the admin API path). The DB must enforce what the code says.

## 6. Phase plan

### Phase 1 — observe-only foundation (next)

- **Scope:** ledger + snapshot pricing + admin JSON API + dashboard
  read-only view. **Zero enforcement.** Evaluator runs, logs
  `would_block`, never blocks.
- **Producer integration:** wire ONE call site first — the
  DeepSeek-backed chat completion path through
  `guardian/core/chat_completion_service.py` → emit a
  `ServiceUsageEvent` on completion (success or error).
- **Pricing data:** seed one `pricing_version` (`deepseek-v1-2026-08-31`)
  with DeepSeek's published rates and the current $40 prepaid balance
  distributed across the seeded test users via an operator script
  (`scripts/metering/seed_balances.py`).
- **Dashboard:** admin-gated React page at `/admin/metering` reading the
  aggregation API. Three views: per-user burn-down, per-service totals,
  top-N consumers.
- **Acceptance:** the operator can stare at the dashboard and answer
  "who spent what, when, on which model" while the $40 burns down.
- **Out of scope for Phase 1:** enforcement, TTS/image/music/coding/
  storage/embedding integration, payments, plans/entitlements, refunds.

### Phase 2 — service expansion (deferred)

- Add TTS / image / music / coding sandbox / cloud storage / embedding
  / web_search adapters to emit `ServiceUsageEvent`.
- Each addition = (a) one `UsageUnitSchema` constant, (b) one
  `pricing_rule` row in a new `pricing_version`, (c) one integration
  test that fakes the adapter and asserts a recorded event.

### Phase 3 — enforcement gate (deferred, gated)

- Promotion criteria: Phase 1 has run for ≥7 days; ≥1 user has
  produced ≥100 events; the operator has reviewed the `would_block`
  verdicts and confirms the limits are sane.
- Implementation: flip the evaluator from observe-only to enforce; on
  `would_block=True`, the route returns 429 with a
  `Retry-After` header computed from the next-period reset.
- This is a separate ADR + Campaign — not in scope of this doc.

### Phase 4 — billing integration (deferred)

- Replace `user_balances` mock with a real PSP (Stripe / Paddle /
  LemonSqueezy).
- Add `billing/` package: plans, entitlements, invoice generation.
- The ledger does not change.

## 7. Where this plugs in (verified call sites)

| Hook | File | What changes |
|---|---|---|
| Chat completion (DeepSeek path) | `guardian/core/chat_completion_service.py` + `guardian/providers/deepseek_adapter.py` | Adapter returns `usage` (request it explicitly); service emits `record_usage(...)` on completion. |
| Inference provider routing | `guardian/core/ai_router.py` | Hook evaluator before dispatch — emits `rate_limit_verdicts` (Phase 1) but never blocks. |
| Provider registry | `guardian/providers/registry.py` | Read `provider_id` for `service_usage_events.provider_id`. Existing `InferenceProvider` model is reused — no new table. |
| Auth boundary | `guardian/routes/auth.py` | Unchanged in Phase 1. The existing `User.id` is the ledger's `user_id`. |
| Frontend (admin dashboard) | `frontend/src/metering/` (new) | Admin-gated React page; calls `GET /api/admin/metering/...`. |
| Admin route | `guardian/routes/metering_admin.py` (new) | JSON API gated by existing admin role check (`User.role == 'admin'` per `users_role_check`). |

## 8. Risks & tradeoffs

1. **Pricing rule drift.** If the operator hand-edits
   `pricing_rules` without bumping `pricing_version_id`, future events
   silently mis-price. Mitigation: the writer only reads from the
   currently-active `pricing_version`; a `pricing_version_bump` operator
   command is the only sanctioned mutation path. Lint/migration refuses
   to add rules to an active version.
2. **Estimating cost before the call.** Streaming responses don't know
   output token count upfront. Strategy: emit a `status="throttled"`
   placeholder at request start with `estimated_cost_usd=0`, then emit
   the real row at completion. Idempotency key collapses them. Phase 1
   tolerates the simpler "emit only on completion" approach; Phase 2
   adds the streaming case.
3. **Multi-currency.** `user_balances.currency` exists but Phase 1 is
   USD-only. PSP integration in Phase 4 introduces real FX.
4. **Provider that returns no `usage` block.** Some legacy providers
   (or a local whoosh'd model) don't return token counts. The
   catalog must support a `billing_mode="derived"` rule (charge per
   request, per second, per byte) so we don't drop the event. Phase 1
   supports `per_request` and `per_second`; Phase 2 adds the rest.
5. **Append-only discipline.** "No UPDATE" is a contract we have to
   defend. Mitigation: the SQLAlchemy mapper for `ServiceUsageEvent`
   exposes no UPDATE method; the DB role grant removes UPDATE
   permission; aggregation functions read `estimated_cost_usd` directly
   so no "fix-up" job is ever needed.
6. **Idempotency collisions.** `request_id` is caller-supplied; if a
   caller reuses a request id for a *different* request, the events
   collapse. Mitigation: the writer also persists a `payload_hash` of
   `usage_units` + `metadata` and rejects a conflicting re-insert with
   `IdempotencyConflictError`. Phase 1 logs and returns the original
   row; Phase 2 hard-rejects.

## 9. Open questions (locked decisions recorded as they happen)

- [x] **Q1: Where does the layer live?** New `guardian/metering/`
  package — see §3. The conceptual split between
  `account_observability` / `metering` / `billing` is the firewall.
- [x] **Q2: Multi-service shape?** Generic `ServiceType` + per-service
  pricing rules. No table-per-service, no arbitrary JSONB for the
  authoritative accounting fields.
- [x] **Q3: Rate-limit dimension?** Phase 1 observe-only. USD spend
  is the first dimension to be considered when enforcement is enabled
  (Phase 3). Token count and request rate are evaluated in parallel
  but not enforced in Phase 1.
- [x] **Q4: Dashboard surface?** Admin JSON API + React dashboard.
  The dashboard consumes a Guardian-owned admin API; it does not own
  the accounting logic.
- [ ] **Q5: First pricing source?** Need confirmation: DeepSeek's
  published rates (`deepseek-chat`, `deepseek-reasoner`) plus any
  free-tier allowance. Locked when Phase 1 seeds `pricing_versions`.
- [ ] **Q6: PSP choice for Phase 4?** Stripe / Paddle / LemonSqueezy /
  other. Out of scope for this doc but blocks Phase 4.

## 10. What this document does NOT do

- **No runtime changes.** No code, no migrations, no routes.
- **No schema changes.** The SQL sketch in §5 is illustrative — a
  concrete migration will be authored when Phase 1 begins.
- **No ADR.** This design sketch is the precursor to (a) an ADR
  locking the snapshot-pricing + append-only ledger decisions, and
  (b) a Campaign document for Phase 1's phased implementation.
  Neither is implied by this doc.
- **No modification to `docs/architecture/00-current-state.md`.**
  Release-truth is unchanged.
- **No enforcement.** Phase 1 explicitly does not block requests.
- **No billing integration.** Phase 4 is out of scope; mocked balance
  only.

## 11. Acceptance criteria for THIS document

This design sketch is acceptable when:

- [x] The conceptual split `account_observability` / `metering` /
      `billing` is unambiguous and cited.
- [x] The service catalog is generic (one schema per service, not one
      table per service).
- [x] Snapshot pricing is mandatory and the cost field is
      `Decimal(12, 6)`.
- [x] Phase 1 is observe-only and the enforcement promotion criteria
      are named.
- [x] The dashboard consumes an admin API — accounting logic stays in
      `guardian/metering/`.
- [x] Every "where this plugs in" reference is a verified file path
      in the current working tree.
- [x] No runtime, schema, ADR, or release-truth file has been
      modified by this document.

## 12. Next authorized slice

When this design is approved:

1. Author the Phase-1 Campaign document
   (`docs/Campaign/CAMPAIGN_2026_09_XX_METERING_FOUNDATION.md`) with
   the implementation order: (a) DB migration, (b) catalog + pricing
   seed, (c) ledger writer, (d) DeepSeek integration, (e) admin JSON
   API, (f) React dashboard, (g) evaluator observe-only, (h) tests.
2. Canvas the four ADRs the design implies — the append-only ledger,
   the snapshot-pricing discipline, the metering/billing firewall,
   and the rate-limit phased-enforcement gate. Each becomes its own
   ADR or amendment.
3. Implement Phase 1 behind a single PR series, one Campaign gate at
   a time, with the operator (you) staring at the dashboard the whole
   time the $40 burns down.
