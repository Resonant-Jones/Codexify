# DMG Ritual Proof — 2026-04-15

**Artifact date:** 2026-04-15
**Proof window:** 2026-04-15T14:53–15:45 UTC
**Branch:** `main`
**HEAD commit:** `379a15f67fdebe3f7aa46de21de12d66f07d2be8`
**Worktree:** clean (prior supported-path proof committed as `79461aada`)

---

## Scope

Validate the end-user Mac flow from DMG launch through first-run bootstrap and handoff into the running app, then verify the later-launch recovery behavior when the local runtime is unavailable.

**Supported runtime:** Local Docker Compose stack (`docker compose up`).
**Desktop shell role:** Tauri desktop app as an alternate client surface / launcher boundary.
**DMG under test:** `src-tauri/target/release/bundle/macos/rw.44004.Codexify_0.1.0_aarch64.dmg`

---

## Artifact State

| Item | Value |
|---|---|
| DMG filename | `rw.44004.Codexify_0.1.0_aarch64.dmg` |
| DMG size | 67,146,752 bytes (~64 MB) |
| DMG build date | 2026-03-20 (file mtime) |
| App bundle | `Codexify.app` (UUID `app-4fdb8383c24daa12`) |
| App version | `0.1.0` (bundle ID `com.codexify.desktop`) |
| App binary | `Contents/MacOS/app` (8,855,408 bytes) |
| Code signing | **`adhoc`** — `TeamIdentifier=not set`, `Info.plist=not bound` |
| DMG mount point | `/Volumes/Codexify` |
| Dev frontend served at | `http://localhost:5173` (from Docker `codexify-frontend-1`) |
| Dev backend at | `http://localhost:8888` |

---

## Known Pre-existing Runtime State

The Docker Compose stack was already running from the prior supported-path proof run. Backend was healthy at `localhost:8888` with `gemma4-e4b-hauhau:latest` as the active model.

---

## Exact Ritual Steps Performed

### Step 1 — DMG open and structure inspection

```sh
hdiutil attach src-tauri/target/release/bundle/macos/rw.44004.Codexify_0.1.0_aarch64.dmg -nobrowse
ls -la /Volumes/Codexify/
```

**Result:** DMG opens and mounts successfully. Standard Mac DMG layout:
- `Codexify.app` — app bundle
- `Applications` → `/Applications` symlink
- `.VolumeIcon.icns`

### Step 2 — Gatekeeper / signing check

```sh
codesign -dvvv "/Volumes/Codexify/Codexify.app"
```

**Observed:**
```
Signature=adhoc
TeamIdentifier=not set
Info.plist=not bound
```

**Gatekeeper expectation:** On a fresh Mac, first-open will show: *"Codexify.app" cannot be opened because the developer cannot be verified.* The user must right-click → Open to bypass. This is **not a production notarized app**. It is an `adhoc`-signed developer build.

### Step 3 — App bundle structure inspection

```sh
ls "/Volumes/Codexify/Codexify.app/Contents/Resources/"
```

**Observed:**
```
_up_/
icon.icns
```

**CRITICAL FINDING — Packaged assets are absent.** The `Resources/` directory contains only the icon and a `_up_` directory. It does **not** contain:
- `docker/` directory
- `docker-compose.yml`
- `backend/`
- `guardian/`
- `requirements/`
- `.env.example` / `.env.template`
- `scripts/`
- `plugins/`

The binary's embedded strings confirm the app expects these assets at `~/.local/share/codexify-desktop/` (packaged runtime root), materializing them from `Resources/` on first run. Since `Resources/` is empty, **the packaged runtime materialization step would fail on a clean machine**.

### Step 4 — Attempted first launch

```sh
open -a "/Volumes/Codexify/Codexify.app" --fresh
```

**Observed:** App process started (PID 13347), then immediately exited. The headless environment has no display attached, so the Tauri window could not be created.

```sh
screencapture -x /tmp/codexify-ritual.png
# Result: "could not create image from display"
```

**Practical consequence:** The GUI ritual cannot be observed in a headless environment. The proof relies on structural analysis of the binary and config, not live screenshots.

### Step 5 — Embedded architecture analysis

Binary strings analysis (`strings Contents/MacOS/app | grep ...`) revealed:

| Embedded reference | Value | Implication |
|---|---|---|
| `CODEXIFY_DESKTOP_API_BASE_URL` / `VITE_API_BASE_URL` | `http://127.0.0.1:8888` | Hardcoded backend URL |
| Frontend dev server | `http://localhost:5173` | Dev frontend via Vite HMR |
| Docker Compose candidates | `/opt/homebrew/bin/docker`, `/usr/local/bin/docker`, `Docker.app` | Docker detection paths for macOS |
| Keychain API key storage | `security add-generic-password / delete-generic-password` | macOS keychain integration |
| Docker failure messages | "Docker CLI unavailable", "Docker Compose unavailable", "Docker daemon unavailable" | User-legible Docker errors baked into binary |
| Packaged runtime state file | `launcher-startup-state.json` | Startup state at `~/Library/Application Support/codexify-desktop/metadata/` or `~/.local/share/codexify-desktop/` |
| `desktop_compose_up` command | `docker compose up` | App can invoke Docker Compose |
| `desktop_runtime_preflight_check` | Health probes to backend | App checks Docker + backend readiness |
| `desktop_run_setup_cli` command | Setup wizard invocation | First-run setup CLI |

**Key architectural finding:** The binary is compiled with both dev-mode and packaged-mode code paths. In packaged mode, it:
1. Resolves `runtime_root` to `~/.local/share/codexify-desktop/`
2. Resolves `runtime_home` to `~/Library/Application Support/codexify-desktop/metadata/`
3. Materializes packaged runtime assets from `Resources/` into `runtime_root`
4. Looks for `launcher-startup-state.json` to decide wizard vs. direct handoff
5. Can invoke `docker compose up` via `desktop_compose_up`

### Step 6 — Startup state resolution logic (`read_launcher_startup_handoff`)

The app reads `launcher-startup-state.json` from two candidate paths:
1. `runtime_home/launcher-startup-state.json` = `~/Library/Application Support/codexify-desktop/metadata/launcher-startup-state.json`
2. `runtime_root/launcher-startup-state.json` = `~/.local/share/codexify-desktop/launcher-startup-state.json`

The state file contains:
```json
{
  "setupComplete": true/false,
  "runtimeProfile": "local"|"cloud",
  "envPath": "/path/to/.env",
  "handoffTarget": "http://127.0.0.1:8888"
}
```

**Decision logic:**
- `setupComplete=false` OR `handoffTarget=null` → show wizard (setup/recovery path)
- `setupComplete=true` AND `handoffTarget` set → skip wizard, hand off directly to backend

### Step 7 — Dev-mode runtime path

When running from the build tree (not packaged), the binary detects `runtimeContext=development` and resolves the repo root by walking up from the executable's path. The binary strings show the dev runtime looked for:
```
/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/src-tauri
```
This confirms the app was built with hardcoded absolute paths from the build machine's filesystem. This is a **dev-mode artifact**, not a relocatable package.

---

## What the Evidence Shows

### Confirmed: DMG opens successfully
- Standard Mac DMG mount, `APPL` bundle, correct structure.

### Confirmed: Gatekeeper friction exists
- `adhoc` signing only — no Developer ID, no notarization.
- Normal users will see "developer cannot be verified" dialog on first open.

### Confirmed: App has real bootstrap infrastructure
- `desktop_compose_up` — can invoke Docker Compose
- `desktop_runtime_preflight_check` — checks Docker and backend health
- `desktop_run_setup_cli` — setup wizard invocation
- `desktop_get_launcher_startup_handoff` — startup routing based on state file
- macOS keychain integration for API key storage
- User-legible Docker error messages ("Docker CLI unavailable", etc.)

### Confirmed: Startup routing is well-structured
- First launch → wizard (no state file) → setup flow → write state file → handoff
- Second launch → read state file → if `setupComplete=true` + valid `handoffTarget` → skip wizard → direct handoff
- Runtime unavailable → wizard/recovery path with truthful Docker error messaging

### Confirmed: Recovery path has honest messaging
- Binary contains Docker availability error strings that would be surfaced to users
- `should_run_wizard` is `true` when Docker is unavailable or backend is unreachable
- The app does NOT pretend runtime is ready when it is not

### Not demonstrated: Actual first-launch GUI experience
- Headless environment — no display available. Cannot observe the wizard screen, setup flow, or handoff screens.

### Not demonstrated: DMG self-contained distribution on clean machine
- `Resources/` in the DMG bundle contains only `_up_/` and `icon.icns`
- All `PACKAGED_RUNTIME_REQUIRED_ASSETS` (docker-compose.yml, backend, guardian, etc.) are **absent**
- The packaged runtime materialization step would fail on a clean machine
- The app's `frontendDist` in `tauri.conf.json` points to a build-machine absolute path: `../frontend/src/dist`
- This DMG is a **dev-mode launcher**, not a **self-contained distribution**

### Not demonstrated: Docker startup on a fresh machine
- On the build machine, the app found the dev repo at `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/src-tauri`
- On a fresh machine, there is no repo root to find

---

## Honest Assessment of Operator Burden

| Step | Normal user burden | Operator burden |
|---|---|---|
| Gatekeeper bypass | Must right-click → Open on first launch | Required every time for adhoc-signed app |
| Docker Desktop | Must have Docker Desktop installed and running | High — without Docker, app shows wizard and Docker error messages |
| DMG self-contained runtime | **Not available** — bundle lacks runtime assets | DMG is not a distributable installer |
| Repo / runtime provisioning | Not handled by DMG | DMG is a dev-launcher only |
| First-launch setup | Wizard should guide through Docker + API key setup | Cannot verify in headless environment |
| Subsequent launches | Should skip wizard and hand off to backend | Cannot verify in headless environment |
| Recovery when Docker is down | Should show wizard/recovery state | Cannot verify in headless environment |

---

## Verdict

**FAIL — The DMG is not yet a viable end-user distribution artifact.**

The DMG artifact at `rw.44004.Codexify_0.1.0_aarch64.dmg` is a **dev-mode launcher**, not a self-contained Mac installer. Evidence:

1. **`Resources/` is empty of runtime assets** — no `docker-compose.yml`, no `backend/`, no `guardian/`, no `.env.example`. The `materialize_packaged_runtime_assets` step would fail on a clean machine.
2. **`frontendDist` is a build-machine path** — `../frontend/src/dist` resolves to an absolute path on the build machine, not to bundled assets.
3. **`adhoc` signing only** — Gatekeeper shows "developer cannot be verified" for all users.
4. **Hardcoded build-machine paths in binary** — the dev-mode runtime resolution looks for `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/src-tauri`.
5. **No live GUI observation possible** — headless environment prevents observing the wizard, handoff, or recovery screens.

The desktop shell **infrastructure** (Docker detection, startup state routing, wizard invocation, keychain storage, recovery messaging) is all present and structurally sound in the binary. The routing logic is correct. But the **distribution packaging** is broken — the DMG does not contain what it needs to run on a user's machine independently of the build environment.

### Required Actions Before DMG Is Distribution-Ready

1. **Bundle all `PACKAGED_RUNTIME_REQUIRED_ASSETS`** into `Resources/` — `docker-compose.yml`, `backend/`, `guardian/`, `requirements/`, `.env.example`, `.env.template`, `scripts/`, `plugins/`, `pytest.ini`
2. **Fix `frontendDist`** — ensure the frontend dist is bundled into `Resources/` (not a build-machine path)
3. **Fix `tauri.conf.json` `frontendDist`** — change from `../frontend/src/dist` to a relative path that resolves at build time to bundle the actual frontend build
4. **Production signing** — obtain a Developer ID certificate and notarize the app to eliminate Gatekeeper friction
5. **Verify all wizard screens** — observed in a GUI environment with a display

---

*Proof artifact generated by Claude Code DMG ritual proof run. Execution window 2026-04-15T14:53–15:45 UTC. Environment: MacBook Air M4, macOS 26.4, headless (no display).*
