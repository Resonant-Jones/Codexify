# Codexify Electron bundled-Chromium Browser Host candidate

This directory contains a proof-only, unsupported comparative Browser Host
candidate. It is deliberately isolated from production Codexify code and uses
the shared loopback fixture and Guardian-stub harness.

The candidate has three explicit boundaries:

- The trusted Electron main process reads the synthetic credential, owns policy,
  capture, envelope construction, and authenticated stub requests.
- The trusted-shell renderer loads only local candidate assets and receives a
  narrow immutable `contextBridge` API from `trusted-preload.js`.
- The remote renderer is a separate `BrowserWindow` with no preload, no Node
  integration, context isolation, Chromium sandboxing, no `<webview>`, and a
  run-scoped non-persistent session partition.

The remote window is intentionally separate for proof automation. This proves
the trust and interaction boundaries under test; it does not prove an
integrated one-window child-view product UX.

## Candidate-local commands

Run from this directory after dependencies are installed:

```sh
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci
npm run check
npm test
npm run package
```

The exact dependency pins are in `package.json` and `package-lock.json`.
`node_modules`, Electron downloads, package output, proof output, and temporary
user data are ignored and are not part of the committed candidate.

The proof driver is `proof/run-proof.js`. It is invoked by the shared Python
adapter and must receive a harness runtime manifest through
`CODEXIFY_BROWSER_HOST_RUNTIME_MANIFEST`. The proof runtime is loopback-only;
dependency acquisition is recorded separately.

This candidate is not a production browser, does not read production
credentials or configuration, and does not select Electron as Codexify's
Browser Host architecture.
