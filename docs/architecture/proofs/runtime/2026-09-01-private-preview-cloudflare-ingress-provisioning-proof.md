# 2026-09-01 Private-Preview Cloudflare Ingress Provisioning Proof

## Conclusion

`PRIVATE_PREVIEW_CLOUDFLARE_INGRESS_BLOCKED`

The operator attests that One-time PIN is now enabled, but the next resumption
stopped before Cloudflare inventory or mutation because the local
private-preview runtime became unreachable. Static configuration still passes;
live loopback reachability does not.

This is a pre-mutation local-runtime block. Docker Desktop reported
`stopping`, the private-preview container inventory was unavailable, and both
the public root and `/health` on `127.0.0.1:8081` timed out. Restarting Docker
Desktop would affect unrelated workloads and is outside this task's mutation
authority. No Tunnel, DNS record, Access application, Access policy, connector
configuration, guest account, or application behavior was created, changed,
or deleted. The friends-and-family canary remains closed.

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
- OTP-enablement resumption source commit:
  `0de037df6eb974950be7eb47cc100665d552f421`
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
| Loopback reachability | BLOCKED | The validator ended with `curl: (56) Recv failure: Connection reset by peer`; bounded follow-up requests to `/` and `/health` both timed out with HTTP `000`. |
| Docker authority | BLOCKED | `docker desktop status` reported `stopping`; `docker compose ... ps` and `docker ps` returned no running inventory during the bounded diagnosis. |
| Private-preview host-port isolation | NOT CURRENTLY PROVABLE | Static configuration still resolves only `private-preview-origin 127.0.0.1:8081 -> 8080`, but live container publication could not be re-observed while Docker Desktop was stopping. |
| Recovery prerequisite | PASS (prior proof) | The 2026-09-01 recovery requalification receipt remains proven and its retained checkpoint was not touched. |
| Guardian secret rotation prerequisite | PASS (prior proof) | The 2026-09-01 Guardian authentication-secret rotation receipt remains proven; no session or secret state was changed. |

No Docker restart, Compose start/stop, or container mutation was attempted
because Docker Desktop authority is shared with unrelated workloads. This
receipt makes no claim about those workloads' current state, architecture, or
support posture.

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
| Access identity-provider inventory | PRIOR BLOCK RESOLVED BY OPERATOR ATTESTATION; OTP live verification deferred because the local prerequisite failed first. |

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

The following gates require restored local runtime health and were not weakened
or substituted:

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

The operator must restore Docker Desktop to `running` without asking this task
to restart the shared engine or mutate unrelated workloads. Once Docker is
running, the private-preview project must again pass the canonical static and
reachability validators and re-establish the live loopback-only publication
before any Cloudflare API call or mutation resumes.

After local health is restored, rerun this same atomic task with the existing
secure token file if the token remains active. The task must first verify the
operator-attested OTP provider, repeat the full inventory before mutation,
reconcile rather than duplicate resources, and retain the fail-closed
conclusion unless every canonical DNS, HTTPS, Access, Guardian-layering,
isolation, fallback, and preservation gate passes.

## Validation results

- `git status --short --branch` — PASS; source branch/HEAD recorded and only
  the unrelated Dev Log deletion was initially dirty.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh static` — PASS, 39 focused checks.
- `PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 bash scripts/private_preview_validate.sh reachability` — BLOCKED by connection reset.
- Bounded `curl` requests to `/` and `/health` — BLOCKED by timeout, HTTP
  `000`.
- `docker desktop status` — BLOCKED, `stopping`.
- Live Docker/Compose publication inventory — unavailable while the shared
  engine was stopping.
- `cloudflared --version` — PASS after authorized installation,
  `2026.8.3`.
- Secure token-file mode/ownership/structure checks — PASS.
- Cloudflare API-token verification — PASS, active.
- Exact account/zone identity verification — PASS.
- Tunnel and DNS pre-mutation inventory — PASS; no Tunnel and no preview DNS
  record existed.
- Access application inventory — PASS; Access is enabled and no applications
  exist.
- Access identity-provider inventory — prior result was zero; the operator now
  attests OTP is enabled, but live re-verification was not reached because the
  local prerequisite failed first.
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

Record that the 2026-09-01 Cloudflare ingress provisioning task remains
fail-closed across resumptions. After the operator attested OTP enablement, the
next local preflight passed 39 static checks but failed loopback reachability;
Docker Desktop was `stopping`, root and health timed out, and live container
publication could not be observed. Cloudflare was not queried or mutated in
that resumption because local health precedes external exposure. No shared
Docker restart, guest, Cloudflare resource, application code, credential,
unrelated DNS, or unrelated worktree state was changed.
