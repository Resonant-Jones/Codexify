# Codexify Browser Host

This directory is the canonical production Browser Host source root established
by [ADR-054](./../docs/architecture/adr/054-browser-host-topology-and-release-ownership.md).
It is deliberately separate from `browser_host_candidates/`, `src-tauri/`,
`frontend/`, and `guardian/`.

## Current status

This package now contains the bounded production one-tab Browser Host runtime
skeleton selected by ADR-054. It creates one trusted Electron `BrowserWindow`
and one untrusted remote `WebContentsView`; a deterministic loopback Guardian
stub must complete compatible negotiation before the remote view is created or
loaded. Candidate code remains evidence, not production source.

Guardian remains the authentication, policy, persistence, task, and
provider-execution authority. Future remote content remains untrusted evidence;
it will not receive Guardian credentials or native authority. Capture,
attachment, and durable persistence remain separate operations.

The immediate release posture is `development/internal unsigned proof`.
The skeleton has live Playwright Electron proof for negotiation ordering,
renderer isolation, loopback navigation policy, permission/popup/download
denial, renderer degradation, and cleanup. Product proof and release gates
remain closed: capture, attachment, persistence, live Guardian integration,
packaging, signing, updater, and release behavior are not implemented.

The trusted preload exposes only `getState()`, `reloadRemote()`, and
`onStateChanged(callback)`. The remote renderer has no preload, Node, Electron,
IPC, credential, filesystem, process, shell, keychain, updater, Command Bus, or
persistence authority. The proof-only synthetic token is main-process-only and
is never written to state or proof artifacts.

## Local validation

From this directory, using the repository's existing Node/npm installation:

```sh
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install
npm ls --all
npm run check
npm run test:unit
npm run test:electron
npm test
npm run contracts:validate

# Optional sanitized proof run
PROOF_OUT="$(mktemp -d /tmp/codexify-browser-host-one-tab.XXXXXX)"
npm run proof:one-tab -- --output-dir "$PROOF_OUT"
npm run proof:validate -- --proof "$PROOF_OUT/proof.json"
```

The Python conformance suite consumes the same JSON manifest, schemas, token
registry, and fixtures:

```sh
cd ..
.venv/bin/python -m pytest -v tests/contracts/test_browser_host_contracts.py
```

## Explicit non-claims

- No React, Vite, or other runtime framework is a dependency; Electron and
  Playwright are exact-pinned development dependencies for this skeleton and
  its local proof driver.
- No live Guardian integration, credential, route, authentication, or provider call exists.
- No browser action, capture, attachment, or durable persistence implementation
  exists beyond the one-tab navigation/policy skeleton.
- No captured content is transported or persisted.
- No browser profile, cookies, history, bookmarks, downloads, or durable browser state is defined.
- No signing, notarization, updater, rollback, supported-platform, beta, or public-release claim exists.
- Passing package and contract tests proves only this scaffold and its conformance fixtures.
