# Codexify Browser Host Topology and Repository-Boundary Evaluation

## 1. Title

Codexify Browser Host topology and repository-boundary evaluation.

## 2. Artifact date

2026-07-30.

## 3. Branch and HEAD

| Field | Observed value | Evidence |
|---|---|---|
| Repository root | `/Volumes/Dev_SSD/Codexify-main` | `proven-repository` |
| Branch | `codex/establish-browser-campaign` | `proven-repository` |
| Starting HEAD | `7e338c54236c2b265792778faf8e3a164b3252af` | `proven-repository` |
| Starting worktree | Clean; branch was two commits ahead of `origin/codex/establish-browser-campaign` | `proven-repository` |
| Execution lane | Architecture-impact | `documented-contract` |
| Task kind | Proof / decision evaluation | `documented-contract` |

## 4. Prerequisite commit verification

`git merge-base --is-ancestor 7e338c54236c2b265792778faf8e3a164b3252af HEAD`
returned success before this artifact was created. The required Stage 2 commit is
therefore an ancestor of the working HEAD. The following prerequisite artifacts
also existed at preflight:

- `docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md`
- `docs/architecture/browser-authority-and-context-boundary-contract.md`
- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md`

The authorized output path did not exist, the worktree was clean, and no accepted
ADR selecting a Browser Host technology or repository topology was found in the
current ADR index or accepted ADR set. `proven-repository`

## 5. Scope

This proof evaluates three independent decision axes:

1. Browser Host technology family.
2. Repository topology.
3. Release posture.

It maps the current Chrome extension, React frontend, Tauri shell, Guardian,
Postgres, Redis/workers, provider, build, package, test, and release seams. It
also identifies the contract, security, profile, migration, versioning, and
operational evidence needed before an ADR may responsibly select an
architecture. `proven-repository`

This proof does not select a technology or repository, create an ADR or
repository, implement a host or proof application, alter a release claim, or
exercise a build, runtime, packaging, signing, updater, publishing, or deployment
path. `documented-contract`

## 6. Evidence taxonomy

The classifications used below are:

- `proven-repository`: direct evidence from current tracked code, Git state,
  build/package configuration, or repository structure.
- `proven-test`: a relevant automated test was observed passing.
- `live-runtime proven`: the relevant behavior was observed in a running
  supported path.
- `official-source documented`: a current official primary source describes a
  framework capability; this is not Codexify implementation proof.
- `documented-contract`: a Codexify contract or ADR governs the behavior, but
  implementation may not exist.
- `code-path only`: checked-in code suggests a path, but execution was not
  proven in this task.
- `working theory`: a reasoned hypothesis or recommendation that requires proof.
- `unknown`: evidence is insufficient.

Matrix cells abbreviate these classifications as `PR`, `PT`, `LR`, `OS`, `DC`,
`CP`, `WT`, and `U`, respectively. A framework capability marked `OS` is never a
claim that Codexify implements or proves it.

## 7. Executive finding

Codexify currently has a continuity client, not a Browser Host. The Chrome
extension is a manually loaded Guardian side-panel client with no page
observation or browser-action authority. The Tauri application is a privileged
local launcher and client shell that loads the bundled Codexify React frontend;
it does not currently host arbitrary remote web content. Guardian remains the
authentication, policy, persistence, task, and provider-execution boundary.
`proven-repository`, `documented-contract`

The existing Tauri shell cannot be relabeled a Browser Host. It registers a
large native command surface with process, filesystem, network, keychain, and
runtime-management authority, while its current capability and CSP posture was
designed for trusted bundled UI rather than an untrusted remote renderer.
Introducing remote content into that privilege domain without a separate
renderer-isolation and IPC proof would violate the Browser Authority and Context
Boundary Contract. `proven-repository`, `official-source documented`,
`documented-contract`

The decision is not yet ADR-ready. Comparable one-tab proofs do not exist for
the relevant candidate families, and packaging, renderer isolation, capture
mediation, observability, security-patch ownership, and operator burden have not
been measured under a common harness. The resulting classification is
`PROOF_REQUIRED`. `proven-repository`, `working theory`

No technology winner is selected. No repository winner is selected.

## 8. Current Codexify client topology

### Implemented relationship

```text
Chrome MV3 side panel ─┐
                       ├─ authenticated HTTP/SSE ─> Guardian ─> Postgres
React web frontend ────┤                              │
                       │                              └─ Redis queues/workers
Tauri trusted shell ───┘                                      │
                                                             └─ providers
```

The extension and main React client share selected TypeScript contracts and
utilities, but they have different entry points and packaging paths. The Tauri
shell embeds the main React build and adds native commands. All three client
surfaces reach Guardian; clients do not own canonical chat/task persistence or
provider execution. `proven-repository`

### Component ownership and release map

| Component | Owning directory / build root | Runtime and trust | Credentials / persistence | Tests and packaging | Independent boundary |
|---|---|---|---|---|---|
| Chrome extension | `frontend/chrome-extension/`; build root `frontend/` | MV3 service worker plus side panel; browser-extension client trust | Local mode `X-API-Key` or remote Bearer session; no canonical persistence | Extension Vitest surface; generated `frontend/dist/chrome-extension`; manual unpacked load | Build command exists, but imports shared frontend sources and has no independent package/release lane (`PR`) |
| React frontend | `frontend/src/`; workspace root `frontend/src/` | Browser renderer; trusted only as a client, not policy authority | Runtime auth in module/session state; no canonical chat/task persistence | Vite/Vitest/Playwright surfaces; WebUI Docker/Nginx output and Tauri frontend bundle | Independently buildable as web assets; release remains coupled to repo CI/runtime (`PR`) |
| Tauri shell | `src-tauri/`; build root `src-tauri/` plus `frontend/src/` | Native host plus trusted bundled React webview | macOS Keychain API key, local runtime files, process/network access; no canonical product data store | Rust unit tests and mocked bridge tests; `.app` bundle target | Buildable, but no current independent signed/updatable release lane (`PR`, `CP`) |
| Guardian | `guardian/` and backend packaging roots | Server policy/auth/API boundary | Guardian key or remote session/JWT; owns persistence mediation | Python tests, backend image, Compose services, CI | Independently container-buildable; compatibility is repo-coordinated (`PR`) |
| Postgres | Compose/runtime configuration and backend models/migrations | Durable system of record | Canonical account, thread, message, task, and artifact state | Migration/tests and Compose proof surfaces | Runtime service, not a client release (`PR`, `DC`) |
| Redis and workers | Compose, queue, worker, and backend roots | Ephemeral coordination and execution | Queue/task state, locks, retries; workers receive scoped execution context | Backend/worker tests and Compose proof surfaces | Runtime services, not client releases (`PR`, `DC`) |
| Providers | Backend/provider modules and worker execution | Inference execution behind Guardian/worker policy | Provider credentials/config remain server/runtime-side | Provider-specific tests and health surfaces | Not a Browser Host concern except status presentation (`PR`, `DC`) |
| Browser authority contract | `docs/architecture/browser-authority-and-context-boundary-contract.md` | Governs future browser evidence and authority | Forbids Guardian credentials in remote renderers; separates capture from action | Documentation validation only | Contract is in-repo, not a published protocol package (`DC`) |

The supported release path remains local Docker Compose. Web and desktop
surfaces do not supersede that current-state boundary. `documented-contract`

## 9. Current Chrome-extension boundary

The canonical source is `frontend/chrome-extension/`; the generated output is
`frontend/dist/chrome-extension`. The build command is
`cd frontend && pnpm build:chrome-extension`, which invokes the extension Vite
configuration. The extension remains within the Codexify repository and imports
shared frontend contracts/utilities rather than consuming a separately
versioned SDK. `proven-repository`

The implemented authority is:

- toolbar activation to an MV3 service worker and side panel;
- an explicit Guardian origin permission;
- local `X-API-Key` or remote Bearer authentication;
- Guardian chat/task and event interactions;
- no active-tab read, page DOM observation, page capture, screenshot, download,
  cookie, filesystem, browser-action, or command-bus authority.

These are repository observations and Stage 1 proof findings, not new live
runtime observations. Stage 1 recorded 68 passing extension tests across five
test files, but this task did not rerun them. `proven-repository`,
`proven-test`

There is no Web Store artifact, CRX/ZIP signing path, extension updater
ownership, release CI, or Tauri integration. Loading remains manual and
unpacked. `proven-repository`

## 10. Current Tauri-shell boundary

### Identity, navigation, and packaging

The canonical Tauri root is `src-tauri/`, not `frontend/src-tauri/`.
`src-tauri/tauri.conf.json` identifies `Codexify` version `0.1.0` as
`com.codexify.desktop`, points development at `http://localhost:5173`, embeds
`../frontend/src/dist` for production, defines one `main` window, and requests
only the `app` bundle target. `proven-repository`

The checked-in application loads the Codexify frontend. No use of
`WebviewWindow`, `WindowBuilder`, multi-view construction, or arbitrary
remote-page navigation was found. Tauri supports remote URLs and additional
webviews as framework capabilities, but those are not implemented Browser Host
features in Codexify. `proven-repository`, `official-source documented`

### Native command and IPC surface

`src-tauri/src/lib.rs` registers frontend-callable custom commands for:

- runtime configuration, authentication, and startup handoff;
- retrieving, setting, and clearing the API key through macOS Keychain;
- signed media retrieval;
- opening external URLs, the WebUI, or Docker;
- runtime preflight and setup;
- image pulls, Compose startup/restart/log retrieval, readiness, and health.

The implementation in `src-tauri/src/commands.rs` uses filesystem access,
environment/runtime roots, macOS `security` and `open`, Docker/Python child
processes, HTTP requests, and TCP probes. Clipboard, notification, shell-plugin,
filesystem-plugin, and updater-plugin dependencies were not found; absence of
those plugins does not remove the custom command authority above.
`proven-repository`

The shell can return the Keychain-backed API key in
`desktop_get_runtime_auth_config` and `desktop_get_api_key`; the trusted React
client stores it in module memory and attaches it to authenticated Guardian
requests. This is credential injection into the trusted Codexify client, not
permission to expose the credential to remote page content.
`proven-repository`, `documented-contract`

The main-window capability file grants `core:default`. The current Tauri
documentation says registered application commands are allowed to application
windows/webviews by default unless further restricted, while capabilities scope
core/plugin permissions by window or webview. Therefore a future remote renderer
must not share the present command registration and privilege domain without an
explicit capability, origin, IPC-validation, and isolation proof.
`official-source documented`, `working theory`

Remote web content cannot currently reach privileged IPC because the current
application does not load remote web content. This is a repository-topology
observation, not a hostile-content runtime test. If remote content were later
loaded into the current `main` webview, its access posture would require proof
before any safety claim. `proven-repository`, `working theory`

### Security and release posture

`security.csp` is `null`. Tauri documents CSP as active only when configured and
recommends a restrictive policy. A null CSP is not a demonstrated vulnerability
for the current bundled content, but it is not an acceptable proof of remote
renderer containment. `proven-repository`, `official-source documented`

The build surfaces are `make desktop-dev` and `make desktop-build`, ultimately
using `cargo tauri dev` or `cargo tauri build`. The bundle build script stages a
large runtime payload, including backend, Guardian, Compose, scripts, tests, and
frontend assets. No current updater configuration, Developer ID signing
configuration, notarization workflow, or desktop packaging CI was found.
Historical DMG proof shows an ad hoc-signed bundle with a populated runtime
payload, but did not prove user-ready first launch, ready handoff, second launch,
recovery, or production trust. `proven-repository`, `code-path only`

The source contains macOS-specific Keychain, `open`, Docker application, and
runtime-root behavior. A Windows subsystem attribute exists and Tauri supports
multiple desktop platforms, but no current Windows or Linux Browser Host
package/runtime proof exists. `proven-repository`, `official-source documented`

### Gap to a Browser Host

The shell lacks a proven untrusted renderer boundary, remote content lifecycle,
tab model, session/cookie partitioning, popup policy, downloads, browser
history/bookmarks, capture broker, browser permissions, crash recovery,
host/client compatibility negotiation, signed distribution, independent
updater/rollback, and engine security-patch ownership. `proven-repository`

## 11. Current Guardian boundary

Guardian is the policy and persistence authority. It authenticates local
clients with `X-API-Key`, remote clients with session/JWT Bearer credentials,
rejects static local keys in remote mode, applies exposure policy, accepts chat
and task requests, publishes status/events, persists through backend models and
Postgres, and coordinates Redis-backed workers/provider execution.
`proven-repository`, `documented-contract`

The future Browser Host must remain a client of this boundary:

- remote page renderers receive no Guardian credentials;
- the trusted host or companion client owns authenticated Guardian transport;
- page content is untrusted evidence, not authority;
- explicit capture produces a bounded Browser Context Envelope;
- capture does not authorize browser action;
- Guardian remains responsible for server-side policy, durable attachment,
  identity scope, and audit-relevant persistence.

`documented-contract`

## 12. Current build, package, and release surfaces

| Surface | Build and artifact | Signing / updater / version | CI and rollback | Current claim / missing proof |
|---|---|---|---|---|
| Web frontend | Vite build from `frontend/src/`; Docker WebUI build serves static assets with Nginx and proxies Guardian routes (`PR`) | No client signing; package version differs from Tauri/extension versions (`PR`) | Frontend lint/build/test in Guardian CI; rollback is image/source revision (`PR`) | Client surface inside supported Compose path; no independent compatibility guarantee (`DC`) |
| Tauri desktop | `make desktop-build` then Tauri `app` bundle; staged packaged runtime (`PR`, `CP`) | `0.1.0`; no updater; no repo-owned Developer ID/notarization workflow found (`PR`) | No Tauri build/release CI found; rollback remains manual artifact/source selection (`PR`, `U`) | Historical ad hoc DMG is not a production-trusted or end-to-end proven distribution (`CP`) |
| Chrome extension | `cd frontend && pnpm build:chrome-extension`; generated extension directory (`PR`) | Manifest `0.2.0`; no signing/updater ownership (`PR`) | Tests run through frontend test script; no extension artifact-release CI or rollback channel (`PR`) | Manual unpacked continuity bridge only (`PR`, `DC`) |
| Guardian backend | Backend/Docker build and Compose services (`PR`) | Runtime/image versions are repo/config owned; client-protocol package absent (`PR`) | Backend CI, smoke, migration, and Compose surfaces; image/source rollback (`PR`) | Supported local Compose runtime; public exposure remains allowlisted (`DC`) |
| Docker Compose runtime | Root/runtime Compose configurations and `local-beta` image references (`PR`) | Image/config ownership remains in repo; no Browser Host version (`PR`) | Smoke/health/migration checks; operational rollback is deployment-specific (`PR`, `U`) | Current supported path; not proof of an independent browser product (`DC`) |

Version ownership is currently fragmented: Python/Tauri use `0.1.0`, the
frontend package uses `1.0.0`, the extension manifest uses `0.2.0`, and runtime
images use a `local-beta` posture. There is no Browser Host compatibility
version binding these surfaces. `proven-repository`

## 13. Product capability tiers

| Tier | Required capability | Implemented / contract-defined | Proven | Missing proof | Likely owner |
|---|---|---|---|---|---|
| Tier 0 — continuity bridge | Current side panel, Guardian chat, explicit backend-origin permission, no page observation, manual unpacked loading | Implemented in extension; auth governed by ADR-051 (`PR`, `DC`) | Stage 1 automated extension tests; no new live proof (`PT`) | Current dual-auth live browser proof and release artifact (`U`) | Extension client plus Guardian |
| Tier 1 — one-tab Browser Workspace proof | One remote page, URL/title/navigation state, Guardian companion, explicit context capture, renderer isolation, no production claim | Browser Context Envelope and authority rules are contract-defined; host behavior is absent (`DC`, `PR`) | None (`U`) | Same-harness one-tab, isolation, capture, packaging, and observability proof (`U`) | Trusted Browser Host, untrusted renderer, Guardian companion |
| Tier 2 — Browser Host beta | Multi-tab lifecycle, crash recovery, partitioned profiles/sessions, cookies/storage, history/bookmarks, downloads, diagnostics, capture, permission broker, signed package, updater/rollback | Not implemented; selected contracts only cover authority/capture (`PR`, `DC`) | None (`U`) | Functional, security, migration, packaging, signing, updater, rollback, accessibility, and platform proof (`U`) | Browser Host/release owner with Guardian policy boundary |
| Tier 3 — independently releasable browser product | Stable protocol, engine patching, compatibility, release CI, signing/notarization, updater, migrations, backup/recovery, privacy/telemetry, incident response, supported platforms | Not implemented or accepted (`PR`) | None (`U`) | Full release qualification and operating model (`U`) | Independent product, security, release, and protocol owners |

## 14. Browser Host technology-family matrix

These matrices compare capability and ownership questions. They do not score,
rank, or select a family.

### Browser and renderer capabilities

| Dimension | Existing OS-webview / Tauri host | Bundled Chromium / Electron-class | Embedded Chromium / CEF-class | Custom Chromium fork/distribution | Extension-only continuity bridge |
|---|---|---|---|---|---|
| Web compatibility | OS webview; site parity requires proof (`OS`, `U`) | Bundled Chromium capability (`OS`); Codexify proof absent | Embedded Chromium capability (`OS`); proof absent | Chromium compatibility possible; fork delta unknown (`OS`, `U`) | User's Chrome engine (`PR`); no dedicated host |
| Renderer/process isolation | Tauri webview/capability primitives exist; current remote isolation absent (`OS`, `PR`) | Chromium sandbox/context-isolation guidance exists (`OS`); implementation proof absent | Multi-process renderer model documented (`OS`); implementation proof absent | Controllable but wholly operator-owned (`WT`) | Chrome owns site isolation; extension authority remains separate (`PR`, `OS`) |
| Typed host/renderer IPC | Tauri commands exist, but Browser Host schema absent (`PR`) | IPC primitives exist; typed contract remains app work (`OS`, `U`) | Native IPC/process messages exist; typed contract remains app work (`OS`, `U`) | Must be designed and maintained (`WT`) | Extension messages exist; host IPC does not (`PR`) |
| Sessions/cookie partitioning | Framework-specific capability not established here (`U`) | Session/partition APIs documented (`OS`) | Request-context/profile control documented generally; exact design requires proof (`OS`, `U`) | Full engine control with high ownership (`WT`) | Chrome owns profiles/cookies; current extension has no cookie permission (`PR`) |
| Tabs/web-content views | Additional Tauri webviews documented, not used (`OS`, `PR`) | `WebContentsView` supports multiple content views (`OS`) | Browser instances can be embedded (`OS`) | Native Chromium surfaces possible (`WT`) | Existing browser tabs, but no dedicated Browser Host (`PR`) |
| Navigation lifecycle | Current Tauri app has only Codexify navigation (`PR`) | WebContents lifecycle APIs documented (`OS`) | Native browser lifecycle callbacks documented (`OS`) | Must own Chromium lifecycle integration (`WT`) | Browser owns lifecycle; extension does not observe it (`PR`) |
| Popup/new-window policy | Not implemented (`PR`) | Framework hooks documented; policy requires proof (`OS`, `U`) | Client handlers enable policy; proof required (`OS`, `U`) | Fully operator-owned (`WT`) | Chrome owns default policy; extension bridge has none (`PR`) |
| Downloads | Not implemented (`PR`) | Session/webContents download hooks documented (`OS`) | Download handlers available in framework surface; proof required (`OS`, `U`) | Fully operator-owned (`WT`) | Chrome owns downloads; current extension has no permission (`PR`) |
| History/bookmarks | Not implemented (`PR`) | Application feature, not supplied as Codexify behavior (`U`) | Application feature, not supplied as Codexify behavior (`U`) | Fully operator-owned (`WT`) | Chrome owns them; current extension cannot read them (`PR`) |
| DevTools | Webview diagnostics need a defined posture (`U`) | Chromium DevTools capability (`OS`) | Chromium DevTools capability (`OS`) | Chromium DevTools possible; distribution posture owned locally (`WT`) | Chrome DevTools exists; not a Codexify host diagnostic surface (`PR`) |
| Extension compatibility | No proof for Chrome-extension reuse in OS webview (`U`) | Chromium does not imply Chrome Web Store compatibility (`U`) | CEF does not imply Chrome-extension compatibility (`U`) | Possible only with substantial distribution work (`WT`) | Native continuity (`PR`) |
| Permission mediation | Tauri capabilities cover app IPC, not browser permissions (`OS`, `PR`) | Must implement product permission broker (`U`) | Must implement product permission broker (`U`) | Must implement and maintain broker (`WT`) | Chrome mediates extension permissions; current grant is Guardian origin only (`PR`) |
| Page-context capture | Contract exists; host mediation absent (`DC`, `PR`) | Technically plausible; must prove contract-compliant mediation (`WT`) | Technically plausible; must prove contract-compliant mediation (`WT`) | Technically plausible; high ownership (`WT`) | Absent under current permissions (`PR`) |
| Screenshot/document capture | Absent (`PR`) | Engine APIs may enable it; proof and policy required (`OS`, `U`) | Engine APIs may enable it; proof and policy required (`OS`, `U`) | Fully operator-owned (`WT`) | Absent under current permissions (`PR`) |
| Crash recovery | Launcher/runtime recovery is not tab crash recovery (`PR`) | Chromium process events available; product recovery absent (`OS`, `U`) | Process termination callbacks available; product recovery absent (`OS`, `U`) | Fully operator-owned (`WT`) | Chrome owns browser recovery; Codexify state recovery absent (`PR`) |

### Platform, release, and operational properties

| Dimension | Existing OS-webview / Tauri host | Bundled Chromium / Electron-class | Embedded Chromium / CEF-class | Custom Chromium fork/distribution | Extension-only continuity bridge |
|---|---|---|---|---|---|
| Memory/startup footprint | Current shell not measured as host (`U`) | Bundled engine footprint unmeasured (`U`) | Embedded engine footprint unmeasured (`U`) | Custom build footprint unmeasured (`U`) | Incremental extension footprint unmeasured (`U`) |
| macOS | Current shell/build docs and historical artifact exist (`PR`, `CP`) | Officially supported (`OS`) | Official distributions exist (`OS`) | Chromium build supported (`OS`); product proof absent | Current Chrome extension path exists (`PR`) |
| Windows | Framework support, no Codexify proof (`OS`, `U`) | Officially supported (`OS`) | Official distributions exist (`OS`) | Chromium build supported (`OS`) | Likely browser-supported; not qualified here (`U`) |
| Linux | Framework support, no Codexify proof (`OS`, `U`) | Officially supported (`OS`) | Official distributions exist (`OS`) | Chromium build supported (`OS`) | Likely browser-supported; not qualified here (`U`) |
| Accessibility | Current remote-content/browser workflow unproven (`U`) | Chromium accessibility possible; product proof required (`OS`, `U`) | Chromium accessibility possible; product proof required (`OS`, `U`) | Full product qualification burden (`WT`) | Chrome supplies browser accessibility; extension UI proof is separate (`U`) |
| Code signing | Tauri distribution docs exist; repo workflow absent (`OS`, `PR`) | Platform signing required for trusted distribution (`OS`) | Native app signing/distribution remains application-owned (`U`) | Entire distribution trust chain operator-owned (`WT`) | Store/package signing absent; unpacked only (`PR`) |
| Update mechanism | Tauri updater exists but is not configured (`OS`, `PR`) | Auto-updater capability documented; app integration/release server required (`OS`) | Application must own update delivery (`U`) | Entire engine/product updater owned locally (`WT`) | Browser updates extension only after a real distribution channel exists; absent (`PR`) |
| Security patch cadence | OS webview/Tauri dependencies split responsibility; ownership not accepted (`U`) | Electron/Chromium version updates become product responsibility (`OS`, `WT`) | CEF/Chromium updates become product responsibility (`OS`, `WT`) | Direct Chromium security cadence ownership (`WT`) | Chrome owns engine patching; Codexify owns extension security (`PR`) |
| Supply chain | Rust/Tauri plus OS webview and current packaged runtime (`PR`) | Node/Electron plus bundled Chromium (`OS`); exact surface unmeasured | Native CEF binaries/build integration (`OS`); exact surface unmeasured | Chromium source/toolchain/distribution is largest ownership surface (`WT`) | Chrome platform plus current frontend dependencies (`PR`) |
| Test automation | Existing Tauri unit/mock tests; no host E2E (`PR`) | Framework automation exists; Codexify harness absent (`OS`, `U`) | CEF test integration must be built (`U`) | Full harness ownership (`WT`) | Existing extension tests; no host proof (`PT`, `PR`) |
| React UI reuse | Current main React UI is already embedded (`PR`) | Standard web UI reuse is plausible; integration proof absent (`WT`) | Web UI reuse is plausible; bridge/integration proof absent (`WT`) | Possible but high integration ownership (`WT`) | Selected shared contracts already reused, not full app shell (`PR`) |
| Guardian boundary preservation | Possible only with isolated renderer/credential broker proof (`DC`, `U`) | Possible only with isolated renderer/credential broker proof (`DC`, `U`) | Possible only with isolated renderer/credential broker proof (`DC`, `U`) | Possible only with isolated renderer/credential broker proof (`DC`, `U`) | Current extension preserves direct authenticated client boundary, but renderer evidence flow is absent (`PR`, `DC`) |
| Solo-operator fit | Existing familiarity helps; security redesign still material (`PR`, `WT`) | Packaging/engine updates add recurring burden (`WT`) | Native integration and engine updates add recurring burden (`WT`) | Highest apparent maintenance burden; must be measured (`WT`) | Lowest new host burden, but cannot satisfy dedicated-host tiers (`PR`, `WT`) |

Official-source research was retrieved on 2026-07-30 and remained bounded to
primary documentation:

- Tauri: [Capabilities](https://v2.tauri.app/security/capabilities/),
  [Permissions](https://v2.tauri.app/security/permissions/),
  [core permissions](https://v2.tauri.app/reference/acl/core-permissions/),
  [CSP](https://v2.tauri.app/security/csp/),
  [Webview API](https://v2.tauri.app/reference/javascript/api/namespacewebview/),
  [distribution](https://v2.tauri.app/distribute/), and
  [updater API](https://v2.tauri.app/reference/javascript/updater/).
- Electron: [WebContentsView](https://www.electronjs.org/docs/latest/api/web-contents-view),
  [session](https://www.electronjs.org/docs/latest/api/session),
  [security](https://www.electronjs.org/docs/latest/tutorial/security),
  [distribution](https://www.electronjs.org/docs/latest/tutorial/distribution-overview),
  and [autoUpdater](https://www.electronjs.org/docs/latest/api/auto-updater).
- CEF: [General usage](https://chromiumembedded.github.io/cef/general_usage.html)
  and the [official CEF repository](https://github.com/chromiumembedded/cef).
- Chromium: [source/build documentation](https://www.chromium.org/developers/how-tos/get-the-code/),
  [version numbers](https://www.chromium.org/developers/version-numbers/), and
  [release process](https://www.chromium.org/developers/release-process/).

All statements derived from these sources are `official-source documented` or
`working theory`; no repository content, secrets, or private paths were sent.

## 15. Repository-topology matrix

Technology and repository placement remain independent. In particular, Tauri
does not imply the existing app, Electron does not imply a separate repository,
and a dedicated repository does not imply Chromium.

### Coupling, contracts, and build seams

| Criterion | Extend existing desktop app | Separate app/package in monorepo | Dedicated Browser Host repository | Retain extension / defer host |
|---|---|---|---|---|
| Current source coupling | Reuses existing frontend/Tauri coupling (`PR`) | Can share sources initially; boundary must be explicit (`WT`) | Must replace direct imports with published contracts (`WT`) | Preserves current extension coupling (`PR`) |
| Shared frontend imports | Direct reuse available (`PR`) | Workspace/package boundary required (`WT`) | Versioned package/SDK required (`WT`) | Existing selected direct imports remain (`PR`) |
| Guardian API coupling | Existing runtime clients available (`PR`) | Can reuse in-repo clients but must isolate host protocol (`WT`) | Requires versioned API/auth/compatibility contract (`WT`) | Current direct client remains (`PR`) |
| Shared protocol ownership | Repo-local documents/types (`PR`, `DC`) | Monorepo contract package could own it, not yet present (`WT`) | Published source of truth and release policy required (`WT`) | Repo-local ownership remains (`PR`) |
| Independent buildability | Desktop build exists; Browser Host slice does not (`PR`) | Requires new isolated build target (`U`) | Mandatory before split; absent (`PR`) | Extension build exists but is source-coupled (`PR`) |
| Independent testability | Current tests do not isolate a host (`PR`) | Separate test target required (`U`) | Contract/E2E suites required (`U`) | Extension tests exist; no host tests (`PT`) |
| Migration cost | Native privilege isolation inside existing shell may be substantial (`WT`) | New package/app and build boundary (`WT`) | Protocol publishing, CI, release, and migration overhead (`WT`) | Minimal immediate migration; defers Tier 1+ evidence (`WT`) |

### Release and operational ownership

| Criterion | Extend existing desktop app | Separate app/package in monorepo | Dedicated Browser Host repository | Retain extension / defer host |
|---|---|---|---|---|
| Independent release cadence | Conflicts with current launcher/runtime coupling unless separated (`WT`) | Possible with distinct artifact/version workflow (`WT`) | Natural requirement, not current proof (`WT`) | Extension cadence remains undefined (`PR`) |
| Version/compatibility matrix | Needed between host, Guardian, and bundled client (`WT`) | Needed across packages/artifacts (`WT`) | Mandatory across repositories (`WT`) | Needed if extension becomes distributed (`WT`) |
| CI ownership | Existing CI lacks desktop host lane (`PR`) | New monorepo lane required (`WT`) | New repo CI plus cross-repo contract gate required (`WT`) | Current frontend CI runs tests, not release packaging (`PR`) |
| Signing ownership | Could extend desktop release owner; owner not established (`U`) | Must define per-app key custody (`U`) | Dedicated release owner/key custody mandatory (`U`) | Store/package signing owner absent (`PR`) |
| Updater ownership | Existing Tauri updater absent (`PR`) | Per-app updater/channel required (`U`) | Independent updater/channel mandatory (`U`) | Browser store could own transport only after distribution exists (`U`) |
| Security-patch ownership | Desktop owner must absorb engine/webview response (`WT`) | Package/app owner must own cadence (`WT`) | Dedicated repo owner must own engine and release response (`WT`) | Chrome owns engine; Codexify owns extension (`PR`) |
| Issue/review workflow | Existing repo workflow (`PR`) | Existing workflow with component ownership (`WT`) | Cross-repo triage and coordinated releases (`WT`) | Existing repo workflow (`PR`) |
| Rollback complexity | App/runtime coupling complicates rollback (`WT`) | Multiple in-repo artifacts require compatibility rollback (`WT`) | Cross-repo rollback requires compatibility windows (`WT`) | Manual unpacked rollback today (`PR`) |

### Integrity and operator burden

| Criterion | Extend existing desktop app | Separate app/package in monorepo | Dedicated Browser Host repository | Retain extension / defer host |
|---|---|---|---|---|
| Source-of-truth risk | Low file duplication, but shell/host roles may blur (`WT`) | Moderate risk without package ownership rules (`WT`) | High unless protocol source is singular and published (`WT`) | Current source remains singular (`PR`) |
| Duplicated dependencies | Lowest immediate duplication (`WT`) | Possible additional JS/Rust/native graph (`WT`) | Separate dependency graph by design (`WT`) | Current graph unchanged (`PR`) |
| Cross-repository drift | None for host code, though release surfaces can drift (`WT`) | None across repos; package drift still possible (`WT`) | Material risk requiring compatibility automation (`WT`) | None added (`PR`) |
| Atomic Campaign work | Maximum atomicity, but broad blast radius (`WT`) | Preserves atomic commits if package boundaries are disciplined (`WT`) | Cross-repo changes cease to be atomic (`WT`) | Preserves current Campaign atomicity (`PR`) |
| Solo-operator burden | One repo, broader native security surface (`WT`) | One repo, more build/release lanes (`WT`) | Highest coordination and release burden unless seam is mature (`WT`) | Lowest immediate burden, but defers Browser Host capability (`WT`) |

No repository winner is selected. Repository placement must follow a proven,
independently buildable, testable, releasable, signable, versioned, securable,
and operable boundary rather than precede it. `working theory`

## 16. Release-posture matrix

Release posture is a third independent axis; none of these rows dictates a host
technology or repository.

| Posture | Required evidence and ownership | Current applicable evidence | Principal gaps |
|---|---|---|---|
| Development-only proof | Reproducible local build, one-tab harness, isolation/capture assertions, diagnostics | Extension build/tests and Tauri dev/build configuration exist (`PR`, `PT`) | No comparative host harness or one-tab runtime proof (`U`) |
| Internal unpacked or unsigned client | Controlled artifact, installation steps, version identity, operator rollback, risk disclosure | Extension is manually unpacked; historical Tauri DMG was ad hoc signed (`PR`, `CP`) | Host capability absent; no consistent release manifest/rollback proof (`U`) |
| Signed private beta | Signing/notarization, key custody, release CI, update channel, rollback, migration, supported platform, incident owner | No current Browser Host evidence; Tauri metadata only (`PR`) | All trust, update, migration, compatibility, and support proofs (`U`) |
| Independently updatable public browser product | Stable protocols, engine patch SLA, public updater, compatibility windows, privacy/telemetry, backup/recovery, vulnerability response | No current implementation or accepted ownership model (`PR`) | Complete Tier 3 qualification (`U`) |

## 17. Required host/client contract seam

| Seam | Current classification | Required before an independent repository/release |
|---|---|---|
| Guardian endpoint and auth | Already canonical; implemented but not separately packaged; requires live cross-client proof | Versioned public client contract, exposure rules, auth-mode fixtures |
| Browser Context Envelope | Documented but not implemented | Versioned schema, size/content rules, validation fixtures |
| Context attachment | Documented but not implemented | Durable/ephemeral attachment semantics and contract tests |
| Browser-action contract | Missing; requires ADR | Separate action schema, confirmation, authorization, audit, denial semantics |
| Task/request correlation | Already canonical; implemented but not separately packaged | Published identifiers and end-to-end conformance fixtures |
| Canonical status/failure tokens | Already canonical; implemented but not separately packaged | Exported token registry/package and compatibility policy |
| Provider/runtime status presentation | Already canonical in existing runtime contracts; implemented but not separately packaged | Client presentation contract and degradation fixtures |
| User/thread/project/artifact identifiers | Already canonical in APIs/contracts; implemented but not separately packaged | Stable serialized forms, ownership rules, SDK types |
| Capability/permission schema | Documented in principle; missing implementation | Versioned grants, scopes, denial/revocation, feature discovery |
| Export/restore lineage | Already canonical at account level; browser data integration missing | Browser artifact lineage, portability, restore conflict rules |
| Host/client compatibility version | Missing; requires ADR | Negotiated protocol/version range and support matrix |
| Feature negotiation | Missing | Capability advertisement and safe fallback rules |
| Rolling-upgrade behavior | Missing; requires ADR | Mixed-version sequence, backward/forward compatibility windows |
| Deprecation policy | Missing | Notice period, removal gates, migration guidance |
| Generated/published client SDK | Missing | Independently consumable artifact with provenance/version |
| Contract test suite | Missing | Provider/client conformance fixtures runnable in every release lane |

The Browser Host cannot safely leave the repository merely because HTTP routes
exist. Cross-repository safety requires independently consumable contracts,
compatibility negotiation, conformance tests, and release ownership.
`working theory`

## 18. Security and authority ownership map

| Concern | Current owner/state | Required future owner |
|---|---|---|
| Remote renderer isolation | No remote renderer in current shell (`PR`) | Trusted Browser Host process with least-privilege webview/process policy |
| Browser profile/cookie storage | Chrome owns current browser state; Codexify has no host profile (`PR`) | Browser Host profile subsystem, outside Guardian identity/memory |
| Guardian credentials | Extension/main client/Tauri trusted client paths; remote page receives none by contract (`PR`, `DC`) | Trusted companion/host transport, never remote renderer |
| Page-observation permissions | Absent; capture contract requires explicit grants (`PR`, `DC`) | Host permission broker with user-visible scope/revocation |
| Context sanitization | Contract-defined, not implemented (`DC`) | Trusted capture broker plus Guardian validation |
| Host-to-renderer validation | Browser Host IPC absent (`PR`) | Trusted host schema validator with origin/capability checks |
| Command/action confirmation | Browser-action contract absent (`PR`) | Separate future action broker and Guardian policy; requires ADR |
| Filesystem authority | Tauri commands have runtime filesystem authority; remote content absent (`PR`) | Native host, never remote renderer; narrowly scoped capabilities |
| Download handling | Browser Host handling absent (`PR`) | Host download broker with path, consent, scanning, and audit policy |
| Browser history | Browser Host history absent (`PR`) | Host profile subsystem; not Codexify memory |
| Crash dumps | Ownership/policy absent (`U`) | Host/release owner with privacy and retention policy |
| Logs | Existing client/Guardian/runtime logs are fragmented (`PR`) | Host observability owner with redaction and correlation |
| Updates | Browser Host updater absent (`PR`) | Release owner with signed channels and rollback |
| Signing keys | Browser Host key custody absent (`PR`) | Named release/security owner outside source control |
| Vulnerability response | General repository process not evaluated as Browser Host SLA (`U`) | Product security owner with intake, patch, and release SLA |
| Browser-engine patches | Chrome/OS vendor owns current engine delivery; future dedicated host owner unresolved (`PR`, `U`) | Explicitly accepted owner per selected family |

## 19. Data, profile, and migration ownership map

| Data class | Current state | Future ownership and migration rule |
|---|---|---|
| Browser profile data | No Codexify Browser Host profile (`PR`) | Host-owned local profile; versioned migration and backup |
| Cookies/sessions | User's Chrome owns them; extension has no cookie permission (`PR`) | Host-owned browser state, never identity or memory |
| Bookmarks | No Codexify ownership (`PR`) | Host profile feature only if explicitly adopted |
| History | No Codexify ownership (`PR`) | Host profile state, never Codexify identity or memory |
| Download metadata | No Codexify host surface (`PR`) | Host-owned operational state with privacy/retention policy |
| Saved browser artifacts | Browser attachment behavior is contract-level only (`DC`) | Guardian-owned durable artifact with account/project/thread lineage |
| Ephemeral page contexts | Envelope defined, capture absent (`DC`, `PR`) | Request-scoped host capture; no silent persistence |
| Durable page captures | Not implemented (`PR`) | Explicit Guardian attachment/artifact with provenance and consent |
| Atlas migration material | No current proof located (`U`) | Remains unclaimed until source schema, authority, and user consent are proven |
| Account export/restore | Account contract exists; browser classes are not integrated (`DC`) | Extend only through versioned artifact types and lineage-preserving restore |
| Local encryption | Browser Host policy absent (`U`) | Host/profile owner with key storage, rotation, and recovery contract |
| Profile backup | Absent (`PR`) | Host/release owner; explicit inclusion/exclusion of sensitive browser state |
| Host upgrades | No Browser Host migration system (`PR`) | Versioned, atomic, reversible profile/schema migrations |
| Cross-repository schema evolution | No published seam (`PR`) | Single contract source, compatibility windows, SDK and conformance tests |

Browser cookies, sessions, profiles, bookmarks, and history are browser state.
They must not silently become Codexify identity, memory, retrieval material, or
Guardian persistence. `documented-contract`

## 20. Current tests and live-proof coverage

| Surface | Current evidence | Qualification |
|---|---|---|
| Chrome extension | Stage 1 recorded 68 passing tests in five files | `proven-test`; not rerun in this docs-only task |
| Main React frontend | Existing Vite/Vitest and Playwright surfaces; CI runs lint/build/test | `proven-repository`; no new result |
| Tauri bridge | Unit/mocked frontend tests and Rust unit tests are present | `proven-repository`; not executed |
| Desktop packaging | Historical `.app`/DMG proofs show code-path progress and unresolved trust/handoff gaps | `code-path only`; not current release proof |
| Guardian | Backend, auth, route, worker, migration, health, and smoke test surfaces exist | `proven-repository`; not rerun |
| Supported runtime | Current-state documentation identifies local Compose as supported | `documented-contract`; no runtime started |
| Browser Host | No implementation, proof app, one-tab proof, isolation test, capture test, package, updater, or release lane | `unknown` / absent |

No automated runtime tests apply to this docs-only evaluation. Static tests and
historical proof do not substitute for a live Browser Host proof.

## 21. Missing evidence

The following evidence blocks an architecture selection:

1. A common one-tab remote-page proof across the relevant candidate families.
2. Proof that remote content cannot reach Guardian credentials or unrelated
   native commands.
3. Explicit renderer/process, origin, capability, and IPC-validation results.
4. Contract-compliant explicit context capture with bounded data and provenance.
5. Comparable navigation, popup, download, crash, and observability behavior.
6. Comparable cold-start, memory, artifact-size, and build-time measurements.
7. macOS packaging and accessibility results under the same criteria.
8. A credible Windows/Linux proof or a deliberately narrower supported-platform
   decision.
9. Signing, notarization, updater, rollback, and key-custody ownership.
10. Engine security-patch cadence and incident-response ownership.
11. Host/profile migration, backup, local encryption, and recovery design.
12. A versioned host/client seam, feature negotiation, compatibility window,
    published SDK, and conformance suite.
13. Real solo-operator maintenance measurements rather than framework
    reputation or intuition.

All remain `unknown` or `working theory`; none may be converted into a release
claim by documentation alone.

## 22. ADR-readiness classification

`PROOF_REQUIRED`

The authority contract is sufficient to define safe proof criteria, so the
blocker is not a missing governing contract. No accepted decision conflicts
with the Campaign, so the blocker is not governance conflict. The unresolved
issue is comparative evidence: the repository contains no one-tab Browser Host
implementation or common-harness live proof for renderer isolation, context
capture, packaging, observability, resource cost, accessibility, or release
ownership. Selecting topology or repository placement now would elevate
framework documentation and working theory into accepted architecture.

## 23. Proposed future ADR title and decision question

Proposed future ADR title:

> Codexify Browser Host Topology and Release Ownership

Decision question:

> Which Browser Host topology, repository boundary, protocol-ownership model,
> and release-ownership model should Codexify adopt for the first independently
> supportable browser product, given common proof results and the existing
> Guardian and browser-authority invariants?

This question deliberately does not supply the answer.

## 24. Future ADR decision drivers

The future ADR must weigh these non-negotiable drivers:

- Guardian remains policy authority.
- Browser content remains evidence rather than authority.
- Remote renderers receive no Guardian credentials.
- Capture and browser actions remain separate.
- Browser state does not silently become identity or memory.
- Current extension continuity survives migration.
- Production claims require signed and updateable artifacts.
- Engine security-patch ownership is explicit.
- Repository boundaries follow proven build/release seams.
- Independent versioning includes compatibility policy and contract tests.
- The maintenance model is realistic for a solo operator.
- Renderer/process isolation, capability scoping, and IPC validation are
  demonstrated, not inferred.
- Profile, cookie, history, download, backup, migration, privacy, and recovery
  ownership is explicit.
- Partial failure, retry, crash recovery, rollback, and mixed-version behavior
  have defined owners and observable outcomes.

## 25. Repository-split prerequisites

A dedicated Browser Host repository is not safe to create until all of the
following are true:

1. The Browser Host is independently buildable from a declared source root.
2. Its tests do not depend on unversioned relative imports from Codexify.
3. A versioned Guardian/browser contract package or generated SDK exists.
4. Guardian auth, IDs, status/failure tokens, Browser Context Envelope, and
   attachment semantics have conformance fixtures.
5. Host/client compatibility, feature negotiation, deprecation, and
   rolling-upgrade policies are accepted.
6. Cross-repository CI runs the same contract suite on producer and consumer.
7. The artifact is independently packageable, signable, and releasable.
8. Updater, rollback, signing-key, release-channel, and vulnerability-response
   ownership is named.
9. Engine security-patch ownership and cadence are operationally credible.
10. Profile/data schema migration, backup, recovery, and export/restore lineage
    are versioned.
11. Issue/review ownership and coordinated compatibility releases are workable
    for the actual operator.
12. The split preserves a single source of truth and has a reversible migration
    plan.

These prerequisites do not recommend a split; they define the minimum evidence
for considering one. `working theory`

## 26. Known risks

- Treating the current privileged Tauri webview as suitable for remote content
  without isolation proof could expose native commands or credentials.
- Equating framework support with Codexify implementation could create false
  security and release claims.
- Selecting a repository before establishing a consumable protocol seam could
  create duplicated types and cross-repository drift.
- Coupling Browser Host releases to the current packaged runtime could make
  engine security updates slower or rollback more complex.
- A dedicated engine increases supply-chain, binary, patch, and incident burden.
- An OS webview reduces bundled-engine ownership but may introduce platform
  behavior variance that is currently unmeasured.
- An extension-only posture preserves continuity but does not establish the
  dedicated Browser Host required by higher product tiers.
- Browser profile, cookie, history, and capture data can become an unbounded
  privacy surface if ownership and retention are not explicit.
- Version fragmentation already exists across frontend, extension, Tauri, and
  runtime artifacts.
- Historical desktop package proofs may be stale and do not qualify current
  browser behavior.

## 27. Recommended next atomic task

Create a technology-neutral comparative Browser Host proof-harness
specification. The specification must apply the same one-tab, renderer
isolation, authority-contract-compliant context-capture, packaging, and
observability criteria to the relevant candidate families. It must define
acceptance evidence without selecting or implementing a candidate.

This is the only recommended immediate next task.

## 28. Exact commands executed

The following read-only repository commands were executed from
`/Volumes/Dev_SSD/Codexify-main` before drafting:

```sh
wc -l /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
sed -n '1,900p' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
git status --short --branch --untracked-files=all
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git merge-base --is-ancestor 7e338c54236c2b265792778faf8e3a164b3252af HEAD
test -f docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md
test -f docs/architecture/browser-authority-and-context-boundary-contract.md
test -f docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md
test ! -e docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md
rg -n 'Browser Host|repository split|browser topology|Tauri|Electron|CEF|Chromium' /Users/chriscastillo/.codex/memories/MEMORY.md
git ls-files | grep -E '(^|/)(src-tauri|tauri\.conf|capabilities|permissions|electron|chrome-extension|vite\.chrome-extension)'
find frontend -path '*/node_modules' -prune -o -maxdepth 4 -type f \( -iname '*tauri*' -o -iname '*electron*' -o -iname '*browser*' -o -iname '*extension*' \) -print | sort
git grep -n -E 'tauri::command|invoke_handler|Webview|WebviewWindow|WindowBuilder|shell::|updater|bundle|signing|notar|capabilit|permission' -- frontend src-tauri Cargo.toml Cargo.lock package.json Makefile scripts .github 2>/dev/null || true
git grep -n -E 'BrowserWindow|WebContentsView|webContents|session\.fromPartition|contextIsolation|nodeIntegration|partition' -- . ':!frontend/node_modules' ':!frontend/src/node_modules' 2>/dev/null || true
git grep -n -E 'build:chrome-extension|tauri build|tauri dev|cargo tauri|electron-builder|electron-forge|updater|notar|codesign|signing' -- package.json frontend/package.json Makefile scripts .github docs 2>/dev/null || true
git grep -n -E 'GUARDIAN_API_KEY|X-API-Key|Authorization: Bearer|VITE_GUARDIAN_API_BASE|runtimeConfig|runtimeAuth' -- frontend guardian src-tauri 2>/dev/null || true
git grep -n -E 'chrome-extension|Browser Host|browser authority|Browser Workspace|renderer|repository split' -- docs frontend guardian 2>/dev/null || true
rg --files docs/architecture docs/Campaign frontend guardian src-tauri scripts .github | sort
rg -n 'status:|Status:|Accepted|Superseded|Browser Host|browser host|repository' docs/architecture/adr/adr-index.md docs/architecture/adr
```

The current-truth and governing documents were read with bounded `sed`, `rg`,
`wc`, `find`, `git ls-files`, and `git grep` calls, including:

```sh
sed -n '1,260p' docs/architecture/00-current-state.md
sed -n '1,260p' docs/architecture/README.md
sed -n '1,280p' docs/architecture/kb-validity-matrix.md
sed -n '1,320p' docs/architecture/adr/adr-index.md
sed -n '1,320p' docs/architecture/system-overview.md
sed -n '1,320p' docs/architecture/modules-and-ownership.md
sed -n '1,360p' docs/architecture/data-and-storage.md
sed -n '1,360p' docs/architecture/config-and-ops.md
sed -n '1,320p' docs/architecture/tech-debt-and-risks.md
sed -n '1,320p' docs/architecture/agent-protocol-operations.md
sed -n '1,320p' docs/architecture/agent-tool-loop-contract.md
sed -n '1,360p' docs/architecture/self-extending-agent-plugin-system.md
sed -n '1,360p' docs/architecture/account-export-restore-contract.md
sed -n '1,360p' docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md
sed -n '1,420p' docs/architecture/proofs/2026-07-30-codexify-browser-extension-repository-inventory.md
sed -n '1,420p' docs/architecture/browser-authority-and-context-boundary-contract.md
sed -n '1,320p' docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md
sed -n '1,320p' docs/architecture/adr/021-web-agent-boundary-and-retrieval-contract.md
sed -n '1,300p' docs/architecture/adr/040-network-profile-topology-resolution-contract.md
sed -n '1,300p' docs/architecture/adr/039-operator-user-access-boundary.md
sed -n '1,260p' docs/architecture/adr/003-message-identity-vs-request-identity.md
sed -n '1,260p' docs/architecture/adr/004-retrieval-policy-as-control-plane.md
sed -n '1,260p' docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md
```

The implementation and release surfaces were inspected with:

```sh
sed -n '1,260p' src-tauri/tauri.conf.json
sed -n '1,260p' src-tauri/Cargo.toml
sed -n '1,220p' src-tauri/capabilities/default.json
sed -n '1,260p' src-tauri/src/lib.rs
sed -n '1,300p' src-tauri/build.rs
rg -n '^#\\[tauri::command\\]|pub async fn|pub fn|Command::new|reqwest|TcpStream|keychain|security |open |docker|compose|api_key|filesystem|std::fs' src-tauri/src/commands.rs
rg -n 'WebviewWindow|WindowBuilder|Webview|navigate|remote|http://|https://|invoke_handler|generate_handler|plugin\\(' src-tauri
rg -n 'updater|signing|notar|certificate|APPLE_|TAURI_SIGNING|targets|bundle|mainBinaryName|identifier|csp' src-tauri scripts .github Makefile
sed -n '1,240p' frontend/package.json
sed -n '1,240p' frontend/src/package.json
sed -n '1,200p' pnpm-workspace.yaml
sed -n '1,280p' frontend/vite.chrome-extension.config.ts
sed -n '1,260p' frontend/chrome-extension/manifest.json
sed -n '1,300p' frontend/src/lib/runtimeConfig.ts
sed -n '1,260p' frontend/src/lib/runtimeAuth.ts
sed -n '1,320p' frontend/src/lib/api.ts
sed -n '1,320p' frontend/src/lib/guardianEventSource.ts
sed -n '1,240p' frontend/src/App.tsx
sed -n '1,320p' guardian/core/dependencies.py
sed -n '1,280p' guardian/core/public_exposure.py
sed -n '1,300p' guardian/guardian_api.py
sed -n '1,300p' guardian/routes/chat.py
sed -n '1,260p' guardian/routes/health.py
rg -n 'desktop-dev|desktop-build|chrome-extension|frontend|docker|compose' Makefile package.json frontend/package.json
rg -n 'frontend|pnpm|tauri|chrome-extension|docker|compose|build|test|release|sign|notar|updater' .github/workflows
sed -n '1,260p' frontend/Dockerfile.webui
sed -n '1,340p' docker-compose.runtime.yml
sed -n '1,180p' docs/Codexify/macos-beta-packaging.md
sed -n '1,160p' docs/architecture/2026-04-16-dmg-ritual-proof.md
sed -n '1,140p' docs/architecture/2026-04-15-dmg-ritual-proof.md
rg -n '^(#|##)|package beta handoff|beta handoff|Codexify\\.app|DMG|dmg|signed|notar|rollback|update|Result|Status|Conclusion' docs/Codexify/macos-beta-packaging.md docs/architecture/2026-04-16-dmg-ritual-proof.md docs/architecture/2026-04-15-dmg-ritual-proof.md | head -260
```

The task packet was rechecked with:

```sh
rg -n '^#{1,4} |^## |Required|MUST|must|Validation|command|commit|Non-goals|Acceptance|stop|Stop' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt | head -320
sed -n '35,115p' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
sed -n '120,310p' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
sed -n '310,640p' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
sed -n '640,865p' /Users/chriscastillo/.codex/attachments/b473c7ee-1e61-42eb-942e-3042381f21e6/pasted-text.txt
```

Official web documentation was retrieved through bounded search/open operations,
not shell commands. No build, test, runtime, release, signing, updater,
publishing, deployment, or dependency-install command was executed.

## 29. Validation results

The first validation pass executed:

```sh
proof_path='docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md'
test -f "$proof_path"
grep -n 'Browser Host technology-family matrix' "$proof_path"
grep -n 'Repository-topology matrix' "$proof_path"
grep -n 'Release-posture matrix' "$proof_path"
grep -n 'ADR-readiness classification' "$proof_path"
grep -n 'Proposed future ADR' "$proof_path"
grep -n 'Repository-split prerequisites' "$proof_path"
grep -n 'No technology winner' "$proof_path"
grep -n 'No repository winner' "$proof_path"
python3 scripts/validate_docs.py
git diff --check
git diff --name-only
git status --short --branch --untracked-files=all
```

Results:

- File existence: passed.
- All eight required-content checks: passed.
- `python3 scripts/validate_docs.py`: passed with required architecture docs,
  README links, and source headings verified.
- `git diff --check`: passed.
- Scope: the status contained exactly the one authorized untracked proof
  artifact; no tracked or unrelated file was modified.

The final unstaged and staged validation results are recorded by the commit that
contains this artifact and in the task closeout.

Staged-scope validation executed:

```sh
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
test "$(git diff --cached --name-only | wc -l | tr -d ' ')" -eq 1
test "$(git diff --cached --name-only)" = 'docs/architecture/proofs/2026-07-30-codexify-browser-host-topology-repository-boundary-evaluation.md'
git status --short --branch --untracked-files=all
```

Results:

- Cached whitespace validation: passed.
- Cached scope: exactly the one authorized proof artifact.
- Initial cached statistic: one file with 852 inserted lines; this validation
  note was then added to that same file and revalidated before commit.

No automated runtime tests apply.

## 30. ADR impact

Classification: ADR evaluation only. No ADR is created, modified, accepted, or
superseded.

Governing ADRs:

- ADR-051 governs the current Chrome side-panel client and authentication
  posture.
- ADR-021 governs the adjacent web-agent authority boundary.
- ADR-039 governs the operator/user authority boundary.
- ADR-040 governs network profile and trust-boundary posture.
- ADR-003, ADR-004, and ADR-005 govern request/message identity, retrieval
  policy, and runtime/account separation where browser evidence attaches to
  existing flows.

Governing contracts:

- Browser Authority and Context Boundary Contract.
- Account Export + Restore Contract.
- Runtime Protocol Token Contract.
- Chat Runtime Contract.
- Agent Tool Loop Contract.
- Self-Extending Agent Plugin System.

Future ADR surface:

- Browser Host technology and host/renderer topology;
- repository and protocol ownership;
- release, signing, updater, and rollback ownership;
- browser profile/session and migration ownership;
- browser-engine security-patch responsibility.

These decisions change durable architecture ownership and would be dangerous to
reinterpret later. This task gathers evidence only. `documented-contract`

## 31. Documentation follow-through

This proof is the only documentation change. Campaign documents, existing
proofs, ADRs, the ADR index, architecture README, KB validity matrix,
`00-current-state.md`, and all governing contracts remain unchanged.

The next documentation artifact is explicitly deferred to the single atomic
task in section 27. No current-state or release-claim update is warranted.

## 32. Explicit non-claims

- No Browser Host exists or was implemented.
- No one-tab Browser Workspace proof was executed.
- No multi-tab browser, browser profile, cookie store, history, bookmark,
  download, capture, screenshot, or browser-action surface was implemented.
- No host/renderer IPC contract was implemented.
- No technology family was selected, recommended, scored, or ranked.
- No repository topology was selected, recommended, created, or implied.
- No ADR was created, modified, accepted, or superseded.
- No package, lockfile, manifest, build, test, CI, configuration, schema,
  migration, runtime, Campaign, contract, or current-state file changed.
- No dependency was installed.
- No build, runtime, browser, package, signing, notarization, updater, release,
  publishing, or deployment command was run.
- No signed Browser Host package, updater, rollback, release CI, compatibility
  policy, or independent release boundary is proven.
- No framework-documented capability is claimed as Codexify implementation.
- No static test, historical proof, or documentation is presented as current
  live Browser Host proof.
- No browser profile, cookie, session, bookmark, or history is reclassified as
  Codexify identity or memory.
- No repository content was sent to an external model provider.
- No external DeepSeek delegation was used.
- No push occurred.
