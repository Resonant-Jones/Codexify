# Codexify Browser Host

This directory is the canonical production Browser Host source root established
by [ADR-054](./../docs/architecture/adr/054-browser-host-topology-and-release-ownership.md).
It is deliberately separate from `browser_host_candidates/`, `src-tauri/`,
`frontend/`, and `guardian/`.

## Current status

This package now contains the bounded production one-tab Browser Host runtime,
capture-preview/ephemeral-attachment proof, and development-only Guardian
negotiation plus attachment integration slices selected by ADR-054. It
creates one trusted Electron `BrowserWindow` and one untrusted remote
`WebContentsView`; the explicitly selected Guardian development adapter must
complete compatible negotiation before the remote view is created or loaded.
The deterministic loopback transport remains available only when explicitly
selected for isolated regression proof. Candidate code remains evidence, not
supported release source.

Guardian remains the authentication, policy, persistence, task, and
provider-execution authority. Future remote content remains untrusted evidence;
it will not receive Guardian credentials or native authority. Capture,
attachment, and durable persistence remain separate operations.

The immediate release posture is `development/internal unsigned proof`.
The bounded Guardian development flow explicitly selects the credential-free
Guardian negotiation adapter before remote view creation, then uses the
separate one-use attachment grant. Existing live packets cover the one-tab,
capture, deterministic attachment, and prior attachment-adapter paths; the new
combined negotiation-plus-attachment Electron attempt is currently blocked at
the pinned Electron process-launch boundary. Product and release gates remain
closed: production Guardian authentication, durable persistence, packaging,
signing, updater, and release behavior are not implemented.

The trusted preload exposes state/reload plus explicit selected-text,
visible-page, attach, and cancel actions and `onStateChanged(callback)`. The
remote renderer has no preload, Node, Electron, IPC, credential, filesystem,
process, shell, keychain, updater, Command Bus, or persistence authority. The
proof-only synthetic token is main-process-only and is never written to state
or proof artifacts.

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

# Optional sanitized capture/attachment proof
CAPTURE_PROOF_OUT="$(mktemp -d /tmp/codexify-browser-host-capture.XXXXXX)"
npm run proof:capture -- --output-dir "$CAPTURE_PROOF_OUT"
npm run proof:capture:validate -- --proof "$CAPTURE_PROOF_OUT/proof.json"

# Development-only Guardian attachment-grant integration proof
ATTACHMENT_PROOF_OUT="$(mktemp -d /tmp/codexify-browser-host-guardian-attachment.XXXXXX)"
npm run proof:guardian-attachment -- --output-dir "$ATTACHMENT_PROOF_OUT"
npm run proof:guardian-attachment:validate -- --proof "$ATTACHMENT_PROOF_OUT/proof.json"

# Development-only Guardian negotiation plus attachment proof
NEGOTIATION_PROOF_OUT="$(mktemp -d /tmp/codexify-browser-host-guardian-negotiation.XXXXXX)"
npm run proof:guardian-negotiation -- --output-dir "$NEGOTIATION_PROOF_OUT"
npm run proof:guardian-negotiation:validate -- --proof "$NEGOTIATION_PROOF_OUT/proof.json"

# Live Electron launch diagnostic and deterministic negotiation proof
LIVE_ELECTRON_OUT="$(mktemp -d /tmp/codexify-browser-host-live-electron.XXXXXX)"
npm run diagnose:live-electron
npm run proof:live-electron -- --output-dir "$LIVE_ELECTRON_OUT"
npm run proof:live-electron:validate -- --proof-dir "$LIVE_ELECTRON_OUT"
npm run test:live-electron

# macOS Electron trust-path qualification (macOS only)
MACOS_ELECTRON_OUT="$(mktemp -d /tmp/codexify-browser-host-macos-electron.XXXXXX)"
npm run proof:qualify:macos-electron -- --output-dir "$MACOS_ELECTRON_OUT"
npm run proof:qualify:macos-electron:validate -- --proof-dir "$MACOS_ELECTRON_OUT"
npm run test:macos-electron

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
- No live production Guardian route, production credential, reusable Browser
  Host credential, durable persistence, or supported release path exists. The
  development adapter proof is local-only and explicitly gated.
- Guardian development negotiation is credential-free, local-only, and
  explicitly selected through `guardian_dev_adapter`; it must succeed before
  remote loading. Negotiation and attachment origins must match when both
  adapters are enabled. The deterministic stub remains an explicitly selected
  isolated test transport with no automatic fallback.
- Captured content is held ephemerally in bounded in-memory ticket state and is
  never durably persisted.
- No browser profile, cookies, history, bookmarks, downloads, or durable browser state is defined.
- No signing, notarization, updater, rollback, supported-platform, beta, or public-release claim exists.
- Passing package and contract tests proves only this scaffold and its conformance fixtures.

## Live Electron launch proof boundary

The live launch diagnostic records bounded host, Electron, Playwright, entrypoint,
startup, readiness, negotiation-order, and cleanup evidence without recording
environment dumps, credentials, grants, cookies, tokens, page content, or raw
protocol bodies. Its proof status is one of `passed`, `next-proof-needed`, or
`failed`; `next-proof-needed` is not a pass claim.

The diagnostic and proof runner use the production `src/main.js` entrypoint and
deterministic loopback negotiation only. They must not use `--no-sandbox`, enable
Node integration, disable context isolation, inject credentials, or introduce a
fallback entrypoint. Full real-Guardian process qualification remains a later
task even when this deterministic launch proof passes.

## macOS Electron trust-path qualification

The macOS-only qualification compares a signed Apple control application, the
current locked Electron bundle, and a clean isolated locked install. Each
Electron bundle is checked for architecture, code-signing verification,
Gatekeeper assessment, quarantine presence, SHA-256, and a minimal local
`BrowserWindow` using `nodeIntegration: false`, `contextIsolation: true`, and
`sandbox: true`. The clean workspace contains only the Browser Host package
manifests; Electron's package-provided install hook uses an isolated cache.

The runner never changes Gatekeeper, SIP, quarantine, signing, trust services,
or security databases. It does not use `sudo`, `--no-sandbox`, credentials, or a
real Guardian session. A repository-local `node_modules` reinstall is attempted
only if the Apple control passes, the clean locked install and minimal app pass,
the pinned versions match, and the evidence isolates repository-local
corruption. A `passed` qualification still requires the existing bounded
production-entrypoint live proof; code-signing or `spctl` output alone cannot
qualify the host.

The committed qualification packet is
`docs/architecture/proofs/browser-host/2026-08-02-macos-electron-host-qualification/`.
The current result is `next-proof-needed` with primary classification
`host_code_signing_subsystem_unavailable`: the Apple control app and both exact
arm64 Electron distributions report the same Code Signing subsystem assessment
error, and both minimal Electron launches abort before a window. No dependency
repair or live production-entrypoint rerun was justified.
