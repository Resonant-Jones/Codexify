# Codexify Private Beta Entry Paths

This private beta has two supported entry paths.

Both paths use the same local backend runtime.

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

This is the universal non-macOS beta path.

Use it when you want the browser UI without the Tauri shell.

You will need:

- Docker Desktop installed and running
- Ollama installed and running if you are testing the local model path
- The required local model available in Ollama if you stay on the default local path

Start the bundle with:

- `docker compose -f docker-compose.webui-runtime.yml up -d`

Open:

- `http://localhost:3000`

Quick smoke test:

1. Open the webUI in your browser.
2. Wait for startup to finish.
3. Send `hello`.
4. Confirm that an assistant response appears.
5. Refresh the page or restart the Compose stack.
6. Confirm that the thread is still there.

WebUI runtime config lives in the repository root `.env` file used by Docker Compose. Do not edit the macOS app bundle for this path.

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
