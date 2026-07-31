# Codexify Browser Host comparative proof summary

## 1. Artifact identity

- Artifact date: `2026-07-31`.
- Repository: `/Volumes/Dev_SSD/Codexify-main`.
- Branch: `codex/establish-browser-campaign`.
- HEAD at comparison: `3854cfd3214f0300be5cb6aa1799ad03b1bb3ed3`.
- Scope: technology-neutral synthesis of the terminal incumbent OS-webview
  packet and the terminal materially different bundled-Chromium packet.
- This artifact is evidence and architecture-readiness documentation. It does
  not select a host technology, create a repository, open Gate C, or qualify a
  production release.

## 2. Governing contracts and boundaries

The comparison uses the common proof method in
`docs/architecture/browser-host-comparative-proof-harness-spec.md`, the
Browser Authority and Context Boundary Contract, and the existing architecture
contracts governing identity, retrieval, runtime mode, operator access,
network topology, and the private Chrome side-panel client. In particular:

- Guardian remains policy and persistence authority.
- Remote page content is evidence, not authority.
- Remote renderers receive neither Guardian credentials nor unrelated native
  command authority.
- Capture is explicit, bounded, origin-aware, and separate from durable
  persistence.
- The Chrome side panel is a Tier 0 continuity control, not a Tier 1 host
  candidate.
- The comparison does not alter production Tauri, frontend, extension,
  Guardian, package, lockfile, CI, Docker, or current-state files.

## 3. Evidence taxonomy

The packet evidence is interpreted using the harness taxonomy: repository,
test, live-runtime, packet, measurement, code-path-only, platform-blocked,
and unknown evidence remain separate claims. `proof_complete` means that the
declared packet was assembled with every mandatory case terminal and cleanup
verified; it does not mean every case passed or that the candidate is
release-qualified.

## 4. Source packet lineage

| Candidate family | Candidate | Packet | Run | Proof source / implementation lineage |
| --- | --- | --- | --- | --- |
| OS webview | `codexify-tauri-os-webview-incumbent-v1` | `docs/architecture/proofs/browser-host/2026-07-30-tauri-incumbent/` | `tauri-proof-79fdb67b` | implementation commit `59617cf32f40928db969f4455459923f9558e268`; packet source commit `eb6eb416d0f70d6b68bd582cb9ffdb82c27e5678` |
| Bundled Chromium | `codexify-electron-bundled-chromium-v1` | `docs/architecture/proofs/browser-host/2026-07-31-electron-bundled-chromium/` | `harness-0288e8f5` | final candidate commits `37db52dd1`, `3777171c4`, and `3854cfd32`; packet proof source commit `3777171c4ea6b65b4639d125654b8f4d07bf2caf` |

The supplied final Electron lineage supersedes the earlier
`environment_blocked` packet associated with commit `05f5952bc`. That earlier
packet is not included in current totals or readiness reasoning.

## 5. Receipt and registry reconciliation

- Both receipts declare harness `0.1.0`, fixture corpus `1.0.0`, and Guardian
  stub `0.1.0`.
- Both receipts contain 89 cases, exactly matching
  `scripts.browser_host_harness.candidate_cases.MANDATORY_CANDIDATE_CASES`.
- Both receipts have registry hash
  `1308e4d9192282aece0c98da5b38ab81a66c8dfccefc7ad0cefc4f0d3a58f9c5`.
- Neither receipt omits or adds a case; both case sets are identical and
  terminal, with no `not_run` case.
- Both receipts report cleanup passed, an empty invariant-violation list, and
  an empty failure list.
- No candidate runtime was rerun for this synthesis.

## 6. Terminal status comparison

| Candidate | Passed | Inconclusive | Blocked | Failed | Invariant violations | Packet status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| OS webview incumbent | 34 | 42 | 13 | 0 | 0 | `proof_complete` |
| Bundled Chromium | 85 | 4 | 0 | 0 | 0 | `proof_complete` |

The status totals describe evidence outcomes for the fixed 89-case corpus.
They are not a technology selection mechanism and do not convert
inconclusive or blocked cases into passes.

## 7. Case-status relationship

- 34 cases passed for both candidates.
- 51 cases passed for the bundled-Chromium candidate and were not passed by
  the OS-webview candidate.
- No case passed for the OS-webview candidate and failed to pass for the
  bundled-Chromium candidate.
- Four cases were inconclusive for both: `accessibility_text_scaling`,
  `failure_malformed_response`, `resource_idle_memory`, and
  `resource_one_tab_memory`.
- The OS-webview candidate had 13 blocked cases; each of those cases passed for
  the bundled-Chromium candidate.
- No case was failed or marked as an invariant violation for either candidate.

These relationships are descriptive evidence for the future ADR. They do not
establish product suitability, release ownership, or a selected implementation.

## 8. Evidence-level relationship

Evidence strength differs by candidate and by case. The OS-webview packet has
21 `code-and-process-only`, 17 `test-proven-code-path`, 14
`proven-repository`, 13 `platform-blocked`, 5 `live-build-proven`, 5
`proof-packet-proven`, 4 `live-cleanup-proven`, 3
`process-measurement-only`, 1 `code-path-only`, 1
`configuration-and-cleanup-proven`, and 1 `live-process-proven` result. The
bundled-Chromium packet has 59 `live-runtime-proven`, 14
`proven-repository`, 4 `proven-test`, 4 `live-cleanup-proven`, 4
`live-measurement`, 2 `code-path-only`, and 2
`live-measurement-unavailable` results.

The difference is material: identical case names do not imply identical
runtime proof strength. The comparison therefore preserves the evidence label
alongside each status and does not treat a repository assertion as equivalent
to a live renderer observation.

## 9. Lane-level comparison

| Proof lane | OS-webview incumbent | Bundled Chromium |
| --- | --- | --- |
| Static boundary | 8 passed | 8 passed |
| Build and package | 5 passed | 5 passed |
| Launch and navigation | 1 passed, 2 inconclusive, 2 blocked | 5 passed |
| Renderer credential isolation | 6 inconclusive | 6 passed |
| Native authority containment | 6 inconclusive | 6 passed |
| Capture | 7 inconclusive | 7 passed |
| Origin and document identity | 4 inconclusive, 1 blocked | 5 passed |
| Sensitive-field exclusion | 5 inconclusive | 5 passed |
| Prompt-injection containment | 5 inconclusive | 5 passed |
| Permission failure | 5 blocked, 3 inconclusive | 7 passed, 1 inconclusive |
| Renderer failure containment | 4 blocked | 4 passed |
| Observability | 5 passed | 5 passed |
| Accessibility | 5 passed, 1 inconclusive | 5 passed, 1 inconclusive |
| Resources | 4 passed, 3 inconclusive, 1 blocked | 6 passed, 2 inconclusive |
| Cleanup | all required cases passed | all required cases passed |

The OS-webview blocks and inconclusives are bounded platform/driver and
measurement limitations in the packet. They remain unresolved evidence, not
retroactive passes. The bundled-Chromium packet has stronger live interaction
coverage but still has explicit unknowns for memory, malformed responses, and
scaling.

## 10. Authority-invariant comparison

Both packets record no invariant violation. Both candidates declare a trusted
host shell, an untrusted remote renderer, explicit user-initiated capture, a
bounded context envelope, one-attempt attachment, and cleanup. The difference
is proof coverage, not permission to relax the common authority model.

The bundled-Chromium manifest records `nodeIntegration: false`,
`contextIsolation: true`, `sandbox: true`, `webviewTag: false`, no preload for
the remote `BrowserWindow`, a narrow trusted-shell preload bridge, a
run-scoped nonpersistent partition, fixed IPC channels, and validation at the
bridge boundary. The OS-webview manifest records a trusted Rust host, a
constrained WebView renderer, and one remote native authority,
`candidate_return_capture`, with caller-label, origin, state, input-size, and
generation/failure validation.

These are candidate-specific implementations of the same contract. Neither
manifest alone proves production safety; the packet's live and bounded
negative cases are the relevant proof.

## 11. Trusted-shell and remote-renderer topology

The OS-webview candidate uses an OS-managed WebKit/WKWebView engine
(`21624`) inside a Tauri 2.8.5 shell. Its trusted Rust host owns the capture
authority and returns bounded data through the candidate adapter. The
renderer remains a web document with no Guardian credential and no unrelated
native authority.

The bundled-Chromium candidate uses Electron `43.2.0`, Chromium
`150.0.7871.129`, bundled Node `24.18.0`, and V8
`15.0.1240245-electron.0`. Its remote renderer uses a sandboxed,
context-isolated `BrowserWindow` with node integration disabled and a
nonpersistent run-scoped partition. The trusted preload bridge exposes only
fixed, validated channels.

The architectural tradeoff is engine ownership versus host-surface
complexity. OS-webview behavior follows the operating system's engine and
driver availability. Bundled Chromium supplies a more uniform engine surface
for this packet but adds a larger binary and an additional vendor patch
cadence. The future ADR must make that tradeoff explicit without treating
either property as a release guarantee.

## 12. Credential and native-authority isolation

The shared Guardian stub uses only synthetic sentinel credentials. Both
packets report no sentinel leakage to the remote page and no invariant
violation. For the OS-webview candidate, credential and native-authority
interaction cases are mostly inconclusive or blocked because an approved
macOS driver did not establish the required live interaction path. For the
bundled-Chromium candidate, the corresponding cases are live-runtime-proven
passes except for the explicitly recorded malformed-response inconclusive.

This is a proof asymmetry, not evidence that the OS-webview boundary is
unsafe. The exact unresolved claim is that the OS-webview packet does not
provide the same live negative proof for those cases. Production Guardian
compatibility remains unproven for both.

## 13. Navigation, origin, and capture

The common corpus exercises metadata, origin changes, navigation races,
selection capture, stale-capture rejection, sensitive-field exclusion,
prompt-injection text, cross-origin iframe handling, oversized content,
popup/download containment, and protected targets.

The bundled-Chromium packet passes the live capture and document-integrity
cases with selected capture latency values of `[60, 33, 34]` milliseconds and
visible capture trials of `[13, 32, 40, 20, 17, 26, 16, 15, 36, 29, 19, 32]`
milliseconds. The OS-webview packet has code-path, packet, or platform-bound
evidence for the same lanes, with the interaction-dependent cases remaining
inconclusive or blocked. Neither packet authorizes browser actions, silent
capture, durable browser-state persistence, or identity mutation.

## 14. Failure containment and companion continuity

Both packets complete the deterministic failure and cleanup protocol without
an invariant violation. The bundled-Chromium candidate passes the renderer
failure and permission-containment cases live, while the OS-webview candidate
records renderer-failure cases as blocked and several permission cases as
blocked or inconclusive. Both retain the ordinary Guardian companion contract
as a separate surface in the proof model. A capture or renderer failure must
not be interpreted as proof that a production Guardian session is available.

## 15. Accessibility comparison

Both candidates pass the five common accessibility checks covering keyboard,
focus, labeling, and the inspected host surface. Scaling remains inconclusive
for both: the OS-webview result is repository/code-path evidence and the
bundled-Chromium result is code-path-only. No claim is made about complete
assistive-technology support, platform coverage, or release accessibility
qualification.

## 16. Packaging and resource evidence

| Measure | OS-webview incumbent | Bundled Chromium |
| --- | --- | --- |
| Build | `cargo build --offline --locked --release`, 61.4514 s, return 0 | `npm run check && npm test`, 0.8464 s, return 0 |
| Package | `cargo tauri build --bundles app --ci --no-sign`, 37.542 s, return 0 | `npm run package`, 16.3328 s, return 0 |
| Artifact posture | unsigned proof app bundle only | unsigned development-only package; not release-qualified |
| Artifact size | release binary 14,866,272 bytes; app bundle 14,820,411 bytes | 266 files; 501,667,438 bytes; app executable entry 33,968 bytes |
| Cold launch | one value: 2.4346 s | trials: `[459, 318, 302, 281]` ms |
| Capture | unavailable in packet measurement | selected `[60, 33, 34]` ms; visible trials recorded |
| Idle / one-tab memory | both 103,776,256 bytes at process level | unavailable in packet measurement |
| Process count | 1 | 1 |
| Shutdown | 0.6346 s | `[529]` ms |

These measurements are candidate-packet observations, not performance
requirements. The memory asymmetry is especially important: the OS-webview
packet has one process-level observation, while the bundled-Chromium packet
explicitly marks per-process memory unavailable. The shared inconclusive
memory cases remain open for later qualification.

## 17. Repository boundary and release posture

Both candidate sources are proof-only surfaces inside the Codexify repository.
The Electron packet records `directCodexifyProductionImports: false`, an
independent package root, an empty production-boundary diff, and a shared
harness import limited to the declared runtime and case registries. The Tauri
packet records `productionTauriUnchanged: true` and a repository posture
pending a future ADR. Neither candidate is an independently released product
or a supported Browser Host.

The current release truth remains the local Docker Compose, local-first beta
described by `docs/architecture/00-current-state.md`. No Browser Host claim
may be promoted from this packet without a separately authorized live
integration and release-qualification path.

## 18. Maintenance, security, and ownership evidence

The OS-webview packet identifies the OS WebKit vendor as engine maintainer but
leaves framework update, signing, updater, rollback, crash, migration,
vulnerability, platform, and release ownership unassigned or unknown. The
bundled-Chromium packet identifies the Electron/Chromium vendor cadence and a
Playwright proof-lane owner, but Codexify response SLA, signing, updater,
crash, migration, rollback, vulnerability, platform, and product owners are
unknown or unassigned.

These are explicit maintenance evidence fields, not missing packet structure.
They are decision-relevant unknowns for the future ADR and independently
releasable repository question. They are not a reason to rewrite the packet
totals or to claim release readiness.

## 19. Extension control baseline

The existing private Chrome side-panel client remains the Tier 0 continuity
control. Its current authentication and storage boundary is governed by
ADR-051 and the Chrome side-panel contract. The control baseline is recorded
for continuity and regression comparison only; it is not a third Tier 1 host
candidate and does not settle host topology.

## 20. Shared unknowns

- Live production Guardian compatibility is unproven for both candidates.
- No production signing, notarization, updater, rollback, migration, or
  vulnerability-response path is qualified.
- Cross-repository protocol versioning, compatibility, rolling upgrade, and
  recovery contracts do not exist.
- Browser profiles, cookies, tabs, history, downloads, browser actions,
  autonomous browsing, and durable browser state are outside this proof.
- Memory proof is incomplete for both candidates, and scaling plus malformed
  response proof remains incomplete for both where recorded above.
- The packet does not prove a supported release, beta availability, or a
  repository split.

## 21. Candidate-specific unknowns

### OS-webview incumbent

- The 42 inconclusive and 13 blocked cases do not establish live interaction
  behavior for credential isolation, native authority, capture, origin, or
  renderer-failure lanes.
- Engine behavior, framework updates, signing, updater, rollback, crash,
  migration, vulnerability, platform, and release ownership remain
  unassigned or unknown.
- Capture latency is not measured; the memory observation is a single
  process-level value.

### Bundled Chromium

- Idle and one-tab memory are unavailable in the packet.
- Malformed-response handling and text-scaling remain inconclusive.
- The package is unsigned and development-only, so packaging does not prove a
  releasable desktop artifact.
- Electron/Chromium patch, product response SLA, signing, updater, crash,
  migration, rollback, vulnerability, platform, and release ownership remain
  unknown or unassigned.

## 22. Decision-relevant tradeoffs

The evidence supports a bounded architectural comparison along four axes:

1. **Engine surface:** OS-managed WebKit reduces bundled-engine ownership but
   exposes the proof to platform and driver variation; bundled Chromium offers
   a more uniform engine surface at substantially larger artifact size and
   vendor-cadence cost.
2. **Interaction proof:** the bundled-Chromium packet provides materially more
   live coverage for the common authority and capture cases; the OS-webview
   packet preserves bounded repository and build evidence where live driver
   proof was unavailable.
3. **Operational ownership:** neither packet names the product owners needed
   for signing, recovery, upgrades, vulnerability response, or release
   channels.
4. **Repository independence:** both remain proof-only in the monorepo; a
   separate repository would create protocol, compatibility, storage,
   security, and release obligations not solved by this comparison.

The future ADR should decide how these tradeoffs are owned and governed. This
summary does not decide them.

## 23. Repository-split prerequisite reassessment

The 12 prerequisites from the topology evaluation are reassessed against the
terminal packets and current repository state. `Partially met` means evidence
exists for a bounded proof surface but the independent-release obligation is
not complete.

| # | Prerequisite | Classification | Evidence and remaining boundary |
| ---: | --- | --- | --- |
| 1 | Independent build source root | Met | Both candidate proof roots build independently inside the monorepo; no separate repository exists. |
| 2 | Tests independent of unversioned relative imports | Partially met | The common harness imports declared runtime/case modules; an independent-repository test package is not established. |
| 3 | Versioned Guardian/browser contract package or SDK | Unmet | Existing contracts are repository documentation and current-client seams, not a released versioned package. |
| 4 | Conformance fixtures for auth, IDs, status, failure tokens, envelope, and attachment | Partially met | The fixed fixture, stub, receipt, and registry are versioned proof assets; cross-repository conformance packaging is absent. |
| 5 | Accepted compatibility, feature, deprecation, and rolling-upgrade policy | Unmet | No accepted Browser Host topology ADR or cross-repository compatibility policy exists. |
| 6 | Cross-repository CI running the same contract suite | Unmet | The common suite runs in this repository; no cross-repository CI boundary exists. |
| 7 | Independently packageable, signable, and releasable artifact | Partially met | Both candidates package unsigned proof artifacts; neither has release signing, channel, or production qualification. |
| 8 | Named updater, rollback, signing-key, release-channel, and vulnerability owners | Unmet | Packet maintenance fields record unknown or unassigned owners. |
| 9 | Credible engine patch ownership and cadence | Partially met | Vendor engine/framework lines are identified; Codexify patch-response ownership and SLA are not. |
| 10 | Versioned profile/data migration, backup/recovery, export/restore lineage | Unmet | Profiles and durable browser state are out of scope; no migration or recovery contract exists. |
| 11 | Workable issue, review, compatibility, and release ownership | Unmet | No accepted ownership model or release process exists for a separate host surface. |
| 12 | Single source of truth and reversible split plan | Unmet | Both candidates remain monorepo proof roots; no accepted source-of-truth or reversible split plan exists. |

The packet closes the comparative proof requirement, but it does not make the
repository split prerequisites complete. Gate C therefore remains closed.

## 24. ADR-readiness classification

**Classification: `ADR_READY`.**

The future Browser Host topology and release-ownership ADR is ready to be
authored because the comparative proof minimum is satisfied:

- an incumbent OS-webview candidate and a materially different bundled-
  Chromium candidate both have terminal packets;
- every mandatory case is terminal in both receipts, with no omitted or
  `not_run` case;
- the fixed registry and harness versions are reconciled;
- invariant violations and failed cases are explicitly absent;
- packaging, resource, accessibility, repository-boundary, maintenance, and
  ownership evidence are present;
- the Tier 0 extension control baseline is recorded; and
- every blocked, inconclusive, and unknown claim is bounded rather than hidden.

`ADR_READY` means the evidence is sufficient to deliberate and record the
architecture decision. It does not mean a technology is selected, a
repository split is authorized, a candidate is release-qualified, or Gate C
is open. The 12 prerequisite table above remains part of the ADR decision
surface and must not be represented as complete independent-release proof.

## 25. Proposed future ADR

- Title: `Codexify Browser Host Topology and Release Ownership`.
- Decision question: Given the terminal comparative evidence and the current
  Guardian/browser authority contracts, what Browser Host topology, source of
  truth, repository boundary, protocol/versioning model, identity and storage
  ownership, signing/updater/recovery responsibility, compatibility policy,
  and reversible migration plan should Codexify adopt, defer, or reject?

The ADR may rely on this summary, the two terminal packets, the common proof
specification, the topology evaluation, and the existing governing contracts.
It must not overstate proof as production Guardian compatibility, release
qualification, independent repository readiness, durable browser-state
support, or a complete accessibility/resource assessment.

## 26. Gate C posture

Gate C remains **closed**. `ADR_READY` permits authoring the future ADR; it
does not accept the ADR and does not authorize repository creation, source
movement, package publication, signing, or release. The current supported
release truth remains unchanged.

## 27. Recommended next atomic task

Author the future ADR titled `Codexify Browser Host Topology and Release
Ownership`, using this comparative summary and the two terminal proof packets
as evidence, with no implementation, repository creation, source movement,
package change, current-state update, or technology commitment.

This is the single next task. Its acceptance boundary is the reviewed ADR
artifact and its explicit disposition of the 12 repository-split prerequisites.

## 28. Commands executed for this synthesis

The following read-only or validation commands were executed from the
repository root; no candidate was rerun:

- `git status --short --branch --untracked-files=all`
- `git rev-parse --show-toplevel`, `git branch --show-current`, and
  `git rev-parse HEAD`
- `git merge-base --is-ancestor 59617cf32f40928db969f4455459923f9558e268 HEAD`
- `git merge-base --is-ancestor 3854cfd32 HEAD`
- receipt validation for both packet runs using the repository validator
- bounded receipt/registry reconciliation against the 89 mandatory cases
- packet and source-boundary diff checks for both candidate packet directories
- targeted reads of the current-state, architecture, contract, ADR, campaign,
  harness specification, topology evaluation, and candidate packet artifacts

## 29. Validation results

- Tauri receipt: passed; `proof_complete`; 89 terminal cases.
- Electron receipt: passed; `proof_complete`; 89 terminal cases.
- Registry identity and case-set reconciliation: passed.
- Candidate packet diff checks before documentation edits: passed.
- No candidate runtime was rerun.
- Documentation validation and final diff checks are reported in the task
  closeout after the scoped edits are complete.

## 30. Documentation and ADR follow-through

- This summary is the comparative evidence artifact and readiness
  reassessment.
- The comparative harness specification is updated only to point its current
  terminal status at the final packets and this summary; its normative proof
  criteria remain unchanged.
- The Browser Campaign is updated only to reflect the final evidence,
  `ADR_READY`, the still-closed Gate C, and the one next atomic task.
- No ADR is created or modified by this task.
- `docs/architecture/00-current-state.md` is unchanged.

## 31. Explicit non-claims

This artifact does not claim:

- a selected Browser Host technology or repository topology;
- a supported Browser Host release or production beta;
- production Guardian compatibility or real-account access;
- signing, notarization, updater, rollback, migration, or vulnerability
  readiness;
- durable browser profiles, cookies, tabs, history, downloads, browser
  actions, or autonomous browsing;
- complete accessibility, memory, performance, or platform qualification; or
- authorization to open Gate C or modify production runtime surfaces.
