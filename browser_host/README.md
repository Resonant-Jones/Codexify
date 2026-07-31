# Codexify Browser Host

This directory is the canonical production Browser Host source root established
by [ADR-054](./../docs/architecture/adr/054-browser-host-topology-and-release-ownership.md).
It is deliberately separate from `browser_host_candidates/`, `src-tauri/`,
`frontend/`, and `guardian/`.

## Current status

This commit establishes a package boundary and a language-neutral,
versioned Guardian/Browser Context contract scaffold. Electron is the accepted
Browser Host family, but Electron is not installed here and no Browser Host
runtime is implemented. Candidate code remains evidence, not production
source.

Guardian remains the authentication, policy, persistence, task, and
provider-execution authority. Future remote content remains untrusted evidence;
it will not receive Guardian credentials or native authority. Capture,
attachment, and durable persistence remain separate operations.

The immediate release posture is `development/internal unsigned proof`.
Product proof and release gates remain closed. This package does not create a
window, renderer, navigation path, capture path, attachment transport, network
connection, persistence path, updater, signed artifact, or production route.

## Local validation

From this directory, using the repository's existing Node/npm installation:

```sh
npm install --package-lock-only --ignore-scripts
npm ls --all
npm run check
npm test
npm run contracts:validate
```

The Python conformance suite consumes the same JSON manifest, schemas, token
registry, and fixtures:

```sh
cd ..
.venv/bin/python -m pytest -v tests/contracts/test_browser_host_contracts.py
```

## Explicit non-claims

- No Electron, Playwright, React, Vite, or other runtime framework is a dependency.
- No live Guardian integration, credential, route, authentication, or provider call exists.
- No BrowserWindow, remote renderer, navigation, browser action, or capture implementation exists.
- No captured content is transported or persisted.
- No browser profile, cookies, history, bookmarks, downloads, or durable browser state is defined.
- No signing, notarization, updater, rollback, supported-platform, beta, or public-release claim exists.
- Passing package and contract tests proves only this scaffold and its conformance fixtures.
