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

- setup runs against the runtime home and receives runtime attachment environment variables
- Docker Compose commands resolve with explicit `--project-directory` and `--file` arguments rooted at `~/Library/Application Support/Codexify`
- `CODEXIFY_RUNTIME_ENV_FILE` points to the runtime-home `.env`
- the packaged runtime manifest path is exported for subprocesses that need deterministic attachment metadata

Development behavior is unchanged:

- repo-attached development continues to resolve the runtime root from the local checkout
- packaged-only materialization does not run for dev/repo-attached flows

## Failure classification

Packaged bootstrap now distinguishes runtime attachment failures from Docker failures:

- `runtime-home-unavailable`
- `packaged-runtime-assets-missing`
- `packaged-runtime-materialization-failed`
- `packaged-runtime-assets-corrupt`
- `docker-cli-unavailable`
- `docker-cli-execution-failed`
- `docker-cli-found-but-unusable-from-packaged-context`
- `docker-daemon-unavailable`
- `packaged-bootstrap-unsupported`
- `unexpected-execution-error`

Meaning:

- `packaged-runtime-assets-missing`: the app bundle is missing part of the packaged runtime payload
- `packaged-runtime-materialization-failed`: first-run/runtime refresh copying did not complete
- `packaged-runtime-assets-corrupt`: the runtime home exists, but the materialized attachment is incomplete after refresh/verification

The bootstrap UI now keeps those cases separate from:

- Docker missing
- Docker daemon unavailable
- packaged startup unsupported in the current context
- generic packaged startup failure

That prevents runtime attachment failures from being mislabeled as “install Docker Desktop.”

## Known limitations

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

Current factual posture:

- suitable for local engineering validation
- not yet a general technical-preview distribution artifact
