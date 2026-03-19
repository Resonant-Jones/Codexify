# Codexify macOS beta packaging

## Scope

This runbook covers macOS `.app` launchability for the packaged Codexify desktop build. It does not change or validate the Codexify runtime/bootstrap sequence after the app process starts.

## Build command

Use the packaged-app build, not `cargo tauri dev`:

```bash
cd src-tauri
cargo tauri build --bundles app
```

If the repo is in a stale-lock state, use the same command with the target workaround already required by the local environment and record that exact command in the validation notes. No stale-lock workaround was identified in this task; the current blocker is host disk exhaustion during Rust/Tauri build output.

## Bundle metadata contract

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

## Manual launch validation

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

## Current real status

Configuration status:

- Updated to keep product name, bundle name, and executable identity aligned on `Codexify`.

Validation status on this worktree as of 2026-03-19:

- `pnpm test` did not pass because the host ran out of disk space (`ENOSPC` in temp-file creation).
- `cargo check --manifest-path src-tauri/Cargo.toml` did not pass because the host ran out of disk space (`No space left on device` while linking/writing Rust artifacts).
- `cd src-tauri && cargo tauri build --bundles app` did not complete for the same host-level disk exhaustion reason.
- Because the packaged build did not complete on this host, the expected artifact path `src-tauri/target/release/bundle/macos/Codexify.app` was not emitted in this worktree during this task.
- Because the artifact was not emitted, a fresh manual launch outside `cargo tauri dev` could not be completed in this worktree during this task.

Current conclusion:

- The bundle metadata is now normalized to remove the executable-name drift that likely caused `kLSNoExecutableErr`.
- `kLSNoExecutableErr` is not yet empirically resolved in this worktree because the host could not finish a packaged build.
- The DMG remains blocked after this task. This change only targets `.app` launchability, and the current build/validation run did not reach a state where DMG work would be relevant or unblocked.
