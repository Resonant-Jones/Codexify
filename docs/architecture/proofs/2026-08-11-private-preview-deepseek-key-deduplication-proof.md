# Private-preview DeepSeek credential deduplication proof

## Scope

This architecture-impact task resolved exactly one duplicate `DEEPSEEK_API_KEY` assignment in the durable ignored private-preview environment. Existing Compose resolution established authority without exposing the credential. No non-secret profile field, other protected field, source, Compose file, service, Cloudflare, DNS, Access, Render, or Tailscale state changed.

## Workflow classification

- Execution lane: architecture-impact.
- Task kind: machine-local secret-configuration deduplication plus focused contract proof.
- Evidence posture: configuration integrity and focused source-contract proof; not provider-completion, Cloudflare, public-host, or release proof.

## ADR impact

Aligned with existing ADRs; no ADR changed. ADR-039 preserves operator configuration authority, ADR-040 preserves explicit profile and exposure boundaries, and ADR-052 confines the named preview provider profile. The packet named ADR-061 Capability-Oriented Mesh Architecture; that path is absent in this checkout, while the related capability-mesh document is `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`. This discrepancy does not authorize a topology change.

## Previous blocking proof

`docs/architecture/proofs/2026-08-11-private-preview-profile-reconciliation-proof.md` recorded the protected duplicate stop condition.

## Previous proof commit

`419234b317a143010eca890dc6ca9b241fef51eb`.

## Task branch and pre-task HEAD

- Branch: `codex/audit-reports-2026-08-07`.
- Pre-task HEAD: `419234b317a143010eca890dc6ca9b241fef51eb`.
- The task checkout was clean before adding this receipt.

## Durable runtime checkout

The durable runtime checkout is `/Volumes/Dev_SSD/Codexify-main`. Its pre-existing unrelated nested worktree remained untouched.

## Environment permission / Git isolation

The durable `.env.private-preview` remained mode `600`, ignored by the repository rule, and untracked before and after the edit. It was never staged or committed.

## Duplicate-key occurrence baseline

The bounded non-evaluating parser confirmed exactly two non-empty, non-placeholder `DEEPSEEK_API_KEY` assignments. Neither value, hash, fingerprint, length, or line content was printed.

## Compose authority-resolution method

The existing private-preview Compose configuration was rendered only to mode-600 temporary JSON files. A bounded in-memory comparison evaluated the two candidates against effective `backend` and `worker-chat` values. Temporary files were deleted without display.

## Authority-resolution classification

`EFFECTIVE_MATCH=SECOND_ONLY`: the second existing assignment reproduced the pre-edit effective Compose credential for both `backend` and `worker-chat`.

## Deduplication result

Pass. Exactly the first redundant `DEEPSEEK_API_KEY` assignment was removed; the Compose-effective second assignment was preserved byte-for-byte. No other environment line changed.

## Effective credential preservation result

Pass. A fresh protected Compose render after atomic replacement proved backend effective credential preservation, worker-chat effective credential preservation, and backend/worker credential parity.

## Protected-field uniqueness result

Pass. Each protected key now occurs exactly once, including `DEEPSEEK_API_KEY`; all four secret-bearing keys remain non-empty.

## Protected-field preservation result

Pass. Guardian secrets and preview administrator, approved-user, and feedback fields remained byte-identical. The surviving DeepSeek credential is byte-identical to the pre-edit effective Compose value.

## Unrelated-field preservation result

Pass. Structural comparison proved that every remaining environment-file line matches its pre-edit counterpart byte-for-byte. No non-secret profile field changed.

## Non-secret profile reconciliation deferral

Confirmed. The previously identified non-secret profile mismatch is outside this task and remains pending.

## Focused contract-test result

Pass: `.venv/bin/python -m pytest -v` over the three focused private-preview suites collected and passed 10 tests (one warning).

## Cloudflare untouched confirmation

No Cloudflare action, tunnel inspection, connector action, token operation, or public-host change was performed.

## DNS untouched confirmation

No DNS query or mutation was performed.

## Cloudflare Access untouched confirmation

No Access application, policy, login, service token, or credential operation was performed.

## Render untouched confirmation

No Render command or connector action was performed.

## Tailscale untouched confirmation

No Tailscale command or configuration action was performed.

## Services untouched confirmation

No application service was started, stopped, restarted, or otherwise mutated.

## Secret/exposure review

No credential, Guardian secret, account-email value, password, session/JWT, secret hash, fingerprint, length, complete environment, or resolved Compose JSON was printed, committed, or retained in this receipt. No credential was generated, rotated, replaced, or validated by a model request.

## What this proves

- The duplicate credential assignment was resolved using existing Compose effective value as authority rather than line order.
- One and only one credential assignment remains, with the same effective backend and worker-chat credential as before.
- Protected fields, unrelated environment lines, isolation, mode, and focused private-preview source contracts remain intact.

## What this does not prove

This does not prove non-secret profile reconciliation, canonical static configuration, a running private-preview origin, provider completion, authenticated session behavior, Cloudflare publication, public reachability, or release readiness.

## Final classification: PASS

All secret-deduplication requirements in this task passed.

## Exact next gate

Resume the separately authorized non-secret private-preview profile reconciliation. It may edit only approved profile fields, must preserve the now-unique DeepSeek credential and every other protected field, and must rerun the canonical static validator before any Cloudflare work.
