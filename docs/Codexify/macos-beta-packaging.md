# Codexify macOS Beta Packaging

## Scope

This runbook covers macOS `.app` launchability for the packaged Codexify desktop build. It does not change or validate the Codexify runtime/bootstrap sequence after the app process starts.

## Build Command

Use the packaged-app build, not `cargo tauri dev`:

```bash
cd src-tauri
cargo tauri build --bundles app
```

If the repo is in a stale-lock state, use the same command with the target workaround already required by the local environment and record that exact command in the validation notes. No stale-lock workaround was identified in this task.

## Bundle Metadata Contract

Codexify now pins the top-level Tauri bundle identity as:

- `productName`: `Codexify`
- `identifier`: `com.codexify.desktop`
- `mainBinaryName`: `Codexify`
- `bundle.targets`: `["app"]`
- `bundle.macOS.bundleName`: `Codexify`
- `bundle.macOS.bundleVersion`: `0.1.0`

This is the launchability contract for the macOS bundle:

- The emitted app bundle path is expected at `src-tauri/target/release/bundle/macos/Codexify.app`.
- The executable inside the bundle is expected at `src-tauri/target/release/bundle/macos/Codexify.app/Contents/MacOS/Codexify`.
- `Info.plist` must point `CFBundleExecutable` at `Codexify`, not at Cargo's default package/binary name (`app`).

Why this matters:

- In Tauri 2, the bundle executable is no longer renamed to match `productName` automatically.
- This repo's Cargo package is still named `app`, so leaving `mainBinaryName` unset risks a bundle whose visible app name is `Codexify` while the actual executable identity remains `app`.
- That name drift is a credible cause of `kLSNoExecutableErr` and must be eliminated before the `.app` can be trusted as a distribution artifact.

## Manual Launch Validation

After `cargo tauri build --bundles app` completes successfully, validate the emitted bundle outside `cargo tauri dev`:

```bash
test -x src-tauri/target/release/bundle/macos/Codexify.app/Contents/MacOS/Codexify
plutil -p src-tauri/target/release/bundle/macos/Codexify.app/Contents/Info.plist | rg 'CFBundleExecutable|CFBundleIdentifier|CFBundleName'
open -n src-tauri/target/release/bundle/macos/Codexify.app
```

Equivalent Finder validation is acceptable if double-click opens the app normally.

Success criteria:

- `Codexify.app` exists at the expected path.
- `Contents/MacOS/Codexify` exists and is executable.
- `Info.plist` reports `CFBundleExecutable = Codexify`.
- `open -n src-tauri/target/release/bundle/macos/Codexify.app` opens the app without `kLSNoExecutableErr`.
- If the app launches, note whether it proceeds to the existing startup/bootstrap gate. Bootstrap behavior remains a separate concern from this task.

## Current Real Status

Configuration status:

- Updated to keep product name, bundle name, and executable identity aligned on `Codexify`.

Validation status on this worktree as of 2026-03-19:

- `pnpm test` passes after clearing generated Rust artifacts and stale host caches.
- `cargo check --manifest-path src-tauri/Cargo.toml` passes when run with `CARGO_INCREMENTAL=0 CARGO_BUILD_JOBS=1 RUSTFLAGS='-Cdebuginfo=0'`.
- `cd src-tauri && cargo tauri build --bundles app` has been retried after reclaiming disk space, but the packaged build still needs to complete before manual `.app` launch validation can be recorded here.

Launchability posture:

- The bundle metadata is normalized so the `.app` executable identity no longer drifts from the bundle name.
- `kLSNoExecutableErr` is not yet fully closed out in this worktree until the packaged build finishes and the fresh `open -n` validation succeeds.
- The DMG remains blocked after this task. This change only targets `.app` launchability.

## Separate Runtime Work

Packaged runtime attachment and bootstrap detachment are tracked separately from this launchability fix. If runtime home materialization is present in the current branch, keep it out of this bundle-launchability scope and validate it on its own path.
