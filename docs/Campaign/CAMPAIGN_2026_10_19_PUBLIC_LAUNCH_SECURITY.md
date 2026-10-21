# Public Launch Security Hardening Campaign

**Started:** 2026-10-19  
**Repository evidence tip:** `146bef7bed5030f5a10f5ef365d97f13bb4f4383` (`main`)  
**Current qualification:** `HOLD`  
**Ingress decision:** Cloudflare Access remains mandatory; this campaign does not authorize changing public exposure.

## Objective

Qualify Guardian application-level authentication, account isolation, operator boundaries, session controls, deployment posture, abuse controls, and PostgreSQL recovery before considering removal of Cloudflare Access. Cloudflare Access remains an independent outer admission control until the entire public-ingress gate below has current, reviewed evidence.

A passing unit or repository test is code evidence only. It does not qualify the deployed Mac mini, public ingress, backups, recovery, or production readiness.

## Current evidence and findings

| ID | Finding | Current evidence | Status |
|---|---|---|---|
| PLS-01 | The September configuration-omission failure is corrected in the intended Private Preview Compose profile. That overlay sets `private_preview`, `remote`, and multi-user mode, and its one-shot posture check gates backend startup. The general/local configuration still intentionally has local auth defaults and the fallback local user; omitting the Private Preview overlay is not a safe public deployment. | `docker-compose.private-preview.yml`; `guardian/core/dependencies.py`; [2026-09-25 proof](../architecture/proofs/runtime/2026-09-25-public-ingress-auth-boundary-proof.md) | Corrected for that profile; public profile qualification open |
| PLS-02 | Cross-account task-event reads now resolve a task through the durable PostgreSQL completion-attempt row and enforce canonical thread ownership before Redis is read. Regression tests cover owner and foreign-account behavior. | `guardian/core/task_event_access.py`; `tests/identity/test_task_event_stream_authorization.py`; ADR-091 | Corrected in current main; live deployment qualification open |
| PLS-03 | The task-cancel endpoint required an account session but canceled any caller-supplied task ID without checking the durable task-to-thread owner. This permits an authenticated account to cancel another account's known task. A narrow correction and owner/foreign/unknown regression cases are in this campaign branch and await CI/review. | `guardian/guardian_api.py::request_task_cancel`; ADR-091 defines the canonical mapping | Fix implemented in branch; not yet merged or qualified |
| PLS-04 | The base Compose file supplies `codexify` defaults for PostgreSQL credentials, while `.env.private-preview.example` does not explicitly provide `POSTGRES_PASSWORD`. These are repository defaults, not proof of the value on the running Mac mini. Public deployment must fail closed when a default or missing database password is selected. | `docker-compose.yml`; `.env.private-preview.example` | Configuration hardening required; live value unverified |
| PLS-05 | The Mac mini's internal APFS Data volume reports FileVault enabled, but Docker Desktop's `Docker.raw` symlink resolves to `/Volumes/Dev_SSD/offload/docker/Docker.raw`. `Dev_SSD` is an external USB APFS volume and reports `Encrypted: No`; therefore the active Docker disk image and PostgreSQL volume are not covered by FileVault. Backup encryption, recovery-key escrow, and a restore drill were not verified. | Read-only `fdesetup status`, `diskutil info /System/Volumes/Data`, `readlink` of Docker Desktop `Docker.raw`, and `diskutil info /Volumes/Dev_SSD` on 2026-10-19 | Internal volume encrypted; active Docker volume on unencrypted external SSD; open at-rest gap |
| PLS-06 | The canonical architecture state continues to classify the supported release as `HOLD` and says tests, route presence, or isolated proofs do not establish public-ingress readiness. | `docs/architecture/00-current-state.md` | Remains controlling |
| PLS-07 | The existing API test module cannot import the current app in this worktree: `guardian/services/memory_purge.py` imports `MemoryLifecycleRevision`, which is absent from `guardian/db/models.py`. This is outside W1, but blocks app-level integration tests and must be reconciled before a live candidate can be qualified. | pytest collection on current `main`; `guardian/services/memory_purge.py:89-97` | Existing mainline startup/test blocker; not changed in this campaign branch |
| PLS-08 | The public allowlist middleware denies paths only when `GUARDIAN_EXPOSURE_MODE=public_allowlist`; other exposure modes pass requests through to the app. Private Preview pins a different profile behind Cloudflare Access, and there is no independently qualified public route profile. | `guardian/core/public_exposure.py::PublicExposureMiddleware`; `docker-compose.private-preview.yml`; `docs/Ops/private-browser-preview.md` | Profile selection is security-critical; full route inventory and public profile qualification open |
| PLS-09 | Operator authentication is distinct in `require_operator_auth`; route-auth migration tests enforce operator dependencies for their frozen route inventory. The admin module has a debug bypass only inside the local auth boundary. The full mounted public-route inventory and live rejection matrix have not been qualified. | `guardian/core/dependencies.py`; `guardian/routes/admin.py`; `tests/identity/test_operator_route_auth_migration.py` | Existing controls present; complete inventory and live tests open |
| PLS-10 | Account sessions have a 24-hour default TTL and logout calls the session-store revocation method. This code evidence does not prove revocation propagation across runtime instances or behavior during store loss/restart. | `guardian/core/session_store.py`; `guardian/routes/auth.py` | Code paths present; end-to-end public lifecycle qualification open |
| PLS-11 | The frontend injects the dev API key only in Vite development mode; `X-User-Id` override is honored only under explicit debug/local conditions, and Private Preview rejects caller-controlled overrides. The production bundle and deployed environment were not inspected in this task. | `frontend/src/vite.config.ts`; `guardian/core/dependencies.py::get_request_user_id`; `frontend/src/lib/__tests__/trustedRemoteAuthTransport.test.ts` | Guarded in source; production artifact/runtime verification open |

## Independently testable work packages

### W1 — Task resource authorization for mutation (P0)

**Scope:** Bind account task cancellation to the canonical task's chat thread while retaining the existing account-session requirement.

**Acceptance criteria:**

- The owning authenticated account can request cancellation of its task.
- A different authenticated account receives denial and the cancellation backend is never called.
- Unknown tasks and tasks lacking a durable mapping fail closed before mutation.
- Account credential validation remains required; operator and guest credentials do not become account authority.
- Tests use PostgreSQL-attempt/thread ownership as authority and assert denial occurs before Redis/task mutation.

**Current disposition:** implementation and focused regression tests are in draft PR #882; run CI and obtain review before considering W1 closed.

### W2 — Public route and privilege inventory (P0)

**Scope:** Enumerate every route mounted by the proposed public profile, including aliases and conditionally mounted routers. Record method, path, exposure-profile decision, auth dependency, principal class, account/resource owner check, and operator-only requirement. Review default and private-preview exposure manifests separately.

**Acceptance criteria:**

- The route inventory is generated from the actual app/router graph for each candidate profile and diffed against the approved inventory.
- Every user-data route proves account ownership on every read and mutation; opaque or caller-supplied IDs never grant authority.
- Operator routes require the operator principal and reject account sessions; account routes reject operator credentials; guest routes remain restricted to their room capability.
- Routes absent from the public allowlist return the configured denial response, including aliases and trailing-slash variants.
- A negative test matrix covers anonymous, account A, account B, operator, expired/revoked, malformed, and mixed-principal credentials against representative routes in each family.
- Any unresolved route or ambiguous principal mapping blocks public qualification.

### W3 — Authentication, session lifecycle, defaults, and development paths (P0)

**Scope:** Verify account login/activation, credential purpose separation, expiration, revocation/logout, cookies and CSRF/origin rules, recovery, API-key behavior, frontend development credentials, and local/debug identity overrides.

**Acceptance criteria:**

- Public-mode startup fails closed unless remote auth and multi-user isolation are explicitly active and all required secrets are present, unique, non-placeholder, and sufficiently strong.
- The public runtime cannot use static operator API keys as account credentials or local fallback-user identity.
- Development headers/keys are inactive in production builds and public runtime configuration; debug identity override tests prove denial when debug/local mode is off.
- Account sessions have documented expiry and revocation behavior; logout/revocation denies the next protected request.
- Account, operator, and guest purpose tokens are rejected in each other's credential lane, including mixed credentials.
- Password recovery, activation, session issuance, and account lifecycle negative cases are tested without exposing token material.

### W4 — Account isolation and operator boundary qualification (P0)

**Scope:** Exercise direct records and derived/task resources across two accounts, including reads, writes, deletes, exports, event streams, cancellation, connector state, and administrative views.

**Acceptance criteria:**

- For each resource family, account A can access only A-owned records; account B cannot read, mutate, infer existence of, or trigger side effects on A-owned records by changing IDs.
- Operator authority is restricted to explicitly enumerated administrative operations and cannot silently act as an account user.
- Ownership is derived from canonical durable records on every request, not Redis, browser state, initiator metadata, or caller-supplied owner IDs.
- Multi-user mode is exercised with at least two independently authenticated accounts on the same running candidate.

### W5 — Rate limits and account controls (P1)

**Scope:** Protect login/session issuance, activation/recovery, expensive inference/task submission, connector actions, and storage-heavy operations.

**Acceptance criteria:**

- Limits are enforced per account and per source network where appropriate, using storage shared by all app instances.
- Burst and sustained-limit tests prove bounded work, correct `429` responses, and safe recovery after the window expires.
- Quotas/storage limits and account deletion/export/recovery behavior have explicit user-visible contracts and abuse tests.
- Sensitive responses do not disclose whether another account exists.

### W6 — PostgreSQL at-rest encryption and recovery (P0)

**Scope:** Protect the host volume and all copies of canonical PostgreSQL data; document recovery-key custody and restore procedure.

**Acceptance criteria:**

- Protect the actual APFS volume containing Docker Desktop's VM disk image and PostgreSQL volume: either enable encryption on `Dev_SSD` with a separately recoverable unlock key, or move Docker Desktop storage to a FileVault-protected internal volume. Verify the resolved `Docker.raw` target and effective volume encryption after the change; retain a timestamped non-secret evidence receipt.
- Use an encrypted backup destination (or client-side encrypted backup artifact) with keys stored separately from the Mac and backup media.
- Document key recovery and perform a restore drill into an isolated destination, verifying schema and representative account-separated data without exposing content.
- Confirm database ports are not reachable from public interfaces and that Docker volume ownership/permissions are least-privilege.
- PostgreSQL/database credentials are generated secrets with no Compose fallback in any public profile.

**Protection boundary:** FileVault or APFS volume encryption protects data against offline disk access when the volume is locked. It does not protect a running host from root or malware, an exposed database from stolen service credentials, or plaintext/unencrypted backups. PostgreSQL transport TLS protects network traffic, not the data directory at rest. Consider application-level encryption only for fields whose threat model requires protection from database operators; it does not replace request authorization or runtime host security. Docker documents that its Mac containers/images live in the `Docker.raw` disk image; Apple documents encryption for external storage devices; PostgreSQL documents encryption at multiple layers, with the threat boundary depending on which layer is used.

### W7 — Public-ingress requalification and gate decision (P0)

**Scope:** Re-run an adversarial deployment proof against the exact candidate revision and intended Mac mini/public ingress, with the independent Cloudflare Access layer still active during qualification.

**Acceptance criteria:**

- Candidate image, Compose files, environment posture, secrets source, published ports, reverse-proxy configuration, and route manifest are captured without printing secrets.
- Reproduce the September omitted-settings probe and prove the public profile fails closed; prove intended Private Preview settings remain pinned.
- Run anonymous, account-isolation, operator, session revocation, default-credential, development-auth, rate-limit, backup-restore, and recovery-key negative controls against the running candidate.
- Verify PostgreSQL/Redis/admin interfaces are not publicly reachable and inspect effective runtime config rather than relying on checked-in examples.
- Independent reviewer accepts the evidence and updates the canonical release gate through its normal process. Until then Cloudflare Access stays enabled and the release remains `HOLD`.

## PostgreSQL strategy for the Mac mini

Protect the storage that actually holds Docker Desktop's VM disk image. The inspected `Docker.raw` path is a symlink to the external USB APFS volume `Dev_SSD`, which reports encryption off. Enabling FileVault on the Mac's internal APFS Data volume does not encrypt this external volume. The appropriate baseline is to encrypt `Dev_SSD` with APFS volume encryption and separately recoverable unlock-key custody, or move Docker Desktop's disk image to FileVault-protected internal storage. Keep PostgreSQL in its existing Docker volume; the Compose named-volume declaration does not encrypt it. Store database passwords as generated secrets, and encrypt backups separately before they leave the Mac. Store FileVault and backup recovery material in independently recoverable, access-controlled custody and test restoration.

This is a storage-at-rest control. It does not replace Guardian authorization, account isolation, least-privilege database access, host patching, or protection of a running service. The external volume encryption gap was directly observed on the inspected Mac mini. The active Compose project/volume, backup encryption, recovery-key escrow, and restore process remain to be verified. See [Docker Desktop for Mac storage](https://docs.docker.com/desktop/troubleshoot-and-support/faqs/macfaqs/), [Apple external storage encryption](https://support.apple.com/guide/disk-utility/encrypt-protect-a-storage-device-password-dskutl35612/mac), and [PostgreSQL encryption options](https://www.postgresql.org/docs/current/encryption-options.html).

## Campaign sequencing

1. Merge W1 only after focused regression tests and review.
2. Complete W2–W4 before calling application-level identity/isolation qualified.
3. Complete W5–W6 and retain operational evidence.
4. Complete W7 with Cloudflare Access still enabled throughout testing.
5. Ask for a separate release-gate decision only after independent review of the full evidence packet. This campaign itself never changes production exposure.
