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

- Stage 3 produced
  `docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md`
  at commit `1cbf68113b9113faa907c22d868248609f49f9a5`.
- Its ADR-readiness result is `PROOF_REQUIRED`.
- No technology or repository winner was selected.
- The future topology ADR remains blocked pending common comparative evidence.
- `docs/architecture/browser-host-comparative-proof-harness-spec.md` defines
  the normative, technology-neutral comparison method. It is documentation,
  not a harness implementation or live Browser Host proof.

### Documented contract

- Guardian retains policy, context, account, and task authority.
- ADR-051 governs the current private side-panel authentication and storage
  boundary.
- Browser capture must be user-initiated, visibly scoped to an origin, and
  fail closed on protected or unavailable pages.
- Browser capture availability and ordinary chat availability are separate
  states; capture failure must not silently disable or impersonate chat.
- Remote content is untrusted evidence, not an instruction or permission source.

### Working theory

- The current extension source boundary is `frontend/chrome-extension`, while
  `frontend/dist/chrome-extension` is generated output loaded through Chrome's
  unpacked-extension flow.
- A future Browser Host may form an independently releasable subsystem.

Task 01 must verify the first theory exhaustively. A later ADR must decide the
second.

### Unproven

- No Codexify Browser Host exists.
- No Electron, Tauri, Chromium Embedded Framework, Chromium fork, or other host
  technology has been selected.
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
- The incumbent OS-webview/Tauri family must be tested rather than assumed
  suitable, and at least one materially different host family must be tested
  under the same proof method.
- The Stage 3 topology evaluation returned `PROOF_REQUIRED`.
- No Browser Host technology or repository topology has been selected.
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

- No browser, extension, page-capture, or Browser Host implementation.
- No extension repair, relocation, rename, or packaging change.
- No Electron, Tauri, CEF, Chromium fork, or other technology selection.
- No dependency, package, build, Tauri, backend, frontend, or runtime change.
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
- Result: `PROOF_REQUIRED`; no technology or repository winner was selected.
- Proof methodology:
  `docs/architecture/browser-host-comparative-proof-harness-spec.md`.
- Shared technology-neutral scaffold: now exists at
  `scripts/browser_host_harness/` with focused tests at
  `tests/browser_host_harness/`. Scaffold proof artifact:
  `docs/architecture/proofs/2026-07-30-browser-host-shared-harness-scaffold-proof.md`.
  The scaffold provides the deterministic fixture server, Guardian contract
  stub, canonical harness registries, and proof-receipt scaffold. It does not
  implement a candidate adapter; the extension remains the Tier 0 control;
  Gate C remains closed.
- Goal: produce decision-grade comparative evidence, then author the future
  Browser Host topology and release-ownership ADR.
- Prerequisite: Tasks 01 and 02.
- Required pre-ADR evidence: the shared technology-neutral
  fixture/stub/receipt scaffold (done), an incumbent OS-webview/Tauri candidate
  proof packet, at least one materially different host-family proof packet, and
  a common comparative summary.
- Next prerequisite: implement the incumbent OS-webview/Tauri candidate adapter
  and produce its candidate proof packet under the common harness.
  At least one materially different candidate remains mandatory before ADR
  authoring.
- Expected decision artifact after proof: an accepted ADR covering build,
  release, signing, storage, security ownership, compatibility, and rolling
  upgrade implications.
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

Status: closed. The Stage 3 evaluation returned `PROOF_REQUIRED`. Comparative
proof packets governed by
`docs/architecture/browser-host-comparative-proof-harness-spec.md` are required
before the ADR may be authored. Gate C remains closed until that evidence exists
and a later accepted ADR resolves repository ownership.

### Gate D: Product proof

Tabs, profiles, downloads, history, session persistence, or browser actions may
not become release claims until the selected Browser Host passes live proof for
the claimed surface.

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
- The common comparison method is
  `docs/architecture/browser-host-comparative-proof-harness-spec.md`. No
  Browser Host technology or repository split has been selected.
- The next prerequisite is the shared technology-neutral fixture server,
  deterministic Guardian contract stub, and proof-receipt scaffold only. The
  incumbent Tauri family and at least one materially different family must then
  produce comparable proof packets before ADR authoring.
- Later proof tasks must update their own proof artifacts and compatibility
  records.
- `docs/architecture/00-current-state.md` changes only in a separately
  authorized release-truth task after qualifying proof.

## ADR impact

- Classification: aligned with existing ADRs; future ADR remains
  evidence-blocked.
- ADR created or modified here: none.
- Existing governing contract: ADR-051 continues to govern the current private
  Chrome side-panel client.
- Future ADR subject: Browser Host authority, repository topology, renderer
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
