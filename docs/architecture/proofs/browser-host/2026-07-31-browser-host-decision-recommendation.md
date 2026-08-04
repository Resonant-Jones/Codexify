# Codexify Browser Host topology and release-ownership decision recommendation

## 1. Classification and status

- **Classification:** architecture-impact decision recommendation.
- **Status:** recommended for ADR drafting.
- **ADR readiness:** recommendation complete when accepted as the singular
  decision input to the future ADR.
- **Target future ADR:** `Codexify Browser Host Topology and Release Ownership`.
- **Observed next unused ADR number:** `054`; this document does not reserve or
  create that number.
- **Gate C:** closed.
- **Artifact posture:** pre-ADR deliberation artifact, not an accepted ADR,
  not runtime truth, not release qualification, and not permission to modify
  production code or proof evidence.
- **Evidence basis:** committed Browser Host packets, the comparative summary,
  the technology-neutral proof specification, current architecture contracts,
  and the current release-truth document.

## 2. Executive recommendation

Recommend that the future ADR:

1. Select the `bundled_chromium_electron` family for the Browser Host.
2. Create the production Browser Host first as an isolated application/package
   inside the Codexify monorepo.
3. Retain the production Tauri application as the trusted Codexify desktop
   shell and launcher, without placing arbitrary remote content inside its
   existing privileged command boundary.
4. Retain the Chrome extension as the optional Tier 0 side-panel continuity
   bridge, not as the canonical Tier 1 Browser Host.
5. Preserve Guardian as authentication, policy, persistence, task, and
   provider-execution authority.
6. Assign authority-bearing Browser Context Envelope construction and
   authenticated attachment orchestration to the trusted Browser Host main
   process, with Guardian validating the attachment and owning any later
   persistence decision.
7. Treat browser profiles and browser-generated state as Browser Host-owned
   product data, separate from Codexify identity and memory; keep durable
   browser data outside the first implementation stage.
8. Give the Browser Host an independent semantic component version and a
   versioned Guardian compatibility contract inside the monorepo.
9. Treat the Electron proof candidate as evidence and reference material, not
   automatically as production source.
10. Keep the immediate release posture at `development/internal unsigned
    proof`.
11. Defer a dedicated Browser Host repository until independent build, tests,
    packaging, CI, versioning, compatibility, release, signing, updater,
    rollback, migration, recovery, and security ownership are proven.

This recommendation is singular. It is not an accepted ADR, does not open
Gate C, and does not authorize implementation beyond the one post-ADR task in
section 22.

## 3. Decision principles

The recommendation applies these principles:

- Authority invariants are non-negotiable.
- Live proof is stronger than source inspection for runtime behavior.
- Repeatable automation is part of maintainability and security verification.
- Package success is not release proof.
- Performance cannot outweigh an authority violation.
- Candidate pass counts are evidence, not a weighted score.
- Repository extraction requires proven independent ownership.
- Current product roles should not be collapsed without necessity.
- Guardian remains the policy, persistence, identity, and execution authority.
- Browser content remains bounded evidence rather than an instruction or
  permission source.
- Capture, attachment, and durable persistence remain separate state changes.
- The current supported path remains governed by
  `docs/architecture/00-current-state.md`.

## 4. Candidate evidence interpretation

### OS-webview incumbent

The incumbent `os_webview_tauri` candidate is
`codexify-tauri-os-webview-incumbent-v1`, with terminal run
`tauri-proof-79fdb67b`. Its packet records 89 terminal cases: 34 passed, 42
inconclusive, 13 blocked, and 0 failed, with no invariant violation.

It proves that the incumbent family can build and package a proof artifact and
can preserve static least-privilege boundaries. It also records repository,
build, cleanup, accessibility, and bounded resource evidence. Its live
interaction-dependent claims remain substantially unresolved: renderer
credential isolation, native-authority isolation, capture, attachment,
navigation and origin integrity, sensitive-field exclusion, prompt-injection
containment, permission failure, and renderer-failure containment are
inconclusive or blocked where the approved macOS interaction driver was not
available.

The incumbent evidence is valuable for the trusted current desktop shell. It
does not justify stretching the existing privileged Tauri command boundary to
host arbitrary remote content, and it does not prove production Guardian
compatibility.

### Bundled Chromium candidate

The `bundled_chromium_electron` candidate is
`codexify-electron-bundled-chromium-v1`, with terminal run `harness-0288e8f5`.
Its final packet records 89 terminal cases: 85 passed, 4 inconclusive, 0
blocked, and 0 failed, with no invariant violation.

The four Electron inconclusive cases are:

- `accessibility_text_scaling`;
- `failure_malformed_response`;
- `resource_idle_memory`; and
- `resource_one_tab_memory`.

Under the same harness, the Electron packet exercises substantially more
mandatory cases through live trusted-shell interaction, including capture,
attachment, navigation, denial, stale-state, sensitive-field, prompt-
injection, and failure behavior. It supplies a deterministic bundled engine,
repeatable interaction evidence, and an explicit renderer-isolation posture.
It also introduces a larger runtime, dependency graph, packaging footprint,
and engine-security ownership burden.

The distinguishing factor is the kind and completeness of live evidence under
identical rules, not the numerical difference between the candidate pass
totals. The Electron candidate is proof material, not automatically accepted
production code.

## 5. Technology-family recommendation

Recommend the `bundled_chromium_electron` family for the future Browser Host.

This family fits the Browser Host role because the proof demonstrates a more
repeatable trusted-shell and remote-renderer interaction lane for the common
authority, capture, navigation, denial, and failure corpus. A bundled engine
reduces dependence on operating-system WebKit variation for the Browser Host
proof and makes the tested rendering surface more reproducible across the
declared candidate environment. Repeatable live automation is itself part of
the future security and regression-verification surface.

The accepted consequence is a larger runtime and a new vendor patch cadence.
That cost must remain visible in package ownership, security response,
supported-platform, signing, updater, rollback, and release planning. It is
not ignored or converted into a release claim.

Selecting a family for ADR consideration does not approve a package, qualify
a release, establish production Guardian compatibility, or promote the proof
candidate into production source.

## 6. Production Tauri relationship

The future ADR should retain production Tauri as the trusted Codexify desktop
shell and launcher.

- Tauri may later launch, discover, or coordinate with the Browser Host
  through explicit versioned contracts.
- The existing production Tauri application must not directly host arbitrary
  remote pages inside its privileged application webview.
- Tauri commands, trusted application credentials, and privileged desktop
  authority remain unavailable to remote browser content.
- The existing production Tauri shell remains unchanged by this
  recommendation.
- Any future Tauri-to-Browser Host coordination must identify caller,
  capability, consent, request identity, cancellation, and receipt semantics.

This preserves the current desktop role instead of making one privileged shell
simultaneously own trusted Codexify UI and arbitrary remote content.

## 7. Chrome-extension relationship

The future ADR should retain the private Chrome extension as an optional Tier 0
continuity bridge.

- Preserve its side-panel Guardian workflow and current authentication/storage
  boundary under ADR-051.
- Do not widen the extension into the canonical Tier 1 Browser Host.
- Retain it during transition and as an optional browser-native companion.
- Treat any Web Store distribution, enhanced page observation, or broader
  extension capability as a separate proof and architecture task.
- Do not count extension continuity as Browser Host implementation proof.

## 8. Repository recommendation

Recommend an **isolated Browser Host application/package in the Codexify
monorepo** for the first production implementation stage.

The monorepo keeps the Guardian contract, Browser Context Envelope schema,
proof fixtures, and implementation review synchronized while the ownership
boundary is still being established. The Browser Host must nevertheless have
its own:

- source root;
- package manifest and lockfile;
- tests and proof entry points;
- build and package commands;
- artifact identity and ownership;
- independent semantic component version; and
- explicit Guardian compatibility contract.

The package must not import production Tauri commands or privileged
application internals. The proof-candidate source is not silently promoted to
production. A dedicated repository is deferred until the extraction
prerequisites in section 9 are proven.

## 9. Future extraction prerequisites

Before a dedicated Browser Host repository may be created, the following must
be proven and assigned:

- independent build;
- independent tests;
- independent package production;
- independent CI;
- independent release version;
- stable versioned Guardian client contract;
- stable versioned Browser Context Envelope schema;
- compatibility matrix;
- feature negotiation;
- deprecation policy;
- rolling-upgrade proof;
- signing ownership;
- updater ownership;
- rollback ownership;
- Chromium/Electron security-patch ownership;
- migration and recovery ownership;
- cross-repository vulnerability response;
- export and restore policy; and
- documented issue, review, compatibility, and release coordination.

Until these prerequisites are proven, the monorepo package remains the source
and release coordination boundary. Repository extraction is not implied by
technology selection.

## 10. Guardian and Browser Context Envelope ownership

The future ADR should preserve the following authority split:

- Guardian remains policy and persistence authority.
- Guardian remains authentication, task, and provider-execution authority.
- The trusted Browser Host main process owns credentials needed for its
  authenticated Guardian communication.
- The trusted Browser Host main process constructs authority-bearing Browser
  Context Envelope metadata.
- The remote renderer contributes bounded extracted content only.
- Guardian validates the attachment and determines any later persistence.
- Capture does not imply attachment.
- Attachment does not imply durable persistence.
- Capture and request identifiers remain correlated and inspectable.
- Capture failure or renderer failure must leave ordinary Guardian
  communication available or report a bounded degraded state.

The remote renderer receives no Guardian credentials, unrestricted native APIs,
direct persistence authority, or identity/memory mutation authority. The
Browser Host main process may orchestrate a user-initiated capture and one
authenticated attachment attempt, but it does not become the source of truth
for Guardian policy or durable application state.

## 11. Browser-data ownership

Browser engine cache, ephemeral session state, and temporary capture state are
owned by the Browser Host and remain separate from Codexify identity and
memory.

- The first production stage uses isolated, non-persistent browser state.
- Remote page storage does not silently enter Guardian.
- Durable cookies, profiles, history, bookmarks, downloads, and sessions are
  deferred.
- Each durable browser-data feature requires its own retention, deletion,
  migration, export, restore, encryption, and recovery contract.
- Codexify account export does not automatically include browser state until
  that relationship is explicitly governed.
- Browser state must not silently mutate identity, memory, account scope, or
  Guardian persistence.

## 12. Version and compatibility recommendation

The future ADR should require:

- an independent semantic component version for the Browser Host;
- a versioned Guardian compatibility protocol;
- an explicit Browser Context Envelope schema version;
- feature negotiation;
- fail-closed behavior for incompatible versions;
- inspectable minimum and maximum compatible versions;
- documented deprecation windows; and
- rolling-upgrade proof before independent release.

These are recommendation-level contracts only. This task does not implement
the protocol, schema, feature negotiation, or compatibility machinery.

## 13. Release and operational ownership recommendation

The recommended role domains are:

| Responsibility | Recommended owner domain | Current status |
| --- | --- | --- |
| Browser Host package | Browser Host subsystem owner | To be formally assigned |
| Guardian protocol | Guardian runtime owner | Existing authority domain; implementation contract to be versioned |
| Browser Context Envelope | Shared Browser Host / Guardian contract owner | To be formally assigned |
| Chromium and Electron patching | Browser Host security and release owner | `unassigned prerequisite` |
| Signing and notarization | Release engineering | `unassigned prerequisite` |
| Updater | Browser Host release engineering | `unassigned prerequisite` |
| Rollback | Browser Host release engineering | `unassigned prerequisite` |
| Browser data | Browser Host subsystem owner | To be formally assigned before durable state |
| Export and restore | Codexify data-portability owner | To be formally assigned before durable state |
| Vulnerability response | Browser Host security owner | `unassigned prerequisite` |
| Supported platforms | Browser Host release owner | `unassigned prerequisite` |

No individual names are invented by this recommendation. Where a role is not
formally established, it remains an `unassigned prerequisite` rather than an
implicit responsibility.

## 14. Immediate release posture

Recommend:

`development/internal unsigned proof`

This posture permits:

- local development;
- architecture implementation;
- harness regression; and
- internal proof builds.

It does not permit:

- private beta distribution;
- public distribution;
- production signing;
- automatic updating;
- claims of browser-data durability; or
- replacement of the current supported Codexify path.

The current supported release remains the local Docker Compose, local-first
beta described by `docs/architecture/00-current-state.md`.

## 15. Proof code versus production code

Both candidate packets remain immutable evidence. The Electron candidate may
inform production implementation, but candidate code is not automatically
accepted as production code.

Production implementation must use an explicitly owned source root and must
have its own tests, threat review, dependency review, package identity, and
supported-path proof. The proof packet, candidate manifest, and comparative
summary must remain unchanged by implementation work.

The `proof_complete` status means the candidate packet has terminal evidence
for the fixed corpus. It does not mean that the candidate is a supported
Browser Host, that the package is signed, or that the candidate is ready for
private beta.

## 16. Accepted consequences

### Positive

- deterministic bundled rendering engine;
- repeatable live proof and regression lane;
- explicit renderer isolation;
- clear Browser Host ownership boundary;
- independent Browser Host evolution without contaminating Tauri authority;
- monorepo synchronization of contracts and proof fixtures during incubation.

### Negative

- bundled engine footprint;
- additional JavaScript dependency graph;
- duplicated desktop-shell concepts;
- Chromium security-response obligations;
- separate packaging, signing, updater, and rollback burden; and
- possible higher memory use.

### Neutral continuity decisions

- Tauri remains the trusted Codexify shell.
- The Chrome extension remains the Tier 0 continuity bridge.
- Guardian remains authority.
- Gate D and release qualification remain future work.

## 17. Rejected or deferred alternatives

### Extension-only Browser Host

Rejected for the canonical Browser Host role because the extension is a Tier 0
continuity bridge rather than the isolated Tier 1 host boundary. It remains
available as an optional companion.

### Production Tauri directly hosting arbitrary remote content

Rejected for this stage because the existing shell is privileged and the
incumbent candidate left live interaction-dependent claims unresolved. Tauri
remains the trusted shell and launcher.

### Dedicated Browser Host repository now

Deferred because independent release, protocol, compatibility, recovery,
signing, updater, rollback, and security ownership are not yet proven.

### Custom Chromium or CEF

Deferred because the additional engine, packaging, security, and ownership
burden is not justified by the current requirements or evidence.

### No Browser Host

Rejected because it would not satisfy the intended Browser Workspace
direction represented by the common proof surface and Campaign.

## 18. Residual uncertainties and closure phases

The following residual uncertainties remain explicit:

| Uncertainty | Closure phase |
| --- | --- |
| Four Electron inconclusive cases: text scaling, malformed response, idle memory, and one-tab memory | May remain open during the first package/contract scaffold; must be closed at the appropriate supported-platform or release-proof gate before corresponding claims |
| Production Guardian integration | Must close before any production Browser Host interaction or private beta |
| Production source organization and package boundary | Must close in the first post-ADR implementation task |
| Final IPC schema and versioned Guardian/Envelope contracts | Must close in the first post-ADR implementation task before browser interaction implementation |
| Signing and notarization | Must close before private beta |
| Updater and rollback | Must close before private beta |
| Durable browser-data contracts | May remain open during the first scaffold; must close before any durable profile, cookie, history, bookmark, download, or session claim |
| Migration, export, restore, and browser-data recovery | Must close before durable browser data or private beta |
| Supported-platform qualification | Must close before private beta |
| Accessibility across supported platforms | May remain open during the first scaffold; must close before private beta |
| Resource posture outside the proof machine | May remain open during the first scaffold; must close before performance or private-beta claims |
| Vulnerability response and incident ownership | Must close before private beta |

These closure phases do not authorize the work. They identify which unknowns
belong to the package/contract scaffold, product proof, or release gate.

## 19. Proposed future ADR decisions

| ADR axis | Singular proposed decision |
| --- | --- |
| Technology family | Select `bundled_chromium_electron` for the Browser Host. |
| Tauri relationship | Retain production Tauri as the trusted Codexify desktop shell and launcher; do not host arbitrary remote content inside its privileged webview. |
| Extension relationship | Retain the Chrome extension as the optional Tier 0 continuity bridge, not the canonical Tier 1 Browser Host. |
| Guardian boundary | Guardian remains authentication, policy, persistence, task, and provider-execution authority. |
| Repository topology | Incubate an isolated Browser Host application/package in the Codexify monorepo first. |
| Package ownership | Browser Host subsystem owner owns the package source, tests, artifacts, and component release surface. |
| Version ownership | Browser Host owns an independent semantic component version governed by a versioned Guardian compatibility protocol. |
| Engine update ownership | Browser Host security and release owner owns Electron/Chromium patch response; until assigned, this is an `unassigned prerequisite`. |
| Signing ownership | Release engineering owns signing and notarization; until assigned, this is an `unassigned prerequisite`. |
| Updater ownership | Browser Host release engineering owns updater behavior; until assigned, this is an `unassigned prerequisite`. |
| Rollback ownership | Browser Host release engineering owns rollback behavior; until assigned, this is an `unassigned prerequisite`. |
| Browser-profile ownership | Browser Host owns isolated browser state; durable profiles and related data remain deferred behind separate contracts. |
| Browser Context Envelope ownership | A shared Browser Host / Guardian contract owner owns the versioned envelope; the trusted Browser Host main process constructs metadata and Guardian validates attachment. |
| Proof-versus-product status | Candidate packets remain immutable proof evidence; production code requires a new owned source root, tests, threat review, and supported-path proof. |
| Extraction conditions | Defer a dedicated repository until the section 9 independent build, contract, compatibility, release, recovery, and security prerequisites are proven. |
| Immediate release posture | `development/internal unsigned proof`; no private beta, public distribution, signing, updater, or durable browser-data claim. |
| First implementation stage | Establish the production Browser Host package boundary and versioned Guardian/Browser Context contracts without implementing the full browser product. |

No row defers the decision to a later choice. Ownership rows identify a role
domain and label missing formal assignment as an `unassigned prerequisite`.

## 20. ADR drafting readiness

This recommendation is ready to serve as the singular decision input for the
future ADR because:

- the recommendation is singular;
- every required decision axis has one proposed answer;
- the recommendation is grounded in the committed comparative packets and
  current contracts;
- the evidence distinction between proof and product is explicit;
- residual uncertainties are classified by closure phase; and
- the future ADR can independently verify the evidence and record acceptance.

The future ADR must still independently verify the comparative summary,
candidate receipts, authority contracts, ownership prerequisites, and current
release truth before accepting the decision. Gate C remains closed until that
ADR is accepted.

## 21. Exactly one next atomic task

**Author and adopt ADR-054, `Codexify Browser Host Topology and Release
Ownership`, using this decision recommendation as its singular decision input.**

The ADR task must re-resolve the next unused ADR number before creating the ADR
file. This recommendation does not generate, reserve, or execute the ADR.

## 22. Evidence and validation posture

- Comparative synthesis commit: `af7f4738a3d17abb7da3d4cfef711c5808878a45`.
- Tauri run: `tauri-proof-79fdb67b`, `proof_complete`, 34 passed, 42
  inconclusive, 13 blocked, 0 failed, no invariant violations.
- Electron run: `harness-0288e8f5`, `proof_complete`, 85 passed, 4
  inconclusive, 0 blocked, 0 failed, no invariant violations.
- The comparative summary remains `ADR_READY` and intentionally
  non-decisional; this document supplies the singular recommendation.
- Candidate proof packets and the comparative summary are immutable evidence
  and were not modified by this task.
- No candidate was rerun, no external research was performed, and no runtime
  or production integration was attempted.

## 23. ADR impact and non-claims

- **Classification:** prepares a required new ADR.
- **ADR created, accepted, modified, or superseded:** none.
- This document is the singular recommendation input for the future ADR.
- Gate C remains closed.
- No production Browser Host exists.
- No candidate code is production code automatically.
- No signed or supported Browser Host exists.
- No production Guardian integration, updater, rollback, migration, or
  private-beta qualification exists.
- No current-state release truth is widened.
- No repository split, package scaffold, versioned protocol implementation,
  signing, updater, release, or implementation is authorized by this document.

## 24. Source evidence

- `docs/architecture/proofs/browser-host/2026-07-31-browser-host-comparative-summary.md`
- `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/candidate-proof.md`
- `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/candidate-proof.json`
- `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/candidate-proof.md`
- `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/candidate-proof.json`
- `docs/architecture/browser-host-comparative-proof-harness-spec.md`
- `docs/architecture/browser-authority-and-context-boundary-contract.md`
- `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
- `docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md`
- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/adr/003-message-identity-vs-request-identity.md`
- `docs/architecture/adr/004-retrieval-policy-as-control-plane.md`
- `docs/architecture/adr/005-Runtime-Mode-and-Account-Boundary-Invariants.md`
- `docs/architecture/adr/021-web-agent-boundary-and-retrieval-contract.md`
- `docs/architecture/adr/039-operator-user-access-boundary.md`
- `docs/architecture/adr/040-network-profile-topology-resolution-contract.md`
- `docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md`
