---
tags:
- architecture
- adr
- admin
- observability
- privacy
- presence
- geography
- invite-attribution
- analytics
aliases:
- ADR-049
- Admin Account Observability and Invite Attribution
---

# ADR-049: Admin Account Observability and Invite Attribution

## Status

Proposed (docs-only)

## Date

2026-07-21

## Context

Codexify is being prepared for guest access and account registration. The operator needs a private admin surface to answer questions about account growth, active usage, coarse geography, and invite-link effectiveness.

No such analytics surface exists today. No presence model, guest identity model, invite model, geography resolution, or admin analytics route exists. The `User` model carries `id`, `username`, `password_hash`, `role` (`admin`/`guest`), and `created_at`. The dashboard snapshot provides health and sensor telemetry but no account analytics.

Without an explicit architecture contract, future implementation could easily:
- Derive "active" from message timestamps, violating the separation between conversation content and operational metadata.
- Persist raw IP addresses or precise location for "analytics convenience."
- Use third-party behavioral analytics SDKs.
- Repurpose invite tokens as identity or expose them in dashboards.
- Confuse guest sessions with registered accounts.
- Invent historical data for existing users.

This ADR records the binding decisions before any schema, route, collection, or UI implementation begins.

## Decision

### 1. Guardian is the sole account-observability authority

Guardian owns identity, authorization, sessions, and the analytics snapshot. No second user database, frontend-owned role map, or independent analytics authority may be introduced. A presentation layer (e.g., Codexify.Space) may render Guardian-owned data server-side but must not own source data.

### 2. Measurement is presence-based and content-free

"Active" is derived only from foreground presence heartbeats. A presence heartbeat is operational metadata carrying no page path, route, content, message ID, thread ID, project ID, or action name. Message creation, thread access, document access, model execution, and API requests do not update presence on their own.

### 3. Guest and account populations remain distinct

Registered accounts and guests are separate metric populations. Guest identity uses a server-issued random first-party identifier. No IP address, fingerprint, email guess, or user-agent hash may serve as guest identity.

### 4. Raw IP and precise geography are prohibited

- Raw IP addresses must never be persisted.
- Hashed IP addresses must never be persisted.
- Geography is resolved transiently at the Guardian boundary, and only ISO country code and first-level region code are stored.
- City, postal code, latitude, longitude, ISP, ASN, street, and device-level location are prohibited.
- The raw source IP is discarded immediately after coarse resolution.

### 5. First-touch, first-party invite attribution is canonical

- Each invite link uses a cryptographically random token; only the one-way hash is persisted.
- Attribution uses a first-party cookie or equivalent random identifier, unrelated to the authentication session.
- First-touch attribution: the first valid invite associated with the guest lineage becomes the canonical acquisition source.
- Later invite opens do not rewrite the completed account's canonical source.
- No IP, fingerprint, email similarity, or probabilistic identity resolution is used for attribution.
- Revoked or expired links fail closed for new attribution.
- The primary effectiveness denominator is attributed guest sessions, not raw HTTP opens.

### 6. Interaction/clickstream analytics are deferred

No per-action event log, clickstream, page-path history, feature-use event stream, or behavioral tracking may be collected. This ADR explicitly defers interaction analytics to a future, separately governed ADR. This ADR does not authorize any form of behavioral tracking.

### 7. Row-level telemetry is short-lived

Presence-session rows: 30 days. Guest-session/attribution rows: 90 days (unless converted). Raw IP: zero retention. These retention periods prevent unbounded telemetry accumulation while supporting the operator's need for recent activity and conversion data.

### 8. Long-horizon analysis uses bounded aggregates

Hourly activity and geography aggregates are retained for 13 months. Daily registration and invite-conversion aggregates are retained as long-term non-content business aggregates. These aggregates are non-reidentifiable for small cohorts due to the `other_or_suppressed` threshold (fewer than 3 distinct users).

### 9. Operator access is explicitly authorized and dual-authority-compatible

The analytics snapshot requires:
- An authenticated Guardian human session.
- Explicit operator/admin role authorization.
- The server-held Guardian service credential where the current dashboard dual-authority boundary requires it.

Browser JavaScript must never receive `GUARDIAN_API_KEY`. Frontend code must not maintain an independent admin list.

### 10. Missing data remains unknown rather than becoming zero

- `zero`, `unknown`, `unavailable`, `stale`, and `suppressed` are distinct states.
- Zero is returned only when the source is healthy and truthfully produced zero.
- Unknown is returned when the metric was never collected.
- Unavailable is returned when the source cannot be queried.
- Stale is returned when the update exceeds its freshness policy.
- Suppressed is returned when privacy thresholds prevent display.

### 11. Existing messages, audit rows, and request logs are not analytics backfill sources

Historical data before collection begins must remain visibly incomplete. Existing accounts without trustworthy registration timestamps receive explicit limited coverage rather than fabricated dates. No backfill from messages, request logs, audit logs, or browser data is permitted.

### 12. Deletion is contract-bound

Account deletion removes account-linked presence rows and severs the acquisition-invite association. Non-reidentifiable aggregate counts may remain. A deleted account must not appear in the active-account list. Retention cleanup must be deterministic and testable.

## Alternatives Considered and Rejected

### 1. Deriving activity from message or request history

Rejected. This would collapse the separation between conversation content and operational metadata. It would make "active" dependent on content inspection and would violate the privacy boundary between content and analytics.

### 2. Persisting raw or hashed IPs

Rejected. Even hashed IPs are reidentifiable with rainbow tables or cross-referencing. The coarse-geography requirement can be satisfied with transient resolution and immediate IP discard.

### 3. Using third-party behavioral analytics

Rejected. Third-party SDKs introduce external data processing, broaden the trust boundary, and make privacy guarantees unenforceable within the Guardian-owned system boundary.

### 4. Storing city-level or more precise location

Rejected. Country and first-level region satisfy the operator's need for coarse usage patterns. City-level or more precise geography is unnecessary for account observability and introduces disproportionate privacy risk.

### 5. Frontend-owned analytics and role mapping

Rejected. The frontend must not own analytics data, maintain an independent role/account database, or hold `GUARDIAN_API_KEY`. Guardian remains the sole authority.

### 6. One giant unbounded event table

Rejected. Separating presence sessions, invite attribution, and hourly aggregates into bounded, retention-governed tables keeps the data model auditable and keeps retention enforceable per data class.

### 7. Using Prometheus user/geo/invite labels

Rejected. Prometheus labels must remain low-cardinality. User IDs, invite IDs, countries, and regions are unbounded or high-cardinality dimensions that would explode the Prometheus time-series cardinality.

### 8. Probabilistic cross-device guest identification

Rejected. Cross-device probabilistic identification (fingerprinting, IP correlation, behavioral matching) violates the privacy prohibition on fingerprinting and introduces reidentification risk.

## Consequences

### Positive

- Operators gain a privacy-bounded observability surface for account growth, activity, geography, and invite effectiveness.
- Presence-based activity measurement is content-free and auditable.
- IP addresses are never persisted, reducing privacy and compliance risk.
- First-party invite attribution without fingerprints protects guest privacy.
- Explicit retention periods prevent unbounded telemetry accumulation.
- Distinct `zero`/`unknown`/`unavailable`/`stale`/`suppressed` states prevent false confidence in analytics.
- Dual-authority operator access preserves the existing Guardian security model.
- Small-cohort suppression protects individual privacy in aggregate views.

### Negative

- Presence-based activity measurement requires clients to implement heartbeat endpoints.
- First-touch attribution cannot capture multi-touch conversion paths.
- Coarse-geography resolution depends on GeoIP accuracy, which is inherently imperfect.
- Operators cannot drill down into individual user behavior or content patterns.
- Pre-existing accounts will have limited historical coverage.

### Privacy consequences

- No message content, prompt, or assistant-output collection.
- No raw or hashed IP persistence.
- No browser or device fingerprinting.
- No city, postal, or coordinate-level location persistence.
- Guest identity uses random first-party identifiers.
- Small-cohort suppression in region aggregates.
- Attribution uses first-party identifiers unrelated to authentication.
- Invite tokens are never exposed in analytics.

### Compatibility consequences

- Existing accounts receive a documented coverage start, not fabricated history.
- Seeded system/local users are excluded from human metrics.
- Rollback must stop collection without affecting authentication or conversation data.
- Analytics collection failure must not block login, chat, or account creation.
- The existing dashboard snapshot is not modified by this contract.

### Future implementation gates

Each of the seven implementation slices defined in the companion contract requires:
- An atomic Task Spec.
- A separate commit.
- Slice-appropriate proof (model tests, privacy sentinels, authorization tests, or end-to-end proof).

No slice may widen the supported beta release promise without separate release-evidence work.

## Conditions Requiring a Superseding ADR

A new ADR is required if any future work proposes to:

- Collect message content, prompts, or assistant output for analytics.
- Persist raw or hashed IP addresses.
- Store city-level or more precise location.
- Introduce third-party analytics SDKs.
- Use fingerprinting or probabilistic cross-device identification.
- Change "active" to derive from message/request history instead of presence heartbeats.
- Use invite tokens as identity or expose them in dashboards.
- Remove or reduce the `other_or_suppressed` threshold for small cohorts.
- Extend retention periods beyond the contract without privacy review.
- Add interaction analytics, clickstream, or behavioral event streams.

## Related Documents

- `docs/architecture/admin-account-observability-contract.md` — companion normative contract
- `docs/architecture/00-current-state.md` — current release truth
- `docs/architecture/adr/005-Runtime-Mode-and-Account-Boundary-Invariants.md` — governing account-boundary ADR
- `docs/architecture/adr/039-operator-user-access-boundary.md` — governing operator/user boundary ADR
- `docs/architecture/guardian-dashboard-snapshot-contract.md` — existing dashboard snapshot contract
- `docs/architecture/account-export-restore-contract.md` — account export/restore contract
- `docs/architecture/canonical-token-philosophy.md` — canonical token discipline
- `docs/architecture/runtime-protocol-token-contract.md` — runtime protocol token registry
- `docs/architecture/data-and-storage.md` — storage systems and invariants
