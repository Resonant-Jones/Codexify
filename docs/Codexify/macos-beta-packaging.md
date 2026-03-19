# Codexify macOS Beta Packaging

## Runtime attachment contract

Packaged Codexify no longer treats the repo checkout as its runtime root.

On macOS, the packaged desktop shell resolves one stable user-scoped runtime home:

- `~/Library/Application Support/Codexify`

Implementation detail:

- Tauri resolves the user data directory with `app.path().data_dir()`
- Codexify appends `Codexify`
- the packaged command layer treats that directory as the runtime root for setup, Compose, logs, restart, and recovery

If the app cannot resolve or create that directory, packaged bootstrap fails with `runtime-home-unavailable` and the workspace remains locked.

## First-run materialization

First-run materialization happens during Tauri startup, before preflight begins.

Packaged launch flow:

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

The packaged app also creates these runtime-only placeholders inside the runtime home:

- `models`
- `models/bge-large-en-v1.5`
- `.chroma`

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

In packaged mode, desktop commands no longer assume repo-root working-directory layout.

Packaged command behavior:
This slice changes what packaged startup does after preflight and how later phases resolve their inputs:

- packaged setup no longer shells out through the repo-oriented Python setup path
- packaged setup now writes the runtime `.env` natively inside the materialized runtime home
- packaged Compose commands now run with explicit `--file`, `--project-directory`, and `CODEXIFY_RUNTIME_ENV_FILE` values rooted in the packaged runtime home
- packaged setup/compose/log/restart commands validate the materialized runtime home before they run instead of assuming repo-root semantics

- setup runs against the runtime home and receives runtime attachment environment variables
- Docker Compose commands resolve with explicit `--project-directory` and `--file` arguments rooted at `~/Library/Application Support/Codexify`
- `CODEXIFY_RUNTIME_ENV_FILE` points to the runtime-home `.env`
- the packaged runtime manifest path is exported for subprocesses that need deterministic attachment metadata

Development behavior is unchanged:

- repo-attached development continues to resolve the runtime root from the local checkout
- packaged-only materialization does not run for dev/repo-attached flows

## Failure classification

Packaged bootstrap now distinguishes runtime attachment failures from Docker failures:

- `packaged-runtime-home-unusable`
- `packaged-runtime-assets-missing`
- `packaged-runtime-assets-invalid`
- `packaged-runtime-materialization-failed`
- `packaged-runtime-assets-corrupt`
- `docker-cli-unavailable`
- `docker-cli-execution-failed`
- `docker-cli-found-but-unusable-from-packaged-context`
- `docker-daemon-unavailable`
- `packaged-setup-failed`
- `packaged-compose-up-failed`
- `packaged-readiness-failed`
- `packaged-bootstrap-unsupported`
- `unexpected-execution-error`

Meaning:

- `packaged-runtime-assets-missing`: the app bundle is missing part of the packaged runtime payload
- `packaged-runtime-materialization-failed`: first-run/runtime refresh copying did not complete
- `packaged-runtime-assets-corrupt`: the runtime home exists, but the materialized attachment is incomplete after refresh/verification
- the packaged app still requires Docker Desktop and a reachable Docker daemon
- Docker Desktop must be configured to share `~/Library/Application Support/Codexify` (or the equivalent packaged runtime home). Without that file-sharing allowance, packaged `compose up` fails when Docker tries to mount `backend`, `guardian`, `docker`, and related runtime-home paths.
- Finder-launched packaged startup still depends on Codexify reconstructing a Docker-safe subprocess environment; if macOS blocks CLI execution in that context, bootstrap stays locked and classifies `docker-cli-found-but-unusable-from-packaged-context`
- the app bundle must contain the packaged runtime payload listed above
- model weights are not bundled by this slice
- signing and notarization automation are still not part of this task

The bootstrap UI now keeps those cases separate from:

- Docker missing
- Docker daemon unavailable
- packaged startup unsupported in the current context
- generic packaged startup failure

That prevents runtime attachment failures from being mislabeled as “install Docker Desktop.”

## Known limitations
- launches via Finder/open outside `cargo tauri dev`
- resolves and creates the user-scoped runtime home at `~/Library/Application Support/Codexify`
- materializes the packaged runtime payload into that directory
- writes the packaged runtime marker at `.codexify-packaged-runtime`
- keeps the workspace locked unless setup, Compose, and readiness truly succeed
- classifies packaged setup/compose/readiness failures separately instead of collapsing them into a generic bootstrap error
- writes packaged setup state into the runtime home instead of assuming a repo checkout or a repo-local virtualenv

This task only detaches packaged runtime state from the repo and materializes first-run assets.

Known limitations that remain:

- Docker Desktop is still required
- a reachable Docker daemon is still required
- packaged setup still depends on a usable Python runtime with the Guardian/Codexify Python dependencies available; this slice does not bundle that interpreter environment
- model weights are not bundled
- the app is still unsigned and not notarized
- this slice does not redesign bootstrap UI
- this slice does not change Docker Compose topology
- this slice does not add signing or notarization automation

If materialization, preflight, setup, or Compose cannot proceed safely, the workspace stays locked.

## Release posture

The DMG is still blocked for broader technical-preview distribution.

Reason:

- runtime detachment is implemented, but this slice alone does not remove the local Docker dependency
- runtime detachment is implemented, but the packaged setup path still depends on host Python packages that are not bundled into the beta artifact
- the app is still ad hoc signed / unsigned for distribution purposes and not notarized
- technical-preview distribution should wait until packaged end-to-end bootstrap is consistently validated on the produced artifact, not just repo-attached or partial startup paths
- `/Applications/Docker.app/Contents/Resources/bin/docker --version`: success
- `docker compose version`: success
- `docker info --format '{{json .ServerVersion}}'`: success

Validated post-preflight packaged startup behavior in this slice:

- native packaged setup can materialize the runtime `.env` contract inside `~/Library/Application Support/Codexify`
- packaged Compose startup now resolves its compose file, project directory, and env file from the runtime home instead of the repo root
- the next concrete blocker on this machine is `packaged-compose-up-failed` when Docker Desktop rejects mounts under `~/Library/Application Support/Codexify` because that path is not shared in Docker Desktop file sharing

Current end-to-end status on this machine:

- welcome/unlock is not yet reached from the packaged artifact
- the bootstrap should remain locked and surface the compose-stage failure truthfully instead of pretending the runtime is ready

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

Observed local status:

- app bundle signature: ad hoc
- Team ID: not set
- notarization: not present

This task does not add signing or notarization automation.

## Release posture

The DMG remains an internal-only artifact rather than a developer beta or public beta.

Reason:

- it is not signed or notarized
- packaged startup still depends on local Docker Desktop availability and Docker Desktop file-sharing configuration for the packaged runtime home
- this validation did not reach welcome/unlock end to end from the packaged artifact
- the runtime payload is local-materialized, not fully self-contained

## Packaged startup expectations

For a packaged Finder launch to succeed end-to-end, the app should:

Current factual posture:

- suitable for local engineering validation
- not yet a general technical-preview distribution artifact
