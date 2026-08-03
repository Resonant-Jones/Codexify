# ADR-054: Codexify Browser Host Topology and Release Ownership

## Status

Accepted

## Date

2026-07-31

## Classification

Requires new ADR.

## Decision owners

- Human architecture authority: accepts the architecture decision and any
  later superseding decision.
- Guardian runtime owner: owns Guardian authentication, policy, persistence,
  task, provider-execution, and compatibility boundaries.
- Browser Host subsystem owner: owns the future Browser Host package and
  product implementation boundary; formal assignment remains a prerequisite.
- Browser Host release and security owners: own packaging, engine updates,
  signing, updater, rollback, vulnerability response, and supported-platform
  qualification; formal assignments remain prerequisites where stated below.

No individual names are implied by these role domains.

## Supersedes

None.

## Related ADRs

- [ADR-003: Message Identity vs Request Identity](./003-message-identity-vs-request-identity.md)
- [ADR-004: Retrieval Policy as Control Plane](./004-retrieval-policy-as-control-plane.md)
- [ADR-005: Runtime Mode and Account Boundary Invariants](./005-runtime-mode-and-account-boundary-invariants.md)
- [ADR-021: Web Agent Boundary and Retrieval Contract](./021-web-agent-boundary-and-retrieval-contract.md)
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md)
- [ADR-040: Network Profile Topology Resolution Contract](./040-network-profile-topology-resolution-contract.md)
- [ADR-051: Chrome Side-Panel Dual-Auth Client Contract](./051-chrome-side-panel-dual-auth-client-contract.md)

## Related contracts and evidence

- [Browser Authority and Context Boundary Contract](../browser-authority-and-context-boundary-contract.md)
- [Comparative Browser Host Proof Harness Specification](../browser-host-comparative-proof-harness-spec.md)
- [Canonical Token Philosophy](../canonical-token-philosophy.md)
- [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Browser Host comparative summary](../proofs/browser-host/2026-07-31-browser-host-comparative-summary.md)
- [Browser Host decision recommendation](../proofs/browser-host/2026-07-31-browser-host-decision-recommendation.md)
- [Tauri incumbent proof packet](../proofs/browser-host/2026-07-30-tauri-incumbent/candidate-proof.md)
- [Electron bundled Chromium proof packet](../proofs/browser-host/2026-07-31-electron-bundled-chromium/candidate-proof.md)

## Context

Codexify has a private Chrome side-panel client and a production Tauri
application, but it does not yet have a supported Codexify-owned Browser Host.
The side panel provides Tier 0 continuity; it does not establish a canonical
Tier 1 one-tab Browser Workspace with an owned renderer, capture boundary,
packaging surface, and recovery model.

The production Tauri application is a trusted bundled Codexify client with a
privileged command boundary. It was not designed to absorb arbitrary remote
content. Reusing that boundary for remote pages would combine trusted
Codexify UI authority and untrusted browser content without the independent
host surface required by the Browser Authority and Context Boundary Contract.

Two proof-only candidate families were examined under one technology-neutral
harness:

- The OS-webview/Tauri incumbent reached `proof_complete` with 89 terminal
  cases: 34 passed, 42 inconclusive, 13 blocked, 0 failed, and no invariant
  violation.
- The bundled-Chromium/Electron candidate reached `proof_complete` with 89
  terminal cases: 85 passed, 4 inconclusive, 0 blocked, 0 failed, and no
  invariant violation.

The counts are descriptive evidence, not a weighted score or selection
formula. The Electron packet provides substantially broader live
trusted-shell interaction evidence under the identical corpus, while the
Tauri packet preserves valuable build, packaging, static-boundary, cleanup,
and incumbent-shell evidence with larger live interaction gaps.

The comparative summary intentionally remained non-decisional. The separate
decision recommendation converted its evidence into one recommendation
covering technology, topology, ownership, compatibility, release posture, and
the first implementation boundary. This ADR accepts that recommendation while
preserving the distinction between architecture acceptance, implementation,
and release qualification.

## Accepted decision

### Technology family

Codexify adopts Electron with bundled Chromium for the future Browser Host.
The canonical family token is `bundled_chromium_electron`.

This is an architecture selection, not release approval. The Electron proof
candidate remains evidence and reference material; its source is not
automatically production source.

The selected family fits the Browser Host role because it supplied a more
repeatable live trusted-shell and remote-renderer interaction lane for the
common authority, capture, navigation, denial, stale-state, sensitive-field,
prompt-injection, attachment, and failure corpus. The deterministic bundled
engine supports repeatable regression and security verification.

The accepted costs are a larger runtime footprint, an additional JavaScript
dependency graph, Electron/Chromium patch responsibility, packaging burden,
and potentially higher process or memory cost. These costs remain explicit
release and ownership prerequisites.

Electron is selected because the type and completeness of live evidence better
match the Browser Host role. It is not selected merely because its passed-case
total is larger.

### Repository topology

The production Browser Host will begin as an isolated application/package
inside the Codexify monorepo.

The package must have its own:

- source root;
- package manifest and lockfile;
- tests and proof entry points;
- build and package commands;
- artifact identity and ownership; and
- independent semantic component version.

The package must not import production Tauri command implementations or other
privileged application internals. The package boundary must expose an
explicit, versioned Guardian compatibility contract. Monorepo incubation does
not make the Browser Host a supported runtime.

### Production Tauri relationship

Production Tauri remains the trusted Codexify desktop shell and launcher.

- Arbitrary remote pages must not be loaded inside the current privileged
  Tauri renderer.
- Tauri commands, trusted application credentials, and privileged desktop
  authority remain unavailable to remote browser content.
- Tauri may later discover, launch, or coordinate with the Browser Host through
  explicit versioned contracts.
- No immediate production Tauri change is authorized by this ADR.

### Chrome-extension relationship

The Chrome extension remains the optional Tier 0 side-panel continuity bridge.

- Its existing side-panel Guardian workflow remains governed by ADR-051.
- It is not the canonical Browser Host.
- It remains available during Browser Host incubation and transition.
- Enhanced page observation, Web Store distribution, or broader extension
  capabilities require separate proof and governance.

### Guardian boundary

Guardian remains authentication, policy, persistence, task,
provider-execution, and durable-state authority.

- The trusted Browser Host main process owns Guardian credentials needed for
  authenticated communication.
- Remote renderers never receive Guardian credentials.
- Remote renderers never receive unrestricted native APIs, Command Bus
  authority, direct persistence authority, or identity/memory mutation
  authority.
- Browser content remains evidence rather than policy or permission.
- Browser Host failures must leave ordinary Guardian communication available or
  expose a bounded degraded state.

### Browser Context Envelope ownership

The trusted Browser Host main process constructs authority-bearing Browser
Context Envelope metadata. Remote renderers contribute only bounded extracted
content.

- Capture requires explicit user initiation.
- Attachment requires a separate explicit action.
- Guardian validates attachment and decides any later persistence.
- Capture does not imply attachment.
- Attachment does not imply durable persistence.
- Capture and request identifiers remain correlated and inspectable.
- The Browser Context Envelope requires an explicit schema version and a
  versioned Guardian compatibility contract.

### Browser-data ownership

Browser engine cache, ephemeral session state, and temporary capture state
belong to the Browser Host subsystem. They are not Codexify identity or
memory.

The first production stage uses isolated, non-persistent browser state. Durable
profiles, cookies, sessions, history, bookmarks, downloads, and
password-management state are deferred. Each future durable browser-data
feature requires explicit retention, deletion, encryption, migration,
recovery, export, and restore governance. Browser state must not silently
mutate identity, memory, account scope, or Guardian persistence.

### Version and compatibility

- The Browser Host has an independent semantic component version.
- Guardian integration uses a versioned compatibility contract.
- The Browser Context Envelope has an explicit schema version.
- Feature negotiation is required.
- Incompatible versions fail closed.
- Supported minimum and maximum protocol versions are inspectable.
- Deprecation windows are documented.
- Rolling-upgrade proof is required before independent release.

### Immediate release posture

The immediate posture is:

`development/internal unsigned proof`

This permits local implementation, proof runs, harness regression, and
internal architecture testing. It does not permit private beta distribution,
public distribution, production signing, automatic updating, or browser-data
durability claims. It does not replace the current supported Codexify path.

## Release ownership

| Responsibility | Owner domain | Status |
| --- | --- | --- |
| Browser Host package and component version | Browser Host subsystem owner | Role assignment required |
| Guardian protocol | Guardian runtime owner | Existing authority domain; contract versioning required |
| Browser Context Envelope | Shared Browser Host / Guardian contract owner | Role assignment required |
| Electron and Chromium patch monitoring | Browser Host security and release owner | `unassigned prerequisite` |
| Build and packaging | Browser Host release owner | Role assignment required |
| Signing and notarization | Release engineering | `unassigned prerequisite` |
| Updater | Browser Host release engineering | `unassigned prerequisite` |
| Rollback | Browser Host release engineering | `unassigned prerequisite` |
| Browser profiles and browser-data lifecycle | Browser Host subsystem owner | Role assignment required before durable state |
| Export and restore | Codexify data-portability owner | Role assignment required before durable state |
| Vulnerability response | Browser Host security owner | `unassigned prerequisite` |
| Supported platforms | Browser Host release owner | `unassigned prerequisite` |
| Crash reporting | Browser Host operations owner | `unassigned prerequisite` |

No individual names are fabricated. A role that has not been formally
established remains an `unassigned prerequisite` rather than an implicit
responsibility.

## Security-update policy

Electron and bundled Chromium updates are owned by Codexify rather than by the
operating system. The Browser Host security owner must monitor supported
Electron releases and Chromium vulnerability advisories.

- Unsupported Electron versions block release qualification.
- Critical engine vulnerabilities may block distribution until patched or
  explicitly risk-accepted through later governance.
- Major Electron or Chromium upgrades require harness regression,
  authority-boundary proof, capture and attachment proof, packaging proof,
  accessibility proof, and resource reassessment.
- Patch response, vulnerability response, and supported-platform ownership
  remain release prerequisites until formally assigned.

## Repository-extraction prerequisites

Before a dedicated Browser Host repository may be created, Codexify must prove
and assign:

- stable versioned Guardian client contract;
- stable Browser Context Envelope schema;
- canonical status and failure tokens;
- feature negotiation;
- compatibility matrix;
- generated or maintained client SDK;
- independent contract-test suite;
- independent build;
- independent package;
- independent CI;
- independent release version;
- signing ownership;
- updater ownership;
- rollback ownership;
- security-patch ownership;
- vulnerability-response process;
- browser-data migration and recovery policy;
- account export and restore policy;
- rolling-upgrade proof;
- deprecation policy; and
- cross-repository issue and release coordination.

Technology selection does not authorize repository extraction.

## Rationale

The Tauri incumbent successfully built, packaged, and launched its proof
artifact, preserved static least-privilege boundaries, produced no invariant
violation, and remains appropriate as the trusted existing shell. Its packet
retained substantial uncertainty around live renderer interaction, capture,
navigation, attachment, and failure containment.

The Electron candidate exercised substantially more mandatory behavior through
live trusted-shell automation. It more completely proved navigation, capture,
separate attachment, denial, stale-state rejection, sensitive-field
exclusion, prompt-injection containment, and failure behavior under the same
harness. It provides a deterministic bundled engine and repeatable regression
lane while introducing accepted costs in binary size, memory, dependencies,
packaging, and security ownership.

The selection follows the kind and completeness of live evidence required for
the Browser Host role. It does not treat pass totals as a scoring formula and
does not convert proof completion into release approval.

## Rejected and deferred alternatives

### Extension-only Browser Host

Rejected as the canonical Browser Host. The extension remains the Tier 0
continuity bridge and optional browser-native companion.

### Production Tauri directly hosting arbitrary remote content

Rejected for the first Browser Host implementation. The existing Tauri shell
is privileged, and remote content must not be placed inside its current
command boundary. Tauri remains the trusted shell and launcher.

### OS-webview/Tauri Browser Host family

Not selected for this decision cycle. It may be reconsidered if later
decision-grade live evidence closes its interaction and containment gaps
without weakening authority boundaries.

### Dedicated Browser Host repository now

Deferred until the repository-extraction prerequisites are proven.

### Custom Chromium, CEF, or bespoke browser engine

Deferred because current requirements do not justify the additional ownership,
maintenance, security, and packaging burden.

### No Browser Host

Rejected because it would not satisfy the intended Browser Workspace and
page-evidence direction represented by the Campaign and common proof surface.

### Private or public release now

Rejected because signing, updater, rollback, browser-data, migration, and
operational ownership are unproven.

## Consequences

### Positive

- explicit Browser Host technology;
- deterministic engine behavior;
- repeatable live regression;
- clear remote-renderer boundary;
- preserved Guardian authority;
- preserved Tauri and extension roles;
- explicit release and security ownership domains; and
- synchronized contracts and proof fixtures during monorepo incubation.

### Negative

- bundled runtime footprint;
- Electron and Chromium patch responsibility;
- additional JavaScript dependency graph;
- separate packaging, signing, updater, rollback, and incident-response
  burden;
- temporary duplication of desktop-shell concepts; and
- potentially higher process and memory cost.

### Neutral continuity decisions

- Production Tauri remains unchanged.
- The extension remains available.
- Candidate packets remain immutable evidence.
- No release posture changes automatically.
- Repository extraction remains possible later, subject to its prerequisites.

## Implementation authorization boundary

ADR-054 authorizes future work on:

- an isolated production Browser Host package inside the monorepo;
- versioned Guardian compatibility contracts;
- a versioned Browser Context Envelope contract;
- the selected trusted main-process, shell, and remote-renderer topology; and
- the first one-tab implementation stages.

ADR-054 does not authorize:

- a full multi-tab browser;
- history;
- bookmarks;
- password management;
- durable cookies or profile migration;
- autonomous browser actions;
- production signing;
- automatic updating;
- private beta;
- public release;
- silent replacement of Tauri or the extension; or
- repository extraction.

## Release gates

### Gate C: Repository split and ownership direction

**Passed by acceptance of ADR-054.**

This means the Browser Host architecture and ownership direction are accepted:
Electron/bundled Chromium is selected, the monorepo-first isolated package is
the incubation boundary, Tauri and the extension retain their stated roles,
and Guardian remains authority. It does not mean that a repository split is
authorized or that independent-release prerequisites are complete.

### Next implementation gate

**Closed.** It requires the production Browser Host package boundary and
versioned Guardian/Browser Context contract scaffold. It does not authorize a
full browser product implementation.

### Later one-tab proof gate

Requires supported-path Guardian integration, live credential-isolation and
native-authority proof, capture and attachment proof, accessibility, failure
recovery, cleanup, and resource proof.

### Private-beta gate

Requires a signed and notarized package, updater and rollback proof,
Electron/Chromium security-response ownership, browser-data ownership and
recovery rules, migration and compatibility proof, and supported-platform
qualification.

### Public release

Explicitly deferred to a later release-readiness decision.

## Supersession and reconsideration

This decision requires review if any of the following occurs:

- Electron or its bundled Chromium version loses support;
- required security patches cannot be delivered within the response window;
- renderer isolation cannot be maintained;
- production Guardian integration would require weakening the authority
  contract;
- resource use becomes unacceptable;
- accessibility requirements cannot be met;
- monorepo release coupling becomes unmanageable;
- supported-platform requirements change materially;
- a later candidate provides superior decision-grade evidence; or
- browser-data requirements materially change the topology.

A superseding ADR must preserve the evidence distinction between candidate
proof, architecture acceptance, implementation, and release qualification.

## Proof code versus production code

The candidate packets remain immutable evidence. The Electron candidate may
inform production implementation, but candidate code is not automatically
accepted as production code.

Production implementation requires an explicitly owned source root, its own
tests, threat review, dependency review, package identity, and supported-path
proof. The proof packet, comparative summary, and decision recommendation are
not implementation files.

## Explicit non-claims

ADR-054:

- does not implement a production Browser Host;
- does not approve private or public release;
- does not create a signed package;
- does not prove live production Guardian compatibility;
- does not create durable browser profiles or migration;
- does not create browser actions or autonomous browsing;
- does not split the repository;
- does not alter candidate evidence; and
- does not automatically promote proof code into supported product code.

Acceptance of ADR-054 does not widen the current release truth in
`docs/architecture/00-current-state.md`.

## Exactly one next atomic task

Establish the production Browser Host package boundary and versioned
Guardian/Browser Context contracts without implementing the full browser
product.

This is the sole next implementation task. It must preserve the authority
invariants, keep the immediate posture at development/internal unsigned proof,
and stop before full browser-product behavior, durable browser data, signing,
updater, rollback, or release work.

## Documentation follow-through

The architecture routing surfaces must point to this accepted ADR while
preserving the distinction between future architecture and current runtime:

- `docs/architecture/adr/adr-index.md` indexes ADR-054 and its accepted
  decision.
- `docs/architecture/README.md` routes Browser Host topology and ownership
  questions to ADR-054, the recommendation, the comparative evidence, and the
  proof methodology.
- `docs/architecture/kb-validity-matrix.md` records ADR-054 as
  `supplementary_verify_against_code`, unsafe for runtime and UI diagrams.
- `docs/architecture/browser-host-comparative-proof-harness-spec.md` records
  the accepted decision status without changing normative proof rules.
- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md` records Gate C as passed for
  architecture direction while keeping the next implementation gate closed.
- `docs/architecture/00-current-state.md` remains unchanged and authoritative
  for supported release truth.
