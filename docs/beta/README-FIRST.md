# Codexify Private MacOS Local Beta

This is the private macOS local-beta package for trusted testers.

It is not a public release.

The goal is simple: install Codexify, start it on a Mac, and see whether the local-first app can open, chat, and keep your thread after reopening.

## Before You Start

You will need:

- macOS
- Docker Desktop installed and running
- Ollama installed and running if you are testing the local model path
- The required local model available in Ollama if you stay on the default local path

## First Launch

The first launch may take several minutes.

That is normal.

During first launch:

- Docker images may be pulled
- Runtime files will be created under `~/Codexify`
- The app may look busy before it becomes usable

## Quick Smoke Test

1. Open Codexify.
2. Wait for startup to finish.
3. Send `hello`.
4. Confirm that an assistant response appears.
5. Close Codexify.
6. Reopen Codexify.
7. Confirm that the thread is still there.

If the thread is still there after reopening, the basic local beta loop is working.

## Where Your Runtime Config Lives

Your tester-editable runtime config file is:

- `~/Codexify/.env`

Do not edit the app bundle itself.

In particular, do not edit:

- `/Applications/Codexify.app/Contents/Resources`

## What We Want From You

Please tell us:

- Did it open?
- Did startup complete?
- Did chat work?
- Did reopening preserve the thread?
- What felt confusing?
- What felt helpful?

If something failed, a screenshot of the visible error or diagnostic panel is especially helpful.
