# Scout Endpoint Configuration Contract

> Classification: architecture contract
> Status: normative
> ADR impact: aligned with existing architecture contracts
> Governing contracts: `config-and-ops.md`, `account-export-restore-contract.md`, `data-and-storage.md`

Purpose: Define how Scout stores and presents endpoint configuration and enforces its current client authentication selection without granting runtime or identity authority.

Last updated: 2026-10-04

## Scope

This contract defines Scout's local endpoint configuration and current request-authentication boundary. The linked branch qualification establishes a bounded remote-session implementation and hosted live proof; it does not establish release support for remote mobile operation.

Current truth:

- Scout has a tracked Xcode app, passing package tests, and a bounded iPhone Simulator launch and five-route shell smoke result, recorded in `mobile/scout-ios/SCOUT_V1_BUILD_PROOF.md`.
- Guardian remains the operator-facing runtime authority.
- Vault remains the long-term authority for durable Codexify account, thread, memory, document, and artifact state.
- Local Docker Compose remains the supported runtime path.
- Scout's local/operator path can attach `X-API-Key`. The working remote-session branch implements isolated canonical account credentials and qualifies hosted continuity in [the October 4 proof](../../mobile/scout-ios/SCOUT_LIVE_CONTINUITY_2026-10-04.md); personal-node behavior retains unit-test proof and separate live qualification.
- No mobile sync protocol exists yet.
- No release promise exists for remote mobile operation.

This document governs endpoint metadata and client request-authentication selection only. It does not define endpoint routes, transport handshakes, OAuth flows, token refresh behavior, sync semantics, background workers, or document replication.

## Canonical Concepts

### Vault Endpoint

A Vault Endpoint is the user-configured network location for a Codexify Vault-compatible runtime that Scout may try to reach.

A Vault Endpoint is not proof that the runtime exists, is trusted, is authenticated, or is release-supported. It is only a stored target plus the minimum metadata needed to present and validate that target safely.

### Endpoint Profile

An Endpoint Profile is the user-owned record Scout stores for one Vault Endpoint.

Profiles exist so Scout can present connection intent without turning remote configuration into ambient authority. A profile may be selected, validated, edited, deleted, exported, or restored, but it does not make Scout a second source of truth.

### Connection Status

Connection Status is Scout's user-visible interpretation of whether the configured endpoint is ready for use. It is derived from local configuration checks and bounded reachability/authentication probes.

Connection Status must be inspectable and must not silently downgrade failures to success.

### Authentication State

Authentication State is Scout's user-visible interpretation of authentication evidence for the selected endpoint. Credential presence alone does not establish an authenticated state.

Authentication State is distinct from Connection Status. An endpoint can be reachable while still requiring authentication, and a credential can exist locally while the endpoint is unreachable.

### Authentication Mode

Authentication Mode is the explicit client credential mechanism selected for a profile. It is independent of transport and of observed Authentication State. Scout serializes `localAPIKey` or `remoteSession` in `authenticationMode`; it does not infer the mode from a URL, network label, stored key, or HTTP response.

`localAPIKey` retains optional `X-API-Key` request behavior. `remoteSession` requires a valid canonical Guardian `account_session` for the exact profile/origin; missing, expired or wrong-origin sessions fail before protected dispatch with no API-key or anonymous fallback. Personal nodes use Guardian Bearer where supported. The explicitly qualified hosted composition requires client-side Access Authorization and carries the canonical account credential via `X-Guardian-Account-Session` under ADR-092. The qualified edge may consume Authorization; Guardian must still validate the fixed-host/private-preview signed Access assertion before accepting the alternate account transport. Missing Authorization alone grants no trust. A remote profile cannot restore a stale authenticated display as current evidence.

Scout's current browser handoff provisions account sessions only on the qualified hosted composition. Personal-node Bearer transport remains implemented and isolated, but personal account-session provisioning is not implemented. Settings disables new selection of that unavailable personal account-login lane and explains the gap; the personal local API-key lane remains explicit and requires no hosted subscription or account. Stored/imported remote profiles do not fall back to a key. This limitation concerns client provisioning, not a mapping from network transport to Codexify identity.

### Endpoint Validation State

Endpoint Validation State is Scout's interpretation of whether the stored endpoint profile is syntactically and structurally valid enough to attempt connection.

Validation is not authentication. Validation is not reachability. Validation is not sync proof.

## Endpoint Profile Shape

The table describes the profile concepts. Current Swift `Codable` keys use camelCase, including `baseURL`, `transportType`, `authenticationMode`, `authenticationState`, `validationState`, and `lastConnectedAt`.

| Field | Meaning |
| --- | --- |
| `id` | Stable local identifier for this endpoint profile. |
| `name` | User-visible label for the endpoint. |
| `base_url` | Canonical base URL for the remote Vault-compatible runtime. |
| `transport_type` | User-selected transport label; current Scout values are `tailscale`, `localNetwork`, and `custom`. The URL scheme is separate and does not choose authentication mode. |
| `authenticationMode` | Explicit client credential mechanism: `localAPIKey` or `remoteSession`; separate from transport and observed state. |
| `last_connected_at` | Timestamp of the last successful authenticated connection, if any. Absence means no successful connection is known. |
| `authentication_state` | Current user-visible authentication state for the profile. |
| `validation_state` | Current user-visible validation state for the profile. |

Optional future fields may be added only through a compatible schema migration. Future profile extensions must preserve existing profile identity, user ownership, and failure visibility.

For the current on-device `ScoutEndpointProfile` encoding, a stored profile with no `authenticationMode` field decodes as `localAPIKey` while preserving its identifier, label, URL, transport, and other metadata. This compatibility rule applies only to an absent field. Explicit `null`, unknown, or malformed mode values fail decoding and must remain available for explicit repair; they never select local credentials. New encodings include `authenticationMode`. Mode metadata contains no credential material, and the existing profile storage key is unchanged. A full export schema or general profile-version migration is not defined by this narrow compatibility rule.

The current `ScoutRequestAuthentication` policy is applied by every existing Scout request consumer before `URLSession` dispatch, including health checks, writes, and task-event streaming. It clears incompatible selectors, attaches a non-empty local API key only in `localAPIKey` mode, and requires the profile/origin account credential in `remoteSession`. Hosted requests additionally require that connection's separate Access grant. Saving a profile, selecting a mode, possessing a credential, or receiving a health response does not by itself establish authentication. Settings clears stale connection-test presentation when endpoint identity or mode changes and discards a late probe result for a changed draft. Credentials use separate profile/origin Keychain records; legacy global keys are never silently adopted.

## Connection-State Vocabulary

Scout must use bounded connection-state vocabulary for this contract surface:

| State | Meaning |
| --- | --- |
| `UNCONFIGURED` | No endpoint profile is selected or the profile has no usable endpoint target. |
| `VALIDATING` | Scout is checking local profile shape or future bounded reachability/authentication prerequisites. |
| `REACHABLE` | The endpoint target appears reachable, but authentication is not yet established by this state alone. |
| `AUTH_REQUIRED` | The endpoint is reachable or configured enough to require credentials before use. |
| `AUTHENTICATED` | Scout has established an authenticated session or credential posture for the selected endpoint. |
| `UNREACHABLE` | Scout cannot reach the selected endpoint through the configured transport. |
| `INVALID_CONFIGURATION` | The profile is structurally invalid, unsupported, incomplete, or unsafe to attempt. |

These states are UI/configuration vocabulary only. They must not be treated as runtime protocol tokens, task events, queue states, provider states, or sync-engine states.

## Storage Doctrine

Endpoint configuration is user-owned local state. Scout may store enough local data to let the user identify, edit, validate, and reselect endpoint profiles.

Scout may store on-device:

- endpoint profile `id`
- endpoint profile `name`
- endpoint `base_url`
- selected `transport_type`
- non-secret timestamps such as `last_connected_at`
- current connection, authentication, and validation display states
- local migration metadata required to read older endpoint-profile schemas

Scout must not store unencrypted:

- access tokens
- refresh tokens
- session cookies
- API keys
- private keys
- recovery secrets
- raw bearer credentials
- credential-derived material that can authenticate to Vault

Credential-bearing material must use the platform secure storage lane. On iOS, Scout must expect Keychain-backed storage for secrets and must keep secret references separate from exportable profile metadata.

Endpoint profile data must be migration-ready:

- a future exported or shared profile schema requires explicit versioning before that feature is shipped
- migrations must preserve profile identity and user labels
- unsupported future schemas must fail closed or require explicit user repair
- migration failures must be visible to the user and must not silently discard endpoint profiles

## Export and Restore Considerations

Scout endpoint configuration must not redefine the account export and restore contract.

Export and restore behavior must preserve this boundary:

- non-secret endpoint profile metadata may be eligible for future export if the export manifest explicitly includes it
- credential-bearing material must not be exported in plaintext
- restored endpoint profiles must require explicit validation before use
- restored credentials must require a secure restore path or reauthentication
- restore must not imply that a remote Vault endpoint is reachable, authenticated, trusted, or release-supported

If endpoint profiles are added to a future export schema, the export manifest must declare their schema version, counts, integrity coverage, and restore behavior. Silent loss or silent credential downgrade is not allowed.

## Invariants

- Vault remains the long-term source of truth for durable Codexify account, thread, memory, document, and artifact state.
- Guardian remains the operator-facing runtime authority.
- Scout is not a second authority for memory, documents, transcripts, identities, or runtime execution.
- Scout does not own memory.
- Endpoint configuration is user-owned local state.
- Authentication state must be inspectable by the user.
- Connection failure, validation failure, and authentication failure must stay distinct.
- Failure states must not silently downgrade to success.
- Endpoint validation must not be represented as sync readiness.
- Endpoint reachability must not be represented as authentication.
- Authentication must not be represented as document replication.
- Scout does not redefine export/restore semantics.
- Scout does not redefine authentication doctrine.
- This contract does not expand the current release promise.

## Future Compatibility Expectations

Before future export, restore, or cross-client profile exchange, Scout endpoint configuration needs an explicit schema version and migration path beyond the absent-field compatibility rule above.

The [Scout/Vault contract](ios-scout-vault-remote-contract.md), ADR-051 and ADR-092 separately govern the implemented authenticated lane and credential lifecycle. Remaining runtime work must define separately:

- supported endpoint discovery or capability surface
- trust and certificate expectations
- sync protocol, if any
- conflict policy for any replicated state
- user-visible recovery behavior

A stored endpoint profile alone never establishes account identity or sync authority. Both authentication modes remain subject to Guardian authorization; a new personal node or ingress composition requires its own live qualification.

## Non-Goals

This contract does not define:

- general networking implementation beyond authentication selection
- route names or API schemas
- OAuth implementation
- token refresh implementation
- sync engine
- document replication
- local memory authority
- background worker design
- push notifications
- offline queue semantics
- conflict-resolution semantics
- release support for remote mobile operation
