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
| **Integration posture** | **Prove before integrating.** Gate A is disposable and answers one question (§6, Gate A). No Guardian adapter work and **no ADR amendment** until Gate A passes. No sunk-cost attachment if it does not. |

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
| Command Bus commands are derived from the mounted OpenAPI surface | `guardian/command_bus/manifest.py:43-60` |
| A command's risk/effect/idempotency/approval mode is derived from its HTTP method | `guardian/command_bus/manifest.py:134-137` |
| Account identity is a server-derived dependency, never a request body field | `guardian/core/dependencies.py` (`get_account_user_id`, `require_account_session`) |
| Provider credential material is encrypted at rest by a server-side primitive | `guardian/connectors/oauth_crypto.py` |

### Not yet true — do not assume

- OpenConnector is **not installed** anywhere in this repository or on any
  Codexify host by this task.
- Gateway-to-Guardian compatibility is **not proven**. No Codexify code path
  has yet spoken to an OpenConnector instance.
- Multi-user connection isolation is **not proven**. No two-account test has
  been run against a gateway.
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

**Binding obligations for any Codexify distribution or deployment:**

1. **§4(a)** — ship the Apache-2.0 license text with any redistribution of the
   image, source, or derivative work.
2. **§4(b)** — any modified files must carry prominent notices stating the
   change.
3. **§4(c)** — retain all copyright, patent, trademark, and attribution
   notices in the distributed form.
4. **§4(d)** — because a `NOTICE` file **exists**, any derivative distribution
   **must** include a readable copy of the attribution notices from
   `NOTICE.md`, in a NOTICE file, in the source or documentation, or in a
   display. This obligation is **not** optional and **not** satisfied by
   omitting NOTICE. Codexify must reproduce `NOTICE.md` verbatim alongside the
   pinned artifact.
5. **§6 (Trademarks)** — the Apache grant does not extend to upstream's trade
   names or product names beyond customary descriptive use and NOTICE
   reproduction. Codexify must not brand its product surface as
   "OOMOL Connect" or imply upstream endorsement or certification.
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

    # --- Secrets: injected by the host secret store, never committed ------
    env_file:
      - /run/secrets/openconnector.env

    environment:
      OOMOL_CONNECT_DATA_DIR: /app/data
      # Required. Without it upstream stores credentials in PLAINTEXT and
      # only prints a startup warning. See §2.5.
      OOMOL_CONNECT_ENCRYPTION_KEY: ${OOMOL_CONNECT_ENCRYPTION_KEY:?required}
      # Required. Protects /api, /docs, and the Web Console.
      OOMOL_CONNECT_ADMIN_TOKEN: ${OOMOL_CONNECT_ADMIN_TOKEN:?required}
      # NOT set: OOMOL_CONNECT_RUNTIME_TOKEN. A bootstrap runtime token is
      # UNRESTRICTED with respect to connection grants. Per-user scoping
      # requires persistent 'oct_...' tokens (see §4.3).
      OOMOL_CONNECT_ALLOWED_ACTIONS: ${OOMOL_CONNECT_ALLOWED_ACTIONS:?required}
      OOMOL_CONNECT_BLOCKED_ACTIONS: ${OOMOL_CONNECT_BLOCKED_ACTIONS:-}
      # Provider proxy is disabled outright: /v1/proxy/:service reaches
      # provider API endpoints beyond the curated Action catalog, and every
      # proxy is allowed until one of these variables restricts it.
      OOMOL_CONNECT_BLOCKED_PROXIES: "*"
      OOMOL_CONNECT_ALLOWED_PROXIES: ""
      # Keep upstream's SSRF guard in its default posture.
      OOMOL_CONNECT_ALLOW_PRIVATE_NETWORK: "false"
      OOMOL_CONNECT_EGRESS_TRUSTED_HOSTS: ${OOMOL_CONNECT_EGRESS_TRUSTED_HOSTS:-}

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
| **Bootstrap runtime** | `OOMOL_CONNECT_RUNTIME_TOKEN` | `/v1/*`, `/mcp` | **Deliberately left unset.** A bootstrap token carries **no stored connection grant** and is therefore unrestricted with respect to connections — it is a cross-tenant capability. |
| **Persistent runtime** | `oct_...` tokens (hashed at rest) | `/v1/*`, `/mcp` | The **only** runtime credential Codexify's runtime path may use. Each carries an explicit `allowedConnections` allowlist of stable opaque connection IDs. |
| **JWT access** | `OOMOL_CONNECT_JWKS_URI` / `_JWT_ISSUER` / `_JWT_AUDIENCE` | `/v1/*`, `/mcp` | Not used in the first slice. Upstream states JWTs do not map claims to action or proxy policy and have no stored connection grant; a JWT-only deployment would be unrestricted by connection. Deferred behind the ADR question in §4.7. |

Upstream's own security guidance is explicit that **both** admin and runtime
authentication are disabled by default for local development, and that a
deployment must never expose the gateway publicly without both enabled. This
plan enables both, and additionally ensures the administrative interface is not
network-reachable at all (§2.3).

### 2.5 Credential encryption and recoverable key management

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
| **Restart** | `docker compose -p codexify-openconnector restart openconnector`. Provider credentials, named connections, and OAuth state persist in the volume. Upstream's SQLite path auto-migrates on start. |
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
  exactly that URI.
- The `/oauth/callback` route must be reachable by the **provider's redirect**
  — that is, from the public internet, not from the private network. This
  **conflicts with §2.3's "no published administrative interface"** posture
  as currently specified, and is therefore **not resolved by this plan**.
- The upstream callback design assumes the **app that owns the redirect
  forwards the provider's callback query** to the runtime; a Codexify-owned
  public callback endpoint would be a **new Guardian route**, which this
  task is not authorized to create.
- **This is an explicit stopping condition for Gate C.** Before any remote
  OAuth posture is designed, the following must be resolved and separately
  authorized: where the public callback terminates, how its state is signed
  and verified, how the callback result reaches the gateway, and how that
  surface is prevented from becoming a second credential-mutation authority
  outside the Connections control plane.

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
- **This is a genuine second credential authority.** See §4.7 — it is the
  principal item requiring an ADR amendment before implementation.

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

**Per-user token scoping.** Each Codexify user's runtime path uses a
persistent runtime token whose `allowedConnections` contains **only** that
user's bound connection ids, plus `allowedActions` restricted to the
allowlisted action ids and `allowedProxies: []`. Upstream states that a
non-empty `allowedConnections` list is an **exact allowlist of stable, opaque
ids**, that token grants **intersect with** deployment policy and cannot widen
it, and that denied connections fail with `403 connection_not_allowed` before
credential lookup.

**Bootstrap tokens and JWTs are not used for per-user execution.** Upstream is
explicit that bootstrap runtime tokens and JWTs have **no stored connection
grant** and "remain unrestricted." Using either for a multi-user Codexify
path would silently grant every user access to every stored connection. The
topology in §2.2 therefore leaves `OOMOL_CONNECT_RUNTIME_TOKEN` unset.

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
   own authorization settings. Upstream's OAuth credential then fails with a
   bounded `credential_expired` / `scope_missing` classification on next use.

**Ordering:** Guardian revokes its binding first (fast fail-closed), then
deletes the upstream token and connection, then the user handles the provider.
**Restored references must not revive revoked authority** — consistent with
ADR-094, restoring a backup must not resurrect a revoked binding.

### 4.6 Turn-scoped use

Consistent with §3.7 and ADR-024: gateway use is a turn-scoped crossing event.
A bound connection is *connected*; it is not *consulted* every turn. Discovery
results are cached only for the turn unless a future governed feature pins
them longer. The gateway's action catalog is not a standing instruction set.

### 4.7 Authority decisions requiring an ADR amendment

Three points in this plan exceed current accepted ADR text. **Each must be
explicitly resolved before implementation.** No ADR change is authorized by
this task.

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

**(b) The public OAuth callback surface — ADR or architecture review required.**

As established in §2.8, a remote OAuth posture requires a **public HTTPS
callback endpoint** that terminates outside the private network. ADR-075
defines the provider-specific setup and credential seam as provider-specific
and server-owned; a shared public callback endpoint is a **new Guardian
route** and a **new authority surface**. This must be resolved by a future
architecture review before any remote-provider claim.

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
| Authentication | Admin token for setup; a persistent runtime token with `allowedConnections: []` and an explicit `allowedActions` grant for execution |

### 5.2 Why `no_auth` first

The Hacker News action requires no provider credential, no OAuth
registration, no redirect URI, and no provider account. It therefore isolates
**gateway health, action discovery, action execution, response shaping,
idempotency, and error classification** from every credential and OAuth
variable. A failure at this stage is unambiguously a gateway problem.

### 5.3 Test matrix

Each row states its **observable evidence**. Rows are grouped by evidence type,
because the distinction matters (§5.4).

**Group 1 — gateway behavior against the pinned build (no real provider account required).**

| # | Test | Observable evidence |
| --- | --- | --- |
| 1 | **Action discovery** | `GET /v1/actions?service=hackernews` returns the trial action id and its input schema; the returned schema matches the action's actual accepted input. |
| 2 | **Successful execution** | `POST /v1/actions/hackernews.get_top_stories` with the runtime token returns `success` with a bounded payload; the harness records the response envelope shape and the observed payload size. |
| 3 | **Denied action** | An action **outside** `OOMOL_CONNECT_ALLOWED_ACTIONS` is refused. Evidence: the gateway's own denial (not a Guardian denial) with the upstream error code. |
| 4 | **Proxy denial** | `POST /v1/proxy/:service` is refused, proving `OOMOL_CONNECT_BLOCKED_PROXIES="*"` is effective and the raw provider-API escape hatch is closed. |
| 5 | **Missing runtime token** | A `/v1` request with no bearer token is refused. Evidence: gateway auth rejection. |
| 6 | **Gateway unavailability** | The container is stopped; a client call fails as a transport error. Evidence: bounded `unavailable` classification, **not** an action-level `failed`. |
| 7 | **Restart and persistence** | The container is restarted; a previously created named connection and its credential are still present and still usable. Evidence: the connection id is unchanged and the action still succeeds. |
| 8 | **Credential encryption and recovery** | With `OOMOL_CONNECT_ENCRYPTION_KEY` set, the stored credential record on disk is **not** plaintext. Evidence: the raw secret string does not appear in the database file. Then: with the same key and a restored volume, the credential still decrypts and the action still succeeds; with a **wrong** key, decryption fails and the failure is classified, not silently ignored. |
| 9 | **Cancellation and timeout classification** | A request cancelled before completion reports `execution_cancelled` / `timed_out`, and — per upstream's own semantics — is **not** automatically replayed. Evidence: no automatic second dispatch. |
| 10 | **Audit redaction and source provenance** | The harness's own log of the exchange contains **no** credential material, no bearer token, and no admin token. Evidence: a scan of the captured logs for the secret values returns zero matches. |
| 11 | **Runtime baseline** | `docker exec codexify-openconnector node --version` reports a version meeting upstream's CVE-2026-111497 baseline (Node `22.23.4+` / `24.22.1+` / `26.12.1+`, or Bun `1.4.4+`). |
| 12 | **Idempotency** | A repeated request with the same `Idempotency-Key` does not re-dispatch upstream and returns the replayed stored response; a conflicting reuse returns `409 idempotency_key_conflict`. Evidence: upstream's documented status codes, and that the provider was contacted once. |

**Group 2 — tenant isolation (requires two synthetic accounts).**

| # | Test | Observable evidence |
| --- | --- | --- |
| 13 | **Two-user isolation** | Two synthetic users each hold a distinct bound connection and a distinct persistent runtime token. User A's token cannot execute against User B's connection: `403 connection_not_allowed`, raised **before** credential lookup. Evidence: the denial, plus the observation that no provider call was made. |
| 14 | **Wrong-account access** | A token scoped to User A that explicitly names User B's connection id is denied with `connection_not_allowed`. Evidence: the denial code and the absence of a provider call. |
| 15 | **Wrong-connection access** | An unknown or ungranted connection id is denied; upstream's "an unknown selector never falls back to another connection" property is observed. Evidence: denial, not silent fallback to the default connection. |
| 16 | **Shared default connection** | A request that **omits** the connection selector on a deployment that has a shared default connection is denied, proving the shared unscoped default is not reachable. Evidence: `connection_not_allowed`. |

**Group 3 — real upstream provider API calls (separately authorized).**

| # | Test | Observable evidence |
| --- | --- | --- |
| 17 | **Provider authentication failure** | A credentialed provider action with a deliberately invalid credential fails with a bounded `credential_expired` / `scope_missing` classification. Evidence: the classification and the absence of raw upstream error text in any log or projection. |
| 18 | **Real provider read** | The separately authorized read-only provider action succeeds against the **real** provider API and returns real provider content. Evidence: the live upstream response, recorded separately from Group 1. |

### 5.4 Local executor tests versus real provider calls

This distinction is explicit and must not be blurred in any future proof
document:

- **Group 1 and Group 2 are local executor tests.** They exercise the
  gateway's own code paths — discovery, policy evaluation, credential
  resolution, connection grants, persistence, encryption, redaction — and, in
  Group 2, the isolation behavior *between* synthetic accounts. A passing
  Group 2 proves the gateway's **grant mechanism** isolates accounts. It does
  **not** prove that two real provider accounts are isolated in every
  provider-specific code path.
- **Group 3 row 18 is a real upstream provider API call.** It proves that the
  gateway can reach and correctly authenticate against a live third-party API
  and return live provider content. It is a different and weaker kind of
  evidence than Group 2 in one respect — a single account's success says
  nothing about isolation — and a different and stronger kind in another: it
  exercises the full network path, the real OAuth/token refresh path, and the
  real provider contract.
- **A passing Group 1 says nothing about Group 3.** A gateway that executes
  `hackernews.get_top_stories` perfectly may still fail on every
  OAuth provider.
- **Neither group is a Codexify release claim.** Per ADR-075's proof
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
| **Tests and observable evidence** | §5.3 Group 1 (rows 1–12) and Group 2 (rows 13–16) pass against the pinned digest. Evidence: gateway runtime receipts, the health-check transcript, the version-baseline output, the encryption-at-rest scan, the log-redaction scan, and the two-account isolation results. Isolation evidence must come from the **runtime-token grant and connection-binding mechanisms**, not from network placement (§2.3). |
| **Rollback procedure** | Stop and remove the standalone project; remove the `codexify_openconnector_data` volume if the trial is abandoned; revoke the trial tokens; destroy the trial provider credentials at the provider. **Nothing to roll back inside Codexify**, because nothing inside Codexify changed. |
| **Stopping condition** | Stop and escalate if: the pinned digest cannot be pulled or verified; the runtime fails upstream's CVE-2026-111497 baseline; the encryption key cannot be held outside the data volume; two synthetic accounts cannot be isolated; a provider proxy is reachable despite `OOMOL_CONNECT_BLOCKED_PROXIES="*"`; any credential material appears in a log; or upstream's action-grant semantics cannot be made to restrict per-account connections. **Any of these means the substrate does not meet the isolation bar, and Gate B does not begin.** |


### Gate B — Guardian read-only adapter and Command Bus integration

**Purpose.** Introduce the adapter and register gateway-backed read commands
in the Command Bus. Still **no** user-facing setup surface.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Gate A passed with recorded evidence. **The §4.7(a) ADR amendment resolved and accepted** — delegated credential-vault authority must be settled before Codexify holds any gateway token. The §3.1 catalog decision and §3.4 route-posture plan reviewed. |
| **Authorized implementation surface** | A new package `guardian/connections/openconnector/` (adapter, service, router, credentials). A **new** provider-specific operations router with **GET-only** read routes. Registration of those routes in `guardian/guardian_api.py` under a **new, provider-specific route label** added to `config/supported_profiles/v1-local-core-web-mcp.yaml` — `internal_only` first, `enabled` only after this gate's evidence. The corresponding provider entry in `guardian/connections/catalog.py`. Focused tests under `tests/connections/` and `tests/command_bus/`. **The Notion and Google Drive packages, their routes, their catalog entries, and the legacy `connectors` route family must not be modified.** The legacy `connectors` label stays quarantined. |
| **Tests and observable evidence** | The adapter's discover and execute paths are proven against the Gate A gateway. Command Bus invocation evidence: the new routes appear in the manifest as `op::<operation_id>` with `effect=read`, `risk=read_only`, `idempotency=safe`, `approval_mode=none` — the mechanical consequence of the GET-only rule in §3.4. Permission-denial evidence: a request denied by the Guardian permission profile, and one denied by the gateway's connection grant, produce **distinguishable** bounded outcomes. Isolation evidence: the two-account Group 2 results reproduced **through the Guardian adapter**, not only against the raw gateway. Observability evidence: the invocation appears in the Command Bus event stream with actor, subject, and task lineage, and the tool-turn read model reports it with no credential material. Redaction evidence: a scan of Command Bus run records and logs finds no token, secret, or admin token. Catalog evidence: `GET /api/connections` projects the new entry with correct `implementation_state` and per-user setup state, and the **existing** Notion and Drive projections are **byte-for-byte unchanged** for an unchanged user. |
| **Rollback procedure** | Remove the new route label from the supported profile (the route is then unmounted and the Command Bus manifest drops the commands automatically, since the manifest derives from the mounted OpenAPI surface). Remove the catalog entry. Remove the `guardian/connections/openconnector/` package. The gateway project is stopped per Gate A rollback. No database migration is created in this gate, so there is **no schema rollback**. |
| **Stopping condition** | Stop and escalate if: the Command Bus registers the new routes as anything other than `read`/`read_only`/`safe`/`none` (which would mean the GET-only rule was violated); any gateway credential or runtime token appears in a run record, log, event, or result; the existing Notion or Drive projections or behavior change in any way; a second Settings connector surface is introduced; the legacy `connectors` route family is enabled; or the adapter is found to be reachable by a path that bypasses the Guardian permission profile. |

### Gate C — User-scoped connection setup and existing Settings control-plane integration

**Purpose.** Let a user bind their own provider connection, and project that
binding through the **existing** Connections control plane and Settings bay.

| Aspect | Definition |
| --- | --- |
| **Prerequisites** | Gate B passed with recorded evidence. **The §4.7(a) ADR amendment accepted** (the binding record schema and the delegated-custody model must be settled before a schema migration is authored). **The §4.7(b) remote OAuth callback question resolved** — or the gate proceeds **local-only, API-key/no-auth providers only**, with the remote posture explicitly out of scope. **The §4.7(c) ADR-075 catalog-identity confirmation obtained.** A reviewed schema migration for the binding record, plus a data-retention and account-deletion policy for it. |
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

This document is **aligned with** and does not amend:

| ADR | Relationship |
| --- | --- |
| **ADR-024** (Context Command / active connector semantics) | Preserved. The gateway is a connector bridge. Use is turn-scoped; `connected != consulted`; outcomes use ADR-024's canonical vocabulary. No change to connector state semantics. |
| **ADR-069** (Beta runtime support boundary) | Preserved. No release claim is widened. Connectors remain outside default Beta support without current-main qualification. |
| **ADR-071** (Connections control-plane boundary) | Preserved. Connections remains a projection, never an execution owner. No new Settings section. No duplicate mutation routes. Credentials remain server-owned and user-scoped. |
| **ADR-072** (bounded Settings and connections route promotion) | Preserved. The pattern of a separately-labeled route family with an explicit profile posture is followed. The legacy `connectors` label stays quarantined. |
| **ADR-075** (Connections knowledge category and content capabilities) | Preserved. Exactly four categories; provider-specific setup seams; provider-specific adapters; agent-invocable operations through the Command Bus; read-only content capabilities; no new write capability is authorized. |

**No ADR change is authorized by this task.** The three questions in §4.7 —
delegated credential-vault authority, the public OAuth callback surface, and
catalog identity for gateway-backed providers — are **future** decisions. A
future implementation must explicitly resolve them and determine whether an
ADR addition or amendment is required.

**Sequencing decision.** None of these three is opened during Gate A. The
§4.7(a) delegated credential-vault amendment is settled **only after** Gate A
demonstrates that the substrate is worth adopting, and **before** Gate B
begins. Amending an ADR on the strength of a plan for a dependency that has
never been exercised would be premature: it would commit Codexify's
architecture doctrine to a component that may yet fail its own qualification
gate. Gate A's outcome may legitimately be "not worth adopting," in which case
**no ADR is amended and no adapter is written**.

---

## 8. Proof Surface

This task produces **a documented plan only**. It proves no runtime behavior.

Separate future validation must provide:

- **Gateway runtime evidence** — the pinned digest running, healthy, at a
  version meeting upstream's security baseline (Gate A).
- **Command Bus invocation evidence** — gateway-backed read commands
  registered as `read`/`read_only`/`safe`/`none` and executing through the
  existing event and observability surfaces (Gate B).
- **Permission denial and tenant isolation evidence** — Guardian-side and
  gateway-side denials distinguishable, and cross-account access impossible
  (Gates A–D).
- **Restart/persistence and credential recovery evidence** — connections and
  credentials survive restart; encryption at rest is verifiable; key loss is
  a documented unrecoverable condition, not a silent failure (Gates A, C, D).
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
10. No change to `docs/architecture/00-current-state.md`, no release-posture
    change, and no ADR addition or amendment.
11. No upstream fork.
12. No decision on the §4.7 authority questions.
13. No security-monitoring subsystem, bespoke scanner, or dedicated pipeline
    for OpenConnector. The §1.4 monitoring commitment is an operator
    responsibility performed by reading upstream's release and advisory
    channels.

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
| GitHub Release `v1.9.4` | Release metadata, published `2026-10-27`, and per-binary SHA-256 digests. |

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
Apache-2.0 with a `NOTICE.md` that must be reproduced) is a credible
implementation substrate for Codexify's external-application access, deployed
as an **optional, isolated service** with its own pinned image digest, its own
encrypted credential volume, a **private network with no published ports**, and
an **admin token that is never reachable from a model or a runtime path** —
while the private network itself is treated as containment rather than as the
authorization boundary. Codexify does **not** gain a second control plane: the
gateway is not a catalog entry; it is the `runtime_binding.adapter` behind
ordinary provider entries in the existing catalog, and every agent-invocable
operation is a **GET-only route** so the Command Bus derives
`read`/`read_only` semantics mechanically rather than by assertion. Credential
authority splits cleanly — the gateway holds provider credentials, Codexify
holds an explicit **per-user binding** to a gateway connection plus a per-user
persistent runtime token whose `allowedConnections` grant is the enforcement
mechanism. The upstream dependency is **pinned but tracked**: v1.9.4 remains
the licensed baseline, while monitoring, evaluation, and remediation of
upstream releases and advisories is an explicit operator responsibility that
does not extend to copying code newly published under more restrictive
licensing. The first validation slice is a no-auth Hacker News action against
the pinned build, proven locally, with two synthetic accounts, before any
real provider API is touched. Gate A asks one question — can this engine run
reliably, invoke useful actions, and isolate credentials without introducing
a competing authority system? — and its answer may legitimately be **no**, in
which case nothing is adopted, no ADR is amended, and no adapter is written.
Nothing in this document installs, deploys, or promotes anything;
`docs/architecture/00-current-state.md` remains the release truth, and
OpenConnector remains outside Beta support.
