## Purpose

This file is the canonical short-form source of truth for Codexify's current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated

2026-03-29

## Interpretation rule

This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase

Codexify is in release-gate remediation on `main` for the local Docker Compose beta profile. The latest merged release-gate proof on `main` (2026-03-28) confirms profile flags and route quarantine behavior, but does not close readiness because fresh completion and retrieval proofs failed on the live stack.

## What changed recently

- Added fresh release-gate artifact on `main` (`docs/architecture/2026-03-28-release-gate-proof.md`) with explicit pass/fail evidence.
- Chat runtime now surfaces execution truth and fallback model details to the UI and tests for completion semantics were updated.
- Provider/model classification was hardened with soft fallback logic and catalog/provider tests.
- Browser-dev media rendering was fixed across chat/workspace surfaces with new coverage.
- Composer layout contract and send-button placement were tightened across multiple merged UI fixes.

## Current supported reality

- Supported install path remains local Docker Compose with backend, frontend, Postgres, Redis, and workers.
- Supported-profile flags were live-verified on `main`: `CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Quarantined non-core routes were live-verified as unavailable (`404`) in supported profile.
- Chat request acceptance path works on `main` (thread creation, message persistence, completion acceptance with task id/turn id).
- Document upload and embed lifecycle reached `embedding_status=ready` in the latest release-gate run.
- `/health`, `/health/chat`, `/health/llm`, and `/api/llm/catalog` are available but currently not reconciled into one release-signoff truth.

## Not yet true / do not assume

- Do not assume accepted completions produce persisted assistant output on current `main`; latest proof captured worker `502` after local inference endpoint `404`s.
- Do not assume retrieval is proven on current `main`; latest proof saw `/api/retrieve` return `404`.
- Do not assume backend and embed worker use the same vector-store backend in the live supported profile.
- Do not assume health/collateral routes are alias-consistent (`/health*` vs `/api/health*`) without explicit probe evidence.
- Do not assume older supported-path proof artifacts still represent current `main` without a fresh rerun.
- Do not assume `/tools` and command-bus surfaces are one finalized release contract unless stated here.

## Active blockers

- Chat completion execution fails after acceptance on current supported profile because local inference endpoints return `404`, producing worker `502`.
- Retrieval evidence is not closed: `/api/retrieve` is missing in the proven stack and backend retrieval did not return the fresh sentinel.
- Vector-store backend mismatch in live runtime (`backend` observed `faiss`, `worker-document-embed` observed `chroma`) blocks reliable retrieval signoff.
- Release-gate reconciliation is incomplete across `/health`, `/health/chat`, `/health/llm`, and `/api/llm/catalog`.

## This week's priorities

1. Fix local inference endpoint/model wiring so accepted completions persist assistant responses on supported profile.
2. Align backend and embed-worker vector-store configuration and re-prove retrieval with a fresh sentinel document.
3. Restore and verify one supported retrieval API path used by release proof (`/api/retrieve` or documented replacement).
4. Publish one fresh end-to-end supported-path proof on `main` that passes create -> complete -> upload -> embed -> retrieve.
5. Reconcile and document health/catalog route expectations for operator signoff.

## Release definition right now

- [ ] Supported-profile flags are active in live runtime (`CODEXIFY_BETA_CORE_ONLY=true`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`).
- [ ] Quarantined non-core routes return the expected unsupported behavior in the running stack.
- [ ] One fresh supported-path run on `main` proves thread create, completion execution, assistant persistence, document upload, embed readiness, and retrieval evidence.
- [ ] Retrieval runtime uses one aligned vector-store backend across backend and embed worker on the supported profile.
- [ ] `/health`, `/health/chat`, `/health/llm`, and `/api/llm/catalog` are reconciled with the actual supported model/runtime contract.
- [ ] No release claim depends on internal-only or dev-only surfaces.

## How to read the rest of the KB

- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
