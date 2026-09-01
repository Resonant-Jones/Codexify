# 2026-09-01 Private-Preview Cloudflare Ingress Provisioning Proof

## Conclusion

`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_BLOCKED`

The canonical local private-preview origin remains healthy and loopback-only,
and the current official `cloudflared` client is now installed. Cloudflare
control-plane provisioning did not begin because this execution context was
not supplied a least-privilege Cloudflare API token or a secure token-file
pointer.

This is a pre-mutation credential-authority block. No Tunnel, DNS record,
Access application, Access policy, connector configuration, guest account, or
application behavior was created, changed, or deleted. The friends-and-family
canary remains closed.

## Scope and authority

- Execution model requested by the task: `Sol xhigh`
- Workflow lane: `architecture-impact`
- Task kind: implementation plus live proof
- Evidence posture: live-runtime preflight with blocked control-plane
  disposition
- Execution date: 2026-09-01 local time
- Source branch and commit: local `main` at
  `e19defc9fc4e18e0ec75b2cd8f32ed4b61752f4f`
- Blocked-canary lineage commit:
  `e19defc9fc4e18e0ec75b2cd8f32ed4b61752f4f`
- Runtime project: `codexify_private_preview`
- Canonical hostname: `preview.codexify.space`
- Required sole origin: `http://127.0.0.1:8081`

The current local committed state and newer recovery/authentication proof
receipts were treated as authority over stale historical recovery statements.
The unrelated pre-existing deletion of
`docs/DEV_LOG/2026-09-01/Dev Log - 2026-09-01.md` remained untouched and
unstaged.

## Local prerequisite proof

| Gate | Result | Bounded evidence |
| --- | --- | --- |
| Static private-preview validation | PASS | `scripts/private_preview_validate.sh static` passed 39 focused checks and reported only `private-preview-origin 127.0.0.1:8081 -> 8080`. |
| Loopback reachability | PASS | `scripts/private_preview_validate.sh reachability` passed through `http://127.0.0.1:8081`. |
| Private-preview host-port isolation | PASS | Live Docker inspection showed only `private-preview-origin` published, at `127.0.0.1:8081`; Guardian, frontend, Whoosh'd, Postgres, Redis, Neo4j, and workers had no private-preview host bindings. |
| Recovery prerequisite | PASS (prior proof) | The 2026-09-01 recovery requalification receipt remains proven and its retained checkpoint was not touched. |
| Guardian secret rotation prerequisite | PASS (prior proof) | The 2026-09-01 Guardian authentication-secret rotation receipt remains proven; no session or secret state was changed. |

Unrelated Docker workloads and their existing publications were observed but
not modified. This receipt makes no claim about their architecture or support
posture.

## Cloudflare tooling and local state

- `cloudflared` was initially absent from `PATH`.
- The official current macOS package path documented by Cloudflare is
  Homebrew: `brew install cloudflared`.
- Installation completed successfully from the Homebrew bottle.
- Installed version: `cloudflared 2026.8.3`, built 2026-08-31.
- No `/Users/chriscastillo/.cloudflared` directory existed before or after
  installation.
- No Tunnel credential, `cert.pem`, local Tunnel configuration, or managed
  connector process was created.
- No reboot/login persistence mechanism was installed or claimed.

## Current API permission inspection

Current Cloudflare documentation was inspected before any attempted
management operation. The narrow required token boundary is:

- account-scoped Cloudflare Tunnel write/edit capability for the intended
  account;
- account-scoped `Access: Apps and Policies` write/edit capability for the
  intended account;
- zone-scoped DNS write/edit capability restricted to the `codexify.space`
  zone;
- only the corresponding read capability needed to inventory those resources.

Cloudflare's current API documentation names compatible Tunnel permissions as
`Cloudflare One Connectors Write`,
`Cloudflare One Connector: cloudflared Write`, or
`Cloudflare Tunnel Write`, and names the Access permission
`Access: Apps and Policies Write`. The official Tunnel setup documentation
also requires DNS edit authority for the published hostname.

Billing, account membership, unrelated zones, unrelated DNS, Workers, Pages,
unrelated Tunnels, and unrelated Access applications remain outside the grant.
A Global API Key is not an acceptable substitute.

## Credential handoff result

| Check | Result |
| --- | --- |
| `CLOUDFLARE_API_TOKEN_FILE` pointer | ABSENT |
| `CLOUDFLARE_API_TOKEN` environment variable | ABSENT |
| `CF_API_TOKEN` environment variable | ABSENT |
| Standard user-local Cloudflare authentication state | ABSENT |
| Cloudflare management authentication | NOT RUN |
| Account/zone authorization inventory | NOT RUN |

No credential value was requested from shell history, printed, copied into the
repository, or inferred from a broad browser/dashboard session. The task's
secure handoff prerequisite was therefore not satisfied.

## Public DNS baseline

Bounded host DNS checks before any Cloudflare mutation reported:

- `preview.codexify.space`: no answer;
- `codexify.space`: resolves;
- `www.codexify.space`: resolves.

No record values for the apex, `www`, or unrelated names are reproduced here.
No `/etc/hosts` override was used. Because no authenticated control-plane
inventory or mutation occurred, preservation is proven only as a no-operation
fact for this execution, not as a before/after Cloudflare API diff.

## Gates not run

The following gates require the missing least-privilege management credential
and were not weakened or substituted:

- account/zone/Tunnel/DNS/Access inventory;
- creation or reconciliation of `codexify-private-preview`;
- secure local Tunnel credentials and exact ingress configuration;
- canonical DNS attachment;
- Access application and operator-only exact-email policy;
- connector start and health;
- public DNS, TLS, Access challenge, approved-operator admission, Guardian
  authentication layering, public origin/health, and fallback 404 proof;
- authenticated before/after preservation comparison for apex, `www`, and
  unrelated DNS.

No guest tester was provisioned or admitted. No alternate hostname, quick
Tunnel, public signup, wildcard allowlist, Access bypass, or application-code
change was attempted.

## Exact blocker and required handoff

The operator must provide a least-privilege Cloudflare API token through a
mode-`0600` file outside the repository and make its path available as
`CLOUDFLARE_API_TOKEN_FILE`. The token must be limited to the intended
Cloudflare account and `codexify.space` zone with the Tunnel, DNS, and Access
application/policy permissions listed above. Supplying the account ID and zone
ID alongside the handoff avoids requiring broader account/zone discovery
permissions.

After that handoff, rerun this same atomic task. It must inventory existing
state before mutation, reconcile rather than duplicate resources, and retain
the fail-closed conclusion unless every canonical DNS, HTTPS, Access,
Guardian-layering, isolation, fallback, and preservation gate passes.

## Validation results

- `git status --short --branch` — PASS; source branch/HEAD recorded and only
  the unrelated Dev Log deletion was initially dirty.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS, 39 focused checks.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — PASS.
- `docker ps --format '{{.Names}}\t{{.Ports}}'` — PASS for the bounded
  private-preview publication contract.
- `cloudflared --version` — PASS after authorized installation,
  `2026.8.3`.
- Public DNS presence checks — preview absent; apex and `www` present.
- `python3 scripts/validate_docs.py` — PASS.
- `git diff --check` — PASS.

## ADR impact

Aligned with ADR-005, ADR-039, ADR-040, ADR-041, ADR-042, ADR-049, and
ADR-069. No new ADR is required. This attempt preserves the accepted
single-origin, layered-authentication, operator/user-authority, privacy, proof,
and Beta-support boundaries; it does not establish a new exposure or identity
model.

## Documentation follow-through

Only this blocked proof receipt is added. `docs/Ops/private-browser-preview.md`
is intentionally unchanged because the task permits runbook updates only
after `PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_PROVEN`.

## Axis KB addition

Record that the 2026-09-01 Cloudflare ingress provisioning attempt re-proved
the local loopback origin and private-preview port boundary, installed the
official `cloudflared 2026.8.3` client, and then stopped before Cloudflare
inventory or mutation because no least-privilege API-token handoff was
available. `preview.codexify.space` remained unresolved; apex and `www`
continued to resolve; no guest, Cloudflare resource, application code,
credential, unrelated DNS, or unrelated worktree state was changed.
