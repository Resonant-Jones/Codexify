# Codexify macOS Beta Packaging

## Current contract

Codexify currently produces a real macOS Tauri beta artifact, but the packaged desktop shell is still attached to the local Codexify repo/runtime model.

That means:

- the build emits a real `.app`
- the build emits a real `.dmg`
- the packaged app can only run bootstrap actions safely when it can resolve a local Codexify checkout
- the workspace must remain locked whenever packaged bootstrap cannot safely continue

This is a beta packaging contract, not a signed/notarized public-distribution contract.

## Production build command

Run from the repo root:

```bash
cd src-tauri && cargo tauri build
```

## Current output artifacts

On the validated Apple Silicon build path, the production artifacts are:

- `src-tauri/target/release/bundle/macos/Codexify.app`
- `src-tauri/target/release/bundle/dmg/Codexify_0.1.0_aarch64.dmg`

The plain release executable is also produced at:

- `src-tauri/target/release/app`

## Artifact identity

- Product name: `Codexify`
- Bundle identifier: `com.codexify.desktop`
- App bundle name: `Codexify.app`
- DMG name on the validated Apple Silicon build: `Codexify_0.1.0_aarch64.dmg`

The DMG suffix is architecture-specific. On this machine the validated output is `aarch64`.

## Signing and notarization status

Current beta artifacts are not developer-signed or notarized.

Observed local status:

- app bundle signature: ad hoc
- Team ID: not set
- notarization: not present

This task does not add signing or notarization automation.

## Packaged bootstrap behavior

The packaged macOS beta build now resolves runtime context explicitly instead of assuming the repo root from the shell working directory.

Supported packaged bootstrap context today:

- run `Codexify.app` from inside a Codexify checkout, including the default `src-tauri/target/release/bundle/macos/` build output
- or launch with `CODEXIFY_DESKTOP_REPO_ROOT` pointing at a local Codexify checkout

Classified packaged failure modes:

- `runtime-path-unavailable`
- `repo-runtime-missing`
- `packaged-bootstrap-unsupported`
- `unexpected-execution-error`

The bootstrap overlay now distinguishes:

- Docker missing
- Docker daemon unavailable
- packaged app cannot locate local runtime assets/config
- packaged app launched outside a supported local runtime context
- generic packaged startup failure

## Current known limitations

The packaged beta artifact is not self-contained yet.

Known limitations in the current state:

- setup, Compose startup, log retrieval, and restart actions still depend on the real local Codexify repo/runtime directory
- launching the packaged app outside a Codexify checkout is unsupported unless `CODEXIFY_DESKTOP_REPO_ROOT` is provided
- the validated Finder-launched packaged app still reproduced a Docker CLI execution failure even while Docker Desktop and the Compose stack were healthy; the app stayed locked and surfaced packaged startup support copy instead of unlocking the workspace
- this means packaged bootstrap is supportable and classified, but not yet fully end-to-end reliable outside the development shell

## Manual validation checklist

Use this checklist for packaged beta validation:

1. Run `cd src-tauri && cargo tauri build`.
2. Confirm `Codexify.app` exists under `src-tauri/target/release/bundle/macos/`.
3. Confirm the DMG exists under `src-tauri/target/release/bundle/dmg/`.
4. Launch `Codexify.app` outside `cargo tauri dev`.
5. Confirm the bootstrap overlay appears instead of unlocking the workspace prematurely.
6. If the packaged app resolves the local runtime cleanly, confirm setup, Compose startup, readiness, welcome, and unlock complete in order.
7. If packaged bootstrap does not complete, confirm the failure is classified, the workspace remains locked, and the recovery/support copy matches the real failure mode.
8. Confirm logs/restart actions never pretend the packaged app can operate against a repo/runtime path it has not safely resolved.

## Validated current result

The current validated result on this machine is:

- `cargo tauri build` completed successfully and emitted both `Codexify.app` and `Codexify_0.1.0_aarch64.dmg`
- the packaged app launched outside `cargo tauri dev`
- packaged bootstrap did not proceed end-to-end to welcome/unlock in Finder-launched validation
- the window remained locked on the bootstrap gate, which is the required safety behavior

## Beta download target

The `codexify.space` beta download button should ultimately point at the uploaded DMG artifact for the current beta release lineage, not the raw `.app` bundle.

For the currently validated local artifact shape, that means the hosted equivalent of:

- `Codexify_0.1.0_aarch64.dmg`

If universal or signed/notarized artifacts are introduced later, the download target should move to that release asset without changing the in-app bootstrap contract described here.
