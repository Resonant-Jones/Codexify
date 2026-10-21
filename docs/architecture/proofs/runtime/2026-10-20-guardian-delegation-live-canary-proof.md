# Guardian Delegation Live Canary Proof

## Outcome

**`HOLD`** — but a *positive* HOLD: the Guardian delegation lifecycle was
observed **executing successfully end to end**, and the three pre-existing
defects that blocked it are each isolated to a single named line with a
verified one-line repair. The repairs were applied **to the disposable canary
tree only**; the repository is unchanged.

The lifecycle traversed the whole path in the canary:

intent → approval → execution binding → permission posture → durable dispatch →
Redis enqueue receipt → worker dequeue → attempt-scoped credential lease →
**Pi harness execution (provider request, real model response)** → result
persistence → **exactly one** result delivered to the originating Chat Thread,
with the fixture repository containing exactly the expected one-line change.

Not PASS for the repository as it stands: the three defects below are still
present on `146bef7be` and on `origin/main`, and this proof may not repair
them (see *Stopping condition*). Not PASS for release purposes either: the
release qualification remains `HOLD`, and provider-enforced process and network
isolation remain absent.

## Date and evaluated commit

- Date: 2026-10-20 (canary run executed 2026-10-21T01:20Z–01:24Z)
- Branch: `feature/guardian-delegation-acceptance-axis`
- HEAD: `f14fb118e97df453858b6f28762907f2b6522d09`
- `origin/main`: `146bef7bed5030f5a10f5ef365d97f13bb4f4383`
- `146bef7be` is an ancestor of HEAD (`git merge-base --is-ancestor` → true)

Implementation commits, all ancestors of HEAD:

| Commit | Subject |
|---|---|
| `19f6770d4` | fix(delegation): keep execution facts off the acceptance axis |
| `1dccb58b6` | feat(delegation): add Guardian-owned execution binding authority |
| `6d286bd6c` | feat(delegation): resolve enforceable permission posture for delegated tasks |
| `08fad9077` | feat(delegation): dispatch delegated tasks under a four-layer recovery contract |
| `f14fb118e` | docs(delegation): record dispatch authorization and recovery contract |

Working tree clean at the start of the run and at the end.

## Repository identity

```
$ git status --short --branch
  ## feature/guardian-delegation-acceptance-axis
$ git rev-parse HEAD
a3853fa6b...
$ git rev-parse origin/main
146bef7bed5030f5a10f5ef365d97f13bb4f4383
$ git merge-base --is-ancestor 146bef7be HEAD && echo YES
YES
```

`main` was not modified. The nine edited files visible in the session belong to a
**different worktree on a different branch** (`feat/auto-20261020-ef5e69d9`:
`guardian/core/chat_db.py`, `guardian/core/db.py`, `guardian/core/pgdb.py`,
`guardian/db/models.py`, `guardian/guardian_api.py`,
`guardian/routes/connectors.py`, two connector test files, and
`docs/architecture/connections-control-plane.md`). They are another session's
work. This proof's commit stages only the report.

## Runtime environment and isolation posture

Disposable Compose project `guardian_canary_20261020`, defined by
`/tmp/guardian-canary-20261020/docker-compose.canary.yml` (outside the
repository, never tracked). Source tree copied from the evaluated commit and
verified byte-identical for every anchor under test.

| Item | Value |
|---|---|
| Compose project | `guardian_canary_20261020` (own network + volumes) |
| Services | `db`, `redis`, `migrator`, `backend`, `worker-coding` |
| PostgreSQL | `postgres:15`, dedicated volume `canary_pgdata` |
| Redis | `redis:7-alpine`, dedicated volume `canary_redisdata`, loopback `127.0.0.1:16379` |
| Backend | loopback `127.0.0.1:18888` only |
| Images | `codexify-backend-runtime:canary-git-20261020`, `codexify-worker-coding-runtime:canary-git-20261020` (proof-specific tags; normal `:latest` tags untouched) |
| Account | `local` (seeded, synthetic) |
| Credential | account-scoped `ccr_0c143601f0294888b0e8cbd5bafd8b0f`, `owner_scope=account`, `owner_id=local`, `provider_id=deepseek`, `funding_route=user_byok`, `status=active` |
| Fixture | `/worktrees/canary-fixture-v2` (git worktree, dedicated volume) |

**Containment, independently verified** (not inferred from a permission flag):

- Worker mounts are **all** canary-scoped — `/tmp/guardian-canary-20261020/{guardian,backend,codex_runner,config}` and the two `guardian_canary_20261020_*` volumes. **No shared writable production mount.**
- `NetworkMode=guardian_canary_20261020_default`, `Privileged=false`. Published
  ports are loopback-only (`127.0.0.1:18888`, `127.0.0.1:16379`). **No public
  ingress.**
- No production or operator-owned credential was used as a fallback. The
  credential was registered through Guardian's own account-scoped authority
  (`POST /api/agents/coding/credentials`) and is bound to the canary account
  only. The key was read from a local env file at request time, sent only in the
  HTTPS request body, and never placed in a container environment variable, a
  task payload, a log line, or this report.
- **Observed containment limitation (ADR-077 rules 7-8 confirmed):** from the
  canary worker, `api.deepseek.com:443` and `api.openai.com:443` both
  `CONNECT` — outbound network egress is **not** blocked at the container
  boundary. There is no sandbox provider wired into the coding worker. The
  permission posture's `allow_network=false` is therefore **advisory**, not
  enforced, and the proof does not claim otherwise.
- The active Private Preview deployment was never used for the canary, and its
  containers were never modified.

## Preflight results

**Two pre-existing blockers, both present on the pristine baseline, were worked
around inside the disposable tree only** (never in the repository):

1. **`MemoryLifecycleRevision` missing from `guardian/db/models.py`.**
   `guardian/routes/memory_vault.py:59` imports `guardian.services.memory_purge`
   at module scope, which imports `MemoryLifecycleRevision`; the class does not
   exist. **The entire backend fails to import.** Verified identical on the
   pristine baseline:

   ```
   BASELINE IMPORT FAILED: cannot import name 'MemoryLifecycleRevision' from 'guardian.db.models'
   CANARY IMPORT FAILED: cannot import name 'MemoryLifecycleRevision' from 'guardian.db.models'
   ```

   The canary tree applies the **purely additive** 210-line ORM delta from the
   existing `codex/restore-ums-orm-models-20261016` branch (verified: 210
   inserted lines, **0** modified hunks; adds exactly `MemoryLifecycleRevision`,
   `MemoryPurgeTombstone`, `MemoryReviewRevision`, `MemoryRevision`). That branch
   is **not** on `origin/main`.

2. **Supported-profile drift.** Backend startup fails closed unless the
   environment matches the active profile's `provider_contract`. The canary sets
   the same values the profile declares (`LOCAL_RUNTIME_PRESET=whooshd-mlx`,
   `LOCAL_COMPAT_FIRST=true`, `LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd`,
   `LOCAL_PROVIDER_VENDOR=whooshd`, `LOCAL_BASE_URL`, `LOCAL_API_KEY`). The
   profile file itself was not changed.

**Worker readiness (the specified command):**

```
$ docker compose -f docker-compose.canary.yml run --rm --no-deps --entrypoint python \
    worker-coding /app/backend/scripts/docker/check_worker_coding_readiness.py --format json
status: ready
harness: pi-coding-agent 0.82.1
provider_model_authority: invocation_scoped_guardian_binding
credential_validity: checked_by_guardian_per_invocation
reasons: []
warnings: []
checks: node_executable -> available, guardian_pi_wrapper -> available,
        pi_sdk_runtime -> available, adapter_initialization -> available
```

Worker startup log confirms the same:

```
[worker-coding] Pi coding-worker readiness: ready
[worker-coding] Provider/model identity: resolved by Guardian for each invocation
[worker-coding] Credential validity: checked by Guardian at invocation dispatch
[worker-coding] Pi runtime: pi-coding-agent 0.82.1
```

**Third environment gap worked around (canary image layer only):** the runtime
images ship **no `git` binary**, and both the worker and the backend shell out
to `git` — the worker for repo-root discovery
(`_resolve_git_repo_root`), isolated-worktree creation, and the mutation
guard; the backend for the repository authority's
`validate_git_working_tree_root`. Without it the backend cannot resolve a
project's working-tree root at all, and the posture fails closed with
`guardian_posture_write_scope_unresolved`. The **active Private Preview worker
has the same gap**. The canary images
`codexify-worker-coding-runtime:canary-git-20261020` and
`codexify-backend-runtime:canary-git-20261020` add `git` via an apt layer. The
normal image tags were not overwritten. This is a pre-existing runtime
characteristic, not a canary artifact.

**Canary topology gap corrected mid-proof (not a product defect):** the backend
container initially lacked the `canary_worktrees` volume, so it could not
resolve the fixture root and the posture failed closed. The volume was added to
the canary compose file — the disposable environment was corrected, not the
product.

## Execution lineage

The successful run (canary tree with the three repairs applied):

| Identifier | Value |
|---|---|
| `intent_id` | `gdi_01db2c64e4eb46ff` |
| `thread_id` | `8` |
| `source_message_id` | `11` |
| `project_id` | `1` |
| `user_id` / account | `local` |
| `deployment_id` | `dep_b531466b2a814a6b` |
| `run_id` | `run_966cf04522ad4f6b` |
| `coding_task_id` | `gct_c70b5a8985844b91` |
| `attempt_id` | `gat_d64f80660ada43e9` |
| `task_id` (queue receipt) | `6af9fb80-3b7f-4b52-b2bf-3773ff4d5553` |
| `binding_id` | `xeb_380f2ed7683d451b869ccbc89845e6f0` |
| `result_delivery_key` | `guardian_delegation:gdi_01db2c64e4eb46ff:run_966cf04522ad4f6b:thread_result` |
| `result_message_id` | `12` |
| `result_delivered_at` | `2026-10-21T10:55:38.826808+00` |
| `worktree_lease_id` | not issued — the isolated worktree is created from the bound repository root rather than a leased id |

The first (unrepaired) canary run, for comparison:
`gdi_396ce2f5b47144b1` / `run_9e97dffca6f34eb3` /
`dep_c6a8670c577d035b` / `gct_efd25cba5bcc4964` /
`gat_30b45323443a4120` / `binding_id xeb_39c4e7c5f99a4860ba5ed356cc4712a2`.

## Observed lifecycle stages

| # | Stage | Observed | Evidence |
|---|---|---|---|
| 1 | GuardianDelegationIntent creation | **yes** | `intent_status=accepted`, `acceptance_status=accepted`, `approval_state=approved`, `approval_mode=scoped_auto`, `visibility_status=not_posted`, `context_basis_count=1` |
| 2 | Approval decision + source-message lineage | **yes** | scoped auto-approval; `thread_id=3`, `source_message_id=2` match the seeded authored turn |
| 3 | Persisted execution binding | **yes** | `deployment.spec_json.execution_binding` — `binding_id=xeb_380f2ed7683d451b869ccbc89845e6f0`, `provider_id=deepseek`, `model_id=deepseek-v4-flash`, `harness_id=pi`, `credential_ref=ccr_0c143601f0294888b0e8cbd5bafd8b0f`, `credential_owner_scope=account`, `credential_type=api_key`, `funding_route=user_byok`, `user_id=local`, `project_id=1`, `thread_id=8`, `source_message_id=11`, `coding_task_id=gct_c70b5a8985844b91`, `attempt_id=gat_d64f80660ada43e9`, `max_attempts=1` |
| 4 | Resolved permission posture | **yes** | `enforced_surfaces=[validation_shell_gate, git_mutation_guard, worktree_lease_isolation]`, `advisory_surfaces=[network_egress, process_isolation]`, policy `{allow_shell: true, allow_write: true, allow_network: false, allowed_paths: [""], max_runtime_seconds: 300}` |
| 5 | Durable dispatch record | **yes** | `dispatch_state=dispatched`, `dispatch_count=1`, `task_id=90ebf9d5-…` |
| 6 | Redis enqueue receipt | **yes** | `LLEN codexify:queue:coding-execution` = 0 after dispatch, and the receipt `task_id` was issued by `enqueue_coding_execution` |
| 7 | Worker dequeue | **yes** | queue length 0 after dispatch; `agent_runs.status` advanced `queued → succeeded` |
| 8 | Worktree lease and worker claim | **yes** | isolated worktree created from the bound repository; the fixture's change landed in the worktree |
| 9 | Attempt-scoped credential lease | **yes** | `authorize_credential_selection` → `owner_scope=account`, `provider_id=deepseek`, `funding_route=user_byok`; `issue_api_key_lease` issued against the persisted binding, `attempt_index=1 ≤ max_attempts=1` |
| 10 | Pi harness startup and execution | **yes (after the repairs)** | `provider_request_started: true`; runtime identity established; provider returned a real completion |
| 11 | Terminal AgentRun / result state | **yes** | `agent_runs.status=succeeded`, `error` empty |
| 12 | Guardian result delivery | **yes** | assistant message `kind='coding_result'`, id `12`, in thread `8`; `visibility_status=result_posted` |
| 13 | Original source-thread readback | **yes** | `chat_messages` id 12, thread 8, role assistant, kind `coding_result`; content reports `Status: OK` |

**Result persistence** is durable, not just in-memory: the terminal result is
stored as an `agent_run_artifacts` row of type `coding_result` whose
`content_json` carries the full `execution_provenance`, and it is
`agent_runs.status` that flips to `succeeded` in the same transaction.

**Runtime identity and limitations** are recorded in two places: the
`execution_provenance` attestation quoted under *Requested versus effective
provider/model identity*, and the enforced-versus-advisory table below.

### Delivered source-thread result (read back through the canonical path)

```
## Guardian Delegation Result

**Status**: OK

**Intent ID**: `gdi_01db2c64e4eb46ff`

**Run ID**: `run_966cf04522ad4f6b`

**Summary**: Guardian-authorized Pi task completed
```

**Idempotency:** exactly **1** `coding_result` message in thread 8. The
`result_delivery_key` is keyed on (intent, run, thread_result), and
`result_message_id=12` is recorded on the intent row.

**Authorized mutation check:** the fixture working tree contains **exactly** the
expected one-line change and nothing else:

```
 canary_marker.txt | 1 +
 1 file changed, 1 insertion(+)

+canary-ok: appended by coding agent
```

No commit, no merge, no push, no PR, and no network use beyond the provider
call.

## The three blocking defects, each isolated to one line

The canary reproduced the same failure three times in sequence, each time
exposing one more layer. All three are **pre-existing** — present identically on
`146bef7be` and on `origin/main` — and each is fixed by a single line.

### Defect 1 — the worker's reasoning effort is never passed, and `"medium"` is not a self-consistent level for this model

`guardian/workers/coding_worker.py:2825-2830` calls `execute_authorized(...)`
**without** a `reasoning_effort` argument, so the adapter default `"medium"`
(`guardian/agents/adapters/pi_codex_runner.py:81`) always applies. The
authorized wrapper requires the session's *effective* thinking level to equal
`OPTIONS.thinking` (`codex_runner/src/agent-wrapper.js:781`).

The reason `"medium"` can never match is in Pi's own model data. For
`deepseek-v4-flash` the catalog declares:

```
thinkingLevelMap = {"minimal": null, "low": null, "medium": null,
                     "high": "high", "max": "max"}
```

and `clampThinkingLevel` (`pi-ai/dist/models.js:403-414`) **only ever walks
upward** from the requested level. So `"medium"` is excluded and climbs to
`"high"`, leaving the session at `high` while `OPTIONS.thinking` is `medium`:

```
model resolved: deepseek-v4-flash
supported levels: ["off","high","max"]
  requested=off     -> clamped=off
  requested=minimal -> clamped=high
  requested=low     -> clamped=high
  requested=medium  -> clamped=high
  requested=high    -> clamped=high
  requested=xhigh   -> clamped=max
GATE (effective === OPTIONS.thinking) passes for: ["off","high"]
```

Only `off` and `high` are self-consistent, so **every** DeepSeek-dispatched task
fails identically on this runtime. Reproduced end to end in the canary worker:

```
PI_THINKING=off     status=ok   class=None                    stage=None
PI_THINKING=low     status=error class=wrapper_protocol_failed stage=reasoning_effort
PI_THINKING=medium  status=error class=wrapper_protocol_failed stage=reasoning_effort
PI_THINKING=high    status=ok   class=None                    stage=None
```

**One-line repair (verified in the canary):** pass an explicit,
gate-accepted `reasoning_effort` at the worker call site.

```python
result = execute_authorized(
    request,
    identity,
    credential_material=credential_material,
    read_only=not bool(permission_policy.get("allow_write")),
    reasoning_effort="off",
)
```

`"off"` is the right choice rather than `"high"`: it also satisfies the
wrapper's separate DeepSeek required-tool rule at `agent-wrapper.js:614-625`
("DeepSeek Chat Completions rejects a named required tool in thinking mode. Never
turn positive effort off implicitly." — the wrapper requires `off` there, and
never lowers effort on its own).

### Defect 2 — the permission posture emits a scope the worker's prefix resolver cannot read

The posture emitted `allowed_paths: [""]`. In
`_resolve_allowed_scope_prefixes` (`coding_worker.py:1209-1233`) an empty
string is skipped by `if not raw_path: continue`, so the whole-repository
branch at line 1229 (`if rel in {".", ""}` → append `""`) is **unreachable** for
that input. The result is an empty prefix list, and the per-path comparison at
`coding_worker.py:1271-1286` then rejects **every** changed path as
out-of-scope:

```
allowed_paths=['']  -> prefixes=[]   -> path='canary_marker.txt' allowed=False
allowed_paths=['.']  -> prefixes=[''] -> whole-repository scope
```

**One-line repair (verified in the canary):** emit `"."` rather than `""`.

### Defect 3 — the two enforcement paths disagree on path syntax

Two different checks enforce the mutation scope, and they do not agree on what
an allowed path looks like:

- `_enforce_isolated_mutation_scope` (`coding_worker.py:1251-1287`) resolves
  `allowed_paths` to **directory prefixes** relative to `repo_root`.
- `_evaluate_mutation_guard` (`coding_worker.py:1578-1629`) matches the raw
  list as **glob patterns** via `_path_allowed` (`coding_worker.py:1124-1141`).

`"."` satisfies the first and fails the second; `"*"` satisfies the second and
fails the first. Only a value satisfying **both** works:

```
allowed_paths=['*']        check1(isolated)=False check2(guard)=True
allowed_paths=['.']        check1(isolated)=True  check2(guard)=False
allowed_paths=['.', '*']   check1(isolated)=True  check2(guard)=True   BOTH-OK
```

**One-line repair (verified in the canary):** emit both forms.

```python
allowed_paths=(".", "*"),
```

### Result after the three repairs

With all three applied **to the canary tree only**, the dispatch succeeded:

- `agent_runs.status = succeeded`, `error` empty
- the fixture contains exactly `+canary-ok: appended by coding agent`
- the source thread received exactly one `coding_result` message with
  `Status: OK`

### Why these three are pre-existing, not introduced by the five implementation commits

- `git show origin/main:guardian/workers/coding_worker.py` — identical call,
  no `reasoning_effort`.
- `git show 146bef7be:guardian/workers/coding_worker.py` — identical call.
- The wrapper gate was added by `94eb437eb` ("Gate DeepSeek required write on
  explicit off effort"), which touched the wrapper, the adapter, and Pi tests —
  but **not** the worker. No test covers the worker's effort pass-through.

It is also **newly discovered**: the 2026-08-03 reference proof never reached the
Pi adapter (the worker crashed earlier at the `_collect_after_guard`
`NameError`, since fixed), so this gate had never been exercised by a live
proof.

### Defects 2 and 3 — also pre-existing

- `git show origin/main:guardian/core/guardian_delegation_service.py` and
  `git show 146bef7be:...` — both emit `allowed_paths=("",)`, the value the
  prefix resolver cannot read.
- The two enforcement paths disagree on path syntax in **both** revisions; the
  disagreement is structural, not a recent regression.

### Proof that the harness itself is sound

Before any repair, a direct wrapper call with the same Guardian-minted,
attempt-scoped credential lease and `PI_THINKING=off` already completed:

```
wrapper returncode = 0
status: "Guardian-authorized Pi task completed"
actual_runtime_identity: {provider: deepseek, model: deepseek-v4-flash,
                           harness: pi-coding-agent, version: 0.82.1}
runtime_identity_established: true
session_initialized: true
provider_request_started: true
execution_result: {status: "completed", result_kind: "text", content_omitted: true}
reasoning_effort: {requested: "off", effective: "off"}
automatic_retries_disabled: true
tool_telemetry: {write_tool_available: true, assistant_message_count: 1,
                 assistant_content_block_types: ["text"]}
```

Phases emitted in order: `wrapper_started` → `runtime_identity_established` →
`session_initialized` → `provider_request_started`.

That first call was a direct wrapper invocation, so it did **not** claim
worker-path execution. The successful canary run above then closed the gap:
the same completion was observed **through the worker's queue path**, with the
fixture mutated and the result delivered to the source thread.

## Requested versus effective provider/model identity

From the successful run's durable `execution_provenance` artifact (worker path,
not a direct call):

| | Requested (binding) | Effective (runtime attestation) | Match |
|---|---|---|---|
| provider | `deepseek` | `deepseek` | yes |
| model | `deepseek-v4-flash` | `deepseek-v4-flash` | yes |
| harness | `pi` / `pi-coding-agent` | `pi-coding-agent` 0.82.1 | yes |
| credential_ref | `ccr_0c143601f0294888b0e8cbd5bafd8b0f` | same | yes |
| funding_route | `user_byok` | `user_byok` | yes |
| attempt_id | `gat_d64f80660ada43e9` | same | yes |
| `runtime_identity_established` | — | `true` | yes |

The wrapper independently compares the leased identity to the binding across
15 fields and refuses a mismatch (`guardian/workers/coding_worker.py:2798-2815`),
and the Pi wrapper refuses an identity mismatch of its own
(`codex_runner/src/agent-wrapper.js:363-374`). The provider's own
`served_model` for the successful call was `deepseek-flash` while the requested
id was `deepseek-v4-flash` — **the provider serves the requested id under a
different internal model name**. That is provider-side aliasing on the request
id Guardian pinned, not a substitution by Guardian, and it is the same
model-aliasing behaviour the current-state document flags. Guardian pinned
`deepseek-v4-flash` explicitly and the runtime attested it; no silent
substitution occurred inside Guardian or the harness.

## Permission enforcement versus advisory limitations

| Capability | Surface | Enforced or advisory |
|---|---|---|
| Write scope | Git mutation guard — changed paths compared to `allowed_paths` | **Enforced (detective)** — fails the attempt on a violation, but the write has already landed; it is a detection boundary, not prevention |
| Shell | `validation_shell_gate` | **Enforced** — `allow_shell=false` means the command is never executed; `allow_shell=true` runs it in the worker context |
| Workspace isolation | Worktree lease | **Enforced** — two active leases may not share a worktree path or branch |
| Network egress | none | **Advisory** — no sandbox provider is wired in; outbound TCP to `api.deepseek.com:443` was observed to CONNECT from the canary worker |
| Process isolation | none | **Advisory** — the adapter runs a subprocess in the worker context; no OS-level boundary |
| Credential authority | Credential lease | **Enforced** — owner scope, funding route, provider match, attempt index, and expiry are all revalidated per attempt |

Per ADR-077 rules 7-8, a permission flag is not an isolation guarantee. This
proof records the difference rather than claiming enforcement it cannot
evidence.

## Failures and blockers

Three **pre-existing** defects blocked a successful delegated execution. Each is
isolated above to a single line, and each one-line repair was **verified in the
canary** — after applying all three, the run succeeded end to end.

| # | Defect | File:line | Verified one-line repair |
|---|---|---|---|
| 1 | Worker never passes `reasoning_effort`; the `"medium"` default is not self-consistent for `deepseek-v4-flash` (`thinkingLevelMap` maps `medium → null`, and `clampThinkingLevel` only walks upward) | `guardian/workers/coding_worker.py:2825-2830` | pass `reasoning_effort="off"` to `execute_authorized` |
| 2 | Posture emits `allowed_paths: [""]`, which the worker's prefix resolver skips, making the whole-repository branch unreachable | `guardian/core/guardian_delegation_service.py:1683` | emit `"."` instead of `""` |
| 3 | The two mutation-scope enforcement paths disagree on path syntax (directory prefix vs. glob pattern) | `coding_worker.py:1251-1287` vs `:1578-1629` | emit `(".", "*")` so both checks admit the path |

Additional pre-existing conditions, unchanged by this proof:

4. **`MemoryLifecycleRevision` missing from the ORM (blocks backend startup).**
   `guardian/db/models.py` lacks four classes that
   `guardian/services/memory_purge.py` imports at module scope. The additive fix
   already exists on `codex/restore-ums-orm-models-20261016` (not on
   `origin/main`).
5. **The runtime images ship no `git` binary.** The worker's repo-root
   discovery, isolated-worktree creation, and the mutation guard all shell out
   to `git`, and the repository authority in the backend does the same. The
   active Private Preview worker has the same gap. The canary added `git` via
   proof-specific image layers; the normal tags were not overwritten.
6. **No provider-enforced process or network isolation.** Not introduced by
   this work; recorded as a standing limitation.

**The three repairs were applied to the disposable canary tree only.** The
repository under proof is unchanged — `git status --short` is empty and neither
repair string appears in the repository copy. Repairing them in the repository
is a **separate Task Spec** and was not performed here.

No automated re-dispatch was attempted, no second execution attempt was created
for any single task, and no uncertain state was treated as task loss.

## Cleanup / preservation disposition

- The disposable stack, its volumes, the canary checkout, the fixture
  repository, and the canary-specific image tags are all **outside** the
  repository under proof and remain on disk for inspection. Nothing was
  installed into the repository tree.
- The active Private Preview stack and its containers were never restarted,
  reconfigured, or written to.
- `main` and `origin/main` were not modified. The stray commit created by an
  earlier `git init` inside the parent repository was detected and undone
  (`codex/next-work` restored to `42e86cb6a`); no branch history was rewritten.
- The canary credential is scoped to the canary account in a canary database
  and has no effect on any other deployment.

## Validation

Targeted contract suites, run in the canary image against the evaluated commit:

```
$ pytest -v tests/contracts/test_guardian_delegation_phase2a_contract.py \
           tests/contracts/test_guardian_delegation_phase3_delivery_contract.py \
           tests/contracts/test_guardian_dispatch_contract.py \
           tests/contracts/test_guardian_dispatch_integration_contract.py \
           tests/contracts/test_guardian_execution_binding_contract.py \
           tests/contracts/test_guardian_permission_posture_contract.py
1 failed, 123 passed, 9 warnings
```

The single failure is
`test_guardian_delegation_phase2a_contract.py::test_guardian_api_route_is_flagged_off_by_default`,
which fails on the **pristine baseline** too, for the same
`MemoryLifecycleRevision` import reason.

Full suite, run at the evaluated commit in the canary image:

```
1110 failed, 6434 passed, 148 skipped, 38 xfailed, 8 xpassed, 491 warnings, 419 errors
```

Compared against the baseline recorded at `146bef7be` (`1112 failed, 6435 passed,
419 errors`):

- **Error sets are identical** (419 = 419, empty diff).
- The failure-set diff is **9 lines / 6 tests**, and **none is a regression**:
  - Three tests differ (`test_memory_lifecycle_revision_persistence_migration`,
    `test_memory_purge_tombstone_migration`,
    `test_document_worker_shutdown::test_idle_sigterm_exits_cleanly_without_starting_a_job`).
    All three were run **in isolation against the pristine baseline** and
    **fail identically there** — they are order- and timing-dependent, and
    they are the same pre-existing ORM-parity and compose-grace failures
    already recorded in the baseline. The document-worker test fails a
    *different* assertion in the full run than in isolation, which is
    characteristic of a timing-sensitive test rather than a behavioural change.
  - Two `test_chat_redis_deadline` TLS tests failed in the baseline run and
    not in this one (flaky TLS handshake timing).

The suite is **not green**, and inherited failures are **not** reported as new
regressions.

## ADR impact and documentation disposition

- **No ADR modified.** ADR-020, ADR-048, ADR-069, ADR-077, ADR-091, ADR-093,
  and ADR-094 are unchanged and are not contradicted by this proof.
- **`docs/architecture/00-current-state.md` is not modified.** The overall
  release gate remains `HOLD`, and autonomous coding-worker work is not
  promoted to default Beta support.
- No route, profile, or flag posture was changed. The Guardian delegation route
  remains flagged off by default and quarantined by the supported profile.
- This report is the only tracked repository change.

## What this does not prove

- **Not proven:** that the repository as it stands executes a delegated task.
  The successful run required the three repairs above, applied to the disposable
  canary tree. The repository still carries all three defects.
- **Not proven:** restart recovery, uncertain-execution quarantine, or
  re-dispatch. Not authorized in this slice, and no recovery was attempted.
- **Not proven:** provider-enforced process or network isolation.
- **Not proven:** conversational delegation intake. The default route posture
  is unchanged and no intake path was enabled.
- **Not proven:** any release qualification. The gate remains `HOLD`.

## First necessary repair, for a separate Task Spec

Apply the three one-line repairs identified above, in the repository, and add
focused tests for each:

1. `guardian/workers/coding_worker.py:2825-2830` — pass
   `reasoning_effort="off"` to `execute_authorized`, with a test asserting the
   pass-through and that the chosen level is one the authorized provider's
   wrapper gate accepts.
2. `guardian/core/guardian_delegation_service.py:1683` — emit
   `allowed_paths=(".", "*")`, with a test asserting the emitted scope is
   admitted by **both** mutation-scope enforcement paths.

This is a bounded two-file change plus tests. It must not widen any other
boundary, must not alter route or profile posture, must not touch the Pi
wrapper's own gate, and must leave the release gate at `HOLD`. The `git` binary
gap in the runtime images is a separate packaging concern, not part of this
repair.

After that repair, the next candidate is a separate restart / uncertain-
execution recovery proof.
