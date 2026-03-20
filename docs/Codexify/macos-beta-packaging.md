# Codexify macOS Beta Packaging

## Runtime attachment contract

Codexify now uses a split packaged-runtime contract on macOS:

- app metadata and bootstrap state live in `~/Library/Application Support/Codexify`
- Docker Compose assets, bind-mounted content, and packaged runtime materialization live in `~/Codexify`

This split exists because Docker Desktop bind mounts are expected to come from a Docker-shareable user path. The previous packaged runtime root under `~/Library/Application Support/Codexify` was valid for app-owned metadata, but it is not a reliable primary Compose root for Docker Desktop file sharing.

If Codexify cannot resolve or create either the packaged metadata home or the Docker-compatible packaged runtime root, packaged bootstrap fails with `runtime-root-unavailable` and the workspace stays locked.

## First-run materialization

First-run materialization happens during Tauri startup, before preflight begins.

Bundled resources materialized into `~/Codexify`:

1. detect packaged app context
2. resolve `~/Library/Application Support/Codexify`
3. copy or refresh the packaged runtime attachment into that directory
4. write runtime metadata files
5. continue into the existing bootstrap sequence:
   preflight -> setup -> compose up -> readiness wait -> welcome -> unlock

The app refreshes the same attachment on later packaged launches instead of falling back to repo-root assumptions.

## Materialized runtime attachment

The packaged app materializes the minimum runtime payload needed by the existing setup/bootstrap flow:

- `.env.example`
- `.env.template`
- `backend`
- `docker`
- `docker-compose.yml`
- `guardian`
- `plugins`
- `pytest.ini`
- `requirements`
- `requirements.txt`
- `scripts`
- `tests`

Runtime placeholders created under `~/Codexify`:

- `models`
- `models/bge-large-en-v1.5`
- `.chroma`

The model-weight directory is still only a placeholder in this slice. Model weights are not bundled here.

If the app bundle is missing any required packaged runtime resource, bootstrap fails with `packaged-runtime-assets-missing`.
If copying resources or writing the packaged runtime marker fails, bootstrap fails with `packaged-runtime-materialization-failed`.

The packaged app writes two small metadata files into the runtime home:

- `.codexify-runtime-manifest.json`
- `.codexify-packaged-runtime`

The manifest records the attachment version and the deterministic paths for:

- the runtime home
- the Compose file
- the runtime `.env`
- `.env.template`
- `.env.example`
- the bundle resource root

The model-weight directory is only a placeholder in this slice. Model weights are not bundled.

## Packaged command resolution

This slice only changes where packaged startup resolves its runtime contract:

- packaged setup now writes runtime `.env` state into `~/Codexify`
- packaged Compose commands now resolve `--file`, `--project-directory`, and `CODEXIFY_RUNTIME_ENV_FILE` from `~/Codexify`
- packaged log and restart commands use that same explicit runtime root
- Application Support remains app-owned metadata only and is no longer the primary bind-mounted Compose root

The workspace must remain locked unless Compose startup and readiness truly succeed.

## Failure classification

Packaged bootstrap now distinguishes runtime attachment failures from Docker failures:

- `runtime-root-unavailable`
- `packaged-runtime-assets-missing`
- `packaged-runtime-assets-invalid`
- `packaged-runtime-materialization-failed`
- `packaged-runtime-assets-corrupt`
- `docker-cli-unavailable`
- `docker-cli-execution-failed`
- `docker-cli-found-but-unusable-from-packaged-context`
- `docker-daemon-unavailable`
- `docker-mount-path-unshared-or-unsupported`
- `packaged-setup-failed`
- `packaged-compose-up-failed`
- `packaged-readiness-failed`
- `packaged-bootstrap-unsupported`
- `unexpected-execution-error`

`docker-mount-path-unshared-or-unsupported` is reserved for Docker Desktop rejecting the packaged runtime mount path during Compose startup. It must not be collapsed into a generic Docker-installation or generic startup failure.

## Why the old path failed

The previous packaged runtime root was:

- `~/Library/Application Support/Codexify`

That path worked for app-managed metadata, but Docker Desktop rejected bind mounts there on this machine because the Application Support location was not shared in Docker Desktop file sharing.

The result was a truthful but blocking packaged startup outcome:

- packaged setup could succeed
- packaged `docker compose up -d` failed
- bootstrap stayed locked
- the failure surfaced as packaged compose failure rather than a fake readiness success

Moving the packaged Compose root to `~/Codexify` removes that specific Application Support file-sharing blocker without changing the Compose topology.

## Current limitations

This remains a technical-preview packaged runtime model, not a public-distribution contract.

Known limitations:

- the packaged app still requires Docker Desktop and a reachable Docker daemon
- Finder-launched packaged startup still depends on Codexify reconstructing a Docker-safe subprocess environment
- the app bundle must contain the packaged runtime payload listed above
- model weights are not bundled by this slice
- signing and notarization automation are still out of scope

If packaged bootstrap cannot safely proceed, the workspace remains locked.

## Validated result after this task

Validated code-path contract in this slice:

- packaged metadata home resolves to `~/Library/Application Support/Codexify`
- packaged Compose/runtime root resolves to `~/Codexify`
- packaged runtime payload materialization now targets `~/Codexify`
- packaged setup writes `.env` into `~/Codexify/.env`
- packaged Compose, logs, restart, and readiness now resolve from `~/Codexify`
- Docker Desktop mount-path rejection is classified separately as `docker-mount-path-unshared-or-unsupported`

Validated command results on this machine:

- `pnpm test`: passed
- `cargo check --manifest-path src-tauri/Cargo.toml`: passed
- `cd src-tauri && cargo tauri build`: produced the release executable and `Codexify.app`, then failed during DMG bundling while running `bundle_dmg.sh`

Manual packaged validation on this machine is still incomplete:

- an already-running Codexify window was visible outside `cargo tauri dev`
- a fresh `open -n` attempt against the newly built `Codexify.app` returned Launch Services `kLSNoExecutableErr`
- because a fresh post-build packaged launch could not be confirmed cleanly, this task does not yet prove `~/Codexify` materialization or post-Compose readiness from the rebuilt artifact on this machine

If Compose succeeds but readiness still fails in the next validation pass, bootstrap must remain locked and surface the later classified phase truthfully.

## Production build command

Run from the repo root:

```bash
cd src-tauri && cargo tauri build
```

## Output artifacts

On the validated Apple Silicon build path, the production artifacts are:

- `src-tauri/target/release/bundle/macos/Codexify.app`
- `src-tauri/target/release/bundle/dmg/Codexify_0.1.0_aarch64.dmg`

The plain release executable is also produced at:

- `src-tauri/target/release/app`

## Signing and notarization status

Current artifacts are not developer-signed or notarized.

Observed local status remains:

- app bundle signature: ad hoc
- Team ID: not set
- notarization: not present

This task does not add signing or notarization automation.

## Release posture

Release posture after this task remains `internal-only`.

Even if the Application Support mount-path blocker is fixed, this slice is still not public beta ready because:

- the artifact is not signed or notarized
- packaged startup still depends on local Docker Desktop availability
- this task only fixes the packaged runtime-root contract
- fresh packaged launch validation from the rebuilt artifact is still incomplete on this machine
- any remaining readiness failure must keep the workspace locked

## Packaged startup expectations

For a packaged Finder launch to succeed end to end, the app should:

1. resolve `~/Library/Application Support/Codexify` for app metadata
2. resolve `~/Codexify` for the packaged runtime root
3. materialize the packaged runtime payload into `~/Codexify`
4. run preflight
5. run setup
6. start Docker Compose from `~/Codexify`
7. wait for readiness
8. show the welcome screen
9. unlock the workspace

If any packaged runtime step cannot proceed safely, the workspace must stay locked and the failure must be classified.
