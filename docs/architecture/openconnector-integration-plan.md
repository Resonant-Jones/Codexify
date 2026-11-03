# OpenConnector v1.9.4 Integration Plan

> Classification: architecture planning document
>
> Status: proposed future architecture — not current runtime truth
>
> This document is **not** an accepted ADR, **not** a release claim, and **not**
> evidence of any running integration. No OpenConnector runtime is installed,
> deployed, or connected by this task.

### Decisions of record

| Decision | Outcome |
| --- | --- |
| **Licensing baseline** | OpenConnector `v1.9.4`, Apache-2.0. Adopted. |
| **Upstream maintenance policy** | **Pin, but track upstream releases** (§1.4). v1.9.4 remains the licensed baseline; monitoring, evaluation, and remediation are an explicit operator responsibility. Tracking later releases does **not** authorize copying code newly published under more restrictive licensing. Deliberately lightweight — **no dedicated security-monitoring subsystem**. |
| **Deployment boundary** | **Separate Compose project**, not a Codexify stack overlay (§2.1). Independent deployment, storage, and lifecycle. The private network is **containment, not authorization** (§2.3); Guardian-to-gateway authentication and connection scoping remain load-bearing. |
| **Integration posture** | **Prove before integrating.** Gate A is disposable and answers one question (§6, Gate A). It has completed with a **conditional pass**. No Guardian adapter work until the gate that follows is authorized. |
| **Runtime authentication** | **Deployment enforcement secret + explicit bootstrap sequence** (§2.4). The deployment-scoped runtime guard is **required**, never distributed, and never presented for execution; the bootstrap sequence then creates the first scoped persistent token, proves an unauthenticated `/v1` request is rejected, and only then admits credentials. The earlier prohibition on setting `OOMOL_CONNECT_RUNTIME_TOKEN` is **superseded** (§2.4, §4.7(a)). |
| **Delegated custody authority** | **Accepted 2026-11-02** (§4.7(a)). Bounded amendments to ADR-094 and ADR-071 admit the gateway as a subordinate, external credential custodian and execution substrate. Guardian remains the sole account-authorization authority; the custodian holds delegated custody only. Acceptance is an architecture decision and authorizes no deployment, implementation, or release widening on its own. |
| **Connection grants** | **Never empty.** An empty or omitted `allowedConnections` is *unrestricted access*, not deny-all (§5.1.1). Every token carries an explicit non-empty grant, and the unrestricted-grant token is revoked before any credential-bearing connection exists. |
| **Authentication lifecycle** | **The token store is never empty** (§5.1.1). Upstream re-derives runtime auth from a **live** store query on every request, so in the store-dependent mechanism, revoking the last token **reopens** the unauthenticated window. With the deployment guard present the runtime stays fail-closed by configuration regardless, which is why the store invariant is retained as defense in depth rather than as the primary protection: a **sentinel token** keeps the store non-empty for the gateway's life, and every handoff **overlaps** (create successor → verify → revoke predecessor). |
| **Trigger surface** | **Explicitly blocked** at the deployment layer (`OOMOL_CONNECT_BLOCKED_TRIGGERS="*"`). Triggers are an **independent** execution policy from Actions and Proxies, so blocking proxies does not block them. |
| **Read-only enforcement** | The Command Bus GET-only rule is a **classification**, not a safety guarantee (§3.4). Gate B requires a **reviewed, server-controlled read-only action allowlist** — upstream actions carry no read-only marker. |
| **OAuth callback** | **Gate C design decision, deferred** (§2.8, §4.7(b)). Two open options: a restricted HTTPS reverse proxy in front of upstream's own `/oauth/callback`, or a Guardian-owned forwarding handler. **No ADR amendment opened yet.** |

---

## Purpose

Codexify needs access to external applications without maintaining a separate
custom adapter for every provider. OpenConnector
(`oomol-lab/open-connector`) is a candidate **implementation substrate** for
that need: an Apache-2.0 connector gateway that exposes provider Actions over
HTTP, MCP, and OpenAPI while keeping provider secrets behind its own runtime
boundary.

This document is the installation-ready blueprint for integrating OpenConnector
as an **optional, isolated** Codexify connector runtime. It defines:

1. the exact licensed upstream version and how to pin it immutably;
2. an isolated deployment topology with its own image, volume, network, and
   credential custody;
3. the Guardian-side integration boundary that reuses the existing Connections
   catalog and Command Bus without duplicating either;
4. the credential-authority and tenant-isolation model, including the points
   that need an ADR amendment before implementation;
5. the first read-only validation slice and the gate sequence that follows.

### What this task does not do

Per the task authorization, this task produces **a document only**. It does
not install Docker images, deploy containers, configure OAuth applications,
create live credentials, run database migrations, add runtime routes, add
provider adapters, change Settings/UI, enable quarantined connector routes, or
alter existing Notion/Google Drive behavior.

---

## Current-Truth Anchors

These statements are true of the repository as read for this task.

| Fact | Anchor |
| --- | --- |
| Connections is a canonical projection/control plane, never an execution owner | ADR-071, `docs/architecture/connections-control-plane.md` |
| The Command Bus is the existing execution authority for agent-invocable operations | ADR-075, `guardian/command_bus/` |
| The local supported profile is local-first and profile-governed | `config/supported_profiles/v1-local-core-web-mcp.yaml` |
| Generic connector execution is quarantined in the supported profile | `v1-local-core-web-mcp.yaml` → `route_posture.quarantined` includes `connectors` |
| Notion and Google Drive knowledge execution paths already exist | `guardian/connections/notion/`, `guardian/connections/google_drive/` |
| The Connections catalog is a static, code-proven projection; per-user state is merged at request time | `guardian/connections/catalog.py`, `guardian/routes/connections.py` |
| Command Bus commands are derived from the mounted routes, with a visibility policy | `guardian/core/route_visibility.py`, `guardian/command_bus/manifest.py:22-80` |
| A command's risk/effect/idempotency/approval mode is derived from its HTTP method | `guardian/command_bus/manifest.py:134-137` |
| Account identity is a server-derived dependency, never a request body field | `guardian/core/dependencies.py` (`get_account_user_id`, `require_account_session`) |
| Provider credential material is encrypted at rest by a server-side primitive | `guardian/connectors/oauth_crypto.py` |

### Not yet true — do not assume

- OpenConnector is **not installed** anywhere in this repository, and **no gateway
  is running** on any Codexify host — the disposable Gate A trial project, its
  volume, and its network were destroyed after qualification.
- Gateway-to-Guardian compatibility is **not proven**. No Codexify code path
  has yet spoken to an OpenConnector instance.
- Multi-user connection isolation is proven **at the gateway mechanism level**
  only — Gate A observed cross-account denial between two synthetic accounts
  through the runtime-token grant — but is **not proven through the Guardian
  adapter path**, which does not exist yet.
- OpenConnector is **not Beta Supported**. Per ADR-069 and
  `docs/architecture/00-current-state.md`, connectors are not default Beta
  support without current-main qualification.
- No release posture, support claim, or current-state statement is widened by
  this document. `docs/architecture/00-current-state.md` remains the release
  truth source and is **not modified** by this task.

---

## 1. Version, Licensing, and Pinning

### 1.1 Verified upstream identity

| Property | Value | How verified |
| --- | --- | --- |
| Repository | `https://github.com/oomol-lab/open-connector` | — |
| Tag | `v1.9.4` | Git ref API |
| **Exact commit** | **`d89dc9f24f5a057bb500272d7dbf333837c77c68`** | `GET /repos/oomol-lab/open-connector/git/ref/tags/v1.9.4` → `{"type":"commit","sha":"d89dc9f24f5a057bb500272d7dbf333837c77c68"}` |
| Tag type | Lightweight tag pointing directly at the commit object | Same response (`object.type == "commit"`) |
| Release | GitHub Release `v1.9.4`, published `2026-10-27`, `target_commitish` = the same commit | Releases API |
| License | **Apache License, Version 2.0** | `LICENSE.txt` at the commit |
| License file | `LICENSE.txt` (verbatim Apache-2.0 text) | Raw fetch at the commit |
| NOTICE file | `NOTICE.md` **present at repo root** | Raw fetch at the commit |
| Upstream `SECURITY.md` | Present; security fixes land on **latest release and `main` only** | Raw fetch at the commit |

### 1.2 LICENSE and NOTICE obligations

The upstream `LICENSE.txt` is the standard, unmodified Apache-2.0 text,
including its §4 redistribution conditions. `LICENSE.txt` ends with the
Apache "APPENDIX: How to apply the Apache License to your work" boilerplate in
which the placeholder `Copyright [yyyy] [name of copyright owner]` is
**unfilled** — upstream ships no named copyright holder line in the license
file itself.

`NOTICE.md` exists and reads:

> **Notices**
>
> OOMOL Connect is licensed under the Apache License, Version 2.0, except where
> otherwise noted.
>
> Third-party provider and app names, trademarks, logos, icons, service marks,
> trade names, APIs, documentation, and brand assets remain the property of
> their respective owners.
>
> References to third-party providers are included for identification and
> interoperability only. Such references do not imply endorsement, sponsorship,
> partnership, certification, or verification by the third-party owner.

**What the license requires, and what Codexify chooses to do.**

Apache-2.0 §4 is titled *"Redistribution"*. Its obligations attach to
**redistributing** the Work or Derivative Works — §4(d) reads *"any
Derivative Works **that You distribute** must include a readable copy of the
attribution notices contained within such NOTICE file."* Running an unmodified
upstream dependency as part of a hosted service, without redistributing it, is
**not** a redistribution and does not by itself trigger §4's conditions. The
license also does not universally require *verbatim* reproduction of every
sentence of a NOTICE file; §4(d) requires a readable copy of the attribution
notices, excludes notices that do not pertain to the work, and expressly
permits adding Codexify's own attribution alongside the upstream text.

The obligations therefore bind **conditionally, on redistribution**:

| Trigger | Consequence |
| --- | --- |
| Codexify redistributes upstream source, a derivative image, or a vendored bundle | **§4(a)–(d) apply in full**: ship the Apache-2.0 license text (§4a), mark modified files (§4b), retain copyright/patent/trademark/attribution notices in the distributed source form (§4c), and — because a `NOTICE` file exists — include a readable copy of the attribution notices from `NOTICE.md` (§4d). |
| Codexify runs the unmodified upstream image as a private dependency and distributes **no** derivative work | §4's redistribution conditions are **not** triggered. |

**Codexify's own policy — retained deliberately, and stricter than the legal
minimum.** Independently of what the license requires, Codexify **keeps the
upstream `LICENSE.txt` and `NOTICE.md` alongside its dependency artifacts and
records** — the pinned-version entry in this document, and any vendored
artifact directory. This is a **conservative project practice** adopted so
that the licensing position is unambiguous and survives future staff changes,
**not** a claim that §4(d) compels it in a non-redistribution deployment. The
two are kept distinct on purpose: conflating them would overstate the legal
obligation and would equally misstate the policy if the deployment posture
ever changed.

Two further points that hold in **both** cases:

5. **§6 (Trademarks)** — the Apache grant does not extend to upstream's trade
   names or product names beyond customary descriptive use. Codexify must not
   brand its product surface as "OOMOL Connect" or imply upstream
   endorsement, sponsorship, partnership, certification, or verification.
6. Upstream `SECURITY.md` states plainly that **insecure self-hosted
   configuration is out of scope for upstream security reports** — running
   without an encryption key, running without an admin token, binding to
   `0.0.0.0` on an untrusted network, or exposing the data store. Codexify
   therefore owns the hardening posture of its own deployment. This is a
   **responsibility transfer, not a warranty**, and must be stated in the
   operator-facing runbook.

### 1.3 Immutable pinning (the tagged Compose file must not be reused)

The upstream `docker-compose.yml` at `v1.9.4` contains:

```yaml
services:
  connector:
    image: ghcr.io/oomol-lab/open-connector:latest   # <-- MUTABLE
    ports:
      - "3000:3000"                                   # <-- binds all interfaces
    volumes:
      - connector-data:/app/data
```

**The tagged upstream Compose file must not be reused.** Two independent
defects: the image reference is a **mutable `latest` tag**, and the port
mapping publishes the container's administrative interface on **all host
interfaces** with no authentication requirement configured by default. The
`docker-compose.build.yml` overlay is not an acceptable substitute either —
it builds `docker/Dockerfile` from the working tree and tags the result
`ghcr.io/oomol-lab/open-connector:latest`, reintroducing the same mutable
reference.

**Required pinning policy for Codexify:**

| Artifact | Pin form | Value |
| --- | --- | --- |
| Container image | tag **and** digest | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c` |
| `linux/amd64` platform manifest | digest | `sha256:c6752adad5769913daf4eb296f9861175da87198fab15da2fe88330b2b63b58c` |
| `linux/arm64` platform manifest | digest | `sha256:aec27d9ceb68ad0cdf7f28d748bf361cbbd245f1c5b501980eddd77dee17b85b` |
| Source of record | commit | `d89dc9f24f5a057bb500272d7dbf333837c77c68` |
| Upstream release binary digests | sha256 | published in the v1.9.4 release's `SHA256SUMS` asset; e.g. `open-connector-linux-arm64` = `sha256:530d0b75eea8754c8dca1d9894c6d5007c3afb2f36fd037b0f6755d146a94b00` |

The multi-arch index digest `sha256:9cbc8cbb...` is the correct single
reference for `docker pull` on both amd64 and arm64 hosts.

> **Observation, recorded so it is not mistaken for a safety property:** at the
> time of this write, `ghcr.io/oomol-lab/open-connector:latest` resolves to the
> **same** digest `sha256:9cbc8cbb...` as `v1.9.4`. This is a coincidence of
> release timing, **not** a property of `latest`. `latest` is defined by
> upstream as "the newest published release" and moves on every release.
> Pinning must use the `v1.9.4` tag **with** the digest, never `latest`.

**Runtime baseline to verify at build time.** Upstream's `SECURITY.md`
documents CVE-2026-111497 in the native Brotli decoder bundled with Node.js
and Bun, and requires Node.js `22.23.4+` / `24.22.1+` / `26.12.1+`, or Bun
`1.4.4+`. Upstream states the Docker build and runtime stages pin Node
`24.22.1`. Because the vulnerability is in the *runtime*, not the image layer,
the deployed container must be verified with
`docker exec open-connector node --version`. **Pulling a newer image does not
update a running container** — the container must be recreated.

### 1.4 Independent-fork and future-upgrade boundaries

**No upstream fork is authorized or proposed.** Codexify consumes upstream
release artifacts unmodified. A fork would create a permanent maintenance
and security-patch obligation that Codexify has not accepted, and would
undermine the upstream `SECURITY.md` support window.

The operative constraint is upstream's own support policy: upstream applies
security fixes to the **latest release and `main` only**; older releases
receive none. Pinning `v1.9.4` therefore means Codexify inherits a
**time-bounded security exposure** that grows with every upstream release.

That exposure is **accepted deliberately**, and the following policy is the
governing maintenance commitment. It is a **named operator responsibility**,
not an assumption that upstream's maintainers will cover Codexify's exposure.

#### The maintenance policy: pin, but track upstream releases

| Phase | Commitment |
| --- | --- |
| **Pin** | Preserve the exact source commit (`d89dc9f24f5a057bb500272d7dbf333837c77c68`), the Apache-2.0 `LICENSE.txt`, the `NOTICE.md`, and the immutable container digest (`sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c`). The pinned baseline is the licensed artifact Codexify actually depends on. |
| **Monitor** | Track upstream releases, security advisories, and relevant dependency vulnerabilities. Upstream publishes at `github.com/oomol-lab/open-connector` (releases and `SECURITY.md`); vulnerability reports go to upstream's private advisory channel or `support@oomol.com`. |
| **Evaluate** | For each discovered vulnerability, determine whether it **actually affects our deployment and exposure model** — our pinned version, our hardened configuration, our network posture, our action allowlist, and our credential-custody model. Not every upstream advisory is in our path. |
| **Remediate** | Independently implement compatible fixes, update dependencies where possible, purchase a newer license, or switch providers. |
| **Stop condition** | A **material unpatched vulnerability affecting our deployment** blocks promotion or requires disabling the affected capability. |

**This is deliberately lightweight.** Codexify does **not** stand up a
security-monitoring subsystem, a bespoke scanner, or a dedicated pipeline for
OpenConnector. Monitoring is an **operator responsibility performed by
reading upstream's release and advisory channels** — the same manual practice
already applied to every other upstream dependency. Automation, if it ever
becomes warranted, must be justified by the number of tracked upstream
dependencies, not created for this one in isolation.

**Licensing boundary on remediation.** Tracking later upstream releases does
**not** authorize copying code that is newly published under more restrictive
licensing. The pinned baseline is the Apache-2.0-licensed v1.9.4 artifact, and
that is the licensed material Codexify may use and modify. If a future
upstream release changes its license — for example to a source-available or
proprietary term — then:

- code from that release may **not** be copied into the Codexify
  baseline, backported into it, or vendored from it;
- "purchase a newer license" in the remediation table means **obtaining
  rights** to the new artifact on acceptable terms, not assuming the new
  terms apply retroactively to the Apache-2.0 baseline;
- if the new terms are unacceptable, the remediation path is **switching
  providers**, and the Apache-2.0 baseline remains a valid, separately
  licensed, self-contained artifact.

Any license change upstream is therefore an **Evaluate** input, not a routine
upgrade step, and must be surfaced to the operator before any action is taken.

#### Upgrade path

Move the digest forward to a newer upstream release tag, re-run the Gate A
qualification suite against the new digest, and re-verify the action catalog
and provider auth contracts. `v1.9.4` must not be silently replaced by a
floating reference, and a new upstream release is **not** a mandate to
upgrade: adopting it is a deliberate Evaluate-then-Remediate decision.

#### Database compatibility

The upstream runtime applies migrations at startup for SQLite; for PostgreSQL
the image exposes an explicit `migrate` subcommand and the server **never**
applies DDL during startup. Migration and server must use the **same** image
tag/digest. Codexify's Gate A uses SQLite (see §2) so that no external
database migration is introduced into a deployment whose qualification is
still pending.

### 1.5 Third-party provider API and OAuth obligations

OpenConnector is a **gateway**, not a provider. Every provider it fronts has
its own independent obligations that Codexify inherits **only** if and when a
user authorizes that provider:

- **Provider OAuth application registration.** OAuth2 providers require the
  operator to register their own OAuth client with the provider. The redirect
  URI must match upstream's `expectedRedirectUri` exactly. Local operation uses
  `http://localhost:3000/oauth/callback`; remote operation requires a public
  HTTPS origin and a matching `OOMOL_CONNECT_ORIGIN` (see §2.8).
- **Provider scope and verification.** Requested scopes must come from the
  provider's declared scope set; upstream rejects unknown scopes rather than
  silently widening authorization. Some providers classify scopes as
  restricted or sensitive and require app verification — a **provider-side
  verification process Codexify cannot perform or expedite**.
- **Provider terms of service.** Each provider's API terms, rate limits,
  attribution, and retention rules apply independently of upstream's and
  Codexify's licenses.
- **Trademark and naming.** Upstream's `NOTICE.md` reserves third-party
  provider names, trademarks, and brand assets. Codexify's Connections catalog
  must display provider names for identification only, and must not imply
  endorsement, sponsorship, partnership, certification, or verification.
- **Secret handling.** Provider tokens must never reach Codexify's browser,
  logs, or model context (§4).

---

## 2. Deployment Topology

### 2.1 Isolation principle

OpenConnector runs as a **separate, optional service outside the Codexify
Compose project**. This task does **not** modify `docker-compose.yml`. The
proposed artifact is a **new, separately-invoked Compose file** that Codexify
attaches to only when explicitly requested.

Rationale for a separate project rather than an overlay file:

- The existing repo already establishes the pattern of opt-in overlay files
  (`docker-compose.codex-runner-bridge.yml`, `docker-compose.private-preview.yml`)
  that are applied only via an explicit `-f` flag. An OpenConnector overlay
  would technically satisfy "no mutation."
- **A separate project is nevertheless the stronger choice**, because OpenConnector
  introduces a *credential vault with its own administrative interface and its
  own data store*. Co-locating it in the Codexify project network would make
  it reachable from every Codexify service by default and would place its
  encrypted credential database inside the same blast radius as the Codexify
  stack. The isolation boundary should be a project boundary, not just a
  label.
- Consequently the plan **does not create** `docker-compose.openconnector.yml`
  as a Codexify stack overlay. It specifies a standalone Compose project. The
  Codexify side attaches to it deliberately, by name, in a later gate.

### 2.2 Proposed service definition

The following is the **specified target topology**. It is not created by this
task.

```yaml
# Standalone OpenConnector project — NOT part of the Codexify compose stack.
# Invoke with:  docker compose -p codexify-openconnector up -d
name: codexify-openconnector

services:
  openconnector:
    # Immutable pin: tag AND digest. Never use :latest (see §1.3).
    image: ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c
    container_name: codexify-openconnector
    restart: unless-stopped

    # --- Network posture -------------------------------------------------
    # NO 'ports:' stanza at all. The service is reachable only from
    # containers attached to 'codexify_internal'. This removes the
    # 0.0.0.0 administrative-interface exposure of the upstream Compose file.
    networks:
      - codexify_internal
    expose:
      # Documentational only: 'expose' publishes no host port.
      - "3000"

    # --- Data ------------------------------------------------------------
    volumes:
      - openconnector_data:/app/data

    # --- Secrets: ONE injection mechanism ------------------------------
    # env_file is the single source of truth for secret values. It is a
    # container-level mechanism: Compose passes the file's contents into
    # the container verbatim.
    #
    # DO NOT also use ${VAR} interpolation in 'environment:' below for the
    # same values. Compose resolves ${...} from its OWN interpolation
    # environment (the shell, or --env-file / a project .env file) — NOT
    # from the service's env_file. Mixing the two mechanisms silently
    # produces an empty value or a hard startup failure, and the two
    # sources can disagree.
    env_file:
      - /run/secrets/openconnector.env

    environment:
      OOMOL_CONNECT_DATA_DIR: /app/data
      # Non-secret settings only. Secrets live in env_file alone.
      OOMOL_CONNECT_BLOCKED_ACTIONS: ""
      # Provider proxy is disabled outright: /v1/proxy/:service reaches
      # provider API endpoints beyond the curated Action catalog, and every
      # proxy is allowed until one of these variables restricts it.
      OOMOL_CONNECT_BLOCKED_PROXIES: "*"
      OOMOL_CONNECT_ALLOWED_PROXIES: ""
      # Provider Triggers are disabled outright. Triggers are evaluated by an
      # INDEPENDENT policy (allowedTriggers / blockedTriggers), separate from
      # Actions and Proxies, so blocking proxies does not block them. A
      # Trigger can perform provider API calls its registered operation needs
      # "without a public proxy grant", so it is a distinct execution surface.
      # Blocked at the DEPLOYMENT layer so the denial holds even when no
      # runtime token is present (see the zero-token window in section 2.4).
      OOMOL_CONNECT_BLOCKED_TRIGGERS: "*"
      OOMOL_CONNECT_ALLOWED_TRIGGERS: ""
      # Keep upstream's SSRF guard in its default posture.
      OOMOL_CONNECT_ALLOW_PRIVATE_NETWORK: "false"
      OOMOL_CONNECT_EGRESS_TRUSTED_HOSTS: ""

    # --- Health ----------------------------------------------------------
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 20s

    # --- Resource limits -------------------------------------------------
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.25"
          memory: 256M

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  openconnector_data:
    name: codexify_openconnector_data

networks:
  codexify_internal:
    name: codexify_internal
    driver: bridge
```

### 2.3 Network isolation

- **No published ports.** The service has no `ports:` stanza, so Docker
  publishes nothing to the host. The upstream `3000:3000` mapping — which binds
  all host interfaces — is deliberately not reproduced.
- **Named bridge network `codexify_internal`.** Only containers that are
  explicitly attached can resolve `openconnector` and reach port 3000.
  Codexify's `backend` (and any worker that may invoke the gateway) attaches
  to this network **explicitly**, in a later gate. No other Codexify service
  attaches.
- **No public administrative interface.** The Web Console, `/api/*`, and
  `/docs` are reachable only from inside `codexify_internal`, and are
  additionally protected by `OOMOL_CONNECT_ADMIN_TOKEN` (§2.4).
- **The private network is containment, not authorization.** Network
  separation is a **blast-radius and reachability control**: it keeps the
  gateway off the public interface and out of unrelated services' reach. It
  grants **no identity, no tenant isolation, and no credential scoping**. A
  container attached to `codexify_internal` is not thereby a trusted caller —
  it can still reach the admin surface if it holds the admin token, and it can
  still reach another user's connection if it holds an unrestricted token.
  Therefore the network posture is **necessary but not sufficient**: the
  Guardian-to-gateway authentication, per-user runtime-token scoping, and
  explicit user-to-connection binding in §4 remain **load-bearing
  requirements**. Treating the private network as the security boundary would
  be a category error, and no Gate evidence may be produced by pointing at
  network isolation alone.
- **Egress posture.** `OOMOL_CONNECT_ALLOW_PRIVATE_NETWORK` stays `"false"`,
  preserving upstream's default SSRF guard that restricts provider calls to
  public destinations. `OOMOL_CONNECT_EGRESS_TRUSTED_HOSTS` is left empty
  unless a specific corporate-VPN-hosted provider requires it; populating it
  is an explicit operator decision with its own review.
- **Outbound egress remains the provider's problem, not Codexify's.** The
  gateway reaches third-party APIs, not Codexify internals. Codexify's own
  `CODEXIFY_EGRESS_ALLOWLIST` is not widened by this plan.

### 2.4 Authentication: runtime versus administration

Upstream ships **two distinct credential classes** on one port, and the
distinction is load-bearing for the Codexify boundary:

| Class | Variable | Protects | Codexify position |
| --- | --- | --- | --- |
| **Administration** | `OOMOL_CONNECT_ADMIN_TOKEN` | `/api/*`, `/docs`, Web Console | Operator-only. Never sent to a model, never sent from a Guardian runtime path. Held in the host secret store. |
| **Deployment guard** | `OOMOL_CONNECT_RUNTIME_TOKEN` | `/v1/*`, `/mcp` | **Required as a deployment enforcement secret** (§4.7(a)). Service-owned, operator-custodied, and **never presented for execution**. It carries no stored connection grant, so presenting it is unrestricted with respect to connections — which is exactly why no account path may present it. |
| **Persistent runtime** | `oct_...` tokens (hashed at rest) | `/v1/*`, `/mcp` | The **only** runtime credential Codexify's runtime path may use. Each carries an explicit `allowedConnections` allowlist of stable opaque connection IDs. |
| **JWT access** | `OOMOL_CONNECT_JWKS_URI` / `_JWT_ISSUER` / `_JWT_AUDIENCE` | `/v1/*`, `/mcp` | Not used in the first slice. Upstream states JWTs do not map claims to action or proxy policy and have no stored connection grant; a JWT-only deployment would be unrestricted by connection. Deferred behind the ADR question in §4.7. |

Upstream's own security guidance is explicit that **both** admin and runtime
authentication are disabled by default for local development, and that a
deployment must never expose the gateway publicly without both enabled. This
plan enables both, and additionally ensures the administrative interface is not
network-reachable at all (§2.3).

#### The unauthenticated-runtime bootstrap window — and how it is closed

The deployment guard (`OOMOL_CONNECT_RUNTIME_TOKEN`) is a long-lived credential that
carries no stored connection grant, so it is **never presented for execution** —
it exists to make the runtime surface fail closed, not to authorize anything
(§4.7(a)). Configuring it does close the permissive branch described below, **but
only when Codexify actually supplies it and verifies that the running container
carries it**: upstream's behavior on a missing runtime token *is* the permissive
branch, and its startup warning is advisory. **The gateway does not provide
fail-closed startup.** Fail-closed startup is a Codexify-side deployment-pipeline
obligation — the §2.5 preflight, a post-start assertion that the guard is
present in the running container, and a promotion gate (§4.7(a)).

Upstream's auth middleware resolves runtime authentication as follows (verified
in upstream `src/server/api/auth.ts` and `src/server/connect-app.ts` at the
pinned commit):

- `createLocalAuthMiddleware` installs a **pass-through** middleware — no
  authentication at all — when there is no admin token, no runtime token, no
  `requireRuntimeAuth`, **no stored runtime tokens**, and no JWT verifier.
- `hasValidToken` returns `true` for runtime scope when there is no
  configured runtime token **and** `requireRuntimeAuth` is unset **and** no
  runtime tokens are stored **and** no JWT verifier is configured.
- Upstream computes `runtimeAuthConfigured` as
  `requireRuntimeAuth || runtimeToken || verifyRuntimeJwt || hasStoredRuntimeTokens()`,
  and logs `runtime API authentication is disabled; create a runtime token in
  the web console, set OOMOL_CONNECT_RUNTIME_TOKEN, or configure JWT
  authentication` when it is false.

**Consequence:** on a **fresh database**, with no bootstrap token and no
persistent token yet created, the `/v1` runtime API is **unauthenticated**.
The admin API is separately protected by `OOMOL_CONNECT_ADMIN_TOKEN`, so the
exposure is confined to the runtime surface — but the runtime surface is
exactly where action execution lives.

**This closes once the first persistent runtime token exists**, because
`hasStoredRuntimeTokens()` then becomes true and `hasValidToken` stops
short-circuiting to `true`.

**The deployment guard closes it by configuration instead, and more strongly.**
`hasValidToken` resolves the scope's *configured* token first (`tokenForScope`);
for runtime scope that is `OOMOL_CONNECT_RUNTIME_TOKEN`. When one **is**
configured, the permissive branch is unreachable: the request must present that
bearer or satisfy `hasValidRuntimeToken` — a stored persistent token or a JWT
verifier. The token-store count therefore stops being part of the authentication
decision, and the runtime is fail-closed **from the first request**, on a fresh
database, with an empty store.

**The guard is deployment infrastructure, not an execution credential** (§4.7(a)):
service-owned, operator-custodied, never distributed, and never presented by an
account path. It carries no stored connection grant, so presenting it would be
unrestricted with respect to connections — which is precisely why no account path
may present it. Its presence makes the runtime fail closed; it grants nothing.

**The token-store invariant remains, as defense in depth.** It is no longer the
primary protection: it is what keeps the runtime fail-closed **if the guard is
ever absent**, and it keeps the protection from depending on a single
configuration variable. The two mechanisms are independent, and the deployment
posture requires both.

**And it re-opens if the store becomes empty again** — *in the store-dependent
mechanism.* With the deployment guard configured, the runtime does not fall back
to the permissive branch; the store-count dependency is exactly what the guard
removes. The mechanism still matters, because it is what keeps the runtime
fail-closed if the guard is ever absent, and it is why the store invariant
below is a standing requirement rather than a nicety. The check is a **live
per-request query**, not a startup-time flag:

```ts
// src/server/connect-app.ts
const hasStoredRuntimeTokens = async (): Promise<boolean> =>
  (await runtimeTokens.listTokens()).length > 0;
```

Because `revoke` deletes the row (`delete from runtime_tokens where id = $1`),
**revoking the last persistent token reopens the unauthenticated window.**
The bootstrap fix and the token-lifecycle fix are therefore the same problem:
the store must never be empty. See §5.1.1's standing invariant and the
overlapping-handoff procedure.

The safe bootstrap is an explicit, ordered sequence:

| Step | Action | State after |
| --- | --- | --- |
| **1** | Establish network containment **first**: the container runs with **no published ports** on `codexify_internal` only, and the admin token, encryption key, **and the deployment guard** are already in place via `env_file`. | The runtime API is **fail-closed by configuration** from the first request, and reachable only from attached containers. |
| **2** | Using the **admin token** against `POST /api/runtime-tokens`, create the **sentinel token** (§5.1.1) — the token that keeps the store non-empty for the gateway's whole life. | `hasStoredRuntimeTokens()` is now true; the runtime API **requires** a bearer token. |
| **3** | Create the **first working token** (P0), with its explicit non-empty grant. | Store = `{sentinel, P0}` — non-empty. |
| **4** | **Verify** that an unauthenticated `/v1` request is now rejected (expect `401`/`403`), that the new tokens are accepted, and that the sentinel **cannot** authorize any operation. | The bootstrap window is **closed and proven closed**. |
| **5** | Only now introduce provider credentials, and only via the admin surface. | Credentials exist, and the runtime surface is already authenticated. |

**Constraints on this sequence:**

- Steps 1–4 are **ordering requirements, not suggestions**. Introducing a
  provider credential at step 1 rather than step 5 would place a stored
  credential behind an unauthenticated runtime API.
- **The sentinel token is created first** and is **never revoked** while the
  gateway runs with credentials present. It is what makes the store
  non-empty a *standing* property rather than a transient one.
- The bootstrap token, if one is used at all, must be **created, used, and
  deleted within step 2** — it must never outlive the initialization, and it
  must never be the deployment guard. The guard is the one long-lived runtime
  credential in the deployment, and it is never presented by any caller
  (§2.5, §4.7(a)).
- Because containment is what protects the window, the §2.3 rule stands
  absolutely here: **the window is survivable only because the runtime
  surface is not network-reachable.** Removing the no-published-ports posture
  would make this window an internet-exposed unauthenticated action API.
  With the deployment guard in place (§4.7(a)) the window is closed by
  configuration as well, so containment is now defense in depth rather than
  the sole protection — **both** are required, and neither is optional.
- **Evidence:** step 4's rejection check is a required Gate A observation
  (§5.3, row 0a), not an inference from configuration — and it must be
  **repeated after every subsequent token handoff**, because the protection
  is re-derived per request and can vanish silently.

#### A note on `requireRuntimeAuth`

Upstream's auth middleware accepts a `requireRuntimeAuth` option that forces
runtime authentication even when no tokens exist. It is **not** exposed as an
`OOMOL_CONNECT_*` environment variable at v1.9.4 — the full upstream variable
set contains no such flag, and upstream's security fixes ship to the latest
release and `main` only, so the flag is **not** a remediation path at the pinned
version. The available levers are `OOMOL_CONNECT_RUNTIME_TOKEN` and the presence
of a stored persistent token. The deployment guard (§4.7(a)) is now the accepted
lever among them: it is required, it is never distributed, and it is never
presented for execution. **The bootstrap sequence in the table above therefore
remains required** — it establishes the scoped persistent tokens that ordinary
execution actually uses, and the sentinel that keeps the store non-empty
independent of the guard. If a future upstream release adds an
environment-configurable require flag, that is a remediation input under §1.4's
Evaluate phase, and it may simplify this sequence.

### 2.5 Credential encryption and recoverable key management

#### Secret injection: one mechanism, fail closed

The secret file supplied via `env_file` (`/run/secrets/openconnector.env`)
**must** contain exactly these keys:

| Key | Requirement |
| --- | --- |
| `OOMOL_CONNECT_ENCRYPTION_KEY` | Required. Without it upstream stores credentials in plaintext and only warns. |
| `OOMOL_CONNECT_ADMIN_TOKEN` | Required. Protects `/api/*`, `/docs`, and the Web Console. |
| `OOMOL_CONNECT_ALLOWED_ACTIONS` | Required. The deployment-level action allowlist. Non-empty. |
| `OOMOL_CONNECT_RUNTIME_TOKEN` | Required as the **deployment guard** (§4.7(a)): present, non-empty, at least 32 characters, and **not** equal to `OOMOL_CONNECT_ADMIN_TOKEN`. It is never distributed and never presented for execution. Per-user scoping for ordinary execution uses persistent `oct_...` tokens (§4.3), not this value. |

**Fail-closed preflight.** Because `env_file` is the only injection
mechanism, Compose cannot validate it — a missing or empty key fails
*inside* the container, at runtime, after the image has started. A Gate A
preflight therefore runs **before** `docker compose up`, and **aborts the
startup on any missing or empty required key** rather than proceeding with a
degraded posture:

```bash
# Fail-closed preflight. Exits non-zero on any violation.
# Reports KEY NAMES and violation reasons only — never secret values.
set -euo pipefail
SECRETS="${1:-/run/secrets/openconnector.env}"
# The exact action ids approved for the trial. Anything else fails.
APPROVED_ACTIONS="hackernews.get_top_stories"
fail=0

# 1. Required keys present and non-empty.
#    NOTE: the value check requires at least ONE non-space character,
#    so a legitimate single-character value is not falsely rejected.
for key in OOMOL_CONNECT_ENCRYPTION_KEY OOMOL_CONNECT_ADMIN_TOKEN OOMOL_CONNECT_ALLOWED_ACTIONS; do
  if ! grep -qE "^${key}=[^[:space:]]" "$SECRETS"; then
    echo "PREFLIGHT FAIL: missing or empty ${key}" >&2
    fail=1
  fi
done

# 2. The deployment guard (OOMOL_CONNECT_RUNTIME_TOKEN) must be PRESENT and
#    well-formed: non-empty, at least 32 characters, and not equal to the admin
#    token. It is an enforcement secret, never presented for execution (§4.7(a)).
GUARD="$(grep -E '^OOMOL_CONNECT_RUNTIME_TOKEN=' "$SECRETS" | head -1 | cut -d= -f2- || true)"
ADMIN="$(grep -E '^OOMOL_CONNECT_ADMIN_TOKEN=' "$SECRETS" | head -1 | cut -d= -f2- || true)"
if [ -z "$GUARD" ]; then
  echo "PREFLIGHT FAIL: OOMOL_CONNECT_RUNTIME_TOKEN missing or empty (runtime would fail open)" >&2
  fail=1
elif [ "${#GUARD}" -lt 32 ]; then
  echo "PREFLIGHT FAIL: OOMOL_CONNECT_RUNTIME_TOKEN shorter than 32 characters" >&2
  fail=1
elif [ "$GUARD" = "$ADMIN" ]; then
  echo "PREFLIGHT FAIL: OOMOL_CONNECT_RUNTIME_TOKEN equals the admin token (role separation violated)" >&2
  fail=1
fi

# 3. The action allowlist must be EXACTLY the approved trial actions.
#    Rejects wildcards ('*', 'github.*') and any unapproved action id.
actual_actions="$(grep -E '^OOMOL_CONNECT_ALLOWED_ACTIONS=' "$SECRETS" | head -1 | cut -d= -f2- || true)"
if [ "$actual_actions" != "$APPROVED_ACTIONS" ]; then
  echo "PREFLIGHT FAIL: OOMOL_CONNECT_ALLOWED_ACTIONS is not exactly the approved trial actions" >&2
  fail=1
fi

# 4. No wildcard may appear in the allowlist.
if printf '%s' "$actual_actions" | grep -qE '(^|,)\*|\.\*'; then
  echo "PREFLIGHT FAIL: OOMOL_CONNECT_ALLOWED_ACTIONS contains a wildcard" >&2
  fail=1
fi

[ "$fail" -eq 0 ] || exit 1
echo "PREFLIGHT OK"
```

**What the preflight now enforces**, and why each check exists:

| Check | Failure it prevents |
| --- | --- |
| Required keys present and non-empty | A missing or blank `OOMOL_CONNECT_ENCRYPTION_KEY` silently degrades to **plaintext credential storage**; a missing admin token leaves `/api/*` open. |
| Deployment guard **present, non-empty, ≥32 characters, and distinct from the admin token** | A missing or empty guard leaves upstream's permissive branch reachable, so the runtime surface is unauthenticated on a fresh database — and `docker compose restart` will not surface the problem, because the container can report healthy while the guard is absent from its environment. A guard equal to the admin token collapses two credential classes into one and destroys role separation. The 32-character floor is Codexify's own entropy requirement for a secret that is never rotated automatically; upstream imposes no length rule. |
| Allowlist **exactly** equals the approved trial actions | A wildcard or a broader list silently widens the executable surface. This is the check the earlier preflight was missing: it accepted `github.*` as "non-empty" when the trial approves exactly one action. |
| No wildcard in the allowlist | Defense in depth against the exact-match check above being weakened by a future edit (e.g. a list joined across lines). |

**The preflight is a policy gate, not a security control.** It validates the
*operator's* configuration before startup; it does not constrain the running
gateway. The gateway's own enforcement remains the deployment-level
allowlist plus each token's grant (§3.6).

Additional preflight properties:

- The preflight reports **key names and violation reasons only** — never
  values.
- **Do not use `docker compose config` as the verification step.** It renders
  the resolved configuration, which **prints expanded secret values** to
  stdout and into shell history and CI logs. If it is used at all for
  structural validation, its output must be redirected to a protected file
  and never captured into logs. The preflight above deliberately avoids it.
- The secret file must be mode `0600`, owned by the deploying user, and
  **outside the repository**. It is never committed, never written into the
  data volume, and never echoed.
- The approved-action list is **supplied by the reviewer of the trial**, not
  derived from the gateway's catalog at runtime. A preflight that read the
  allowlist from the thing it is meant to constrain would be circular.

#### Verified: the deployment-level execution restrictions survived the switch to `env_file`

Moving secrets out of `environment:` must not have silently dropped the
deployment-level execution policy. This was verified by rendering the
**exact Compose block from §2.2** with `docker compose config` against a
**dummy** secret file, with no container started, and asserting the resolved
environment:

| Assertion | Result |
| --- | --- |
| `OOMOL_CONNECT_BLOCKED_PROXIES` is `"*"` | **PASS** |
| `OOMOL_CONNECT_ALLOWED_PROXIES` is empty (no proxy allowlist) | **PASS** |
| `OOMOL_CONNECT_BLOCKED_TRIGGERS` is `"*"` | **PASS** (Triggers blocked at the deployment layer) |
| `OOMOL_CONNECT_ALLOWED_TRIGGERS` is empty (no trigger allowlist) | **PASS** |
| `OOMOL_CONNECT_ALLOWED_ACTIONS` is non-empty | **PASS** |
| `OOMOL_CONNECT_ALLOWED_ACTIONS` is narrowly scoped (exactly the trial action id) | **PASS** |
| `OOMOL_CONNECT_BLOCKED_ACTIONS` is empty | **PASS** |
| `OOMOL_CONNECT_ENCRYPTION_KEY` present | **PASS** |
| `OOMOL_CONNECT_ADMIN_TOKEN` present | **PASS** |
| `OOMOL_CONNECT_RUNTIME_TOKEN` **absent** | **PASS** — *this was the Gate A configuration, deliberately*; see the note below |
| `OOMOL_CONNECT_ALLOW_PRIVATE_NETWORK` is `"false"` | **PASS** |
| Image is digest-pinned (`@sha256:`) | **PASS** |
| **No published ports** in the resolved config | **PASS** |
| `expose` is `3000` only | **PASS** |

**This table records the configuration Gate A actually verified, not the
deployment posture.** Gate A deliberately ran the gateway **without** the
deployment guard, because establishing what the substrate does with the guard
absent is what made the permissive branch observable and the defect reportable.
The **deployment** posture is the opposite: the guard is now **required** (§2.4,
§2.5, §4.7(a)), and a deployment that reaches the next gate without it fails
the §2.5 preflight, fails the post-start assertion that the guard is present in
the running container, and is refused by the promotion gate. The guard-absent
row above is a **historical record of the trial**, not an approved configuration.

Two further fail-closed behaviors were confirmed in the same check:

- A **missing** `env_file` causes Compose to **refuse to render or start**
  (`env file ... not found`) — the container never starts with a missing
  secret file.
- An **empty** `OOMOL_CONNECT_ALLOWED_ACTIONS` **renders successfully** as an
  empty string. This is the one gap the preflight exists to close, and it is
  why the preflight checks that key's presence and non-emptiness rather than
  relying on Compose.

**Upstream semantics behind these values** (verified in
`src/core/action-policy.ts` and `src/server/index.ts` at the pinned commit):

- `parseActionPolicyList("")` returns `[]`, so an empty value means "no rule"
  rather than a malformed rule. Empty values are therefore **safe** — but an
  empty `allowedActions` list means the deployment layer imposes **no
  action constraint**, which is exactly why it must be non-empty.
- `evaluateProxy` evaluates **`blockedProxies` across every layer first**, and
  a block match wins outright. `OOMOL_CONNECT_BLOCKED_PROXIES="*"` therefore
  denies all provider proxy access regardless of `allowedProxies`.
- `OOMOL_CONNECT_ALLOWED_CONNECTIONS` **does not exist** as a deployment
  variable — upstream states connection grants are a token-level concept
  only. Codexify must not invent a deployment-level connection allowlist.

#### Key custody and rotation

- `OOMOL_CONNECT_ENCRYPTION_KEY` is **mandatory** in the topology above.
  Upstream uses AES-256-GCM for provider credential records, OAuth client
  configuration, pending OAuth state, and completed idempotent Action response
  payloads. **Without the key, those payloads are stored in plaintext** and
  upstream only prints a startup warning. Upstream does not store the key.
- **Recoverability requires the key be held outside the gateway volume.** The
  key is a secret in the host's secret store, backed up under Codexify's
  secret-recovery procedure, and **never** written into the `openconnector_data`
  volume or a committed `.env`.
- **Loss of the key means unrecoverable encrypted records.** Upstream states
  this directly. Codexify's operator runbook must say so in the same words:
  losing `OOMOL_CONNECT_ENCRYPTION_KEY` loses every stored provider
  credential, OAuth client configuration, pending OAuth state, and cached
  idempotent response payload. Recovery then requires re-authorizing each
  provider, not restoring the database.
- **Rotation** uses upstream's supported path:
  `OOMOL_CONNECT_NEW_ENCRYPTION_KEY` plus the runtime data-rotation command.
  Upstream requires **pausing all runtime instances** before rotating a
  PostgreSQL key; the same operational discipline is applied here. Rotation
  re-encodes stored credentials, OAuth client configuration, pending OAuth
  state, and completed idempotent response payloads.
- **The data store is a sensitive store even after encryption.** Upstream
  retains completed idempotent Action responses for a **24-hour replay window**
  and deletes expired records only *opportunistically* — there is no
  guaranteed physical-deletion deadline. A backup of the volume is therefore
  a backup of provider-derived data and must be handled at the same
  classification as a credential store.
- **Local key custody, not plaintext-in-image.** The upstream image itself
  stores no key and no credential; custody is entirely the operator's.

### 2.6 Health checks, startup dependencies, and resource limits

- **Health endpoint.** Upstream exposes `GET /health` (expected
  `{"ok": true}`) and `GET /v1/health`. The Compose healthcheck above uses
  the unauthenticated `/health` path, matching upstream's own verification
  recipe. `start_period: 20s` covers cold start; 12 retries at 10s gives a
  ~2-minute readiness budget before the container is marked unhealthy.
- **Startup ordering.** Codexify's `backend` must not treat the gateway as
  available at boot. The Codexify adapter must perform **lazy, bounded health
  probing at request time** rather than caching a boot-time assumption. A
  gateway that starts after Guardian is not an error condition; a gateway that
  is down at invocation time is a bounded `unavailable` outcome (ADR-024).
- **Resource limits** are declared above: `cpus: 1.0`, `memory: 1G` with
  `0.25`/`256M` reservations, and bounded JSON-file logging (`10m` × `3`) so
  the gateway cannot exhaust host disk.
- **No hard dependency edge into the Codexify stack.** The gateway does not
  depend on Codexify. Codexify depends on the gateway only at invocation time.

### 2.7 Backup, restart, upgrade, rollback

| Procedure | Procedure |
| --- | --- |
| **Backup** | Snapshot the `codexify_openconnector_data` volume while the service is stopped (a consistent copy of `connect.sqlite` plus any transit files), **and** separately confirm the encryption key is recoverable from the host secret store. A volume backup without the key is a backup of unrecoverable ciphertext. Treat the artifact as a credential-class secret. |
| **Restart** | `docker compose -p codexify-openconnector restart openconnector`. Provider credentials, named connections, and OAuth state persist in the volume. Upstream's SQLite path auto-migrates on start. **`restart` does not re-read `env_file`**: it reuses the container's existing environment, so a changed secret file — including the deployment guard — is **not** applied, and the container can report healthy while still running the old value. Any change to the secret file therefore requires `up -d --force-recreate`, followed by verification that the running container actually carries the new value (§4.7(a)). |
| **Upgrade** | (1) Take a backup. (2) Move the digest pin to the new upstream release tag. (3) For PostgreSQL only, run the image's explicit `migrate` subcommand with the **same** digest, before starting the server. (4) Recreate the container. (5) Re-run the Gate A qualification suite. Note upstream's runtime-security warning: **pulling a newer image does not update a running container.** |
| **Rollback** | Stop the new container, restore the previous pinned digest, and restore the pre-upgrade volume snapshot if the schema changed. Because upstream applies SQLite migrations at startup, a rollback across a schema-changing release may require the volume snapshot — the rollback procedure must treat "restore the volume" as the default, not the exception. |

### 2.8 Local-only operation versus remote HTTPS OAuth callbacks

These are two materially different deployment postures and must not be
conflated.

**Local-only (the first validation slice).**

- The gateway is reachable only from `codexify_internal`. No host port is
  published.
- OAuth providers are exercised only if the operator registers an OAuth app
  whose redirect URI is `http://localhost:3000/oauth/callback`. A
  browser-driven callback requires the operator to reach that loopback
  address; with no published port this is reachable **only from inside the
  container network**, so a local trial favors `api_key` or `no_auth`
  providers.
- `OOMOL_CONNECT_ORIGIN` is unset or set to the local origin.
- **The first slice deliberately uses a `no_auth` provider** (Hacker News) and
  at most one separately authorized read-only credentialed provider, so the
  trial does not depend on OAuth callback reachability at all.

**Remote users with HTTPS OAuth callbacks (a later, separately authorized posture).**

- Requires a **public HTTPS origin**. Upstream derives `expectedRedirectUri`
  from `OOMOL_CONNECT_ORIGIN`; the provider OAuth app must be registered with
  exactly that URI. Upstream also supports a per-provider `redirectUri` on the
  saved OAuth client configuration, which must be an absolute URI without user
  info or a fragment, and which upstream sends exactly as saved.
- The `/oauth/callback` route must be reachable by the **provider's redirect**
  — that is, from the public internet, not from the private network. This
  **conflicts with §2.3's "no published administrative interface"** posture
  as currently specified, and is therefore **not resolved by this plan**.
- **This is an explicit stopping condition for Gate C.** Before any remote
  OAuth posture is designed, the following must be resolved and separately
  authorized: where the public callback terminates, how its state is signed
  and verified, how the callback result reaches the gateway, and how that
  surface is prevented from becoming a second credential-mutation authority
  outside the Connections control plane.

#### Two candidate designs — neither accepted here

A public OAuth callback is **necessary** for many remote OAuth flows. A
**Guardian-owned** callback handler is **not** necessarily necessary: upstream
already provides `/oauth/callback` and documents that *"the app that owns the
redirect forwards the provider's callback query (`code` and `state`, or
`error`) to it."* That leaves two plausible designs:

| Approach | Architectural consequence |
| --- | --- |
| **A — Expose only OpenConnector's callback path** through a tightly restricted HTTPS reverse proxy | OpenConnector handles the provider callback end to end; Guardian retains responsibility for initiating the flow, binding the resulting credential to a user and connection, and authorizing subsequent use. **No new Guardian application-level handler.** The proxy is the only new surface, and it can be restricted to exactly one path and method. |
| **B — Introduce a Guardian-owned callback handler** that securely forwards the result | More control over Codexify's ingress and over the correlation boundary, but adds another application-level handler, another state store, and a more complicated state-correlation responsibility inside Codexify. |

**Both remain open.** Neither is accepted merely because it is convenient.
Both require proof that a callback can only complete the authorization
**initiated for the intended user and connection**, and neither may expose
administrative routes.

**What upstream already provides for that proof** (verified at the pinned
commit):

- The OAuth `state` is a **server-side, short-lived record** that binds
  `service`, `connectionName`, `retirementGeneration`, the PKCE verifier,
  the requested scopes, and the `redirect_uri` that the authorization request
  carried.
- Completion **consumes the state destructively** — `completeAuthorization`
  calls `states.take(input.state)`, whose store contract is a destructive
  single-use take. A replayed state is therefore rejected as
  `invalid_oauth_state`, and `discardAuthorization` uses the same take to
  ensure a refused authorization cannot later be completed by another
  callback.
- An expired state is rejected on the same path
  (`isExpiredOAuthState` against `stateMaxAgeMs`).

**This is the property the callback design must preserve.** A Guardian-owned
forwarder (§4.7(b) option B) would have to reproduce it correctly across two
systems — and a restricted proxy (§4.7(b) option A) lets upstream's
single-use state store remain the single authority for correlation, with
Guardian's binding work happening **after** the credential lands, through the
normal connection-creation path.

**This is a Gate C design decision, not a Gate A prerequisite.** No ADR
amendment is opened for it now; §4.7(b) records it as an open question.

Until that is resolved, the remote posture remains **unavailable**, and no
claim of remote-provider support may be made.

---

## 3. Guardian Integration

### 3.1 Invariant: the Gateway is a runtime, not a catalog entry

**Decision:** OpenConnector is **not** a new Connections catalog entry.

ADR-071 fixes exactly four canonical catalog categories — `messaging`, `web`,
`inference`, `knowledge` — and defines Connections as a projection seam that
is "never a new execution owner." The gateway is a **generic execution
substrate** that can front providers in any of those categories. Adding it as
a catalog entry would either (a) require a fifth category, which ADR-075
rejects, or (b) mis-file a cross-category runtime inside one category.

**What the catalog does instead.** The gateway's **providers** appear as
ordinary provider entries in the existing catalog, each bound to the gateway
adapter as its `runtime_binding.adapter`, exactly as the Notion and Google
Drive entries are bound to their own adapters. The catalog continues to
describe *providers*; the gateway is an implementation detail of how a given
provider's read actions execute.

This satisfies the requirement to reuse the existing Connections catalog while
preserving ADR-075's taxonomy and ADR-071's "no parallel control plane"
boundary.

### 3.2 What is reused versus what is new

| Concern | Existing owner | Status in this plan |
| --- | --- | --- |
| Catalog vocabulary, states, capabilities | `guardian/protocol_tokens.py` | **Reused unchanged.** No new category, state, auth method, or capability token. |
| Catalog entries and runtime binding | `guardian/connections/catalog.py` | **Reused.** New provider entries only, following the `_notion_knowledge_entry()` / `_google_drive_knowledge_entry()` pattern. |
| Read-only Connections API | `guardian/routes/connections.py` | **Reused unchanged.** It stays read-only and adds no mutation route. |
| Settings Connectors bay | existing `connectors` tab in `SettingsView.tsx` | **Reused unchanged.** No second Settings connector page. |
| Notion / Google Drive execution | `guardian/connections/notion/`, `guardian/connections/google_drive/` | **Untouched.** Their adapters, routes, and behavior are not modified. |
| Agent-invocable operations | `guardian/command_bus/` | **Reused.** Gateway-backed read operations register as Command Bus commands. |
| Provider credential encryption | `guardian/connectors/oauth_crypto.py` | **Reused** for Codexify-side credential custody. See §4.2 for the split. |
| Gateway runtime | — | **New, external, optional.** Isolated service. |

### 3.3 The adapter interface

The adapter is deliberately **small**: two operations, no provider-specific
code, no raw credential access in the return path.

```
guardian/connections/openconnector/
  adapter.py     # OpenConnectorAdapter — discover + execute, nothing else
  service.py     # HTTP transport to the gateway (runtime surface only)
  catalog.py     # no; provider entries live in guardian/connections/catalog.py
  router.py      # provider setup routes (internal_only) + bounded read routes
  credentials.py # Codexify-side binding of a Guardian user to a gateway connection
```

**The interface contract:**

```python
class OpenConnectorAdapter(Protocol):
    async def discover_actions(
        self, *, provider: str, user_id: str
    ) -> list[ActionDescriptor]: ...

    async def execute_action(
        self, *,
        provider: str,
        action_id: str,
        arguments: Mapping[str, Any],
        user_id: str,
    ) -> BoundedActionResult: ...
```

**Rules that bind the interface:**

1. **Discover** calls the gateway's runtime surface only — `GET /v1/actions`,
   `GET /v1/actions?service=<provider>`, `GET /v1/actions/search`,
   `GET /v1/actions/:actionId`, `GET /v1/apps`. It returns **action metadata
   and schemas only** — ids, names, descriptions, required scopes, input
   schemas. It never returns a credential, a token, a client secret, or a
   bearer header.
2. **Execute** calls `POST /v1/actions/:actionId` with the gateway's runtime
   token, selecting the user's connection explicitly (§4.3).
3. **The adapter never calls the gateway's `/api/*` administrative surface in
   any runtime path.** Admin endpoints are unfiltered by construction — upstream
   states `GET /api/connections` and `GET /api/actions/:actionId/agent.md`
   "stay unfiltered" for runtime-token callers. Therefore:
   - The adapter's runtime client is constructed with a **persistent runtime
     token only**.
   - The admin token is used **only** by an operator-driven setup path, never
     by an agent-invocable operation, and never returned to a model.
4. **Results are bounded before they leave the adapter.** Upstream's
   idempotent-response retention means a completed Action response may contain
   sensitive provider data; the adapter must apply a hard cap and a truncation
   marker before the payload reaches a Command Bus result, a model context, or
   a log. The Command Bus already enforces a `MAX_PAYLOAD_BYTES` of
   `262_144`; the adapter's own bound must be no larger and must be enforced
   **before** the Command Bus sees the payload.
5. **The adapter is provider-agnostic.** Provider-specific behavior
   (credentials, OAuth apps, scopes) is provider configuration, not adapter
   code. This is the whole point of the substrate.
6. **The adapter never exposes a raw provider credential** — not in results,
   not in errors, not in exception messages, not in logs. Upstream's runtime
   surfaces already withhold raw tokens; the adapter must not reintroduce them
   through its own error handling. Errors are classified into bounded codes
   (§3.6).

### 3.4 Routing agent invocations through the Command Bus

Every gateway-backed operation that an agent may invoke is exposed as a
**GET-only** route in a provider-specific operations router, mirroring the
Notion pattern (`GET /api/knowledge/notion/search`,
`GET /api/knowledge/notion/read/{object_id}`).

This matters mechanically. `guardian/command_bus/manifest.py:134-137` derives
the command's semantics from the HTTP method:

```python
effect = "read" if method in {"GET", "HEAD"} else "write"
risk = "read_only" if effect == "read" else "mutating"
idempotency = "safe" if effect == "read" else "unsafe"
approval_mode = "none" if effect == "read" else "blocked_phase1"
```

A `POST` route would register as `mutating` / `blocked_phase1` and be gated
behind an approval mode that this plan does not authorize. A `GET` route
registers as `read` / `read_only` / `safe` / `none`, and the Command Bus
derives the command class as `read` in `guardian/command_bus/invoke.py:149-164`.

**Therefore: the adapter's Guardian-facing read routes are GET-only.** The
*gateway-side* call may be `POST /v1/actions/:actionId` — that is an internal
transport detail inside the adapter, not a Guardian route method. The
distinction is deliberate: Guardian's route method determines the Command Bus
semantics; the upstream method determines the gateway protocol.

#### The GET-only rule is a Command Bus concern, not a safety guarantee

**A GET route does not make the underlying action read-only.** The derivation
above is a *classification* mechanism: it tells the Command Bus how to label
and gate a command. It says nothing about what the gateway will actually do
when invoked. A Guardian `GET` route that forwards to an arbitrary
OpenConnector action could trigger a remote write — a GitHub issue
comment, a message send, a file mutation — while the Command Bus confidently
reports `read_only` and `approval_mode: none`.

This is a real hazard specific to a generic action substrate: upstream
actions are **not** uniformly read-only, and upstream's action definitions do
**not** carry a machine-readable read-only marker (the action definition
carries `id`, `name`, `description`, `requiredScopes`, and
`providerPermissions` — but no read/write classification). The provider's
action naming convention is the only signal, and naming is not enforcement.

**Therefore the Gate B adapter contract must include a server-controlled
allowlist of genuinely read-only actions:**

1. The adapter accepts **only** action ids present in a **reviewed,
   server-controlled allowlist** held in Codexify code — not a list derived
   from the gateway's catalog at runtime, and not a list supplied by the
   model, the user, or the request body.
2. Each allowlisted entry must be **individually reviewed** as read-only
   against the provider's semantics — not inferred from a naming pattern,
   not from the action's HTTP verb upstream, and not from the Command Bus
   label.
3. An action id **not** on the allowlist is refused by the adapter with a
   bounded `denied` outcome — **before** any gateway call is made.
4. The allowlist is **explicitly read-only only**. Any action that can
   mutate remote state is excluded by construction, not by convention. A
   future write-capable action requires a separate decision, a separate
   Command Bus posture, and separate authorization — it does not arrive by
   adding a string to a list.
5. The gateway's own deployment-level
   `OOMOL_CONNECT_ALLOWED_ACTIONS` is a **second, independent** constraint,
   and the intersection of the two is what actually bounds execution. Neither
   alone is sufficient.

This requirement lands in **Gate B** and does **not** expand Gate A.

Route posture follows the existing ADR-072 pattern:

- Operations routes → a provider-specific `*_knowledge` route label added to
  `route_posture.enabled` (or `internal_only` during qualification).
- Setup routes → `internal_only`, matching `notion_setup` and
  `google_drive_setup`.
- The legacy `connectors` label stays **quarantined**. Nothing in this plan
  enables it, and the legacy `/api/connectors` route family remains
  quarantined and unused by the gateway runtime.

### 3.5 Catalog projection stays separate from execution

The Connections catalog remains a **static, code-proven projection**:

- `implementation_state` reflects whether a real adapter and route exist. A
  gateway-backed entry is `implemented` only when its adapter, its bounded
  read routes, and its Command Bus command registration all exist in code.
- Per-user setup state is merged at request time by
  `guardian/routes/connections.py` — never stored in the catalog.
- The catalog **never** confers execution authority. ADR-071's authority
  boundary holds: `guardian/connections/` is "catalog and projection
  authority only."
- The catalog **never** performs, proxies, or caches a gateway call.
  Catalog reads and gateway executions are separate code paths with separate
  authorization.

### 3.6 Mapping to existing semantic meanings

The Connections control plane keeps five distinctions apart
(`docs/architecture/connections-control-plane.md`), and the gateway must not
collapse them. Additionally, ADR-024 defines the canonical bounded outcomes
for a connector invocation.

**Availability / setup state** → `ConnectionSetupState`:

| Gateway reality | Projected state | Rule |
| --- | --- | --- |
| No gateway connection bound for this user and provider | `needs_setup` | Credential presence is derivable per user. |
| Binding record saved, not yet validated upstream | `configured` | `configured` never implies `connected`. |
| Gateway reports a validated provider account for the bound connection | `connected` | Only after an explicit successful upstream validation. |
| Gateway unreachable or binding points at a missing connection | `degraded` | Distinct from `error`. |
| Binding exists but upstream rejects the credential | `error` | Bounded error classification only — no raw upstream error text. |

**Authorization** → remains Guardian's, and is **never** inferred from the
gateway. Upstream reports which actions exist and which scopes a credential
carries; that is **catalog and capability metadata**, not authorization.
Whether a given action may execute for a given account is decided by:

- the Guardian permission profile (`guardian/command_bus/permission_profiles.py`),
  where `connector_allowed` and `network_allowed` gate the `connector` command
  class;
- the supported-profile route posture;
- the gateway's own deployment-level action allowlist
  (`OOMOL_CONNECT_ALLOWED_ACTIONS` / `BLOCKED_ACTIONS`).

These are **independent controls**. The gateway's action list is not
authorization, exactly as a catalog entry's visibility is not authorization.

**Health** → a live probe, distinct from both. `configured` and `connected`
say nothing about whether the gateway is currently reachable. Health is
observed at invocation time and reported through the bounded outcome, never
back-projected into setup state.

**Bounded outcomes** → ADR-024's canonical set, mapped from gateway
conditions:

| Gateway condition | ADR-024 outcome |
| --- | --- |
| Action executed, bounded result returned | `success` |
| Guardian policy denied; gateway `403 connection_not_allowed`; action not in the allowlist | `denied` |
| Gateway unreachable; container unhealthy; network failure | `unavailable` |
| No connection bound; provider not connected for this user | `needs_configuration` |
| Upstream action exceeded the bounded budget; gateway reported `execution_cancelled` or the deadline elapsed | `timed_out` |
| Upstream returned an action-level failure (`scope_missing`, `credential_expired`, `provider_error`) | `failed` |

Upstream's bounded error vocabulary maps cleanly onto these: `invalid_input`,
`scope_missing`, `credential_expired`, `insufficient_credit`, `rate_limited`,
`connection_not_allowed`, `unknown_action`, `execution_cancelled`,
`provider_error`, `proxy_not_supported`, `trigger_source_not_supported`.

**A distinction that must not be lost:** upstream states that timeouts, lost
responses, and cancellations **never automatically replay** action or proxy
POSTs, and that a cancelled call may still have completed at the provider.
A `timed_out` outcome therefore means **"the outcome is unknown," not "the
action did not happen."** This is the same orphaned-versus-completed ambiguity
Codexify's own request/attempt state machine must preserve.

### 3.7 Turn-scoped and observable

- **Turn-scoped.** Consistent with ADR-024, a gateway invocation is a
  **turn-scoped** crossing event. It is not consulted automatically on every
  turn; it occurs when the turn explicitly requests it (a Context Command) or
  when Guardian strongly implies the provider's domain. `connected !=
  consulted` and `attached != consulted` remain true for gateway-backed
  providers.
- **Observable after the fact.** Invocation evidence flows through the
  existing Command Bus event surface (`run.created`, `run.started`,
  `run.completed`, `run.failed`, `run.blocked`) and the existing tool-turn
  observability read model in
  `guardian/command_bus/tool_turn_observability.py`. There is **no hidden
  connector invocation**: the gateway call is made *inside* a Command Bus
  command execution, so it inherits the run id, the actor, the subject, and
  the task lineage.
- **Redaction is inherited, and applies.** `guardian/command_bus/redaction_policy.py`
  already redacts `authorization`, `cookie`, `token`, `secret`, `password`,
  `api_key`, and `x-api-key` keys in arguments and enforces explicit path
  rules for `headers.authorization`, `headers.cookie`, `headers.x-api-key`,
  `query.api_key`, and `query.token`. The adapter must not introduce a
  credential-bearing argument key outside that policy — in particular, the
  gateway runtime token must be injected as an **HTTP header by the transport
  layer**, never as an argument value.
- **Provenance is preserved.** A result returned from a gateway action is
  external evidence with external provenance (provider, action id, connection
  identity, retrieved-at). Consistent with ADR-075, it does **not** silently
  become a Codexify memory, document, embedding, or identity record. Any
  future persistence path must retain that source provenance.

### 3.8 No duplication of existing connectors

- The Notion and Google Drive knowledge paths remain **exactly as they are**.
  Their adapters, routes, catalog entries, credentials, and Command Bus
  commands are not modified. If OpenConnector happens to front a provider
  Codexify already implements natively, the **native adapter keeps precedence**
  and the gateway-backed entry is not created for that provider. Adding a
  gateway-backed duplicate of Notion or Drive is **out of bounds**.
- The legacy `/api/connectors` sync-connector subsystem stays quarantined and
  unused by the gateway runtime (ADR-075: "The legacy `/api/connectors`
  subsystem is not the Knowledge runtime.").

---

## 4. Credential Authority and Tenant Isolation

### 4.1 The six authorities and their owners

| Authority | Owner | Where it lives | Codexify's rule |
| --- | --- | --- | --- |
| **Guardian account identity** | Guardian | `guardian/core/dependencies.py` (`get_account_user_id`, `require_account_session`) | Resolved server-side from the authenticated session. **Never** a request body field, never a model-supplied value. |
| **Guardian authorization policy** | Guardian | `guardian/command_bus/permission_profiles.py`, `guardian/connectors/external_transport_policy.py`, supported-profile route posture | Decides whether a command may execute. Never delegated to the gateway. |
| **OpenConnector connection identity** | The gateway | A stable **opaque** connection id returned by the gateway's connection APIs; plus a `connectionName` alias | A reference, not a capability. Resolved from a Codexify-side binding record, never from model input. |
| **OpenConnector credential storage** | The gateway | The gateway's own database (`/app/data`), AES-256-GCM under `OOMOL_CONNECT_ENCRYPTION_KEY` | Encrypted at rest. The key is held by the operator's secret store, **not** in the volume. Codexify never reads the gateway's credential table. |
| **Scoped runtime tokens** | The gateway | Persistent `oct_...` tokens; **only hashes** are stored upstream | One per Codexify account (or per user-account binding set), carrying an explicit `allowedConnections` allowlist. Held server-side, encrypted with Codexify's existing primitive. |
| **Revocation and provider disconnect** | Split, deliberately | Guardian revokes its side; the gateway revokes its side; the provider revokes the grant | See §4.5. All three are required; none alone is sufficient. |

### 4.2 Credential custody: a deliberate split

Codexify already owns provider credential custody for its native providers
(`guardian/connectors/oauth_crypto.py`, used by
`guardian/connections/notion/credentials.py`). For gateway-backed providers,
custody splits deliberately:

- **The gateway holds the provider credential.** It is the only component that
  ever sees a provider token. This is upstream's runtime boundary and it is
  what makes the substrate valuable.
- **Codexify holds the *binding*, not the credential.** Codexify stores the
  mapping from a Guardian user to a gateway connection id/alias, the provider
  service name, and the Codexify-side encryption of the **gateway runtime
  token** used to reach that connection. It never stores the provider token.
- **Codexify's existing `oauth_crypto` primitive protects the Codexify-side
  runtime token** — the same Fernet-based server-side secret primitive used
  for Notion and MiniMax OAuth material. The provider credential's own
  protection remains upstream's AES-256-GCM under
  `OOMOL_CONNECT_ENCRYPTION_KEY`.
- **This is delegated custody, not a second credential authority.** The gateway
  holds provider credential material and executes provider actions; it grants
  no Codexify account authority, and it cannot widen one. Guardian remains the
  sole account-authorization authority, and exactly one Guardian-owned binding
  authorizes every custodian-backed execution. See §4.7(a) — resolved by the
  ADR-071 and ADR-094 amendments accepted 2026-11-02.

### 4.3 The explicit user-to-connection binding

**Requirement: every gateway execution must be bound to an explicit
Guardian-user-to-gateway-connection mapping.**

Proposed Codexify-side binding record (a **future** schema change — this task
performs no database migration):

| Field | Meaning |
| --- | --- |
| `user_id` | The Guardian account id. The binding is **per user**. |
| `provider` | The gateway service name (e.g. `github`). |
| `connection_id` | The gateway's **stable opaque connection id**. |
| `connection_alias` | The gateway `connectionName` used for selection. |
| `provider_account_label` | The gateway's safe account label (`displayName`, `accountId`, `grantedScopes`). Safe metadata — **not** a token. |
| `runtime_token_ref` | Reference to the Codexify-encrypted persistent runtime token. Never the token itself in plaintext. |
| `status` | Bound / validating / error. |
| `bound_at`, `last_validated_at` | Timestamps. |

**Selection mechanics.** The adapter resolves the binding **from the
authenticated user** and selects the gateway connection explicitly — never by
omitting the selector. Upstream semantics are strict here: omitting
`connectionName` selects the provider's **default** connection, whose id
must also be granted on the token, and a request naming an ungranted
connection fails with `403 connection_not_allowed` **before** credential
lookup, so connection existence is not leaked.

**Measured selector and envelope facts** (Gate A, at the pinned digest). These
are the request shapes that actually work, and they correct assumptions that
would otherwise produce a silently denied call:

| Fact | Consequence for the adapter |
| --- | --- |
| The action request envelope is `{ "input": { ... }, "connectionName": "..." }` — action arguments go **under an `input` wrapper**, not at the top level. | A flat body is rejected as `invalid_input`. The adapter nests arguments under `input`. |
| Selection works through the `x-oo-connector-app-id` header (the admin-API **UUID**), the `x-oo-connector-alias` header, or the body field `connectionName`. | These are the only selectors to use. The binding record must therefore carry the admin-API UUID, not only the alias. |
| A `connectionId` field in the request body is **not wired for selection**. | It is silently denied as `connection_not_allowed`. The adapter must never send it, and must not read that denial as proof that the connection is ungranted. |
| `allowedConnections` grants are expressed with the **admin-API UUID**, not `service:name`. | A grant written in `service:name` form grants nothing, which is indistinguishable at the call site from an ungranted connection. The binding and the grant must agree on the id form. |

**Per-user token scoping.** Each Codexify user's runtime path uses a
persistent runtime token whose `allowedConnections` contains **only** that
user's bound connection ids, plus `allowedActions` restricted to the
allowlisted action ids and `allowedProxies: []`. Upstream states that a
non-empty `allowedConnections` list is an **exact allowlist of stable, opaque
ids**, that token grants **intersect with** deployment policy and cannot widen
it, and that denied connections fail with `403 connection_not_allowed` before
credential lookup.

**The grant list must be non-empty.** Upstream's `evaluateConnection` returns
`allowed: true` when the token's `allowedConnections` list is **empty**, and
upstream documents an omitted or empty list as *unrestricted connection
access*. An empty grant is therefore **not** a deny-all — it is the
opposite. The same permissive-empty convention applies to `allowedActions`: a
policy layer with no allow rules contributes no constraint. Consequently:

- every Codexify-issued runtime token carries an **explicit, non-empty**
  `allowedConnections` list containing exactly that user's connection ids;
- the deployment-level `OOMOL_CONNECT_ALLOWED_ACTIONS` is always **non-empty**,
  because it is the only constraint on action scope when a token's own action
  list is empty;
- an empty or omitted grant is treated as a **defect**, not a permissive
  default, and is a named Gate A and Gate D stopping condition (§5.1.1,
  §6).

**Bootstrap tokens and JWTs are not used for per-user execution.** Upstream is
explicit that bootstrap runtime tokens and JWTs have **no stored connection
grant** and "remain unrestricted." Using either for a multi-user Codexify
path would silently grant every user access to every stored connection. The
topology in §2.2 therefore configures `OOMOL_CONNECT_RUNTIME_TOKEN` as the
**deployment guard** — required, service-owned, never presented for execution,
and used only to make the runtime surface fail closed by configuration (§2.4,
§4.7(a)) — while the §2.4 bootstrap sequence shows how ordinary execution is
authenticated with **scoped persistent tokens**. The guard and the bootstrap
sequence answer different questions: the guard is what makes an empty token
store safe, and the scoped persistent tokens are what ordinary execution
actually presents.

### 4.4 Explicit prohibitions

The following are forbidden by design, and each has a named enforcement
point:

| Forbidden | Enforcement point |
| --- | --- |
| **Cross-account connection discovery** | A user's runtime token grants only that user's connection ids. Upstream filters runtime discovery (`GET /v1/apps`) to granted credential connections, and denies ungranted selections with `403 connection_not_allowed` before lookup. The adapter never calls the **unfiltered** admin `GET /api/connections`. |
| **Shared unscoped default connection execution** | The adapter always selects an explicit bound connection and never omits the selector. The per-user token's `allowedConnections` omits any shared default connection id. |
| **Model-supplied account identifiers as authority** | The binding is resolved from the authenticated Guardian session. A model-supplied `user_id`, `account_id`, `connection_id`, or alias is **never** used to select authority; at most it is ignored, and any attempt is a bounded `denied`. |
| **Direct model access to the gateway admin API** | The runtime client holds a persistent runtime token only. The admin token is used solely by an operator-driven setup path, is never placed in a model-visible argument, a result, or a log, and the adapter never calls `/api/*` from an agent-invocable path. |
| **Credential exposure through logs or UI projections** | Provider tokens never enter Codexify at all. The gateway runtime token is injected as an HTTP header by the transport layer, never as an argument. `redaction_policy.py` covers `authorization`/`token`/`secret`/`api_key` keys and the explicit header/query paths. The Connections projection exposes only safe metadata — provider, status, scopes, expiry, last-refresh, sanitized error classification — never a token, prefix, suffix, hash, or raw upstream error. |

### 4.5 Revocation and provider disconnect

Three distinct actions, all required, none sufficient alone:

1. **Guardian-side revocation.** The binding record is removed or marked
   revoked, and the Codexify-encrypted runtime token reference is deleted.
   Guardian then refuses to resolve a connection for that user. Subsequent
   invocations fail closed with a bounded `denied` or
   `needs_configuration` outcome — never a silent fallback to another
   connection.
2. **Gateway-side revocation.** The persistent runtime token is deleted
   upstream, and the provider connection is removed via the gateway's
   connection API. Because the token's `allowedConnections` was the grant
   mechanism, deleting the token removes the capability even if the
   connection record survives.
3. **Provider-side disconnect.** The user revokes the grant in the provider's
   own authorization settings. **Measured (Gate A):** a provider-side credential
   failure does **not** arrive as a clean `credential_expired` or `scope_missing`
   classification — it arrives as `invalid_input` carrying the provider's own
   error text, verbatim. The adapter must therefore classify `invalid_input` as
   a bounded credential-or-input failure and must sanitize the provider text
   before it reaches a result, a log, or a user-visible surface. This step is
   distinct precisely because it is only visible here: neither Guardian's
   revocation nor the custodian's token deletion observes it.

**Ordering:** Guardian revokes its binding first (fast fail-closed), then
deletes the upstream token and connection, then the user handles the provider.
**Restored references must not revive revoked authority** — consistent with
ADR-094, restoring a backup must not resurrect a revoked binding.

**In-flight execution is stated, not assumed.** Once Guardian has dispatched and
the custodian has accepted the call, a Guardian-side revocation does **not**
retroactively unwind work already in progress at the provider. The honest
disposition for such a call is an **unknown outcome** — recorded as unknown, not
as success and not as "did not happen". The same ambiguity applies to a timeout,
a lost response, and a cancellation, and a cancelled call may still have
completed at the provider. A retry is a **new attempt** under the current
authorization state, never a continuation of a revoked one, and a custodian
failure or uncertain authority fails **closed**.

### 4.6 Turn-scoped use

Consistent with §3.7 and ADR-024: gateway use is a turn-scoped crossing event.
A bound connection is *connected*; it is not *consulted* every turn. Discovery
results are cached only for the turn unless a future governed feature pins
them longer. The gateway's action catalog is not a standing instruction set.

### 4.7 Authority decisions requiring an ADR amendment

Three points in this plan exceed current accepted ADR text. **Each must be
explicitly resolved before implementation.** **(a)** is now **resolved** — the
amendment was accepted on 2026-11-02. **(b)** and **(c)** remain open, and that
amendment does not address them.

**(a) Delegated credential-vault authority — ADR amendment required.**

ADR-094 is precise about credential custody: "Secret custody stays in a
server-controlled, owner-scoped credential facility appropriate to the
credential or entitlement type," and an execution binding "may carry an
opaque, non-bearing credential or entitlement reference." That language
*admits* a delegated custodian, but it does not authorize one that is a
**separate service with its own administrative interface, its own credential
database, and its own bearer-token vocabulary**.

Concretely, ADR-094 does not currently cover:

- a **second credential store** (the gateway's encrypted database) that
  persists **outside** Guardian's Postgres and outside Guardian's
  backup/export/restore path;
- a **Guardian-held bearer token** (the persistent `oct_...` token) whose
  loss or leak is a cross-tenant capability;
- the **revocation semantics** of a credential held by a delegated custodian,
  and the requirement that a restored Guardian backup must not revive a
  revoked upstream binding.

**This is the principal ADR question.** It is most likely an amendment to
ADR-094 (credential authority) and ADR-071 (server-side persistence as sole
credential authority — which currently reads as a Guardian-exclusive
commitment), and it interacts with ADR-092's principal lanes because a
runtime token minted for one account must never serve another.

**Status: accepted 2026-11-02.** The amendment was accepted as an *amendment section
inside* ADR-094 and ADR-071 — not as a new ADR, and not as a change to either ADR's
original accepted status, number, or text. Both carry an explicit acceptance record.
The decision is:

- The custodian is admitted as a **subordinate, external credential custodian**
  and execution substrate. It holds provider credential material and serves
  provider actions. It has **no independent Codexify account authorization
  authority**.
- **One canonical Guardian-owned binding** governs every custodian-backed
  execution: the account-scoped record naming the account, the custodian, the
  provider, the custodian-side connection identity, and the credential
  reference. The custodian's own records are **delegated custody**, never a
  grant of Codexify account access. Possession of a custodian credential is
  never evidence of account authority.
- **Canonical ownership is preserved across scopes.** Discovery, provider
  setup, credential existence, and credential validation each confer **no**
  execution authority.
- **Ordinary execution uses explicitly scoped persistent tokens only.** The
  deployment guard remains deployment infrastructure and never enters the
  adapter, a model context, a queue, a command, or a user-visible API. The
  four accepted conditions of the guard are preserved unchanged.
- **Revocation is ordered and complete.** Guardian authorizes every invocation
  and revalidates at execution time; Guardian denial prevents subsequent
  dispatch and retries; custodian-side token and connection revocation follows
  Guardian denial; provider disconnect is a distinct third step; in-flight
  semantics are stated as an unknown outcome rather than assumed; and
  custodian failures and uncertain authority fail closed.
- **Recovery is specified.** A restored Guardian state must not revive a
  revoked binding; a custodian binding that is unknown to Guardian or
  inconsistent with Guardian's record stays unusable pending reconciliation or
  explicit reauthorization; a custodian-side cleanup failure cannot restore
  Guardian authority; and account deletion has an observable cleanup outcome.
- **Guard rotation is fail-closed and specified** — access shutdown/drain,
  configuration replacement, container recreation, running-container
  verification, anonymous-request rejection, and controlled reopening. **No
  zero-downtime rotation is claimed.**
- **The first authorized implementation class is internal-only**: reviewed
  read-only actions, explicit Guardian permission checks, scoped connection
  selection, sanitized provider outcomes, and no general write access.

**This amendment does not** authorize a deployment, an adapter, a migration, a
route, a UI surface, an OAuth callback, or a release-posture change; it does
not resolve the §4.7(b) callback question or the §4.7(c) catalog-identity
question; and it does not make OpenConnector adopted. **Acceptance was explicit
and human, on 2026-11-02.** It discharges the delegated-custody architecture
prerequisite; Gate B implementation remains a separate bounded task under the
accepted amendments, the runtime proof those amendments require is still
outstanding, and the Gate C and Gate D gates remain separately gated.

**(b) The public OAuth callback surface — ADR or architecture review required.**

As established in §2.8, a remote OAuth posture requires a **public HTTPS
callback endpoint** that terminates outside the private network. ADR-075
defines the provider-specific setup and credential seam as provider-specific
and server-owned; a shared public callback endpoint is a **new Guardian
route** and a **new authority surface**. This must be resolved by a future
architecture review before any remote-provider claim.

**Refinement after upstream review:** the callback endpoint itself need not be
Guardian-owned. Upstream provides `/oauth/callback` and documents the
forwarding contract ("the app that owns the redirect forwards the provider's
callback query to it"), and its `state` store already provides the
correlation property the design must preserve — a short-lived, service- and
`connectionName`-bound record that is **consumed destructively and
single-use** on completion, with expiry enforced. §2.8 sets out the two
candidate designs — a **restricted reverse proxy** in front of upstream's own
callback (option A) versus a **Guardian-owned forwarding handler** (option B)
— and neither is accepted yet.

**The open question is therefore narrower than "where does the callback
live":** it is *which component owns the correlation authority*. Option A
keeps upstream's single-use state store as the sole authority and confines
the new surface to a proxy; option B requires Codexify to reproduce
single-use, expiry-bound correlation across two systems. Both designs must
prove that a callback can only complete the authorization initiated for the
intended user and connection, and neither may expose administrative routes.

**No ADR amendment is opened for this question now.** It remains a Gate C
design decision, and it does not block Gate A.

**(c) Catalog identity for gateway-backed providers — ADR-075 confirmation
required.**

§3.1 keeps OpenConnector itself out of the catalog and admits only
**provider** entries. ADR-075's "Catalog identity rule" requires that
"separate provider products or modes may have distinct entries only when
their authority or runtime domains are materially different." A gateway-backed
GitHub entry and a natively-implemented GitHub entry would share a provider
but differ in authority and runtime domain — the exact situation the rule
governs. The plan's rule (native precedence, no duplicates) must be
confirmed, and if ADR-075's category taxonomy is judged insufficient for
gateway-backed providers, an **ADR-075 amendment** is required.

---

## 5. First Validation Slice

### 5.1 Scope

An **isolated, read-only** trial, executable independently of any Codexify
runtime change. It validates the *gateway*, not the Guardian integration.

| Property | Value |
| --- | --- |
| Build | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c` |
| Topology | The standalone project from §2.2, with `codexify_internal` network |
| Primary action | `hackernews.get_top_stories` — a **no-auth** provider; no credential, no OAuth, no provider account |
| Secondary action | One separately authorized **read-only** provider action, executed only after the no-auth action passes |
| Allowlist | `OOMOL_CONNECT_ALLOWED_ACTIONS` set to exactly the trial action ids; `OOMOL_CONNECT_BLOCKED_PROXIES="*"` |
| Payload bound | Hard cap on the returned payload, applied by the harness; the trial asserts the cap is respected |
| Codexify credentials | **None.** The trial uses no Codexify production credential, no Codexify account, and no Codexify database row. |
| Authentication | Admin token for setup only. Runtime calls use **purpose-scoped persistent `oct_...` tokens** whose `allowedConnections` and `allowedActions` are **non-empty and explicit** — see the token lifecycle in §5.1.1. |

#### 5.1.1 Persistent runtime token lifecycle (mandatory)

**An empty `allowedConnections` list is not a deny-all — it is
unrestricted access.** Upstream's `evaluateConnection` returns
`{ allowed: true }` when the token's grant list is empty, and upstream
documents an omitted or empty `allowedConnections` as *unrestricted
connection access* (verified in upstream `src/core/action-policy.ts` at the
pinned commit). The same permissive-empty convention applies to
`allowedActions`: a layer with no allow rules contributes no constraint, so
the **deployment-level** `OOMOL_CONNECT_ALLOWED_ACTIONS` is the only thing
constraining an action when the token's own list is empty.

##### The standing invariant

> **The persistent-token store must never be empty while the gateway is
> running with credentials stored, and must never be empty between any two
> token lifecycle operations.**

This is not a stylistic rule. Upstream's runtime-auth decision is
**re-evaluated on every request** against the **live** token store:

```ts
// src/server/connect-app.ts
const hasStoredRuntimeTokens = async (): Promise<boolean> =>
  (await runtimeTokens.listTokens()).length > 0;
```

and in `src/server/api/auth.ts`:

```ts
async function hasValidToken(context: Context, options: LocalAuthOptions, scope: AuthScope): Promise<boolean> {
  const token = tokenForScope(options, scope);
  if (!token) {
    if (scope === "admin") return true;
    const hasRuntimeTokens = options.hasRuntimeTokens
      ? await options.hasRuntimeTokens()      // <-- live store query, per request
      : options.resolveRuntimeToken !== undefined;
    if (!options.requireRuntimeAuth && !hasRuntimeTokens && !options.verifyRuntimeJwt) {
      return true;                              // <-- PERMISSIVE: unauthenticated allowed
    }
    return hasValidRuntimeToken(context, options);
  }
  ...
}
```

With no environment bootstrap token, no `requireRuntimeAuth`, and no JWT
verifier, **an empty token store means the runtime API is unauthenticated** —
and `revoke` deletes the row outright (`delete from runtime_tokens where id
= $1`), so revoking the *last* token reopens the window that the first token
closed.

This also means the protection is **not** a startup-time property. It is
re-derived per request, which is precisely why it can silently disappear
mid-run. The consequence for the plan is that "we created a token at
bootstrap" is **not** sufficient evidence; the store must be **observed
non-empty** at every point where authentication is supposed to hold.

##### Overlapping-token handoff (no zero-token window)

The P0-to-P1 transition must **overlap**, never gap. The successor is created
and **proven valid** *before* the predecessor is revoked:

| Step | Action | Store state | Authentication state |
| --- | --- | --- | --- |
| **1** | Create successor token `S` with its full, explicit, non-empty grant. | `{P0, S}` — **non-empty** | **Enforced** |
| **2** | **Verify `S` works**: an action authorized only by `S`'s grant succeeds, and `S` cannot reach any connection `S` was not granted. | `{P0, S}` | **Enforced** |
| **3** | Revoke predecessor `P0`. | `{S}` — **non-empty** | **Enforced** |
| **4** | **Verify the store is still non-empty** and unauthenticated `/v1` is **still rejected**. | `{S}` | **Enforced** |

The store is non-empty at **every** step. There is no moment at which the
gateway has zero tokens.

**A grant may reference a connection id that does not exist yet.** Upstream's
token-creation input validation (`readConnectionIds` in
`src/server/api/policy-input.ts`) checks only that each id is a non-empty
string within size limits — it does **not** verify that the connection
exists. A successor token can therefore be created with the **future**
connection id **before** that connection is created, which is what makes a
genuinely gapless handoff possible: the successor is scoped to a connection
that does not exist yet, and starts working the moment that connection
appears. Upstream separately documents that *"updates must send
`allowedConnections` so a PUT cannot drop an existing restriction"* — the same
rule applies to creation.

##### Token inventory

| Token | `allowedConnections` | `allowedActions` | Purpose |
| --- | --- | --- | --- |
| **`trial-bootstrap` (P0)** | the `no_auth` connection id for the trial provider (see the `no_auth` note below) | the exact trial action id(s) | Executes the no-auth trial actions. **Revoked via overlapping handoff**, never as the first step of creating a credential. |
| **`trial-credentialed` (P1)** | the id of the credential-bearing connection — **may be created before that connection exists** | the exact read-only action id(s) | Executes the credentialed provider action. |
| **`trial-user-a`, `trial-user-b` (P2)** | each user's **own** connection id, and **never** the other's | each user's own read-only action id(s) | The two-account isolation proof. |
| **`trial-sentinel`** | a **non-existent** connection id (a reserved placeholder) | a **non-existent** action id | **Never used to execute anything.** Exists solely so the store is never empty. |

##### The sentinel token

Because the invariant must survive *account deletion*, *token rotation*, and
*restart* — not just the initial bootstrap — the plan keeps a **dedicated
sentinel token** in the store at all times.

- Its grant names a **connection id that does not exist** and an **action id
  that does not exist**, so it can **never** authorize a real operation even
  if it were presented to the runtime.
- It is **never** used as a credential by any caller.
- It exists for exactly one reason: to keep `hasStoredRuntimeTokens()` true,
  so the runtime API never falls back to the permissive branch.
- It is **not** a substitute for the other grants — it grants nothing. Its
  only function is to keep the store non-empty.

**The invariant holds even if every user token is deleted**, because the
sentinel remains. Without it, deleting the last user token — for example
during account deletion — would silently turn runtime authentication off
while stored credentials remained.

**Deleting the sentinel is therefore a deliberate, privileged act** that
must be the **last** token operation, performed only when no credential
exists, and immediately followed by a verification that the gateway is
stopped or that authentication is otherwise re-established.

##### The `no_auth` grant exemption

Upstream's `resolveExecutionTarget`
(`src/execution-target.ts`) skips the connection-grant evaluation entirely
for a `no_auth` connection:

```ts
const authorize = (summary: ConnectionSummary | undefined): void => {
  if (input.operation !== "trigger" && summary?.authType === "no_auth") return;
  const decision = input.policy?.evaluateConnection(summary?.id);
  if (decision && !decision.allowed) throw new ExecutionPolicyError(decision);
};
```

Upstream documents this as *"Virtual `no_auth` connections do not require a
grant."* Two consequences follow, and both matter for how Gate A's evidence
is interpreted:

1. **A `no_auth` action cannot be used to demonstrate connection-grant
   isolation.** If a `no_auth` action succeeds under *any* token, including
   one whose grant list is non-empty and does not include that connection,
   that is **expected upstream behavior, not a grant-control failure**. The
   isolation rows in §5.3 (Group 2) must therefore be exercised against
   **credential-bearing** connections, where the grant is actually evaluated.
   Group 2 is sequenced after Group 3 for this reason.
2. **The P0 token's `allowedConnections` value does not gate `no_auth`
   actions.** The P0 token's real restriction is its `allowedActions` grant
   plus the deployment-level `OOMOL_CONNECT_ALLOWED_ACTIONS`. The plan
   therefore still lists a non-empty `allowedConnections` for P0 — it is
   correct hygiene and it matters the moment any credentialed connection
   exists — but the *enforcement* observed during the P0 phase comes from the
   action allowlist, not the connection grant.

##### Hard rules

- **The store is never empty.** At no point — not during bootstrap, not
  during a handoff, not during account deletion, not during rotation, not
  between a restart and its first health check — may the persistent-token
  store contain zero tokens while the gateway is running.
- **Every handoff overlaps.** Create successor → verify successor → revoke
  predecessor → verify store non-empty and unauthenticated `/v1` still
  rejected. Never revoke first.
- **The sentinel token is present from the first token creation onward**,
  and is revoked only as the final token operation (§5.1.1's "Deleting the
  sentinel").
- **The unrestricted-grant token must not survive into the credentialed or
  two-account phases**, and its revocation happens **through the overlapping
  handoff**, not as a standalone step.
- **`allowedConnections` is never left empty or omitted on any token that
  exists while a credential-bearing connection is present.** An empty list at
  that moment is a cross-tenant capability.
- **Token updates must carry the full grant.** Upstream's token-update path
  replaces the stored policy wholesale. A `PUT /api/runtime-tokens/:id` that
  omits `allowedConnections` would therefore **drop an existing restriction**
  and silently convert a scoped token into an unrestricted one. Any Codexify
  token-lifecycle code that updates a token must send the complete grant set
  every time, and the change must be verified by re-reading the token's
  recorded policy.
- **No shared default connection.** Every execution names an explicit
  connection or alias; `default` is never relied upon.
- **The deployment-level allowlist is not a substitute for the token grant.**
  `OOMOL_CONNECT_ALLOWED_ACTIONS` limits *which actions* can run; the token's
  `allowedConnections` limits *whose credential* can run them. Both are
  required, and they are independent controls (§3.6).
- **A `no_auth` action still executes against the live upstream API.**
  "No-auth" describes the *authentication* requirement of the provider
  endpoint, not the absence of an external call. See §5.4.

### 5.2 Why `no_auth` first

The Hacker News action requires no provider credential, no OAuth
registration, no redirect URI, and no provider account. It therefore isolates
**gateway health, action discovery, action execution, response shaping,
idempotency, and error classification** from every credential and OAuth
variable. A failure at this stage is unambiguously a gateway problem.

### 5.3 Test matrix

Each row states its **observable evidence**. Rows are grouped by evidence type,
because the distinction matters (§5.4).

**Group 0 — authentication and the never-empty-store invariant.** This group
runs **first**, before any credential exists, and is **re-run at every token
lifecycle transition**. It is deliberately separate from Group 4: the
bootstrap assertion must be observable **before** credentials are introduced,
not after.

| # | Test | Observable evidence |
| --- | --- | --- |
| 0a | **Unauthenticated runtime rejected after bootstrap** | Immediately after the sentinel token is created (§2.4 step 2), a `/v1` request with **no** bearer token is rejected (`401`/`403`). **This proves the bootstrap window is closed** and is the single most important observation in Gate A. |
| 0b | **Store is non-empty** | `GET /api/runtime-tokens` (admin surface) lists at least one token. Evidence: the listed token ids. This is the direct check of the §5.1.1 invariant — the runtime's auth decision is a live per-request query of this store, so an empty store means an unauthenticated runtime API. |
| 0c | **Invalid/absent token rejected** | A `/v1` request with a syntactically invalid bearer token, and one with no bearer token at all, are both rejected. Evidence: gateway auth rejection. |
| 0d | **Sentinel authorizes nothing** | The sentinel token, presented to `/v1`, cannot execute any action and cannot select any connection. Evidence: a bounded denial. Its grant names a non-existent connection and action id, so it must grant nothing. |
| 0e | **Trigger denial** | A Trigger execution attempt is refused (`trigger_blocked`), proving `OOMOL_CONNECT_BLOCKED_TRIGGERS="*"` is effective. Triggers are an **independent** execution policy from Actions and Proxies, so blocking proxies does not block them; this row is what proves the separate surface is closed. |
| 0f | **Post-handoff re-assertion** | After **every** token handoff (successor created → verified → predecessor revoked), rows 0a–0c are **re-run** and still pass: unauthenticated `/v1` is still rejected, the store is still non-empty, and invalid tokens are still rejected. Evidence: the repeated rejection statuses and the token list at each transition. |
| 0g | **Post-restart re-assertion** | After a container restart, rows 0a–0c are re-run and still pass — the store persisted, so the runtime API did not become unauthenticated during the restart. Evidence: the repeated results and the persisted token list. |
| 0h | **Post-deletion re-assertion** | After deleting the **last user token** (simulating account deletion), the sentinel remains, the store is still non-empty, and unauthenticated `/v1` is **still rejected**. Evidence: the token list still containing the sentinel, and the rejection status. This is the row that proves the invariant survives account deletion. |

**Group 1 — gateway-internal behavior (no external provider call).** These
tests exercise the gateway's own logic. They make **no call to any external
provider API**, and their evidence is produced entirely by the gateway
itself.

| # | Test | Observable evidence |
| --- | --- | --- |
| 1 | **Action discovery** | `GET /v1/actions?service=hackernews` returns the trial action id and its input schema; the returned schema matches the action's actual accepted input. *Catalog metadata only — no provider call.* |
| 3 | **Denied action** | An action **outside** `OOMOL_CONNECT_ALLOWED_ACTIONS` is refused. Evidence: the gateway's own denial (not a Guardian denial) with the upstream error code. |
| 4 | **Proxy denial** | `POST /v1/proxy/:service` is refused, proving `OOMOL_CONNECT_BLOCKED_PROXIES="*"` is effective and the raw provider-API escape hatch is closed. |
| 6 | **Gateway unavailability** | The container is stopped; a client call fails as a transport error. Evidence: bounded `unavailable` classification, **not** an action-level `failed`. |
| 10 | **Audit redaction and source provenance** | The harness's own log of the exchange contains **no** credential material, no bearer token, and no admin token. Evidence: a scan of the captured logs for the secret values returns zero matches. |
| 11 | **Runtime baseline** | `docker exec codexify-openconnector node --version` reports a version meeting upstream's CVE-2026-111497 baseline (Node `22.23.4+` / `24.22.1+` / `26.12.1+`, or Bun `1.4.4+`). |

**Group 1b — unauthenticated live provider call (external network, no credential).**
These tests **do** reach an external provider API. The provider requires no
credential, but the call is genuinely external and the response is genuinely
live. They must not be reported as local-only executor tests.

| # | Test | Observable evidence |
| --- | --- | --- |
| 2 | **Successful execution (live, unauthenticated)** | `POST /v1/actions/hackernews.get_top_stories` with the P0 runtime token returns `success` with a bounded payload. Evidence: the response envelope shape, the observed payload size, and **the live upstream Hacker News response itself**. This is an external API call — the response content should be recognizable as live HN data, and the recorded evidence must say so. |

**Group 2 — tenant isolation (requires two synthetic accounts).** These are
gateway-internal denials. No provider call is made in any of them, which is
itself part of the evidence. **These rows must use credential-bearing
connections**, because upstream exempts `no_auth` connections from the
connection-grant evaluation entirely (§5.1.1) — a `no_auth` action succeeding
under a foreign token would be expected upstream behavior and proves nothing
about grant isolation.

| # | Test | Observable evidence |
| --- | --- | --- |
| 13 | **Two-user isolation** | Two synthetic users each hold a distinct **credential-bearing** connection and a distinct persistent runtime token. User A's token cannot execute against User B's connection: `403 connection_not_allowed`, raised **before** credential lookup. Evidence: the denial, plus the observation that no provider call was made. |
| 14 | **Wrong-account access** | A token scoped to User A that explicitly names User B's connection id is denied with `connection_not_allowed`. Evidence: the denial code and the absence of a provider call. |
| 15 | **Wrong-connection access** | An unknown or ungranted connection id is denied; upstream's "an unknown selector never falls back to another connection" property is observed. Evidence: denial, not silent fallback to the default connection. |
| 16 | **Shared default connection** | A request that **omits** the connection selector on a deployment that has a shared default connection is denied, proving the shared unscoped default is not reachable. Evidence: `connection_not_allowed`. |
| 16a | **`no_auth` grant exemption observed** | A `no_auth` action executed under a token whose `allowedConnections` does not include that connection **succeeds** — confirming the documented exemption. Evidence: the success, recorded as **expected upstream behavior**. This row exists so the observation is not later misread as a grant-control failure. |

**Group 3 — credentialed provider calls and persistence (real provider API,
separately authorized).**

| # | Test | Observable evidence |
| --- | --- | --- |
| 17 | **Provider authentication failure** | A credentialed provider action with a deliberately invalid credential fails with a bounded `credential_expired` / `scope_missing` classification. Evidence: the classification and the absence of raw upstream error text in any log or projection. |
| 18 | **Real provider read** | The separately authorized read-only provider action succeeds against the **real** provider API and returns real provider content. Evidence: the live upstream response, recorded separately from Groups 1 and 1b. |

**Group 4 — lifecycle, encryption, and idempotency.** These require the
credentialed connection from Group 3 and therefore run last. **The
authentication rows (formerly 5a/5b) live in Group 0**, because the
bootstrap rejection must be observed *before* credentials exist — placing it
here would make it unobservable at the moment it matters.

| # | Test | Observable evidence |
| --- | --- | --- |
| 5 | **Overlapping handoff, no zero-token gap** | The P0→P1 handoff is executed as: create successor with its full explicit grant → **verify the successor works** → revoke the predecessor → **re-run Group 0 rows 0a–0c**. Evidence: at no point in the sequence does `GET /api/runtime-tokens` return an empty list, and unauthenticated `/v1` is rejected at every step. The predecessor's revocation is confirmed by a rejected follow-up call with the revoked token. |
| 7 | **Restart and persistence** | The container is restarted; a previously created named connection and its credential are still present and still usable. Evidence: the connection id is unchanged and the action still succeeds. **Group 0 rows 0a–0c are re-run after the restart** (see row 0g). |
| 8 | **Credential encryption and recovery** | With `OOMOL_CONNECT_ENCRYPTION_KEY` set, the stored credential record on disk is **not** plaintext. Evidence: the raw secret string does not appear in the database file. Then: with the same key and a restored volume, the credential still decrypts and the action still succeeds; with a **wrong** key, decryption fails and the failure is classified, not silently ignored. |
| 9 | **Cancellation and timeout classification** | A request cancelled before completion reports `execution_cancelled` / `timed_out`, and — per upstream's own semantics — is **not** automatically replayed. Evidence: no automatic second dispatch, observed at dispatch level (see row 12). |
| 12 | **Idempotency — dispatch-level proof** | A repeated request with the same `Idempotency-Key` returns the replayed stored response rather than re-executing, and a conflicting reuse returns `409 idempotency_key_conflict`. **Evidence must be dispatch-level, not response-level:** receiving the same response body twice does **not** prove the provider was not contacted twice. The proof requires either (a) **dispatch-level instrumentation** — an upstream request counter or gateway-side dispatch log proving exactly one upstream dispatch — or (b) a **controlled provider fixture** that counts inbound requests. Recording two identical responses is **insufficient** and must not be reported as proof. |

### 5.4 Local executor tests versus real provider calls

This distinction is explicit and must not be blurred in any future proof
document:

- **Groups 0, 1, 1b, 2, and 4 differ in kind, and the difference matters.**
  - **Group 0 (authentication invariant)** — the never-empty-store invariant.
    Runs **before** any credential exists and is **re-run at every
    transition**. Its evidence is the gateway's **rejection** of
    unauthenticated and invalid requests, plus the token list at each
    moment. This is the evidence that distinguishes "authentication is
    configured" from "authentication is currently enforced."
  - **Group 1 (gateway-internal)** — discovery, denials, unavailability,
    redaction, runtime baseline. **No external provider call.**
  - **Group 1b (unauthenticated live call)** — `hackernews.get_top_stories`
    requires **no credential**, but it **does** reach the live Hacker News
    API. It is an **external provider call**, not a local executor test.
    Describing it as "local" would misrepresent the evidence.
  - **Group 2 (isolation denials)** — gateway-internal. The evidence is that
    a request was refused *before* any provider call, which is exactly what
    makes it isolation evidence.
  - **Group 4 (lifecycle and encryption)** — partly gateway-internal, partly
    dependent on a credentialed connection; row 12 requires dispatch-level
    instrumentation rather than response comparison.
- **Group 3 row 18 is a real upstream provider API call.** It proves that the
  gateway can reach and correctly authenticate against a live third-party API
  and return live provider content. It is a different and weaker kind of
  evidence than Group 2 in one respect — a single account's success says
  nothing about isolation — and a different and stronger kind in another: it
  exercises the full network path, the real OAuth/token refresh path, and the
  real provider contract.
- **A passing Group 1b says nothing about Group 3.** A gateway that executes
  `hackernews.get_top_stories` perfectly may still fail on every
  OAuth provider.
- **A passing Group 1 says nothing about Group 1b.** Discovery metadata and
  policy denials do not prove the execution path reaches a live external API.
- **No group is a Codexify release claim.** Per ADR-075's proof
  boundary and ADR-069's evidence doctrine, local adapter and executor
  evidence does not widen the release boundary, and
  `docs/architecture/00-current-state.md` remains the release truth source.

---

## 6. Integration Sequencing

Four gates. **None is executed by this task.** Each gate lists its
prerequisites, the authorized implementation surface, its tests and observable
evidence, its rollback procedure, and its stopping condition. A gate may not
start until the prior gate's evidence is recorded.

### Gate A — Isolated OpenConnector runtime qualification

**Purpose.** Answer one question:

> **Can we run this connector engine reliably, invoke useful actions, and
> isolate credentials without introducing a competing authority system?**

If **yes**, proceed toward Guardian integration. If **no**, stop. There is no
sunk-cost attachment to a dependency Codexify has not yet adopted.

#### Scope discipline

This plan is a **specification of intent**, not an implementation commitment.
Its length reflects the number of boundaries that must be respected, not a
required amount of code. Gate A is deliberately **small and disposable**: a
standalone Compose project, a host-local secret file, and a throwaway trial
harness. The following are explicitly **out of Gate A scope** and must not be
started on the strength of this document:

- **No Guardian adapter work.** No `guardian/connections/openconnector/`
  package, no new routes, no Command Bus registration.
- **No ADR amendment.** The §4.7(a) delegated credential-vault question is
  **not** opened in Gate A. It is settled only **after** Gate A demonstrates
  the substrate is worth adopting — an amendment to an ADR nobody has
  validated is premature.
- **No migration, no schema, no UI, no catalog entry.**
- **No promotion, no release claim, no supported-profile change.**

If Gate A passes, the **next** meaningful milestone is Gate B, and it remains
separately authorized. Gate A's own conclusion may legitimately be "the
substrate does not meet the bar," and that outcome is a **successful
execution of the gate**, not a failure to be rationalized away.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Docker available; the pinned image digest verified; `OOMOL_CONNECT_ENCRYPTION_KEY`, `OOMOL_CONNECT_ADMIN_TOKEN`, and the action allowlist generated into a host secret store; the standalone Compose project from §2.2 authored; the §5.1 trial definition agreed. |
| **Authorized implementation surface** | A **new, separate** Compose project file for the gateway. A host-local secret file outside the repository. A throwaway trial harness that calls the gateway directly over `codexify_internal`. **No file under `guardian/`, `frontend/`, `config/`, or the existing `docker-compose.yml` may be modified.** |
| **Tests and observable evidence** | The §2.5 **fail-closed preflight** runs and passes **before** `docker compose up`, reporting key names only. The resolved Compose configuration is confirmed to still carry `OOMOL_CONNECT_BLOCKED_PROXIES="*"`, `OOMOL_CONNECT_BLOCKED_TRIGGERS="*"`, a **non-empty** `OOMOL_CONNECT_ALLOWED_ACTIONS` **exactly equal to the approved trial actions**, and **no published ports** (§2.5 verification table). *Gate A deliberately ran the gateway **without** the deployment guard, so that the substrate's guard-absent behavior could be established and the defect reported; the §2.5 preflight has since been amended to **require** the guard (§2.4, §4.7(a)), so the recorded Gate A evidence corresponds to the guard-absent configuration and any deployment that proceeds must satisfy the amended preflight.* The §2.4 **bootstrap sequence** is executed in order: containment first, then the **sentinel token**, then the first working token, then **proof that an unauthenticated `/v1` request is now rejected** — and only then any provider credential. **§5.3 Group 0 runs first**, before any credential exists, and is **re-run after every token handoff, after restart, and after deleting the last user token** (rows 0a–0c, 0f–0h). The §5.1.1 **overlapping handoff** is executed and observed (row 5): the store is **never observed empty** at any step, and unauthenticated `/v1` is rejected throughout. §5.3 Groups 1, 1b, 2, 3, and 4 pass against the pinned digest. Group 2 is exercised against **credential-bearing** connections, with row 16a recording the `no_auth` grant exemption as expected behavior. Evidence: gateway runtime receipts, the health-check transcript, the version-baseline output, the encryption-at-rest scan, the log-redaction scan, the trigger-denial result, the two-account isolation results, the token-list snapshots at each transition, and — for §5.3 row 12 — **dispatch-level** idempotency instrumentation rather than response comparison. Isolation evidence must come from the **runtime-token grant and connection-binding mechanisms**, not from network placement (§2.3). |
| **Rollback procedure** | Stop and remove the standalone project; remove the `codexify_openconnector_data` volume if the trial is abandoned; revoke the trial tokens; destroy the trial provider credentials at the provider. **Nothing to roll back inside Codexify**, because nothing inside Codexify changed. |
| **Stopping condition** | Stop and escalate if: the pinned digest cannot be pulled or verified; the runtime fails upstream's CVE-2026-111497 baseline; the encryption key cannot be held outside the data volume; **the fail-closed preflight cannot be made to run before startup, or a required secret is missing/empty at startup**; **an unauthenticated `/v1` request is still accepted after the first token is created** (§2.4 bootstrap step 4); **the token store is observed empty at any point** — including during a handoff, after a restart, or after deleting the last user token — **or unauthenticated `/v1` is accepted at any such point**; **the sentinel token is absent, or is able to authorize any operation**; **a token with an empty or omitted `allowedConnections` is observed while a credential-bearing connection exists**; **the P0 unrestricted-grant token survives into the credentialed or two-account phase**; **a Trigger execution is not refused** (`OOMOL_CONNECT_BLOCKED_TRIGGERS="*"` ineffective); **the resolved allowlist is not exactly the approved trial actions, or contains a wildcard**; two synthetic accounts cannot be isolated; a provider proxy is reachable despite `OOMOL_CONNECT_BLOCKED_PROXIES="*"`; any credential material appears in a log; or upstream's action-grant semantics cannot be made to restrict per-account connections. **Any of these means the substrate does not meet the isolation bar, and Gate B does not begin.** In particular, if the gateway cannot maintain authenticated execution through ordinary token lifecycle operations **without** relying on an unrestricted runtime credential **for execution**, that is **meaningful negative Gate A evidence and a legitimate reason to reject the dependency.** The deployment enforcement guard (§4.7(a)) is not reliance for execution: it authorizes nothing, is never presented by an account path, and exists only to make the runtime fail closed by configuration. Ordinary execution still has to run on scoped persistent tokens alone. |


### Gate B — Guardian read-only adapter and Command Bus integration

**Purpose.** Introduce the adapter and register gateway-backed read commands
in the Command Bus. Still **no** user-facing setup surface.

**Gate B status (2026-11-02) — partial.** This gate is delivered as bounded
slices. Two are implemented, and the gate is **not** complete.

**Slice 1 — the adapter core.** An internal, provider-agnostic adapter core
under `guardian/connections/openconnector/` — a typed Guardian-owned binding
interface, a reviewed server-controlled read-only allowlist, the pinned v1.9.4
transport, and the bounded execution crossing — with focused tests. That slice
registers **no** route, **no** Command Bus command, and **no** catalog entry.

**Slice 2 — the internal route and the Command Bus registration seam.** The
registration contradiction the first slice flagged is resolved from **one**
authority. `guardian/core/route_visibility.py` owns the canonical mounted-route
authority, and two consumers project it with different visibility policies:

* the **public** OpenAPI document — public routes only, with unchanged content;
* the **Command Bus** manifest — public routes plus the internal-only routes
  that are **explicitly** marked command-visible.

Command visibility is declared once, on the route, with the `command_visible`
marker. It is **never** inferred from "mounted": an internal-only route family
that is mounted but not marked stays invisible to the Command Bus, so the
agent-visible command surface cannot widen by accident, and there is no second
command registry. The public document's route set is unchanged by this work.

The new route is
`GET /api/guardian/connections/openconnector/actions/{action_id}`, mounted under
the new `openconnector` route label with an `internal_only` posture. It is a
**read**, because the Command Bus classifies a command by its HTTP method: only
a GET produces the `read` / `read_only` / `safe` / `none` command this gate
requires, and a mutating method would be refused by the phase-one tool policy.
The route exposes **one** operation and accepts **no** action arguments, so no
model-supplied argument can carry account identity, connection identity, or
credential material into the crossing.

Authorization is Guardian's, and it is derived rather than supplied. The account
session is verified by Guardian's existing dependency; the account and subject
come from Guardian's resolved request scope; and the provider comes from the
reviewed allowlist entry for the action. The crossing then requires **two**
separate Guardian facts, and neither substitutes for the other:

| Guardian fact | Answers | Source |
| --- | --- | --- |
| **Credential binding** | *Which* account-owned credential may be selected | Guardian-owned binding, resolved for the authenticated account |
| **Usage grant** | *Whether* this actor may invoke that credential at all | A separate Guardian determination naming account, subject, provider, and action |

This separation is load-bearing rather than cosmetic. ADR-094 requires
credential selection and eligibility to be **separate decisions** and requires
the execution-time boundary to revalidate the binding **and** the policy. When
connector and network permission were derived from the binding, the binding's
existence stood in for the invocation permission check, and a revoked
*permission* would have been invisible to a revalidation that only re-read the
credential. A binding without a usage grant authorizes nothing; a usage grant
without a binding selects nothing; both default to denying. Both are re-read
immediately before the external crossing, so a revocation of either — between
resolution and dispatch — stops the call.

**The hosted path is unqualified.** The hosted deployment runs the
`public_allowlist` exposure mode, which refuses **every** internal-only path
for **every** caller — including the Command Bus loopback. The command is
registered and the local (`local_safe`) path is invocable; the hosted path
cannot invoke it. That is recorded as a **qualification gap**, not solved: no
signed bypass marker, no separate ingress, and no privileged internal caller
were introduced, and the hosted `public_allowlist` restriction is unchanged.
Hosted service-to-service invocation architecture is deferred to a separately
authorized review.

**What remains open.** The catalog entry is **not** added; the durable
Guardian-owned binding store and the durable usage-grant store remain **Gate C**
deliverables; the reviewed allowlist review is not yet recorded; and there is
still **no** guardian-adapter evidence against a running gateway. All evidence so
far is **synthetic and fixture-based** — it proves Guardian's route,
authorization, and registration behavior, not live upstream execution and not
production account authority.

#### Live-trial observation (2026-11-03) — the no-auth connection contract

A bounded live trial ran the pinned gateway (`v1.9.4` @
`sha256:9cbc8cbb…`) with the deployment guard configured, trial-only secrets,
no provider credential, no Codexify account, and no database row. The trial
published the gateway's port on **loopback only** — a deviation from the §2.3
target posture, which publishes no host port at all, required because the
Guardian harness runs on the host and Docker Desktop does not route to
container addresses. The deviation is a trial affordance and does not change
the deployment target.

What the trial measured, at the gateway level:

| Observation | Result |
| --- | --- |
| Unauthenticated `/v1` before bootstrap | **401** — the guard posture held; no zero-token window opened |
| Unauthenticated `/v1` after token creation | **401** — the store never observed empty |
| Sentinel token executing an action | `action_not_allowed` — the sentinel grants nothing |
| `POST /v1/actions/hackernews.get_top_stories` with a scoped token | **200**, live Hacker News story ids — the live provider leg works |
| Admin connection inventory | no-auth connections are **virtual**, enumerated as `service:default` ids (for example `hackernews:default`); they are not stored and have no UUID |

**The finding that matters.** For a **no-auth** provider the only accepted
execution form is **no connection selector at all**. Every explicit selector is
refused with `connection_not_allowed` (403) — whether it names a UUID the grant
carries, or the virtual id `hackernews:default`. A grant naming the virtual id
does not authorize it either. The "explicit connection selection, never a
default" rule therefore holds for **credential-bearing** crossings, where the
stored connection has a UUID that the grant and the selector must both name,
and it is **unsatisfiable** for a **no-auth** crossing, where there is no
account-owned connection to select.

Consequence for the code: the Slice 1 adapter sends
`x-oo-connector-app-id: <binding.connection_uuid>` on every crossing, so it
**cannot** execute the one currently allowlisted action against a live
gateway. The live crossing is therefore blocked on a **connection-contract
amendment**, not on transport, and the amendment touches the reviewed-allowlist
decision that Gate B already lists as outstanding: an action may only execute
without an account-owned connection if its review records that fact.

**Not claimed.** No Guardian-to-gateway crossing completed. Nothing here
establishes Guardian adapter isolation, live transport interoperability through
the adapter, or production account authority. The trial's own evidence is
gateway-level and is not a Gate B proof receipt.

#### Slice 5 observation (2026-11-03) — live credential-bearing isolation

The reviewed no-auth crossing (recorded in
`docs/architecture/proofs/runtime/2026-11-03-openconnector-gate-b-live-crossing-proof.md`)
cannot establish credential-bearing tenant isolation, so this slice qualified
exactly one credential-bearing read action against the real pinned gateway:
`aeroleads.get_details_from_linkedin_url`. Upstream declares it
`operationType: "read"` (`src/providers/aeroleads/actions.ts`, pinned commit
`d89dc9f24f5a057bb500272d7dbf333837c77c68`) and executes it as a
provider-side `GET` lookup (`src/providers/aeroleads/executors.ts`); its
credential class is `api_key` with format-only validation, so disposable fake
credentials exercised the full grant machinery with no real provider account.

Two synthetic accounts each received their own stored connection (distinct
UUIDs), scoped token, binding, and single-connection grant. Through the
existing Guardian route over real HTTP: each account's own-connection call
was Guardian-authorized and gateway-accepted, then rejected by the provider
for the fake credential (the expected, distinguishable shape); every
cross-account, unknown-connection, empty-grant, revoked-binding, missing
authority, and mid-flight revalidation case failed closed with zero
unauthorized provider execution; the gateway independently refused a foreign
token/connection pairing with `connection_not_allowed`, which also proves
the live dispatches ran under grant-checked scoped bearers rather than a
privileged credential. Live execution:
`tests/connections/test_openconnector_credentialed_isolation.py`, 12 passed.
Full evidence:
`docs/architecture/proofs/runtime/2026-11-03-openconnector-gate-b-credentialed-isolation-proof.md`.

Teardown was verified after the run (container, volume, and network
removed with absence listings empty; loopback listener confirmed closed;
scratch removed; tokens revoked). The catalog projection for the qualified
provider is the next independently bounded task. Gate B remains open.

#### Slice 6 observation (2026-11-03) — AeroLeads catalog projection

The qualified provider is projected as exactly one canonical catalog entry,
`aeroleads`. ADR-075 identity confirmation: category `web`, because the
reviewed operation retrieves structured data about a Web resource (a
LinkedIn profile URL) through a Web-provider surface — the existing
`extract` meaning, advertised without `search`. It is not `knowledge`:
AeroLeads is not an authenticated, user-scoped content repository, and
`content_read` is not repurposed for lead enrichment. No category or
capability token was added. Per ADR-071 B1 the custodian is not an entry:
OpenConnector appears only as the entry's runtime binding
(`guardian.connections.openconnector` /
`OpenConnectorAdapter`). The entry is `partial` / `unavailable` with no
setup route, no fields, no scopes, and no OAuth handler: the adapter and
the internal-only read route exist, but user setup, durable bindings,
connected accounts, successful real-provider retrieval, and hosted
callability are unqualified, and the description and setup help say so.
Full evidence:
`docs/architecture/proofs/runtime/2026-11-03-openconnector-gate-b-slice-6-catalog-projection-proof.md`.
Gate B remains open.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Gate A passed with recorded evidence. **The §4.7(a) ADR amendments accepted** (2026-11-02) — delegated credential-vault authority is settled, which is what allows Codexify to hold a gateway token; the accepted amendments remain the contract this gate implements. The §3.1 catalog decision and §3.4 route-posture plan reviewed. |
| **Authorized implementation surface** | A new package `guardian/connections/openconnector/` (adapter, service, router, credentials). A **new** provider-specific operations router with **GET-only** read routes. A **reviewed, server-controlled read-only action allowlist** held in Codexify code (§3.4) — one reviewed entry per permitted action id, with the review recorded. Registration of those routes in `guardian/guardian_api.py` under a **new, provider-specific route label** added to `config/supported_profiles/v1-local-core-web-mcp.yaml` — `internal_only` first, `enabled` only after this gate's evidence. The corresponding provider entry in `guardian/connections/catalog.py`. Focused tests under `tests/connections/` and `tests/command_bus/`. **Binding resolution is a typed interface in this gate, not a store**: the adapter resolves a Guardian-owned binding through an injected resolver, and the Gate B isolation proof uses **synthetic, in-memory bindings** supplied by the test harness, because **durable Guardian-owned binding persistence is a Gate C deliverable** (§4.3). The adapter therefore fails closed whenever no authoritative resolver is configured, and no production binding registry or credential database is created here. **Invocation permission is a second typed interface in this gate, not a store**: the route resolves a Guardian-owned usage grant through an injected authorizer, and the Gate B proof uses **synthetic in-memory grants** supplied by the test harness, because **durable usage-grant persistence is also a Gate C deliverable**. The crossing therefore fails closed whenever no authorizer is configured — a binding's existence never substitutes for the permission check. **The Notion and Google Drive packages, their routes, their catalog entries, and the legacy `connectors` route family must not be modified.** The legacy `connectors` label stays quarantined. |
| **Tests and observable evidence** | The adapter's discover and execute paths are proven against the Gate A gateway. Command Bus invocation evidence: the new routes appear in the manifest as `op::<operation_id>` with `effect=read`, `risk=read_only`, `idempotency=safe`, `approval_mode=none` — the mechanical consequence of the GET-only rule in §3.4. **Read-only allowlist evidence:** an action id **on** the allowlist executes against the gateway; an action id **off** the allowlist is refused by the adapter with a bounded `denied` outcome **and no gateway call is made**; an allowlist entry that the review determined is **not** genuinely read-only is a defect and blocks the gate. **This test must distinguish the Command Bus label from the actual behavior** — the label `read_only` is an assertion about classification, not proof that the upstream action is side-effect-free. Permission-denial evidence: a request denied by the Guardian permission profile, and one denied by the gateway's connection grant, produce **distinguishable** bounded outcomes. Isolation evidence: the two-account Group 2 results reproduced **through the Guardian adapter**, not only against the raw gateway — run against **synthetic Guardian bindings** with credential-bearing synthetic connections, because durable binding storage is Gate C's deliverable. That synthetic proof establishes **adapter** isolation only; it does **not** establish production account authority, and it is not a substitute for Gate C's durable-binding evidence. Observability evidence: the invocation appears in the Command Bus event stream with actor, subject, and task lineage, and the tool-turn read model reports it with no credential material. Redaction evidence: a scan of Command Bus run records and logs finds no token, secret, or admin token. Catalog evidence: `GET /api/connections` projects the new entry with correct `implementation_state` and per-user setup state, and the **existing** Notion and Drive projections are **byte-for-byte unchanged** for an unchanged user. |
| **Rollback procedure** | Remove the new route label from the supported profile (the route is then unmounted and the Command Bus manifest drops the commands automatically, since the manifest derives from the mounted routes). Remove the catalog entry. Remove the `guardian/connections/openconnector/` package. The gateway project is stopped per Gate A rollback. No database migration is created in this gate, so there is **no schema rollback**. |
| **Stopping condition** | Stop and escalate if: the Command Bus registers the new routes as anything other than `read`/`read_only`/`safe`/`none` (which would mean the GET-only rule was violated); **the read-only allowlist is absent, is derived at runtime from the gateway catalog, is model- or request-supplied, or is found to contain an action that can mutate remote state**; any gateway credential or runtime token appears in a run record, log, event, or result; the existing Notion or Drive projections or behavior change in any way; a second Settings connector surface is introduced; the legacy `connectors` route family is enabled; or the adapter is found to be reachable by a path that bypasses the Guardian permission profile. |

### Gate C — User-scoped connection setup and existing Settings control-plane integration

**Purpose.** Let a user bind their own provider connection, and project that
binding through the **existing** Connections control plane and Settings bay.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Gate B passed with recorded evidence. **The §4.7(a) ADR amendments accepted** (2026-11-02) — the delegated-custody model is settled, and the binding record schema it implies must still be settled before a schema migration is authored. **The durable Guardian-owned binding store is created in this gate** — Gate B's synthetic resolver stood in for it, so the Gate B isolation proof is re-run here against the durable store rather than being carried over as evidence. **The durable Guardian-owned usage-grant store is created in this gate** for the same reason: Gate B's synthetic authorizer stood in for the invocation-permission fact, and the credential reference and the permission are kept as separate records because ADR-094 requires separate decisions. **The §4.7(b) remote OAuth callback question resolved** — or the gate proceeds **local-only, API-key/no-auth providers only**, with the remote posture explicitly out of scope. **The §4.7(c) ADR-075 catalog-identity confirmation obtained.** A reviewed schema migration for the binding record, plus a data-retention and account-deletion policy for it. |
| **Authorized implementation surface** | A provider-specific setup router under the existing `/api/connect/<provider>/*` convention, mounted `internal_only` (matching `notion_setup` and `google_drive_setup`). A migration adding the binding record (§4.3). The provider entry's `runtime_binding.setup_route` in `guardian/connections/catalog.py`. The existing read-only Connections API and the existing Settings Connectors bay are **reused, not modified**. **No new Settings section, page, or AppShell view.** No change to the Notion or Drive setup seams. No public OAuth callback route unless §4.7(b) is resolved and separately authorized. |
| **Tests and observable evidence** | Setup evidence: a user binds a provider connection through the setup route; the binding record is written user-scoped; the gateway connection is created under the user's identity; the Codexify-side runtime token is stored encrypted and never returned by any API. Projection evidence: `GET /api/connections` shows the new entry with `needs_setup` → `configured` → `connected` transitions tracking real upstream state, and `configured` is **never** shown without an explicit validation. Revocation evidence: disconnecting removes the binding, deletes the upstream token and connection, and the user can no longer execute against that connection (bounded `denied`/`needs_configuration`, never a silent fallback). Isolation evidence: the two-user matrix is re-run through the **full** setup-and-execute path. Credential-exposure evidence: a scan of API responses, browser-visible payloads, logs, and Command Bus records finds no token, secret, admin token, credential prefix, or suffix. Migration evidence: migration applies cleanly on a disposable PostgreSQL instance; the head stays single; rollback of the migration is exercised. Notion/Drive non-regression evidence: the existing Notion and Drive tests pass **unchanged**. |
| **Rollback procedure** | Revert the migration (a down-migration must exist and be exercised). Remove the setup route and its route label. Revert the catalog entry. Delete the binding table's contents. The gateway project is stopped per Gate A rollback. The existing Notion and Drive setup seams are untouched, so **no rollback is required for them**. |
| **Stopping condition** | Stop and escalate if: the binding record cannot be made strictly user-scoped; a user can observe or infer another user's connection, provider account label, or connection id; the runtime token or any provider credential is reachable by any API response, log, event, or frontend storage; a model-supplied identifier influences connection selection; the public OAuth callback surface is required but §4.7(b) is unresolved; the migration lacks a working down-migration; the migration graph gains a second head; or existing Notion/Drive behavior changes in any way. |

### Gate D — Multi-user security qualification and explicit supported-profile / release review

**Purpose.** Qualify the whole path under realistic multi-user conditions, and
then — **only** — consider a supported-profile or release posture change.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Gates A, B, and C passed with recorded evidence. A **dedicated, adversarial security review** of the delegated credential-vault model, the runtime-token custody path, the revocation ordering, and the redaction surface. Upstream security posture current: upstream applies security fixes to the latest release and `main` only, so the pinned digest must be re-checked against current upstream advisories. An explicit product decision on whether this capability is ever a supported surface. |
| **Authorized implementation surface** | Test and qualification code; updated **release-posture documentation** (`docs/architecture/00-current-state.md` and any relevant ADR or support matrix) **only if** this gate's evidence warrants it and the change is separately authorized. A supported-profile route-posture change from `internal_only` to `enabled` only if warranted. **This gate does not itself grant release status** — the release gate is `HOLD` per current state, and changing it requires the separate release process. |
| **Tests and observable evidence** | Full multi-user qualification: two-plus synthetic accounts with distinct provider connections, cross-account denial, wrong-connection denial, shared-default denial, cross-project and cross-thread attempts, and concurrent invocation under load. Credential-recovery evidence: encryption key loss and restore behavior; runtime-token rotation; revocation ordering (Guardian first, then gateway, then provider). Restart/persistence evidence at the full-stack level, not just the gateway. Egress evidence: no unauthorized external network execution; the SSRF guard remains in its default posture; provider proxy remains disabled. Observability evidence: every gateway invocation is attributable to an actor, subject, task, and connection binding; no hidden invocation. Redaction evidence: a full sweep of logs, events, run records, API responses, and database rows finds no credential material. Provider verification evidence: at least one **real** provider API read, with the provider's own terms respected. **A release-posture document update is produced if and when warranted** — and its absence is also a valid, honest outcome. |
| **Rollback procedure** | Revert the route posture to `internal_only`. Revert the release-posture documentation change if one was made and the posture is withdrawn. Execute the Gate C rollback (migration down, setup route removal, catalog entry removal, binding data deletion). Stop and remove the gateway project. The release gate returns to `HOLD`. |
| **Stopping condition** | Stop and escalate if: any cross-account access is possible; any credential material is observable outside its encrypted store; the upstream runtime baseline cannot be met on a current upstream release; the pinned digest is past upstream's security-fix window and cannot be upgraded safely; a required provider cannot be authorized without violating its terms; the existing Notion/Drive or other supported surfaces regress; or the release evidence cannot be produced within a single qualification run. **Any of these means the capability stays non-supported, and that outcome is a legitimate result of this gate — not a failure to be papered over.** |

---

## 7. ADR Impact

This document is **aligned with** the following, and amends only where the
relationship says so:

| ADR | Relationship |
| --- | --- |
| **ADR-024** (Context Command / active connector semantics) | Preserved. The gateway is a connector bridge. Use is turn-scoped; `connected != consulted`; outcomes use ADR-024's canonical vocabulary. No change to connector state semantics. |
| **ADR-069** (Beta runtime support boundary) | Preserved. No release claim is widened. Connectors remain outside default Beta support without current-main qualification. |
| **ADR-071** (Connections control-plane boundary) | **Amended 2026-11-02 (§4.7(a)).** Preserved: Connections remains a projection, never an execution owner. No new Settings section. No duplicate mutation routes. Credentials remain server-owned and user-scoped. The amendment admits a delegated external custodian as a runtime binding behind ordinary provider entries — never a catalog entry, never a second connection-identity authority, and never a second control surface. |
| **ADR-072** (bounded Settings and connections route promotion) | Preserved. The pattern of a separately-labeled route family with an explicit profile posture is followed. The legacy `connectors` label stays quarantined. |
| **ADR-075** (Connections knowledge category and content capabilities) | Preserved. Exactly four categories; provider-specific setup seams; provider-specific adapters; agent-invocable operations through the Command Bus; read-only content capabilities; no new write capability is authorized. |
| **ADR-077** (sandbox execution authority and provider boundary) | Preserved. The custodian's provider calls stay on the provider side of the boundary; no provider credential or provider-issued material reaches an agent-facing tool, shell command, or sandbox workload absent a separate explicit Guardian grant. |
| **ADR-092** (credential purpose and mixed-principal authentication boundary) | Preserved. The four credential classes are kept on separate lanes and never substitute for one another (§4.7(a)). A runtime token minted for one account never serves another. |
| **ADR-094** (account-scoped execution credential authority) | **Extended by an accepted amendment, 2026-11-02 (§4.7(a)).** Guardian remains the sole account-authorization authority; a delegated external custodian is admitted as a subordinate credential custodian with no independent Codexify account authority, under one canonical Guardian-owned binding, ordered revocation, stated in-flight semantics, and four fixed recovery dispositions. |

**ADR-071 and ADR-094 were amended on 2026-11-02.** The §4.7(a)
delegated credential-vault question is addressed by an *amendment section inside*
each ADR — not a new ADR, and no change to either ADR's original accepted status,
accepted text, or number. The §4.7(b) public OAuth callback question and the §4.7(c)
catalog-identity question for gateway-backed providers **remain open** and are not
addressed by it.

**Sequencing decision.** Gate A completed with a **conditional pass**, and the §4.7(a)
amendment was **accepted on 2026-11-02** — after Gate A demonstrated that the
substrate is worth adopting, and before Gate B begins. The sequencing intent held.
Acceptance discharges the architecture prerequisite only: Gate B implementation
remains a separate bounded task under the accepted amendments, the runtime proof
those amendments require is still outstanding, and the Gate C and Gate D gates remain
separately gated.

---

## 8. Proof Surface

This task produces **a documented plan only**. It proves no runtime behavior.

Separate future validation must provide:

- **Gateway runtime evidence** — the pinned digest running, healthy, at a
  version meeting upstream's security baseline (Gate A).
- **Runtime authentication bootstrap evidence** — the sequence in §2.4
  executed in order, culminating in an **observed rejection** of an
  unauthenticated `/v1` request after the first scoped persistent token
  exists (Gate A).
- **Connection-grant evidence** — every issued token carries an explicit
  non-empty `allowedConnections` grant; the unrestricted-grant token is
  revoked and its revocation observed **before** any credential-bearing
  connection exists (Gate A).
- **Command Bus invocation evidence** — gateway-backed read commands
  registered as `read`/`read_only`/`safe`/`none` and executing through the
  existing event and observability surfaces (Gate B).
- **Read-only allowlist evidence** — actions off the reviewed
  server-controlled allowlist are refused **before** any gateway call, and the
  allowlist is shown to contain no remotely mutating action (Gate B).
- **Permission denial and tenant isolation evidence** — Guardian-side and
  gateway-side denials distinguishable, and cross-account access impossible
  (Gates A–D).
- **Restart/persistence and credential recovery evidence** — connections and
  credentials survive restart; encryption at rest is verifiable; key loss is
  a documented unrecoverable condition, not a silent failure (Gates A, C, D).
- **Dispatch-level idempotency evidence** — proof that a replayed
  `Idempotency-Key` produced **one** upstream dispatch, via instrumentation or
  a controlled fixture, not by comparing response bodies (Gate A).
- **Provider-specific real API verification** — a live read-only provider
  call against the real upstream API (Gate A Group 3, Gate D).
- **Updated release-posture documentation, when warranted** — produced only if
  the evidence supports it, and its absence is an acceptable outcome.

---

## 9. Deferred Work

Explicitly **not** done here, and not authorized by this task:

1. No Docker installation, image pull, container start, or deployment.
2. No production OAuth application registration and no public callback route.
3. No live provider credentials.
4. No database migrations — including the binding record schema in §4.3.
5. No new runtime routes and no new provider adapters in Codexify.
6. No Settings or UI changes.
7. No enablement of the quarantined `connectors` route family, or of any
   other quarantined label.
8. No autonomous tool-execution expansion.
9. No alteration of existing Notion or Google Drive behavior, routes,
   credentials, or catalog entries.
10. No change to `docs/architecture/00-current-state.md` and no release-posture
    change. ADR-071 and ADR-094 were **amended** on 2026-11-02 (§4.7(a)) — an
    amendment section inside each, with no new ADR, no change to either ADR's
    original accepted text, and no release widening.
11. No upstream fork.
12. §4.7(a) is **resolved** — accepted 2026-11-02 (§4.7(a)). §4.7(b) and
    §4.7(c) remain open and unresolved.
13. No security-monitoring subsystem, bespoke scanner, or dedicated pipeline
    for OpenConnector. The §1.4 monitoring commitment is an operator
    responsibility performed by reading upstream's release and advisory
    channels.
14. **Superseded — the deployment guard is now required.** The runtime guard
    (`OOMOL_CONNECT_RUNTIME_TOKEN`) **must** be present in the gateway's
    `env_file` (§2.4, §2.5). It is service-owned, operator-custodied, never
    distributed, and never presented for execution; ordinary execution still
    uses scoped persistent tokens only (§4.3). The earlier prohibition on
    setting it is withdrawn.
15. No `docker compose config` invocation whose output is captured into logs
    or shell history, since it renders expanded secret values (§2.5).

---

## 10. Source Anchors

**Upstream — `oomol-lab/open-connector` at `v1.9.4`
(commit `d89dc9f24f5a057bb500272d7dbf333837c77c68`):**

| Document | Relevance |
| --- | --- |
| `LICENSE.txt` | Apache-2.0 text and §4 redistribution obligations. |
| `NOTICE.md` | Existing NOTICE — triggers §4(d). Third-party trademark reservation. |
| `SECURITY.md` | Supported-version window (latest release and `main` only); hardening baseline; CVE-2026-111497 runtime baseline; explicitly disclaims insecure self-hosted configuration. |
| `docker-compose.yml` | The mutable `:latest` image and the all-interfaces `3000:3000` mapping. |
| `docker-compose.build.yml` | Builds from `docker/Dockerfile` and tags as `:latest`. |
| `docs/docker-ghcr.md` | Tag taxonomy (`latest`, `<release-version>`, `tip`, `<short-sha>`); immutable pinning guidance; `migrate` subcommand for PostgreSQL; health endpoint. |
| `docs/runtime-api.md` | Runtime surfaces (`/v1/*`, `/mcp`); runtime-token vs admin-token split; `allowedConnections` exact-allowlist semantics; `403 connection_not_allowed` before credential lookup; unfiltered admin discovery; alias selection; bounded error codes; idempotency; timeout and cancellation semantics. |
| `docs/configuration.md` | Environment-variable reference; `ALLOW_PRIVATE_NETWORK` default `false`; `EGRESS_TRUSTED_HOSTS`; JWT configuration and its Node-only, unrestricted-by-connection characteristics. |
| `docs/credentials.md` | AES-256-GCM at rest and the plaintext fallback without a key; key rotation and recovery semantics; connection identity (`accountId`, `displayName`, `grantedScopes`); named connections and aliases; action and proxy policy independence; the `hackernews.get_top_stories` no-auth path. |
| `src/server/connect-app.ts` | `runtimeAuthConfigured = requireRuntimeAuth \|\| runtimeToken \|\| verifyRuntimeJwt \|\| hasStoredRuntimeTokens()` — the value that turns runtime authentication on once the first persistent token exists. **Also `hasStoredRuntimeTokens = async () => (await runtimeTokens.listTokens()).length > 0`** — a **live per-request** store query, which is why an empty store reopens the unauthenticated window (§2.4, §5.1.1). |
| `src/server/api/auth.ts` | The auth-mode resolution: `createLocalAuthMiddleware` installs a **pass-through** (no-auth) middleware when no admin token, runtime token, `requireRuntimeAuth`, stored runtime tokens, or JWT verifier exists; `hasValidToken` returns `true` for runtime scope in the same conditions. **This is the source of the bootstrap window in §2.4.** |
| `src/server/storage/postgres/runtime-store.ts` | `revoke` executes `delete from runtime_tokens where id = $1` — revoking the **last** token empties the store and therefore **reopens** the unauthenticated window. The basis for the §5.1.1 never-empty invariant and the overlapping handoff. |
| `src/server/api/policy-input.ts` | `readConnectionIds` validates only that each connection id is a non-empty, size-bounded, unique string — it does **not** verify the connection exists. This is what makes a gapless handoff possible: a successor token can be created with the **future** connection id before that connection exists. |
| `src/server/index.ts` | The startup warnings: `runtime API authentication is disabled; create a runtime token in the web console, set OOMOL_CONNECT_RUNTIME_TOKEN, or configure JWT authentication`; the admin-token warning; the encryption-key warning. |
| `src/core/action-policy.ts` | `evaluateConnection` returns `allowed: true` when `allowedConnections` is **empty** (§5.1.1); `evaluateAction` skips a policy layer whose `allowedActions` list is empty (the permissive-empty convention); `compileActionRule` — the `*`, `service.*`, and exact-id pattern semantics; `evaluateProxy` (blocked wins across layers) and **`evaluateTrigger`** — Triggers are evaluated by an **independent** policy from Actions and Proxies, so blocking proxies does **not** block triggers. |
| `src/core/provider-definition.ts` | The action definition shape (`id`, `name`, `description`, `requiredScopes`, `providerPermissions`, `followUpActions`) — **no read-only marker**, which is the basis for the §3.4 allowlist requirement. |
| `src/execution-target.ts` | `resolveExecutionTarget`'s `authorize` — the **`no_auth` connection-grant exemption** (`authType === "no_auth"` returns before `evaluateConnection`). The basis for the §5.1.1 note and the Group 2 sequencing rule. |
| `src/oauth/oauth-flow-service.ts` | OAuth `state` as a short-lived record binding `service`, `connectionName`, `retirementGeneration`, PKCE verifier, scopes, and `redirect_uri`; `completeAuthorization` consumes it via the **destructive single-use** `states.take(...)`; `discardAuthorization` uses the same take; expiry enforced by `isExpiredOAuthState`. The basis for the §2.8 correlation property. |
| `src/server/storage/runtime-token-service.ts` | Persistent-token records (`allowedActions`, `blockedActions`, `allowedProxies`, `allowedConnections`, `allowedTriggers`); `createToken` defaults to empty grants; `updateTokenPolicy` **replaces the stored policy wholesale** — the basis for the §5.1.1 token-update rule. Only token **hashes** are stored. |
| `src/server/api/runtime-tokens.ts` (admin surface) | `POST /api/runtime-tokens` — the admin-authenticated endpoint used by the §2.4 bootstrap step 2; `GET/PUT/DELETE /api/runtime-tokens` for lifecycle and revocation. |
| GitHub Release `v1.9.4` | Release metadata, published `2026-10-27`, and per-binary SHA-256 digests. |
| Docker Compose documentation | Interpolation semantics: `${VAR}` is resolved from the shell / `--env-file` / project `.env`, **not** from a service's `env_file`; `docker compose config` renders resolved values. The basis for the §2.5 single-mechanism rule and preflight. |
| The complete upstream `OOMOL_CONNECT_*` variable set | Confirms `OOMOL_CONNECT_ALLOWED_CONNECTIONS` **does not exist** (connection grants are token-level only), and that **no environment-configurable `requireRuntimeAuth` flag** exists at v1.9.4 — the basis for the §2.4 bootstrap sequence being the only available window-closing mechanism. |

**Codexify — read for this plan:**

| Path | Relevance |
| --- | --- |
| `docs/architecture/00-current-state.md` | Release truth; local-first Beta envelope; connectors outside default Beta support. **Not modified.** |
| `docs/architecture/connections-control-plane.md` | The five distinctions; setup-state semantics; credential ownership; runtime-binding ownership; the OAuth posture; the explicit non-claims. |
| `docs/architecture/adr/024-…`, `069-…`, `071-…`, `072-…`, `075-…` | The preserved boundaries summarized in §7. |
| `guardian/connections/catalog.py` | `ConnectionCatalogEntry`, `ConnectionRuntimeBinding`, the `_notion_knowledge_entry()` / `_google_drive_knowledge_entry()` entry pattern. |
| `guardian/routes/connections.py` | Read-only Connections API and request-time per-user state merge. |
| `guardian/routes/connectors.py` | Legacy sync-connector surface and the external transport policy call site. |
| `guardian/command_bus/contracts.py` | `CommandSpec`, `InvokeRequest`, `MAX_PAYLOAD_BYTES`, event and approval vocabularies. |
| `guardian/command_bus/invoke.py` | Command-class derivation, permission-profile construction, external-policy construction. |
| `guardian/command_bus/manifest.py` | OpenAPI-derived command registration; method-derived `effect`/`risk`/`idempotency`/`approval_mode`. |
| `guardian/command_bus/permission_profiles.py` | `CommandClass` vocabulary including `connector` and `network`; `connector_allowed` / `network_allowed`. |
| `guardian/command_bus/redaction_policy.py` | Sensitive-key set and explicit redaction paths. |
| `guardian/command_bus/tool_turn_observability.py` | The read model that makes connector use observable and redacted. |
| `guardian/connectors/oauth_crypto.py` | Codexify's server-side credential encryption primitive. |
| `guardian/core/dependencies.py` | Account identity dependencies. |
| `config/supported_profiles/v1-local-core-web-mcp.yaml` | Route posture; `connections` enabled, `connectors` quarantined. |
| `docker-compose.yml` | The existing stack; **not modified** by this task. |

---

## 11. Summary of the Boundary in One Paragraph

OpenConnector v1.9.4 (commit `d89dc9f24f5a057bb500272d7dbf333837c77c68`,
Apache-2.0, with the upstream `LICENSE.txt` and `NOTICE.md` retained as a
Codexify dependency practice) is a credible
implementation substrate for Codexify's external-application access, deployed
as an **optional, isolated service** with its own pinned image digest, its own
encrypted credential volume, a **private network with no published ports**, and
an **admin token that is never reachable from a model or a runtime path** —
while the private network itself is treated as containment rather than as the
authorization boundary. Codexify does **not** gain a second control plane: the
gateway is not a catalog entry; it is the `runtime_binding.adapter` behind
ordinary provider entries in the existing catalog, and every agent-invocable
operation is a **GET-only route** so the Command Bus derives
`read`/`read_only` semantics mechanically rather than by assertion — a
classification that is therefore backed, in Gate B, by a reviewed
server-controlled read-only action allowlist rather than by the HTTP method
alone. Credential
authority splits cleanly — the gateway holds provider credentials, Codexify
holds an explicit **per-user binding** to a gateway connection plus a per-user
persistent runtime token whose `allowedConnections` grant is the enforcement
mechanism — and because an **empty** grant means unrestricted access rather
than deny-all, every Codexify-issued token carries an explicit non-empty
grant, and the unrestricted-grant token is revoked before any
credential-bearing connection exists. Two upstream behaviors refine that
boundary: virtual **`no_auth` connections bypass the connection-grant check
entirely**, so isolation evidence must come from credential-bearing
connections; and **token updates replace the stored policy wholesale**, so any
update that omits the grant would silently widen it. The runtime surface is
authenticated by a **deployment-scoped enforcement secret** plus an
**explicit bootstrap sequence**: the guard is configured as deployment
infrastructure, never distributed and never presented for execution, so the
runtime fails closed by configuration from the first request; the bootstrap
sequence then creates the first scoped persistent token, proves that an
unauthenticated request is rejected, and only then admits credentials. The
token-store invariant is retained as **defense in depth** — that protection is
re-derived from a **live** store query on every request, so the store must
**never be empty**, a **sentinel token** keeps it non-empty for the gateway's
life, and every handoff **overlaps** rather than gaps. The upstream dependency is **pinned but tracked**: v1.9.4 remains
the licensed baseline, while monitoring, evaluation, and remediation of
upstream releases and advisories is an explicit operator responsibility that
does not extend to copying code newly published under more restrictive
licensing. The first validation slice is a no-auth Hacker News action against
the pinned build — an **unauthenticated but genuinely external** call, proven
locally, with two synthetic accounts, before any real provider API is touched.
The remote OAuth posture remains **deferred to Gate C**, where the open
question is narrowed to *which component owns callback correlation* — a
restricted reverse proxy in front of upstream's own single-use `state` store,
or a Guardian-owned forwarder that would have to reproduce that property
across two systems.
Gate A asked one question — can this engine run
reliably, invoke useful actions, and isolate credentials without introducing
a competing authority system? — and answered it with a **conditional pass**:
the substrate runs, the credential isolation holds, and an upstream
authentication defect was confirmed and reported privately upstream. That
answer did not settle the authority question on its own, so the authority question
was taken to architecture review: the delegated-custody relationship is now
**accepted** (2026-11-02) as a bounded amendment to ADR-071 and ADR-094, admitting
the gateway as a subordinate external credential custodian while Guardian remains
the sole account-authorization authority. Acceptance discharges the architecture
prerequisite only — implementation is a separate bounded task, the runtime proof it
requires is still outstanding, and nothing is deployed, promoted, or adopted.
Nothing in this document installs, deploys, or promotes anything;
`docs/architecture/00-current-state.md` remains the release truth, and
OpenConnector remains outside Beta support.
