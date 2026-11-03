# OpenConnector Gate B — live read-crossing qualification receipt

Date: 2026-11-03

Slice under test: `3824262ef` (reviewed no-auth execution mode) on branch
`mcode/31b4bff7-5ff0-43f7-9879-7e88f1405a8e`. No production source change was
made for this qualification; the implementation is exercised as committed.

Plan under evaluation:
[`docs/architecture/openconnector-integration-plan.md`](../openconnector-integration-plan.md).

## Verdict

**PASS** — one real, bounded execution path was established and observed:

Command Bus (`op::openconnector_execute_read_action`)
→ Guardian internal-only route
→ Guardian authorization with execution-time revalidation
→ OpenConnector adapter (Slice 3 no-auth mode, selector omitted)
→ OpenConnector v1.9.4 runtime over real HTTP
→ live Hacker News API
→ bounded, sanitized Guardian result.

All twelve acceptance criteria in the task spec are met. Gate B as a whole
remains **open**: catalog entry, durable binding/grant stores, recorded
allowlist review, and credential-bearing isolation are still outstanding, and
nothing here widens release posture (`00-current-state.md` unchanged, release
gate still `HOLD`).

## Environment

| Property | Value |
| --- | --- |
| Gateway image | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c` |
| Running image (inspected) | Identical digest to the pin |
| Container / network / volume | `codexify-openconnector-gateb` / `codexify_openconnector_gateb` / `codexify_openconnector_gateb_data` (all disposable, since removed — see Cleanup) |
| Health | `GET /health` → `{"ok":true}`; container health `healthy` |
| Listener | Exactly one: `TCP 127.0.0.1:12774 (LISTEN)`, held by the Docker backend. No `0.0.0.0`, no external interface, no externally reachable IPv6 line observed |
| Trial deviation | Loopback-only publication, recorded here as a qualification affordance. The governing topology (separate Compose project, no published ports) is unchanged |
| Codexify containers/networks | Unmodified; verified no attachments to the trial network |
| Secrets custody | Fresh trial-only values in `/private/tmp/gate-b-crossing/` (outside the repository), directory mode `0700`, secret files mode `0600` |
| Codexify/production accounts used | None. Synthetic local account `gateb-trial-account` only |
| Production provider credentials | None stored, none used |

## Deployment posture (requirement 1–2)

- Fail-closed preflight (plan §2.5: required keys present, guard ≥32 chars and
  distinct from the admin token, allowlist exactly
  `hackernews.get_top_stories`, no wildcard): **PASSED** before startup.
- Post-start assertion: `OOMOL_CONNECT_RUNTIME_TOKEN` **PRESENT** in the
  running container (presence only; value never printed or logged).
- Deployment restrictions in force: proxies blocked (`*`), triggers blocked
  (`*`), allowlist exactly the one reviewed action, SSRF guard default.
- Bootstrap order (plan §2.4): unauthenticated `/v1/actions` → **401** with
  the guard configured and an empty store; sentinel `gateb-sentinel` created
  (grants nothing); working token created with grant
  `allowedConnections: ["hackernews:default"]`,
  `allowedActions: ["hackernews.get_top_stories"]`; store observed
  `{gateb-sentinel, gateb-trial-account}` (size 2); unauthenticated `/v1`
  re-asserted **401**; sentinel executing the action →
  `action_not_allowed` (400); invalid bearer → **401**.
- Overlapping handoff (plan §5.1.1): successor `gateb-trial-account-2` with
  the identical grant was created, verified executing (200, no selector), and
  only then was the predecessor revoked. Final store
  `{gateb-sentinel, gateb-trial-account-2}`; unauthenticated `/v1` still
  **401**. The store was never empty.
- Admin connection inventory: **31 rows, all built-in virtual no-auth
  templates** (one per no-auth provider), **0 rows carrying credential
  material**. `hackernews:default` present with no auth type — the virtual
  identity Slice 3 binds.

## Guardian authority (requirement 3)

The harness used the existing Guardian machinery end to end: API-key account
session (`require_account_session` + `get_account_user_scope`), provider from
the reviewed allowlist entry, Guardian-owned synthetic binding (account,
provider `hackernews`, virtual identity `hackernews:default`, non-empty
scoped grant, token reference), separate granting authorizer, and the
permission-profile evaluation with pre-dispatch revalidation. The deployment
guard and admin token were never presented by any Guardian path. The scoped
Bearer [REDACTED] sent; the upstream selector was omitted solely under the reviewed
no-auth classification.

## Command Bus crossing (requirement 4)

| Transport | Form |
| --- | --- |
| Command Bus → Guardian route | In-process ASGI loopback executing the real path rendering, forwarded headers, routing, auth dependencies, and route handler (the pattern pinned by `test_command_bus_invokes_the_internal_route`) |
| Adapter → gateway | Real TCP HTTP to `http://127.0.0.1:12774` via the production `HttpxGatewayClient` |
| Gateway → provider | Real external Hacker News API call by the gateway |

- Manifest entry on the live app object: `op::openconnector_execute_read_action`,
  `GET /api/guardian/connections/openconnector/actions/{action_id}`,
  `read` / `read_only` / `safe` / `none`.
- The route path is **absent** from the public OpenAPI projection of the same
  app object.
- Under the hosted `public_allowlist` posture the route returns **403** with
  zero dispatches (N9). No bypass, separate ingress, or exemption was
  introduced.

## Positive live evidence (requirement 5)

- Invoke `POST /api/guardian/commands/invoke` → HTTP 200, result `completed`.
- Guardian bounded outcome: `success` / `ok`, `truncated: false`.
- Exactly **one** gateway dispatch: `POST
  http://127.0.0.1:12774/v1/actions/hackernews.get_top_stories`, headers
  `accept, authorization, content-type`; **scoped Bearer [REDACTED] (boolean
  observed, value never captured); `x-oo-connector-app-id` absent**; body 12
  bytes (`{"input":{}}`).
- Live provider result: `data.story_ids` is a list of **500 live Hacker News
  story ids** (sample `50351111, 50341174, 50351319, 50327088, 50349276`),
  with gateway `executionId` and `auditPersisted: true`.
- Returned payload **5204 bytes**, under the adapter bound, untruncated.
- No mocking anywhere on the path: the ids are live provider data, not
  fixtures.

## Negative evidence (requirement 6)

Every case used the existing implementation with dispatch counting. Route
cases went through the live-mounted route; adapter cases used the committed
adapter with the live service object but were denied before transport.

| Case | Result | New dispatches |
| --- | --- | --- |
| N0 bad API key | 401, refused before routing | 0 |
| N1 unapproved action | 403 `action_not_approved` | 0 |
| N2 missing Guardian permission | 403 `missing_profile` | 0 |
| N3 revoked binding | 403 `missing_profile` (see note) | 0 |
| N4 missing scoped runtime token | 403 `runtime_token_unavailable` | 0 |
| N5 empty Guardian grant | 403 `missing_profile` (see note) | 0 |
| N6 named connection on a no-auth action | `connection_not_selectable` | 0 |
| N7 credential-bearing action with empty grant | `connection_grant_empty` — denied, never downgraded to selector omission | 0 |
| N8 gateway unreachable (closed loopback port) | `unavailable` / `gateway_unreachable`, `dispatched: true` (unknown outcome, never "did not happen") | n/a (failed transport) |
| N9 hosted `public_allowlist` posture | 403 | 0 |

**Note on N3/N5 codes.** Revocation and empty grants are caught by the
permission-profile revalidation (`_binding_is_eligible`) before the adapter's
binding check, so the observed code is `missing_profile` rather than
`binding_not_authorized` / `connection_grant_empty`. Both layers deny and both
default closed; the property under test — revoked or empty authority cannot
dispatch — holds with zero dispatches either way. The adapter-level codes are
pinned separately by the committed synthetic suite.

**Methodology finding (harness, not product).** A first version of the trial
harness constructed its gateway transport after installing the Command Bus
ASGI loopback patch, which replaces `httpx.AsyncClient` module-wide; adapter
traffic would then have looped back into the test app instead of crossing
TCP. This was caught because the dead-port probe returned a 404 instead of a
connection failure. The harness was fixed to pin the real client class before
patching, and the full run above (including the positive crossing) executed
after the fix. The committed regression suite never had this shape — its
transports are injected fakes — so it is unaffected.

## Evidence classification (requirement 7)

1. **Previously established synthetic evidence.** Slices 1–3: adapter core,
   registration seam, authority separation, no-auth mode; 255 focused tests;
   public-projection isolation. Unchanged by this receipt.
2. **Newly established live gateway evidence.** Guarded loopback deployment,
   bootstrap rejections, sentinel behavior, overlapping handoff, listener
   scope, virtual inventory, the single real Guardian→gateway dispatch with
   verified Bearer [REDACTED] and selector omission, and all gateway-level denials.
3. **Newly established live provider evidence.** 500 live Hacker News story
   ids through the full path, with gateway execution correlation
   (`executionId`, `auditPersisted`).
4. **Unqualified behavior.** No-auth success is not credential-bearing
   tenant-isolation proof. Gateway authentication is not Guardian account
   authorization. Discoverability is not hosted callability. Local success is
   not production-network qualification. Durable bindings, integrated
   revocation, backup restoration, guard rotation, and remote OAuth are not
   qualified.

## ADR invariants check

- Guardian sole account-authorization authority: held — every dispatch passed
  binding + usage-grant + revalidation.
- Custodian is delegated execution/custody only: held — custodian records were
  never treated as authority.
- Scoped tokens non-substitutable with deployment/operator credentials: held
  — guard and admin token never appeared on an execution path (verified by
  construction and by the zero-match redaction scan).
- No-auth omission does not bypass Guardian grants: held — binding, non-empty
  grant, token, and revalidation all still required (N3/N4/N5).
- Execution-time authorization mandatory: held — revalidation runs before
  every dispatch.
- Command Bus remains the agent surface; public visibility not widened: held
  (manifest + OpenAPI + hosted-posture checks).
- Uncertain authority fails closed: held across N0–N9.

Aligned with accepted ADR-071/ADR-094 amendments (2026-11-02), ADR-024,
ADR-075, ADR-092. No new ADR impact.

## Secret handling

- A first bootstrap-script version printed two trial token values to the
  session log (a harness logging slip, caught during the run). Contained:
  trial-only values, loopback-only surface, predecessor token revoked via the
  overlapping handoff, all gateway state destroyed at teardown. The proof
  harness was then fixed to redact token creation responses (names/ids/grants
  only).
- Final automated scan of all captured evidence for the working token, admin
  token, and guard values: **0 matches each**.
- This receipt contains no secret values: digests, ids, names, statuses, and
  shapes only.

## Validation performed

- Focused regression suite (see Closeout for commands and results).
- `make docs PYTHON=python3`, `git diff --check`, `git status --short`.
- Public-OpenAPI exclusion and manifest classification re-verified on the
  live app object inside the harness run itself.

## Cleanup

- Gateway teardown: container, volume, and network removed and verified
  absent (see Closeout).
- Scratch artifacts in `/private/tmp/gate-b-crossing/` removed and verified
  absent; trial secrets destroyed with the volume and the scratch removal.
- No Codexify container, network, or volume was created or modified.

## Remaining Gate B obligations

Catalog entry, durable Guardian-owned binding store, durable usage-grant
store, recorded allowlist review, and credential-bearing tenant isolation
through the adapter. Gate C, Gate D, hosted callability, and release posture
remain unqualified.
