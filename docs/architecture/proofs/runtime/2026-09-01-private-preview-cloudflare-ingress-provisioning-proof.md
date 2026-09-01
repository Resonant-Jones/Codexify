# 2026-09-01 Private-Preview Cloudflare Ingress Provisioning Proof

## Conclusion

`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_BLOCKED`

The canonical local private-preview origin remains healthy and loopback-only,
the current official `cloudflared` client is installed, the resumed
least-privilege Cloudflare credential handoff is valid, and Cloudflare Access
is now enabled. Authenticated inventory then proved that the Access account has
no configured identity provider or login method.

This is a pre-mutation Access identity-provider block. Creating an identity
provider changes account-wide Zero Trust authentication state, while this task
authorizes only the preview application and its policies. No Tunnel, DNS
record, Access application, Access policy, connector configuration, guest
account, or application behavior was created, changed, or deleted. The
friends-and-family canary remains closed.

## Scope and authority

- Execution model requested by the task: `Sol xhigh`
- Workflow lane: `architecture-impact`
- Task kind: implementation plus live proof
- Evidence posture: live-runtime preflight with blocked control-plane
  disposition
- Execution date: 2026-09-01 local time
- Initial source branch and commit: local `main` at
  `e19defc9fc4e18e0ec75b2cd8f32ed4b61752f4f`
- Credential-boundary resumption source commit:
  `5b9dfe8d7fc8de2d17464fef89c2cd1dfd47fade`
- Access-enablement resumption source commit:
  `69311f2cce53892286ca6cd25d0d949d27501d12`
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
| Secure token-file pointer | PASS; operator supplied an absolute path outside Git. |
| Token-file structure | PASS; regular, non-symlink, non-empty, operator-owned, mode `0600`. |
| API-token verification | PASS; token status `active`. |
| Supplied zone identity | PASS; exact zone is `codexify.space` in the supplied account. |
| Tunnel inventory authorization | PASS. |
| DNS inventory authorization | PASS. |
| Access application inventory | PASS; Access is enabled and no applications exist. |
| Access identity-provider inventory | BLOCKED; zero login methods are configured. |

The token was read only from the mode-`0600` file through an in-memory
authorization header. It was not placed in shell history or process arguments,
printed, copied into temporary proof output, copied into the repository, or
inferred from a broad browser/dashboard session.

## Authenticated Cloudflare inventory

The existing-state inventory was completed before any mutation:

- active non-deleted Tunnels in the account: `0`;
- exact `codexify-private-preview` Tunnels: `0`;
- exact `preview.codexify.space` DNS records: `0`;
- total DNS record count observed for preservation comparison: `8`;
- Access applications: `0`;
- Access identity providers/login methods: `0`.

Access application and identity-provider inventories both succeeded. The stop
is caused by an empty authentication-method configuration, not by token denial
or an API failure. No duplicate, partial, stale, or ambiguously owned preview
resource was discovered before the stop.

## Public DNS baseline

Bounded host DNS checks and authenticated zone inventory before any Cloudflare
mutation reported:

- `preview.codexify.space`: no answer;
- `codexify.space`: resolves;
- `www.codexify.space`: resolves.

The authenticated zone inventory contained eight records in total. No record
values for the apex, `www`, or unrelated names are reproduced here. No
`/etc/hosts` override was used. Because no mutation occurred, preservation is
proven as a no-operation fact for this execution; a before/after configuration
comparison remains required when provisioning resumes.

## Gates not run

The following gates require a usable Access identity provider/login method and
were not weakened or substituted:

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

An authorized Cloudflare operator must add one intended Access login method for
account `9c05ebbb19fac01d8c521f4ce19dfa71` through Zero Trust > Integrations >
Identity providers. For this exact-email friends-and-family boundary, the
minimal option is Cloudflare One-time PIN (`onetimepin`); an already trusted
organizational identity provider is also acceptable if it is the operator's
intended authority.

The operator action must not create the preview application, policy, Tunnel,
DNS record, guest account, wildcard rule, or unrelated identity configuration.
After the operator confirms the login method is present, rerun this same atomic
task with the existing secure token file if the token remains active. The task
must repeat inventory before mutation, reconcile rather than duplicate
resources, and retain the fail-closed conclusion unless every canonical DNS,
HTTPS, Access, Guardian-layering, isolation, fallback, and preservation gate
passes.

## Validation results

- `git status --short --branch` — PASS; source branch/HEAD recorded and only
  the unrelated Dev Log deletion was initially dirty.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS, 39 focused checks.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — PASS.
- `docker ps --format '{{.Names}}\t{{.Ports}}'` — PASS for the bounded
  private-preview publication contract.
- `cloudflared --version` — PASS after authorized installation,
  `2026.8.3`.
- Secure token-file mode/ownership/structure checks — PASS.
- Cloudflare API-token verification — PASS, active.
- Exact account/zone identity verification — PASS.
- Tunnel and DNS pre-mutation inventory — PASS; no Tunnel and no preview DNS
  record existed.
- Access application inventory — PASS; Access is enabled and no applications
  exist.
- Access identity-provider inventory — BLOCKED; no login method exists.
- Public DNS presence checks — preview absent; apex and `www` present.
- `python3 scripts/validate_docs.py` — PASS after this resumption update.
- `git diff --check` — PASS after this resumption update.

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

Record that the 2026-09-01 Cloudflare ingress provisioning task re-proved the
local loopback origin and private-preview port boundary, installed the official
`cloudflared 2026.8.3` client, accepted and safely verified the resumed
least-privilege API-token handoff, and inventoried zero Tunnels, zero
`preview.codexify.space` DNS records, zero Access applications, and zero Access
identity providers. It then stopped before mutation because no Access login
method exists and identity-provider configuration is outside this task. Apex
and `www` remained present; no guest, Cloudflare resource, application code,
credential, unrelated DNS, or unrelated worktree state was changed.
