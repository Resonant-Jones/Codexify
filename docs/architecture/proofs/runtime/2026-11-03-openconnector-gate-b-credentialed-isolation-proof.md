# OpenConnector Gate B Slice 5 — live credential-bearing isolation receipt

Date: 2026-11-03

Slice under test: `3824262ef` plus the one reviewed credential-bearing
allowlist entry added by this slice. No adapter, authority, router, or
transport logic was changed: the committed source diff for this slice is the
reviewed action entry, its module documentation, and tests. No production
behavior outside the new entry was modified.

Plan: [`docs/architecture/openconnector-integration-plan.md`](../openconnector-integration-plan.md)
(Gate B section updated by this slice; Gate B not marked complete).

## Verdict

**PASS on all isolation criteria (1–10, 12); criterion 11 (verified
teardown) PENDING.** Two distinct Guardian accounts each used only their
own credential-bearing OpenConnector connection through the existing
Guardian execution path, and every cross-account, empty-grant, revoked,
unknown, and revalidation case failed closed with zero unauthorized
provider execution. Final teardown (`docker compose down -v` plus absence
checks) was approval-gated at commit time — see §6 — and must be recorded
before this slice counts as fully closed.

## 1. Reviewed credential-bearing action (requirement 1)

`aeroleads.get_details_from_linkedin_url` (provider `aeroleads`).

Source anchors (pinned upstream commit `d89dc9f24f5a057bb500272d7dbf333837c77c68`,
verified inside the pinned image, same digest as the trial gateway):

- `src/providers/aeroleads/actions.ts` — declares
  `operationType: "read"`; input is a single required `linkedin_url` string;
  output is the normalized enrichment payload.
- `src/providers/aeroleads/executors.ts` — the handler builds
  `GET https://aeroleads.com/api/get_linkedin_details` with the API key and
  the LinkedIn URL as query parameters (`method: "GET"`). No other provider
  call exists on this path, so the action cannot mutate remote state.
- `src/providers/aeroleads/definition.ts` — credential class `api_key`
  (sent as the `api_key` query parameter); no scopes (`grantedScopes: []`).
- `src/providers/aeroleads/executors.ts` (`credentialValidators`) —
  `validationMode: "format_only"`: any non-empty key is accepted at
  connection time with no live verification. Disposable fake credentials
  therefore exercise the full grant machinery without a real provider
  account, and there is no account to bill.

Test input was the documentation-style URL
`https://www.linkedin.com/in/example` (no real person, no real credential).
With the fake key the provider rejects authentication, which is the
anticipated shape: Guardian authorizes, the gateway accepts the scoped
selection, the provider rejects the credential — three distinguishable
layers, and the denial is never labeled a successful read.

Policy change: exactly this action appended to the production allowlist as
`EXPLICIT` + `credential_bearing=True`. It inherits the existing
internal-only route posture; no catalog entry, no other action, no provider
broadening.

## 2. Trial topology and deployment (requirements 2, 6)

| Property | Value |
| --- | --- |
| Gateway image (inspected on the running container) | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c` |
| Container / network / volume | `codexify-openconnector-gateb5` / `codexify_openconnector_gateb5` / `codexify_openconnector_gateb5_data` (disposable) |
| Health | Container `healthy`; `GET /health` → `{"ok":true}` |
| Listener | Exactly one: `TCP 127.0.0.1:12775 (LISTEN)` on the Docker backend. No `0.0.0.0`, external, or IPv6 listener (accepted trial deviation; production target unchanged: no published ports) |
| Guard | Preflight passed; `OOMOL_CONNECT_RUNTIME_TOKEN` asserted PRESENT in the running container (presence only) |
| Deployment allowlist | Exactly `hackernews.get_top_stories,aeroleads.get_details_from_linkedin_url` |
| Proxies / triggers / SSRF | Blocked `*` / blocked `*` / default guard posture |
| Admin surface | Loopback-only, admin-token protected |
| Codexify production | No production container, network, volume, credential, or database touched |

Accounts (synthetic, local-only): `iso-acct-a` and `iso-acct-b` in the
qualification harness, each with its own Guardian binding, its own
connection UUID, its own scoped token, and a grant naming only its own
connection. Nothing shared. Deployment guard and admin token never left
their infrastructure/operator roles.

Connections (created via `POST /v1/connections/aeroleads/connect/api-key`
with disposable fake keys; names are gateway-assigned UUIDs):

- Account A: `8375b06f-98ec-4c40-8cf5-0f0458ba14ae`, `status: active`,
  `authType: api_key`
- Account B: `bdb58eae-46f4-4727-a06a-c990f72ce3f6`, `status: active`,
  `authType: api_key`

Tokens: `gateb5-sentinel` (grants nothing), `gateb5-account-a`
(`allowedActions: [aeroleads.get_details_from_linkedin_url]`,
`allowedConnections: [<uuid-a>]`), `gateb5-account-b` (mirror). Store
observed non-empty at every step.

## 3. Integration path (requirement 3, 5)

Order preserved: reviewed allowlist → Guardian permission profile (API-key
account session, provider/action grant) → account-owned binding → explicit
connection selection (request may only narrow the binding's grant) →
scoped-token resolution → execution-time revalidation → dispatch over real
HTTP (`HttpxGatewayClient`) to the gateway. No model-supplied token,
connection, alias, account, or provider input exists on the route or the
authority object.

## 4. Isolation matrix (requirement 4)

`A`/`B` = accounts with own connection/token; dispatched = Guardian→gateway
HTTP dispatches observed by the instrumented (not substituted) transport.

| Case | Guardian outcome | Dispatched | Gateway | Provider execution |
| --- | --- | --- | --- | --- |
| A. A invokes own connection | `failed` / `provider_rejected` (502) | 1, selector = uuid-a, scoped Bearer [REDACTED] | accepted selection | reached; rejected fake credential (expected shape) |
| B. B invokes own connection | `failed` / `provider_rejected` (502) | 1, selector = uuid-b, scoped Bearer [REDACTED] | accepted selection | reached; rejected fake credential |
| C. A attempts B's connection | denied / `connection_not_granted` | 0 | not contacted | none |
| D. B attempts A's connection (gateway-level probe) | n/a (raw HTTP) | n/a | 403 `connection_not_allowed` | none |
| E. A presents unknown connection | denied / `connection_not_granted` | 0 | not contacted | none |
| F. A's grant empty/absent | denied / `missing_profile` at revalidation | 0 | not contacted | none |
| G. A's binding revoked | denied / `missing_profile` at revalidation | 0 | not contacted | none |
| H. Authority revoked between check and dispatch | denied at revalidation (2 evaluations observed) | 0 | not contacted | none |
| I. A's token against B's connection | 403 `connection_not_allowed` (gateway grant) | 1 (rejected) | denied | none |
| J. Guard as fallback | no code path reads or presents it; every live dispatch ran under a grant-checked scoped Bearer [REDACTED] per case I's discriminator (a master Bearer [REDACTED] bypass the grant and would not have been denied) | — | — | none |

Guardian denial (`connection_not_granted`, `missing_profile`) and gateway
denial (`connection_not_allowed`) are distinguishable codes on
distinguishable layers; neither substitutes for the other. A Guardian denial
with zero dispatch is not claimed as gateway evidence — cases D and I prove
the gateway grant independently. No existence oracle: denials reveal no
credential material and no confirm/deny signal beyond the bounded code.

Committed execution:
`tests/connections/test_openconnector_credentialed_isolation.py` —
12 passed (5 synthetic always-run + 7 live, env-gated, executed here with
`GATEB_LIVE=1` against the trial gateway).

## 5. Sanitization (requirement 7)

Dispatch-level observation throughout (counts above). Timeouts: none
observed; unknown-outcome semantics untouched in code. Automated scan of the
live response bodies and recorded dispatch metadata for both scoped token
values: **0 matches**; fake-credential prefix absent. Provider rejection
recorded as the bounded `failed` / `provider_rejected` outcome; raw provider
text is dropped by the transport and quoted nowhere in evidence. This receipt
contains digests, ids, names, statuses, codes, and shapes only.

## 6. Cleanup (requirement 8)

- Disposable runtime tokens revoked (both `200`); store observed back to
  sentinel-only. Both revoked token values are therefore inert.
- Temporary secret files and scratch (`/private/tmp/gate-b-isolation/`)
  removed and verified absent.
- Trial connections: no per-connection deletion endpoint exists in the
  pinned source's route table, so removal rides on destroying the encrypted
  volume (below).
- **PENDING at commit time (approval-gated): container
  `codexify-openconnector-gateb5`, volume
  `codexify_openconnector_gateb5_data`, network
  `codexify_openconnector_gateb`, and the `127.0.0.1:12775` listener.**
  Docker control required a human approval that was unavailable when the
  session's approval prompts became disabled, so `docker compose down -v`
  and the absence re-verification could not run. Containment in the interim:
  loopback-only listener, revoked tokens, fake-only credentials in the
  gateway's encrypted store, no production data of any kind. The follow-up
  teardown (`docker compose down -v`, absence checks) must be recorded
  before criterion 11 counts as verified.
- No Codexify resource was created, modified, or deleted at any point.

## 7. Validation performed

- `pytest -v tests/connections/test_openconnector_adapter.py`
- `pytest -v tests/connections/test_openconnector_router.py`
- `pytest -v tests/connections/test_openconnector_credentialed_isolation.py`
  (12 passed live in trial; skips cleanly without `GATEB_LIVE=1`)
- Regression: `pytest -v tests/connections/ tests/command_bus/` (unrelated
  sandbox-blocked socket tests recorded as environmental, not isolation
  results)
- `make docs PYTHON=python3`, `git diff --check`, `git diff --stat`,
  `git status --short`
- Public OpenAPI path set unchanged (no route added, moved, or re-exposed;
  OpenConnector route still internal-only); legacy `connectors` route still
  quarantined in the supported profile.

## 8. ADR assessment

Aligned: ADR-071 and ADR-094 delegated-custodian amendments (Guardian sole
authority; custodian enforces its own grants and refuses without granting
access), ADR-024 bounded outcomes, ADR-075 catalog/Command Bus boundary (no
catalog entry added), ADR-077 (provider credentials never entered an
untrusted environment — they traveled only gateway-side), ADR-092 (scoped
account tokens never substituted with deployment/operator credentials; the
guard was never presented). No invariant changed; no new ADR needed.

## 9. Limitations

- Fake provider credentials: proves isolation of selection and grants, not
  successful provider reads or verified-credential behavior.
- Synthetic Guardian accounts and injected resolver/authorizer: durable
  binding persistence, lifecycle, and recovery remain Gate C.
- Loopback-only listener: production-network posture unqualified.
- Hosted `public_allowlist` callability, Gate B completion, and release
  support: unchanged and unqualified.

## 10. Methodology notes (harness, not product)

- `tests/conftest.py` force-sets `GUARDIAN_API_KEY=test-api-key`; trial
  Guardian auth follows that convention — a harness detail, not a product
  finding.
- The committed live recorder pins a real `httpx.AsyncClient` per recorder
  and the route-level tests hold one entered `TestClient` portal per test:
  without this, a shared HTTP pool strands connections across per-request
  event loops under pytest (`Event loop is closed` on the second dispatch).
  Both patterns are documented in the test file.
