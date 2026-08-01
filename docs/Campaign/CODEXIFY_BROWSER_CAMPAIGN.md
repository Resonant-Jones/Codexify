# Codexify Browser Campaign

## Campaign status

- Execution lane: `architecture-impact`
- Task kind: campaign governance documentation
- Status: `proposed`
- Initial repository: Codexify
- Runtime effect: none
- Architecture review: required before Browser Host implementation or repository separation

This Campaign establishes a prerequisite-ordered governance spine for preserving
the current browser-assisted workflow and evaluating a Codexify-owned browser
surface. It does not implement, select, relocate, package, or release a browser
runtime.

## Problem statement

Codexify already has a private Chrome side-panel client and a documented browser
boundary, but the broader Browser product has no accepted host technology,
repository topology, renderer authority model, cross-repository protocol, or
release contract. Treating a generated directory, a planning document, or a
working browser proof as an implementation boundary would make later security
and ownership decisions depend on assumptions.

The Campaign therefore begins with repository evidence. It preserves the
existing extension while establishing the decisions and proof required before
Codexify adds a Browser Host, browser actions, durable browser state, or a
separate repository.

## User and workflow continuity goal

Preserve the operator's current Atlas-assisted browser workflow long enough to
identify its essential user-visible capabilities, then introduce the smallest
Codexify-owned browser surface that can be built, secured, recovered, and
released without weakening Guardian or identity boundaries.

Continuity means preserving the useful workflow, not importing hidden browser
state or claiming that an Atlas export has completed. Any future import must
have its own provenance, consent, compatibility, and recovery contract.

## Evidence posture

### Test-proven

- The repository contains focused tests for the Chrome side-panel client.
- Existing repository documentation records that the original unpacked
  side-panel path rendered and could participate in the Codexify chat workflow.
  This Campaign does not extend that proof to a Browser Host or supported beta
  client.

### Proven code path and repository evidence

- `frontend/chrome-extension/manifest.json` declares the private Manifest V3
  side panel.
- `frontend/chrome-extension/service-worker.ts` owns toolbar-to-side-panel
  behavior.
- `frontend/chrome-extension/src/` contains the side-panel React client and its
  focused tests.
- `frontend/vite.chrome-extension.config.ts` declares
  `frontend/chrome-extension` as its extension root and
  `frontend/dist/chrome-extension` as its build output.
- `frontend/package.json` declares `build:chrome-extension` and
  `test:chrome-extension`.
- `.gitignore` ignores `dist/`, which covers the extension build output.

These observations are pre-read evidence for shaping Task 01. Task 01 remains
responsible for producing the complete, reviewable inventory proof.

### Proven architecture evaluation

- Stage 3 historically produced
  `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
  at commit `1cbf68113b9113faa907c22d868248609f49f9a5`.
- Its then-current ADR-readiness result was `PROOF_REQUIRED`.
- No technology or repository topology was selected.
- The completed comparative evidence and subsequent ADR-054 supersede that
  pending-evidence state; the earlier evaluation itself did not accept a
  topology decision.
- `docs/architecture/browser-host-comparative-proof-harness-spec.md` defines
  the normative, technology-neutral comparison method.

### Incumbent-family proof evidence

- Shared scaffold prerequisite commit:
  `eb6eb416d0f70d6b68bd582cb9ffdb82c27e5678`.
- Incumbent proof-only source:
  `browser_host_candidates/tauri/`.
- Harness adapter:
  `scripts/browser_host_harness/adapters/tauri_incumbent.py`.
- Terminal packet:
  `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/`.
- Terminal run `tauri-proof-79fdb67b` is `proof_complete` for evidence
  coverage: 89 mandatory cases are terminal (34 `passed`, 42 `inconclusive`,
  13 `blocked`), with no failed case and no invariant violation.
- The proof source baseline is
  `eb6eb416d0f70d6b68bd582cb9ffdb82c27e5678`; the atomic integration commit is
  the commit containing the packet and is reported by Git history and task
  closeout.
- The result does not select Tauri, widen release truth, prove production
  Guardian compatibility, or open Gate C. The comparative update below records
  the final cross-family evidence.

### Materially different-family proof evidence (historical intermediate state)

- Candidate source: `browser_host_candidates/electron/`.
- Candidate family: `bundled_chromium_electron`.
- Candidate adapter: `scripts/browser_host_harness/adapters/electron_bundled_chromium.py`.
- Terminal packet:
  `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/`.
- Intermediate proof source commit: `59617cf32f40928db969f4455459923f9558e268`.
- Intermediate packet status: `environment_blocked`. The candidate-local build,
  dependency verification, unsigned arm64 package attempt, receipt assembly,
  and cleanup completed; Playwright Electron could not establish a meaningful
  Electron runtime on the proof host. No alternate automation framework was
  substituted, no invariant violation was recorded, and live interaction
  cases remain terminally `inconclusive`.
- Electron `43.2.0` bundles Chromium `150.0.7871.129`, Node `24.18.0`, and V8
  `15.0.1240245-electron.0`; Playwright `1.62.1` remains an experimental,
  proof-only driver.
- This intermediate packet is superseded by the final packet and is not part
  of the comparative totals below.

### Comparative terminal evidence update — 2026-07-31

- Incumbent OS-webview candidate: implementation commit
  `59617cf32f40928db969f4455459923f9558e268`, packet
  `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/`, run
  `tauri-proof-79fdb67b`, status `proof_complete`.
- Final bundled-Chromium candidate: commits `37db52dd1`, `3777171c4`, and
  `3854cfd32`, packet
  `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/`,
  run `harness-0288e8f5`, status `proof_complete`.
- The incumbent totals are 34 `passed`, 42 `inconclusive`, 13 `blocked`, and
  0 `failed`; the final bundled-Chromium totals are 85 `passed`, 4
  `inconclusive`, 0 `blocked`, and 0 `failed`.
- Both packets contain the same 89 terminal mandatory cases and no invariant
  violations. The earlier Electron `environment_blocked` packet associated
  with `05f5952bc` is superseded and excluded from these totals.
- Comparative summary:
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-comparative-summary.md`.
- ADR-readiness classification: `ADR_READY`; ADR-054 now accepts the future
  architecture decision.
- Accepted decision: Electron/bundled Chromium, family
  `bundled_chromium_electron`, with an isolated monorepo-first package;
  production Tauri remains the trusted shell and the extension remains Tier 0.
- Gate C is passed for architecture and ownership direction by ADR-054
  acceptance. Repository extraction and implementation gates remain closed.

### Decision recommendation update — 2026-07-31

- The prior ADR task stopped correctly because the comparative summary was
  `ADR_READY` but intentionally contained no singular recommendation.
- The decision-recommendation artifact is
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-decision-recommendation.md`.
- ADR-054 accepts the `bundled_chromium_electron` family through Electron.
- ADR-054 accepts an isolated Browser Host application/package in the
  Codexify monorepo first; dedicated-repository extraction is deferred until
  independent ownership prerequisites are proven.
- Production Tauri remains the trusted Codexify desktop shell and launcher;
  arbitrary remote content must not enter its privileged command boundary.
- The Chrome extension remains the optional Tier 0 continuity bridge, not the
  canonical Tier 1 Browser Host.
- Guardian remains authentication, policy, persistence, task, and
  provider-execution authority; the trusted Browser Host main process owns
  authority-bearing envelope construction and authenticated attachment
  orchestration.
- The immediate release posture remains `development/internal unsigned proof`.
- Candidate packets and the comparative summary remain immutable evidence.
- The recommendation has been adopted by ADR-054; the ADR is accepted future
  architecture, not current supported runtime.
- Gate C is passed for architecture and ownership direction; the next
  implementation gate remains closed.
- The package-boundary and versioned Guardian/Browser Context contract
  prerequisite is now the completed implementation slice recorded below.

### Documented contract

- Guardian retains policy, context, account, and task authority.
- ADR-051 governs the current private side-panel authentication and storage
  boundary.
- Browser capture must be user-initiated, visibly scoped to an origin, and
  fail closed on protected or unavailable pages.
- Browser capture availability and ordinary chat availability are separate
  states; capture failure must not silently disable or impersonate chat.
- Remote content is untrusted evidence, not an instruction or permission source.
- The production package boundary is `browser_host/`; the language-neutral
  contract package is `browser_host/contracts/`.
- Contract package versions are `@codexify/browser-host` `0.1.0`,
  `@codexify/browser-host-contracts` `0.2.0`, protocol `1.0.0`, Browser Context
  Envelope `1.0.0`, and attachment `1.0.0`.
- JavaScript and Python consume the same manifest, schemas, canonical tokens,
  and synthetic fixture index; Electron exists only under the private
  `browser_host/` proof package and live Guardian integration remains absent.

### Working theory

- The current extension source boundary is `frontend/chrome-extension`, while
  `frontend/dist/chrome-extension` is generated output loaded through Chrome's
  unpacked-extension flow.
- A future Browser Host may form an independently releasable subsystem.

Task 01 must verify the first theory exhaustively. A later ADR must decide the
second.

### Unproven

- No Codexify Browser Host exists.
- ADR-054 selects Electron/bundled Chromium as future Browser Host
  architecture; no production Browser Host implementation exists.
- No dedicated Browser repository has been approved.
- No cross-repository browser protocol, signing boundary, updater, compatibility
  contract, or release process exists.
- Atlas browser data has not been proven exported, restored, or compatible.
- Tabs, profiles, sessions, history, downloads, browser actions, or autonomous
  browsing are not release-qualified Codexify capabilities.

## Current-truth anchors

### What is true now

- Codexify's supported release posture remains the local Docker Compose,
  local-first beta described by `docs/architecture/00-current-state.md`.
- Codexify contains a React frontend, Guardian backend, persistent
  project/thread state, Tauri shell, and a private Chrome side-panel client.
- The current side-panel client is an internal, unpacked client outside the
  supported beta release surface.
- The Codexify repository is authoritative for Guardian policy, frontend
  integration, browser-context contracts, identity boundaries, and shared
  architecture documentation.
- The current extension remains the Tier 0 continuity control.
- The incumbent OS-webview/Tauri family and a materially different
  bundled Chromium/Electron family have terminal packets under the same proof
  method; their comparative summary is recorded at
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-comparative-summary.md`
  with an `ADR_READY` reassessment; ADR-054 accepts the future topology.
- The Stage 3 topology evaluation returned `PROOF_REQUIRED` before the
  comparative terminal-packet reassessment; ADR-054 now records the accepted
  architecture and ownership direction.
- The accepted future topology is Electron/bundled Chromium in an isolated
  monorepo-first package; this is not current runtime or release truth.
- Campaigns are prerequisite-ordered arcs. Each Task is atomic, independently
  validated, and independently committed.

### What is not yet true

- Codexify Browser is not implemented or selected for beta.
- The existing side panel is not proof of a general browser host.
- No repository split, browser-state persistence contract, session importer, or
  autonomous browser agent is authorized.
- Generated output is not canonical source.

## Product thesis

The minimal viable network is one user-controlled browser surface, one explicit
origin-scoped capture boundary, and Guardian-mediated context intake. Browser
rendering and page state stay outside Guardian's secret and command authority.
The user chooses when context crosses that boundary.

The Browser product should grow only through independently provable slices:
inventory, authority contract, repository decision, continuity stabilization,
one-tab proof, host proof, governed commands, stateful browser features, and
finally release hardening.

## Repository-boundary posture

- Campaign governance, shared contracts, Guardian integration, current
  Chrome-extension integration, and Codexify UI work remain in the Codexify
  repository.
- The existing extension remains in place during inventory and architecture
  evaluation.
- No implementation may use `frontend/dist/chromeextension` or
  `frontend/dist/chrome-extension` as canonical source. The former path is not
  established by current evidence; the latter is currently documented and
  configured as generated output, subject to the full Task 01 inventory.
- A future Browser Host may move to a dedicated repository only after inventory
  and an accepted architecture ADR prove an independently buildable,
  releasable, signable, recoverable, and securable boundary.
- Repository separation must follow a proven subsystem seam. It must not be used
  to manufacture one.

## Security and sovereignty invariants

1. Guardian retains policy and context authority; a renderer is not Guardian.
2. Renderer and page processes receive no Guardian API keys, provider
   credentials, unrestricted filesystem authority, or unrestricted command-bus
   authority.
3. Browser capture is explicit, user-initiated, origin-scoped, observable, and
   revocable.
4. Protected, restricted, unsupported, or ambiguous pages fail closed.
5. Remote page content is untrusted input and cannot grant identity, permission,
   approval, or tool authority.
6. Browser state does not silently become durable identity, memory, retrieval
   truth, or project truth.
7. Browser capture and browser action semantics use explicit canonical
   contracts, not prompt-based authority.
8. Credentials, cookies, sessions, downloads, history, and profile state have
   separate ownership, retention, export, deletion, and recovery rules.
9. Network partitions, renderer crashes, duplicate requests, and replay are
   normal failure modes; actions require idempotency and attributable receipts.
10. Protocol and schema changes require versioning and forward/backward
    compatibility before independently released components are permitted.

## Explicit non-goals

- No supported or release-qualified browser, extension, page-capture, or
  Browser Host implementation; the bounded `browser_host/` runtime is internal
  proof only and does not widen release truth.
- No extension repair, relocation, rename, or packaging change.
- No Electron, Tauri, CEF, Chromium fork, or other technology selection.
- No supported production dependency, build, Tauri, backend, frontend, or
  release-surface change; the private `browser_host/` package remains an
  internal proof surface.
- No dedicated repository.
- No Atlas, bookmark, cookie, history, or session import.
- No autonomous browsing or new browser command tokens.
- No ADR creation or `docs/architecture/00-current-state.md` update.
- No widened beta, compatibility, migration, or release claim.

## Prerequisite-ordered task map

### 01. Extension and repository inventory

- Status: passed. The accepted inventory proof is
  `docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md`
  at commit `acff4ef26ca7a8ff56babceb275c8ecf51d3e8b1`.
- Proven source boundary: `frontend/chrome-extension/` is canonical source and
  `frontend/dist/chrome-extension` is generated output.
- Goal: prove the existing extension's source, manifest, worker/bridge,
  AppShell/browser integration points, tests, build command, generated output,
  packaging path, ignore behavior, and smallest stable source boundary.
- Prerequisite: this Campaign is accepted for execution.
- Expected evidence: one repository inventory proof with path-to-owner and
  path-to-build-step mappings, exact Git evidence, and unresolved gaps.
- Explicit exclusions: no edits to extension/runtime files, relocation,
  repository creation, technology choice, or implementation.
- Stage kind: `proof`.

### 02. Browser authority and context-boundary contract

- Status: documented at
  `docs/architecture/browser-authority-and-context-boundary-contract.md`.
  This is documentation-layer contract evidence; implementation and live
  browser proof remain unproven.
- Goal: define the user, renderer, Browser Host, Guardian, origin, capture,
  storage, confirmation, and failure boundaries.
- Prerequisite: Task 01 inventory proof.
- Expected evidence: reviewed architecture contract with threat model, data
  ownership, consistency, consent, revocation, and protected-page behavior.
- Explicit exclusions: no browser actions, host implementation, credentials in
  renderer processes, or prompt-based authority.
- Stage kind: `documentation`.

### 03. Repository-topology and Browser Host evidence gate

- Status: architecture evaluation completed in
  `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
  at commit `1cbf68113b9113faa907c22d868248609f49f9a5`.
- Historical Stage 3 result: `PROOF_REQUIRED`; no technology or repository
  topology was selected by that evaluation.
- Proof methodology:
  `docs/architecture/browser-host-comparative-proof-harness-spec.md`.
- Shared technology-neutral scaffold: now exists at
  `scripts/browser_host_harness/` with focused tests at
  `tests/browser_host_harness/`. Scaffold proof artifact:
  `docs/architecture/proofs/2026-07-30-browser-host-shared-harness-scaffold-proof.md`.
  The scaffold provides the deterministic fixture server, Guardian contract
  stub, canonical harness registries, and proof-receipt contracts.
- Incumbent candidate: the proof-only Tauri source exists at
  `browser_host_candidates/tauri/`; its terminal packet is
  `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/`.
  Candidate status is `proof_complete` for terminal evidence coverage, with no
  invariant violation. Interaction-dependent cases that lacked an approved
  macOS Tauri driver remain `blocked` or `inconclusive`.
- Materially different candidate: the proof-only bundled Chromium/Electron
  source exists at `browser_host_candidates/electron/`; its adapter is
  `scripts/browser_host_harness/adapters/electron_bundled_chromium.py`, and its
  terminal packet is
  `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/`.
-  The final packet is `proof_complete` with 85 passed, 4 inconclusive, 0
  blocked, and 0 failed cases, with no invariant violation. An earlier
  `environment_blocked` packet is superseded.
- Control and gate posture: ADR-054 accepts Electron/bundled Chromium and the
  monorepo-first isolated package posture; the extension remains the Tier 0
  control, Tauri remains the trusted shell, and Gate C is passed for
  architecture and ownership direction.
- Goal: establish the accepted package-boundary and versioned-contract
  scaffold before any full Browser Host product behavior. This prerequisite is
  complete; product proof remains closed.
- Prerequisite: Tasks 01 and 02.
- Required pre-ADR evidence: the shared technology-neutral
  fixture/stub/receipt scaffold (done), an incumbent OS-webview/Tauri candidate
  proof packet, at least one materially different host-family proof packet, and
  a common comparative summary.
- Decision recommendation: the adopted artifact at
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-decision-recommendation.md`
- records the singular decision adopted by ADR-054: Electron/bundled Chromium
  and monorepo-first isolated implementation, while retaining Tauri as the
  trusted shell and the extension as Tier 0.
- Completed prerequisite: `browser_host/`, `browser_host/contracts/`, the
  normative contract, and JavaScript/Python fixture-parity tests exist without
  runtime Browser Host behavior. The next implementation gate remains closed.
- Expected decision artifact after proof: ADR-054, now accepted, with build,
  release, signing, storage, security ownership, compatibility, and rolling
  upgrade implications recorded.
- Explicit exclusions: no repository creation, code movement, or host choice by
  implication.
- Stage kind: `proof` followed by `documentation`.

### 04. Atlas continuity and Chrome-extension stabilization

- Goal: preserve the required current workflow and stabilize the existing
  extension boundary before introducing a replacement host.
- Prerequisite: Tasks 01 through 03.
- Expected evidence: bounded compatibility matrix, explicit Atlas export/import
  posture, focused extension tests, and live extension proof where authorized.
- Explicit exclusions: no unproven export/restore claim, silent session import,
  or general Browser Host.
- Stage kind: `proof`.

### 05. One-tab Browser Workspace proof

- Goal: prove one user-controlled tab can render, expose explicitly selected
  context, and keep ordinary chat usable when capture is denied or unavailable.
- Prerequisite: Tasks 02 through 04.
- Expected evidence: live proof of origin scope, consent, capture failure,
  renderer isolation, provenance, and chat independence.
- Explicit exclusions: no multi-profile state, downloads, history, autonomous
  action, or release claim.
- Stage kind: `proof`.

### 06. Browser Host technology proof

- Goal: compare and exercise candidate host technology against the accepted ADR
  and one-tab contract.
- Prerequisite: Task 05 and accepted Task 03 ADR.
- Expected evidence: reproducible build/run prototypes, isolation evidence,
  crash recovery, signing/packaging feasibility, performance observations, and
  explicit rejection reasons.
- Explicit exclusions: no production choice based on preference, scaffold
  presence, or marketing claims.
- Stage kind: `proof`.

### 07. Governed browser command contract

- Goal: define explicit, capability-scoped, confirmable, idempotent browser
  commands and attributable receipts.
- Prerequisite: Tasks 02, 03, 05, and 06.
- Expected evidence: reviewed schemas, capability grants, confirmation rules,
  replay behavior, cancellation, failure taxonomy, and audit boundaries.
- Explicit exclusions: no unrestricted scripting, ambient command-bus access,
  prompt-granted actions, or autonomous action.
- Stage kind: `documentation`.

### 08. Tabs, profiles, sessions, history, and downloads

- Goal: implement bounded browser-state features under explicit ownership,
  retention, conflict, recovery, and migration contracts.
- Prerequisite: Tasks 03, 06, and 07.
- Expected evidence: focused implementation tests and live proof for each
  separately accepted feature slice.
- Explicit exclusions: no silent durable identity/memory, cookie import by
  default, cross-profile leakage, or blanket filesystem access.
- Stage kind: `implementation`.

### 09. Security, packaging, recovery, and release proof

- Goal: establish the complete supported installation, signing, update,
  rollback, recovery, compatibility, observability, and incident boundary.
- Prerequisite: all preceding tasks.
- Expected evidence: adversarial review, clean-install and upgrade proof,
  partition/crash recovery, credential-boundary inspection, signed packaging,
  compatibility matrix, and release checklist.
- Explicit exclusions: no release classification from docs, unit tests, or a
  single successful local run alone.
- Stage kind: `proof`.

## Decision gates

### Gate A: Source authority

The extension source, manifest, generated output, build, packaging, and ignore
relationship must be proven before any extension edit or relocation.

Status: passed by the Stage 01 inventory proof at commit
`acff4ef26ca7a8ff56babceb275c8ecf51d3e8b1`.

### Gate B: Browser authority

Renderer, Browser Host, Guardian, user-confirmation, origin, and state-ownership
boundaries must be documented before browser actions are added.

Status: defined at the documentation layer by
`docs/architecture/browser-authority-and-context-boundary-contract.md`.
Implementation proof is still required before page capture or browser actions
can become product claims.

### Gate C: Repository split

A dedicated Browser Host repository may be created only after an accepted ADR
proves independent build, release, signing, storage, compatibility, recovery,
and security ownership.

Status: passed for architecture and ownership direction by accepted ADR-054.
The decision selects Electron/bundled Chromium and a monorepo-first isolated
Browser Host package, retains Tauri as the trusted shell and the extension as
Tier 0, and keeps Guardian as authority. Repository extraction remains closed
until the independent-release prerequisites in ADR-054 are proven.

### Gate D: Product proof

Tabs, profiles, downloads, history, session persistence, or browser actions may
not become release claims until the selected Browser Host passes live proof for
the claimed surface.

Status: the 2026-08-01 packet proves only the bounded one-tab topology,
capture-preview, and ephemeral-attachment behavior against deterministic
loopback stubs. The supported integration gate remains closed; live Guardian,
durable persistence, packaging, signing, updater, and release behavior remain
unproven.

## Proof expectations

- Git evidence distinguishes tracked source, ignored output, generated
  artifacts, and manually maintained files.
- Path mappings identify the owner and build step for every extension artifact.
- Documentation and code-path evidence remain distinct from live browser proof.
- Every future action contract includes origin, identity, capability, consent,
  idempotency, retry, cancellation, and receipt semantics.
- Every persistent state surface identifies its source of truth, consistency
  target, conflict policy, identity binding, retention, export, deletion, and
  recovery rules.
- Cross-repository components require a versioned protocol and compatibility
  matrix before independent release.

## Exit criteria

The Campaign exits only when:

1. all nine stages have accepted evidence at their stated proof level;
2. all four decision gates are satisfied;
3. the Browser Host boundary and technology are governed by an accepted ADR;
4. security, packaging, upgrade, rollback, and recovery proofs pass;
5. current-state release truth is updated by a separately authorized task; and
6. no Browser claim depends only on this Campaign, a scaffold, a test, or an
   unreviewed local build.

## Known risks

- Generated output may be mistaken for canonical source.
- The existing side panel may be overgeneralized into a browser architecture.
- A premature repository split may obscure shared Guardian and UI contracts.
- Renderer compromise may expose credentials or ambient host authority.
- Browser state may leak into durable identity or memory without consent.
- Browser actions may be replayed or duplicated after partitions and retries.
- Atlas continuity pressure may encourage unsafe cookie/session import.
- Host selection may precede proof of signing, recovery, and upgrade behavior.
- Cross-repository protocol drift may make rolling upgrades unsafe.

## Documentation follow-through

- Task 01 produced
  `docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md`
  at commit `acff4ef26ca7a8ff56babceb275c8ecf51d3e8b1`.
- Task 02 documents the browser authority and context boundary in
  `docs/architecture/browser-authority-and-context-boundary-contract.md`;
  implementation and live proof remain deferred.
- Task 03 evaluation produced
  `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
  at commit `1cbf68113b9113faa907c22d868248609f49f9a5`
  and returned `PROOF_REQUIRED`.
- The prior ADR task stopped correctly because the comparative summary was
  `ADR_READY` but intentionally contained no singular recommendation. The
  resulting decision recommendation is recorded at
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-decision-recommendation.md`.
  It recommends Electron/bundled Chromium, monorepo-first isolated
  implementation, retained Tauri and extension roles, Guardian authority, and
  development/internal unsigned proof. ADR-054 now adopts it; the artifact
  remains a decision input rather than runtime proof.
- The common comparison method is
  `docs/architecture/browser-host-comparative-proof-harness-spec.md`.
- The shared scaffold prerequisite is commit
  `eb6eb416d0f70d6b68bd582cb9ffdb82c27e5678`.
- The incumbent Tauri-family source and terminal packet now exist at
  `browser_host_candidates/tauri/` and
  `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/`.
  This is incumbent-family evidence only: Tauri is not selected, production
  Tauri is unchanged, and live production Guardian compatibility is not
  proven.
- A materially different bundled Chromium/Electron candidate now has a
  terminal `proof_complete` packet under the same harness. The comparative
  summary records `ADR_READY`, and the decision recommendation is now recorded
  at
  `docs/architecture/proofs/browser-host/2026-07-31-browser-host-decision-recommendation.md`.
  ADR-054 now adopts the topology and ownership decision. The single next
  prerequisite is the production package-boundary and versioned-contract
  scaffold, while the next implementation gate remains closed.
- Later proof tasks must update their own proof artifacts and compatibility
  records.
- `docs/architecture/00-current-state.md` changes only in a separately
  authorized release-truth task after qualifying proof.

## Current task completion

- ADR-054 commit: `d8649a382711f64d5dcb1c5b22468a272c0b36ed`.
- Production source root: `browser_host/`.
- Versioned contract package: `browser_host/contracts/`.
- Package status: private `0.1.0` scaffold; contract package status: private
  `0.2.0` source-of-truth package.
- Protocol, envelope, and attachment versions: `1.0.0`.
- JavaScript conformance: passed; Python conformance: passed.
- Electron `43.2.0` and Playwright `1.62.1` are exact-pinned development
  dependencies beneath `browser_host/` only. The production package now has a
  bounded one-tab runtime and sanitized proof packet, while live Guardian
  integration, product proof, and release qualification remain closed.
- Gate C remains passed for architecture and ownership direction. Gate D is
  proven only for bounded internal proof slices; supported one-tab integration
  and release behavior remain closed.

## Production one-tab skeleton — 2026-07-31

- Prerequisite scaffold commit: `2f6fcd05cc0f778d9b9bbc16872cdd76a4178c0d`.
- Runtime paths: `browser_host/src/main.js`, `src/runtime/`,
  `src/preload/trusted-shell-preload.js`, and `src/shell/`.
- Topology: one trusted Electron `BrowserWindow` and exactly one untrusted
  remote `WebContentsView`; the remote view has no preload, Node, Electron, or
  IPC authority and uses a non-persistent session.
- Negotiation: the main process constructs and validates the v1 hello, sends it
  to the deterministic 127.0.0.1 Guardian stub with a proof-only synthetic
  token, validates the response, and creates/loads the remote view only after
  compatible negotiation. Incompatible, malformed, and unreachable cases
  leave the trusted shell alive with no remote request.
- Contract versions: package `0.1.0`, contract package `0.2.0`, protocol,
  envelope, and attachment `1.0.0`.
- Proof packet:
  `docs/architecture/proofs/browser-host/2026-07-31-production-one-tab-skeleton/`.
  The packet validates compatible, incompatible, malformed, denial, renderer
  degradation, authority-isolation, and cleanup scenarios.
- Synthetic credential posture: the runtime token is generated by the proof
  parent, passed only through `CODEXIFY_BROWSER_HOST_PROOF_TOKEN` in explicit
  proof mode, read by trusted main, removed from retained environment state,
  never exposed to either renderer, and absent from receipts/screenshots.
- Denial posture: numeric-loopback exact-origin navigation only; cross-origin,
  dangerous schemes, popups, external protocols, downloads, and permissions
  are denied. Renderer termination degrades the remote view without automatic
  recreation; cleanup removes support processes and temporary state.
- DeepSeek orchestration: required pre-edit and post-edit advisory reviews
  were run through the installed orchestration and delegation skills with
  exact `deepseek-v4-pro` through Pi. Codex retained implementation and
  verification authority; no secrets were transmitted and DeepSeek made no
  repository edits.
- Explicit non-claims: no capture, attachment, runtime Browser Context
  Envelope construction, persistence, live production Guardian route,
  production credential, packaging, signing, updater, rollback, or release
  behavior was implemented.

### Next atomic task

Implement explicit selected-text and visible-page capture preview with separate
ephemeral attachment against the deterministic Guardian stub, using the
versioned Browser Context Envelope contracts and without live production
Guardian credentials.

## Capture preview and ephemeral attachment — 2026-08-01

- Baseline: `0973f8e56715d464b115d21911e4a5677e996fe3`.
- Capture paths: trusted-shell selected-text and visible-page preview actions
  call narrow IPC handlers; the remote renderer receives no new authority.
- Main-process ownership: the trusted main process validates the remote result,
  normalizes bounded UTF-8 text, computes hashes and document fingerprints,
  constructs the versioned Browser Context Envelope, and keeps the ticket only
  in bounded memory.
- Sanitization: form controls, password/hidden values, browser storage,
  scripts/styles, and iframe content are excluded. Page prompt-like text stays
  evidence and is rendered as text; it cannot alter host policy or commands.
- Attachment: a separate trusted-shell confirmation constructs the v1
  attachment and sends it only to the deterministic loopback stub. Accepted
  and rejected receipts are `not_persisted`; stale, cancelled, replayed, and
  deterministic failure paths remain fail closed.
- Proof packet:
  `docs/architecture/proofs/browser-host/2026-08-01-capture-preview-attachment/`.
- Validation: 17 unit/contract tests, 8 live Electron tests, proof generation,
  proof validation, and the existing shared contract/Python checks pass.
- DeepSeek orchestration: strict exact-model preflight passed, but the
  read-only pre-edit worker timed out after 180 seconds without a result or
  edits. Codex continued with direct implementation and independent proof;
  no secrets were transmitted.
- Explicit non-claims: no live Guardian route or credential, durable
  persistence, packaging, signing, updater, rollback, or release behavior.

### Next atomic task

Qualify a Guardian-issued one-use attachment grant contract for the v1
ephemeral attachment path before any live production route or durable
persistence work.

## Guardian-issued one-use attachment grant contract — 2026-08-01

- Prerequisite capture commit: `fc7574246eb05259652daeffc65c22bc0d53d896`.
- Contract package: `@codexify/browser-host-contracts` `0.2.0`; Browser Host
  package remains `0.1.0`; protocol, envelope, and attachment remain `1.0.0`.
- Grant schemas:
  `browser_host/contracts/schemas/browser-host-attachment-grant-request.v1.schema.json`
  and
  `browser_host/contracts/schemas/browser-host-attachment-grant.v1.schema.json`.
- Pure Guardian modules:
  `guardian/browser_host/contract_loader.py` and
  `guardian/browser_host/attachment_grants.py`.
- Authorization scheme: `browser_host_attachment_grant`.
- TTL: bounded to 30–300 seconds, default 120 seconds; exactly one use;
  `ephemeral` retention only.
- Storage: process-local, digest-only SHA-256 bearer storage; no database,
  Redis, file persistence, or reusable Guardian credential.
- Concurrency: two same-bearer consumers yield exactly one authorized
  decision and one replay denial.
- Pure seam and sanitized proof are test-proven; Guardian routing,
  authenticated issuance, Browser Host transport, and live integration remain
  unproven.
- No route, network, API key, session cookie, JWT, production credential,
  current-state release change, or supported-release change was added.
- Gate C remains passed for architecture and ownership direction. Gate D
  remains closed for supported integration and release behavior.

## Development-only Guardian attachment-grant HTTP adapter — 2026-08-01

- Prerequisite: `87fe3257c0d0c12ad00a749b631bfeb866ddaaaf`.
- Feature flag: `GUARDIAN_BROWSER_HOST_ATTACHMENT_DEV_ENABLED`, default
  `false`; mounting also requires `GUARDIAN_DEV_MODE=true` and
  `GUARDIAN_EXPOSURE_MODE=local_safe`.
- Route prefix: `/dev/browser-host/v1`; exact paths are
  `POST /attachment-grants` and `POST /attachments`. The default route table,
  supported profiles, and non-local exposure remain unchanged.
- Store: one application-scoped process-local `AttachmentGrantStore`,
  digest-only and ephemeral; shutdown clears it and restart invalidates all
  outstanding grants.
- Issuance: existing Guardian authentication/current-user dependency derives
  the internal subject; the subject, API key, session cookie, and JWT are never
  serialized to the grant response or sent to the Browser Host.
- Attachment: the one-use `BrowserHostAttachmentGrant` and explicit instance
  header are the complete authorization capability. Accepted requests return
  `202` with an existing content-free receipt and `not_persisted`.
- Rejection: replay and expiration return `409`; scope, version, retention,
  confirmation, and budget mismatches return valid `403` receipts; malformed
  bodies are rejected before the grant can be consumed. Concurrent attempts
  produce exactly one success and one replay rejection.
- Non-use: no database, Redis, filesystem persistence, provider, worker,
  queue, command bus, storage writer, or production Browser Host runtime is
  connected. Raw bearer, bearer digest, subject, and page content are absent
  from logs, receipts, proof, and retained app state.
- Proof packet:
  `docs/architecture/proofs/browser-host/2026-08-01-guardian-attachment-http-adapter/`.
- Gate C remains passed for architecture and ownership direction. Gate D
  remains closed for supported integration and release qualification.
- This is a development integration seam, not a supported release path.

### Next atomic task

Wire the production Browser Host main process to the development-only Guardian
attachment-grant adapter behind explicit local operator configuration, using the
one-use grant and no reusable Guardian credential.

## ADR impact

- Classification: aligned with existing ADRs; ADR-054 is accepted.
- ADR created by the adoption task:
  `docs/architecture/adr/054-browser-host-topology-and-release-ownership.md`.
- The decision-recommendation artifact is the singular evidence-backed input
  adopted by ADR-054; it remains separate from runtime proof.
- Existing governing contract: ADR-051 continues to govern the current private
  Chrome side-panel client.
- Accepted ADR subject: Browser Host authority, repository topology, renderer
  isolation, storage ownership, protocol versioning, release/signing ownership,
  and compatibility.
- Reason: these boundaries would be dangerous to reinterpret after
  implementation or repository separation.

## Source evidence

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md`
- `docs/architecture/browser-authority-and-context-boundary-contract.md`
- `docs/architecture/browser-host-comparative-proof-harness-spec.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/self-extending-agent-plugin-system.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/web-agent-spec.md`
- `docs/architecture/chrome-side-panel-client.md`
- `docs/architecture/proofs/2026-06-23-trusted-remote-browser-codex-proof.md`
- `docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md`
- `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
- `frontend/chrome-extension/manifest.json`
- `frontend/chrome-extension/service-worker.ts`
- `frontend/chrome-extension/src/`
- `frontend/chrome-extension/README.md`
- `frontend/vite.chrome-extension.config.ts`
- `frontend/package.json`
- `.gitignore`
