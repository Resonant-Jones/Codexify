# Accepted chat dispatch prerequisite proof

Status: isolated PostgreSQL prerequisite proof; ADR-112 dispatcher remains
unimplemented and Private Preview invocation remains quarantined. No provider,
credential, deployment or release permission changes.

## Isolated authority-fence implementation follow-through

`guardian/command_bus/accepted_knowledge_read.py` now implements the reusable
revalidation component. It remains **unwired**: no chat admission, public invoke
contract, Command Bus orchestration, provider adapter or activation flag changed.
It is not a public capability or a second execution/audit owner.

Preparation freezes exact canonical arguments and task evidence after resolving
persisted acceptance. Every boundary method re-resolves original/current owner,
attempt acceptance/terminal/cancellation/deadline state, current OAuth generation,
expiry and selected GitHub repository. Metadata-only `oauth_store.read_grant`
does not decrypt tokens. Credential resolution is just in time, bracketed by
revalidation, with no legacy/ambient fallback or automatic provider refresh.
Refresh claims, reconnects, completed refreshes and repository reselection fence
the old context. Expired authority fails closed and requires separately governed
refresh before preparing a new attempt.

Replay validation requires matching subject, command, argument hash and a
server-derived key containing exact accepted lineage and connection generation.
Changing a connection cannot replay old connection evidence. Returned arguments
are detached copies; caller mutation cannot change the frozen read. The lineage
projection is secret-free input for existing Command Bus events, **not proof that
events have been persisted**. The remaining-time helper takes the tighter bound
of the accepted wall/monotonic deadline and credential expiry; it does not itself
start a timer or stop network I/O.

New real PostgreSQL negative tests cover before-replay/pre-I/O/post-I/O-check
refusal, disconnect during credential lookup, refresh claim, reconnect,
repository reselection/removal, expired grant, cancellation/terminal state,
cross-account replay, detached arguments, monotonic exhaustion and pending
acceptance. The selected real-database suite passed **87 tests, no skips**.
Always-on unit tests cover all four command forms and safe bounded refusals.
The first run found stale OAuth rows in the synthetic fixture because tombstones
deliberately have no user foreign key; the disposable reset now explicitly clears
both OAuth tables. The failed receipt is retained, and the corrected suite passes.

Remaining wiring is mandatory: enforce this fence at both ordinary and
idempotency-conflict replay returns, before each provider request and before
publishing results; retain Command Bus manifest/policy/permission/run/event gates;
implement native cancellable bounded transport and Notion multi-request traversal.
No arbitrary executor callback or operator-key impersonation is introduced here.
Synchronous database checks and the existing blocking provider clients do not
prove physical deadline/cancellation behavior. A revocation racing an already
sent request cannot retract it; transport must cancel when observed, start no
subsequent request, and discard results if post-I/O revalidation fails. That race
and end-to-end policy/audit lineage remain unproven. No architecture decision is
superseded, and this component is not sufficient to activate reads.

## Scope and ownership

This continues the existing connector task. Accessible native task/worktree
inventory identified that task as the active connector runtime owner; the
separate `docs/trusted-worker-account-binding-20261113` worktree was clean at
`7815f7735`. It contains the accepted ADR, not a second dispatcher implementation.
No other worker was messaged, interrupted or duplicated.

Proof base: serving candidate `2f0278d424e466063138079bef62037ebb04e476`.
The proof-only worktree keeps that candidate and its exact-head CI independent.
The installed application code is unchanged by this proof.

## Real database evidence

`tests/connections/test_accepted_chat_custody_postgres.py` adds 15 opt-in tests
against a fully migrated disposable PostgreSQL database. Its database guard
requires the dedicated `dispatch_proof` name, a private synthetic Unix socket,
and no TCP listener before any schema reset. No ambient application DSN is used.
Provider HTTP is explicitly refused in the fixture. Synthetic credentials and
an inert test encryption key are confined to the disposable database/process.

The tests exercise the real acceptance-row writer, frozen command/argument
checkpoint and custody resolver, alongside real OAuth storage. They prove:

- Exact Notion/GitHub command and argument-hash binding resolves the original
  accepted account; altered command/hash values fail closed.
- Publication before acknowledgement yields acceptance-pending, then a fresh
  lookup succeeds only after acceptance is recorded.
- Changed task owner, canonical thread/Project owner, terminal state,
  cancellation or Preview membership denies a later lookup despite a prior
  successful binding.
- Legacy/expired work is refused and the database rejects original-account
  reassignment.
- Parallel and sequential A/B lookups retain separate canonical account context.
- Disconnect removes connection credential availability while the same valid
  chat custody can still resolve. This is intentional evidence that custody
  and connector permission are independent authorities, not a dispatch grant.

The fresh-schema/predecessor rehearsal reached `d8a90bf32107`, preserved seeded
legacy rows and NULL custody, verified 145 tables, and rejected six forbidden
custody changes. The new tests plus existing custody, local knowledge execution
and Preview-admission tests passed **60/60**, without skips, on PostgreSQL 16.15
and Python 3.12.13. The synthetic cluster had no TCP listener and was stopped
and removed. The selected test source tree was
`3921713c17c67d8b85fe42adb06553a566dfd5d6` before this documentation-only addition.

Reproduce using a newly created disposable database and explicit
`CODEXIFY_DISPATCH_TEST_DATABASE_URL=postgresql+psycopg://<synthetic-user>@/dispatch_proof?host=/tmp/codexify-oauth-pg.<unique>/socket&port=<test-port>`,
with dotenv disabled. Run the new module together with
`tests/core/test_chat_account_custody.py`,
`tests/core/test_knowledge_tool_execution.py` and
`tests/connections/test_preview_oauth_admission.py`.
Task-local runnable harness and receipts are retained in
`dispatch-proof-20261117/` in the existing connector task workspace.

## Explicit limits and next implementation seam

The synthetic acceptance scope stands for an already authenticated route
principal. These tests do not prove HTTP authentication, real queue admission,
provider I/O, physical timeout/cancellation, Command Bus run/event lineage,
idempotent dispatch, or restored live-backup recovery. They add no dispatcher.

Source inspection confirms these required follow-through points:

1. `execute_invoke` returns matching idempotent runs before policy evaluation.
   The future trusted entry point must re-resolve accepted work and current
   connector authority before replay as well as before a new provider attempt.
   Do not change general public readback semantics merely to implement this
   private execution boundary.
2. Ordinary OpenAPI-backed provider commands still execute through the loopback
   HTTP adapter. Supplying `auth_subject` to Command Bus does not authenticate
   an account to that HTTP route. Preserve manifest/policy/permission/run/event
   processing while adding only the four accepted knowledge-read operations to
   an explicit server-owned in-process path. No arbitrary executor callback,
   client-controlled authority object or operator-key account impersonation.
3. Provider credential wrappers currently return token/repository values and
   clients retain those values for requests. The future invocation must carry
   current generation/resource authority to the actual I/O boundary, recheck
   after refresh/disconnect/reselection, and create no cross-account cached
   client. OAuth stale-write fencing alone is not read-execution fencing.
4. Provider clients use synchronous requests and fixed timeouts; Notion reads
   may make multiple requests. Removing loopback transport must preserve the
   accepted deadline, cancellation and network/egress checks rather than drop
   the adapter's existing enforcement. A timeout of an awaiting wrapper alone
   is not proof that a blocking provider request stopped.
5. Complete the ADR-112 A/B, retry, duplicate, revocation-race, lineage and
   policy-denial matrix with stub providers before any real consent/read canary.
   Imported-history exposure remains excluded. Existing public operations and
   knowledge chat admission remain quarantined until full proof and rollout.

The accepted in-process topology does not require another architectural
reconfirmation. The implementation seam and its proofs are engineering work;
provider grants, secret custody, operational rollout and diagnostic suppression
tradeoffs remain operator-owned decisions. No governing ADR is superseded.
