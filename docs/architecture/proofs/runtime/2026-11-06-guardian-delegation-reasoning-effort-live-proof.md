# Guardian delegated execution — reasoning-effort live proof

Date: 2026-11-06

Evaluated source: `64ef74756abb48165ad1848f65f3e91ffb9ed80a` — a disposable worktree of the merged
mainline (`e72464e05`, the merge of PR #1012) carrying one operator-tooling commit
(`scripts/ops/build_cxf_delegation_fixture.sh`, `scripts/ops/seed_cxf_delegation_fixture.py`).
**No application source differs from `main`.**

Backend image: `codexify-backend-runtime:cxf-deleg-64ef74756ab` (`sha256:8ff03e0…` is the Preview
build; this one is `cxf-deleg-64ef74756ab`), built from the evaluated checkout. Coding-worker image:
`codexify-worker-coding-runtime:cxf-deleg-64ef74756ab`.

Runtime: a disposable Compose project (`cxfdelegation`) on a disposable PostgreSQL and Neo4j, bound
to a one-file fixture git repository, with the DeepSeek credential the operator already holds.

Release posture remains `HOLD`. This receipt proves one contract on one runtime. It does not
qualify the product.

## What this receipt establishes

The Guardian-governed `reasoning_effort` **reaches the worker-to-adapter boundary and is attested
there**, live, with the provider actually serving the request. This is the proof the 2026-10-20
canary could not complete: that receipt reproduced the defect — *"the worker's reasoning effort is
never passed, and `medium` is not a self-consistent level for this model"* — and the contract was
repaired afterwards. This receipt exercises the repaired contract against the running service.

**20 of 20 checks passed.**

| Check | Result |
| --- | --- |
| Disposable stack is healthy | PASS |
| Live `alembic_version` is the source head | PASS — `a7d4c9e2f1b3` |
| DeepSeek credential registered account-scoped | PASS — `ccr_15aa500f8e7948d383a6491fe9d31afe` |
| Seeded account and project exist | PASS |
| A fresh thread and user-authored source message exist for this run | PASS — thread 4, message 7 |
| Project is bound to the fixture repository, not the Codexify checkout | PASS — `/fixtures/delegate-fixture` |
| Delegation intent created and auto-approved | PASS — `gdi_a682a1da7e2a48c0` |
| A caller cannot widen the authorized posture to allow network egress | PASS — 403 `guardian_permission_allow_network_not_authorized` |
| Authorized coding task dispatched | PASS — `run_af352565960d448f`, deployment `dep_841c55d707eb440d` |
| Persisted execution binding governs the reasoning effort (schema v2) | PASS — `reasoning_effort='off'`, `schema_version=2` |
| The binding's model is the one the effort lane recognises | PASS — `deepseek-v4-flash` |
| Delegated run reached a terminal state | PASS — `succeeded`, no error |
| The provider that actually served is the one the binding named | PASS — `actual_provider_id=deepseek`, `actual_model_id=deepseek-v4-flash` |
| The harness attested its runtime identity | PASS — `pi-coding-agent` `0.82.1`, `runtime_identity_established=true` |
| The credential was the account's own BYOK key | PASS — `owner_scope=account`, `funding_route=user_byok`, owner `cxf-delegation` |
| The governed effort was forwarded to the adapter, not defaulted | PASS |
| The run succeeded, which requires the wrapper to attest the forwarded effort | PASS |
| The coding result was delivered to the source thread | PASS — one `coding_result` row |
| The fixture's tracked working tree was left unmodified (worktree isolation held) | PASS |
| An isolated coding worktree root was created under the fixture | PASS — `.codexify/coding-worktrees/` |

## The persisted binding

Written by `persist_execution_binding` into the deployment spec **before** the task is enqueued, so
the worker reads exactly what Guardian authorised:

```text
schema_version            : 2
reasoning_effort          : 'off'
provider_id               : 'deepseek'
model_id                  : 'deepseek-v4-flash'
credential_ref            : 'ccr_15aa500f8e7948d383a6491fe9d31afe'
credential_owner_scope    : 'account'
funding_route             : 'user_byok'
harness_id                : 'pi'
harness_selection_mode    : 'default'
```

`schema_version: 2` is the load-bearing fact. A binding that does **not** govern the effort is
minted at schema version 1, carries no effort, and the worker forwards nothing — so the Pi adapter
applies its own `"medium"` default. That is the defect the 2026-10-20 canary isolated. The
authorised level here is schema version 2 with `reasoning_effort: 'off'`, which is the
`(deepseek, deepseek-v4-flash)` lane's default.

## Why a successful run is itself the proof

The adapter hard-asserts that the Pi wrapper attested `requested == effective == expected`, and
returns an error envelope with `failure_stage="reasoning_effort"` otherwise. The wrapper also
refuses a non-`off` effort outright when a required tool is named. So the outcome discriminates in
both directions:

- the run **succeeded** ⇒ the effort was forwarded as `off` and the wrapper attested it;
- the run **failed with a reasoning-effort stage** ⇒ the effort was *not* forwarded and the
  adapter's own default applied.

The runtime identity attestation makes the provider side concrete rather than inferred:

```text
requested_provider_id : deepseek          actual_provider_id : deepseek
requested_model_id    : deepseek-v4-flash actual_model_id    : deepseek-v4-flash
actual_harness_id    : pi-coding-agent   actual_harness_version : 0.82.1
runtime_identity_established : true
```

The delivered result was read back from the canonical path:

```text
## Guardian Delegation Result

**Status**: OK

**Intent ID**: `gdi_a682a1da7e2a48c0`

**Run ID**: `run_af352565960d448f`

**Summary**: Guardian-authorized Pi task completed
```

## The run was contained

The delegated task was bound to a one-file fixture git repository, never to the operator's Codexify
checkout. The project's `RepositoryBinding.canonical_root` was `/fixtures/delegate-fixture`, and the
run manifest records the isolated worktree it actually used:

```text
repo_root          : /fixtures/delegate-fixture
worktree_path      : /fixtures/delegate-fixture/.codexify/coding-worktrees/run_af352565960d448f-gct_…-gat_…
base_head          : 4e37d0320093241a3a3da2c715f17478aa72f538
mutation_guard_status : passed
error_code         : null
```

After the run the fixture's **tracked** working tree was unmodified (`git status
--porcelain --untracked-files=no` is empty). The only new path is the worker's own untracked
`.codexify/` scratch tree. `CODING_WORKER_WORKTREE_ISOLATION=true` was set on the coding worker;
without it the adapter's working directory is the bound root itself and the agent's mutations land
in that working tree.

## The posture gate holds, and the egress surface is still advisory

The authorised posture was `allow_shell=true, allow_write=true, allow_network=false,
allowed_paths=["."], max_runtime_seconds=300`. A dispatch that asked for `allow_network=true` was
refused before anything was queued:

```text
POST /api/agents/coding/execute  ->  403 guardian_permission_allow_network_not_authorized
```

**And yet the provider was reached.** `actual_provider_id=deepseek` with
`runtime_identity_established=true` cannot be true without a completed network call to
`api.deepseek.com`. The profile in force declared `CODEXIFY_EGRESS_ALLOWLIST: ""`. This
re-proves, at this tip and on a live run, the structural finding the 2026-10-20 canary recorded:
**the network-egress surface is advisory, not enforced.** The permission posture refuses a caller
who *asks* for egress; it does not stop the worker from making one. The canary's conclusion —
"disagreement is structural, not a recent regression" — stands.

## A supported path cannot host this run

This is the finding that most constrains what the receipt can claim.

**No supported profile mounts the delegated routes.** Every profile that mounts
`agent_orchestration` is local-only, and every profile that admits a cloud provider quarantines
it:

| Profile | `agent_orchestration` | `ALLOW_CLOUD_PROVIDERS` |
| --- | --- | --- |
| `v1-local-core-web-mcp` | enabled | `false` |
| `v1-user-profile-accent-proof` | enabled | `false` |
| `v1-music-producer` | enabled | `false` |
| `test-continuity` | quarantined | `false` |
| `v1-friends-family-web` | quarantined | `true` |
| `v1-whooshd-deepseek-web` | quarantined | `true` |

The `guardian_delegations` router is additionally gated: `default_enabled=False` behind
`CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES`, with the source comment *"Keep the Phase 2A proof
route explicitly gated so it does not widen the supported release surface before the hybrid
delegation loop is proven."*

The consequence is sharper than it looks. The **only** entry in
`CODING_EXECUTION_REASONING_EFFORT_LANES` is `(deepseek, deepseek-v4-flash)`. A local-only
profile's delegated binding resolves its provider from the account's credential and its model from
`default_model_for_provider`, and a local provider has **no lane** — so the effort is ungoverned,
the binding is minted at schema version 1, and the adapter's own `"medium"` default applies. That
is precisely the defect the canary found.

**So the contract governs no real deployment in the current profile matrix.** This run therefore
executed on a **proof-only profile** (`v1-delegation-proof`), created inside the disposable
worktree and not tracked by the repository. It widens nothing that is release-supported: it is not
named by the release truth, and the qualification registry does not discover it.

Two related refusals were observed live and are worth recording because they are the contracts
working:

```text
supported profile drift: ALLOW_CLOUD_PROVIDERS expected False but found True
supported profile drift: required route 'guardian_delegations' is not mounted
```

The first is the backend refusing to start on a local-only profile whose runtime widened the cloud
posture. The second is the backend refusing to start when a profile declared a route the runtime
did not mount. Neither was worked around.

## Two bounded observations from the run sequence

These are observations about the harness's own sequencing, recorded because they are real product
behaviour and not defects introduced by the proof:

1. **Result delivery is keyed on the (thread, source message) pair.** A second dispatch into the
   *same* lineage cannot deliver a second result: the insert violates
   `uq_chat_messages_source_thread_message`. A first run delivered its result, and a second run
   into the same lineage failed at delivery with the constraint violation. Each proof run therefore
   used its own thread and source message.
2. **The delivery scope check is real.** A run whose thread had no project was refused at
   delivery with `guardian_delegation_scope_mismatch`, while the delegated execution itself
   succeeded. The scope check and the execution are separate gates.

## One note on the model inventory

`deepseek-v4-flash` does **not** appear in the provider's `/models` inventory, which lists
`deepseek-flash` and `deepseek-v4-pro`. A direct completion against `deepseek-v4-flash` **succeeds**.
The lane's model is real and servable; the inventory listing is incomplete. Nothing here was
inferred from that listing.

## What this receipt does not establish

- **The product is not qualified.** This is one contract on one disposable runtime.
- **The delegated path was not exercised on a supported path**, because no supported profile mounts
  the delegated routes. Making it one is a product decision — it widens the release surface — and
  is not made here.
- **No crash-durability claim.** No assertion is made about acknowledged commits surviving a
  server crash.
- **The egress surface is still not enforced.** The provider was reached with
  `allow_network=false`; the receipt proves the gap, not its closure.
- **The fixture's tracked tree was not modified by the agent** (`patch_status: no_changes`). The
  containment is proven; an agent that mutates source under isolation was not exercised.
- **The Private Preview was paused for the duration of this run** and is restored afterwards. This
  receipt concerns the disposable project only.

## Release and ADR posture

No ADR change. ADR-016, ADR-020, ADR-071, ADR-077, ADR-092 and ADR-094 are unchanged. The
credential was the account's own BYOK key, registered account-scoped and issued under the ADR-094
lease boundary, exactly as the 2026-10-20 canary did.

## Reproduction

```sh
# 1. disposable checkout, fixture, env, overlay
EVAL_SHA=<sha> bash scripts/ops/build_cxf_delegation_fixture.sh <fixture>
#    (env carries the operator's DEEPSEEK_API_KEY, copied, never printed)

# 2. images built from the evaluated checkout
export BUILDX_CONFIG=<workspace-local-buildx-config>
docker buildx build --builder desktop-linux --load --network host \
  -f backend/Dockerfile --target runtime -t codexify-backend-runtime:cxf-deleg-<sha12> .
docker buildx build --builder desktop-linux --load --network host \
  -f backend/Dockerfile --target worker-coding-runtime -t codexify-worker-coding-runtime:cxf-deleg-<sha12> .

# 3. up + seed, then the harness
docker compose --project-directory <checkout> --env-file <env> -p cxfdelegation \
  -f <checkout>/docker-compose.yml -f <overlay> up -d db redis neo4j migrator backend worker-coding
docker exec -e CXF_ACCOUNT_ID=… -e CXF_ACCOUNT_PASSWORD=… -e CXF_FIXTURE_REPO=/fixtures/delegate-fixture \
  -e CXF_PROJECT_ID=… cxfdelegation-backend-1 python /app/scripts/ops/seed_cxf_delegation_fixture.py
python .cxf_deleg_harness.py --env-file <env> --project cxfdelegation --out <results.json>
```
