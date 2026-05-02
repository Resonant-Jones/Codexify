# Codexify Private Beta Entry Paths

This private beta has two supported entry paths.

Both paths use the same local backend runtime.

## Release Evidence

Start with [2026-04-30 local beta release evidence](./2026-04-30-local-beta-release-evidence.md) for the validation commands, digests, and proof notes behind this private beta handoff.

The public WebUI zip also includes `Codexify-Beta/AUTHORIZATION.md` for first-launch key setup and recovery.

## Choose Your Path

- macOS desktop app: choose this if you want the Tauri shell on a Mac.
- WebUI Docker bundle: choose this if you are on Linux, Windows, or you want browser-only access.
- macOS users may use either path.

## macOS Desktop App

This is the private macOS local-beta package for trusted testers.

It is not a public release.

The goal is simple: install Codexify, start it on a Mac, and see whether the local-first app can open, chat, and keep your thread after reopening.

### Before You Start

You will need:

- macOS
- Docker Desktop installed and running
- Ollama installed and running if you are testing the local model path
- The required local model available in Ollama if you stay on the default local path

### First Launch

The first launch may take several minutes.

That is normal.

During first launch:

- Docker images may be pulled
- Runtime files will be created under `~/Codexify`
- The app may look busy before it becomes usable

### Quick Smoke Test

1. Open Codexify.
2. Wait for startup to finish.
3. Send `hello`.
4. Confirm that an assistant response appears.
5. Close Codexify.
6. Reopen Codexify.
7. Confirm that the thread is still there.

If the thread is still there after reopening, the basic local beta loop is working.

### Where Your Runtime Config Lives

Your tester-editable runtime config file is:

- `~/Codexify/.env`

Do not edit the app bundle itself.

In particular, do not edit:

- `/Applications/Codexify.app/Contents/Resources`

## WebUI Docker Bundle

This is the browser-first beta path.

Use it when you want the browser UI without the Tauri shell.
This is the low-friction webUI Docker path.
For the small-folder handoff bundle, open `Codexify-Beta/README.md`.

You will need:

- Docker Desktop installed and running
- Ollama installed and running if you are testing the local model path
- The required local model available in Ollama if you stay on the default local path

Normal path:

- `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta` should work from a clean shell without GHCR login.
- `docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta` should also work from a clean shell.

Troubleshooting note:

- If anonymous pulls fail because of GitHub rate limits, stale Docker cache state, or a private fork/mirror, authenticate to `ghcr.io` and retry.
- GHCR login is a fallback for those edge cases, not the normal beta handoff path.

Start the bundle with:

- `docker compose -f docker-compose.webui-runtime.yml up -d`

Open:

- `http://localhost:3000`

The default public handoff bundle in `Codexify-Beta/README.md` starts without requiring Neo4j health. Graph context is optional and should only be enabled when you are explicitly validating graph behavior.

Quick smoke test:

1. Open the webUI in your browser.
2. Wait for startup to finish.
3. Send `hello`.
4. Confirm that an assistant response appears.
5. Refresh the page or restart the Compose stack.
6. Confirm that the thread is still there.

WebUI runtime config lives in the repository root `.env` file used by Docker Compose. Do not edit the macOS app bundle for this path.

If you cannot pull the webUI image from GHCR, use the local rebuild fallback from this repo:

- `bash scripts/verification/check_webui_runtime_bundle.sh`

That script validates the local build and Compose startup path, but it is not registry pull proof.

## What We Want From You

Please tell us:

- Did it open?
- Did startup complete?
- Did chat work?
- Did reopening preserve the thread?
- Which path did you use?
- What felt confusing?
- What felt helpful?

If something failed, a screenshot of the visible error or diagnostic panel is especially helpful.
