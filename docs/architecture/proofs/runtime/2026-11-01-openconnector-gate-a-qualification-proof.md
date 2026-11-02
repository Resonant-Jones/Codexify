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

**CONDITIONAL PASS** — with one **P1 substrate defect confirmed**, and two operational
landmines that the plan did not anticipate.

The gateway does what the plan needs it to do, and the plan's central security properties
hold **when the plan's own discipline is followed**: an explicit non-empty grant per token,
and a token store that is never empty. But the substrate does **not** provide fail-closed
authentication on its own. Its runtime-authentication state is a **side effect of a store
count**, re-derived on every request. Every mitigation this receipt relies on is Codexify
discipline layered on top of upstream behavior, and two of them are load-bearing enough that
getting them wrong is silent.

**Nothing here authorizes Gate B.** Per the plan's own sequencing, Gate B additionally requires
the §4.7(a) delegated credential-vault ADR amendment, which has **not** been opened.

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

**Confirmed at source and reproduced at runtime.**

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

**What this means for the plan.** The plan's standing invariant (§5.1.1) is correct and
necessary, and the sentinel token works: with it present, deleting every user token left the
store non-empty and unauthenticated `/v1` rejected. But the property being defended is
**"authentication is currently enforced,"** not "authentication is configured" — and it is
re-derived per request, so it can vanish **silently**. A Codexify implementation that treats
"we created a token at bootstrap" as sufficient would be wrong.

**Adoption concern, stated plainly.** The plan already frames the sentinel as a mitigation
around upstream behavior rather than a native guarantee. This receipt confirms that framing is
correct and that the mitigation is **load-bearing**: with the sentinel removed, the gateway
holds two stored provider credentials behind an unauthenticated runtime API. Ordinary token
deletion, a database restore, or any operation that empties the token store reproduces that
state without warning. If Codexify's multi-user credential infrastructure depends on this, the
dependency rests on a store count, not on a fail-closed guarantee.

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

## Recommendation

**Proceed to a bounded Gate B preparation, not to Gate B itself.** Specifically:

1. **Resolve §4.7(a) first.** The delegated credential-vault ADR amendment is the gate, and it
   should now be written against the *measured* reality of the sentinel: the property is a
   store count, not a fail-closed guarantee. The amendment should say so plainly.
2. **Correct the plan's operational procedures** before any implementation work: `env_file`
   changes require **recreate**, not restart; and the adapter must use the correct
   connection-id form and the `input` body wrapper, and must **not** send a `connectionId`
   body field.
3. **Classify provider errors defensively.** Upstream surfaces provider auth failures as
   `invalid_input` and passes provider text through; the adapter must map these to bounded
   Codexify outcomes itself.
4. **Keep the sentinel**, and consider whether Codexify's own lifecycle code should *refuse*
   the last-token deletion rather than rely on an operator remembering.
5. **Re-run the revoked-token scenario against a real provider credential** when one is
   authorized, since the trial's credentialed path used an unverified key.

**Rejection remains a legitimate outcome.** If the ADR amendment cannot establish a
credential-custody model that does not depend on a store count — or if Codexify's multi-user
requirements demand a fail-closed guarantee the substrate cannot provide — **the correct
decision is to reject the dependency**, and this receipt is the evidence that would justify it.

The document is now the evidence rather than the plan. Further prose refinement is not
warranted; the remaining uncertainty is in the substrate's behavior under a real provider
credential and under Codexify's own lifecycle operations.
