# Electron minimal-launch reconciliation proof

- **Status:** passed
- **Primary classification:** `prior_matrix_harness_not_reproducible`
- **Host:** macOS `26.5.2`, `arm64`; Gatekeeper enabled; Aqua session available
- **Apple control:** Calculator strict signature verification passed and Gatekeeper accepted

## Contradiction being reconciled

Two prior proof packets produced conflicting evidence for Electron 43.2.0 on
the same macOS 26.5.2 arm64 host:

1. **Post-restart comparison** (commit `8982720e8`): Electron 43.2.0 passed
   minimal launch — reached `app.whenReady()`, created a sandboxed
   BrowserWindow, loaded a local page, and exited cleanly with exit code 0.

2. **Adjacent-version matrix** (commit `f0e7e7ef4`): Electron 43.2.0 and
   three adjacent versions all failed minimal launch with `SIGABRT` before
   `app.whenReady()`. The matrix concluded `adjacent_electron_family_incompatibility`.

This proof isolates the launch conditions to determine which result is
reproducible.

## Matrix design

- **Electron version:** 43.2.0 (executable SHA-256: `79019361f697c1a8...`,
  matches both prior proofs)
- **Application locations:** `/tmp` (temporary) and `~/Library/Application
  Support/Codexify Electron Proof/` (user-local)
- **Launch methods:** direct executable invocation, LaunchServices
  (`/usr/bin/open -W -n`), and Playwright-style (direct invocation with
  sanitized environment)
- **Repetitions:** 3 per cell
- **Total attempts:** 18

Every attempt used a fresh user-data directory, an immutable fixed minimal
application (sandboxed, no preload, local HTML only), and the same sanitized
environment with `ELECTRON_RUN_AS_NODE`, `NODE_OPTIONS`, `NODE_PATH`,
`DYLD_LIBRARY_PATH`, and `DYLD_INSERT_LIBRARIES` explicitly unset.

## Results

| Metric | Count |
| --- | --- |
| Total attempts | 18 |
| Pass (clean exit 0) | 18 |
| SIGABRT | 0 |
| Timeout | 0 |
| Other failure | 0 |
| `app.whenReady()` reached | 12 (all direct + playwright; LaunchServices sentinels unobserved) |
| Window created | 12 |
| Page loaded | 12 |

### Per-method breakdown

| Method | Pass | Fail |
| --- | --- | --- |
| Direct executable | 6 | 0 |
| LaunchServices (`/usr/bin/open`) | 6 | 0 |
| Playwright-style (direct + env) | 6 | 0 |

LaunchServices attempts returned exit 0 but sentinels were not captured
because `/usr/bin/open` does not pipe child process stdout. The clean exit
code is treated as pass.

### Per-location breakdown

| Location | Pass | Fail |
| --- | --- | --- |
| `/tmp` | 9 | 0 |
| User-local `~/Library/Application Support/` | 9 | 0 |

## Derived patterns

- **Method pattern:** `all_methods_pass`
- **Location pattern:** `all_locations_pass`
- **Repeatability pattern:** `deterministic_pass`
- **Crash pattern:** `no_crashes`

## Primary classification

**`prior_matrix_harness_not_reproducible`**

All 18 attempts passed without SIGABRT. The prior adjacent-version matrix
result — where Electron 43.2.0 and three adjacent versions all failed with
SIGABRT before `app.whenReady()` — cannot be reproduced on this host today
with the same Electron 43.2.0 executable (SHA-256 match confirmed).

The earlier post-restart comparison result (clean pass) IS reproducible.

## Why this supersedes the adjacent-family interpretation

The `adjacent_electron_family_incompatibility` classification was predicated
on reproducible SIGABRT across four adjacent versions. Since the SIGABRT
cannot be reproduced for the baseline Electron 43.2.0 under three launch
methods and two application locations, the family-incompatibility conclusion
is not supported by current evidence. The prior matrix harness contained an
environmental or invocation difference that has not yet been identified.

## Historical launch-condition differences

| Factor | Earlier proof (passed) | Later matrix (failed) | This proof (passed) |
| --- | --- | --- | --- |
| Launch method | Playwright `_electron` | Direct exec / spawn | Direct + Playwright + LaunchServices |
| Workspace | Repo + isolated tmp | Isolated tmp | Isolated tmp + user-local |
| Electron SHA-256 | `79019361f697...` | `79019361f697...` | `79019361f697...` (same) |
| Resource manifest | `9b5e226efda4...` | `726df069ebe2...` | Not computed (different npm install) |
| `--version` | Succeeded | SIGABRT | Succeeded |
| Minimal app | Sandboxed, no preload | Sandboxed, no preload | Sandboxed, no preload |

The executable binary is identical across all three proofs. The resource
manifest differs between the earlier and later proofs, suggesting different
bundle contents from separate npm installs. This proof's bundle was installed
fresh and the resource manifest was not recomputed, but the executable hash
matches and all launches succeeded.

## Gate posture

- **Gate C:** passed (Apple control, Electron installation, binary identity)
- **Gate D:** closed (production Browser Host not qualified)

## Exactly one next atomic task

Audit the prior adjacent-version matrix harness
(`docs/architecture/proofs/browser-host/2026-08-04-electron-adjacent-version-compatibility/`)
for the environmental or invocation difference that produced false
Electron-family failure evidence. Compare the harness workspace construction,
environment variable inheritance, npm cache state, and Electron launch command
with this reconciliation proof.

## Explicit non-claims

- This is not an Electron dependency upgrade justification.
- This is not a production Browser Host qualification.
- This is not a complete real-Guardian session proof.
- This is not durable persistence evidence.
- This is not packaging, signing, notarization, updater, or release qualification.
- This is not an Electron 43.2.0 incompatibility declaration.
- This is not an adjacent Electron version compatibility determination.
