# Electron adjacent-version compatibility proof

- Status: **passed**
- Primary classification: `adjacent_electron_family_incompatibility`
- Host: macOS `26.5.2`, `arm64`; Gatekeeper enabled; Aqua session available
- Apple control: Calculator strict signature verification passed and Gatekeeper accepted
- Stable version-list SHA-256: `f2c27e4c16f880bd27959f364d0b2297abf0c52f113f76479268656e638c6c1d`

## Matrix result

The deterministic roles resolved to Electron `43.2.0` (baseline), `43.1.1`
(lower same-major), `43.3.0` (higher same-major), and `42.8.1` (previous
major). No stable `44.x.x` candidate was present after prerelease exclusion.
All four candidates installed in isolated temporary workspaces with `npm ci`
and exact `npm install --no-save` commands; Electron's install hook completed.
All were arm64 and quarantine-free.

Every installed candidate failed the same bounded strict-signature pattern and
Gatekeeper returned the same bounded Code Signing subsystem pattern. Every
minimal requested-sandbox application terminated with `SIGABRT` before
`app.whenReady()` or window creation. The production Browser Host attempts
also stopped at `electron_binary_check` before trusted-window, preload, state,
negotiation, or remote-load milestones. Cleanup passed for every candidate.
One new diagnostic search found only sanitized boundary indicators (`signing`,
`dyld`, and `trust`); no raw crash report is committed.

Patterns: signature `all_tested_versions`; minimal launch `all_fail`;
production launch `all_tested_fail_same_milestone`.

## Classification boundary

This qualifies `adjacent_electron_family_incompatibility` under the task
precedence: multiple adjacent Electron versions fail minimal startup before
Browser Host code, so the behavior is not demonstrated to be an Electron
43.2.0-specific production regression. Signature evidence alone does not
justify an Electron dependency change. The current Codexify Electron
dependency remains `43.2.0`; no package, lockfile, repository dependency,
runtime source, Guardian code, or release posture changed.

Gate C remains passed. Gate D remains closed. This packet does not qualify a
production Browser Host, a real Guardian process session, persistence, or a
supported release.

## Exactly one next atomic task

Investigate the macOS 26.5.2 Electron family launch incompatibility outside
Codexify runtime code using the bounded matrix evidence.
