# Codexify Browser Extension and Repository Inventory Proof

## Artifact date

2026-07-30

## Branch and HEAD

- Repository root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/establish-browser-campaign`
- Inspection HEAD: `c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b`
- Baseline worktree: clean; branch matched
  `origin/codex/establish-browser-campaign`
- Execution lane: `architecture-impact`
- Task kind: `proof`

## Foundation commit verification

The required foundation commit is
`c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b`. At task start:

```text
$ git rev-parse HEAD
c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b

$ git merge-base --is-ancestor \
    c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b HEAD
exit 0
```

The Campaign and Task 01 foundation was therefore present at the exact
inspection revision.

## Scope

This artifact inventories the checked-in Chrome side-panel source, its
configured build/output relationship, Guardian API seam, tests, browser
permissions, and repository coupling. It makes no source, generated-output,
package, build, runtime, configuration, Campaign, Task, current-state, or ADR
change.

The output is repository inspection plus one non-mutating focused test run. A
current extension build was not run because the source/output relationship was
already statically decidable and the task required a residue-free worktree.

DeepSeek delegation was not used. The execution packet prohibited external
repository transmission, the provider acknowledgement was absent, and the
previously failed external-provider preflight was not retried.

## Evidence posture

| Classification | Meaning in this artifact |
|---|---|
| `proven-repository` | Direct Git, filesystem, build-config, import, or manifest evidence at the inspection HEAD |
| `proven-test` | Observed passing result from the focused extension suite in this task |
| `proven-code-path` | A reachable-looking checked-in path whose live Chrome/backend execution was not exercised here |
| `documented-contract` | Governing architecture or operator documentation, not implementation proof by itself |
| `working-theory` | Evidence-backed recommendation requiring a later decision or proof |
| `unknown` | Not established by the inspected repository or this task |

## Executive finding

`frontend/chrome-extension/` is the canonical, fully tracked extension source.
`frontend/vite.chrome-extension.config.ts` builds that source to the ignored,
generated path `frontend/dist/chrome-extension`.

`frontend/dist/chromeextension` (without the second hyphen) is not source,
output, or a second build path at this HEAD. It is absent, untracked, and only
incidentally covered by the root `dist/` ignore rule. No repository build,
packaging, installation, CI, Tauri, or documentation reference identifies it as
an output.

The existing client is a private Manifest V3 side-panel chat application. It
does not discover an active browser tab, inject a script, read the DOM, capture
selected text, create page-context payloads, or attach browser context to a
thread or project. Its current browser-to-Guardian path is:

```text
toolbar action
  -> MV3 side panel
  -> explicit exact-origin permission request
  -> local API-key or remote Bearer profile
  -> Guardian chat/profile/task HTTP and SSE APIs
  -> Guardian-owned thread/message persistence
```

The smallest stable edit boundary is the repository root with
`frontend/chrome-extension/` as the extension-specific source subtree. Future
extension work should remain in Codexify until a Browser Host exists and an ADR
proves an independently buildable, releasable, signable, versioned, and
securable boundary.

## Repository paths inspected

Primary source and build paths:

- `frontend/chrome-extension/`
- `frontend/vite.chrome-extension.config.ts`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `pnpm-workspace.yaml`
- `.gitignore`

Shared frontend imports:

- `frontend/src/theme/index.ts`
- `frontend/src/contracts/runtimeTokens.ts`
- `frontend/src/contracts/userAccentTokens.ts`
- `frontend/src/lib/guardianEventSource.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/persona/layout/AppShell.tsx`

Governance and proof:

- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md`
- `docs/tasks/CODEXIFY_BROWSER_01_EXTENSION_AND_REPOSITORY_INVENTORY.md`
- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/chrome-side-panel-client.md`
- `docs/architecture/web-agent-spec.md`
- `docs/architecture/proofs/2026-06-23-trusted-remote-browser-codex-proof.md`

Packaging and integration searches covered `Makefile`, `scripts/`, `.github/`,
`frontend/src-tauri/`, and `frontend/src/`. No extension packaging, CI, or
Tauri integration was found outside the paths recorded below.

## Canonical extension source

### Source authority

| Surface | Canonical path | Evidence | Classification |
|---|---|---|---|
| Extension root | `frontend/chrome-extension/` | All 18 maintained files are returned by `git ls-files --stage`; history begins with `09213fa4f` | `proven-repository` |
| Manifest source | `frontend/chrome-extension/manifest.json` | Vite reads this exact file and emits it as `manifest.json` | `proven-repository` |
| Side-panel HTML | `frontend/chrome-extension/sidepanel.html` | Manifest `side_panel.default_path` names `sidepanel.html`; Vite names it as an input | `proven-repository` |
| Side-panel TypeScript entry | `frontend/chrome-extension/src/main.tsx` | `sidepanel.html` loads `/src/main.tsx`; it renders `SidePanelApp` | `proven-repository` |
| UI root | `frontend/chrome-extension/src/SidePanelApp.tsx` | Imported and rendered directly by `main.tsx` | `proven-repository` |
| Background/service worker | `frontend/chrome-extension/service-worker.ts` | Vite input; manifest output refers to `service-worker.js` | `proven-repository` |
| Guardian adapter | `frontend/chrome-extension/src/codexifyExtensionApi.ts` | Direct authenticated fetch/SSE adapter for Guardian routes | `proven-code-path` |
| Origin/auth profile | `frontend/chrome-extension/src/connectionProfile.ts` | URL normalization, exact-origin match pattern, auth-mode model, permission client | `proven-code-path` |
| Browser storage adapter | `frontend/chrome-extension/src/chromeStorage.ts` | Local profile storage and session-scoped remote credential storage | `proven-code-path` |
| Markdown renderer | `frontend/chrome-extension/src/MarkdownMessage.tsx` | Separate safe Markdown component; does not import AppShell | `proven-test` |
| Extension styles | `frontend/chrome-extension/src/sidepanel.css` | Imported by `main.tsx` and bundled by Vite | `proven-repository` |
| Chrome type boundary | `frontend/chrome-extension/src/chrome.d.ts` | Declares only runtime, sidePanel, storage, and permissions APIs used by source | `proven-repository` |
| Operator runbook | `frontend/chrome-extension/README.md` | Documents build and unpacked-load flow | `documented-contract` |

### Maintained source-file disposition

Every tracked file under the canonical source directory has the following
owner/build disposition:

| Tracked file | Owning role | Build disposition |
|---|---|---|
| `frontend/chrome-extension/README.md` | Extension operator documentation | Not emitted; describes build/load/reload/smoke flow |
| `frontend/chrome-extension/manifest.json` | Extension manifest source | Copied unchanged to output `manifest.json` by the custom Vite plugin |
| `frontend/chrome-extension/service-worker.ts` | MV3 lifecycle/action worker | Compiled to fixed output `service-worker.js` |
| `frontend/chrome-extension/sidepanel.html` | Side-panel HTML entry | Vite processes and emits `sidepanel.html` |
| `frontend/chrome-extension/src/MarkdownMessage.tsx` | Safe assistant-message renderer | Bundled into the side-panel JavaScript graph |
| `frontend/chrome-extension/src/SidePanelApp.tsx` | Side-panel state and UI root | Bundled into the side-panel JavaScript graph |
| `frontend/chrome-extension/src/__tests__/MarkdownMessage.test.tsx` | Markdown renderer tests | Test-only; no runtime artifact |
| `frontend/chrome-extension/src/__tests__/SidePanelApp.test.tsx` | Side-panel component/workflow tests | Test-only; no runtime artifact |
| `frontend/chrome-extension/src/__tests__/codexifyExtensionApi.test.ts` | Guardian adapter/auth/task tests | Test-only; no runtime artifact |
| `frontend/chrome-extension/src/__tests__/connectionProfile.test.ts` | Profile, origin, and storage tests | Test-only; no runtime artifact |
| `frontend/chrome-extension/src/__tests__/userAccentTokens.test.ts` | Shared accent-token contract tests | Test-only; no runtime artifact |
| `frontend/chrome-extension/src/chrome.d.ts` | Local Chrome API type boundary | Compile-time input only; no standalone runtime artifact |
| `frontend/chrome-extension/src/chromeStorage.ts` | Extension connection/session storage adapter | Bundled into the side-panel JavaScript graph |
| `frontend/chrome-extension/src/codexifyExtensionApi.ts` | Guardian HTTP/SSE adapter | Bundled into the side-panel JavaScript graph |
| `frontend/chrome-extension/src/connectionProfile.ts` | URL, auth profile, and origin-permission contract | Bundled into the side-panel JavaScript graph |
| `frontend/chrome-extension/src/main.tsx` | React bootstrap entry | Vite entry imported by `sidepanel.html`; bundled into hashed JavaScript |
| `frontend/chrome-extension/src/sidepanel.css` | Extension-specific visual styles | Emitted as hashed CSS and linked from processed HTML/bundle |

The Git inventory returned 17 tracked files under this directory, all accounted
for above. No icon, content-script, injected-script, public asset, second
manifest, or packaging file exists under the source root.

### Manifest and entrypoint findings

`frontend/chrome-extension/manifest.json` declares:

- Manifest V3, version `0.2.0`;
- minimum Chrome version `116`;
- required permissions: `sidePanel`, `storage`;
- optional origin declarations: `http://*/*`, `https://*/*`;
- module service worker: `service-worker.js`;
- side-panel default path: `sidepanel.html`;
- toolbar action title only.

It declares no:

- `host_permissions`;
- `content_scripts`;
- `activeTab`, `tabs`, `scripting`, `debugger`, `webRequest`, `cookies`, or
  `downloads` permission;
- icons or other packaged public assets;
- `web_accessible_resources`;
- explicit `content_security_policy`.

The absence of an explicit manifest CSP is `proven-repository`. The effective
Chrome MV3 default CSP was not exercised or browser-inspected here and remains
`unknown` for this proof.

The service worker only configures
`chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true})` at initial
evaluation, installation, and browser startup. It contains no profile, fetch,
credential, message, task, DOM, tab, or command behavior.

### AppShell and Tauri relationship

The side panel does not mount `frontend/src/App.tsx` or
`frontend/src/components/persona/layout/AppShell.tsx`. It renders its own
`SidePanelApp`.

It directly reuses four checked-in frontend sources:

- theme variable injection from `frontend/src/theme/index.ts`;
- request-state tokens from `frontend/src/contracts/runtimeTokens.ts`;
- user-accent tokens from `frontend/src/contracts/userAccentTokens.ts`;
- authenticated SSE behavior from
  `frontend/src/lib/guardianEventSource.ts`.

No extension reference was found in `frontend/src-tauri/`, and the extension
does not import `@tauri-apps/api`. Tauri and the extension share the broader
frontend repository/dependencies but have separate entry, build, state, and
packaging paths.

## `frontend/dist/chromeextension` classification

### Exact no-hyphen path

`frontend/dist/chromeextension` is:

- absent at `c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b`;
- absent from `git ls-files`;
- matched by `.gitignore:56` through the general `dist/` rule;
- absent from the Vite configuration, package scripts, Makefile, scripts,
  `.github/`, Tauri configuration, source imports, operator README, and
  extension architecture document.

Classification: **ignored absent path, not a configured output**.

It is not proven to be stale output because no bytes or history exist at the
inspected path. It is not partially tracked or manually assembled. No evidence
supports more than one build producer.

### Configured hyphenated path

`frontend/dist/chrome-extension` is:

- absent at the inspection HEAD;
- absent from `git ls-files`;
- matched by `.gitignore:56` through the general `dist/` rule;
- the sole `outputRoot` in `frontend/vite.chrome-extension.config.ts`;
- configured with `emptyOutDir: true`;
- named by the extension README as the directory loaded with Chrome's **Load
  unpacked** flow.

Classification: **ignored generated output, currently absent**.

No checked-in generated bytes exist to compare against current source. Current
source/output byte parity is therefore `unknown`.

## Source-to-output map

| Generated or packaged path | Owning source | Build/copy step | Git state at HEAD | Runtime role | Evidence | Confidence |
|---|---|---|---|---|---|---|
| `frontend/dist/chrome-extension/manifest.json` | `frontend/chrome-extension/manifest.json` | Custom Vite `emit-chrome-extension-manifest` plugin reads and emits the source unchanged | Ignored; absent | MV3 declaration | Vite config lines 12-23 | `proven-repository` |
| `frontend/dist/chrome-extension/sidepanel.html` | `frontend/chrome-extension/sidepanel.html` | Vite HTML input processing | Ignored; absent | Side-panel document | Vite input plus manifest `default_path` | `proven-repository` |
| `frontend/dist/chrome-extension/service-worker.js` | `frontend/chrome-extension/service-worker.ts`, `frontend/chrome-extension/src/chrome.d.ts` | Vite/Rollup service-worker input; fixed `service-worker.js` entry name | Ignored; absent | Toolbar-to-side-panel lifecycle | Vite input/output config | `proven-repository` |
| `frontend/dist/chrome-extension/assets/sidepanel-<hash>.js` and possible shared chunks | `src/main.tsx`, `SidePanelApp.tsx`, `MarkdownMessage.tsx`, `codexifyExtensionApi.ts`, `connectionProfile.ts`, `chromeStorage.ts`, plus shared frontend imports | Vite React/Rollup bundle; hashed entry/chunk patterns | Ignored; absent | Side-panel React UI, storage, auth, Guardian chat/SSE | Import graph and output patterns | `proven-code-path` |
| `frontend/dist/chrome-extension/assets/<name>-<hash>.css` | `src/sidepanel.css` plus Vite-processed CSS imports | Vite asset emission with hashed naming | Ignored; absent | Side-panel styling | `main.tsx` CSS import and asset pattern | `proven-code-path` |
| None | `src/__tests__/*` | Vitest only; not a Rollup input | Tracked source; no runtime output | Focused verification | Test config includes only `src/__tests__` | `proven-test` |
| None | `frontend/chrome-extension/README.md` | No build step | Tracked source | Operator instructions | Git and repository search | `proven-repository` |
| None | icons/public assets | No source files and `publicDir: false` | Absent | No icon bundle | File inventory and Vite config | `proven-repository` |

The exact hashed bundle filenames and emitted chunk partition are `unknown`
because this task did not run the build. The configured artifact classes and
ownership are still directly established by the source/import graph and Vite
configuration.

## Build and packaging flow

### Package and command

- Package manager: pnpm.
- Extension package root: `frontend/`.
- Lockfile: tracked `frontend/pnpm-lock.yaml`.
- Root workspace: `pnpm-workspace.yaml`; it declares `frontend/src`, while the
  extension build is a script in the `frontend` package.
- Exact operator command:

```bash
cd frontend
pnpm build:chrome-extension
```

- Script expansion:

```text
pnpm --dir src exec vite build --config ../vite.chrome-extension.config.ts
```

- Bundler: Vite with React and Rollup.
- Source root: `frontend/chrome-extension`.
- Output: `frontend/dist/chrome-extension`.
- Clean behavior: `emptyOutDir: true`.
- Source maps: disabled.
- Public directory: disabled.
- Extension-specific required environment variables: none referenced by the
  script, Vite configuration, or extension source.

The command uses already declared dependencies. No dependency installation or
lockfile change is part of the build contract.

### Loading and packaging

Development/operator installation is manual:

1. run the build command;
2. open `chrome://extensions`;
3. enable Developer mode;
4. choose **Load unpacked**;
5. select `frontend/dist/chrome-extension`.

No Web Store, CRX, ZIP, signing, updater, release-publishing, CI build, Make
target, Tauri bundle, or production packaging path was found.

The repository is configured to reproduce the unpacked artifact from checked-in
source and locked dependencies. This task did not run a build, so successful
current-HEAD emission and byte-for-byte reproducibility are `unknown`, not
claimed.

## Current browser workflow

### Implemented side-panel chat path

1. The user clicks the extension toolbar action.
2. The MV3 service worker asks Chrome to open the native side panel.
3. Chrome loads `sidepanel.html`, whose `main.tsx` renders `SidePanelApp`.
4. On first connection, the user enters a Guardian backend URL and selects
   local API-key or remote account-session mode.
5. The client normalizes the URL, derives `${origin}/*`, and calls
   `chrome.permissions.request` from the submit gesture.
6. Local mode creates a profile carrying the Guardian API key. Remote mode
   sends username/password directly to `/api/auth/login`, discards the password,
   and creates a Bearer-session profile.
7. The client verifies `/ping` reachability and authenticated thread listing
   before saving the profile.
8. It lists or creates Guardian chat threads, persists a user message, then
   requests completion with root request and turn identifiers.
9. It observes the accepted task through authenticated per-task SSE, rejects
   explicitly mismatched correlation, and waits for terminal evidence.
10. On completion it re-reads the Guardian-persisted transcript. It does not
    synthesize the assistant reply from event payloads.

### Browser-context and capture path

No current path exists for:

- active-tab discovery;
- passive page metadata;
- page permissions beyond the configured Guardian backend origin;
- content-script or injected-script execution;
- page DOM or selection extraction;
- screenshot capture;
- page-context payload creation;
- browser-context transfer into AppShell or Guardian;
- page-context attachment to a thread or project;
- durable saved page artifacts;
- protected-page classification.

Therefore there is no implemented protected-page failure path to evaluate. The
current side-panel chat remains available because page capture is not part of
this client at all. Any capture and browser-specific failure states belong to
the next browser-authority contract, not this implementation.

### Persistence and attachment behavior

- Guardian/Postgres owns threads and messages.
- The extension stores one selected Guardian thread ID as derived client state.
- A new extension-created thread contains a title only; no project ID or page
  context is attached by this source.
- The extension local profile stores URL, auth mode, timestamps, selected
  thread, and a local API key only in local mode.
- The remote token is session-scoped; the remote password is request-local.
- The user accent is persisted through Guardian `/api/user/profile`, not Chrome
  storage.

## Guardian and browser-context integration

The extension page calls these Guardian surfaces directly:

- `/ping`;
- `/api/auth/login` and `/api/auth/logout` in remote mode;
- `/api/chat/threads`;
- `/api/chat/{thread_id}/messages`;
- `/api/chat/{thread_id}/complete`;
- `/api/tasks/{task_id}/events`;
- `/api/tasks/{task_id}/cancel`;
- `/api/user/profile`.

Local mode attaches only `X-API-Key`. Remote mode attaches only
`Authorization: Bearer`. Absolute discovery URLs are rejected when their origin
differs from the configured backend origin.

This is a browser-to-Guardian chat integration, not a browser-context attachment
integration. The Web Agent and Continuity browser-context documents describe
future contracts only.

## Authority and security boundaries

| Question | Current evidence | Classification |
|---|---|---|
| Where are Chrome APIs called? | Service worker: `chrome.sidePanel`; connection profile: `chrome.permissions`; storage adapter: `chrome.storage.local/session` | `proven-repository` |
| Is remote-page content treated as untrusted? | No remote page is read. Persisted assistant Markdown disables raw HTML and strips unsafe link protocols. General remote-page intake remains future work. | `proven-test` for Markdown; `not applicable` for page capture |
| Where are credentials held? | Local API key exists in extension-page state/profile and `chrome.storage.local`; remote token exists in extension-page state and `chrome.storage.session`; remote password is form/request-local | `proven-code-path` |
| Is a Guardian API key exposed to extension code? | Yes in explicit local mode. It is not exposed to a remote page because there are no content scripts or page bridge. | `proven-code-path` |
| Can a renderer invoke Codexify actions? | The trusted extension page can create threads, write messages, request/cancel completion, and update accent under its credential. Remote web pages have no bridge. | `proven-code-path` |
| Does it have command-bus/tool authority? | No command-bus route, UI, permission, or source reference exists in the extension. | `proven-repository` |
| Origin scope | Manifest declares broad optional HTTP(S) origins, but runtime requests exactly one normalized `${origin}/*` permission and rejects cross-origin discovery URLs | `proven-test` and `proven-code-path` |
| Browser storage | Local connection profile/local key in trusted-context local storage; remote token in trusted-context session storage; no sync storage | `proven-test` |
| Cookies/session access | No cookies permission or `chrome.cookies` use; login uses `credentials: "omit"` and subsequent auth uses explicit headers | `proven-code-path` |
| Filesystem access | No filesystem/download permission or API reference | `proven-repository` |
| Confirmation gates | Connection submission plus Chrome origin-permission prompt; explicit send/cancel/disconnect gestures | `proven-test` |
| CSP | No explicit manifest CSP; effective Chrome default not inspected | `unknown` beyond manifest absence |
| Compromised Chrome profile/host | README warns it can inspect an active extension credential; no application-level encryption is claimed | `documented-contract` |

The repository does not prove that browser storage is inaccessible to a
compromised host, that Chrome enforces the intended effective CSP in a given
installation, or that a live remote deployment sends only the inspected
headers. Those require browser/runtime proof.

## Test and proof coverage

Observed command:

```bash
cd frontend
pnpm test:chrome-extension
```

Observed result:

```text
Test Files  5 passed (5)
Tests       68 passed (68)
```

Warnings:

- Node reported `--localstorage-file` without a valid path for test workers.
- The warning did not fail tests.
- Vitest created an ignored
  `frontend/chrome-extension/node_modules/.vite` cache; the exact generated
  directory was removed, and subsequent Git status was clean.

| Surface | Coverage | Classification | Limit |
|---|---|---|---|
| Connection URL, origin pattern, local profile, remote session separation, malformed storage | `connectionProfile.test.ts` | `proven-test` | jsdom/mocked Chrome storage |
| Local versus remote auth headers, login/logout, completion correlation, cancellation | `codexifyExtensionApi.test.ts` | `proven-test` | mocked fetch/event inputs |
| First run, connection, restore, chat, completion terminal distinction, cancel, disconnect, accent behavior | `SidePanelApp.test.tsx` | `proven-test` | component tests, not Chrome |
| Safe Markdown and unsafe-protocol/raw-HTML handling | `MarkdownMessage.test.tsx` | `proven-test` | renderer unit tests |
| Shared accent token contract | `userAccentTokens.test.ts` | `proven-test` | token registry only |
| Manifest structure | Direct inspection only | `proven-repository` | no automated manifest schema check found |
| Build | Vite config and historical documentation | `proven-code-path` | current build not executed |
| Original local unpacked load/action | `chrome-side-panel-client.md` records a live screenshot | `documented-contract` with historical live-proof claim | does not cover current dual-auth/accent HEAD |
| Trusted remote browser flow | `2026-06-23-trusted-remote-browser-codex-proof.md` | historical `next-proof-needed` | normal web app proof, not this extension |
| Dual-auth extension in live Chrome | Required by ADR-051 proof surface | `unknown` | no current live packet found |
| Page capture/active tab/protected pages | No implementation or tests | `unproven` | future contract and implementation |
| Web Store/signing/update/recovery | No implementation or tests | `unproven` | future release work |

## Stable source-boundary recommendation

### Recommended edit boundary

- Edit extension-specific behavior only under
  `frontend/chrome-extension/`, plus the smallest directly required shared
  frontend contract or Vite/package file when a separately approved task names
  it.
- Never edit `frontend/dist/chrome-extension` or
  `frontend/dist/chromeextension` directly.
- Regenerate unpacked output with:

```bash
cd frontend && pnpm build:chrome-extension
```

### Ownership map

- Extension-specific: `frontend/chrome-extension/`.
- Extension build ownership: `frontend/vite.chrome-extension.config.ts` and
  `frontend/package.json`.
- Shared Codexify UI/contracts: theme, runtime tokens, accent tokens, and
  Guardian SSE under `frontend/src/`.
- Guardian/browser contract: ADR-051,
  `docs/architecture/chrome-side-panel-client.md`, and the Guardian routes
  called by `codexifyExtensionApi.ts`.
- Generated output: `frontend/dist/chrome-extension`.

A directory-scoped project rooted only at `frontend/chrome-extension` cannot
safely see the shared imports, package scripts, lockfile, Guardian route
contracts, ADR-051, or build configuration. Future extension work should remain
rooted at the Codexify repository root with an explicit narrow write scope.

## Repository-topology assessment

### Recommendation

**Remain in Codexify until the Browser Host exists.**

Do not split the current extension. If a future Browser Host establishes a
stable seam, consider a monorepo package boundary before any repository split,
then let the repository-topology ADR decide whether an independently released
host moves out.

### Evidence

| Factor | Current state | Implication |
|---|---|---|
| Coupling | Direct imports from four `frontend/src` sources and direct reliance on Guardian chat/profile/task contracts | Current extension is not repository-independent |
| Independent buildability | Separate Vite input/output, but dependencies resolve through the frontend package and `frontend/src/node_modules` | Buildable as a target, not yet a standalone package |
| Release/signing | Manual unpacked load only; no signing, updater, CI, or release owner | No proven release seam to split |
| Shared contracts | Auth mode, request states, accent tokens, SSE semantics, persistence, and task correlation are shared | Split would require versioned contract packaging first |
| Tests | Tests use shared frontend setup and dependencies | A split would require harness extraction or duplication |
| Versioning | No cross-repository protocol or compatibility matrix | Independent releases would introduce drift risk |
| Migration cost | Imports, package resolution, test setup, docs, and Guardian API ownership would need separation | Cost is unjustified before Browser Host proof |
| Security ownership | Guardian owns auth/policy; extension owns Chrome permission/storage behavior | Boundary is real but not independently governed for release |

Conditions that could justify a later split:

1. an accepted Browser Host and renderer-authority ADR;
2. a versioned Guardian/browser protocol;
3. standalone package/build/test boundaries;
4. independent signing, update, rollback, and recovery ownership;
5. a compatibility matrix and rolling-upgrade policy;
6. explicit secret, storage, filesystem, and command-authority isolation;
7. live proof that the host can be built and released without repository-local
   assumptions.

## Known gaps and risks

- No current generated artifact exists to compare with source.
- The current extension build was not run in this task.
- No current live Chrome proof covers the dual-auth/accent HEAD.
- No automated manifest schema or permission regression test was found.
- The manifest has no explicit CSP; effective Chrome default behavior was not
  inspected.
- Local mode deliberately places a Guardian API key in extension-local storage;
  host/profile compromise remains a credential risk.
- Broad optional HTTP(S) origins exist in the manifest even though runtime
  requests one exact origin.
- No active-page capture, protected-page failure, browser-context provenance,
  or browser-to-project attachment contract exists.
- No packaging, signing, updater, rollback, or release ownership exists.
- Direct shared-source imports make isolated extension repository work unsafe.
- Existing browser proof documents cover other browser contexts or earlier
  extension revisions and must not be promoted to current release proof.

## Decision-gate result

### Gate A: Source authority — PASS for inventory

The canonical source, manifest, service worker, UI entry, shared imports, build
command, configured output, ignore rule, manual load path, and absence of a
second output producer are established from repository evidence.

This PASS permits future source-scoped work to name the correct paths. It does
not prove a current build, live Chrome behavior, Web Store packaging, or
release readiness.

### Gates B through D — not evaluated or not satisfied

- Browser authority: not yet contracted for capture/actions/Browser Host.
- Repository split: no ADR or independently releasable host boundary.
- Product proof: no Browser Host or live feature proof.

## Recommended next atomic task

**Define the browser authority and context-boundary contract.**

This is the immediate Campaign prerequisite because source authority is now
established and no repository evidence requires source repair or build
stabilization before the contract stage. The task should define user,
extension/renderer, future Browser Host, Guardian, origin, capture, provenance,
confirmation, storage, protected-page, and failure boundaries. It must not
select a Browser Host technology, create a repository, or implement capture.

This artifact does not generate or execute that task.

## Exact commands executed

Repository gate:

```bash
git status --short --branch --untracked-files=all
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git merge-base --is-ancestor c7d4510c178ebbc2f23612b67fe2b41ae9af1b8b HEAD
```

Task-required inventory:

```bash
find docs/Campaign -maxdepth 2 -type f | sort | head -80
find docs/tasks -maxdepth 2 -type f | sort | head -80
find frontend -path '*/node_modules' -prune -o -type f \
  \( -name 'manifest.json' -o -name 'manifest.*.json' \) -print | sort
find frontend -path '*/node_modules' -prune -o -type d \
  \( -iname '*extension*' -o -iname '*chrome*' -o -iname '*browser*' \) -print | sort
git grep -n -E '"side_panel"|"Codexify Side Panel"|chrome\.(tabs|permissions|scripting|sidePanel)' -- frontend docs
git grep -n -E 'chromeextension|chrome-extension|web-extension|browser-extension' -- package.json frontend scripts Makefile docs .github
git ls-files --stage -- frontend/chrome-extension frontend/dist/chromeextension frontend/dist/chrome-extension
git status --ignored --short -- frontend/chrome-extension frontend/dist/chromeextension frontend/dist/chrome-extension
git check-ignore -v frontend/dist/chromeextension frontend/dist/chrome-extension
git log --follow --oneline -- frontend/chrome-extension/manifest.json
```

Additional bounded inspection:

```bash
find frontend/chrome-extension -type f | sort
git log --oneline --all -- frontend/vite.chrome-extension.config.ts frontend/chrome-extension frontend/package.json
git log -p --follow -- frontend/vite.chrome-extension.config.ts
rg -n --hidden -g '!frontend/node_modules/**' -g '!frontend/src/node_modules/**' \
  -g '!.git/**' \
  'build:chrome-extension|dist/chrome-extension|dist/chromeextension|chrome-extension|Codexify Side Panel' \
  .github scripts Makefile frontend/src-tauri frontend
rg -n 'activeTab|chrome\.tabs|chrome\.scripting|content_scripts|content_security_policy|host_permissions|optional_host_permissions|web_accessible_resources|cookies|downloads|debugger|webRequest' \
  frontend/chrome-extension docs/architecture/chrome-side-panel-client.md
rg -n 'from [\"'\"']\.\./\.\./src|AppShell|Tauri|tauri' \
  frontend/chrome-extension frontend/vite.chrome-extension.config.ts \
  docs/architecture/chrome-side-panel-client.md
pnpm test:chrome-extension
```

The exact ignored Vitest cache created by the test run was removed:

```bash
rm -rf /Volumes/Dev_SSD/Codexify-main/frontend/chrome-extension/node_modules
```

No dependency install, build, deployment, release, repository creation, push,
or external delegation command was run.

## Validation results

At draft time:

- Foundation ancestry: passed.
- Required repository and Git inspection: completed.
- Focused extension tests: passed, 5 files and 68 tests.
- Test residue: removed.
- Unauthorized tracked changes: none before this proof file.
- Documentation validator and final staged-scope checks: pending the completed
  artifact, recorded at closeout rather than preclaimed here.

## ADR impact

- Classification: aligned with existing ADR-051.
- Existing governing ADR:
  `docs/architecture/adr/051-chrome-side-panel-dual-auth-client-contract.md`.
- ADR created, amended, accepted, or superseded: none.
- Future ADR evaluation remains required for Browser Host topology, renderer
  authority, browser-session ownership, cross-repository protocol, signing and
  release ownership, and any permanent repository split.

This proof gathers evidence only and makes no permanent Browser Host decision.

## Documentation follow-through

- This artifact completes Browser Campaign Stage 01 inventory.
- The next task should author the Browser authority/context-boundary contract.
- The repository-topology/Browser Host ADR remains downstream of that contract.
- `docs/architecture/00-current-state.md` is unchanged because this proof does
  not widen the supported beta surface.
- Campaign and Task documents are unchanged.

## Explicit non-claims

This artifact does not claim:

- that Codexify Browser or a Browser Host exists;
- that the extension captures or understands an active page;
- that protected-page failure behavior is implemented;
- that a current extension build succeeds or matches absent output bytes;
- that the current dual-auth/accent source passed live Chrome proof;
- that any Web Store, signing, updater, compatibility, migration, or recovery
  path exists;
- that Atlas browser data was exported or restored;
- that browser state is durable identity or memory;
- that autonomous browsing, browser actions, command-bus access, or page
  injection exists;
- that a repository split is approved;
- that the supported beta release surface changed.
