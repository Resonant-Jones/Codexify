# Scout Endpoint Configuration Contract

> Classification: architecture contract
> Status: normative
> ADR impact: aligned with existing architecture contracts
> Governing contracts: `config-and-ops.md`, `account-export-restore-contract.md`, `data-and-storage.md`

Purpose: Define how Scout stores, validates, and presents remote Vault endpoint configuration without implementing networking, authentication, sync, or runtime behavior.

Last updated: 2026-06-20

## Scope

This contract defines the local configuration surface for a future Scout client that can point at a remote Codexify Vault runtime.

Current truth:

- Scout currently exists only as a SwiftUI shell scaffold.
- Guardian remains the operator-facing runtime authority.
- Vault remains the long-term authority for durable Codexify account, thread, memory, document, and artifact state.
- Local Docker Compose remains the supported runtime path.
- No authenticated Scout-to-Vault API lane exists yet.
- No mobile sync protocol exists yet.
- No release promise exists for remote mobile operation.

This document is a configuration contract only. It does not define endpoint routes, transport handshakes, OAuth flows, token refresh behavior, sync semantics, background workers, or document replication.

## Canonical Concepts

### Vault Endpoint

A Vault Endpoint is the user-configured network location for a Codexify Vault-compatible runtime that Scout may try to reach in the future.

A Vault Endpoint is not proof that the runtime exists, is trusted, is authenticated, or is release-supported. It is only a stored target plus the minimum metadata needed to present and validate that target safely.

### Endpoint Profile

An Endpoint Profile is the user-owned record Scout stores for one Vault Endpoint.

Profiles exist so Scout can present connection intent without turning remote configuration into ambient authority. A profile may be selected, validated, edited, deleted, exported, or restored, but it does not make Scout a second source of truth.

### Connection Status

Connection Status is Scout's user-visible interpretation of whether the configured endpoint is ready for use. It is derived from local configuration checks and, in a future implementation, bounded reachability/authentication probes.

Connection Status must be inspectable and must not silently downgrade failures to success.

### Authentication State

Authentication State is Scout's user-visible interpretation of whether the selected endpoint has usable credentials.

Authentication State is distinct from Connection Status. An endpoint can be reachable while still requiring authentication, and a credential can exist locally while the endpoint is unreachable.

### Endpoint Validation State

Endpoint Validation State is Scout's interpretation of whether the stored endpoint profile is syntactically and structurally valid enough to attempt connection.

Validation is not authentication. Validation is not reachability. Validation is not sync proof.

## Endpoint Profile Shape

The first profile shape is a contract-level data shape, not implementation code.

| Field | Meaning |
| --- | --- |
| `id` | Stable local identifier for this endpoint profile. |
| `name` | User-visible label for the endpoint. |
| `base_url` | Canonical base URL for the remote Vault-compatible runtime. |
| `transport_type` | Transport family selected for the profile. Initial contract value is `https`. Future values require a contract update. |
| `last_connected_at` | Timestamp of the last successful authenticated connection, if any. Absence means no successful connection is known. |
| `authentication_state` | Current user-visible authentication state for the profile. |
| `validation_state` | Current user-visible validation state for the profile. |

Optional future fields may be added only through a compatible schema migration. Future profile extensions must preserve existing profile identity, user ownership, and failure visibility.

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

- profile schemas must be versioned before durable storage is shipped
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

Before implementation, Scout endpoint configuration needs an explicit schema version and migration path.

Future runtime work must define separately:

- authenticated API lane
- supported endpoint discovery or capability surface
- credential lifecycle and revocation behavior
- trust and certificate expectations
- sync protocol, if any
- conflict policy for any replicated state
- user-visible recovery behavior

Until those contracts exist, endpoint profiles remain inert configuration and presentation state.

## Non-Goals

This contract does not define:

- networking implementation
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
