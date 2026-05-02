## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-05-02

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in late beta hardening on `main`. The codebase now carries both the local Docker Compose path and the packaged tester-facing delivery surfaces, including the macOS desktop shell and the public webUI handoff bundle. Release truth still depends on the live runtime matching the supported local-first posture, not just on docs or build artifacts.

- Public webUI beta handoff docs and the GHCR pullability note were added on `main`.
- A public webUI handoff bundle was packaged for tester distribution.
- Mainline release docs were refreshed to reflect the current beta packaging story.
- The desktop shell and runner/TUI work were refined on `main`, but that does not change the release gate by itself.

- Local Docker Compose remains the supported install path.
- The packaged macOS desktop shell remains part of the beta delivery surface.
- The public webUI Docker bundle is available for browser-only tester use.
- The supported beta story remains local-first and backend-shared across those surfaces.
- Current release evidence still treats live health, provider posture, and fresh runtime proof as required signoff inputs.

- Do not assume any unmerged branch work is shipped.
- Do not assume the public webUI bundle replaces the local Compose path.
- Do not assume docs that mention a surface prove it is live on the current `main` tip.
- Do not assume operator or internal routes are part of the release promise unless this file says so.
- Do not assume release readiness if the live runtime posture has not been rechecked.

- The live backend posture still needs confirmation against the supported local-only profile before release signoff.
- Fresh live evidence still needs to cover the supported beta path on the exact current `main` tip.
- Any runtime mismatch between supported profile, catalog, and health surfaces remains a release hold.

## This week's priorities
1. Re-run live supported-path proof on the current `main` tip.
2. Confirm the backend is in the supported local-only posture.
3. Verify chat completion, retrieval posture, and upload -> embed -> retrieve on the live stack.
4. Re-check the provider catalog and health surfaces against the supported profile.
5. Keep the public webUI and macOS delivery notes aligned with what is actually shipped.

## Release definition right now
- [ ] Supported-profile flags match the beta contract on the live runtime.
- [ ] Fresh live evidence exists on the current `main` tip for the supported path.
- [ ] Chat, retrieval, and upload/embedding behavior are proven on the live stack.
- [ ] Catalog, health, and provider posture agree with the supported profile.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
