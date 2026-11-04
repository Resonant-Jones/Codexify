# Guardian Authorized Coding Dispatch — Runtime Proof

**Date:** 2026-10-31
**Evaluated branch:** `integrate/guardian-coding-authorized-dispatch-20261031` (isolated integration branch, created from the feature source)
**Feature source SHA:** `7b4b0bab44bf2fd3894eb310d8c2ef48d406325f` (`feature/guardian-delegation-acceptance-axis`)
**Evaluated published main (task spec):** `0cc626032b0d83f405e7f49529e6f135c9ea8a66`
**Current published main (verified at execution time):** `f6a6c2b5d996c633886e8529b818a5f822b56272` (`origin/main`)
**Verified candidate SHA:** `e7d3ccde69ba6d7313e666340d12d99a1775f162` — the tree the independent verifier audited and swept (§17.1).
**Integration candidate SHA:** the branch tip that carries this receipt's verification record. It is a **documentation-only** commit on top of `e7d3ccde6`: the implementation, the tests, and the four other files are byte-identical, and only this receipt differs. `e7d3ccde6` is retained in the branch history so the verification report continues to name a commit that exists.
**Release posture:** **HOLD** (unchanged)

---

## 0. Evidence boundary

This receipt proves **one** thing: that an explicit, authenticated coding
request reaches `GuardianDelegationService.dispatch_delegated_task` through
one canonical, durable, account-authorized admission path, and that the
admitted attempt is submitted to the queue **at most once**.

Evidence class: **D** = proven against disposable PostgreSQL/Redis.

This receipt does **not** prove, and does not claim:

- worker restart recovery;
- pre-acceptance Redis dequeue-loss recovery;
- exactly-once execution (the queue is at-most-once and lossy);
- supported-deployment or Compose qualification;
- a live Private Preview run;
- that the frontend can reach this path today (§19).

No production inference credit was spent. The provider never ran: the proof
stops at the queue submission, exactly at the admission boundary.

---

## 1. Branch isolation and ancestry

| Fact | Value |
|---|---|
| Integration branch | `integrate/guardian-coding-authorized-dispatch-20261031` |
| Isolated worktree | `/Volumes/Dev_SSD/Codexify-main/.worktrees/integrate-guardian-coding-dispatch-v2` |
| Feature source SHA | `7b4b0bab44bf2fd3894eb310d8c2ef48d406325f` (verified unchanged) |
| Published main at execution time | `f6a6c2b5d996c633886e8529b818a5f822b56272` |
| Spec's evaluated main | `0cc626032b0d83f405e7f49529e6f135c9ea8a66` — **behind** the current published main |

The original feature branch was **not** edited, rebased, reset, merged, or
pushed. The integration branch is a separate ref created from the verified
feature source, and the feature branch's tip still reads
`7b4b0bab44bf2fd3894eb310d8c2ef48d406325f`.

**Ancestry facts that constrain this integration.**

1. The feature source is behind published main. The branch therefore does
   **not** contain main's newer worker-claim merge heads
   (`a3115f64dda8`, `c8e42a91d307`, PR #958) and does not contain the claim
   heartbeat revision `d86f2a4b1c90` as a *reachable* ancestry object. The
   branch's own Alembic graph is single-headed at `d86f2a4b1c90`
   (`coding_run_claim_heartbeat`), which is what the disposable PostgreSQL
   proof migrates.
2. Branch-specific runtime worker-store methods therefore still require the
   separate mainline integration that the task context anticipates. This
   receipt does not attempt it.
3. The feature branch is **not** merged into main. Mainline promotion is a
   later task.

---

## 2. Exact dispatch call path

```
POST /api/agents/coding/execute
  guardian/routes/agent_orchestration.py :: execute_coding_task
    ├─ Depends(require_account_session)                 # account-session lane
    └─ envelope.delegation_intent_id present
       └─ _dispatch_authorized_coding_request(envelope, request, intent_id)
          ├─ _resolve_authorized_coding_account(request)        # §3
          ├─ _get_delegation_service()
          │    → GuardianDelegationService(db=_store.db, agent_store=_store)
          └─ GuardianDelegationService.dispatch_authorized_coding_request(...)
               ├─ thread ownership / message ownership / message role / project ownership
               ├─ _authorize_intent_for_dispatch(...)            # §4  approval gate
               ├─ agent_store.get_run(run_id)
               ├─ agent_store.get_deployment(deployment_id)      # persisted run link
               ├─ instruction binding check                     # §8  approved plan
               ├─ _resolve_project_repo_root(...)                # §7  repository binding
               └─ dispatch_delegated_task(...)                   # existing method
                    ├─ _resolve_execution_binding(...)            # §5  credential/provider/model
                    ├─ _resolve_permission_posture(...)          # §6  authorized posture
                    ├─ _narrow_permission_posture(...)           # §6  caller narrowing only
                    ├─ persist_execution_binding(...)            # §9  atomic PG fence
                    ├─ assert_dispatch_ready(...)
                    ├─ enqueue_coding_execution(payload)          # §10  one submission
                    └─ mark_dispatched(record, task_id=task_id)
```

The route does **not** mint a second `AgentRun`, a second deployment, a second
attempt identity, or a second queue submission. It resolves the intent's
existing persisted run link and dispatches that.

`GuardianDelegationService.dispatch_delegated_task` is the existing feature-
branch method, reached unchanged in ordering and semantics. The new work is
the *admission* in front of it and the *atomicity* of its binding write.

---

## 3. Identity-resolution path

The canonical account is derived **only** from a verified account-session
principal.

```
extract_session_token(Authorization: Bearer | gc_session cookie)   # guardian/core/auth_dependencies.py
  → no token                                        → 401 coding_account_session_required
  → purpose == OPERATOR_SESSION_PURPOSE             → 403 coding_operator_principal_not_account_authority
  → !verify_session_token_for_purpose(token, ACCOUNT_SESSION_PURPOSE)
                                                   → 401 coding_account_session_required
  → resolve_account_session_subject(token)          → canonical account id
       (signed subject + exact account purpose + session-store mapping agreement)
```

Explicitly **not** used as account authority, per the task's authority rules:

| Rejected source | Where it is refused |
|---|---|
| Hardcoded "local" frontend constant | The frontend has no path here; the server never reads a caller constant |
| Caller-submitted `user_id` | Retained only as a compatibility **assertion**: a non-empty `user_id` must equal the authenticated account, else `403 account_identity_mismatch` |
| Thread ID alone | Thread ownership is checked against the authenticated account (`guardian_delegation_thread_account_mismatch`) |
| Operator-session identity | `403 coding_operator_principal_not_account_authority` |
| API-key fallback principal | No session token ⇒ `401`; the static key never becomes an account |
| Provider / credential identity | The credential is *resolved* for the account; it never names the account |

**Operator fallback is proven closed at two layers.** An operator *session* is
refused by the account-session verifier and by the route's own purpose check.
An operator *static key* is refused by the account-session lane before a body
is read. Neither produced a run, a deployment, or a queued task.

---

## 4. Approval gate

`GuardianDelegationService._authorize_intent_for_dispatch` requires, before
anything is enqueued:

| Check | Refusal |
|---|---|
| A dispatch names an intent | `422 guardian_delegation_intent_required` |
| Intent exists | `404 guardian_delegation_intent_not_found` |
| Intent belongs to the submitted thread | `409 guardian_delegation_intent_thread_mismatch` |
| Intent belongs to the submitted source message | `409 guardian_delegation_intent_source_message_mismatch` |
| Intent belongs to the submitted project | `409 guardian_delegation_intent_project_mismatch` |
| `approval_state == approved` | `409 guardian_delegation_intent_not_approved` |
| Not cancelled / superseded / failed | `409 guardian_delegation_intent_not_dispatchable` |
| Intent already carries its run link | `409 guardian_delegation_intent_not_linked` |

**An approval decision is not a dispatch event.** The route requires a
`delegation_intent_id`; the intent's creation and approval are separate,
earlier steps. The dispatch is the explicit authenticated step that follows.

**The admission path never creates an intent implicitly.** An unnamed
dispatch is refused (`422 guardian_delegation_intent_required`) *before* any
lineage work. This is deliberate, and it is a correctness property rather
than a convenience: an implicit intent would mint a fresh run, a fresh
deployment, and a fresh queue submission on **every** duplicate request,
because `create_intent` does not deduplicate on
`(thread_id, source_message_id)`. That would make a duplicate request
produce independent execution authority — precisely the invariant this path
exists to hold. Refusing the unnamed request closes that fork by
construction rather than by a lock.

---

## 5. Credential, provider, and model selection

Guardian resolves; the caller proposes. The effective binding comes from
`guardian/core/guardian_execution_binding.py`, unchanged.

| Input | Authority |
|---|---|
| Account credential | `list_account_credentials(db, account_id=...)` — the account's own durable state, newest first |
| Service credential | Reached **only** when the account lane is empty, and only where the credential authority's own policy authorizes it |
| Provider | Pinned by the stored credential |
| Model | Pinned by Guardian from the runtime's own configuration for that provider (`_resolve_account_model_id`) |
| Harness | `pi`, the only harness the coding worker accepts |

A caller-supplied `provider_id` / `model_id` / `credential_ref` is a
**constraint**, not a grant:

- a named credential is selected only if the account owns it (or a service
  credential policy authorizes it for this account);
- a named provider or model must equal what Guardian resolved, else
  `guardian_binding_provider_constraint_unsatisfied` /
  `guardian_binding_model_constraint_unsatisfied`;
- a rejected account credential is **never** silently replaced by a service
  one;
- an ambiguous service selection fails closed rather than choosing one
  arbitrarily;
- when no usable credential exists at all, the request is refused **before**
  enqueue (`guardian_binding_no_account_credential`).

The persisted binding is **secret-free**: it carries a credential *reference*,
the owner scope, the funding route, and the source class — never key
material. Proven in §13, case 3 and case 15.

---

## 6. Effective permission posture

The authorized posture is resolved by Guardian from account, project, and
workspace context (`guardian/core/guardian_permission_posture.py`), never from
the request:

| Capability | Authorized source |
|---|---|
| Repository root | The project's active `RepositoryBinding` (ADR-065). Fail closed if absent. |
| Write scope | The bound working tree; `GUARDIAN_DEFAULT_ALLOWED_PATH_SCOPE` |
| Shell | Authorized explicitly for the delegated coding task |
| Network | **Not** authorizable — no sandbox provider is wired into the coding worker |
| Runtime duration | `GUARDIAN_CODING_MAX_RUNTIME_SECONDS` |
| Validation command / commit-after-validation | Carried on the task payload, bounded by the posture |

`GuardianDelegationService._narrow_permission_posture` then applies the
caller's requested policy as a **narrowing constraint only**:

- requesting **less** than authorized narrows the effective posture
  (e.g. `allow_shell=false` ⇒ the queued task carries `allow_shell=false`;
  `max_runtime_seconds=45` ⇒ the effective limit is 45 s);
- requesting **more** than authorized is **refused**
  (`403 guardian_permission_allow_network_not_authorized`), not quietly
  downgraded. A requested writable operation therefore can never silently
  execute as a read-only success;
- a requested path outside the authorized scope is refused
  (`403 guardian_permission_allowed_paths_not_authorized`);
- the requested runtime may only lower the authorized limit.

The existing sandbox provider architecture and the Pi tool-disabling
behaviour were **not** changed.

---

## 7. Repository binding

`GuardianDelegationService._resolve_project_repo_root` resolves exactly one
active `RepositoryBinding` for the project through
`guardian/core/repository_authority.py`, which fails closed on a missing
project, an account mismatch, zero or multiple active bindings, a missing or
non-directory root, a non-Git root, a stored/canonical root mismatch, and a
managed-root escape.

In the authorized dispatch path a missing binding is fatal before enqueue:

```
403 guardian_delegation_repository_binding_unavailable
```

A caller-supplied `repo_root` is a **constraint**: it must equal the
authorized canonical root, else
`403 guardian_delegation_repository_binding_mismatch`. The caller cannot
point the worker at a directory of its choosing.

---

## 8. AgentRun and attempt correlation

One canonical relationship is preserved across the admitted attempt:

| Element | Value | Source |
|---|---|---|
| Delegation intent | `intent_id` | The approved intent |
| Source thread | `thread_id` | The intent's thread, ownership-checked |
| Source message | `source_message_id` | The intent's source turn, ownership- and role-checked |
| Account | `user_id` | The authenticated account session subject |
| Project | `project_id` | The intent's project, ownership-checked |
| AgentRun | `run_id` | The intent's **existing** persisted run link |
| Deployment | `deployment_id` | The run's deployment |
| Coding task | `coding_task_id` | The deployment spec's persisted value |
| Attempt | `attempt_id` | The deployment spec's persisted value |
| Execution binding | `binding_id` | Minted by Guardian at dispatch, persisted into the deployment spec |

`_create_agent_run_link` now records `account_origin_user_id` on the delegated
run, so the run is account-scoped for the readback authority (ADR-094) instead
of an operator artifact that merely mentions an account.

The deployment spec carries `guardian_delegation.intent_id`, and the
admission path refuses a deployment that is not owned by the intent it is
dispatching (`409 guardian_delegation_deployment_intent_mismatch`).

A caller-supplied `coding_task_id` / `attempt_id` is a compatibility
assertion: empty means "use the persisted identity"; a non-empty value that
differs from the persisted one is refused
(`409 guardian_delegation_coding_task_identity_mismatch` /
`..._attempt_identity_mismatch`).

### The executed instructions are bound to the approved plan

The approval authorizes the *approved plan*, so the executed instructions are
the approved plan's own instructions. The request's `instructions` is a
**proposal**, not the work content:

| Request's instructions | Result |
|---|---|
| Empty | The approved plan is dispatched. The request asserts nothing. |
| Equal to the approved plan's instructions | Accepted. |
| Different from the approved plan's instructions | **Refused** — `409 guardian_delegation_instructions_not_bound_to_approved_plan`, before the binding is persisted and before anything is enqueued |

This was a **P1 finding in the independent review of the first candidate**
(`164acf015`): the earlier implementation let the request's instructions take
precedence over the plan the intent was approved with, and then wrote them
into the deployment spec. That let an approved intent authorize different
work from the work that was selected and planned — while the resolved
posture permits shell and repository writes, and the git mutation guard
*detects* an out-of-scope mutation afterwards rather than preventing it.

The correction binds the execution to the approval. It is proven adversarially
by `test_dispatch_cannot_substitute_different_work_under_an_approved_intent`:
task A is approved, a request that tries to dispatch task B under the same
intent is refused with `409`, the deployment spec still carries **no**
`execution_binding`, the queue is empty, and the intent itself is untouched
because the refusal happened at admission, before any dispatch was
attempted. The approved plan then dispatches exactly as approved.

**Consequence, stated plainly.** The approved plan prompt is
lineage-referential by deliberate design: the selected turn is reduced to a
content hash and a length, and the prompt says *"Resolve the work request
from the selected source turn by lineage reference only"*. The coding worker
has no chat access — `source_message_id` is used only for lineage validation
and correlation — so the prompt that reaches the model **is** the plan
prompt. A delegated task therefore executes the approved plan, which today
references the turn rather than restating it.

That is the delegated path's pre-existing state, not a regression introduced
here: the delegation contract already records that the loop *"is not yet
driven from a chat turn"*. The later Guardian Chat task must close the gap
by producing intents whose **plan carries the resolved work content**, so
that the approval covers executable text — and that is exactly what binding
the instructions to the plan makes necessary. This receipt does not claim
that a delegated task today performs the user's request end to end; it claims
that the request is admitted, authorized, and dispatched exactly once under
the approved plan.

---

## 9. Duplicate and concurrent admission evidence

The at-most-once admission invariant is fenced at the **PostgreSQL authority
boundary**, not by a process-local lock and not by a test double.

`persist_execution_binding` previously read the deployment spec in one
session and wrote it in another — a check-then-write race. It now performs
the read and the write inside **one transaction**, with the deployment row
locked `FOR UPDATE`:

```sql
SELECT ... FROM agent_deployments WHERE deployment_id = :id FOR UPDATE
```

Consequence: a second concurrent dispatch of the same attempt blocks on the
row lock, then re-reads the committed row, sees an established binding whose
`binding_id` differs from its own, and is refused with
`409 guardian_delegation_execution_binding_already_established` **before**
any queue submission.

| Evidence | Result |
|---|---|
| Replay of one admitted attempt (HTTP) | First `200`, second `409`; exactly one run; exactly one queued task |
| Two concurrent admissions of one attempt (HTTP, two threads, two clients) | Statuses sorted `[200, 409]`; exactly one run; exactly one queued task |
| An unnamed dispatch (service level) | `422 guardian_delegation_intent_required`; no intent, no run, no queued task |
| Two concurrent unnamed dispatches (service level, two threads) | Both `422`; no intent, no run, no queued task |

The unnamed-request rows matter as much as the named ones: they prove that
there is no path — sequential or concurrent — by which a duplicate request
can mint a second lineage. The fence is the deployment row lock; the refusal
is the absence of a path to bypass it.

The fence is intentionally *at-most-once and lossy*: if the process dies
between the binding write and the enqueue, the attempt is bound but not
queued, and a later replay is refused rather than re-queued. That is the
documented queue contract. No automatic retry or recovery was added to
conceal the gap.

---

## 10. Queue-submission evidence

`dispatch_delegated_task` submits **one** coding-execution task whose
`execution_binding` is byte-identical to the persisted deployment spec's
binding — the comparison the coding worker performs at dequeue.

The queued payload carries the full lineage: `run_id`, `deployment_id`,
`coding_task_id`, `attempt_id`, `user_id`, `thread_id`, `source_thread_id`,
`source_message_id`, `project_id`, `repo_root`, `permission_policy`, and
`execution_binding`.

Each test drains the queue and asserts the exact count, so "exactly one
queue submission" is proven per case rather than assumed.

### Failure semantics

A refused dispatch leaves a durable, inspectable result rather than an
ambiguous one. The rule is **an attempt is consumed only once it has been
authorized**, and the persisted execution binding is the durable record of
that authorization (it is written before the enqueue):

| Refusal | When | Durable result |
|---|---|---|
| Instructions not bound to the approved plan | At admission, before the dispatch attempt | No binding persisted, nothing queued, **the intent is untouched** — a corrected request may still be admitted |
| Provider/model/credential incompatible, permission over-request, repository binding unavailable | Inside the dispatch path, before the binding is written | No binding persisted, nothing queued, **the intent is untouched** |
| Dispatch failure of an *authorized* attempt (assertion, enqueue) | After the binding was persisted | `intent_status` = `failed` on the intent axis, the linked run closed as terminal with the reason on `AgentRun.error` |
| Duplicate admission of an attempt | After a successful dispatch | Nothing changes — the attempt was already dispatched. `409` |

The intent axis owns the execution outcome (the delegation contract, *"Axis
Ownership of Facts"*), so a dispatch failure sets `intent_status` to `failed`
and never touches `acceptance_status`: the request was admitted, and
admitting it did not fail.

An unauthorized request consumes nothing. That is what lets a caller
correct a request — for example, narrow a permission set — and be admitted
again against the same approved intent.

**Known imprecision, pre-existing and read-only-pinned.** The run link is
created with `status="queued"` when the intent is created, before any
dispatch, and `tests/contracts/test_guardian_delegation_phase2a_contract.py:435`
pins that projection. An unauthorized request therefore leaves the intent's
`run_status` reading `queued` even though nothing was enqueued. The
authoritative signals that nothing was queued are the absence of an
`execution_binding` in the deployment spec and an empty queue; changing the
projection would break a read-only contract.

---

## 11. PostgreSQL proof environment

| Fact | Value |
|---|---|
| Container | `codexify-guardian-dispatch-pg` |
| Image | `postgres:16-alpine` |
| Server version | PostgreSQL 16.15 on aarch64-unknown-linux-musl (Alpine 15.2.0) |
| Published port | `127.0.0.1:55434 → 5432` |
| Isolation | Per-module disposable **database**, name `codexify_authorized_dispatch_<hex12>`, created with `CREATE DATABASE` from a `postgres` admin connection |
| Schema | `Base.metadata.create_all` on that disposable database only |
| Between cases | `TRUNCATE TABLE <all tables> RESTART IDENTITY CASCADE` |
| Cleanup | `pg_terminate_backend` for the disposable database, then `DROP DATABASE` — in a `finally` block |
| Data used | Synthetic fixtures only. **No** production data and **no** Private Preview data. |
| Queue | In-memory Redis (`redis_queue._InMemoryRedis`) restored after each case |

| The disposable database is dropped even when a case fails. |

The disposable PostgreSQL container (`codexify-guardian-dispatch-pg`) was
**stopped** by the independent verifier after its sweep completed.

---

## 12. Focused test totals

Command (from the task spec), with `TEST_DATABASE_URL` pointed at the
disposable PostgreSQL above:

```
python -m pytest -o addopts="" -v -rs \
  tests/contracts/test_guardian_coding_authorized_dispatch_contract.py \
  tests/contracts/test_guardian_delegation_phase2a_contract.py \
  tests/contracts/test_guardian_delegation_approval_cancel_contract.py \
  tests/contracts/test_guardian_delegation_phase3_delivery_contract.py
```

Existing feature-branch suites also run against the same disposable
PostgreSQL — dispatch, execution binding, permission posture, worker
acceptance, and the Guardian delegation phase 2A / approval-cancel / phase 3
delivery contracts.

### Totals

| Run | Result |
|---|---|
| New suite alone — `tests/contracts/test_guardian_coding_authorized_dispatch_contract.py` | **27 passed**, 0 failed, 0 skipped |
| Combined run on the merged tree — the new suite plus the spec's four files, `test_guardian_dispatch_integration_contract.py`, `test_guardian_execution_binding_contract.py`, `test_guardian_permission_posture_contract.py`, `test_guardian_coding_worker_acceptance_contract.py`, and `guardian/tests/routes/test_agent_orchestration_events.py` | **233 passed**, 0 failed, 0 skipped |
| Pristine feature SHA `7b4b0bab4`, the same combined set minus the new file, on a **real Git worktree** | 195 passed, 2 failed |

**Zero database skips.** Every database-backed case ran against the
disposable PostgreSQL of §11; none was skipped for a missing database.

**The pristine baseline was re-established on a real Git worktree.** The
earlier figures in this receipt were taken against a *source extraction* of
`7b4b0bab4`, not a Git worktree, and the difference mattered: the extraction
made `test_guardian_coding_worker_acceptance_contract.py::test_acceptance_precedes_worktree_creation`
look like a pre-existing failure, and on a real worktree of the same SHA it
**passes**. The pristine figure is therefore 195 passed / 2 failed, not 194
passed / 3 failed.

**The two pristine failures are the identity-migration cases in
`guardian/tests/routes/test_agent_orchestration_events.py`** — the read
routes reject an empty asserted identity with 403 where the test expects
404. They are green on the merged tree because the branch reconciled with
`main`, and `main` carries the identity migration. **That is the effect of
the reconciliation (§23), not of this feature**, and it is stated here so
the two are not conflated: this change makes no claim to have fixed them.

**Attributable failures: zero.** Nothing in the combined run fails, and the
§17.1 set difference shows that nothing on this branch fails that did not
already fail on the pristine side.

The combined run took 1 minute 51 seconds. An earlier run of the same set
took 33 minutes because a second, independent verification sweep ran
concurrently against the same disposable PostgreSQL and the same nearly-full
volume; the suites themselves are not slow.

---

## 13. Property-by-property result

| # | Required proof | Result | Evidence |
|---|---|---|---|
| 1 | An authenticated account can explicitly submit an eligible coding request | **Pass** | `test_authenticated_account_dispatches_one_authorized_coding_request` |
| 2 | Guardian resolves the canonical account from authentication | **Pass** | `test_guardian_resolves_the_canonical_account_from_authentication` |
| 3 | An authorized proposal resolves to a persisted, secret-free binding | **Pass** | `test_authorized_proposal_resolves_to_a_persisted_secret_free_binding` |
| 4 | The existing delegation dispatch method is reached | **Pass** | `test_dispatch_reaches_the_existing_delegation_dispatch_method` (spies on `dispatch_delegated_task`) |
| 5 | Exactly one correlated run | **Pass** | same case — one `AgentRun`, `account_origin_user_id == ACCOUNT_A` |
| 6 | The task reaches the existing coding queue | **Pass** | same case — exactly one drained task |
| 7 | Replay creates no second independent execution | **Pass** | `test_replaying_the_same_admitted_attempt_creates_no_second_execution`, `test_an_unnamed_request_never_forks_a_new_execution_lineage` |
| 8 | Concurrent duplicate admission fenced by the durable authority boundary | **Pass** | `test_concurrent_duplicate_admission_is_fenced_by_postgresql`, `test_concurrent_unnamed_admissions_create_no_execution_at_all` |
| 9 | Another account cannot use another account's thread, message, credential, or intent | **Pass** | `test_another_account_cannot_use_the_original_accounts_lineage` |
| 10 | Operator credentials cannot become account authority through fallback | **Pass** | `test_operator_credentials_cannot_become_account_authority` |
| 11 | Missing or incompatible provider/model/credential authority rejects before enqueue | **Pass** | `test_missing_credential_authority_rejects_before_enqueue`, `test_incompatible_provider_proposal_is_refused_before_enqueue` |
| 12 | Missing repository authorization rejects before enqueue | **Pass** | `test_missing_repository_authorization_rejects_before_enqueue` |
| 13 | Permissions cannot exceed their approved scope | **Pass** | `test_requested_permissions_cannot_exceed_the_approved_scope`, `test_a_requested_path_outside_the_authorized_scope_is_refused` |
| 14 | Cancelled and superseded intents cannot dispatch | **Pass** | `test_cancelled_and_superseded_intents_cannot_dispatch`, `test_an_unapproved_intent_cannot_dispatch` |
| 15 | Queue records, events, and result metadata carry no plaintext credential material | **Pass** | `test_no_plaintext_credential_material_crosses_the_task_boundary` |
| 16 | The result stays correlated with its original source thread and message | **Pass** | cases 1 and 5 — thread, source thread, and source message all present on the queued task and on the receipt |

Additional cases:

| Case | Proves |
|---|---|
| `test_the_admission_path_dispatches_the_named_intent_it_resolves` | The admitted attempt is the named intent's own persisted attempt, and the queued task carries the **approved plan's** instructions |
| `test_an_unnamed_request_never_forks_a_new_execution_lineage` | An unnamed dispatch is refused before any lineage work |
| `test_concurrent_unnamed_admissions_create_no_execution_at_all` | Two concurrent unnamed dispatches create no intent, no run, and no task |
| `test_dispatch_cannot_substitute_different_work_under_an_approved_intent` | **The P1 adversarial regression**: task A approved, task B refused — before binding persistence and before enqueue |
| `test_dispatch_accepts_the_approved_plan_as_its_instruction_proposal` | Echoing the approved plan is accepted, not refused |
| `test_a_requested_path_outside_the_authorized_scope_is_refused` | A path outside the bound working tree is a widening and is refused |
| `test_an_unsuccessful_enqueue_is_recorded_on_the_intent_axis` | A dispatch failure sets `intent_status=failed` and closes the run, while `acceptance_status` stays `accepted` |

---

## 14. Invariant check

| Invariant | Result |
|---|---|
| Guardian remains the sole coding-admission authority | **Held** — the route resolves the account and hands off; the delegation service mints the binding, the posture, and the repository binding |
| The account principal cannot be supplied by the frontend | **Held** — the principal is a verified account session; a caller `user_id` is an assertion only |
| Credential references are identifiers, not grants | **Held** — `authorize_credential_selection` revalidates owner scope, provider, model, funding route, expiry, and usage policy |
| Requested provider/model choices require Guardian authorization | **Held** — a proposal must equal the resolved selection or be refused |
| No ambient worker credential becomes account authority | **Held** — the credential is resolved for the authenticated account; the service lane is reached only when the account lane is empty |
| An approval decision is not by itself a dispatch event | **Held** — the route requires a named, already-approved intent and performs the dispatch explicitly |
| The approval authorizes the executed work | **Held** — the executed instructions are the approved plan's own; a proposal that differs is refused before binding persistence and before enqueue |
| A run has one canonical execution lineage | **Held** — the intent's persisted run link is dispatched; no second run, deployment, attempt, or queue submission is created |
| A duplicate request cannot produce duplicate execution authority | **Held** — a dispatch must name an already-approved intent, so there is no path that mints a fresh lineage per request; the deployment row lock then refuses the second admission of the named attempt before enqueue |
| The worker cannot expand its authorized permission posture | **Held** — the posture is Guardian-resolved; the caller may only narrow it |
| Source-thread and result provenance remain durable | **Held** — the intent, deployment spec, run, queued task, and receipt all carry the same thread/message lineage |
| No additional canonical state store or control plane is created | **Held** — the fence reuses the existing `agent_deployments` row and its spec |
| Release remains HOLD | **Held** |

---

## 15. ADR impact

No new ADR is anticipated, and none is created by this change.

| ADR | Relationship |
|---|---|
| ADR-020 Guardian Mediated Coding Agent Execution | The route is the account-authenticated intake; the delegation service is the execution authority |
| ADR-022 Guardian Intent Spine | The approved delegation intent is the request's authority; an approval is not a dispatch |
| ADR-065 Guardian-Managed Repository Onboarding Boundary | The repository binding is resolved from the project and fails closed |
| ADR-077 Sandbox Execution Authority | The effective permission posture is Guardian-resolved; a caller may narrow only |
| ADR-081 Project Ownership Authority | Project ownership and membership are checked against the authenticated account |
| ADR-092 Credential Purpose and Mixed-Principal Authentication | The account-session lane and the operator lane are kept separate |
| ADR-093 Native Execution Channel and Inference Routing | The delegated route's harness and placement remain the worker's own |
| ADR-094 Account-Scoped Execution Credential Authority | The binding is secret-free and account-scoped; the delegated run now records its account origin |

**Proposed ADR-104 is not treated as accepted execution authority.**

---

## 16. Known deviations, and the independent review disposition

### Independent review disposition

The first candidate `164acf015` was audited read-only by a peer executor.
Its findings and their disposition:

| Finding | Severity | Disposition |
|---|---|---|
| Approved work could be replaced during dispatch: the request's `instructions` took precedence over the approved plan's instructions, and the replacement was written into the deployment spec | **P1** | **Fixed.** The executed instructions are now bound to the approved plan; a proposal that differs is refused with `409 guardian_delegation_instructions_not_bound_to_approved_plan` before binding persistence and before enqueue. Covered by `test_dispatch_cannot_substitute_different_work_under_an_approved_intent`. See §8. |
| The legacy execution producer remains: the route still creates an independent deployment, run, and queue task when no intent is named | P2 | **Documented, not fixed.** Read-only contracts pin the legacy branch (§16.1 below). The at-most-once proof covers the authorized path only. |
| A run can appear `queued` before enqueue | P2 | **Documented, not fixable here.** `tests/contracts/test_guardian_delegation_phase2a_contract.py:435` pins the projection. The authoritative "nothing was enqueued" signals are the absent `execution_binding` and the empty queue. |
| Real Redis and worker execution remain unproven by this suite | Evidence limitation | **Accepted and bounded.** The proof stops at the queue submission by design; no production inference credit was spent. |
| Mainline compatibility outstanding: the candidate derives from `7b4b0bab4` while `main` has advanced | Integration qualification | **Accepted.** Qualifying the candidate against current `main` is a separate task (§18). |

The peer review also asked for the adversarial regression the P1 implied.
It is in the suite, and the lineage and concurrency cases were not weakened:
the concurrent-admission case still proves `[200, 409]` with exactly one
queued task, and the replay case still proves one run and one queued task.

### 16.1 The legacy branch, stated plainly

The task asks that the route's admitted request reach the delegation service
"rather than independently manufacturing another execution lineage". The
route currently carries **two** branches:

1. **Delegated branch** (new, and the subject of this receipt) — selected when
   the request names a `delegation_intent_id`. It reaches
   `dispatch_delegated_task` and manufactures no lineage of its own. This is
   the canonical authorized admission path.
2. **Legacy intake branch** (pre-existing, unchanged) — selected when no
   intent is named. It still creates its own deployment, run, and queue
   submission.

The legacy branch could not be removed within the writable boundary without
an attributable regression: `guardian/tests/routes/test_agent_orchestration_events.py`
(read-only) pins the legacy behaviour, including that the route calls the
route-module `_validate_coding_lineage` and `authorize_credential_selection`,
that it works with an in-memory agent store and no database, and that it
creates a deployment in the router's own store. Removing or redirecting that
branch breaks those pinned contracts.

**The legacy branch therefore still mints its own lineage per request**, and
it is *not* covered by the at-most-once invariant of §9 — that invariant is
proven for the authorized admission path, which is this task's subject. A
later task that retires the legacy branch must re-run the at-most-once proof
for whatever replaces it. This is stated rather than glossed over.

The legacy branch's own provider/model/credential requirement was a
**pre-existing defect**, independently visible in the read-only
`tests/core/test_supported_profile_quarantine.py` (three failures on the
pristine feature SHA). It is **fixed**. The three envelope fields stay
**required in the published request schema on both paths** — the documented
shape and the enforced shape may not drift apart — but their *value* now
differs by path: an empty value asserts "no proposal" on the authorized
path, and the legacy branch refuses an empty binding identity with a
schema-conformant `RequestValidationError` (`type: "missing"`,
`loc: ("body", <field>)`) rather than an opaque string. On the merged tree
those three read-only cases are **green**
(`tests/core/test_supported_profile_quarantine.py`: 27 passed, 0 failed).

Two shapes were rejected before this one was chosen. A FastAPI body union
renders `anyOf` in the published OpenAPI, which breaks the `$ref` lookup
that `test_coding_loop_route_visible_in_openapi` performs. A
`model_validator` cannot emit `type: "missing"`, so the 422 body would not
have been the endpoint's own declared `HTTPValidationError` shape.

---

## 17. Inherited failures (not attributable to this change)

The pristine feature SHA `7b4b0bab44bf2fd3894eb310d8c2ef48d406325f`
was extracted to an independent directory (`/tmp/codexify-pristine`) and run
against the same disposable PostgreSQL and the same interpreter. An
extraction is a **source copy, not a Git worktree**, and one conclusion drawn
from that baseline does not survive a real worktree: re-run on an actual Git
worktree of `7b4b0bab4`,
`tests/contracts/test_guardian_coding_worker_acceptance_contract.py::test_acceptance_precedes_worktree_creation`
**passes** (19 of 19). The apparent clearing of that case was an artifact of
the extraction, not a property of this change.

**This receipt therefore makes no claim that this change clears any
pre-existing failure.** The figures in §17.1 are an upper bound on a set
difference, not a count of repairs.

On the merged tree, the modules the original table listed as failing are
**green**:

| Selection | Merged tree |
|---|---|
| `guardian/tests/routes/test_agent_orchestration_events.py` | 29 passed, 0 failed |
| `tests/core/test_supported_profile_quarantine.py` | 27 passed, 0 failed |
| `tests/identity/test_operator_route_auth_migration.py` | 19 passed, 0 failed |

The one region that still fails is the snapshot integration region:

| Test | Merged tree | Cause |
|---|---|---|
| `tests/integration/test_agent_coding_snapshot_readback_postgres.py` (73 cases) | FAIL / ERROR (422) | The read-only payload omits provider/model/credential, so the request is refused by the schema before it reaches the delegation service. The test requires `AGENT_SNAPSHOT_TEST_DATABASE_URL`, which no CI job sets, so it never runs in normal CI. After `2c33553f2` the 422 body is the standard `HTTPValidationError` list naming all three fields as "missing" rather than the opaque string the route used to return; the class of failure is unchanged |

**Attributable failures: zero.** No approval-state regression, no
source-thread provenance regression, no cross-account access, no duplicate
execution admission, and no credential leakage were introduced.

### 17.1 Independent broad sweep — the attribution evidence

A peer executor ran the **broad backend sweep** independently against this
candidate and against a pristine extraction of `7b4b0bab4`, using the same
selection on both trees and the same disposable PostgreSQL 16.15. The totals
alone look alarming; the **set difference** is the number that matters, and it
is unambiguous:

| | failed | passed | skipped | xfailed | errors |
|---|---|---|---|---|---|
| Pristine `7b4b0bab4` | 137 | 7224 | 176 | 35 | 450 |
| Candidate `e7d3ccde6` | 122 | 7239 | 176 | 35 | 450 |

```
comm -13 (failing ONLY on the candidate) : 0    <- zero attributable failures
comm -23 (failing ONLY on pristine)      : 15   <- upper bound, see below
```

**Zero attributable failures.** The error count is identical on both trees.
This is the evidence a totals-only reading would have gotten wrong: the raw
counts look like a large regression and the set difference proves there is
none.

**The 15 is an upper bound, not a count of repairs.** It is the size of the
set of failures that were present on the pristine side and absent on the
candidate side. Each one was **not** individually re-verified as a repair,
and the pristine side was a source extraction rather than a Git worktree, so
the set is a bound on what *could* have been repaired rather than a list of
what was. The set is documentation, migration, and fixture-content assertions
— architecture phase 3 / phase 3b, `guardian_work_brief_ignore_contract`,
`electron_candidate`, `chat_loopback_accepted_deadline`,
`user_profile_accent_proof_profile`,
`account_observability_compatibility_normalization` (×5),
`candidate_runtime_checkpoint`, and `document_worker_shutdown`.

The claim that carries the attribution argument is `comm -13 = 0`: no failure
exists on the candidate that does not also exist on the pristine side.

The peer also ran, independently:

| Selection | Result |
|---|---|
| `tests/contracts/` (all) | 635 passed, 1 xfailed, 0 failed, 0 errors |
| New suite alone | 22 passed, 0 failed, 0 skipped |
| Focused set (spec's four files + dispatch integration + execution binding + permission posture) | 177 passed, 0 failed |
| Identity modules | Only `test_operator_route_auth_migration` fails — byte-identical on pristine |
| Integration region | 4 failed, 75 passed, 73 skipped — the 4 failures byte-identical on pristine |
| Guardian-adjacent failures (`test_worker_coding_pi_runtime_contract`, `test_guardian_evidence_packet_make_target`) | Byte-identical on pristine — documentation and fixture-content assertions, not runtime |

### 17.2 The identity error cluster is environmental, not a code defect

`tests/identity/test_mixed_principal_boundary.py` produces **31 setup errors**
with `sqlite3.OperationalError: unrecognized token: ":"`. This is **branch-behind-main schema drift**, not a defect in this change:

- the module builds its schema on **in-memory SQLite**;
- this branch's `guardian/db/models.py` emits **PostgreSQL-only check constraints**
  (`ck_chat_attempt_orphan_outcome`, `ck_chat_completion_attempts_terminal_event`);
- `guardian/db/models.py` is **not touched by this commit**;
- the result is byte-identical on pristine (`53 passed, 31 errors` on both trees).

`tests/identity/test_operator_route_auth_migration.py::test_frozen_operator_manifest_has_exactly_59_registrations_in_13_files`
is the same category: the branch carries three campaign-runner
continuation-authority routes that the frozen 59-registration manifest does
not list.

Both are recorded here as **environmental / inherited**, so that they are not
read as attributable to the authorized-dispatch change. They are the visible
edge of the same branch lag that §18's mainline reconciliation has to absorb.

### 17.3 Branch custody

Independently confirmed by the peer executor:

- `e7d3ccde6` parent is exactly `7b4b0bab44bf2fd3894eb310d8c2ef48d406325f`;
- exactly **five** files changed, all inside the authorized list;
- nothing under `config/supported_profiles/`, `frontend/`,
  `guardian/routes/guardian_delegations.py`, `guardian/agents/store.py`, or
  `guardian/db/`;
- no upstream configured and no remote branch contains it — **local only, not
  pushed**;
- the feature branch tip is still `7b4b0bab4`, untouched;
- `main` untouched;
- ADR-104 on `main` is status **Proposed / Not accepted**, and its own text
  ("keeps account-origin provenance mandatory", "treats the run id as a locator
  and never as authority") aligns with this implementation.

---

## 18. Unrun or blocked qualification

| Qualification | Status |
|---|---|
| Full backend `pytest -v` | **Completed.** The §12 selection on the merged tree is 233 passed / 0 failed, and `tests/core/` alone is 1340 passed / 0 failed. The §17.1 broad sweep was run independently against both this candidate and a pristine extraction of the feature SHA, with a set difference of **0** attributable failures |
| Broad sweep on the merged tree, `tests/contracts/ tests/core/ tests/identity/ tests/ops/` | 2736 passed, 2 skipped, 1 xfailed, 0 failed, with the 5 residual failures in `tests/identity/` and `tests/ops/` identified in §17.2 |
| Live Private Preview deployment | Not run — out of scope for a backend integration candidate |
| Supported-Compose qualification | Not run |
| Worker restart recovery | Not proved here; deliberately deferred (the campaign recorded it as `BLOCKED`) |
| Pre-acceptance queue-loss recovery | Deliberately deferred; not implemented |
| Exactly-once execution | Not claimed — the queue is at-most-once and lossy |
| Live provider execution | Not performed; no inference credit spent |
| Route-profile promotion | Not performed |
| Mainline reconciliation | **Performed.** The candidate was merged with `main` twice: at `00c3a4163` (merge `802c3c358`) and again at `74fd8f489` (merge `efd1a7892`). The single textual conflict, `guardian/db/models.py`, resolved to `main`'s version because `main` is a structural superset of the branch's copy and the coding-claim migrations are byte-identical on both sides — no schema change. See §23. |
| Human approval of the executable plan | **Not implemented.** The admission gate checks `approval_state == approved` only; an auto-approved (`scoped_auto`) intent reaches writable execution today. See the agreed next boundary in §16. |
| Plan-version hash bound to the approval | **Not implemented.** `plan_summary` has no write path after creation today, so the deployment snapshot and the intent's plan cannot diverge yet. They can once the plan becomes editable under review. See §16. |

---

## 19. Remaining frontend and profile gaps

Deliberately **not** done in this task:

- No Coding Mode control in `frontend/src/features/chat/components/Composer.tsx`.
- No change to the frontend `executionMode` or permission-policy UI.
- No user-facing repository picker; the repository binding is resolved from
  the project, never chosen by the caller.
- The Guardian delegation router remains **quarantined** — not mounted in
  `config/supported_profiles/`, and this change did not modify that
  directory.
- Coding execution is **not** part of Beta Supported.

A later frontend task must make the approved request shape reachable through
authenticated Guardian Chat. Today the frontend still posts a hardcoded local
identity and omits the provider, model, and credential-reference fields, so
**the delegated branch is not yet reachable from the product UI**.

The shape that frontend task must send is **present-but-empty**, not
omitted. The published request schema requires those three keys, and a
missing key is a schema violation that the route rejects before it reaches
the delegation service at all. An *empty* value is the assertion "no
proposal": Guardian then resolves the effective provider, model, and
credential from the account's own durable posture.

---

## 20. Release posture

**HOLD.** This is a backend integration candidate. A separate profile and
supported-runtime qualification gate must precede any release claim.

---

## 21. Files changed

| File | Change |
|---|---|
| `guardian/core/guardian_delegation_service.py` | New `dispatch_authorized_coding_request`, `_authorize_intent_for_dispatch`, `_assert_intent_is_dispatch_authority`, `_lock_intent_for_dispatch_commitment`, `_attempt_was_authorized`, and `_record_dispatch_failure`; instruction binding to the approved plan; atomic `persist_execution_binding` (deployment row lock, one transaction); proposal constraints in `_resolve_execution_binding`, `_select_newest_usable_account_credential`, and `_select_service_credential`; `GuardianDelegationRefusalError` and `BINDING_REFUSAL_STATUS` so a binding refusal is a 4xx with its own reason code; `_narrow_permission_posture` and `_path_is_within_scope`; `_create_agent_run_link` records the account origin |
| `guardian/routes/agent_orchestration.py` | `_resolve_authorized_coding_account`, `_get_delegation_service`, `_requested_permission_policy`, `_dispatch_authorized_coding_request`; `execute_coding_task` gains the delegated branch and an optional `Request` |
| `guardian/agents/coding_agent_contracts.py` | `delegation_intent_id` added; provider/model/credential remain **required in the published schema** — an empty value asserts "no proposal" on the authorized path, and the legacy path refuses an empty binding identity with a schema-conformant `RequestValidationError` (`type: "missing"`) |
| `guardian/core/guardian_dispatch.py` | The coding-run heartbeat cadence reads the same `CODING_RUN_HEARTBEAT_INTERVAL_SECONDS` override the worker reads, instead of restating a literal that could drift from it (§22, finding 2) |
| `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json` | One freshness field, rebound to the revision `main` holds (§23). The governed document's bytes are unchanged |
| `tests/contracts/test_guardian_coding_authorized_dispatch_contract.py` | New — 27 cases covering the 16 required properties, plus the adversarial substitution, failure-semantics, unnamed-path fork, cancellation/dispatch contention, credential-selection, refusal-mapping, and receipt-posture cases |
| `docs/architecture/proofs/runtime/2026-10-31-guardian-coding-authorized-dispatch-proof.md` | This receipt — implementation proof, independent-review disposition, and the independent verification record (§17.1–§17.3) |

The feature branch was not touched. `guardian/core/guardian_dispatch.py` and
the knowledge-graph node are outside the feature branch's own delta; the
first is a correction to code the feature branch introduced, and the second
is a reconciliation with `main` (§23).

**Untracked scratch files.** A number of `_*.py` / `_*.md` / `_*.json`
scratch files and one `guardian/routes/agent_orchestration.py~72523` editor
backup remain untracked in the worktree. They are **not** in the authorized
file list and were **not** staged; the commit uses an explicit `git add`
list. The host refuses unlink in this worktree (`Operation not permitted` /
`EXDEV`), so they could not be removed. They are inert: no module imports
them, and `guardian/routes/agent_orchestration.py~72523` is not a `.py`
import target.

---

## 22. Automated review findings and their disposition

An automated review ran against the head `2c33553f2` and reported five
findings. All five were read against the code before anything was changed,
and **all five were confirmed real**. They are fixed in this candidate.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | P2 | The newest account credential was selected before the credential authority had ruled on it, so a revoked or expired newest credential shadowed every older usable one and the request failed on that row alone | **Fixed.** `_select_newest_usable_account_credential` offers the candidates, newest first, to `authorize_credential_selection` and selects the first one the authority will actually use. The credential authority remains the only policy engine; nothing is re-implemented here |
| 2 | P2 | `guardian/core/guardian_dispatch.py` restated the heartbeat cadence as the literal `15` while the worker reads `CODING_RUN_HEARTBEAT_INTERVAL_SECONDS` from the environment, so raising the cadence left a 60-second staleness horizon in force and a healthy run could be classified `stale_uncertain` | **Fixed.** The core module now reads the same override with the same default. `guardian.core` still never imports a worker module, and the existing contract that asserts the two agree is unchanged and still passes |
| 3 | P1 | The dispatch's intent check was an unlocked read in its own transaction, so a cancellation could commit between that check and the queue submission, and the worker could then execute a task for an already-cancelled intent | **Fixed.** The dispatch now holds the intent row `FOR UPDATE` across its commitment, and re-asserts the intent's authority from its committed state at the moment the task is queued. The cancellation path already locks the same row, so cancellation and dispatch contend on it. The unlocked check survives as a fail-fast pre-check, and both share one assertion helper so they cannot drift apart |
| 4 | P2 | Every binding refusal was reported as `503 guardian_delegation_dispatch_failed`, which told the client the service was unavailable and invited an unbounded retry of a request that could never succeed, and discarded the reason code | **Fixed.** `GuardianDelegationRefusalError` carries the refusal's own stable reason code and a status chosen from `BINDING_REFUSAL_STATUS` — 403 for an authorization refusal, 409 for a proposal that conflicts with what Guardian resolved, 422 for a missing or malformed trusted input. Only `guardian_binding_credential_authority_unavailable` and `guardian_binding_model_unresolved` remain 503, because those are the only ones that are genuinely transient. It stays a `GuardianDelegationDispatchError`, so every existing caller that catches a dispatch failure keeps catching it, and the original binding error stays the `__cause__` |
| 5 | P2 | The dispatch receipt reported the authorized posture while the task was dispatched with the narrowed one, so a consumer reading the receipt recorded capabilities the attempt did not have | **Fixed.** The receipt's `permission_policy` is the effective narrowed policy — the same object the queued task carries. A contract asserts the receipt's policy equals the dispatched task's policy |

**A note on the fix for finding 3.** The lock is held across the queue
submission, not merely across the intent check. A refusal at that point
leaves a durable, inspectable attempt that was never queued, which is the
same lossy shape the deployment-lock fence already has: the attempt is
bound, the task is absent, and a later replay is refused rather than
re-queued. No retry or recovery was added to conceal it.

**A note on the fix for finding 4.** The reason code is safe to return: it
names a condition and never carries credential material. The credential
authority's own more specific refusal reason (for example
`credential_expired`) remains available on the exception's cause.

**Not fixed here.** Finding 2 lives in `guardian/core/guardian_dispatch.py`,
which was outside this task's authorized writable set. It was fixed only
after the owner widened that set for this specific file.

---

## 23. Mainline reconciliation and the knowledge-graph node

The branch was reconciled with `main` twice.

| Merge | `main` tip | Conflict | Resolution |
|---|---|---|---|
| `802c3c358` | `00c3a4163` | One, in `guardian/db/models.py` | `main`'s version. `main` is a structural superset of the branch's copy (1838 → 1892 elements, no branch element missing) and the coding-claim migrations are byte-identical on both sides, so this was a duplicate of PR #958 and not a schema change |
| `efd1a7892` | `74fd8f489` | None | The merge was clean. #984 touches the account-history recall surface; this branch's delta does not overlap it |

### 23.1 The one-line knowledge-graph repair

`main` at `74fd8f489` was **red on its own CI** — Architecture Contracts and
Backend Tests both failed — and every pull request whose merge ref included
`main` inherited that failure. The cause was a freshness pointer, not a
document: `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json`
declared `freshness.verified_commit = 644a2bcaf…`, a commit that exists only
in PR #984's own branch history. PR #984 was squash-merged, so that revision
never entered `main` and is not an ancestor of any merge ref built on `main`.

The node's `content_hash` was already correct. The validator compares a
node's `content_hash` against the bytes of the node's governed source **at
that node's declared `verified_commit`**, so the hash and the revision are
one claim and have to agree with each other. The bytes did not change, so
the revision that produced them did not change either: `main`'s tip
`74fd8f489…` is the commit that last touched
`docs/architecture/adr/adr-index.md`, and
`git cat-file blob 74fd8f489:docs/architecture/adr/adr-index.md | sha256sum`
is `cfacdecf4dd1e3483a702368b9aba676096a6a48a431edf104ed23578983a84d`, which
is exactly the node's recorded `content_hash`.

This branch carries that identical one-field correction, so its merge ref
validates regardless of the order in which `main` is repaired. The same
repair was landed on `main` itself as PR #987 (`69ef035a4`), and the two
produce **byte-identical** node files (`883835e0…`), so the two lines cannot
conflict.

Verified on the merged tree: the DLG validator returns `result = pass` with
**0 errors**, and `tests/architecture/test_document_lifecycle_graph_phase3.py`
together with `tests/architecture/test_document_lifecycle_graph_revision_binding.py`
give **53 passed** — the four cases that had been failing are green.

The six `broken_local_markdown_link` warnings on
`docs/architecture/README.md` remain warnings. They are severity
`warning`, not `error`, so they do not fail the validator, and they are
pre-existing on `main` and untouched by this change.

**A trap worth recording.** `docs/knowledge-graph/**/*.json` is excluded from
the LFS filter by `.gitattributes` (`!filter`), so those nodes are stored as
plain text. `git hash-object -w` on a `*.json` path *outside* that directory
applies the root LFS rule and writes a pointer blob instead, which silently
replaces a text blob. A hand-edit of a node has to be written with
`--no-filters` (or with `--path` pointing inside the excluded directory).

---

## 24. CI attribution for this pull request

A pull request's CI builds a **merge ref**: the pull request's head merged
with the base branch's current tip. So this branch's CI verdicts are a
function of `main` as well as of this branch.

The first two CI runs of this pull request were red, and both failures were
inherited rather than caused:

| Run | Head | Failure | Attribution |
|---|---|---|---|
| `41669687644` | `2c33553f2` | `tests/core/test_supported_profile_quarantine.py::test_coding_loop_execute_route_registered_and_rejects_incomplete_binding` | **This branch.** The envelope's optionality had emptied the published `required` set and let an incomplete body reach the route, which refused it with a string detail instead of a `type: "missing"` validation list. Fixed by `2c33553f2` |
| `41695817606` | `2c33553f2` | `tests/ops/test_worker_coding_pi_runtime_contract.py::test_runbook_uses_compose_owned_environment_and_canonical_readiness` | **A merge artifact.** The merge brought `main`'s stricter test but kept the branch's substantively newer runbook, which wrapped the asserted sentence one word earlier. Fixed by `855a98063`, a two-line reflow that preserves the branch's newer content in full |
| `41702277276` | `855a98063` | `tests/architecture/test_document_lifecycle_graph_phase3.py` and `tests/architecture/test_document_lifecycle_graph_revision_binding.py` | **Inherited from `main`.** The failing set was *identical* to the set failing on `main`'s own tip `74fd8f489`. See §23.1 |

The attribution method is the set difference, not the totals: this branch's
failing set and `main`'s failing set on the same base were compared and are
the same four cases, so the branch introduced none of them.

One further trap belongs in the record: **the merge ref does not refresh when
`main` advances.** A pull request whose head has not been re-pushed keeps
running CI against the base tip as of its last synchronization, so it can
keep reporting a defect that `main` has already repaired. Re-syncing the
head — a push, or "Update branch" — is what re-points it.

## 25. The `guardian/agents/store.py` conflict with `main`, and its resolution

### 25.1 The conflict surface

`main` advanced to `c1e377158` (PR #986, the coding-worker claim-store
reconciliation) while this branch was open, and both sides had rewritten the
same module. `git merge-tree --write-tree 1b2934ace c1e377158` produced
**exactly one conflicted file**: `guardian/agents/store.py`.

Relative to the merge base `74fd8f489`, both sides changed `<module>`,
`_is_terminal_agent_run_status` and the `AgentStore` class body; each side
also added its own module-level helper. At method granularity inside
`AgentStore`, **exactly three methods were rewritten on both sides**:

| Method | `main`'s form | This branch's form |
|---|---|---|
| `claim_run_for_acceptance` | 85-line PostgreSQL compare-and-set | 190-line in-Python acceptance |
| `renew_coding_run_heartbeat` | PostgreSQL conditional update | in-Python conditional update |
| `claim_coding_run_terminal` | PostgreSQL claim-fenced terminal | in-Python claim-fenced terminal |

Two facts decided the shape of the resolution.

**`main` adds no `AgentStore` method that this branch lacks.** The method-set
difference is one-directional: 12 members exist only on this branch (the
liveness snapshot, the unresolved-run review, the uncertain quarantine and its
operator route, the terminal finalization and side-evidence writers, the
artifact and escalation writers, and the lineage matcher), and **0** exist only
on `main`. `main`'s `AgentStore` is a method-level subset of this branch's.

**The merged worker is this branch's.** `guardian/workers/coding_worker.py`
auto-merges to this branch's version, and that version calls
`finalize_claimed_coding_result`, `finalize_claimed_run_status` and
`list_unresolved_guardian_coding_runs` — all three are members that exist only
on this branch. So a resolution that took `main`'s file wholesale would have
deleted the very layer the merged worker calls.

The resolution is therefore **additive**: this branch's `store.py` with
`main`'s three compare-and-set methods and `main`'s two module-level helpers
lifted in verbatim, and nothing of this branch's removed. The method bodies
were lifted by `ast` line range from `c1e377158` and spliced in; none was
hand-transcribed.

### 25.2 The terminal-time lineage guard is strengthened, not dropped

This branch guarded the terminal decision with a class-level method,
`_coding_run_lineage_matches(self, session, run_row)`, that re-reads the
deployment and refuses the terminal decision when the deployment's asserted
thread or user contradicts the run. `main` guards the same decision with a
module-level function, `_coding_run_lineage_matches(run, deployment, claimed)`.

`main`'s is **strictly stronger**, and it is the guard the merged code now
carries:

| Condition | This branch's method | `main`'s function |
|---|---|---|
| Run carries no deployment at all | allow | refuse |
| Deployment id set but the row is absent | refuse | refuse |
| Deployment id does not match the run | not checked | refuse |
| Run carries no account origin | not checked | refuse |
| Run carries no thread | not checked | refuse |
| Deployment spec is not a dict | tolerate | refuse |
| Persisted execution binding is not a dict | not checked | refuse |
| Asserted thread contradicts the run | refuse | refuse |
| Asserted user contradicts the run | refuse | refuse |
| Any *other* identity assertion contradicts | not checked | refuse |

Every condition this branch's method refuses on, `main`'s function refuses on
as well; `main`'s refuses on seven more. The superseded class-level method is
therefore removed as dead code — no caller remains — and **no terminal-time
authority guard is dropped**.

### 25.3 The one genuine contradiction: the clock of the durable run row

The two sides disagreed about one persisted value, and the disagreement was
not reconcilable.

This branch's acceptance stamped `agent_runs.started_at` from the **host**
clock (`_utc_now()`). `main`'s acceptance stamps it from the **database**
clock (`func.coalesce(AgentRun.started_at, func.now())`), together with the
initial heartbeat column, and `main`'s own contract states the invariant
explicitly — *"A wildly wrong host clock cannot affect persisted execution
timestamps"* — asserting `before <= started_at <= heartbeat <= after` against
database `clock_timestamp()` readings.

This branch's heartbeat contract asserted the opposite for `started_at`:
under a patched host clock it required `started_at.year == 1999`. Both
contracts read the **same persisted column** of the same row, so no
implementation can satisfy both. The disagreement was a real one, not an
artifact: the first run of the merged tree failed exactly this case, and
nothing else.

The resolution takes `main`'s position, and **does not change `main`**.
`main`'s three methods are adopted verbatim; what changes is one
over-specified assertion in this branch's own heartbeat contract. That
assertion pinned the acceptance stamp *to* the host clock in order to show
that the heartbeat was *not* on the host clock. Corrected, it asserts the
invariant the test's own name and docstring already claim — *"The heartbeat
uses PostgreSQL's clock, not the worker's wall clock"* — now covering both
timestamps:

```python
# before
assert state["started_at"].year == 1999
assert state["heartbeat_at"].year != 1999

# after
assert state["started_at"].year != 1999
assert state["heartbeat_at"].year != 1999
```

The corrected assertion is **stronger**: the previous one proved only that
the heartbeat was independent of the host clock, while pinning the acceptance
stamp to it; the corrected one proves that *neither* persisted timestamp can
be moved by a wrong host clock. It also brings the acceptance stamp into
line with the branch's own terminal comment — *"The database clock is the
canonical time source for the durable run row"* — which the branch already
applied to `ended_at`.

### 25.4 Verification of the resolved tree

Run against the resolved tree, with PostgreSQL 16.15 as the durable store
(`postgresql://` scheme; the `postgresql+psycopg://` scheme is rejected by
raw `psycopg` and errors 36 unrelated tests locally):

| Selection | Result |
|---|---|
| `tests/contracts/` (29 files) | **719 passed, 1 xfailed, 0 failed** |
| The ten coding contract suites alone, before §25.3 | 307 passed, 1 xfailed, **1 failed** (the clock case) |
| The same ten suites, after §25.3 | all green |

The ten coding suites are: authorized dispatch, claim store, worker
acceptance, worker heartbeat, worker ownership, worker recovery, worker
terminal fencing, run liveness, run uncertain quarantine, and worker restart
review.

### 25.5 What was not changed

`main` was not modified in any way by this resolution. No file on `main` was
edited, no claim on `main`'s lane was taken, and `main`'s own
`tests/contracts/test_guardian_coding_claim_store_contract.py` was carried
across unmodified and passes as written. The peer's claim-store
implementation is present in the resolved tree exactly as `main` holds it.

