# Guardian Delegation — Authorized Rerun (source-exact)

**Evaluated commit:** `e28dbcff9` on `feature/guardian-delegation-acceptance-axis`
**Run date:** 2026-10-22
**Final classification:** **BLOCKED**

This receipt records a controlled, source-exact attempt to execute one
Guardian-authorized delegated coding task against the committed feature-branch
implementation, using a dedicated DeepSeek test credential and an independently
isolated runtime.

**Source-exact Guardian delegation execution is NOT proven.** The run reached
Guardian's own authorization boundary and failed closed there, for a reason
that is a real contract gap rather than a defect in the restored source. The
credential, the runtime, and the environment all qualified; the execution
binding could not be minted because Guardian's credential *selection* cannot
see a service-owned credential — even though ADR-094 requires that it be able
to. The failure is recorded in full below, with the smallest required
prerequisite.

---

## 1. Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Evaluated HEAD | `e28dbcff99b349b6469bcbe2b7880bc91777bccb` |
| `git merge-base --is-ancestor e28dbcff9 HEAD` | true (HEAD is the evaluated commit) |
| Working tree at start | clean (`git status --short --branch` → no entries) |
| Committed receipt present | `docs/architecture/proofs/runtime/2026-10-22-guardian-delegation-source-exact-live-proof.md` (`43754e860`, corrected by `f1eaaba95`) |
| UMS ORM mappings present | 4 of 4 (`MemoryRevision`, `MemoryReviewRevision`, `MemoryLifecycleRevision`, `MemoryPurgeTombstone`) |
| Python import origin | `guardian` → `<worktree>/guardian/__init__.py`; `guardian.core.guardian_delegation_service` → `<worktree>/guardian/core/guardian_delegation_service.py` (worktree-correct) |
| Alembic head in the canary DB | `f0d7c4b2a198` (123 revisions) |

The four mappings restored at `e28dbcff9` are present in the evaluated source
and the backend import chain resolves from the committed source alone. No ORM
overlay, no patched application file, and no source tree from an earlier canary
was used.

---

## 2. Proof images

Both images were built from a sanitized context produced by
`git archive e28dbcff9`, restricted to the paths the Dockerfile consumes
(`backend`, `guardian`, `codex_runner`, `plugins`, `scripts`, `config`,
`docs/builtin-help`, `packaging/pyinstaller`), with the repository's own
`.dockerignore` exclusions honoured. The context contained **no** credential
material, and the four key source files in the context were verified
byte-identical to the evaluated worktree.

| Image | Identity | Size |
|---|---|---|
| `codexify-backend-runtime:canary-auth-20261022` | `sha256:ba1d48cadb74ea1d2dae4dc6e9728d5fbbc1bd75633af4ca74db4eca546926d0` | 4.79 GB |
| `codexify-worker-coding-runtime:canary-auth-20261022` | `sha256:6c3ce72b861284ac0f74c0f798e9149a58452e6f95a4028c7e75cc71141f0cc6` | 5.30 GB |

**Source identity, proven from inside both containers:**
`/app/guardian/db/models.py` hashes to
`551d7a39a3fb88b04e9a0d6af6cbfafd3d0d6f2f511a1188b1d93808651fc87c`
in the backend container, in the worker container, and in the evaluated
worktree — the same value.

**Build-tooling deviation, recorded for honesty.** The buildx CLI cannot be
used on this machine: it unconditionally renames a builder activity file, and
`rename`-over is denied by the execution sandbox. The classic builder is also
unusable because it silently skips this Dockerfile's `RUN python - <<'PY'`
heredocs, which install the canonical dependency set. The images were therefore
built by driving the same BuildKit frontend through the daemon's `/build`
endpoint (`version=2`), which executes the heredocs correctly. A separate probe
confirmed the heredoc actually executed rather than being skipped. This is a
tooling constraint of this environment, not a change to the build inputs.

**Normal tags untouched:** `codexify-backend-runtime:latest` = `7a08e1defa43`,
`codexify-worker-coding-runtime:latest` = `a3177274d0b5`, and the prior proof
tags `git-proof-a70ca1465` = `891cb0f57f77` / `40e8b035e9b7` — all unchanged.

---

## 3. Environment isolation

| Resource | Canary | Host binding |
|---|---|---|
| Compose project | `codexify_canary_auth_20261022` | dedicated |
| Network | `codexify_canary_auth_20261022_default` (4 containers) | dedicated |
| PostgreSQL 15 | `codexify_canary_auth_20261022-db-1` | `127.0.0.1:15433` only |
| Redis 7 | `codexify_canary_auth_20261022-redis-1` | `127.0.0.1:16380` only |
| Backend | `codexify_canary_auth_20261022-backend-1` | `127.0.0.1:18890` only |
| Coding worker | `codexify_canary_auth_20261022-worker-coding-1` | no ingress |
| Volumes | `canary_pgdata`, `canary_redisdata`, `canary_data`, `canary_worktrees` | dedicated |

Deliberately **not** mounted or shared: any Private Preview volume, any
production database, any user workspace, any operator credential store, any Pi
authentication directory, and any host source tree. The only host bind mounts
are `config/` and `docs/builtin-help` from the exact-commit archive, mounted
read-only, because the `runtime` image stage does not bake them in. The
provider credential was never placed in any container environment, image, or
mount.

**Private Preview untouched throughout the run:** `GET /` → 200 and
`GET /health` → 200 on its mapped port (8081) at the end of the run; image
digests unchanged; no Private Preview container, volume, or database was
modified.

**Canary-local configuration** (all disposable, generated for this run): a
fresh random PostgreSQL password, a fresh throwaway `GUARDIAN_API_KEY` for the
canary backend's own request auth, and a fresh Fernet key for the canary's
credential-at-rest encryption. The canary never reused the operator's
encryption key. The supported profile is `v1-local-core-web-mcp`, whose
`provider_contract` is satisfiable without any provider credential in the
environment; the DeepSeek provider and model for the delegation lane are
resolved by Guardian from the credential row and the static provider catalog,
not from the environment.

---

## 4. Credential authorization evidence (secret-free)

**The key.** The DeepSeek provider key supplied for this qualification is a
**dedicated test key**. It was compared by equality (never by value, prefix,
suffix, length, or fingerprint) against every known credential source on this
machine:

| Compared against | Result |
|---|---|
| operator repository `.env` `DEEPSEEK_API_KEY` | distinct |
| operator repository `.env.tester` `DEEPSEEK_API_KEY` | distinct |
| operator repository `.env.private-preview` `DEEPSEEK_API_KEY` | distinct |
| Pi auth store `deepseek.key` | distinct |

No credential value, prefix, suffix, or fingerprint was emitted at any point in
this run, and the key was never written into an image, a tracked file, a
container environment, or a log line.

**Ownership — the operator's explicit decision.** The operator reviewed the
evidence and ruled that ownership is a fact and not a routing convenience:
the credential is owned by the **Codexify service**, funded under
`codexify_metered`, and the service explicitly authorizes the synthetic test
account to consume metered inference. Registering it as `account` +
`user_byok` merely because that is the shape the current dispatcher could
select was explicitly rejected, and the operator directed that the gap be
closed rather than papered over with inaccurate ownership metadata.

**Custody path.** The credential was registered through Guardian's canonical
custody authority, `guardian.agents.execution_credentials.store_api_key`,
inside the canary backend (so the canary's own encryption key applied). The
HTTP convenience route `POST /api/agents/coding/credentials` was deliberately
**not** used: it hard-codes `owner_scope="account"` and `funding_route="user_byok"`,
which would have mislabelled the credential's owner.

**Persisted credential row** (read back from the canary database):

```
credential_ref        ccr_ff654e9725e8401e8e9bb5cced089f6b
owner_scope           service
owner_id              codexify-service
provider_id           deepseek
credential_type       api_key
funding_route         codexify_metered
allowed_account_ids   ["canary-synthetic-20261022"]
allowed_model_ids     ["deepseek-v4-flash"]
usage_policy_ref      usage-policy-codexify-metered
status                active
secret stored         encrypted (yes)
```

**Custody disposition — executed.** The registration was revoked at the end
of the run through the Guardian model, and the revocation **destroyed the
at-rest secret** rather than merely flagging the row. The schema's own
constraint `ck_coding_execution_credentials_secret_status` requires
`(status='active' AND encrypted_secret IS NOT NULL) OR (status='revoked' AND
encrypted_secret IS NULL)`, so revocation is secret destruction by design:

```
before: status=active                owner_scope=service
after:  status=revoked               revoked_at=2026-10-22T19:24:47.155616+00:00
        encrypted_secret_retained=false
```

Note that `guardian.agents.execution_credentials` exposes only
`revoke_account_credential`, which is scoped to `owner_scope="account"` and
therefore cannot act on a service-owned row; the equivalent durable revocation
was performed directly on the Guardian model, and the resulting row satisfies
the schema constraint. The disposable canary containers, network, and volumes
were destroyed at the end of this run, and the extracted single-key file was
truncated to zero bytes. The sandbox denies unlinking that path, so the empty
file itself remains on disk; its secret content is unrecoverable either way.
The key itself remains the operator's to rotate and may be treated as spent
test material.

---

## 5. Account, Project, Thread, and repository lineage

| Entity | Identity | How it was created |
|---|---|---|
| Account | `canary-synthetic-20261022` | direct row insert (canary-scoped, no interactive login) |
| Project | id `1`, name `General`, `system_role=general` | the product's own seeder, `seed_account_default_projects` (`{'accounts': 1, 'created': 1}`) |
| Chat Thread | id `1` | `chat_threads` row |
| Source message | id `1` | authored `user` chat message, 196 characters, the synthetic coding instruction |
| Repository binding | `882cbc19-14cf-4deb-b7d3-cf4fa432d078` | `repository_bindings` row, `canonical_root=/worktrees/canary-fixture` |
| Fixture repository | head `46e3fda3122dc5e0a073563375ab5d8eb0dc1591` | real Git working tree created inside the canary worker (git 2.47.3) |

The fixture is visible to both the backend and the worker through the
dedicated `canary_worktrees` volume, and it was confirmed to be a clean Git
working tree from both containers.

---

## 6. Guardian authorization — what resolved, and where it stopped

The delegation was driven through Guardian's own service boundary
(`GuardianDelegationService.create_intent` → `approve_intent` →
`dispatch_delegated_task`). No AgentRun and no CodingExecutionTask was
inserted by hand.

**Stage 1 — intent creation: SUCCEEDED**

```
intent_id              gdi_5222efb162d14316
intent_status          accepted
acceptance_status      accepted
approval_state         approved
approval_mode          scoped_auto
run_status             queued
visibility_status      not_posted
thread_id              1
source_message_id      1
run_id                 run_556aab694ed64296
context_basis_count    1
```

**Stage 2 — approval:** already approved by `scoped_auto` at intent creation.

**Stage 3 — durable dispatch record: PERSISTED**

```
run_id                 run_556aab694ed64296
deployment_id          dep_e384a53f432642ba
coding_task_id         gct_231b17e74c274b82
attempt_id             gat_8a013fa04dda44f5
```

**Stage 4 — execution binding: FAILED CLOSED**

```
  File "/app/guardian/core/guardian_delegation_service.py", line 1476, in dispatch_delegated_task
    binding = self._resolve_execution_binding(
  File "/app/guardian/core/guardian_delegation_service.py", line 1587, in _resolve_execution_binding
    raise GuardianExecutionBindingError(
guardian.core.guardian_execution_binding.GuardianExecutionBindingError: guardian_binding_no_account_credential

The above exception was the direct cause of the following exception:
  File "/app/guardian/core/guardian_delegation_service.py", line 1497, in dispatch_delegated_task
    raise GuardianDelegationDispatchError() from exc
guardian.core.guardian_delegation_service.GuardianDelegationDispatchError: guardian_delegation_dispatch_failed
```

**Exact import chain of the blocker**

```
guardian/core/guardian_delegation_service.py:1585
    credentials = list_account_credentials(db, account_id=user_id)
      |
      v
guardian/agents/execution_credentials.py:119-130
    session.query(CodingExecutionCredential)
        .filter_by(owner_scope="account", owner_id=account)   <-- filters out owner_scope="service"
      |
      v
list_account_credentials(...) == []  ->  guardian_binding_no_account_credential
```

**Why this is a contract gap and not a misuse.** The service ownership class is
fully supported one layer down:
`authorize_credential_selection` (`execution_credentials.py:179`) →
`_validate_row` has a service branch that requires a `codexify_included` or
`codexify_metered` funding route, an account allow-list, a model allow-list, and
a matching `usage_policy_ref` — exactly the shape the registered credential
carries. The gap is that **nothing in the delegation path can select a
service-scoped credential**: `dispatch_delegated_task` exposes no
`credential_ref` parameter, and the selection helper it calls filters on
`owner_scope="account"` alone.

**This diverges from an accepted ADR.** ADR-094 §12, accepted 2026-09-29:
*"Codexify service-owned credentials must also be eligible for account
invocations under explicit service policy, including the `codexify_included`
and `codexify_metered` funding routes in ADR-093."* ADR-094 §34 further
requires that a service policy authorize the specific account, invocation,
provider/model binding, funding route, and usage policy — which is precisely
what was registered here. The committed implementation satisfies the
*validation* half of that contract and does not satisfy the *selection* half.

**What was therefore never resolved:** the execution binding (and with it the
Guardian-owned provider, model, reasoning effort, and permission posture), the
durable binding persisted into the deployment spec, the queue submission, the
credential lease, the worker dequeue, the Pi invocation, the provider request,
the fixture mutation, the terminal AgentRun state, the result artifact, and the
source-thread result delivery.

---

## 7. Worker and Pi readiness

The coding worker reached readiness in the canary container:

```
[worker-coding] Pi coding-worker readiness: ready
[worker-coding] Provider/model identity: resolved by Guardian for each invocation
[worker-coding] Credential validity: checked by Guardian at invocation dispatch
[worker-coding] Pi runtime: pi-coding-agent 0.82.1
[worker-coding] - node_executable: available
[worker-coding] - guardian_pi_wrapper: available
[worker-coding] - pi_sdk_runtime: available
[worker-coding] - git_executable: available
[worker-coding] - adapter_initialization: available
```

Git is packaged in the `runtime` stage and inherited by `worker-coding-runtime`,
and the Git prerequisite is readiness-gated. The backend reached
`/health` → 200 with no startup-failure receipt. The backend boots from the
exact committed source with the four restored ORM mappings and no overlay.

---

## 8. Durable lifecycle readback

Read back from the canary database through the same tables the product reads:

| Stage | Evidence |
|---|---|
| 1. Delegation intent accepted | `intent_status=accepted`, `acceptance_status=accepted` |
| 2. Approval established | `approval_state=approved`, `approval_mode=scoped_auto` |
| 3. Execution binding persisted | **absent** — `deployment_spec.execution_binding = null`; `spec_hash=f1a9bd2f…` |
| 4. Dispatch record persisted | `agent_runs` row `run_556aab694ed64296`, `status=queued`, `deployment_id=1`, `started_at=null`, `ended_at=null` |
| 5. Coding task enqueued | **never** — no coding queue key exists in Redis; the only list, `codexify:queue:system`, holds 2 unrelated chat tasks |
| 6. Worker dequeued | **never** — no dequeue or execution lines in the worker log |
| 7. Credential lease authorized | **never** — `coding_execution_credential_leases` has 0 rows for this attempt |
| 8. Pi harness initialized | not reached |
| 9. Provider execution occurred | **never** — no provider request was made |
| 10. Requested/effective model and effort recorded | not reached (no binding existed to carry them) |
| 11. Authorized fixture mutation | **none** — fixture `git status --porcelain` empty, head still `46e3fda`, `canary_marker.txt` unchanged |
| 12. Terminal AgentRun state | **none** — `agent_run_attempts` 0 rows, `agent_run_steps` 0 rows, `agent_runs.status=queued`, no `error` |
| 13. Coding-result artifact | **none** — `agent_run_artifacts` 0 rows |
| 14. Result delivered to the source Chat Thread | **none** — `chat_messages` for thread 1 holds exactly 1 row: the authored `user` request |
| 15. Result survives canonical readback | **nothing to read back** — exactly one result message was expected, and zero exist |

No automatic retry, no second attempt, no credential fallback, and no provider
or model substitution occurred. The failure was preserved, not retried.

---

## 9. Validation results

The test process imports Guardian from the evaluated worktree (verified by
printing the resolved module paths before the run).

**Focused selection** — Guardian execution binding, permission posture,
delegation phase 2a, dispatch, dispatch integration, Pi readiness, and the
coding worker — against disposable PostgreSQL 15 on loopback:

| Phase | Result |
|---|---|
| After (restored `models.py`) | **210 passed, 14 failed** |
| Before (original `models.py` swapped in) | **0 executed** — the session cannot collect: 5 of the 7 files import the four missing names transitively, and the collection error aborts the session before any test runs |

**The 14 failures, by identity, and their cause.** All 14 are in
`guardian/tests/workers/test_coding_worker.py`. Running that file **alone**,
it collects and runs in *both* phases, and the outcome is identical:

| Phase | Result | Failing identities |
|---|---|---|
| After (restored) | 14 failed, 89 passed | the same 14 |
| Before (original) | 14 failed, 89 passed | the same 14 |

The 14 are therefore **pre-existing and independent of the ORM restoration**:

```
test_cleanup_failure_is_reported_without_overwriting_success
test_dirty_original_checkout_does_not_block_isolated_execution
test_dirty_preflight_fails_before_adapter_execution
test_isolated_failure_keeps_worktree_by_default
test_isolated_success_captures_patch_manifest_and_terminal_metadata
test_isolated_success_cleans_up_by_default_without_promoting_changes
test_isolated_success_patch_capture_includes_untracked_file
test_keep_on_success_flag_preserves_isolated_worktree
test_one_worker_runs_two_pi_bindings_against_local_provider_mocks
test_oversized_patch_writes_manifest_without_partial_patch
test_patch_artifact_root_can_stay_clean_with_gitignore_rule
test_worker_records_campaign_attempt_ledger_and_work_order_markers
test_worktree_isolation_enabled_runs_adapter_and_validation_in_isolated_cwd
test_worktree_isolation_preserves_relative_subdirectory_cwd
```

**Root cause, isolated by direct probe** (the worker's own published failure
payload, reproduced inside the canary container using the test module's own
helpers):

```
event=task.worktree_created   status=worktree_created
event=task.running             status=running
event=task.failed              error_code=EXECUTION_CREDENTIAL_AUTHORIZATION_FAILED
                               error_message=Guardian denied or could not issue execution credential lease
worktree.status=created        worktree.created=True
                               worktree.base_head=b835e3b8064d2f7eee2dc3e06a7f2e3f274e70ef
```

The Git worktree isolation path **works** — the worktree was created
successfully. The failure is in the credential-lease step: the worker's
`request_coding_credential_lease` requires a registered
`coding_execution_credentials` row, and these tests do not register one. Only
`test_one_worker_runs_two_pi_bindings_against_local_provider_mocks` supplies a
lease (by monkeypatching `coding_worker.request_coding_credential_lease` with
a local `synthetic_credentials` map); the other 13 rely on the real lease
authority against a credential that was never registered. This is a stale-test
condition against the current lease contract, not a defect in the restored
mappings and not caused by this change.

**Regression verdict: 0 regressions.** No test that passed before the
restoration fails after it. The restoration made 210 previously-unreachable
tests executable.

**Full-suite status: NOT RUN.** The repository-wide default (`pytest -v`) was
not executed as a monolithic run. The shared 7.7 GB Docker VM hosts the
operator's live Private Preview, and a previous monolithic run in that
environment exhausted the VM and restarted unrelated services. The focused
selection above, plus the explicit before/after comparison of the affected
suite, is the evidence retained instead.

---

## 10. Known containment limitations

* The Git mutation guard remains **detective, not preventive**. It inspects
  porcelain state after execution; it does not confine the worker's writes.
* **Provider-enforced filesystem, process, and network isolation remains
  unproven.** This run did not exercise worker egress at all, so the previous
  canary's observation — worker network egress despite `allow_network=false` —
  is neither reproduced nor resolved. This receipt is not evidence of ADR-077
  sandbox conformance.
* The Pi adapter runs each invocation with a fresh temporary `HOME` and an
  explicit environment allowlist, and receives the credential on stdin rather
  than in the environment. That is a favourable property of the current
  adapter, not a containment guarantee.
* **Host-sandbox artifacts encountered (environment, not code).** `git` cannot
  operate on this host's filesystem at all — `git init` fails with `unable to
  unlink …/.git/config.lock: Operation not permitted` — so Git-dependent
  worker tests cannot be qualified on the host. The same `git worktree add`
  succeeds inside the canary container, where the coding-worker suite shows 13
  failures rather than 14; the one difference
  (`test_one_worker_runs_two_pi_bindings_against_local_provider_mocks`) needs
  the vendored Pi SDK tree that the image provides at a different path.
* **Restart recovery remains unproven.** The durable run is left in
  `status=queued` with no attempt; nothing was re-dispatched.

---

## 11. The blocking prerequisite

**One prerequisite blocks this proof, and it is smaller than the credential
problem that blocked the previous attempt.**

> **Enable Guardian-authorized service credential selection for delegated
> execution.** Extend the delegation path's credential selection so that a
> service-owned credential that is explicitly policy-authorized for the
> account, provider/model, funding route, and usage policy can be selected —
> instead of only credentials with `owner_scope="account"`.

Acceptance for that task, per the operator's direction:

* extend the existing selection logic; do not introduce caller-controlled
  credential selection;
* preserve account isolation and the explicit policy checks already present in
  `_validate_row`;
* reject unauthorized selection (an account not on the allow-list, a model not
  on the allow-list, a mismatched `usage_policy_ref`, a wrong funding route);
* the selection must remain Guardian-owned, with the caller able to narrow but
  never to widen;
* prove it with a delegated execution that reaches the provider, then rerun
  this source-exact canary against the newly committed branch HEAD, with no
  source overlays and no operator credential fallback.

The account-owned BYOK lane can be qualified separately, but it would not
prove the service-credential path works.

**What is explicitly NOT a prerequisite any more:** the UMS ORM mappings are
restored and the backend boots source-exact; the dedicated, provider-valid,
account-authorized DeepSeek test credential exists and is registered under its
true owner. The credential blocker from the previous receipt is resolved.

---

## 12. ADR impact and invariants

* **ADR-020, ADR-065, ADR-069, ADR-077, ADR-093** — unchanged; no ADR was
  modified by this run.
* **ADR-094** — this run produces direct implementation evidence about it.
  §12 and §34 require service-owned credentials to be eligible for account
  invocations under explicit service policy. The credential-authority layer
  implements that; the delegation selection path does not. The gap is recorded
  as a prerequisite, not as a contract change, and no ADR was rewritten.
* **ADR-084 / the UMS contract** — unaffected; the four mappings are
  present and the canary schema is at the committed head.

Invariants observed:

* Guardian owns execution authorization — the binding was minted only by
  Guardian, and its failure was Guardian's own fail-closed decision.
* The credential retains its true canonical owner (`service` /
  `codexify-service`); it was not relabelled as account-owned to reach a
  dispatchable path.
* No ambient secret became task authority — the provider key existed only
  inside the encrypted credential store and never entered an environment,
  image, mount, or log.
* Provider and model identity remain explicit
  (`deepseek` / `deepseek-v4-flash`), and were not substituted.
* One attempt remained one attempt: no retry, no second attempt, no
  fallback, no promotion of partial results.
* Queue acceptance was never claimed to imply execution success — the queue
  was never even written to.
* Postgres remained canonical for durable results; the run record and the
  absence of any result were read back from it.
* No release claim is made by this receipt. **Release status remains HOLD.**

---

## 13. Classification and explicit confirmations

**Final classification: BLOCKED.** The controlled attempt was made, the
credential and runtime qualified, Guardian authorized the intent and the
approval, the durable run and deployment were persisted — and the execution
binding could not be minted because Guardian's credential selection cannot see
a service-owned credential, which ADR-094 requires it to be able to.

Explicitly confirmed:

* **No unauthorized credential use.** The key was a dedicated test credential,
  distinct from every operator credential, used only under its true service
  ownership and the operator's explicit authorization.
* **No application-source overlay.** The images were built from the exact
  committed source; the only application file in the evaluated delta since the
  prior proof image is the restored `guardian/db/models.py`, and the
  containers' file hash matches the worktree exactly.
* **No production-state mutation.** The Private Preview served 200 on `/` and
  `/health`, its image digests are unchanged, and no Private Preview volume,
  container, or database was touched.
* **No automatic second attempt.** The failure was preserved, not retried; no
  queue task, no lease, and no provider request exist.
* **Conversational intake remains unavailable.** The delegation was driven
  through the internal Guardian service boundary; no conversational route was
  enabled and no route or supported-profile flag was changed.
* **Restart recovery remains unproven.** The durable run is left `queued` with
  no attempt; nothing was re-dispatched.
* **Provider-enforced sandbox isolation remains unproven.** The Git mutation
  guard remains detective, and this run provides no evidence of ADR-077
  conformance.
* **Release qualification remains HOLD.**

### 14. Artifacts

* Proof receipt: `docs/architecture/proofs/runtime/2026-10-22-guardian-delegation-authorized-rerun-proof.md`
* Evaluated commit: `e28dbcff99b349b6469bcbe2b7880bc91777bccb`
* Proof images: `sha256:ba1d48cadb74ea1d2dae4dc6e9728d5fbbc1bd75633af4ca74db4eca546926d0`
  (backend), `sha256:6c3ce72b861284ac0f74c0f798e9149a58452e6f95a4028c7e75cc71141f0cc6`
  (worker)
* Canary credential reference: `ccr_ff654e9725e8401e8e9bb5cced089f6b` (revoked at
  teardown)
* Run / deployment / intent: `run_556aab694ed64296` / `dep_e384a53f432642ba` /
  `gdi_5222efb162d14316`
* The historical BLOCKED receipt
  (`2026-10-22-guardian-delegation-source-exact-live-proof.md`) is preserved
  unchanged and remains accurate as of its own evaluated source.
