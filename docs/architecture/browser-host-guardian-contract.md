# Browser Host and Guardian Contract Boundary

## Status

- Classification: normative architecture contract; architecture-impacting.
- Governing decision: [ADR-054](./adr/054-browser-host-topology-and-release-ownership.md).
- Implementation status: bounded production one-tab topology skeleton with
  deterministic stub proof; live Guardian integration remains unproven.
- Release status: not current release truth, not supported-runtime proof, and
  not a beta or public-release claim.
- Source of truth for wire meaning: the language-neutral JSON files under
  `browser_host/contracts/`; JavaScript and Python are consumers of that source.

## Purpose

This contract establishes the first production-owned Browser Host seam and its
bounded one-tab topology skeleton. It defines how the trusted Browser Host and
Guardian can advertise compatibility, negotiate bounded versions, produce a
Browser Context Envelope, request ephemeral attachment, and return a content-
free receipt. It preserves the distinction between browser evidence, Guardian
authority, capture, attachment, and durable persistence.

The package boundary is `browser_host/`. The language-neutral contract package
is `browser_host/contracts/`. The package is intentionally separate from
`browser_host_candidates/`, `src-tauri/`, `frontend/`, and `guardian/`.

## Scope and current implementation truth

The repository now contains JSON schemas, canonical Browser Host tokens,
synthetic fixtures, a Node built-in consumer adapter, a production
package-boundary module, a one-trusted-shell/one-remote-view runtime,
deterministic loopback Guardian and fixture support, live Playwright Electron
tests, JavaScript/Python conformance tests, and a pure Guardian-owned
attachment-grant issuer/consumer seam.

There is no live production Guardian route, production credential, or
supported authenticated grant-issuance path. A development-only Guardian
adapter is now available only behind explicit development, adapter, and
local-safe exposure gates. The deterministic stub exercises hello,
negotiation, capture, and ephemeral attachment; compatible negotiation gates
remote loading, and the trusted/remote renderer boundary is live-test proven
for this skeleton. The pure grant proof uses a synthetic authorized context,
process-local digest-only storage, and no network or persistence. The bounded
proof is not a supported feature. Electron is the accepted family under
ADR-054.

Candidate source and proof packets remain evidence only. They are not imported
by the production package and are not promoted into production code.

## Package ownership

| Surface | Owner | Current boundary |
|---|---|---|
| `browser_host/` | Codexify Browser Host package owner | Private `@codexify/browser-host` package, version `0.1.0`; bounded one-tab topology skeleton. |
| `browser_host/contracts/` | Shared Browser Host/Guardian contract owner | Private `@codexify/browser-host-contracts` package, version `0.2.0`; JSON source of truth. |
| Trusted Browser Host main process | Browser Host owner | Owns the bounded shell/view topology, negotiation, navigation policy, redacted state, and v1 envelope construction; it does not receive a reusable Guardian credential. |
| Guardian | Guardian owner | Remains authentication, policy, persistence, task, provider-execution, and durable-state authority. |
| Remote renderer/page | Untrusted content boundary | Evidence only; never receives Guardian credentials or native authority. |
| Tauri | Existing trusted shell owner | Remains shell and launcher under ADR-054; unchanged by this task. |
| Chrome extension | Existing Tier 0 owner | Remains the optional continuity bridge; unchanged by this task. |

## Protocol and schema versions

The manifest at `browser_host/contracts/manifest.json` records the initial
compatibility range:

- Contract package: `@codexify/browser-host-contracts` `0.2.0`.
- Guardian/Browser Host protocol: current, minimum, and maximum `1.0.0`.
- Browser Context Envelope: current and supported `1.0.0`.
- Context attachment: current and supported `1.0.0`.
- Hash algorithm: `sha256`.
- Timestamp format: RFC3339 UTC.
- Common inline capture budget: 65,536 UTF-8 bytes, copied from the neutral
  harness budget.

The initial range does not claim backward or forward compatibility beyond
`1.0.0`. Every wire object carries an explicit schema version.

## Browser Host hello

`browser-host-hello.v1.schema.json` describes a compatibility advertisement,
not authentication. It contains the Browser Host component version, supported
protocol, envelope, and attachment versions, supported feature tokens,
platform, architecture, request correlation ID, and generation time.

The hello object does not contain credentials, cookies, storage, user content,
page bodies, environment dumps, or raw filesystem paths. A hello can describe
capability; it cannot grant authority.

## Guardian negotiation

`browser-host-negotiation.v1.schema.json` describes the bounded decision made
against the hello advertisement. It records the compatibility outcome,
selected versions or explicit absence, enabled features, disabled features with
bounded reasons, a canonical error when incompatible, Guardian contract
identity, and generation time.

Compatibility is fail-closed:

- no mutually unsupported version may be selected;
- incompatible negotiation selects no transport versions;
- no undeclared feature may be enabled;
- compatible negotiation cannot carry an error code;
- negotiation does not authenticate a remote page; and
- negotiation does not grant native, credential, command, or persistence
  authority.

The v1 Guardian contract identity is
`guardian-browser-host-contract` at version `1.0.0`. It is a contract identity,
not a live route or an authentication credential.

## Compatibility and feature negotiation

The canonical feature identifiers are `capture:selected`, `capture:visible`,
and `capture:attach`, reused from the proven candidate control vocabulary.
Feature negotiation only enables a declared contract capability. It does not
authorize a broader capture mode, browser action, command bus call, or durable
write.

Unknown versions and features are rejected. Disabled features carry one of the
bounded reasons `not_supported`, `not_authorized`, `undeclared_feature`, or
`incompatible_version`. A future component may advertise a larger set, but the
v1 consumer must not silently interpret it.

## Browser Context Envelope v1

`browser-context-envelope.v1.schema.json` defines the authority-bearing
metadata that a future trusted Browser Host main process will construct around
bounded visible evidence. The v1 fields are:

- `schemaVersion`, `contextId`, `captureRequestId`, `requestId`, and
  `attemptNumber` for distinct correlation and retry identities;
- `sourceKind`, `sourceUrl`, `sourceOrigin`, `sourceTitle`, and `capturedAt`
  for source provenance;
- `captureMode`, `contentType`, `content`, `contentHash`, `contentLength`,
  `originalContentLength`, and `truncated` for bounded representation;
- `extractorVersion`, `permissionScope`, and `retentionClass` for extraction
  and retention provenance;
- `userInitiated`, which must be true;
- `documentGeneration` and `documentFingerprint` for stale-document
  correlation; and
- `sanitizationEvidence` for explicit exclusion declarations.

The v1 capture modes are the existing candidate tokens `selected_text` and
`visible_page_text`. Content is UTF-8 text and must remain within the 65,536
byte neutral harness budget. A truncated representation declares its original
length and remains evidence; truncation never implies completeness.

The schema rejects additional properties. It contains no Guardian credential,
cookie, browser-storage, form-value, native-command, command-bus, or
persistence-authority field. Sanitization evidence records that form-control,
password, hidden-input, cookie, local-storage, session-storage, script/style,
and cross-origin-iframe material was excluded. These booleans are evidence
declarations, not permission grants.

`sourceOrigin` must match the origin parsed from `sourceUrl`. The content hash
must match the submitted representation. Request identity and attempt identity
remain distinct from capture and context identity.

## Attachment attempt

`browser-context-attachment.v1.schema.json` models a separate operation from
capture. It carries protocol and attachment versions, `requestId`,
`attemptNumber`, an explicit `idempotencyKey`, the envelope, requested
ephemeral retention, separate trusted-shell user confirmation, an optional
target scope, and generation time.

Attachment v1 requires:

- `requestedRetention` to be `ephemeral`;
- `userConfirmation.confirmed` to be true and the method to be
  `trusted_shell`;
- a distinct, bounded idempotency key;
- an envelope that passes the v1 contract; and
- no implicit retry, persistence, or assistant-completion claim.

Capture and attachment are not interchangeable. A captured envelope can remain
unattached. An attachment attempt can be rejected. A retry is a new attempt
identity governed by the same request and stale-state rules.

## Attachment receipt

`browser-context-attachment-receipt.v1.schema.json` is a content-free result.
It contains schema and protocol versions, request/attempt/context identities,
an `accepted` or `rejected` attachment outcome, the explicit
`not_persisted` persistence outcome, a bounded error or explicit null, receipt
time, and a Guardian correlation identifier only when accepted.

An accepted attachment may still report no durable persistence. A rejected
attachment cannot claim Guardian acceptance. A receipt never echoes raw page
content, credentials, cookies, storage, or form values, and it never implies
assistant completion or task completion.

## Error contract

`browser-host-error.v1.schema.json` defines a bounded error code, safe message,
retryable flag, request correlation ID, generation time, and an allow-listed
`safeDetails` object. Error details may identify a contract, version, feature,
field, expected value, or actual bounded scalar. They may not contain raw page
content, credentials, cookies, storage, environment dumps, or stack traces.

Permission, capture, attachment, compatibility, and persistence meanings remain
separate. The token registry includes the conceptual failure vocabulary from
the browser authority contract plus the versioned contract-validation codes.

## Canonical tokens

`browser-host-tokens.v1.json` is the single bounded source for this protocol's
token domains:

- negotiation and compatibility outcomes;
- capture modes;
- retention classes;
- attachment and persistence outcomes;
- feature identifiers;
- disabled-feature reasons;
- hash algorithms;
- authority flags; and
- machine-readable error codes.

The registry does not redefine general chat, task, provider, or command-bus
tokens. New Browser Host protocol values must be added here with documented
meaning and conformance fixtures before use.

## Identity model

The package keeps these identities distinct:

- `requestId`: one execution request identity;
- `attemptNumber`: one attempt within that request;
- `captureRequestId`: one explicit capture initiation;
- `contextId`: one immutable captured representation;
- `idempotencyKey`: one attachment retry boundary; and
- `guardianCorrelationId`: Guardian's bounded receipt correlation.

Changing the document or origin invalidates the pending capture and requires a
new user initiation. A receipt does not become a message, task, assistant
completion, durable document, memory record, or permission grant.

## Guardian authority boundary

Guardian remains the authority for authentication, policy, persistence, task
acceptance, provider execution, and durable state. This package does not add a
Guardian route, client, credential, database model, migration, or persistence
behavior.

The trusted Browser Host main process constructs authority-bearing metadata only
within the reviewed trusted-shell boundary. The remote renderer and page
remain untrusted. Page content is evidence, not instruction, policy, identity,
permission, command, or memory authority.

## Guardian-issued attachment authorization grant

The Browser Host must not receive `GUARDIAN_API_KEY`, a Guardian session cookie,
or a reusable JWT. An already-authenticated Guardian surface will eventually
request the grant, and Guardian will derive the subject and policy server-side
from that trusted authentication boundary. The trusted Browser Host main
process may receive one short-lived, scope-bound, single-use attachment grant;
the remote renderer never receives the grant.

The grant is sensitive authorization material and must be protected as such. It
authorizes one ephemeral attachment attempt only. It does not authorize
durable persistence, provider execution, Command Bus actions, authentication of
page content, or representation of human identity. Consumption is atomic and a
replay fails closed. The v1 attachment body and receipt meanings remain
unchanged. The development adapter does not connect the production Browser
Host runtime or create a supported Guardian route.

Use the precise term `long-lived-credential-free Browser Host integration`.
Do not use the prohibited overclaim `credentialless attachment`: the bounded
grant is authorization material even though the Browser Host receives no
long-lived reusable Guardian credential.

## Trusted main-process ownership

The trusted main process owns capture correlation, source metadata,
document-generation checks, sanitization declarations, content hashing, bounded
envelope construction, and the separate ephemeral attachment attempt. This
slice implements those seams against deterministic loopback stubs; live
production Guardian integration and durable persistence remain outside scope.

## Remote-renderer prohibitions

The future remote renderer must not receive Guardian credentials, authentication
headers, cookies, storage, form values, native command capability, filesystem
authority, process authority, command-bus authority, or persistence authority.
Remote page text cannot change host policy or widen permissions. Any future
browser action requires a separate capability-scoped, confirmable, idempotent,
receipt-bearing contract.

## Fail-closed rules

The following are mandatory for any consumer:

1. Reject unsupported protocol, envelope, and attachment versions.
2. Select no transport version on incompatible negotiation.
3. Reject undeclared enabled features.
4. Reject missing or false user initiation.
5. Reject non-ephemeral v1 retention.
6. Reject origin, generation, hash, length, and content-mode mismatches.
7. Reject credentials, cookies, storage, form values, native commands, and
   unexpected additional properties.
8. Reject attachment without separate trusted-shell confirmation.
9. Never echo page content in receipts or wire errors.
10. Never widen capture, retry with another origin, or persist silently.

## Retention and persistence semantics

Capture produces a bounded ephemeral candidate envelope. Attachment makes an
accepted envelope available to one identified request attempt. Durable
persistence is not implemented or defined by v1. A future durable write must
be separately authorized by Guardian and must define destination, ownership,
retention, deletion, provenance, export/restore, recovery, and migration.

The `not_persisted` receipt outcome is explicit. It prevents an accepted
attachment from being misread as a durable document, retrieval record, memory
mutation, identity fact, or release capability.

## Security and redaction rules

- Synthetic fixtures contain no credentials, personal data, private URLs, or
  production identifiers.
- Raw page bodies never belong in receipts, errors, ordinary logs, or proof
  metadata.
- Hashes and lengths are integrity metadata, not authorization.
- Safe error details are bounded and allow-listed.
- Browser content remains evidence and cannot become instruction authority.
- The package has no network, credential, database, Electron, Playwright,
  renderer, or filesystem-runtime dependency.

## Language-neutral conformance fixtures

`fixtures/fixture-index.json` is the shared validity and expected-error index.
The ten positive fixtures cover hello, negotiation, selected-text and
truncated visible-page envelopes, an ephemeral attachment attempt, accepted
and rejected receipts, a bounded error, and the valid grant request/response.
The forty negative fixtures cover the existing v1 failures plus grant
retention, count, budget, TTL, version, confirmation, identity, credential,
and additional-property failures.

JavaScript uses Node's built-in test runner and the narrow adapter in
`browser_host/contracts/index.js`. Python uses the repository's already
available `jsonschema` package plus standard-library semantic checks. Both
languages consume the same manifest, schemas, tokens, fixtures, and expected
validity; neither language maintains a separate fixture expectation list.

## Version-change process

- Additive optional fields require a compatible minor contract change.
- New required fields require a new schema version.
- Token removal or semantic change requires a breaking version.
- Incompatible versions fail closed.
- Schema versions remain explicit in every wire object.
- Every change requires JavaScript and Python fixture parity.
- Major changes require Browser Host harness reassessment.
- Release compatibility remains unproven until live integration proof exists.

## Compatibility and deprecation policy

The v1 package has one supported protocol, envelope, and attachment version.
Consumers must inspect the manifest's minimum and maximum range rather than
assuming compatibility. Future deprecations must name the affected token or
field, preserve an explicit compatibility window, add positive and negative
fixtures, and document the removal version. A component must reject a version
outside the declared range instead of guessing or silently downgrading.

## Extraction and independent-release prerequisites

Before repository extraction or independent release, Codexify must prove a
stable live Guardian contract, versioned envelope and feature-negotiation
behavior, canonical-token ownership, supported-path contract tests, an SDK or
equivalent consumer seam, independent build/package/version/CI behavior,
signing and notarization ownership, updater and rollback proof, security and
vulnerability response, browser-data migration/recovery/export/restore rules,
rolling-upgrade compatibility, deprecation policy, and cross-repository
coordination. This scaffold records those prerequisites; it does not satisfy
them.

## Implementation status

- Package boundary: complete as a private scaffold.
- Contract package: complete as v1 JSON source and Node adapter.
- Contract package: additive v0.2.0 grant request/response schemas, canonical
  grant tokens, and shared fixtures are complete.
- JavaScript conformance: complete for the shared fixtures.
- Python conformance: complete for the shared fixtures.
- Guardian pure grant seam: test-proven process-local digest-only issuance,
  atomic one-use consumption, replay/expiry/scope/version/retention/budget
  rejection, and concurrency behavior.
- Electron runtime: bounded one-tab runtime plus capture preview implemented and live-test proven.
- Deterministic Guardian negotiation: implemented for test-only loopback stub.
- Trusted-main-process envelope construction and ephemeral attachment: implemented and live-test proven against the deterministic stub.
- Development-only Guardian HTTP adapter: test-proven behind
  `GUARDIAN_DEV_MODE=true`, `GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED=true`,
  and `GUARDIAN_EXPOSURE_MODE=local_safe`; it is absent from the default route
  surface and owns one process-local application store.
- Live production Guardian integration, supported grant issuance, Browser Host
  transport, and production authentication remain not implemented or proven.
- Durable browser persistence: not implemented; attachment receipts are explicitly `not_persisted`.
- Browser persistence: not implemented.
- Supported release: not qualified.

Gate C remains passed for architecture and ownership direction. Gate D remains
closed for supported product/release behavior; the bounded topology proof does
not widen current release truth. Current release truth remains
`docs/architecture/00-current-state.md`.

## Development-only Guardian HTTP adapter — 2026-08-01

The Guardian adapter is mounted at `/dev/browser-host/v1` only when all three
conditions hold: the existing `GUARDIAN_DEV_MODE` is true, the explicit
`GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED` setting is true, and exposure
resolves to `local_safe`. It is not mounted by default, in a supported profile,
or under non-local exposure.

`POST /attachment-grants` uses the existing Guardian current-user/authentication
dependency and returns the existing one-use grant response with `201` and
`Cache-Control: no-store`. The subject remains internal. `POST /attachments`
uses only the exact `BrowserHostAttachmentGrant` authorization scheme plus the
browser-host instance header; it does not accept or forward an API key, session
cookie, or JWT. Accepted requests return the existing content-free receipt with
`202` and `persistenceOutcome: not_persisted`.

The store is application-scoped, process-local, digest-only, and restart
volatile. Shutdown clears the app-owned records. Replay and expiry return
`409`; scope, version, retention, confirmation, and budget rejection return
bounded `403` receipts; malformed bodies are rejected before grant consumption.
The adapter does not call databases, Redis, queues, workers, providers,
command-bus routes, or storage writers. Raw attachment content, bearer
material, and internal subjects are excluded from logs, receipts, proof, and
retained state. This remains a development seam, not production Browser Host
integration or a supported release path.

Proof: [Guardian attachment HTTP adapter proof](./proofs/browser-host/2026-08-01-guardian-attachment-http-adapter/).

## Non-goals

- No live production Guardian route, production credentials, durable
  persistence, or supported release behavior.
- No React, Vite, database client, or general runtime framework.
- No live Guardian route, authentication, credential, provider invocation, or
  database persistence.
- No captured content transport, durable browser state, browser profile,
  cookies, history, bookmarks, downloads, or migration.
- No signing, notarization, updater, rollback, release, repository split, or
  current-state update.
- No promotion of proof-candidate code into production.

## ADR impact

This contract is aligned with ADR-054 and implements its first authorized
bounded topology and capture-preview proof slices. It preserves ADR-051's current private Chrome
side-panel boundary, ADR-021's web-agent boundary, ADR-039/040's access and
network-topology constraints, ADR-003's identity distinctions, and ADR-004/005's
control-plane and identity ownership. It does not modify any ADR.

## Next atomic task

Wire the production Browser Host main process to the development-only Guardian
attachment-grant adapter behind explicit local operator configuration, using the
one-use grant and no reusable Guardian credential.
