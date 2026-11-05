# OpenConnector Gate B — independent re-validation of the live no-auth crossing

Date: 2026-11-05

Slice under test: `3824262ef` (reviewed no-auth execution mode), as committed.
Evaluated HEAD: `acf8e451c` on branch
`mcode/31b4bff7-5ff0-43f7-9879-7e88f1405a8e`.

Plan under evaluation:
[`docs/architecture/openconnector-integration-plan.md`](../../openconnector-integration-plan.md).

Related receipts:
[`2026-11-03-openconnector-gate-b-live-crossing-proof.md`](./2026-11-03-openconnector-gate-b-live-crossing-proof.md)
(R-HN), [`2026-11-03-openconnector-gate-b-credentialed-isolation-proof.md`](./2026-11-03-openconnector-gate-b-credentialed-isolation-proof.md)
(R-ISO),
[`2026-11-03-openconnector-gate-b-acceptance-revalidation.md`](./2026-11-03-openconnector-gate-b-acceptance-revalidation.md).

## 1. Why this receipt exists

This is a **second, independent execution** of the same qualified slice. It is
not a new gate, not a re-adjudication, and it does not change the Gate B
disposition. It exists because the committed implementation was re-executed
against a fresh pinned gateway deployment, and because that run produced three
observations R-HN does not contain:

1. the loopback-only publication was verified by **active refusal** on the
   host's non-loopback addresses, not only by the absence of a listening line;
2. the custodian's **run log** served as an independent dispatch witness, by
   counting the entries it gained;
3. the upstream **no-auth grant exemption** was reproduced live, which fixes a
   boundary that must not be misread later.

No source, test, configuration, ADR, or release file was changed for this
run. The implementation is exercised exactly as committed.

## 2. Verdict

**PASS — corroboration.** Every property R-HN established for the no-auth
crossing was independently re-observed on a fresh deployment, and no defect
was found. The three additional observations above are recorded as measured.

This receipt does **not** widen any boundary. Credential-bearing isolation
remains R-ISO's evidence and was not re-run here. The hosted
`public_allowlist` path remains **unqualified**. The private-network
deployment proof remains outstanding for its own gate. The release posture
is unchanged (`00-current-state.md` untouched, release gate still `HOLD`).

## 3. Environment

| Item | Value |
| --- | --- |
| Custodian image | `ghcr.io/oomol-lab/open-connector:v1.9.4@sha256:9cbc8cbb52d22553bd153d02a83ee1247b7470932bd5f6469d80895a17b3ef9c` |
| Image digest pinned | yes |
| Container health | `healthy` |
| Restart policy | `no` |
| Container network | `codexify_openconnector_trial` (ephemeral, removed at teardown) |
| Published host port | `127.0.0.1:12773 -> 3000/tcp` |
| Entry point exercised | Guardian internal-only route, over real HTTP to the gateway |
| Provider | live Hacker News API |

Deviation from R-HN, recorded for honesty: R-HN entered through the Command
Bus ASGI loopback; this run entered through the internal route directly, so
the Command Bus invocation itself is **not** re-proven by this receipt. It
remains covered by R-HN and by the committed test
`test_command_bus_invokes_the_internal_route`. This run also used a sentinel
plus working token rather than R-HN's overlapping handoff, and published on
port 12773 rather than 12774. None of these changes affect the properties
under test.

## 4. Deployment posture

The deployment carried the required enforcement surface. Values below are
deployment posture; the three deployment secrets are recorded by presence and
length only.

| Variable | Value |
| --- | --- |
| `OOMOL_CONNECT_ALLOWED_ACTIONS` | `hackernews.get_top_stories` |
| `OOMOL_CONNECT_BLOCKED_PROXIES` | `*` |
| `OOMOL_CONNECT_BLOCKED_TRIGGERS` | `*` |
| `OOMOL_CONNECT_ALLOWED_PROXIES` | *(empty)* |
| `OOMOL_CONNECT_ALLOWED_TRIGGERS` | *(empty)* |
| `OOMOL_CONNECT_ALLOW_PRIVATE_NETWORK` | `false` |
| `OOMOL_CONNECT_EGRESS_TRUSTED_HOSTS` | *(empty)* |
| `OOMOL_CONNECT_RUNTIME_TOKEN` | present, length 64 (value not recorded) |
| `OOMOL_CONNECT_ADMIN_TOKEN` | present, length 64 (value not recorded) |
| `OOMOL_CONNECT_ENCRYPTION_KEY` | present, length 64 (value not recorded) |

### 4.1 Loopback-only publication, verified by active refusal

R-HN observed the absence of a `0.0.0.0` binding and of an externally
reachable IPv6 line. This run additionally attempted to reach the published
port and required every attempt to be refused. Three independent checks:

| Check | Result |
| --- | --- |
| `HostConfig.PortBindings` | exactly one binding: `{"HostIp": "127.0.0.1", "HostPort": "12773"}` — no `0.0.0.0`, no `::` |
| Listening sockets for the port | exactly one: `127.0.0.1:12773` (IPv4 loopback) |
| TCP connect to host LAN IPv4 `192.168.4.37:12773` | **refused** (`ConnectionRefusedError`) |
| TCP connect to host IPv6 `fd20:c2b:54dc:1:1cb5:4b4a:90ad:3017:12773` | **refused** (`ConnectionRefusedError`) |
| TCP connect to host IPv6 `fd20:c2b:54dc:1:49c:71c8:51d9:5ca5:12773` | **refused** (`ConnectionRefusedError`) |
| TCP connect to `127.0.0.1:12773` | connected (the trial's own access path) |

This satisfies the bounded-trial posture. Loopback publication was a **trial
deviation** from the plan's no-published-ports topology, which remains the
governing deployment target. It is not evidence of production network
isolation.

## 5. Guardian authority

Guardian's account authority was synthetic, as the trial scope required: a
synthetic binding resolver and a synthetic usage grant stood in for a
production account. No Codexify account, credential, or database row was
created. Every other component on the path was the real one — the real
internal-only route, the real adapter, the real authority module, and the real
HTTP transport.

The synthetic binding named the custodian's **virtual** no-auth connection
identity and carried an explicit, non-empty scoped grant over it:

- `connection_id`: `hackernews:default` — confirmed against the custodian's
  own `GET /api/connections`, where that entry carries `credential: null` and
  no stored UUID;
- `allowed_connections`: `("hackernews:default",)` — non-empty, as ADR-094
  B5 requires;
- `runtime_token_ref`: resolved to the account-scoped persistent token whose
  grant names the same identity and whose `allowedActions` names the reviewed
  action.

The token store was never empty: a sentinel token was created first and a
working token second, and the anonymous rejection was asserted both before
bootstrap and after it.

## 6. Positive live evidence

| Measurement | Value |
| --- | --- |
| HTTP status | `200` |
| Guardian outcome / code | `success` / `ok` |
| Custodian envelope | `success: true`, `message: OK` |
| Provider payload | `story_ids`: **500** live Hacker News story ids, all numeric |
| Sample story ids | `50378228, 50379704, 50380810, 50381383, 50381687` |
| Execution id | `76a66f13-f25b-4d68-a59e-06c2ab6f3580` |
| `auditPersisted` | `true` |
| Response size | 4749 bytes (bound 262144) |
| Truncated | `false` |
| Dispatches observed by the transport | 1 |
| Outbound selector header present | **false** |
| Outbound body | `{"input": {}}` |
| Outbound bearer | the account-scoped token |

The selector omission was observed **on the wire**, not inferred from a
response: the recorded outbound request carried no `x-oo-connector-app-id`
header, while its bearer, body shape, and endpoint were otherwise unchanged.

### 6.1 The run log as an independent dispatch witness

The custodian's own run log (`GET /api/runs`) was counted before and after
the crossing and again after every negative control.

| Window | Run log before | Run log after | Delta |
| --- | --- | --- | --- |
| The crossing | 7 | 8 | **+1** |
| All six negative controls | 8 | 8 | **+0** |

The newest entry names `actionId: hackernews.get_top_stories`,
`service: hackernews`, and `connectionId: hackernews:default` — the custodian
independently identifies the target as the virtual no-auth connection. This
is a witness from the custodian's side, not from Guardian's own record of the
call.

## 7. Negative evidence

Every refusal path reached the gateway **zero** times and left the run log
unchanged. Guardian's denial codes and the custodian's denial codes are
distinguishable and were never substituted for one another.

| Control | HTTP | Guardian code | Dispatches |
| --- | --- | --- | --- |
| Action not on the reviewed allowlist | 403 | `action_not_approved` | 0 |
| Guardian binding revoked | 403 | `missing_profile` | 0 |
| No invocation grant | 403 | `missing_profile` | 0 |
| No scoped runtime token | 403 | `runtime_token_unavailable` | 0 |
| Binding grant does not cover its own identity | 403 | `missing_profile` | 0 |
| Unauthenticated caller | 401 | — | 0 |

Total dispatches across all six controls: **0**. Run log delta across all six
controls: **0**.

The distinction the campaign exists to protect is visible here: the revoked
binding, the absent invocation grant, and the binding whose grant does not
cover its own identity are three different Guardian facts, and all three stop
the crossing before the custodian is contacted. None of them is inferred from
the others, and a missing binding is never treated as permission.

## 8. Selector observation

The custodian was probed directly with the scoped token, holding everything
else constant:

| Selector | HTTP | Upstream code |
| --- | --- | --- |
| Omitted | **200** | — |
| Explicit: the granted virtual id `hackernews:default` | 403 | `connection_not_allowed` |
| Explicit: `service:default` | 403 | `connection_not_allowed` |

The omitted form is therefore not a convenience. For a no-auth action it is
the **only** reachable form, because upstream refuses an explicit selector
aimed at a virtual connection. That is why the omission is a property of the
reviewed allowlist entry and not a generic "connection optional" fallback: the
credential-bearing path still names its connection explicitly, and the
committed suite pins that difference.

## 9. New observation: the no-auth grant exemption is upstream behavior

This is the one boundary this run adds, and it is recorded so it cannot be
misread as a Codexify-side control.

A second token was minted whose grant was explicit and non-empty but named a
**non-existent** connection identity, with `allowedActions` naming the
reviewed action. Executing the no-auth action with that token returned
**HTTP 200**.

Upstream exempts a `no_auth` connection from the connection-grant
evaluation. The consequence is precise:

- the **Codexify-side** invariant still holds and is still enforced by
  Guardian — the binding must exist, be authorized, belong to the account,
  match the provider, and carry a non-empty scoped grant covering the
  identity it names, and the token must be present. §7 shows each of those
  independently stopping the crossing with zero dispatches;
- the **custodian-side** enforcement for a no-auth action is the action
  allowlist and the token's `allowedActions` grant, **not** the
  `allowedConnections` grant.

So the Codexify-side non-empty grant is a Guardian invariant for no-auth
actions, not an upstream-enforced one. It is recorded as expected upstream
behavior, not as a grant-control failure and not as evidence of
credential-bearing isolation. Credential-bearing isolation is R-ISO's
evidence, under a grant the custodian does enforce.

## 10. What this receipt does not establish

- **Credential-bearing isolation.** Not re-run. R-ISO remains the evidence.
- **Hosted callability.** The hosted `public_allowlist` path remains
  **unqualified**. This run exercised the internal route against a
  loopback-published trial gateway; it says nothing about the hosted
  posture, which stays deliberately unresolved.
- **Private-network deployment proof.** Still outstanding for its own gate.
- **Production network isolation.** Loopback publication was a bounded-trial
  deviation, not the plan's target topology.
- **Command Bus invocation.** Not re-proven by this run's entry path; see
  §3. R-HN and the committed suite cover it.
- **Provider credential retrieval.** Out of scope; no credential was used.

## 11. Secret handling and cleanup

- No production account, credential, provider key, or database row was
  created. The only secrets were trial-only, generated per run, and used
  solely between the local Guardian process and the loopback gateway.
- The three deployment secrets and the two minted runtime tokens existed only
  in the trial environment file and in the trial state file, both mode `0600`.
  Neither value was recorded in this receipt.
- The gateway container, its data volume, and its network were removed at
  teardown, and the absence of all three was verified afterwards. The
  published port was released.
- The trial environment file and state file were overwritten with a
  single-byte fill after teardown, and the fill was verified byte-uniform.
  The token material is not recoverable from them.
- No secret value is reproduced in this receipt, in the commit, or in any
  file added to the repository.

## 12. Validation performed against the committed tree

Run against the evaluated HEAD, with no working-tree changes.

| Check | Result |
| --- | --- |
| `pytest tests/connections/ tests/command_bus/` | **287 passed, 7 skipped** — matches the recorded result in the acceptance revalidation |
| `pytest tests/connections/test_openconnector_credentialed_isolation.py` | 5 passed, 7 skipped (the 7 are live-gated; they passed live in the R-ISO trial) |
| Public OpenAPI projection, `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`, with `CODEXIFY_ENABLE_OPENCONNECTOR_ROUTES=1` | **166 paths**, byte-identical to the pre-Slice-2 baseline at `85cf884ae`; **no** `openconnector` path present |
| `make docs PYTHON=python3` | passed |
| `git diff --check` | clean |

### 12.1 One stale line corrected in the plan

Appending this observation exposed a factual contradiction already present in
the plan: the Slice 6 observation section ended with "Gate B remains open",
while the acceptance revalidation section above it had closed the gate. The
acceptance revalidation evaluated HEAD `8154474f3` — the Slice 6 commit
itself — and adjudicated Gate B **CLOSED**, so that trailing line was stale.

The line was corrected in place to "Gate B was subsequently closed by the
acceptance revalidation recorded above." No criterion, status, boundary, or
disposition was changed by the correction; it aligns one sentence with the
adjudication that already existed. The correction is recorded here so it is
not mistaken for part of this run's findings.

## 13. Disposition

Corroboration only. The Gate B disposition recorded in the acceptance
revalidation (**CLOSED** at `acf8e451c`) is unchanged and is not reopened by
this run. No defect was found, so there is nothing to correct in the earlier
receipts.

The one addition to the evidence base is §4.1 (active refusal on
non-loopback addresses), §6.1 (the custodian's run log as an independent
dispatch witness), and §9 (the upstream no-auth grant exemption, recorded so
the Codexify-side grant invariant for no-auth actions is never mistaken for
an upstream enforcement).

Remaining obligations are unchanged and are tracked by their own gates:
durable binding and grant stores (Gate C), provider verification and release
qualification (Gate D), the hosted callability decision, and the
private-network deployment proof.
