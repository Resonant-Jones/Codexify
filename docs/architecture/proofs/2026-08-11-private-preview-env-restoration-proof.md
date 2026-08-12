# Private-preview environment restoration proof

## Scope

This architecture-impact task resolved the ownership question for the ignored, machine-local `.env.private-preview` prerequisite from the preceding Cloudflare receipt. It did not inspect or modify Cloudflare, DNS, Access, cloudflared, Render, Tailscale, services, source, Compose, templates, or Git ignore rules.

## Workflow classification

- Execution lane: architecture-impact.
- Task kind: operator-configuration prerequisite restoration plus static proof.
- Evidence posture: local configuration evidence only; not runtime, public-host, or release proof.

## ADR impact

Aligned with existing ADRs; no ADR changed. ADR-039 preserves operator ownership, ADR-040 preserves explicit profile and exposure boundaries, and ADR-052 confines the named preview provider posture. The task packet named ADR-061 Capability-Oriented Mesh Architecture; that path is absent here, while the related checked-in capability-mesh document is `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`. This provenance discrepancy does not authorize a topology change.

## Previous blocking proof and commit

`docs/architecture/proofs/2026-08-11-cloudflare-public-preview-tunnel-proof.md` stopped before Cloudflare mutation and was committed as `ed8190576d0da990dff5c1773dc92d62cdb782b5`.

## Task branch and pre-task HEAD

- Branch: `codex/audit-reports-2026-08-07`.
- Pre-task HEAD: `ed8190576d0da990dff5c1773dc92d62cdb782b5`.
- The task checkout was clean before adding this receipt.

## Runtime checkout discovery method

No active Docker Compose project with the `com.docker.compose.project=codexify_private_preview` label was found, so no Compose working-directory label could establish ownership. Registered Git worktrees were then enumerated without reading environment contents; exactly one non-Codex worktree contained an ignored `.env.private-preview` file.

## Durable runtime checkout classification

`/Volumes/Dev_SSD/Codexify-main` is the sole non-Codex candidate found by the registered-worktree scan. It is outside `/Users/chriscastillo/.codex/worktrees/` and is the durable operator-checkout candidate for this task.

## Existing environment source classification

`/Volumes/Dev_SSD/Codexify-main/.env.private-preview` is both the only candidate source and durable target path. No copy was necessary or made. Its non-secret profile identity did not pass the required contract check, so it cannot be silently accepted as a restorable source.

## Environment-file permission result

The candidate environment file exists and has mode `600`. No permission change was necessary.

## Git-ignore/tracking result

In the durable candidate checkout, `.env.private-preview` is ignored by `.gitignore` and is not tracked. It was not staged or modified. An unrelated registered nested worktree appeared as pre-existing untracked content there and was preserved.

## Required-key presence result

All required secret-bearing key names are present, non-empty, and differ from the committed template placeholders: `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`, `GUARDIAN_API_KEY`, and `DEEPSEEK_API_KEY`. Required administrator, approved-user, and feedback fields are also present and non-empty. No values, counts, hashes, or addresses were printed or retained.

## Preview-profile identity result

Failed. The candidate does not satisfy the approved non-secret profile contract. The validation recorded only key-name classifications:

- `CODEXIFY_PREVIEW_PORT` did not meet the required present/non-empty contract.
- `LOCAL_RUNTIME_PRESET`, `LOCAL_PROVIDER_VENDOR`, and `LOCAL_BASE_URL` did not meet the required contract.
- `VITE_GUARDIAN_API_KEY` and `VITE_GUARDIAN_DEV_API_KEY` did not meet the required present-and-empty contract.

The candidate was not rewritten and no selection was made between alternate profile values.

## Secret handling result

No secret value, hash, complete environment, resolved Compose environment, password, session token, JWT, Guardian API key, or DeepSeek API key was printed, copied, generated, or rotated. The durable environment file was not written in this task.

## Canonical static validator result

Not run. The required stop condition is reached when the candidate profile identity materially differs from the committed template. No Docker service was started.

## Focused contract-test result

Not run in the durable checkout because the profile-identity gate failed before the prescribed validation phase. This receipt does not replace the prior focused-test evidence.

## Cloudflare untouched confirmation

No Cloudflare tunnel, connector, token, or public-host configuration was inspected or changed.

## DNS untouched confirmation

No DNS query or mutation was performed.

## Cloudflare Access untouched confirmation

No Access application, policy, login, service token, or credential was inspected or changed.

## Render untouched confirmation

No Render command or connector action was performed.

## Tailscale untouched confirmation

No Tailscale command or configuration action was performed.

## What this proves

- The durable operator-checkout candidate is unambiguous from registered worktree evidence.
- Its existing private-preview file is mode `600`, ignored, untracked, and has the required secret-bearing key presence without revealing any secret.
- The existing candidate cannot be silently reused because its non-secret profile identity does not satisfy the committed private-preview contract.

## What this does not prove

This does not prove a repaired environment, static configuration, a running private-preview origin, host-port isolation, provider execution, authenticated Guardian behavior, Cloudflare Tunnel, DNS, Cloudflare Access, public reachability, or release readiness.

## Final classification: NEXT_PROOF_NEEDED

Failing seam: the only existing durable operator-owned `.env.private-preview` has a non-secret preview-profile identity mismatch, and this task does not authorize rewriting it.

## Exact next gate

Create one explicitly authorized operator-configuration reconciliation task to review and correct only the identified non-secret profile identity fields in the durable environment while preserving all existing secret values; then rerun the canonical static validator before resuming Cloudflare work.
