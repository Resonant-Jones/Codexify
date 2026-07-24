# Admin Account Observability Contract

> Classification: architecture contract
> Status: proposed (docs-only)
> Privacy sensitivity: high
> Implementation status: not implemented; this contract defines the normative boundary for future implementation slices.
> Release claim: this contract does not widen the supported beta release promise.
> Last updated: 2026-07-21

## Purpose

Define the privacy-bounded, Guardian-owned architecture contract for admin-facing account observability, coarse-usage measurement, and invite attribution. This contract constrains what Codexify may collect, how metrics are defined, and how the operator surface must behave before any persistence, route, or UI implementation begins.

## Scope

This contract covers:

- Canonical metric definitions for account counts, presence, growth, geography, and invite attribution
- Privacy prohibitions and allowed telemetry fields
- Presence heartbeat semantics
- Coarse-geography resolution policy
- Invite-link attribution semantics (first-touch, first-party only)
- Operator authorization model
- Snapshot API ownership and transport boundaries
- Retention, deletion, and export/restore implications
- Freshness, staleness, and failure semantics
- Implementation sequencing (future slices)
- Proof expectations for each future slice

This contract explicitly does **not** cover:

- Message content, conversation analytics, prompt collection, or assistant-output collection
- Page-level behavioral tracking, clickstream, or per-action event logs
- Precise location tracking
- Third-party analytics SDK integration
- Public registration implementation
- Guest-session implementation
- Any UI implementation

## Current-Truth Boundary

### What is true now (as of this writing)

- Guardian is the authority for authentication, canonical identity, human sessions, authorization, and dashboard truth.
- Codexify.Space or another presentation layer may fetch Guardian data server-side, but it must not own a second account database or independent role mapping.
- Postgres is the durable system of record.
- Generic runtime `/metrics` and existing health surfaces are not account analytics.
- The current supported release posture remains bounded by `docs/architecture/00-current-state.md`.
- The `User` model carries `id`, `username`, `password_hash`, `role` (constrained to `admin`/`guest`), and `created_at` (server-default `now()`).
- A `POST /auth/register` route exists but is gated behind private-preview checks.
- The dashboard snapshot (`GET /api/dashboard/snapshot`) requires dual authority: service API key plus authenticated human Guardian session.
- Admin routes use `X-Admin-Token` header-based authorization.

### What is not yet true

- No canonical guest identity model exists.
- No presence heartbeat model, session table, or `last_seen_at` field exists.
- No invite-link, referral, or attribution persistence exists.
- No registration-attribution linkage exists.
- No active-user counting, geography resolution, or invite-conversion analytics exist.
- Public account registration is not part of the supported beta claim set.

### What this contract may assume

- Guardian remains the sole backend authority for the proposed analytics snapshot.
- A future presentation layer may render the snapshot without owning its source data.
- New contract-bearing metric names, states, and failure codes will require bounded canonical registries during implementation.
- Historical data before collection begins may be incomplete and must remain visibly incomplete.

### What must not be inferred

- Documentation is not runtime proof.
- The presence of user rows is not proof of working public registration.
- A request, message, or thread timestamp must not be silently repurposed as presence.
- A link open is not the same as a human guest session.
- A guest session is not the same as a completed registration.
- An invitation token is not an account identity.
- Missing telemetry is not zero activity.

## Threat Model

### Adversaries and risks

| Threat | Mitigation |
|---|---|
| Operator overreach (inspecting individual conversation behavior through analytics) | Message content, thread metadata, prompts, and assistant output are explicitly outside this contract. The active-account list exposes only identity/status fields, not conversation or content columns. |
| Third-party analytics creep | No third-party analytics SDK, no fingerprinting, no cross-site tracking. |
| IP-based surveillance | Raw and hashed IP persistence are prohibited. Geography is resolved transiently and only coarse country/region stored. |
| Invite-token leakage | Only one-way token hashes are persisted. Tokens never appear in analytics responses, logs, or dashboard tables. |
| Guest reidentification | Guest identity uses a server-issued random first-party identifier. No fingerprinting, IP correlation, or probabilistic cross-device identification. |
| Analytics data surviving account deletion | Deletion rules sever row-level links. Only non-reidentifiable aggregate counts may remain. |
| Frontend impersonation | Browser clients must never receive `GUARDIAN_API_KEY`. Operator authorization requires server-side Guardian session verification. |
| Metadata inference from aggregate drill-down | Region-level cells with fewer than three distinct users are suppressed into `other_or_suppressed`. |

## Canonical Terminology

| Term | Definition |
|---|---|
| `registered_account` | A canonical non-system account whose registration completed through the accepted account path. Has a row in `users` with a trustworthy `created_at` timestamp. |
| `guest` | A pseudonymous, first-party browser/session identity without a canonical account. Identified by a server-issued random guest ID. |
| `system_account` | A non-human account used for internal service operation (e.g., seed/local user, service principals). Excluded from all human-registration and active-user totals. |
| `service_principal` | A machine identity used for service-to-service authentication. Excluded from human metrics. |
| `operator` | A canonical human account with explicit operator/admin authorization, verified through the Guardian session and role system. |
| `presence_session` | Operational activity metadata representing a foreground application heartbeat. Not a conversation, message, or content object. |
| `invite_link` | An operator-authored acquisition source identified by a canonical invite ID with campaign and placement labels. |
| `invite_attribution` | The binding of an eligible guest session or completed registration to a canonical invite ID through first-party, first-touch attribution. |
| `active_window` | The time window (default 5 minutes) following the latest accepted foreground heartbeat during which the account or guest is considered "active now." |
| `foreground_heartbeat` | A periodic client signal (default interval 60 seconds) sent only while the application tab is foregrounded. Carries no page path, route, content, or feature name. |

## Actor and Identity Categories

The contract distinguishes these identity categories:

| Category | Canonical identity source | Included in registered-account metrics? | Included in active-user metrics? |
|---|---|---|---|
| `system_account` | Seed/local bootstrap user, service principals | No | No |
| `service_principal` | Machine identities | No | No |
| `registered_account` | `users` table row with completed registration | Yes | Yes, when presence lease is active |
| `guest` | Server-issued random guest ID | No | Yes, as separate guest population |
| `operator` | `registered_account` with operator/admin role | Yes (counted as registered account) | Yes (counted as registered account) |

Rules:

- Display names, emails, browser labels, or arbitrary `X-User-Id` values must not become canonical account identity.
- A `system_account` or `service_principal` is excluded from human registration and active-user totals.
- An `operator` is a canonical human account; operator status does not create a separate identity class for metric purposes.

## Metric Definitions

### Canonical conceptual metrics

| Metric | Definition | Population | Notes |
|---|---|---|---|
| `registered_accounts_current` | Count of current non-deleted, non-system registered accounts | `registered_account` rows excluding `system_account` and `service_principal` | Excludes guests, incomplete registrations, and system accounts. |
| `registrations_lifetime` | Count of completed human registrations since trustworthy registration measurement began | All completed `registered_account` creations, including subsequently deleted accounts | Deleted accounts remain in this historical aggregate. Distinct from `registered_accounts_current`. |
| `registrations_daily` | Completed human registrations grouped by UTC calendar day | Daily buckets of `created_at` | UI may display in an operator-selected timezone; storage and canonical bucketing remain UTC. |
| `active_registered_now` | Distinct registered accounts with at least one valid foreground presence lease whose `last_seen_at` is within the active window | `registered_account` + valid presence lease | Approximate within active-window tolerance. |
| `active_guests_now` | Distinct guest identities with at least one valid foreground presence lease within the active window | Guest identities + valid presence lease | Counted by random guest identity, not open browser tab. |
| `daily_active_registered` | Distinct registered accounts with at least one valid presence bucket during the UTC day | `registered_account` + presence bucket for UTC day | DAU. |
| `weekly_active_registered` | Distinct registered accounts with at least one valid presence bucket during the trailing 7-day window | `registered_account` + presence bucket in window | WAU. Trailing, not calendar-aligned. |
| `monthly_active_registered` | Distinct registered accounts with at least one valid presence bucket during the trailing 30-day window | `registered_account` + presence bucket in window | MAU. Trailing 30 days, not calendar month. |
| `hourly_active_registered` | Distinct registered accounts with valid foreground presence in each UTC hour bucket | `registered_account` + presence bucket for UTC hour | Time-of-day usage pattern. |
| `hourly_active_guests` | Distinct guest identities with valid foreground presence in each UTC hour bucket | Guest identities + presence bucket for UTC hour | Guest time-of-day pattern. |
| `guest_to_account_conversions` | Completed registrations that can be bound to the same first-party guest attribution lineage | Guest-to-account attribution linkage | Does not infer conversion from IP, email similarity, device fingerprinting, or timing coincidence. |
| `invite_attributed_guest_sessions` | Distinct first-party guest sessions that began with a valid invite attribution | Guest sessions with invite attribution | Bots and link-preview agents may resolve URLs; this metric counts only sessions with confirmed first-party attribution. |
| `invite_attributed_registrations` | Completed registrations whose canonical first-touch acquisition source is the invite link | `registered_account` with canonical invite attribution | First-touch only. |
| `invite_conversion_rate` | `invite_attributed_registrations / invite_attributed_guest_sessions` | Derived | Returns `null` with explicit reason when denominator is zero or unavailable. Must not return a fabricated zero percentage. |
| `active_accounts_list` | Paginated operator-only read model | `registered_account` rows with optional presence and invite fields | Includes: canonical account ID, username/display name, email (only when already part of the account contract), role/status, registration timestamp, current active flag, `last_seen_at`, and operator-facing invite label. Excludes: messages, thread counts, message counts, document counts, prompt counts, location history, individual geographic fields. |

## Allowed Telemetry

### Conceptual presence-session fields

| Field | Type | Required | Notes |
|---|---|---|---|
| presence-session ID | random identifier | Yes | Server-issued, unrelated to authentication token |
| canonical account ID | nullable FK | No | Null for guest sessions |
| random guest ID | nullable | No | Server-issued, first-party only |
| session start timestamp | UTC datetime | Yes | |
| latest foreground heartbeat timestamp | UTC datetime | Yes | Updated on each accepted heartbeat |
| session end timestamp | UTC datetime | No | Set on explicit logout or lease expiry |
| invite ID | nullable FK | No | From first-party attribution cookie/binding |
| ISO country code | nullable | No | Coarse-geography only |
| first-level region code | nullable | No | Coarse-geography only |
| created_at | UTC datetime | Yes | |
| updated_at | UTC datetime | Yes | |

### Conceptual registration-attribution fields

| Field | Type | Required | Notes |
|---|---|---|---|
| canonical account ID | FK | Yes | |
| registration completion timestamp | UTC datetime | Yes | |
| canonical acquisition invite ID | nullable FK | No | First-touch only |
| prior guest ID or attribution ID | nullable | No | Only while required for verified conversion linkage |
| attribution method | constrained token | Yes | Fixed to contract-defined values (e.g., `first_party_cookie`) |
| attribution confidence | constrained token | Yes | Fixed to contract-defined values (e.g., `direct`) |

### Conceptual invite-link fields

| Field | Type | Required | Notes |
|---|---|---|---|
| opaque invite ID | identifier | Yes | Canonical identifier |
| operator-authored name | string | Yes | Human-readable label |
| campaign label | string | No | Operator-defined grouping |
| placement label | string | No | Where the link was placed |
| created-by operator ID | FK | Yes | |
| one-way token hash | string | Yes | Never the raw token |
| status | constrained token | Yes | `active`, `revoked`, `expired`, `disabled` |
| created_at | UTC datetime | Yes | |
| expires_at | UTC datetime | No | |
| revoked_at | UTC datetime | No | |
| disabled_at | UTC datetime | No | |

## Prohibited Telemetry

The following must **never** be collected, persisted, or derivable from the analytics system:

- User messages, assistant messages, prompts, or retrieved context
- Message history, thread titles or contents, project titles or contents
- Document titles, paths, filenames, or contents
- Model responses, tool inputs, or tool outputs
- Per-feature usage events or feature-use event streams
- Click events, navigation history, page paths, scroll depth
- Text-selection events, keyboard events, composer events
- Raw referrer URLs (except for the one-time invite-token resolution, after which the referrer is discarded)
- Raw query strings unrelated to the canonical invite token
- Raw IP addresses
- Hashed IP addresses
- Full user-agent strings
- Canvas, font, audio, hardware, or browser fingerprints
- City, postal code, latitude, longitude, or street-level geography
- ISP, ASN, or exact device location
- Contact/address-book data
- Third-party advertising identifiers

## Presence Contract

### Heartbeat timing defaults

| Parameter | Default | Notes |
|---|---|---|
| Heartbeat interval | 60 seconds | While application is foregrounded |
| Active window | 5 minutes | Since latest accepted foreground heartbeat |
| Idle session expiry | 30 minutes | Without an accepted foreground heartbeat |

These values must be documented as future canonical configuration values rather than scattered literals.

### Presence rules

1. Heartbeats carry no page path, route, content, feature name, message ID, thread ID, project ID, or action name.
2. Hidden/background tabs must not continue presenting the account as actively using the service.
3. Logout should end the presence lease best-effort.
4. Lease expiry remains authoritative when logout or disconnect is missed.
5. Multiple browser tabs or devices count as one active account for account-level metrics.
6. Guest sessions count by random guest identity, not by open browser tab.
7. `last_seen_at` is presence metadata only.
8. A model generation, API request, message send, or document access must not update presence unless it is also accompanied by the canonical presence heartbeat.
9. Live counts are approximate within the active-window tolerance.

## Coarse-Geography Policy

### Resolution rules

1. Resolve geography transiently from the trusted request source at the Guardian or approved edge boundary.
2. Store only:
   - ISO 3166-1 alpha-2 country code
   - First-level administrative region code when available and reliable
3. For the United States, first-level region means state (e.g., ISO 3166-2 `US-CA`).
4. For other countries, first-level region means the equivalent province, state, territory, or administrative subdivision.
5. Immediately discard the raw source IP after coarse resolution.
6. Never persist a raw or hashed IP.
7. Never store city, postal code, coordinates, ISP, ASN, or street information.

### Geography usage rules

1. Do not use geography as an authentication or authorization signal.
2. Do not expose per-account geography in the default admin account table.
3. Aggregate geography separately for registered accounts and guests where useful.
4. Preserve `unknown` as an explicit category (GeoIP unavailable, resolution failure, or suppressed).
5. Region-level dashboard cells with fewer than three distinct users in the selected period must be combined into `other_or_suppressed`.
6. Country totals may remain visible, but must not expose a drill-down that reveals an individual's location.

### Limitations

VPNs, proxies, mobile networks, and inaccurate GeoIP data may produce incorrect or misleading geography. The dashboard must not present coarse-geography data as precise or authoritative.

## Invite-Link Attribution

### Invite-link model

One invite link per campaign or placement. Examples of operator-authored placement labels:

- `friends-email-wave-1`
- `discord-profile`
- `reddit-post-july`
- `conference-qr`
- `personal-text-group-a`

### Invite rules

1. Use a cryptographically random opaque token (minimum 128 bits of entropy).
2. Persist only a one-way token hash (e.g., SHA-256).
3. Never expose the raw token in admin analytics, logs, or dashboard tables.
4. Never use the token as account identity.
5. Each invite record carries operator-authored campaign and placement labels.
6. Do not require raw external referrer collection.

### Attribution mechanics

1. A valid invite may establish a first-party attribution cookie or equivalent random attribution identifier.
2. The attribution identifier must be unrelated to the authentication-session token.
3. The attribution cookie must have a bounded lifetime (default 30 days) and an explicit privacy disclosure.
4. Initial conversion attribution is **first-touch**:
   - The first valid invite associated with the guest lineage becomes the canonical acquisition invite.
   - Later invite opens may be counted as landings but must not silently rewrite the completed account's canonical acquisition source.
5. A completed registration may link to the guest lineage only when the registration flow receives the same valid first-party attribution identifier.
6. No IP, fingerprint, email similarity, or probabilistic identity resolution may be used for attribution.
7. Revoked or expired links must fail closed for new attribution.
8. Historical aggregate results for a revoked link may remain visible.
9. Link opens, attributed guest sessions, and completed registrations are different events and must not be collapsed.
10. The primary effectiveness denominator is attributed guest sessions, not raw HTTP opens, because bots and link-preview agents may resolve URLs.

## Operator Authorization and Transport

### Authority model

1. Guardian owns the analytics snapshot and all authorization decisions.
2. Codexify.Space or another web presentation layer owns rendering and server-side transport only.
3. The account-observability snapshot requires:
   - An authenticated Guardian human session.
   - Explicit operator/admin authorization.
   - The existing server-held Guardian service credential where the current dashboard boundary requires it (dual authority).
4. A service credential alone must not impersonate a human operator.
5. A human session alone must not bypass the server-side service boundary where dual authority is required.
6. Browser JavaScript must not call Guardian with `GUARDIAN_API_KEY`.
7. Frontend code must not maintain an independent list of admin emails or roles.
8. Client-provided `X-User-Id`, display names, or query parameters must not grant admin access.
9. Every successful or denied snapshot access should produce a bounded security audit record containing operator identity, route, decision, timestamp, and request ID, but not the response body.

## Snapshot/API Ownership

### Conceptual contract identifier

`guardian.admin.account_observability.snapshot.v1`

### Conceptual future routes

```
GET /api/operator/account-observability/snapshot
GET /api/operator/account-observability/active-accounts
```

### Snapshot contents (conceptual)

| Field | Description |
|---|---|
| contract/version identifier | `guardian.admin.account_observability.snapshot.v1` |
| `as_of` | UTC timestamp when the snapshot was generated |
| `coverage_start` | UTC timestamp when trustworthy measurement began |
| `source_freshness` | Per-section freshness classification |
| `degraded_reasons` | Explicit reasons for any degraded or unavailable sections |
| `registered_accounts_current` | Current registered account count |
| `registrations_lifetime` | Lifetime completed registrations |
| `registrations_daily` | Daily registration time series |
| `active_registered_now` | Current active registered count |
| `active_guests_now` | Current active guest count |
| `daily_active_registered` | DAU |
| `weekly_active_registered` | WAU |
| `monthly_active_registered` | MAU |
| `hourly_active_registered` | Hourly activity buckets |
| `hourly_active_guests` | Hourly guest activity buckets |
| `geography` | Aggregate country and region distribution |
| `invite_performance` | Per-invite metrics |
| `guest_to_account_conversions` | Conversion count |
| `retention_posture` | Declared retention periods |

### What must not be exposed

- Raw presence-session rows
- Raw guest IDs
- Invite tokens
- IP-derived source values
- Individual geography
- Conversation or content metadata
- User IDs, invite IDs, countries, or regions in Prometheus label dimensions

### Active-accounts list pagination

The `GET /api/operator/account-observability/active-accounts` route must be paginated and separately authorized. It must not expose per-account geography, message counts, thread counts, or content metadata.

## Freshness and Failure Semantics

### Required fields in every analytics response

| Field | Meaning |
|---|---|
| `as_of` | UTC timestamp when the snapshot or section was computed |
| `coverage_start` | UTC timestamp when trustworthy measurement for this metric began |
| `freshness` | `fresh`, `stale`, `unavailable` |
| `degraded_reasons` | List of explicit reason strings when not fully fresh |

### State semantics

| State | Meaning |
|---|---|
| `zero` | Returned only when the relevant source is healthy, coverage exists, and the query truthfully produced zero. |
| `unavailable` | Returned when the underlying source cannot be queried (e.g., database unreachable, GeoIP service down). |
| `unknown` | Returned when the metric was never collected or the source has no data for the queried period. |
| `stale` | Returned when the latest aggregate or presence update exceeds its freshness policy. |
| `suppressed` | Returned when data exists but cannot be displayed due to privacy thresholds (e.g., region cells with < 3 users). |

### Rules

1. Return zero only when the source is healthy, coverage exists, and the value is truthfully zero.
2. Return `unavailable` or `unknown` when the underlying source cannot be queried.
3. Return `stale` when the latest update exceeds its freshness policy.
4. Do not silently substitute cached totals without marking them stale.
5. Do not infer historical activity before telemetry collection began.
6. Do not backfill historical location or invite attribution from messages, request logs, account emails, audit logs, or browser data.
7. Existing accounts without trustworthy registration timestamps must be represented with explicit limited coverage rather than fabricated dates.

## Retention and Deletion

### Retention periods

| Data class | Retention | Notes |
|---|---|---|
| Foreground presence-session rows | 30 days | Rolling window from `created_at` |
| Pseudonymous invite-attribution/guest-session rows | 90 days | Unless converted to a registered account or deleted earlier |
| Per-account `registered_at` | Durable | Account metadata |
| Per-account `last_seen_at` | Retained while account exists | |
| Per-account canonical acquisition invite ID | Retained while account exists | Unless deletion or privacy policy requires earlier removal |
| Hourly activity aggregates | 13 months | Rolling window |
| Hourly geography aggregates | 13 months | Rolling window |
| Daily registration aggregates | Long-term | Non-content business aggregates |
| Invite-conversion aggregates | Long-term | Non-content business aggregates |
| Raw IP | Zero retention | Never persisted |
| Message/content telemetry | Zero collection, zero retention | Never collected |

### Deletion rules

1. Account deletion must remove account-linked presence rows.
2. Account deletion must sever the account's acquisition-invite association.
3. Guest deletion or cookie reset must make the old guest identity unavailable for new attribution.
4. Non-reidentifiable aggregate counts may remain after deletion.
5. The contract must distinguish:
   - `registered_accounts_current` (existing, non-deleted)
   - `registrations_lifetime` (all completed, including deleted)
   - Deleted-account presence/activity removed from current metrics
6. A deleted account must not continue appearing in the active-account list.
7. Retention cleanup must be deterministic and testable.

## Export and Restore Implications

1. Account registration timestamp is account metadata; it must be included in the account export.
2. Active presence rows are operational telemetry and must not be restored as live sessions.
3. Invite-open and guest-session telemetry must not be restored as active attribution state.
4. Restored accounts must not become active automatically.
5. Restored accounts must not recreate expired presence leases.
6. Long-term operator aggregates are not canonical conversation/account content; they are not part of the account export artifact.
7. A future privacy/data-access export may need to disclose row-level telemetry even when the portability restore artifact does not replay it.
8. No existing Account Export + Restore guarantee may be silently weakened.

## Admin-Panel Information Architecture (Future UI Reference)

This section describes the conceptual information architecture for a future operator UI. It does not implement any UI.

### Overview section

- Current registered accounts
- Lifetime registrations
- Registrations today, trailing 7 days, and trailing 30 days
- Active registered accounts now
- Active guests now
- Guest-to-account conversion count
- `as_of` and coverage annotation

### Growth section

- Cumulative registrations chart
- Daily registrations chart
- Current versus deleted accounts distinction
- Coverage-start annotation

### Activity section

- DAU, WAU, MAU
- Hourly registered-user activity
- Hourly guest activity
- Operator-selectable display timezone
- Clear statement: activity means foreground presence, not messages or actions
- `as_of` and freshness annotation

### Active Accounts section

- Paginated currently active account list
- Account identity/status fields only
- Registration timestamp
- Last-seen timestamp
- Acquisition invite label where present
- No conversation, content, or individual geography columns

### Geography section

- Country distribution (aggregate)
- First-level region distribution (aggregate)
- Separate registered and guest cohorts where useful
- Explicit `unknown` and `other_or_suppressed` categories
- No map precision beyond country/region

### Invites section

- Per-invite: label, campaign, placement, status
- Attributed guest sessions count
- Attributed registrations count
- Conversion rate
- Creation, expiry, and revocation timestamps
- No token display

Every section must show its `as_of`, coverage, and degraded state.

## Implementation Sequencing

The following slices are ordered and must be implemented as separate atomic tasks:

### Slice 1: Canonical tokens, persistence entities, migration, and focused model tests

- Register canonical token domains for metric names, attribution methods, invite statuses, freshness states, and presence states.
- Create persistence entities (presence session, invite link, registration attribution, hourly aggregates).
- Create Alembic migration.
- Write focused model tests.

### Slice 2: Invite creation/resolution and first-party attribution lineage

- Implement invite-link creation (operator-only).
- Implement invite-token resolution endpoint.
- Implement first-party attribution cookie/binding.
- Write attribution lineage tests.

### Slice 3: Guest/account foreground presence heartbeat and retention cleanup

- Implement heartbeat endpoint.
- Implement presence-session lifecycle (create, update, expire, end on logout).
- Implement retention cleanup job for presence-session rows.
- Write presence contract tests.

### Slice 4: Transient coarse-GeoIP resolution with no raw-IP persistence and privacy tests

- Implement transient GeoIP resolution at the Guardian boundary.
- Persist only country and region codes.
- Immediately discard raw IP.
- Write privacy sentinel tests proving IP is not persisted.

### Slice 5: Aggregate builders and Guardian operator snapshot routes

- Implement hourly/daily aggregate builders.
- Implement `GET /api/operator/account-observability/snapshot`.
- Implement `GET /api/operator/account-observability/active-accounts`.
- Write route authorization and freshness tests.

### Slice 6: Codexify.Space or approved operator UI

- Implement the admin observability panel in the approved presentation layer.
- Render snapshot data server-side.
- Never expose `GUARDIAN_API_KEY` to the browser.

### Slice 7: Live supported-path proof, privacy sentinel tests, deletion proof, freshness/failure proof, and documentation reconciliation

- Prove end-to-end: registration → presence → aggregate → snapshot → UI render.
- Prove: IP is never persisted.
- Prove: account deletion severs attribution links.
- Prove: region suppression with < 3 users.
- Prove: freshness/staleness/unavailable transitions.
- Reconcile documentation with implementation reality.

Each slice requires its own atomic Task Spec and commit.

## Non-Goals

- No database models in this task.
- No Alembic migration in this task.
- No account-registration implementation.
- No guest-session implementation.
- No heartbeat endpoint.
- No GeoIP dependency.
- No IP processing code.
- No invite-link route.
- No analytics aggregation worker.
- No admin API route.
- No dashboard snapshot modification.
- No frontend component.
- No Codexify.Space modification.
- No Prometheus metrics.
- No third-party analytics SDK.
- No cookie implementation.
- No privacy-policy copy.
- No deployment changes.
- No backfill.
- No release claim.
- No unrelated ADR cleanup.

## Proof Expectations (Per Future Slice)

| Slice | Required proof |
|---|---|
| Slice 1 | Migration applies and downgrades cleanly. Token registries have contract tests. |
| Slice 2 | Invite creation, resolution, and first-party attribution lineage pass focused tests. Revoked links fail closed. |
| Slice 3 | Heartbeat creates/updates presence. Background tab stops presence. Logout ends lease. Lease expiry authoritative. Retention cleanup runs deterministically. |
| Slice 4 | IP address is not present in any persisted row, log, or dump after resolution. Country/region codes are stored. `unknown` works when GeoIP unavailable. |
| Slice 5 | Snapshot route returns versioned, freshness-annotated payload. Operator authorization is enforced. Dual authority works. |
| Slice 6 | UI renders snapshot data without exposing tokens, guest IDs, or individual geography. No `GUARDIAN_API_KEY` in browser. |
| Slice 7 | Full end-to-end proof: registration → presence → aggregate → snapshot → UI. Privacy sentinels pass. Deletion proof passes. Freshness/failure transitions verified. |

## Invariants

1. Guardian remains the identity, authorization, session, and analytics authority.
2. No second user database or frontend-owned role map may be introduced.
3. Admin analytics require an authenticated human operator and the existing server-side Guardian service boundary.
4. Browser clients must never receive `GUARDIAN_API_KEY`.
5. Message content, message history, prompts, assistant output, retrieved context, document contents, and thread contents are outside this analytics contract.
6. Message, thread, project, document, memory, and artifact identifiers must not be used as account-analytics dimensions.
7. No clickstream, page-path history, scroll tracking, keystroke tracking, composer tracking, feature-use event stream, or per-action event log may be collected.
8. No raw or hashed IP address may be persisted.
9. No city, postal code, latitude, longitude, street, ISP, ASN, or exact device location may be persisted.
10. No browser or device fingerprinting may be used.
11. Guest identity must use a server-issued random first-party identifier, not an IP address, fingerprint, email guess, or user-agent hash.
12. Registered accounts and guests must remain separate metric populations.
13. "Active" must be derived only from the canonical presence contract, never from message creation, thread access, document access, or model execution.
14. Geography must be presented as aggregate country or first-level region data, not as an individual-account location column.
15. Invite tokens are bearer transport artifacts and must never appear in analytics responses, logs, or dashboard tables.
16. Invite attribution must use the invite's canonical ID and operator-authored labels, not raw external referrer URLs.
17. Generic Prometheus labels must not contain user IDs, emails, guest IDs, invite IDs, region codes, or other unbounded/high-cardinality account dimensions.
18. Unknown, unavailable, stale, suppressed, and zero are distinct states.
19. Account deletion must remove or sever row-level analytics links according to the contract.
20. Existing users must not receive fabricated historical presence, geography, or invite attribution.
21. This documentation task must not change runtime behavior or release claims.

## Compatibility and Migration Impact

- This task changes documentation only.
- No migration runs in this task.
- Future migrations must preserve existing user/account boundaries.
- Existing seeded local/system users must be excluded from human registration metrics.
- Existing accounts must receive a documented coverage start rather than invented historical telemetry.
- Future rollback must be able to stop collection without affecting account authentication or conversation data.
- Analytics collection failure must not block login, guest access, chat, retrieval, or account creation.

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/005-Runtime-Mode-and-Account-Boundary-Invariants.md`
- `docs/architecture/adr/039-operator-user-access-boundary.md`
- `docs/architecture/guardian-dashboard-snapshot-contract.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/data-and-storage.md`
