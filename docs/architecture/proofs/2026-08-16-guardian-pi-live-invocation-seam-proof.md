# Guardian-authorized Pi live invocation seam proof

## 1. Scope

Implemented and deterministically proved one internal Guardian-owned, one-shot
Pi invocation primitive. It consumes existing Pi authorization contracts,
invokes an injected or existing Pi harness adapter once, and returns bounded
in-memory outcome, receipt, and result objects. It adds no Campaign Engine
orchestration, persistence, queueing, MiniMax configuration, or live provider
call.

## 2. Workflow classification

- Execution lane: `architecture-impact`
- Task kind: `implementation + proof`
- Evidence posture: `IMPLEMENTED_AND_TEST_PROVEN`, not live-provider proof.

## 3. ADR impact

`Aligned with existing ADR(s)`. No ADR was created or modified. This is the
accepted lower-level implementation of Guardian authority, identity, result
validation, and bounded-mutation requirements.

## 4. Governing ADRs/contracts

- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract

## 5. Task base HEAD

`a71c8d1c88e9a6f861af6ffbf197c760f174a642`

## 6. Integration/drift result

`PASS`. The required prior base
`bf0d46bc05037486dbf4af17592e61abe38c9a68` is an ancestor of the observed
remote head. Intervening changes were inspected before editing and did not
modify Guardian Pi, agent adapters, Coding Worker, Pi wrapper, ADR-066,
ADR-068, Pi Invocation Boundary, Agent Tool Loop, provider-execution, or
coding-execution authority. The worktree was created from that remote head;
no merge or rebase occurred.

## 7. Prior blocker

`RESOLVED_AT_IMPLEMENTATION_AND_TEST_PROOF_LEVEL`.

Before this change, `guardian/pi/` supplied contracts and pure validation only;
the direct Codex adapter intentionally failed closed; the legacy Pi adapter
used ambient/default provider/model configuration; and the Pi task wrapper had
no actual provider/model/harness attestation. Campaign Engine remains
provider-free and has no live invocation adapter.

## 8. Existing Pi boundary before change

`PiInvocationEnvelope`, `PiInvocationPolicyDecision`,
`PiInvocationReceipt`, and `PiHarnessResult` already represented the needed
authority lineage, permissions, configured provider lane, harness identity,
and bounded result shapes. No contract meaning changed.

## 9. New Guardian invocation owner

`guardian/pi/invocation.py` provides `invoke_guardian_authorized_pi`. It has
no Campaign Engine, FastAPI, database, Redis, AgentStore, Coding Worker, or
queue dependency. It returns only a non-persisted bounded outcome to its
caller.

## 10. Authorization validation sequence

The entrypoint validates envelope and policy decision, validates their exact
cross-object relationship, requires `decision == allowed`, rejects
credential-named contract material, freezes explicit identity, captures target
and Git state, then calls the harness at most once. Preflight rejection makes
zero runner calls.

`GUARDIAN_AUTHORIZATION_BEFORE_EXECUTION: PASS`

## 11. Envelope/policy cross-object validation

`validate_policy_decision_against_envelope` requires exact invocation id,
source thread/message lineage, harness id, full Guardian boundary,
requested-permission set, and granted-permission set equality. It preserves
existing validation failures and adds canonical relationship mismatch failure
tokens. Deterministic tests cover each mismatch with zero runner calls.

## 12. Provider identity freeze

The validated envelope's non-empty provider name is frozen in a typed request
and passed only through the adapter's invocation-local subprocess environment.
Authorized wrapper mode does not use the legacy provider default.

`IMMUTABLE_PROVIDER_IDENTITY: PASS`

## 13. Model identity freeze

The validated envelope's non-empty model id is frozen identically. Authorized
wrapper mode passes it directly to Pi resolution and does not apply legacy
alias/default normalization.

`IMMUTABLE_MODEL_IDENTITY: PASS`

## 14. Harness identity freeze

The envelope's non-empty harness id and version are frozen with the same typed
request. Authorized wrapper mode compares both with the installed Pi package
identity before it creates a session.

`IMMUTABLE_HARNESS_IDENTITY: PASS`

## 15. Actual identity source

The opt-in `guardian-authorized-task` wrapper mode obtains provider and model
from the resolved Pi model object and harness version from installed Pi package
metadata. It returns them as `actual_runtime_identity`; the adapter parses
that structure separately from arbitrary model content and the wrapper returns
only bounded result metadata in this mode.

`ACTUAL_RUNTIME_IDENTITY_ATTESTATION: PASS`

## 16. Requested vs authorized vs actual equality rule

Requested/authorized provider, model, harness id, and harness version derive
from the validated envelope. Actual identity originates with the harness
response and must equal all four frozen fields. Missing attestation or any
mismatch fails closed after one call and returns no successful receipt/result.

`IDENTITY_MISMATCH_FAIL_CLOSED: PASS`

## 17. Filesystem mutation enforcement

Each `files.write` resource is resolved against target cwd before execution.
Empty roots, traversal, and roots outside target fail before a call. The rail
snapshots all target entries, including untracked content, before and after;
only the Git-internal directory is excluded from tree hashing. Changes outside
a granted root fail, as do changed symlinks that resolve outside the target.

`FILESYSTEM_SCOPE_ENFORCEMENT: PASS`

## 18. Git mutation enforcement

For a Git target, the rail records `HEAD` before and after execution. Any
advance is `git_mutation_violation`; the rail does not reset or repair the
fixture. A temporary repository test creates a commit and proves closure.

`NO_GIT_HISTORY_MUTATION: PASS`

## 19. Read-only enforcement

No `files.write` grant yields a read-only harness request. The existing wrapper
mechanism receives `PI_DISABLE_TOOLS=1`, disabling coding tools rather than
relying on prompt wording. Target state must remain equivalent; any mutation
is `read_only_violation`.

`READ_ONLY_ENFORCEMENT: PASS`

## 20. Receipt construction

Success constructs a completed `PiInvocationReceipt` with the original
Guardian boundary, invocation/source lineage, permissions, configured provider
lane, harness identity, and a bounded `pi://guardian-authorized/.../result`
artifact reference. It is validated against the envelope before return.

`RECEIPT_VALIDATION: PASS`

## 21. HarnessResult construction

The same success path constructs a success `PiHarnessResult` with attested
identity only after equality validation, inherited authorization lineage and
permissions, and a bounded artifact reference. It validates against receipt.

`HARNESS_RESULT_VALIDATION: PASS`

## 22. Zero-retry behavior

There is one execution site and no loop. Every terminal outcome reports
`retry_count=0`.

`AUTOMATIC_RETRY: 0`

## 23. Zero-fallback behavior

The primitive has no fallback provider/model/harness input or secondary runner
path. Every terminal outcome reports `fallback_count=0`.

`AUTOMATIC_FALLBACK: 0`

## 24. Legacy Coding Worker compatibility

Legacy `PiCodexRunnerAdapter.execute` and wrapper `task` behavior remain
separate from new `execute_authorized` and `guardian-authorized-task` paths.
Coding Worker source was not changed; its direct runtime-contract regression
passed.

## 25. Direct Codex fail-closed status

`guardian/agents/adapters/codex.py` was not changed. A focused test confirms
`CodexAdapter()` still raises the established unsupported error.

## 26. External provider-call count

`0`. All invocation tests used injected deterministic fake runners or mocked
subprocess execution. The wrapper was syntax-checked only; no provider,
credential store, API, subscription, MiniMax configuration, or live harness
was invoked.

`EXTERNAL_PROVIDER_CALLS: 0`

## 27. Credential exposure review

No credentials, tokens, headers, cookies, auth-file contents, or provider
request payloads were added to tracked files, tests, receipts, results, or this
proof. The runtime rejects credential-named envelope/policy metadata before a
harness call and its authorized wrapper output omits model response content.
The focused test proves a credential-like prompt string is absent from returned
receipt/result payloads. No repository secret scanner was available or claimed.

## 28. Focused tests

The requested tests passed without provider calls:

```text
PYTHONPATH="" .venv/bin/python -m pytest -v \
  tests/pi/test_pi_invocation_contracts.py \
  tests/pi/test_pi_live_invocation.py \
  tests/ops/test_worker_coding_pi_runtime_contract.py

47 passed in 1.07s
```

The new suite has 29 passing tests: pre-invocation zero-call failures; exact
frozen identity; actual provider/model/harness id/version mismatches;
read-only and scoped writes; traversal and symlink escape; commit detection;
no retry/fallback; contract validation; credential non-persistence; legacy
adapter compatibility; and direct Codex failure closure.

## 29. Campaign Engine regression

Campaign Engine was inspected but not changed. Its provider-free regression
suite passed:

```text
PYTHONPATH="" .venv/bin/python -m pytest -v \
  codex_runner/tests/test_campaign_engine_schemas.py \
  codex_runner/tests/test_campaign_engine_runtime.py

96 passed in 0.96s
```

`CAMPAIGN_ENGINE_MUTATION: NONE`

## 30. What this proves

The repository now has a deterministic Guardian-owned Pi invocation rail that
enforces authorization-before-invocation, explicit identity freeze, runtime
identity equality, filesystem/read-only/Git constraints, bounded receipt/result
construction, and zero retry/fallback behavior. Provider-free Campaign Engine
and Coding Worker contract surfaces remain regression-green.

## 31. What this does not prove

This does not prove a live provider execution, Codex-compatible subscription
binding, MiniMax configuration/evaluation, Campaign Engine consumption,
provider governance, cross-process sandbox completeness, queue/store behavior,
autonomous remediation, or a release-support expansion.

`MINIMAX_CONFIGURATION_CHANGE: NONE`

`LIVE_PROVIDER_PROOF: NOT_PERFORMED`

## 32. Final classification

`PASS` — all deterministic authority, identity, filesystem, Git, read-only,
receipt/result, compatibility, and provider-free regression requirements passed
without a real provider call.

## 33. Documentation follow-through

Added this focused proof receipt only. `docs/architecture/00-current-state.md`
and release/support documentation were intentionally unchanged because no
release claim was proven false or widened.

## 34. Exact next gate

Return to Axis. The next atomic task is:

> Qualify one Codex-compatible subscription-backed Executor binding through
> the new Guardian-authorized Pi invocation seam.

That task must prove one real Executor invocation in a disposable repository.
MiniMax configuration and qualification remain a separate subsequent gate.
