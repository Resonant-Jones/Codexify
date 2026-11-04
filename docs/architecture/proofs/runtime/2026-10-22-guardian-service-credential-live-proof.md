# Guardian Delegation — Service-Owned Credential, Live End-to-End Proof

**Evaluated commit:** `089445dee6dfff2975dde806044d0c11e8e34a3a`
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-23
**Final classification:** **PASS**

One Guardian-authorized coding delegation executed end to end against the
committed feature-branch implementation, using a **service-owned** DeepSeek
credential, in a fully isolated synthetic environment, and returned its result
to the originating Chat Thread.

This is a functional execution canary. It does not establish preventive
sandbox isolation, restart recovery, or release qualification.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Evaluated HEAD | `089445dee6dfff2975dde806044d0c11e8e34a3a` |
| `git merge-base --is-ancestor 089445dee HEAD` | true (HEAD is the evaluated commit) |
| Working tree at start | clean |
| Service-selection repair present | `list_service_credential_candidates` at `guardian/agents/execution_credentials.py:133`; `_select_service_credential` at `guardian/core/guardian_delegation_service.py:1631`; wired in at line 1598 |
| Python import origin | `guardian` → `<worktree>/guardian/__init__.py`; `guardian.core.guardian_delegation_service` → `<worktree>/guardian/core/guardian_delegation_service.py` — **worktree-correct**, not the shared virtualenv's editable installation of main |

The build context was produced by `git archive 089445dee` and restricted to the
paths the Dockerfile consumes, with the repository's own `.dockerignore`
exclusions applied by hand. It contained no credential material. The three
application files that carry the repair and the restored ORM mappings hash
identically in the build context, in both containers, and in the worktree:

| File | SHA-256 |
|---|---|
| `guardian/db/models.py` | `551d7a39a3fb88b04e9a0d6af6cbfafd3d0d6f2f511a1188b1d93808651fc87c` |
| `guardian/core/guardian_delegation_service.py` | `c2d85a9800bcb7bdce0473bcd9f6b45147b0420ddbde6bf91c30187c5c31d48f` |
| `guardian/agents/execution_credentials.py` | `60bf8c73a0e5f5227727b8930f86b19f91311fd354e8471a355b0d5f66f29c84` |

---

## 2. Proof images

| Image | Identity | Size |
|---|---|---|
| `codexify-backend-runtime:svc-canary-20261023` | `sha256:644d131b8a1a5cf4ad7ee891e54168bd4b309f43fb94fbc91e7105b3da4f9c9f` | 4.79 GB |
| `codexify-worker-coding-runtime:svc-canary-20261023` | `sha256:6b7e2170b03d799ff8a1d8f0083fcdbac3271ee8a055e739195040de466363e7` | 5.30 GB |

Both were built from the exact evaluated commit through the Docker daemon's
BuildKit endpoint. The buildx CLI cannot be used on this machine — it
unconditionally renames a builder activity file and `rename`-over is denied by
the execution sandbox — and the classic builder is unusable because it
silently skips this Dockerfile's `RUN python - <<'PY'` heredocs. The daemon
endpoint runs the same BuildKit frontend, and a separate probe confirmed the
heredoc executed rather than being skipped.

Normal image tags were not touched: `codexify-backend-runtime:latest` =
`7a08e1defa43`, `codexify-worker-coding-runtime:latest` = `a3177274d0b5`, and
the prior proof tags `git-proof-a70ca1465` = `891cb0f57f77` / `40e8b035e9b7`.
No historical canary image was reused.

---

## 3. Environment isolation

| Resource | Canary | Binding |
|---|---|---|
| Compose project | `codexify_svc_canary_20261023` | dedicated |
| PostgreSQL 15 | `codexify_svc_canary_20261023-db-1` | `127.0.0.1:15443` only |
| Redis 7 | `codexify_svc_canary_20261023-redis-1` | `127.0.0.1:16390` only |
| Backend | `codexify_svc_canary_20261023-backend-1` | `127.0.0.1:18899` only |
| Coding worker | `codexify_svc_canary_20261023-worker-coding-1` | no ingress |
| Network | `codexify_svc_canary_20261023_default` | private, 4 containers |
| Volumes | pgdata, redisdata, data, worktrees | dedicated |

**Not mounted or shared:** any Private Preview volume, container, database, or
credential; any production database; any user workspace; any operator
credential store; any Pi authentication directory; any host source tree. The
only host bind mounts are `config/` and `docs/builtin-help/` from the
build context, read-only, because the `runtime` image stage does not bake them
in. The provider credential was never placed in an image, a container
environment, a mount, or a log line — it reached the worker only as a
per-attempt lease.

**Private Preview was untouched throughout:** `GET /` → 200 and `GET /health`
→ 200 on its mapped port, image digests unchanged, no Private Preview volume
or container modified.

---

## 4. Credential authority (secret-free)

**The key.** The DeepSeek provider key supplied through the authorized service
custodian was compared by **equality only** against every known credential
source on this machine — the operator repository `.env`, `.env.tester`,
`.env.private-preview`, and the Pi auth store. It is **distinct from all of
them**: it is the dedicated test key created for this qualification. No value,
prefix, suffix, length, or fingerprint was displayed at any point.

Only `DEEPSEEK_API_KEY` was extracted from the custodian file into isolated
custody (mode 600, outside the tracked repository). The source file carries 38
variables; the other 37 — including a GitHub PAT, a Tailscale key, and the
Private Preview's `GUARDIAN_API_KEY` — were deliberately left behind and never
entered the canary.

**Ownership and authorization.** The operator explicitly ruled that the
credential is **Codexify service-owned** and authorized its use for this test.
It was registered through Guardian's canonical custody authority
(`guardian.agents.execution_credentials.store_api_key`), inside the canary
backend so the canary's own encryption key applied. The HTTP convenience route
`POST /api/agents/coding/credentials` was **not** used: it hard-codes
`owner_scope="account"` and `funding_route="user_byok"`, which would have
misrepresented the owner.

**Persisted credential row** (read back from the canary database):

```
credential_ref        ccr_d4c2305b91b8425faace5f1138723105
owner_scope           service
owner_id              codexify-service
source_class          service_api_key
provider_id           deepseek
funding_route         codexify_metered
usage_policy_ref      usage-policy-codexify-metered
allowed_account_ids   ["canary-svc-20261023"]
allowed_model_ids     ["deepseek-v4-flash"]
status                active
secret stored         encrypted
```

**Custody disposition.** The registration is revoked at teardown and the
at-rest secret destroyed (the schema's
`ck_coding_execution_credentials_secret_status` requires
`status='revoked' AND encrypted_secret IS NULL`; revocation *is* secret
destruction by design). The extracted key file is truncated to zero bytes. The
**provider-side** key is *not* revoked at the provider — that action was not
separately authorized, and no provider-side revocation is claimed. The key
remains the operator's to rotate.

---

## 5. Synthetic lineage and readiness

| Entity | Identity |
|---|---|
| Account | `canary-svc-20261023` (direct insert, canary-scoped, no interactive login) |
| Project | id `1`, name `General`, `system_role=general` — created by the product's own `seed_account_default_projects` |
| Chat Thread | id `1` |
| Source message | id `1`, authored `user` chat message, 196 characters |
| Repository binding | `c78fd141-5c2b-4918-a27c-33135e78e221`, `canonical_root=/worktrees/canary-fixture` |
| Fixture repository | head `6db4f10a9fc512da7cb716cd31fe92cf9dcdef7a`, a real Git working tree created inside the canary worker |

**Readiness confirmed:**

* Backend `/health` → 200, no startup-failure receipt.
* The canonical Alembic graph reached its **actual** head `f0d7c4b2a198`
  (123 revisions, 135 public tables). The four restored UMS tables
  (`memory_revisions`, `memory_review_revisions`,
  `memory_lifecycle_revisions`, `memory_purge_tombstones`) are all present.
  The actual graph was inspected rather than relying on any inherited
  terminal-head assertion.
* Coding-worker readiness: `ready`; Pi runtime `pi-coding-agent 0.82.1`;
  `node_executable`, `guardian_pi_wrapper`, `pi_sdk_runtime`,
  `git_executable`, `adapter_initialization` all `available`.
* Provider/model resolution: `deepseek` / `deepseek-v4-flash`, and
  `deepseek-v4-flash` is the model the Pi SDK's own `deepseek` provider
  registry lists, so the harness resolved it from its registry rather than
  from a stub.
* Service credential policy: valid, active, and scoped to this account and
  model.

---

## 6. Guardian authorization

Driven through Guardian's own service boundary
(`GuardianDelegationService.create_intent` → `approve_intent` →
`dispatch_delegated_task`). No AgentRun and no CodingExecutionTask was
inserted by hand, and no credential reference was injected through a request
parameter.

| Stage | Evidence |
|---|---|
| Intent | `gdi_8664a398e507432c` — `intent_status=accepted`, `acceptance_status=accepted` |
| Approval | `approval_state=approved`, `approval_mode=scoped_auto` |
| Run | `run_56ed123f3ffe4b0c` |
| Deployment | `dep_e034592525ab475c` |
| Coding task | `gct_bf36f950b34a4c63` |
| Attempt | `gat_b9f49d37d2544040` |
| Dispatch | `dispatch_state=dispatched`, `dispatch_count=1`, `task_id=a650a060-2696-4980-a37f-c949e158f296` |
| Permission posture | enforced: `validation_shell_gate`, `git_mutation_guard`, `worktree_lease_isolation`; advisory: `network_egress`, `process_isolation` |
| Permission policy | `allow_network=false`, `allow_shell=true`, `allow_write=true`, `allowed_paths=["."]`, `max_runtime_seconds=300` |

### Credential selection and authorization

The service-owned credential was discovered, submitted to the existing
authorization authority, and authorized. The issuance is recorded by exactly
one durable lease:

```
lease_id        cl_3c474339752c4e71893a115435490393
binding_id      xeb_7b582373ed9947509b492faf9a052d50
attempt_id      gat_b9f49d37d2544040
attempt_index   1
credential_ref  ccr_d4c2305b91b8425faace5f1138723105
owner_scope     service
owner_id        codexify-service
account_id      canary-svc-20261023
issued_at       2026-10-23T08:53:41Z
expires_at      2026-10-23T08:55:41Z   (2-minute lease lifetime)
```

The lease carries the credential's **actual** owner, not a relabelled one.

### Execution binding (durable, from the deployment spec)

```
schema_version             2
provider_id                deepseek
model_id                   deepseek-v4-flash
harness_id                 pi
harness_selection_mode     default
placement                  container
reasoning_effort           off
credential_ref             ccr_d4c2305b91b8425faace5f1138723105
credential_owner_scope     service
credential_owner_id        codexify-service
credential_type            api_key
credential_source_class    service_api_key
funding_route              codexify_metered
usage_policy_ref           usage-policy-codexify-metered
max_attempts               1
user_id                    canary-svc-20261023
project_id / thread_id / source_message_id / coding_task_id / attempt_id   carried
authorization_evidence_ref  xeb_7b582373ed9947509b492faf9a052d50
```

Every expected value held: provider `deepseek`, model `deepseek-v4-flash`,
harness `pi`, `reasoning_effort=off`, owner scope `service`, owner
`codexify-service`, funding route `codexify_metered`, `allowed_paths=(".",)`.
The binding version is 2, which is the effort-governed discriminator, and the
effort is carried in the binding rather than selected by the worker.

---

## 7. Durable and queued bindings agree

The queued payload was consumed destructively by the worker, so the queued
side is reconstructed from the task's own completed event — the payload the
worker actually received and executed.

| Comparison | Result |
|---|---|
| Durable binding id | `xeb_7b582373ed9947509b492faf9a052d50` |
| Queued binding id | `xeb_7b582373ed9947509b492faf9a052d50` |
| Binding fields compared | 20 |
| Fields that differ | **0** |
| Artifact provenance identical to queued provenance | true |

The three fields the runtime provenance projection drops
(`max_attempts`, `reasoning_effort`, `schema_version`) are present in the
durable binding; the seven the harness adds
(`requested_provider_id`, `requested_model_id`, `actual_provider_id`,
`actual_model_id`, `actual_harness_id`, `actual_harness_version`,
`runtime_identity_established`) are runtime observations.

**The worker's own boundary is the authority here, and it passed:**
`guardian/workers/coding_worker.py:1895` raises
`execution_binding_queue_mismatch` when the task's binding differs from the
persisted one, and line 1915 raises
`execution_binding_lineage_mismatch` on a lineage divergence. The attempt
completed, so the worker found the queued and persisted bindings equal.

---

## 8. Worker, Pi, and provider observations

The worker executed the task and reported the real runtime identity:

```
requested_provider_id          deepseek
actual_provider_id             deepseek
requested_model_id             deepseek-v4-flash
actual_model_id                deepseek-v4-flash
actual_harness_id              pi-coding-agent
actual_harness_version         0.82.1
runtime_identity_established   true
```

`runtime_identity_established` is set only after the Pi wrapper resolves the
model from the SDK's own provider registry and reports the identity it
actually ran under. The requested and effective provider and model are equal,
so no provider or model substitution occurred.

**Reasoning effort.** Guardian's binding authorized `off`, and the adapter
fails closed unless the requested *and* effective effort both equal the
authorized value
(`guardian/agents/adapters/pi_codex_runner.py:549-552`). The attempt
succeeded, so requested == effective == `off`. The effort was Guardian-owned
and reached the harness unchanged; the worker selected no level of its own.

**One attempt.** The run's event stream holds exactly two events —
`task.running` then `task.completed` — both carrying
`attempt_id=gat_b9f49d37d2544040`. The database holds exactly one lease
(`attempt_index=1`), one credential row, and one artifact. There was no
automatic retry, no second attempt, and no credential fallback.

**Secret exclusion.** The leased secret was checked for presence — without
printing it — in the durable binding, the queued payload, the deployment
spec, and the result artifacts:

| Blob | Secret present |
|---|---|
| Durable execution binding | **false** |
| Queued task payload | **false** |
| Deployment spec | **false** |
| Result artifacts | **false** |

The credential reached the harness on the subprocess **stdin**, not in argv,
not in the environment, and not in any durable record
(`pi_codex_runner.py:222,256`).

---

## 9. Fixture mutation and scope validation

The mutation guard was enabled and reported the change it detected:

```
mutation_guard_enabled     true
mutation_guard_status      within_allowed_paths
allowed_paths              ["."]
changed_paths              ["canary_marker.txt"]
disallowed_paths           []
changed_paths_total        1
mutation_guard_error_code  null
```

The intended fixture diff, read from the Git working tree:

```diff
diff --git a/canary_marker.txt b/canary_marker.txt
index bfd6755..e1da6d0 100644
--- a/canary_marker.txt
+++ b/canary_marker.txt
@@ -1,2 +1,3 @@
 guardian-canary-fixture
 expected: the harness appends one line beginning with 'canary-ok:'
+canary-ok: pi-agent verification line
```

Exactly one file, exactly one harmless line, matching the synthetic
instruction. Nothing else in the repository changed. **No commit was
created** — the fixture head is still `6db4f10`, `commit_status=not_requested`,
`commit_hash=null`, `merge_ready=false`, `human_review_required=true`. The
worktree directory contained only the fixture.

One honest observation: the adapter's own `files_changed` list was empty and
`patch_artifact` was null, while the mutation guard independently detected
`canary_marker.txt` and the Git working tree shows the change. The guard's
detection and the working tree agree; the adapter's self-report did not. The
Git working tree is the ground truth here.

---

## 10. Terminal result and source-thread readback

| Evidence | Value |
|---|---|
| `agent_runs.status` | `succeeded` |
| `agent_runs.error` | `null` |
| `agent_runs.ended_at` | `2026-10-23T08:53:47Z` |
| Result artifact | 1 row, `artifact_type=coding_result`, `status=ok`, `summary="Guardian-authorized Pi task completed"` |
| Delivery | `result_captured_by_guardian=true`, `delivery_ok=true`, `delivery_reason=null` |
| Errors | `errors=[]`, `error_code=null`, `error_message=null` |
| Thread messages | 2 in total |

The originating Chat Thread holds **exactly one** result message alongside the
authored request:

```
id=1  role=user       kind=chat           (the synthetic instruction)
id=2  role=assistant  kind=coding_result
     "## Guardian Delegation Result
      **Status**: OK
      **Intent ID**: `gdi_8664a398e507432c`
      **Run ID**: `run_56ed123f3ffe4b0c`
      **Summary**: Guardian-authorized Pi task completed"
```

The canonical database readback — the same `chat_messages` table the product
reads — confirms the result is durable and is associated with this attempt.

---

## 11. Validation results

Focused checks against the evaluated worktree, on disposable PostgreSQL:

| Selection | Result |
|---|---|
| `tests/contracts/test_guardian_delegation_phase2a_contract.py` | pass |
| `tests/contracts/test_guardian_execution_binding_contract.py` | pass |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | pass |
| `guardian/tests/agents/test_execution_credentials.py` | pass |
| `guardian/tests/agents/test_pi_readiness.py` | pass |
| **Total** | **99 passed, 0 failed** |

**Full-suite status: NOT RUN.** A monolithic `pytest -v` was not executed. The
shared 7.7 GB Docker VM hosts the operator's live Private Preview, and a prior
monolithic run in that environment exhausted the VM and restarted unrelated
services. The focused selection above, together with the live execution
evidence, is the retained proof.

---

## 12. Known containment limitations

* This is a **functional execution canary**. It is **not** ADR-077 sandbox
  conformance.
* The Git mutation guard is **detective, not preventive**: it inspects the
  working tree after execution and fails the attempt on an out-of-scope
  mutation. It does not confine the worker's writes.
* **Provider-enforced filesystem, process, and network isolation remains
  unproven.** The posture records `network_egress` and `process_isolation` as
  *advisory*, not enforced. The previous canary's observation of worker
  network egress despite `allow_network=false` is neither reproduced nor
  resolved here; this run made no egress measurement, and the trusted
  adapter/provider inference traffic is not to be conflated with
  model-controlled tool egress.
* The execution was **not** performed in an isolated Git worktree: the run
  carries `worktree_id=null` and `worktree_path=null`, because
  `CODING_WORKER_WORKTREE_ISOLATION` was not enabled for this runtime. The
  mutation was therefore detected in, and confined to, the bound fixture
  repository — the disposable fixture was the only thing present under
  `/worktrees`, and nothing outside it changed.
* **Restart recovery remains unproven.** The run is durably `succeeded`; no
  restart or uncertain-execution recovery was exercised.
* The `files_changed`/`patch_artifact` observation in section 9 is an
  unresolved reporting asymmetry, recorded rather than patched.

---

## 13. ADR impact and invariants

* **ADR-020, ADR-065, ADR-069, ADR-077, ADR-093, ADR-094** — unchanged. No
  ADR was modified. This run is implementation evidence that ADR-094 §§12 and
  34 hold in practice: a service-owned credential was selected through existing
  trusted policy, and it served an account invocation while remaining
  service-owned and metered.
* Guardian owned the delegation authorization throughout; the credential's
  owner, funding route, model policy, and usage policy all came from
  existing durable state, never from a request parameter.
* Service ownership was never reinterpreted. The binding and the lease both
  carry `service` / `codexify-service` / `codexify_metered`.
* No ambient secret became task authority; the provider credential existed
  only inside the encrypted credential store and the per-attempt lease.
* Reasoning effort remained Guardian-owned (`off`, carried in a v2 binding)
  and reached the harness unchanged.
* Write scope could not expand after authorization: the mutation guard
  confirmed the change was within `["."]`, and nothing outside the fixture
  changed.
* One attempt remained one attempt.
* PostgreSQL remained canonical for durable execution state, and the result
  was read back from it.

---

## 14. Cleanup

* Disposable worker and backend stopped; PostgreSQL and Redis containers
  removed; the dedicated Docker network removed.
* The extracted key file truncated to zero bytes; the canary credential
  registration revoked with its at-rest secret destroyed.
* Normal production image tags verified unchanged; Private Preview verified
  healthy after teardown.
* Only secret-free evidence is retained. The provider-side key was **not**
  revoked at the provider, and no provider-side revocation is claimed.

---

## 15. Classification

**PASS.** The functional lifecycle is proven end to end: exact committed source
booted without overlays; a service-owned credential was selected and authorized
under existing trusted policy; the binding preserved service ownership and
metered funding; Guardian approved and dispatched; the durable and queued
bindings agreed; the worker executed through the real Pi harness
(`pi-coding-agent 0.82.1`) against `deepseek-v4-flash`; the requested and
effective identities matched; the permitted fixture mutation succeeded; scope
validation passed; the terminal state is durable; exactly one result artifact
was persisted; and exactly one result reached the originating Chat Thread and
survived canonical readback. No retry, no fallback, and no production-state
modification occurred.

**A functional PASS does not change release status.** Release qualification
remains **HOLD**. The next separate task is restart and uncertain-execution
recovery qualification.

### Confirmations

* No account-ownership misrepresentation — the credential was registered and
  executed as service-owned, metered, with its real owner on the binding and
  the lease.
* No unauthorized operator credential use — the key used was the dedicated test
  key, byte-distinct from every operator credential, explicitly authorized for
  this test.
* No application-source overlays — the images were built from the exact
  evaluated commit and the source hashes were verified inside both containers.
* No production modification — the Private Preview served 200 on `/` and
  `/health` throughout, with image digests and volumes untouched.
* No automatic second attempt — one intent, one attempt, one lease, one
  artifact, one result.
* Conversational intake remains unavailable.
* Restart recovery remains unproven.
* Provider-enforced sandbox isolation remains unproven.
* Release qualification remains **HOLD**.

### Artifacts

* Proof receipt: `docs/architecture/proofs/runtime/2026-10-22-guardian-service-credential-live-proof.md`
* Evaluated commit: `089445dee6dfff2975dde806044d0c11e8e34a3a`
* Proof images: `sha256:644d131b8a1a5cf4ad7ee891e54168bd4b309f43fb94fbc91e7105b3da4f9c9f`
  (backend), `sha256:6b7e2170b03d799ff8a1d8f0083fcdbac3271ee8a055e739195040de466363e7`
  (worker)
* Credential reference: `ccr_d4c2305b91b8425faace5f1138723105` (revoked at
  teardown, at-rest secret destroyed)
* Intent / run / deployment / task / attempt / binding / lease:
  `gdi_8664a398e507432c` / `run_56ed123f3ffe4b0c` / `dep_e034592525ab475c` /
  `gct_bf36f950b34a4c63` / `gat_b9f49d37d2544040` /
  `xeb_7b582373ed9947509b492faf9a052d50` / `cl_3c474339752c4e71893a115435490393`
* Previous BLOCKED receipts are unchanged and remain accurate for their own
  evaluated commits.
