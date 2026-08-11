# Private-preview non-secret profile reconciliation and static-gate proof

Date: 2026-08-11

## Scope

This architecture-impact task reconciled the complete approved non-secret private-preview profile in the machine-local, ignored `/Volumes/Dev_SSD/Codexify-main/.env.private-preview`. It changed only authorized non-secret assignments and added this receipt. The static gate then stopped at one frontend credential-isolation seam. No source, Compose, infrastructure, or service operation occurred.

## Workflow classification

- Execution lane: architecture-impact.
- Task kind: operator-owned non-secret runtime-profile reconciliation plus canonical static-gate proof.
- Evidence posture: durable environment integrity and static configuration evidence only; not runtime, public-host, provider-completion, or release proof.

## ADR impact

Aligned with existing ADRs; no ADR changed. ADR-039 Operator / User Access Boundary preserves operator-owned configuration, ADR-040 preserves explicit topology and exposure boundaries, and ADR-052 confines the named Whoosh'd and DeepSeek preview profile. The packet's requested `061-capability-oriented-mesh-architecture.md` path is absent; the checked-in capability-mesh record is `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`. That provenance mismatch does not authorize a topology change.

## Previous proof and commit

Previous proof: [2026-08-11-private-preview-deepseek-profile-deduplication-proof.md](2026-08-11-private-preview-deepseek-profile-deduplication-proof.md)
Previous proof commit: `52f38f62495e16586dd87d7bfd04aca9505108fe`

## Task branch and pre-task HEAD

Task branch: `codex/audit-reports-2026-08-07`
Pre-task HEAD: `52f38f62495e16586dd87d7bfd04aca9505108fe`

## Durable runtime checkout

The durable private-preview environment belongs to `/Volumes/Dev_SSD/Codexify-main`. Its pre-existing untracked `.worktrees/render-relay-codexify/` entry was preserved untouched.

## Environment permission / Git isolation baseline

Before reconciliation, `.env.private-preview` existed with mode `600`, matched the `.env.*` ignore rule, and was untracked. It was never staged or committed.

## Protected-field uniqueness baseline

Each protected field occurred exactly once before reconciliation: `GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`, `GUARDIAN_API_KEY`, `DEEPSEEK_API_KEY`, `CODEXIFY_PREVIEW_ADMIN_EMAILS`, `CODEXIFY_PREVIEW_APPROVED_EMAILS`, and `CODEXIFY_PREVIEW_FEEDBACK_EMAIL`.

## Authorized profile baseline inventory

The bounded raw-text inventory reported these classifications without emitting values:

| Authorized key | Occurrences | Baseline status |
| --- | ---: | --- |
| `COMPOSE_PROJECT_NAME` | 1 | MATCH |
| `CODEXIFY_RUNTIME_ENV_FILE` | 1 | MISMATCH |
| `CODEXIFY_PREVIEW_PORT` | 0 | MISSING |
| `CODEXIFY_SUPPORTED_PROFILE` | 1 | MISMATCH |
| `LLM_PROVIDER` | 1 | MISMATCH |
| `ALLOW_CLOUD_PROVIDERS` | 1 | MATCH |
| `CODEXIFY_LOCAL_ONLY_MODE` | 1 | MATCH |
| `CODEXIFY_EGRESS_ALLOWLIST` | 1 | MATCH |
| `LOCAL_RUNTIME_PRESET` | 0 | MISSING |
| `LOCAL_PROVIDER_VENDOR` | 0 | MISSING |
| `LOCAL_BASE_URL` | 0 | MISSING |
| `LOCAL_CHAT_MODEL` | 1 | MATCH |
| `DEEPSEEK_BASE_URL` | 1 | MATCH |
| `DEEPSEEK_CHAT_MODEL` | 1 | MATCH |
| `VITE_GUARDIAN_API_KEY` | 0 | MISSING |
| `VITE_GUARDIAN_DEV_API_KEY` | 0 | MISSING |

## Mismatching keys

- `CODEXIFY_RUNTIME_ENV_FILE`
- `CODEXIFY_SUPPORTED_PROFILE`
- `LLM_PROVIDER`

## Duplicate authorized keys

None. The previously normalized DeepSeek non-secret assignments remained unique and canonical.

## Missing authorized keys

- `CODEXIFY_PREVIEW_PORT`
- `LOCAL_RUNTIME_PRESET`
- `LOCAL_PROVIDER_VENDOR`
- `LOCAL_BASE_URL`
- `VITE_GUARDIAN_API_KEY`
- `VITE_GUARDIAN_DEV_API_KEY`

## Reconciled keys

- `CODEXIFY_RUNTIME_ENV_FILE`
- `CODEXIFY_PREVIEW_PORT`
- `CODEXIFY_SUPPORTED_PROFILE`
- `LLM_PROVIDER`
- `LOCAL_RUNTIME_PRESET`
- `LOCAL_PROVIDER_VENDOR`
- `LOCAL_BASE_URL`
- `VITE_GUARDIAN_API_KEY`
- `VITE_GUARDIAN_DEV_API_KEY`

## Duplicate normalization result

No duplicate authorized key remained to normalize in this task.

## Protected-field preservation result

PASS. A raw-text, non-evaluating pre-replacement comparison retained every protected assignment byte-for-byte; the post-edit parser confirmed every protected field remains unique.

## DeepSeek credential preservation result

PASS. `DEEPSEEK_API_KEY` remained unique and byte-for-byte unchanged. Its value was not displayed, hashed, fingerprinted, or recorded.

## Unrelated-line preservation result

PASS. The in-memory structural comparison confirmed that every non-authorized environment line remained byte-identical and in its original order.

## Final authorized profile uniqueness result

PASS. Every authorized non-secret profile field occurs exactly once.

## Final canonical profile identity result

PASS. Every authorized non-secret profile field equals its committed canonical assignment, including the previously reconciled DeepSeek base URL and model.

## Vite Guardian-key isolation result

PASS for the durable environment file: `VITE_GUARDIAN_API_KEY` and `VITE_GUARDIAN_DEV_API_KEY` each occur once and are empty. This does not prove the distinct Compose frontend credential-isolation invariant below.

## Environment permission result

PASS. The editor used a same-directory mode-`600` temporary file and atomic replacement; the final durable environment remains mode `600`.

## Git ignore/tracking result

PASS. The final durable environment remains ignored by `.gitignore` and untracked by Git.

## Canonical static validator result

FAIL. Executed from the durable checkout:

```text
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static
```

The validator's included static suites reported 37 passing tests. Its secure Compose render then failed the frontend credential-isolation check because the resolved `frontend` environment contains the `DEEPSEEK_API_KEY` field. No resolved Compose JSON or credential value was displayed.

## Focused preview contract-test result

Not run. The prescribed focused suites are ordered after a passing canonical static validator, and the static gate failed.

## Non-failing warning summary

No warning was emitted by the static-validator output. The post-static focused suites were not run.

## Cloudflare untouched confirmation

No Cloudflare command, API, tunnel inspection, configuration, or remote resource was accessed or changed.

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

No protected-field value, credential value, account-email value, hash, fingerprint, length, complete environment contents, resolved Compose output, password, session token, or JWT was printed, committed, or retained. The receipt records only permitted key names, non-secret profile classifications, and the sanitized static-gate seam.

## What this proves

The durable private-preview environment now has one canonical assignment for every authorized non-secret profile field, retains its protected and unrelated data byte-for-byte, remains mode `600` and untracked, and keeps both Vite Guardian API-key assignments empty. The static gate's included suites pass, but its frontend credential-isolation assertion fails.

## What this does not prove

This does not prove the canonical static gate, a running preview origin, local reachability, provider response, queue/worker execution, authenticated persistence, Cloudflare publication, DNS, Access, Render, Tailscale, or release readiness.

## Final classification: NEXT_PROOF_NEEDED

Remaining failing seam: the private-preview static Compose render places the DeepSeek credential field in the `frontend` service environment, violating the browser credential-isolation contract.

## Exact next gate

Run one atomic Compose-boundary repair that ensures the private-preview `frontend` service does not resolve `DEEPSEEK_API_KEY`, preserves the now-canonical durable profile, and reruns `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static`.
