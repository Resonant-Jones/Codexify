# Codexify macOS Beta Packaging

## Current contract

Codexify now has a packaged-safe runtime attachment model for macOS.

The packaged desktop app does not depend on the repo checkout for startup. Instead, it resolves a user-scoped runtime home and materializes the minimum runtime payload there before setup or Compose starts.

Packaged runtime home on macOS:

- `~/Library/Application Support/Codexify`

Implementation detail:

- Tauri resolves the user data directory for the app
- Codexify appends `Codexify`
- that directory becomes the primary packaged runtime home

If the runtime home cannot be resolved or created, packaged bootstrap fails with a classified error and the workspace stays locked.

## Packaged runtime assets

On packaged startup, Codexify expects the app bundle to contain the runtime payload needed for setup, Compose startup, logs, restart, and readiness checks.

Bundled resources currently expected by the packaged app:

- `backend`
- `backend/requirements.txt`
- `backend/requirements-tts.txt`
- `docker`
- `docker-compose.yml`
- `guardian`
- `plugins`
- `pytest.ini`
- `requirements`
- `requirements.txt`
- `scripts`
- `tests`

The packaged app copies those resources into the runtime home on startup.

Runtime placeholders created under the runtime home:

- `models`
- `models/bge-large-en-v1.5`
- `.chroma`

The model-weight directory is only created as a placeholder here. It is not bundled by this slice.

If the app bundle is missing any required packaged runtime resource, bootstrap fails with `packaged-runtime-assets-missing`.
If copying or marker creation fails, bootstrap fails with `packaged-runtime-materialization-failed`.

## Startup order

The bootstrap sequence is unchanged:

1. preflight
2. setup
3. compose up
4. readiness wait
5. welcome
6. unlock

This slice changes what packaged startup does after preflight and how later phases resolve their inputs:

- packaged setup no longer shells out through the repo-oriented Python setup path
- packaged setup now writes the runtime `.env` natively inside the materialized runtime home
- packaged Compose commands now run with explicit `--file`, `--project-directory`, and `CODEXIFY_RUNTIME_ENV_FILE` values rooted in the packaged runtime home
- packaged setup/compose/log/restart commands validate the materialized runtime home before they run instead of assuming repo-root semantics

## Packaged failure classification

Packaged bootstrap now distinguishes these failure modes:

- `packaged-runtime-home-unusable`
- `packaged-runtime-assets-missing`
- `packaged-runtime-assets-invalid`
- `packaged-runtime-materialization-failed`
- `docker-cli-unavailable`
- `docker-cli-execution-failed`
- `docker-cli-found-but-unusable-from-packaged-context`
- `docker-daemon-unavailable`
- `packaged-setup-failed`
- `packaged-compose-up-failed`
- `packaged-readiness-failed`
- `packaged-bootstrap-unsupported`
- `unexpected-execution-error`

The frontend copy now surfaces those cases separately instead of collapsing them into a generic startup failure or defaulting packaged Docker execution issues to "Install Docker Desktop".

Current Docker classification semantics:

- `docker-cli-unavailable`: no usable Docker binary was found after probing the known macOS locations and the normalized `PATH`
- `docker-cli-execution-failed`: Docker was found, but `docker --version` could not execute successfully from the current app context
- `docker-cli-found-but-unusable-from-packaged-context`: Docker was found, but the packaged macOS launch context could not execute it cleanly even after Codexify normalized the subprocess environment
- `docker-daemon-unavailable`: Docker CLI and Compose resolved, but the daemon was not reachable

## Current limitations

This packaged runtime model is still a beta attachment model, not a full public-distribution contract.

Known limitations:

- the packaged app still requires Docker Desktop and a reachable Docker daemon
- Docker Desktop must be configured to share `~/Library/Application Support/Codexify` (or the equivalent packaged runtime home). Without that file-sharing allowance, packaged `compose up` fails when Docker tries to mount `backend`, `guardian`, `docker`, and related runtime-home paths.
- Finder-launched packaged startup still depends on Codexify reconstructing a Docker-safe subprocess environment; if macOS blocks CLI execution in that context, bootstrap stays locked and classifies `docker-cli-found-but-unusable-from-packaged-context`
- the app bundle must contain the packaged runtime payload listed above
- model weights are not bundled by this slice
- signing and notarization automation are still not part of this task

If packaged bootstrap cannot safely proceed, the workspace remains locked.

## Validated current result

On this machine, the packaged app now:

- launches via Finder/open outside `cargo tauri dev`
- resolves and creates the user-scoped runtime home at `~/Library/Application Support/Codexify`
- materializes the packaged runtime payload into that directory
- writes the packaged runtime marker at `.codexify-packaged-runtime`
- keeps the workspace locked unless setup, Compose, and readiness truly succeed
- classifies packaged setup/compose/readiness failures separately instead of collapsing them into a generic bootstrap error
- writes packaged setup state into the runtime home instead of assuming a repo checkout or a repo-local virtualenv

Validated packaged Docker probe shape:

- `PATH=/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin`
- preserve `HOME` when Finder provides it; otherwise reconstruct it from the packaged runtime home or `/Users/$USER`
- preserve `DOCKER_CONFIG` when present; otherwise default it to `$HOME/.docker`
- probe known Docker binaries directly before falling back to `docker` on `PATH`

Validated direct packaged-safe probe results on this machine:

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

1. resolve `~/Library/Application Support/Codexify`
2. materialize the packaged runtime payload into that directory
3. run preflight
4. run setup
5. start Docker Compose from the runtime home
6. wait for readiness
7. show the welcome screen
8. unlock the workspace

If any packaged runtime step cannot proceed safely, the workspace must stay locked and the failure must be classified.
