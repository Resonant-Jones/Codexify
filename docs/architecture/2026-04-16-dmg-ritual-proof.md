# DMG Ritual Proof — 2026-04-16

**Artifact date:** 2026-04-16  
**Proof window:** 2026-04-16T20:04–20:22-0400  
**Branch:** `main`  
**HEAD commit:** `61efb3b3d4c9a8115780bbd400cb751311551ffb`  
**Worktree:** clean

## Scope

Validate the Mac DMG install-and-launch ritual for the current `main` tip after packaged-runtime hardening. The supported runtime remains the local Docker Compose stack. The desktop app is treated as an alternate launcher surface, not a replacement for Compose.

## Tested Artifact / Environment

| Item | Value |
|---|---|
| DMG under test | `src-tauri/target/release/bundle/macos/rw.44004.Codexify_0.1.0_aarch64.dmg` |
| Installed app | `/Applications/Codexify.app` |
| Mounted DMG volume | `/Volumes/Codexify` |
| Runtime stack | Local Docker Compose stack already running and healthy |
| Backend | `http://127.0.0.1:8888` |
| Frontend | `http://127.0.0.1:5173` |

Local runtime conditions during the proof:

| Item | Value |
|---|---|
| Docker Compose status | healthy; backend, db, redis, neo4j, workers up |
| Pre-existing Codexify runtime state | reset before the clean launch by moving `~/Library/Application Support/Codexify` aside |
| GUI capture support | none; `screencapture` could not create an image from display in this session |

## Bundle-Structure Validation

The DMG and installed app bundle are now structurally populated.

Observed inside `Codexify.app`:

```text
Contents/Resources/_up_/frontend/src/dist/index.html
Contents/Resources/_up_/frontend/src/dist/assets/*
Contents/Resources/_up_/docker/entrypoints/backend.sh
Contents/Resources/_up_/docker-compose.yml
Contents/Resources/_up_/backend/*
Contents/Resources/_up_/guardian/*
Contents/Resources/_up_/plugins/*
Contents/Resources/_up_/scripts/*
Contents/Resources/_up_/requirements/*
Contents/Resources/_up_/tests/*
Contents/Resources/_up_/pytest.ini
Contents/Resources/_up_/.env.example
Contents/Resources/_up_/.env.template
Contents/Resources/icon.icns
```

The runtime payload is bundled under `Contents/Resources/_up_/`, which is the correct self-contained packaging shape for the packaged runtime path.

## Ritual Steps Performed

1. Verified the repo was on `main`, recorded `HEAD`, and confirmed the worktree was clean.
2. Identified the exact DMG artifact at `src-tauri/target/release/bundle/macos/rw.44004.Codexify_0.1.0_aarch64.dmg`.
3. Mounted the DMG with `hdiutil attach`.
4. Copied `Codexify.app` from the DMG into `/Applications`.
5. Launched the installed app with `open /Applications/Codexify.app`.
6. Reset the local runtime by moving `~/Library/Application Support/Codexify` aside.
7. Relaunched from the installed app to test first-launch behavior from a clean runtime state.
8. Checked Launch Services, accessibility, filesystem state, and system logs for bootstrap and handoff evidence.
9. Ran the packaged binary directly from `/Applications/Codexify.app/Contents/MacOS/app` as a supporting check.
10. Inspected the local Docker Compose stack to confirm the supported runtime was healthy during the proof window.

## First-Launch Result

I reset the local runtime by moving `~/Library/Application Support/Codexify` out of the way, then relaunched the installed app from `/Applications/Codexify.app`.

Observed results:

1. Launch Services showed `Codexify` as running and in front.
2. Accessibility only exposed the app window shell and standard window controls.
3. `screencapture` failed with `could not create image from display`.
4. After more than 20 seconds, the fresh runtime directory contained only placeholder state:

```text
~/Library/Application Support/Codexify/.chroma
~/Library/Application Support/Codexify/models/
~/Library/Application Support/Codexify/models/bge-large-en-v1.5/
```

5. The expected packaged-runtime artifacts did not appear in the fresh runtime root:

```text
~/Library/Application Support/Codexify/.codexify-runtime-manifest.json
~/Library/Application Support/Codexify/.codexify-packaged-runtime
~/Library/Application Support/Codexify/.codexify-launcher-startup-state.json
```

Interpretation: the app opened, but I did not get a verifiable first-launch bootstrap screen or a completed materialization state. In this session, first launch did not progress to a confirmed usable handoff.

## Setup / Bootstrap Result

The normal setup/bootstrap path could not be completed as a user-facing ritual in this environment.

What I observed:

1. No visible wizard text or actionable controls were exposed through macOS accessibility.
2. No manifest/state files were written into the fresh runtime root.
3. The runtime remained at the placeholder-directory stage only.

What that means:

- The launcher did not reach a proven setup-complete state.
- I could not truthfully claim the wizard path was legible end to end.
- I could not verify the prerequisite messaging or the bootstrap CTA flow from the GUI.

## Ready-Runtime Handoff Result

Not proven.

The local Docker Compose stack was already healthy, but the launcher never produced a confirmed ready handoff target in this clean run. No verified transition into a usable app surface was observed.

## Second-Launch Result

Not verified.

Because the first-launch/setup path did not produce a completed launcher state, I did not have a trustworthy second-launch state to test. I did not fabricate a ready state file to paper over that gap.

## Recovery-Path Result

Not fully exercised.

I did not reach a verified ready state first, so there was no honest later-launch recovery transition to test by making Docker unavailable. The launcher remained at the first-run boundary instead of reaching a ready-to-recover state.

## Signing / Gatekeeper / Trust-Friction Result

The app is still ad hoc signed and not notarized.

Observed signing output for the app bundle:

```text
Signature=adhoc
TeamIdentifier=not set
Info.plist=not bound
Sealed Resources=none
```

`spctl -a -vv` on the bundle returned:

```text
internal error in Code Signing subsystem
```

No explicit Gatekeeper warning dialog was captured in this session, but the trust posture remains weak for ordinary end users. This is not a production-trusted Mac distribution artifact.

## Failures / Ambiguities / Operator Burden

1. The GUI session could not be captured visually in this environment.
2. Accessibility only exposed the app shell, not the bootstrap webview content.
3. The clean launch did not produce the expected manifest or launcher-state files.
4. The setup and handoff paths were not verifiably completed from the user-facing surface.
5. Recovery behavior could not be honestly validated because no ready state was reached first.
6. The proof depends on the pre-existing healthy local Compose stack, which was already up before the desktop launch.
7. Trust friction remains: ad hoc signing, no notarization, and no verified first-open friendliness.

## Verdict

**FAIL**

Bundle structure is now correct, but the actual desktop-launch ritual is not yet friend-safe enough to call this a real end-user distribution artifact. The DMG installs and launches, and the packaged runtime payload is present inside the bundle, but this clean proof run did not complete a verified first-launch bootstrap, did not reach a confirmed ready handoff, and did not prove the second-launch or recovery paths end to end.

### What was proven

- The DMG mounts.
- The app bundle is present and launchable.
- The packaged runtime payload is bundled under `Contents/Resources/_up_/`.
- The local Compose runtime was already healthy.

### What was not proven

- A visible, legible first-run wizard.
- A completed bootstrap/setup ritual.
- A verified handoff into the running local app.
- A verified second launch that skips setup.
- A verified recovery state when the runtime is unavailable.
