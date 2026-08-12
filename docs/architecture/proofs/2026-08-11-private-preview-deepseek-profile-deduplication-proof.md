# Private-preview DeepSeek profile deduplication proof

Date: 2026-08-11
Classification: Architecture-impact, bounded environment normalization

## Scope

This receipt covers only the machine-local, ignored `/Volumes/Dev_SSD/Codexify-main/.env.private-preview` assignments for `DEEPSEEK_BASE_URL` and `DEEPSEEK_CHAT_MODEL`, plus this proof document. No other profile fields or repository files were changed.

## Workflow classification

The task is an architecture-impact operational-profile reconciliation: it changes the durable non-secret provider profile while preserving the credential and preview-access boundary. It does not change runtime topology, route semantics, provider code, or release claims.

## ADR impact

No ADR was changed. The requested ADR-061 path is not present in this checkout; the related capability-boundary record is [ADR-039](../adr/039-capability-oriented-mesh-architecture.md). This normalization preserves its least-authority and explicit-configuration direction; it introduces no new authority, network boundary, or topology.

## Previous blocking proof

The preceding profile-reconciliation receipt is [2026-08-11-private-preview-profile-reconciliation-rerun-proof.md](2026-08-11-private-preview-profile-reconciliation-rerun-proof.md). It identified duplicate DeepSeek non-secret assignments as the remaining blocker for the broader static-validation gate.

## Previous proof commit

`d3238a33b6312500085f61663f799166f3234f6a`

## Task branch and pre-task HEAD

Task branch: `codex/audit-reports-2026-08-07`
Pre-task HEAD: `d3238a33b6312500085f61663f799166f3234f6a`

## Durable runtime checkout

The edited runtime profile is owned by the durable checkout at `/Volumes/Dev_SSD/Codexify-main`. This proof receipt is committed from the task worktree at `/Users/chriscastillo/.codex/worktrees/aaba/Codexify-main`.

## Environment permission / Git isolation baseline

Before the edit, `.env.private-preview` existed as a local mode-`600` file, was ignored by the repository rule for `.env.*`, and was untracked. The durable checkout also had a pre-existing untracked `.worktrees/render-relay-codexify/` entry; it was not touched.

## Protected-field uniqueness baseline

All protected fields were present exactly once before normalization: `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`, `GUARDIAN_API_KEY`, `DEEPSEEK_API_KEY`, `CODEXIFY_PREVIEW_ADMIN_EMAILS`, `CODEXIFY_PREVIEW_APPROVED_EMAILS`, and `CODEXIFY_PREVIEW_FEEDBACK_EMAIL`.

## DEEPSEEK_BASE_URL duplicate count

Baseline count: two assignments.

## DEEPSEEK_CHAT_MODEL duplicate count

Baseline count: two assignments.

## DEEPSEEK_BASE_URL normalization result

The final-position assignment was retained in place and canonicalized to `https://api.deepseek.com`; the earlier duplicate was removed.

## DEEPSEEK_CHAT_MODEL normalization result

The final-position assignment was retained in place and canonicalized to `deepseek-v4-flash`; the earlier duplicate was removed.

## Canonical uniqueness result

Each authorized DeepSeek non-secret field now occurs exactly once and has its required canonical value.

## Compose backend resolution result

`docker compose config` was rendered only to a mode-`600` temporary JSON file. The inspected `backend` environment resolves both DeepSeek non-secret fields to their canonical values.

## Compose worker-chat resolution result

The same secure Compose rendering confirms that `worker-chat` resolves both DeepSeek non-secret fields to their canonical values.

## Backend/worker parity result

The inspected `backend` and `worker-chat` values match exactly for both authorized DeepSeek non-secret fields.

## Protected-field preservation result

All protected fields remained unique and byte-for-byte unchanged across the atomic replacement.

## DeepSeek credential preservation result

`DEEPSEEK_API_KEY` remained byte-for-byte unchanged and unique. Its value was neither displayed nor recorded.

## Unrelated-field preservation result

Every non-target line in `.env.private-preview` was byte-identical before and after normalization.

## Broader profile reconciliation deferral

No unrelated non-secret profile mismatch was reconciled. That separately authorized work remains deferred.

## Environment permission result

The normalizer used a same-directory mode-`600` temporary file and atomic replacement. The final `.env.private-preview` remains mode `600`.

## Git ignore/tracking result

The final environment file remains ignored and untracked; no environment file was staged or committed.

## Focused preview contract-test result

Executed from the durable checkout:

```text
.venv/bin/python -m pytest -v tests/auth/test_private_preview_access.py tests/ops/test_private_preview_contract.py tests/ops/test_private_preview_origin_recovery_contract.py
```

Result: 10 passed; one non-failing warning was reported.

## Cloudflare untouched confirmation

No Cloudflare command, configuration, or remote resource was accessed or changed.

## DNS untouched confirmation

No DNS lookup, record change, or zone action was performed.

## Cloudflare Access untouched confirmation

No Cloudflare Access application, policy, identity-provider, or session action was performed.

## Render untouched confirmation

No Render deployment, service, environment, or API action was performed.

## Tailscale untouched confirmation

No Tailscale command, tailnet setting, device, ACL, or Funnel action was performed.

## Services untouched confirmation

No application service was started, stopped, restarted, deployed, or otherwise operated.

## Secret/exposure review

The proof records only permitted non-secret canonical values and pass/fail outcomes. It contains no credential values, protected-field values, raw environment-file contents, or complete Compose JSON.

## What this proves

The durable private-preview profile has exactly one canonical `DEEPSEEK_BASE_URL` and exactly one canonical `DEEPSEEK_CHAT_MODEL`; its protected data and unrelated lines were preserved; and the `backend` and `worker-chat` Compose environments agree on those fields. The focused preview-access and profile-contract tests pass.

## What this does not prove

This is not a completed broader profile reconciliation, static validator run, provider-response proof, service-runtime proof, Cloudflare/DNS/Access proof, Render proof, Tailscale proof, or public-release proof.

## Final classification: PASS

PASS for the narrowly authorized duplicate DeepSeek non-secret profile assignment normalization.

## Exact next gate

Resume the previously blocked non-secret private-preview profile reconciliation. It may edit the remaining approved profile fields, must preserve these two canonical and unique DeepSeek assignments, then must run `PRIVATE_PREVIEW_BASE_URL=... bash scripts/private_preview_validate.sh static`. Only a passing static-validation receipt may reopen the Cloudflare task.
