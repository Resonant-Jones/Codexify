# OpenConnector v1.9.4 Gate A — runtime qualification receipt

Date: 2026-11-01

Evaluated upstream artifact: `ghcr.io/oomol-lab/open-connector:v1.9.4` at digest
`sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c`, built from upstream
commit `d89dc9f24f5a057bb500272d7dbf333837c77c68`.

Plan under evaluation:
[`docs/architecture/openconnector-integration-plan.md`](../../openconnector-integration-plan.md)
(commits `6bcd9754d`, `a5cbfd038`, `f838aa55e`, `8a5f505da`, `ec4bfb254`).

Release posture remains **HOLD**. This receipt qualifies one **external, unadopted dependency**
in an isolated disposable runtime. It does not qualify the Codexify product, does not promote
OpenConnector to any support class, and does not authorize any Guardian integration.

## Verdict

**CONDITIONAL PASS** — with one **P1 substrate defect confirmed as a complete exploit
path**, and two operational landmines that the plan did not anticipate.

The gateway does what the plan needs it to do, and the plan's central security properties
hold **when the plan's own discipline is followed**: an explicit non-empty grant per token,
and a token store that is never empty. But the substrate does **not** provide fail-closed
authentication on its own. Its runtime-authentication state is a **side effect of a store
count**, re-derived on every request. Every mitigation this receipt relies on is Codexify
discipline layered on top of upstream behavior, and two of them are load-bearing enough that
getting them wrong is silent.

**Nothing here authorizes Gate B.** Per the plan's own sequencing, Gate B additionally requires
the §4.7(a) delegated credential-vault ADR amendment, which has **not** been opened. Before
that amendment is even drafted, the **fail-closed boundary decision** below must be answered.

## Gate A disposition

| Dimension | Result |
| --- | --- |
| Gateway execution and discovery | **Pass** — 21,053 actions and 1,680 providers loaded; live provider calls executed |
| Connection-grant isolation with scoped tokens | **Pass in the tested configurations** — cross-account attempts denied at the grant |
| Encryption, persistence, and redaction | **Pass for the synthetic trial** — `enc:v1:` ciphertext, no plaintext in db/wal/shm, no credential material in logs or the audit trail |
| Idempotency | **Strong gateway-level evidence** — dispatch-level, not response-level |
| **Fail-closed runtime authentication** | **FAIL** — the token store becoming empty disables authentication, and the stored credential becomes anonymously spendable |
| Production credential custody | **Not qualified** — no live provider credential was used |
| Guardian integration readiness | **Blocked** pending the fail-closed boundary decision |

The distinction matters: the connector engine demonstrated useful capability, but its native
authentication lifecycle did **not** meet the security invariant Codexify needs.

## Environment

| Property | Value |
| --- | --- |
| Host | macOS (darwin 27.2.0), Docker 29.9.2, Docker Compose v5.6.1 |
| Gateway image | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb…b3ef9c` (620,259,162 bytes) |
| Digest verification | Pulled digest matched the plan's pin exactly |
| Runtime baseline | `node v24.22.1` — meets upstream's CVE-2026-111497 baseline (`24.22.1+`) |
| Runtime backend | SQLite (`/app/data/connect.sqlite`), 12 migrations applied at boot |
| Catalog | 1,680 providers, 21,053 actions loaded |
| Topology | Standalone Compose project `codexify-openconnector`, own network `codexify_internal`, own volume, **no published host ports** |
| Secrets | Disposable values generated on-host, mode `0600`, outside the repository, never committed |
| Codexify credentials used | **None.** No Codexify account, database, or production secret was involved |
| Real provider credentials used | **None.** Provider credentials were syntactically valid but fabricated (`FAKE_…`) |
| Teardown | Container, volume, and network removed; verified absent |
| Host scratch cleanup | **Outstanding — requires host permissions.** Trial artifacts were consolidated into `.gate-a-cleanup/` in the worktree and excluded from git via `.git/info/exclude`. See [Host scratch cleanup](#host-scratch-cleanup). |

The plan's §2.2 Compose block was used **verbatim**, with one adaptation: the `env_file` path
pointed at the trial directory instead of `/run/secrets/openconnector.env`. The plan's §2.5
preflight was used **verbatim** and passed before startup.

## What passed

| Row | Observation | Evidence |
| --- | --- | --- |
| 0a | Unauthenticated `/v1` **rejected** once a token exists | HTTP 401 `unauthorized` on `/v1/actions`, `/v1/apps`, `/v1/providers`, `/v1/health` |
| 0b | Token store non-empty and observable | `GET /api/runtime-tokens` listed tokens by name at every checkpoint |
| 0c | Invalid/absent bearer rejected | HTTP 401 on both an absent and a malformed bearer |
| 0d | Sentinel grants nothing | Sentinel bearer: action execution → `action_not_allowed` (400); proxy → `proxy_blocked` (403) |
| 0e | Triggers blocked | `POST /v1/providers/hackernews/triggers/…/execute` → HTTP 403 `trigger_blocked` |
| 0f | Post-handoff re-assertion | Store never observed empty; unauthenticated `/v1` rejected at every handoff step |
| 0g | Post-restart re-assertion | After `docker compose up -d --force-recreate`: tokens persisted, connections persisted, unauthenticated `/v1` → 401 |
| 0h | Post-deletion re-assertion | After deleting every user token, the sentinel remained, store = 1, unauthenticated `/v1` → 401 |
| 1 | Action discovery | `GET /v1/actions?service=hackernews` returned action ids and input schemas |
| 3 | Denied action | Action outside the allowlist → `action_not_allowed` (400) |
| 4 | Proxy denial | `POST /v1/proxy/hackernews` → `proxy_blocked` (403) |
| 5 | Overlapping handoff | Store observed non-empty at every step; predecessor revocation observed via rejected follow-up call |
| 7 | Restart and persistence | Both credential connections and both tokens survived recreate, with ids unchanged |
| 8 | Credential encryption | Stored values are `enc:v1:` AES-256-GCM ciphertext. Raw secrets absent from `connect.sqlite`, `-wal`, and `-shm` |
| 10 | Audit redaction | Zero credential-material matches in the persisted run trail and in container logs |
| 12 | Idempotency — **dispatch level** | 3 HTTP calls (same key) → identical `executionId` (`e2e5f873…`), identical payload, and the gateway's **own run log grew by exactly 1**. A different body on the same key → 409 `idempotency_key_conflict` |
| 13/14/15/16 | Tenant isolation | Cross-account attempts via `x-oo-connector-app-id` header and via `connectionName` body field → `connection_not_allowed` (403). Omitted selector → `connection_not_allowed` (403), never a fallback to a shared default |
| 16a | `no_auth` exemption | A `no_auth` action succeeded under a token whose grant did not include it — expected upstream behavior, recorded so it is not later misread as a grant failure |
| 1b | Live provider execution | `hackernews.get_top_stories` returned **live** Hacker News story ids, `auditPersisted: true`, real `executionId` |

**A live upstream provider call did occur** (Group 1b, row 17): the `aeroleads` action with the
fabricated credential reached the real provider API and was rejected by it —
*"User not Found, Please Pass Valid Api Key"*.

## P1 — the substrate has no fail-closed authentication guarantee

**Confirmed at source and reproduced at runtime — and the exploit path is complete, not
merely a precondition.**

Upstream re-derives runtime authentication from a **live store query on every request**:

```ts
// src/server/connect-app.ts
const hasStoredRuntimeTokens = async (): Promise<boolean> =>
  (await runtimeTokens.listTokens()).length > 0;
```

and `hasValidToken` returns `true` — unauthenticated access permitted — when there is no
environment runtime token, no `requireRuntimeAuth`, no JWT verifier, **and no stored tokens**.
`revoke` executes `delete from runtime_tokens where id = $1`.

**Runtime proof.** On a fresh database with no token, the container logged
`runtime API authentication is disabled; create a runtime token in the web console, set
OOMOL_CONNECT_RUNTIME_TOKEN, or configure JWT authentication` — and unauthenticated
`/v1/actions`, `/v1/apps`, and `/v1/providers` all returned **HTTP 200**, exposing **21,053
actions and 1,680 providers** with no credential. The admin surface was correctly protected
(HTTP 401) throughout.

**The window reopens.** Revoking every token drove the store to zero and unauthenticated
`/v1/actions` returned **HTTP 200** again — while **two credential-bearing connections
remained stored**. Revoking the sentinel last, with credentials still present, reproduced the
same state.

### The exploit path is complete — an anonymous caller can spend a stored credential

The finding above establishes a *precondition*: credentials stored while authentication is
disabled. That is not by itself proof of exploitability. A second, targeted run answered the
remaining question directly.

**Setup.** A fresh gateway (empty database → zero tokens → authentication disabled by
construction), one credential-bearing connection stored (`aeroleads`, named `default`, key
`FAKE_CREDENTIAL_PROBE_0123456789`), and `aeroleads.get_details_from_linkedin_url` present in
the deployment allowlist.

**The call.** `POST /v1/actions/aeroleads.get_details_from_linkedin_url` with **no bearer token
at all**, body `{ "input": { "linkedin_url": "https://www.linkedin.com/in/example" } }`.

**Result.**

```text
-> HTTP 400  errorCode=invalid_input
-> User not Found, Please Pass Valid Api Key
-> meta: {"executionId":"b02c5245-68e0-4fa8-9fba-9d7b0f1be2a9",
          "actionId":"aeroleads.get_details_from_linkedin_url",
          "auditPersisted":true}
```

That response is the **provider's own rejection**. It is conclusive: the gateway retrieved the
stored credential, transmitted it to the live provider, and recorded the attempt in its audit
trail as a normal execution. An anonymous caller spent a stored provider credential.

**Controls, run in the same state:**

| Call | Result |
| --- | --- |
| Deployment-allowed, credential-bearing action, **no bearer** | HTTP 400, **provider's rejection** — credential was retrieved and sent |
| Action **not** in the deployment allowlist (`hackernews.get_ask_stories`), no bearer | HTTP 400 `action_not_allowed` |
| Deployment-allowed `no_auth` action (`hackernews.get_top_stories`), no bearer | HTTP 200, live execution, `auditPersisted: true` |

**Reading.** The deployment action allowlist is the **only** barrier between an anonymous
caller and a stored provider credential. In this deployment the gateway had no published ports
and was reachable only from the private network — so the exposure was contained by
**containment, not by authorization**. If the gateway were reachable by an unauthorized party
with the token store empty, every deployment-allowed credentialed action would execute against
the stored credential on that party's behalf.

This upgrades the finding from "dangerous precondition" to "**confirmed exploit path**" — but
it also makes the containment requirement unambiguous: with this substrate, network isolation
is not a hardening measure, it is the thing standing between the defect and a
credential-spending incident.

### What this means for the plan

The plan's standing invariant (§5.1.1) is correct and
necessary, and the sentinel token works: with it present, deleting every user token left the
store non-empty and unauthenticated `/v1` rejected. But the property being defended is
**"authentication is currently enforced,"** not "authentication is configured" — and it is
re-derived per request, so it can vanish **silently**. A Codexify implementation that treats
"we created a token at bootstrap" as sufficient would be wrong.

**Adoption concern, stated plainly.** The plan already frames the sentinel as a mitigation
around upstream behavior rather than a native guarantee. This receipt confirms that framing is
correct and that the mitigation is **load-bearing**: with the sentinel removed, the gateway
holds stored provider credentials behind an unauthenticated runtime API, and an anonymous
caller can spend them. Ordinary token deletion, a database restore, or any operation that
empties the token store reproduces that state without warning. If Codexify's multi-user
credential infrastructure depends on this, the dependency rests on a store count, not on a
fail-closed guarantee.

## Two operational landmines the plan did not anticipate

### 1. `docker compose restart` does not re-read `env_file`

Observed directly: after editing the secret file and running `docker compose restart`, the
running container still reported the **old** `OOMOL_CONNECT_ALLOWED_ACTIONS`, and a credentialed
action was denied with `action_not_allowed`. Only `docker compose up -d --force-recreate` applied
the new value.

This matters because the plan's §2.7 procedure says "restart" for routine changes and
"recreate" only for upgrades. **A restart silently ignores configuration changes.** The plan's
restart procedure is wrong as written, and the failure mode is silent — the container reports
healthy while enforcing the previous policy.

### 2. Connection selection and connection grants use *different* id forms

Observed at runtime:

| Surface | Value |
| --- | --- |
| `GET /api/connections` (admin) → `id` | `1ec84993-ce7b-42cc-9848-97c44424862c` (UUID) |
| `allowedConnections` grant must contain | the **UUID** — `service:name` was rejected with `connection_not_allowed` |
| Selector: `x-oo-connector-app-id` header | UUID — **works** |
| Selector: `x-oo-connector-alias` header | alias — **works** |
| Selector: `connectionName` body field | alias — **works** (and is stripped from action input) |
| Selector: `connectionId` body field | **does not work** — silently denied as `connection_not_allowed` |
| Action input | goes under an **`input`** wrapper — a flat body fails with `invalid_input` |

The `connectionId` body field is the trap: it is present in upstream's internal action-runner
input type, it is **not** wired for HTTP body selection, and using it produces a
`connection_not_allowed` denial that reads like a permissions problem rather than a malformed
request. An adapter that copies upstream's internal field names would ship this bug.

## Host scratch cleanup

The gateway itself — container, encrypted volume, and network — was destroyed and verified
absent. The trial's *scratch artifacts* could not be removed by the executing sandbox and
remain on disk. This is reported rather than worked around, and is an explicit outstanding
hygiene item.

**What blocks it.** The sandbox permits file creation in `/private/tmp` and `$HOME` but denies
`unlink` in both (EPERM), and denies a trash move with EXDEV on the `/Volumes/Dev_SSD`
volume. Deletion inside the worktree works, but `mavis-trash` cannot move files from that
volume to the trash either. No recoverable deletion path was available for the original
locations. Permanent deletion was **not** used.

**What was done instead.** All 23 trial artifacts — including copies of the disposable secret
files — were consolidated into a single directory inside the worktree:

```text
.gate-a-cleanup/          # 23 files, excluded from git via .git/info/exclude
```

The exclusion is recorded in `.git/info/exclude`, which is **local git configuration, not a
tracked file**, so the working tree stays clean and no scratch artifact can be staged
accidentally. `git status` was verified empty after the move.

**Why this is not urgent.** The gateway volume is destroyed. The admin token and encryption
key in those files protect a database that no longer exists, and the hashed token store went
with it. The values are **cryptographically inert**. They are a hygiene concern, not a live
exposure — and nothing reached the repository.

**To complete the cleanup with host permissions:**

```bash
cd /Volumes/Dev_SSD/Codexify-main/.worktrees/mcode-31b4bff7-5ff0-43f7-9879-7e88f1405a8e
rm -rf .gate-a-cleanup /tmp/gate-a /tmp/oc-verify
```

## Additional findings

**Provider error text is passed through verbatim.** The `aeroleads` rejection reached the
client as `invalid_input` with the provider's own message intact (*"User not Found, Please Pass
Valid Api Key"*). Two consequences: upstream's provider-auth failures are **not** classified as
`credential_expired` / `scope_missing` as the plan's §3.6 mapping assumed — they arrive as
`invalid_input`; and raw provider text reaches the runtime API response. The adapter must
classify and sanitize before anything reaches a model or a Connections projection.

**Credential verification is enforced at connection time.** Every provider probed with a
fabricated key rejected it (`credential_verification_failed`, `unsupported_auth_type`). Two
providers (`aeroleads`, `agility`) accept an `api_key` without verification and were used for
the isolation and encryption tests. This is good hygiene — but it means the trial could not
exercise a genuinely *verified* credential, and a real provider read with a live credential
remains unproven.

**The admin surface is correctly separated.** `/api/*` required the admin bearer throughout,
including while the runtime surface was unauthenticated.

## What this receipt does not establish

- **No Guardian integration was built or exercised.** No adapter, route, Command Bus
  registration, catalog entry, migration, or Settings change exists.
- **No ADR was opened or amended**, including the §4.7(a) delegated credential-vault question
  that Gate B requires.
- **No real provider credential was used.** The only live provider calls were the `no_auth`
  Hacker News action and one call that reached a real provider and was rejected by it.
- **The exploit was demonstrated, not weaponized.** The anonymous caller was a harness running
  **inside the gateway container** on the private network, against a **fabricated** credential,
  with the gateway publishing **no host ports**. The finding establishes that the *path* is
  complete; it does not establish that the gateway was reachable by an unauthorized party, and
  it involved no real credential.
- **No live OAuth flow.** The remote callback posture remains undecided (§4.7(b)).
- **No multi-user qualification at Codexify scale.** Two synthetic accounts were used inside
  one gateway instance.
- **No trigger execution was permitted**, so trigger *behavior* is unproven even though trigger
  *denial* is proven.
- **Server-side cancellation classification was not observed.** A client-side abort produced
  `AbortError`; upstream's `execution_cancelled` path was not exercised.
- **The substrate was not tested under PostgreSQL** — the trial used SQLite, as the plan
  specified.
- **No conclusion about the version's fitness beyond v1.9.4**, and no basis for a release or
  support claim.

## Candidate 1 — the undistributed runtime authentication guard (tested)

**The native candidate, tested before building an external proxy or considering a fork.**

`OOMOL_CONNECT_RUNTIME_TOKEN` has two properties that matter together. In upstream's
`hasValidToken`, the permissive zero-token branch is reached only when **no** runtime token is
configured. When one *is* configured, a request must either present that bearer or satisfy
`hasValidRuntimeToken`, which resolves persistent `oct_...` tokens **and their scoped grants**.

**Candidate:** configure a high-entropy runtime token **solely as an authentication-enforcement
secret**. Never distribute it to Guardian, users, models, or runtime clients. Continue using
individually scoped persistent tokens for actual execution.

**First, a constraint that narrows the field.** Upstream's auth middleware accepts a
`requireRuntimeAuth` option that would enforce authentication with no tokens at all — and it is
**not reachable** at v1.9.4. The complete `OOMOL_CONNECT_*` environment surface read from
`src/server/index.ts` is 31 variables; `requireRuntimeAuth` is not among them, it does not
appear in the server entry at all, and `npm start` runs `node src/server/index.ts` directly with
no flag to set it. It is an in-process option only. **`OOMOL_CONNECT_RUNTIME_TOKEN` is therefore
the only native, configuration-only lever that makes the condition fail closed.**

### The four required observations

| Observation | Result |
| --- | --- |
| **Zero stored tokens** → anonymous denied | **PASS** — `GET /v1/actions` → HTTP **401**; anonymous `POST` of the credentialed action → HTTP **401** `unauthorized` |
| **Scoped user token** → own grant allowed | **PASS** — user-a's token on user-a's connection reached the **provider layer** (provider rejected the fabricated key), not `connection_not_allowed` |
| **Cross-user attempt** → foreign grant denied | **PASS** — user-a's token → user-b's connection → HTTP **403** `connection_not_allowed`; user-a's token → user-b's action → HTTP **400** `action_not_allowed` |
| **Delete final user token** → anonymous still denied | **PASS** — store reduced to **0**, anonymous `GET /v1/actions` → HTTP **401**, anonymous credentialed action → HTTP **401** |

The fourth observation is the one the sentinel could not provide natively. **The candidate
achieves fail-closed behavior by configuration, with no stored-row dependency at all.**

### The trade-off, measured rather than asserted

The candidate's cost is real and was confirmed by a controlled pairing — **same action, same
service, same valid input; only the connection differs**, against a third connection on the
same provider (`aeroleads/user-c`):

| Bearer | Target connection | Result |
| --- | --- | --- |
| user-a's **scoped** token | user-c | HTTP 403 `connection_not_allowed` |
| the **guard** bearer | user-c | HTTP 400 — **provider-level rejection** |

**The guard bypasses per-connection grants.** Its holder can reach any stored connection and any
deployment-allowed action, with no per-user grant applied. The candidate therefore trades a
dependency on a **database row count** for a dependency on a **privileged deployment secret** —
exactly the trade the review anticipated.

**Scope of the guard, measured:**

| Surface | Result |
| --- | --- |
| Runtime action execution (`/v1/actions/*`) | Authorized (bypasses per-user grants) |
| MCP (`POST /mcp`) | Authorized — HTTP 200 on `tools/list` |
| Admin surface (`/api/*`) | **Not** authorized — HTTP 401. The guard is **runtime scope only**. |

**No leakage.** The guard value did not appear in the container logs, the persisted run log, or
any response body. It is also never placed in a request, an argument, a result, or a projection.

### Operational requirements — the guard is only as good as its enforcement

A fail-closed secret that can be silently dropped is not fail-closed. Three requirements were
therefore tested:

**Detection before deployment.** A guard-aware preflight was written and behavior-tested across
six cases:

| Case | Result |
| --- | --- |
| Guard present, distinct from the admin token, ≥32 chars | **PASSED** |
| Guard key missing | REJECTED — missing or empty |
| Guard key present but empty | REJECTED — missing or empty |
| Guard shorter than 32 characters | REJECTED — too weak to be an enforcement secret |
| Guard equal to the admin token | REJECTED — role separation violated |
| Wildcard in the action allowlist | REJECTED — not exactly the approved actions |

**`env_file` recreate behavior makes configuration verification mandatory.** The plan's earlier
finding — that `docker compose restart` does **not** re-read `env_file` — was confirmed in the
fail-unsafe direction with the guard specifically:

| Sequence | Result |
| --- | --- |
| Guard added to the secret file, then **restart only** | Guard **still absent** in the running container; anonymous `/v1` → **HTTP 200, window open**; container reported **healthy** |
| Guard added, then **recreate** | Guard present (73 chars); anonymous `/v1` → **HTTP 401, fail closed**; the upstream `runtime API authentication is disabled` startup warning was **absent** |

So an operator who adds the guard and runs `restart` believes the gateway is fail-closed when it
is not, and nothing reports the difference. **A post-start assertion that the guard is present in
the *running container* is therefore a mandatory part of the deployment, not an optional
verification.** The stale-config direction is fail-safe (a leftover guard keeps authentication
closed); the add-without-recreate direction is fail-unsafe.

### Assessment

The candidate is a **genuine simplification** of the sentinel: it removes the sentinel's
security responsibility entirely, replaces a database-row invariant with a deployment-secret
invariant, needs no extra service and no fork, and does not depend on a future upstream release.

It is **not** a free guarantee. It introduces a **privileged master bearer** whose leak bypasses
every per-user connection grant. Whether that is acceptable is an architecture decision, not a
technical one — and it is exactly the decision the §4.7(a) ADR amendment would have to record.
Its operational burden is a preflight rule and a post-start assertion; its residual risk is
concentrated in a single secret whose custody, rotation, and non-distribution must be specified.

**What this receipt does not settle:** whether Codexify's multi-user credential model can accept
an unrestricted master bearer existing at all, and whether the guard can be rotated without a
window (a rotation invalidates the old bearer before the new one is live — the ordering
implications are untested).


The fail-closed question is **prior to** the ADR amendment, because the amendment's content
depends on its answer. Writing §4.7(a) first would normalize the sentinel workaround as
accepted doctrine before anyone has established that a better boundary exists.

> **Can Codexify establish a fail-closed authentication boundary that is independent of
> OpenConnector's token-store count, without taking on unreasonable operational complexity?**

| | |
| --- | --- |
| **Desired invariant** | Runtime requests require authentication **regardless of token-store contents**. |
| **Observed implementation** | Runtime requests require authentication only while certain mechanisms are configured — **including the presence of at least one stored token**. |
| **Codexify mitigation** | Keep a permanently stored, deliberately powerless token so the implementation continues enforcing authentication. |
| **Status** | Operationally workable in the tested scenario. **Not the same guarantee.** |

A database restore, an administrative mistake, or a token-lifecycle defect could change the
security posture **without changing a single line of application configuration** — and, as the
exploit test shows, the consequence is not merely exposure but **credential spending**.

**Candidate boundaries to evaluate.** None may be assumed cheap or sufficient without proof:

- **An undistributed runtime authentication guard** — `OOMOL_CONNECT_RUNTIME_TOKEN` configured
  as a high-entropy enforcement secret, never distributed, with scoped persistent tokens still
  used for execution. **Tested above: it satisfies the required invariant by configuration**, with
  no stored-row dependency, no extra service, and no fork. Its cost is a privileged master
  bearer that bypasses per-user connection grants.
- A **narrowly scoped external authentication boundary** in front of the gateway — a component
  that enforces authentication independently of the gateway's own store, so that the gateway's
  empty-store condition is no longer reachable by an unauthorized caller. Not yet evaluated.
- An **upstream fix** — a change to upstream's runtime-authentication logic that makes the
  condition fail closed. Cost, maintainability, and upstream's own security-fix window (latest
  release and `main` only) all bear on whether this is a real option. Note that upstream's
  `requireRuntimeAuth` option already expresses the desired semantics but is **not reachable
  from configuration** at v1.9.4.
- **A permanent fork** — available, but it converts a commodity substrate into a
  Codexify-maintained fork, which **undermines the original objective** of adopting a
  maintained connector ecosystem. It should be the last resort, not a default.

**Decision rule.** If a reliable, maintainable enforcement boundary is **not** available at
acceptable complexity, then **reject OpenConnector for Codexify's multi-user credentialed
integration** rather than write an ADR that normalizes the sentinel workaround. A rejection at
this stage is a good outcome: it is cheaper than discovering this inside Codexify's
multi-user credential infrastructure.

**This decision opens no ADR and starts no Gate B work.** It is recorded here as the gating
question, and it is the only thing that should move next. The guard candidate has now been
tested and satisfies the invariant; **the remaining question is not technical but architectural —
whether Codexify's credential model can accept an unrestricted master bearer existing at all.**

## Recommendation

**Do not proceed to Gate B preparation until the adoption decision above is answered.**

1. **Answer the fail-closed boundary question first.** The **undistributed runtime
   authentication guard** has now been tested and satisfies the required invariant by
   configuration alone — no stored-row dependency, no extra service, no fork, no dependence on a
   future upstream release. The remaining question is architectural: **whether Codexify's
   credential model can accept an unrestricted master bearer existing at all.** That is a
   judgement about Codexify's threat model, and it is the input §4.7(a) needs. If the answer is
   no, the external authentication boundary becomes the next candidate — and if that also fails,
   the dependency is rejected.
2. **Correct the plan's operational procedures** as Gate B preparation inputs, to be applied
   when Gate B preparation is authorized: `env_file` changes require **recreate**, not restart;
   the adapter must use the correct connection-id form and the `input` body wrapper, and must
   **not** send a `connectionId` body field.
3. **Classify provider errors defensively.** Upstream surfaces provider auth failures as
   `invalid_input` and passes provider text through; the adapter must map these to bounded
   Codexify outcomes itself.
4. **Specify the guard's custody if it is adopted.** Non-distribution, rotation ordering (the
   untested part), preflight enforcement, and a **post-start assertion that the guard is present
   in the running container** — the last is not optional, because `restart` silently ignores
   `env_file` changes.
5. **Re-run the revoked-token scenario against a real provider credential** when one is
   authorized, since the trial's credentialed path used an unverified key.

**Rejection remains a legitimate outcome.** If the boundary question cannot be answered
affirmatively, the correct decision is to reject the dependency, and this receipt is the
evidence that would justify it.

The document is now the evidence rather than the plan. Further prose refinement is not
warranted; the remaining uncertainty is in the substrate's behavior under a real provider
credential and under Codexify's own lifecycle operations.

## Responsible disclosure

**This receipt is not cleared for publication.** It documents a reproducible unauthorized
credential-backed execution path in a currently-supported upstream release, and the details are
specific enough to be actionable. Upstream's `SECURITY.md` asks that vulnerabilities be reported
**privately** and kept private until a fix is released — it targets publication within 90 days,
and faster for actively exploited issues.

The report should go to upstream's **private** channel before any of this is published:

1. **GitHub private vulnerability reporting (upstream's preferred channel)** — the repository's
   **Security** tab → **Advisories** → **Report a vulnerability**.
2. **Email** — `support@oomol.com`, if private reporting is unavailable.

Upstream asks that reports **not** include secrets, credentials, or customer data; every value
in this receipt is a disposable placeholder. Upstream also commits to acknowledgement within 3
business days, to coordinating a fix before disclosure, and to crediting the reporter in the
advisory unless asked not to.

**Until upstream has responded, the branch stays unpushed and this receipt stays local.** The
Gate A commits are on a local branch only; nothing has been pushed to `origin`, and no release
posture, current-state document, or support claim has been widened.
