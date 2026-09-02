# 2026-09-01 Friends-and-Family Private-Preview Canary Proof

## Conclusion

`PRIVATE_PREVIEW_FRIENDS_FAMILY_CANARY_BLOCKED`

The first external friends-and-family canary was stopped before any tester was
admitted. The local private-preview boundary is healthy and fails closed for
unauthenticated identity, but the intended external ingress is not presently
reachable and there is no provisioned non-admin tester account in the effective
allowlist.

This is a pre-admission operational block, not a qualified canary and not a
release promotion. No guest traffic was accepted, no tester conversation was
created or inspected, and no provider-execution, cross-account-isolation, or
real-traffic claim is made by this receipt.

## Scope and authority

- Workflow lane: `architecture-impact`
- Task kind: proof
- Evidence posture: live-runtime observation with blocked external-canary
  disposition
- Execution date: 2026-09-01 local time
- Source branch and commit: local `main` at
  `5fbd423da3185769058957f98097d656933ab0ab`
- Runtime project: `codexify_private_preview`
- Intended external hostname: `preview.codexify.space`
- Intended sole host publication: `127.0.0.1:8081 -> private-preview-origin:8080`

The newer recovery and Guardian-secret-rotation receipts remain the governing
prerequisites for this canary. Their recovery checkpoint and source
persistence were not touched. The known stale recovery statement in
`docs/architecture/00-current-state.md` was left visible rather than silently
normalized.

One unrelated pre-existing deletion,
`docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md`, remained unstaged and
untouched. No application source, Compose file, Cloudflare configuration,
allowlist, provider policy, account, session secret, database, media bytes, or
Docker volume was modified.

## Local private-preview boundary

| Gate | Result | Evidence |
| --- | --- | --- |
| Static private-preview contract | PASS | `scripts/private_preview_validate.sh static` passed its 39 focused checks and rendered only `private-preview-origin 127.0.0.1:8081 -> 8080`. |
| Loopback reachability | PASS | `scripts/private_preview_validate.sh reachability` passed `/health`, `/health/chat`, `/api/health/llm`, catalog, and origin reachability through `http://127.0.0.1:8081`. |
| Preview Compose health | PASS | Database, Redis, Neo4j, and backend were healthy; frontend, private-preview origin, and required workers were up. |
| Direct unauthenticated thread creation | PASS (denied) | `POST /api/chat/threads` without a session returned `401`. |
| Caller-controlled identity rejection | PASS (denied) | The same thread request with `X-User-Id: canary-spoof@example.invalid` returned `401`. |
| Public self-registration | PASS (denied) | `POST /api/auth/register` returned `404` in preview mode. |
| Browser/server secret separation | PASS (static) | The resolved frontend configuration kept Guardian API-key fields empty and excluded Guardian/session/DeepSeek server credentials. |

These local results prove only the exercised loopback configuration and
unauthenticated application boundary. They do not prove Cloudflare Tunnel,
Cloudflare Access, public DNS, external browser login, a real tester session,
or account isolation between testers.

## External ingress and Access gate

| Gate | Result | Evidence |
| --- | --- | --- |
| Public DNS resolution for `preview.codexify.space` | BLOCKED | `dig +short preview.codexify.space` returned no record. |
| External HTTPS reachability | BLOCKED | A direct unsandboxed `curl --head https://preview.codexify.space` failed DNS resolution (`curl` exit `6`, HTTP code `000`). |
| Local Cloudflare Tunnel client | BLOCKED | `cloudflared` was absent from the active PATH. |
| Standard local Tunnel configuration | BLOCKED | No `/Users/chriscastillo/.cloudflared` configuration directory was present for inspection. |
| Managed Tunnel service observation | BLOCKED | No matching Cloudflare/cloudflared launchd label was present. |
| Cloudflare Access denial/login behavior | NOT RUN | The hostname was not resolvable, so no external request could reach the Access boundary. |

The observations above do not prove that no Cloudflare configuration exists in
every possible operator-managed location. They do prove that this execution
context had no working DNS/HTTPS path to the required hostname, which is
sufficient to fail closed before admission.

## Admission gate

The effective preview configuration was inspected without printing email
identities or secret values:

- `effective_allowlisted_count=2`
- `admin_count=1`
- `guest_count=1`
- `allowlisted_account_count=1`
- `guest_account_count=0`
- `unprovisioned_guest_count=1`
- `.env.private-preview` remained ignored and mode `0600`; no wildcard entry
  was found.

Therefore the configured boundary does not currently contain the required
two-to-three distinct, provisioned non-admin friends-and-family tester
accounts. No password was requested or handled by this proof, and the
operator-only provisioning CLI was not invoked.

## Gates intentionally not run

The following gates require working external ingress plus explicit tester
identity and consent, and were deliberately not substituted with synthetic or
operator-only activity:

- Cloudflare Access unauthenticated denial and authenticated login.
- Admission of two or three named trusted tester accounts.
- Independent Tester A / Tester B project, thread, document, and media
  isolation checks.
- Simultaneous real-user observation using content-free presence only.
- Provider-specific guest execution and durable persisted transcript readback.
- Host resource posture under real guest traffic.

No fallback provider result would have been counted as a DeepSeek success.

## Required next atomic prerequisite

Before rerunning this canary, an authorized operator must establish and prove
all of the following without widening the lane:

1. A named Cloudflare Tunnel and DNS record for `preview.codexify.space` that
   forwards only to `http://127.0.0.1:8081`, with the final catch-all `404`
   rule and no direct publication of Guardian, Vite, Whoosh'd, data stores, or
   workers.
2. Cloudflare Access denial for an unauthenticated request and login for an
   approved identity, while Guardian remains the canonical session/account
   authority.
3. Two or three explicitly approved trusted tester email identities, each
   provisioned interactively into a distinct non-admin Codexify account; no
   public signup, wildcard allowlist, or shared account.

Only then may the canary resume with external account-isolation, provider,
persistence, and bounded-observability proof. Any authentication,
cross-account exposure, persistence-integrity, secret-exposure, or non-loopback
internal-service publication failure must terminate the canary immediately.

## Validation results

- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — PASS.
- Direct loopback unauthenticated/identity-spoof/registration checks — PASS
  as denials (`401`, `401`, `404`).
- External DNS/HTTPS checks — BLOCKED as recorded above; no retry or topology
  change was attempted.
- Documentation validation and diff checks are recorded after this receipt is
  added.

## ADR impact

Aligned with ADR-005, ADR-039, ADR-041, ADR-042, ADR-049, and ADR-069. No new
ADR is required. This receipt exercises no new account, provider, telemetry,
or exposure model and does not alter the Beta/private-preview support posture.

## Axis KB addition

Record that the first friends-and-family private-preview canary stopped before
admission on 2026-09-01: the loopback preview boundary and unauthenticated
application denials were healthy, but `preview.codexify.space` had no working
DNS/HTTPS path in the execution context and the effective allowlist had zero
provisioned non-admin guest accounts. The recovery checkpoint remains
available; no source persistence or unrelated workload was changed.
