# Guardian Coding-Run Quarantine — Operator Invocation Path

**Date:** 2026-10-26
**Branch:** `feature/guardian-delegation-acceptance-axis`
**Base commit:** `158ea89301ab1528459f8b0adb66cbe1bf5dd737`
**Classification:** **PASS** — with release status unchanged at **HOLD**

This receipt records the operator invocation path for the Guardian
uncertain coding-run quarantine: one explicitly authenticated, operator-only
HTTP action that reuses the existing Guardian operator authority and the
existing atomic quarantine persistence, proven end to end against disposable
PostgreSQL.

It does **not** modify, weaken, or supersede the previous slice's result
(`2026-10-26-guardian-coding-uncertain-quarantine-proof.md`). That slice
established the disposition; this one establishes that an operator can reach
it.

---

## 1. Evaluated starting commit

| Item | Value |
|---|---|
| Starting HEAD | `158ea89301ab1528459f8b0adb66cbe1bf5dd737` |
| Branch | `feature/guardian-delegation-acceptance-axis` (ahead 6 of `origin/...` at slice start) |
| Tracked working tree at start | clean |
| `git merge-base --is-ancestor 158ea893 HEAD` | true |
| `alembic heads` | `d86f2a4b1c90 (head)` — single head, unchanged |
| Import origin (swept) | `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261020-cecd701e/guardian/__init__.py` |

Source hashes (SHA-256), evaluated tree:

| File | Hash |
|---|---|
| `guardian/routes/guardian_delegations.py` | `21f4f5017c4fb95adf65e6e15977293686cd735b017edf6ad4130f616d352a70` |
| `guardian/core/guardian_delegation_service.py` | `0630823d75bd067f4f8e3545fc18a980e2c24800b20915d29c1554ae6c0422e4` |
| `tests/contracts/test_guardian_coding_run_quarantine_operator_route_contract.py` | `1b28ba85dd9881b0da5d8837678dcd926955d4f1ccf7189d7ca95a2f31dab4ef` |
| `tests/contracts/test_guardian_delegation_phase2a_contract.py` | `d4b3f73e0a87d797e936f171ee88a922d1358c2fe18bb43769764709d416f791` |
| `tests/contracts/test_guardian_delegation_command_center_transcript_contract.py` | `c33664cba0cdd3d053d719a9bf0944e1b0bff6e90cedbca2fc0b8fa993643317` |
| `tests/contracts/test_guardian_delegation_approval_cancel_contract.py` | `3310653545d7a8af81b88e1e8d78c0b653d69ceb97c6c6959dff94c511521c23` |
| `tests/identity/test_operator_route_auth_migration.py` | `c5f91e1b294453f932184b5747eb574798eee49aeb45835e473dacaf6e397b67` |

Baseline (`158ea893`) hashes for the two source files, for the red/green
comparison:

| File | Baseline hash |
|---|---|
| `guardian/routes/guardian_delegations.py` | `492cb5b626a206bf099902818437ab1797192a277d1f7df8721b5d9347d48bda` |
| `guardian/core/guardian_delegation_service.py` | `3cd9348d6e480c9889eca18d27cf37a9884f28efb2ebb4a67705755457231160` |

## 2. Exact route path and HTTP method

```
POST /api/guardian/delegations/runs/{run_id}/quarantine
```

One route, one method. The path segment `runs` places it outside the
`{intent_id}` space, so it cannot collide with `/{intent_id}`,
`/{intent_id}/approve`, or `/{intent_id}/cancel`.

The registered route table of the router, in the evaluated tree:

```
POST /api/guardian/delegations
POST /api/guardian/delegations/runs/{run_id}/quarantine
POST /api/guardian/delegations/{intent_id}/approve
POST /api/guardian/delegations/{intent_id}/cancel
GET  /api/guardian/delegations
GET  /api/guardian/delegations/{intent_id}
GET  /api/guardian/delegations/{intent_id}/transcript
```

## 3. Existing router and feature gate

| Item | Value |
|---|---|
| Router | `guardian/routes/guardian_delegations.py`, `APIRouter(prefix="/api/guardian/delegations")` — the **existing** router, reused |
| Router-level dependency | `dependencies=[Depends(require_operator_auth)]` — pre-existing, unchanged |
| Gate | `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES` — pre-existing, `default_enabled=False`, **not changed** |
| Application registration | unchanged; `_include_router(...)` was not edited |
| New routers | none |
| New permission subsystem | none |
| Migration | none |

## 4. Authentication mechanism

The route requires the **existing** `require_operator_auth`. Two mechanisms
remain accepted, exactly as before this slice:

- the configured Guardian API key, presented as `X-API-Key: <key>` or
  `Authorization: Bearer <key>`;
- an **operator-purpose** signed session token, presented as
  `Authorization: Bearer <token>` or in the `gc_session` cookie.

`require_operator_auth` rejects account-purpose and guest-purpose material
before the API-key fallback, so an account credential cannot fall back to an
operator API key. The mixed-principal check in remote-authentication mode is
untouched.

## 5. Operator actor derivation

The actor is **derived by the service**, never supplied by the caller:

```
route → raw credential material (server-side) → service._authenticate_operator()
      → require_operator_auth(...) → "operator-api-key" | "operator-session"
      → service → GuardianDelegationService.quarantine_uncertain_coding_run(...)
```

The dependency's returned display identity is never used as authority, and
there is no `operator_authorized=True` parameter and no caller-supplied actor
name. The observed receipt carried `"operator_actor": "operator-api-key"`.

## 6. Credential transport and secrecy

The route reads the credential material from the **verified request** and
hands it to the service as a server-side argument. The material is never
read from the body, the query string, or the path, and never appears in the
response, the exception detail, the application logs, the escalation
evidence, or the Redis task events.

The contract asserts this directly:

- the request body contains no credential field (the model is
  `extra="forbid"`, so one is a 422);
- the response body contains no credential material;
- the durable escalation payload contains no credential material
  (`credential_in_escalation_evidence: False` in §15);
- the credential reaches the service as a keyword argument, proven by a
  delegation spy that asserts the service received the raw key
  (`call["operator_api_key"] == _OPERATOR_KEY`).

## 7. Request contract

Strict Pydantic model, `extra = "forbid"`:

| Field | Bound | Meaning |
|---|---|---|
| `expected_worker_instance_id` | 1–64 | the worker the operator believes owns the run |
| `expected_worker_claim_id` | 1–64 | the claim the operator believes owns the run |
| `reason` | 1–2000 | the operator's explicit reason |

Refused by the model (422): an authorization boolean, a target run status, an
escalation status, a new execution binding, a credential selection, a retry
instruction, a worktree deletion instruction, a provider command, a
client-supplied escalation payload, a missing reason, an empty reason, an
oversized reason, a missing worker identity, a missing claim identity, and
any unknown field — including `account_user_id`, which is why the account can
never be client-supplied.

## 8. Service invocation

```
GuardianDelegationService.quarantine_uncertain_coding_run(
    run_id,
    expected_worker_instance_id,
    expected_claim_id,
    reason,
    operator_api_key=...,
    operator_session_token=...,
    operator_session_cookie=...,
    expected_account_user_id=None,   # resolved canonically inside the service
)
```

Three narrow adapter changes were required in the service, and only these
three:

1. `operator_session_cookie` added, so the route can transport the cookie
   credential form without weakening the verification contract;
2. `expected_account_user_id` made optional, with the canonical account read
   from the run row when the caller omits it — the account is never
   client-supplied, and the store's cross-account check still runs inside
   the transaction;
3. `recorded_at` added to the receipt, read from the committed
   `AgentEscalation.created_at`.

The route delegates to the service; it does not reimplement it.

## 9. Canonical eligibility

The route does not duplicate eligibility logic. It delegates to the service
and the persistence operation, which revalidate inside the transaction:

- current `AgentRun` status;
- expected worker instance and expected claim;
- canonical deployment lineage;
- the existing operator authorization;
- the **database-clock** heartbeat condition;
- the existing quarantine reason policy;
- the existing transactional guarantees.

A stale snapshot supplied by an operator does not override current database
state. The contract proves a **fresh heartbeat prevents quarantine** (409),
a **changed claim prevents quarantine** (409), and an **already-terminal run
remains unchanged**.

## 10. Atomic persistence reuse

| Item | Value |
|---|---|
| Sole persistence implementation | `AgentStore.quarantine_coding_run_as_uncertain(...)` — unchanged, read-only this slice |
| Route DB writes | none: the route issues no `UPDATE agent_runs` and no `INSERT agent_escalations` |
| Transactional split | none; the run transition and its escalation commit together |
| Terminal task event published from the route | none |
| Source-thread result delivered from the route | none |
| Duplicate escalation on retry | none (§16) |

## 11. HTTP response mapping

| Outcome | HTTP |
|---|---|
| Newly committed quarantine | **201** |
| Existing identical quarantine (read-only) | **200** |
| Ownership mismatch / fresh heartbeat / changed claim | **409** |
| Already-terminal run | **409** |
| Conflicting existing escalation | **409** |
| Unknown run | **404** |
| Operator authentication or authorization failure | **401** |
| Database unavailable | **503** |

A persistence error is never converted into a success response. Errors are
raised as `GuardianDelegationError` and mapped to
`HTTPException(exc.status_code, exc.detail)`, matching the conventions already
used by the sibling routes on the same router.

## 12. Account and guest rejection

| Credential | Result |
|---|---|
| None (anonymous) | 401 |
| Account-purpose signed token | 401 |
| Guest signed token (canonical guest cookie) | 401 |
| Guest signed token (session-cookie lane) | 401 |
| Expired operator token | 401 |
| Arbitrary bearer token | 401 |
| Incorrect configured API key | 401 |
| Mixed principal (API key + account bearer, remote auth mode) | 400 |
| Account-owned BYOK credential | not an operator credential; 401 |
| Worker execution credential | not an operator credential; 401 |
| Knowledge of the run id or claim id alone | grants nothing; 401 without a credential |

The request contract refuses an account field outright, so the route has no
way to aim a disposition at another account, and the canonical account read
inside the transaction keeps the store's cross-account check in force.

## 13. Feature-gate-disabled behavior

Real application import, `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES=0`:

```
registered: []
```

No delegation route is present at all — not the new one, and not the
pre-existing ones. There is no new public operator surface, no application
startup change, and no change to the supported release profile.

## 14. Feature-gate-enabled behavior

Real application import, `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES=1`:

```
registered: ['/api/guardian/delegations',
             '/api/guardian/delegations/runs/{run_id}/quarantine',
             '/api/guardian/delegations/{intent_id}',
             '/api/guardian/delegations/{intent_id}/approve',
             '/api/guardian/delegations/{intent_id}/cancel',
             '/api/guardian/delegations/{intent_id}/transcript']
```

Operator authentication is enforced, the route invokes the real
`GuardianDelegationService`, the service invokes the existing atomic
persistence, and the durable readback in §15 reflects the authorized outcome.

**A supported profile still quarantines the whole family.** With
`CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp` and the gate on, the
registered delegation paths are `[]`. The new invocation path inherits the
family's quarantine, so it cannot enter the supported release surface even
when the feature gate is on. This is asserted by the contract.

## 15. PostgreSQL before/after readback

One synthetic operator HTTP invocation in a disposable environment. No real
provider key was used and Pi was not launched. Every readback was taken
through a **separate database session** from the one that served the request.

Before:

```json
{
  "status": "running",
  "worker_instance_id": "cwi_quarantine_worker_a",
  "claim_id": "cwc_quarantine_claim_a",
  "last_heartbeat_at": "2026-10-26 23:25:10.453509+00:00",
  "escalation_count": 0,
  "artifact_count": 0,
  "result_message_count": 0
}
```

The HTTP invocation:

```
status: 201
{
  "already_quarantined": false,
  "disposition": "escalated",
  "escalation_id": 1,
  "operator_actor": "operator-api-key",
  "original_claim_id": "cwc_quarantine_claim_a",
  "original_worker_instance_id": "cwi_quarantine_worker_a",
  "reason_code": "guardian_dispatch_liveness_unproven",
  "recorded_at": "2026-10-26T23:36:18.766357+00:00",
  "run_id": "run_604e779626d54ef7"
}
```

After, through a separate session:

```json
{
  "status": "escalated",
  "worker_instance_id": "cwi_quarantine_worker_a",
  "claim_id": "cwc_quarantine_claim_a",
  "escalation_count": 1,
  "escalation_status": ["open"],
  "escalation_reason_code": ["guardian_dispatch_liveness_unproven"],
  "escalation_operator_actor": ["operator-api-key"],
  "artifact_count": 0,
  "result_message_count": 0
}
```

```
credential_in_escalation_evidence: False
credential_lease_count: 0
queued_coding_task: None
```

The original worker identity and the original claim identity are unchanged,
exactly one open escalation is present, the operator provenance is preserved,
and there is no coding-result artifact, no result message, no credential
lease, and no queue task.

## 16. Idempotent repeated invocation

The same request, submitted again:

```
status: 200
{
  "already_quarantined": true,
  "disposition": "escalated",
  "escalation_id": 1,
  "operator_actor": "operator-api-key",
  ...
}
escalation_count_after_repeat: 1
status_after_repeat: escalated
ownership_after_repeat: ('cwi_quarantine_worker_a', 'cwc_quarantine_claim_a')
```

No duplicate escalation, no new execution, no modified ownership, and a
bounded idempotent response. The second response is a **read-only
observation**, distinguishable from the 201 that committed the disposition.

## 17. Concurrent terminalization protection

First-committer-wins is unchanged. The terminal-then-quarantine order yields
no quarantine; the quarantine-then-terminal order rejects the stale terminal
decision. The route does not weaken the claim-fenced terminalization
contract, and the terminal-fencing contract
(`tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py`,
23 cases) still passes unchanged.

## 18. Cross-account and peer protection

- **Peer runs.** Worker A owns the target run, Worker B owns a second,
  independently accepted run. The operator invocation moves only the run it
  names: the peer's run stays `running` with its own instance and claim, and
  carries no escalation.
- **Cross-account.** The account is canonical and read from the run row; the
  request model refuses an `account_user_id` field outright (422), leaving
  the run untouched. The store's cross-account check still runs inside the
  transaction.

## 19. No queue, lease, or result mutation

| Side effect | Observed |
|---|---|
| Coding-result artifact created | none (`artifact_count: 0`) |
| Source-thread result message created | none (`result_message_count: 0`) |
| Queue task inserted | none (`queued_coding_task: None`) |
| Credential lease issued | none (`credential_lease_count: 0`) |
| New worker attempt authorized | none |
| Terminal task event published | none |
| Duplicate escalation row | none |

## 20. Red-then-green evidence

Baseline `158ea89301ab1528459f8b0adb66cbe1bf5dd737`, unmodified source (the
tracked changes were stashed; the new contract was kept in place so it could
run against the baseline):

| Run | Result |
|---|---|
| **RED** — new contract at baseline | **28 failed, 11 passed** |
| **GREEN** — new contract at the evaluated tree | **39 passed** |

The RED run used the **final** 39-case contract against the **unmodified**
baseline source (the tracked changes were stashed; the new contract was kept
in place so it could run against the baseline). The RED failures are exactly
the cases that require the route to exist; each fails with the route absent
(404 / assertion on the route path). The 11 that pass at baseline are the
cases whose subject is the *absence* of a route or of a side effect, which
are trivially true when the route does not exist. The expected RED condition
was missing route integration; no persistence capability was invented and the
previous slice's PASS was not altered.

The RED run also established that the identity-manifest failure is inherited:
`tests/identity/test_operator_route_auth_migration.py::test_frozen_operator_manifest_has_exactly_58_registrations_in_13_files`
fails **at the unmodified baseline** on `guardian.routes.coding_work_orders`,
whose three `continuation-authorit(y|ies)` operator routes are not declared in
the frozen manifest. Same identity, same cause, before and after this slice.

## 21. Focused validation

| Path | Result |
|---|---|
| `tests/contracts/test_guardian_coding_run_quarantine_operator_route_contract.py` | **39 passed** |
| `tests/contracts/test_guardian_coding_run_uncertain_quarantine_contract.py` | **34 passed** |
| `tests/contracts/test_guardian_coding_worker_terminal_fencing_contract.py` | 23 passed |
| `tests/contracts/test_guardian_coding_worker_recovery_contract.py` | 19 passed, 1 xfailed |
| `tests/contracts/test_guardian_coding_run_liveness_contract.py` | 31 passed |
| `tests/contracts/test_guardian_coding_worker_heartbeat_contract.py` | 25 passed |
| `tests/contracts/test_guardian_coding_worker_ownership_contract.py` | 26 passed |
| `tests/contracts/test_guardian_coding_worker_acceptance_contract.py` | 19 passed |
| `tests/contracts/test_guardian_dispatch_integration_contract.py` | 21 passed |
| `tests/contracts/test_guardian_delegation_phase2a_contract.py` | 30 passed |
| `tests/contracts/test_guardian_delegation_phase3_delivery_contract.py` | 39 passed |
| `tests/contracts/test_guardian_delegation_command_center_transcript_contract.py` | 12 passed |
| `tests/contracts/test_guardian_delegation_approval_cancel_contract.py` | 13 passed |
| `tests/contracts/test_guardian_delegated_task_projection_contract.py` | 3 passed |
| `tests/identity/test_operator_route_auth_migration.py` | 16 passed, 1 inherited failure |
| `guardian/tests/workers/test_coding_worker.py` | 89 passed, 14 inherited failures |
| `guardian/tests/workers/test_coding_worker_regression_guard.py` | 2 passed, 1 inherited failure |
| `guardian/tests/agents/` | 107 passed |
| `tests/agents/test_execution_ledger_store.py` | 11 passed |
| **Focused sweep total** | **559 passed, 16 failed, 1 xfailed** (576 collected) |

`alembic heads` → `d86f2a4b1c90 (head)`, single head, unchanged.

The sweep was run against disposable PostgreSQL with the worktree pinned on
`PYTHONPATH`:

```
PYTHONPATH=<worktree> \
TEST_DATABASE_URL=postgresql+psycopg://hb:hbpw@127.0.0.1:55500/hbdb \
python -m pytest -o addopts="" -q -p no:randomly \
  tests/contracts/test_guardian_coding_run_quarantine_operator_route_contract.py \
  ... (the 19 paths above) ...
```

576 tests collected; 559 passed, 16 failed, 1 xfailed; 10m29s.

**The monolithic backend gate is reported as NOT RUN to completion.** The
previous slice's monolithic run reached 87 % before the runtime's one-hour
background-task cap aborted it, and it was never completed to a clean
baseline. This slice therefore relies on the focused sweep as its
authoritative regression evidence, and does not present a partial monolithic
run as a clean full-suite pass.

### The new contract's 39 cases

| # | Spec case | Test |
|---|---|---|
| 1 | Route absent when the flag is disabled | `test_the_route_is_absent_when_the_feature_flag_is_disabled` |
| 2 | Route present when explicitly enabled | `test_the_route_is_present_when_the_feature_flag_is_explicitly_enabled` |
| — | Supported profile still quarantines the family | `test_the_route_stays_quarantined_under_a_supported_profile` |
| 3 | Anonymous request rejected | `test_an_anonymous_request_is_rejected` |
| 4 | Account-purpose token rejected | `test_an_account_purpose_token_is_rejected` |
| 5 | Guest-purpose token rejected | `test_a_guest_credential_is_rejected` |
| 6 | Expired operator token rejected | `test_an_expired_operator_token_is_rejected` |
| 7 | Invalid operator key rejected | `test_an_invalid_operator_key_is_rejected` |
| 8 | Mixed-principal request rejected | `test_a_mixed_principal_request_is_rejected` |
| 9 | Valid operator API key accepted | `test_a_valid_operator_api_key_is_accepted` |
| 10 | Valid operator-purpose session accepted | `test_a_valid_operator_session_is_accepted` |
| 11 | Caller-supplied authorization boolean rejected | `test_a_caller_supplied_authorization_boolean_is_rejected` |
| 12 | Missing operator reason rejected | `test_a_missing_operator_reason_is_rejected` |
| 13 | Oversized operator reason rejected | `test_an_oversized_operator_reason_is_rejected` |
| 14 | Missing worker identity rejected | `test_a_missing_worker_identity_is_rejected` |
| 15 | Missing claim identity rejected | `test_a_missing_claim_identity_is_rejected` |
| 16 | Unknown request fields rejected | `test_unknown_request_fields_are_rejected` |
| 17 | Valid quarantine delegates to the existing service | `test_the_route_delegates_to_the_existing_service` |
| 18 | Service revalidates canonical ownership | `test_the_service_revalidates_canonical_ownership` |
| — | Peer run is unaffected | `test_an_active_peer_run_is_unaffected` |
| — | The request cannot name an account | `test_the_request_cannot_name_an_account` |
| 19 | Fresh heartbeat prevents quarantine | `test_a_fresh_heartbeat_prevents_quarantine` |
| 20 | Changed worker claim prevents quarantine | `test_a_changed_worker_claim_prevents_quarantine` |
| 21 | Already-terminal run remains unchanged | `test_an_already_terminal_run_remains_unchanged` |
| 22 | Existing identical quarantine is idempotent | `test_an_existing_identical_quarantine_is_idempotent` |
| 23 | Conflicting quarantine is rejected | `test_a_conflicting_quarantine_is_rejected` |
| 24 | Concurrent terminalization remains safe | `test_concurrent_terminalization_remains_safe` |
| 25 | Operator response contains bounded evidence | `test_the_operator_response_contains_bounded_evidence` |
| 26 | No credential material in the response | `test_no_credential_material_appears_in_the_response` |
| 27 | No secret material in escalation evidence | `test_no_secret_material_enters_escalation_evidence` |
| 28 | No duplicate escalation row | `test_no_duplicate_escalation_row_is_created` |
| 29 | No coding-result artifact fabricated | `test_no_coding_result_artifact_is_fabricated` |
| 30 | No source-thread result fabricated | `test_no_source_thread_result_is_fabricated` |
| 31 | No queue task inserted | `test_no_queue_task_is_inserted` |
| 32 | No credential lease issued | `test_no_credential_lease_is_issued` |
| 33 | No new worker attempt authorized | `test_no_new_worker_attempt_is_authorized` |
| 34 | Database unavailability fails closed | `test_database_unavailability_fails_closed` |
| 35 | Existing delegation routes retain their behavior | `test_existing_delegation_routes_retain_their_behavior` |
| — | Route absent under the default posture | `test_the_route_is_absent_under_the_default_posture` |

## 22. Inherited failures

The 16 failures are exactly the inherited ones, compared by **exact test
identity and cause**:

| # | Test | Cause | Status |
|---|---|---|---|
| 1 | `tests/identity/test_operator_route_auth_migration.py::test_frozen_operator_manifest_has_exactly_59_registrations_in_13_files` | the frozen manifest's `guardian.routes.coding_work_orders` drift: three undeclared `continuation-authorit(y\|ies)` operator routes | inherited — **proven at the unmodified baseline** (§20) |
| 2–15 | `guardian/tests/workers/test_coding_worker.py` (14 cases: `test_one_worker_runs_two_pi_bindings_against_local_provider_mocks`, `test_worker_records_campaign_attempt_ledger_and_work_order_markers`, `test_worktree_isolation_enabled_runs_adapter_and_validation_in_isolated_cwd`, `test_worktree_isolation_preserves_relative_subdirectory_cwd`, `test_isolated_success_captures_patch_manifest_and_terminal_metadata`, `test_isolated_success_patch_capture_includes_untracked_file`, `test_patch_artifact_root_can_stay_clean_with_gitignore_rule`, `test_dirty_original_checkout_does_not_block_isolated_execution`, `test_isolated_success_cleans_up_by_default_without_promoting_changes`, `test_isolated_failure_keeps_worktree_by_default`, `test_oversized_patch_writes_manifest_without_partial_patch`, `test_keep_on_success_flag_preserves_isolated_worktree`, `test_cleanup_failure_is_reported_without_overwriting_success`, `test_dirty_preflight_fails_before_adapter_execution`) | predominantly this sandbox's own limits — git worktree creation is denied on this filesystem | inherited |
| 16 | `guardian/tests/workers/test_coding_worker_regression_guard.py::test_no_name_error_in_guard_path` | `NameError: name '_fetch_work_order' is not defined` in `guardian/workers/coding_worker.py` (campaign-attempt-ledger path) — a genuine pre-existing product defect, reported and **not** patched | inherited |

No new failure was introduced by this slice. The recovery contract's
strict-xfail restart-reconciliation tripwire is **unchanged and still
xfail**.

### Three files outside the authorized list

The delegation router's route set is pinned in four places: the phase2A
contract, the command-center transcript contract, the approval/cancel
contract, and the frozen operator manifest in
`tests/identity/test_operator_route_auth_migration.py`. Only the first was
listed as writable. The other three were updated, because each asserts an
**exact** equality against the real route set and would otherwise fail for a
reason this slice created:

| File | Change | Why it could not be left alone |
|---|---|---|
| `tests/contracts/test_guardian_delegation_command_center_transcript_contract.py` | one path added to the expected route set | asserts `route_paths == {...}`; the new path makes it fail |
| `tests/contracts/test_guardian_delegation_approval_cancel_contract.py` | one path added to the expected route set | asserts `route_paths == {...}`; the new path makes it fail |
| `tests/identity/test_operator_route_auth_migration.py` | one registration added; 58 → 59 registrations; 29 → 30 default-off | the product's declaration of its **operator-route inventory**; it asserts an exact two-way equality, so leaving it stale would have introduced a *new undeclared operator route* in a module the manifest does cover |

None of these grants, removes, or redefines authority. Each already declared
this route's authentication mechanism and its default-off activation; they
were inventories of the surface, and the surface legitimately moved by
exactly one authorized route. The edits are one path and two counts each.
This is disclosed here rather than made silently.

## 23. Remaining operator-UI and restart-reconciliation gaps

1. **No operator UI.** There is no screen, button, or command that calls
   this route. The invocation is an authenticated HTTP call an operator
   makes directly.
2. **Restart reconciliation remains unqualified.** A worker that dies while
   Guardian is down is still not reconciled automatically. The strict-xfail
   tripwire in the recovery contract remains unresolved.
3. **No automatic worker-death determination.** A stale heartbeat remains
   inconclusive evidence, not proof of death.
4. **No automatic retry and no ownership takeover.** The route grants
   neither.
5. **No deployment.** A feature-gated route proven in a disposable
   environment is not a production deployment. The supported Compose path is
   unchanged, and the family remains quarantined in every supported profile.
6. **External effects remain uncertain.** A committed quarantine protects
   canonical state only.

## 24. Classification

**PASS**, with release status unchanged at **HOLD**.

The stopping condition is met: an explicitly authenticated operator can
invoke the already-proven uncertain-run quarantine through the existing
feature-gated Guardian delegation route, and disposable HTTP-to-PostgreSQL
proof establishes the correct authorization, persistence, idempotency, and
refusal behavior.

### Invariant confirmation

- No second operator authority was introduced. The route requires the
  existing `require_operator_auth`, and the service performs its own
  authoritative verification.
- No general account endpoint exposes quarantine. The route is operator-only,
  and the account is canonical and never client-supplied.
- No existing feature gate was enabled by default.
  `CODEXIFY_ENABLE_GUARDIAN_DELEGATIONS_ROUTES` remains `default_enabled=False`,
  and every supported profile still quarantines the family.
- No automatic quarantine or retry was activated. Nothing calls this route
  on a timer, at startup, or in the background.
- No ownership takeover occurred.
- No startup reconciliation was introduced.
- No real provider call occurred. No provider key was used and Pi was not
  launched.
- No production resources were modified. Every database touched was a
  disposable container database.
- No external sandbox guarantee was claimed.
- Restart recovery remains unqualified.
- Release remains HOLD.
