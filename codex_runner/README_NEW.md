# Pi Runner Notes

This file is a compatibility note for the new Pi wrapper path.

Canonical runner documentation remains [`README.md`](./README.md). Use that doc for the deterministic `runner.py` flow and treat the Pi wrapper as an optional, local-environment feature.

Pi wrapper prerequisites:

- The repo ships a vendored Pi SDK tree under `codex_runner/vendor/pi-coding-agent`, so the normal path does not require a separate Pi install.
- The wrapper reuses the shared Pi auth store at `~/.pi/agent/auth.json`, so an existing Pi login or API-key setup on the same user account is visible automatically.
- If the vendored tree is missing or incomplete, `src/agent-wrapper.js` fails closed with repair guidance instead of guessing a machine-specific path.
