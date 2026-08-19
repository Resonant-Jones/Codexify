# Guardian Pi Authorized Readiness Canonicalization Proof — 2026-08-19

## Result

`PASS`

The historical redacted Pi adapter failure diagnostic / readiness rail
implemented by `87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e` is now
canonical on current `main`. The bounded failure vocabulary, the
backend-supplying `AuthStorage.create()` construction path in the
readiness rail, the redacted wrapper / adapter / Guardian propagation,
and the non-inference `guardian-authorized-readiness` semantics are all
preserved verbatim. No live provider request, OAuth operation, or Pi
package modification occurred.

## Source reconciliation

| Field | Value |
| --- | --- |
| Current `origin/main` | `15227e6f8e997f1d295a98d82cf73ac3a5ecbca8` |
| Historical implementation commit | `87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e` |
| Historical merge base with current `main` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Path-bounded drift result | **NO CURRENT-MAIN DRIFT** on any of the six implementation/test paths |
| Reconciliation method | **Exact transplant** via `git checkout 87535e90 -- <path>` |

The merge-base result confirms that `87535e90...` is **not** an ancestor of
current `origin/main`. The historical patch was authored on a branch that
diverged at `eb6bdc530...` and never merged. Main has not touched any of the
six implementation/test paths since `eb6bdc530...`. Diff between
`87535e90^` and `origin/main` is empty on all six paths.

| Path | Drift classification |
| --- | --- |
| `codex_runner/src/agent-wrapper.js` | `no-current-main-drift` |
| `guardian/agents/adapters/base.py` | `no-current-main-drift` |
| `guardian/agents/adapters/pi_codex_runner.py` | `no-current-main-drift` |
| `guardian/pi/invocation.py` | `no-current-main-drift` |
| `guardian/pi/tokens.py` | `no-current-main-drift` |
| `tests/pi/test_pi_authorized_failure_diagnostics.py` | `no-current-main-drift` (file did not exist on current `main`) |

Because all six paths had `no-current-main-drift`, the historical
implementation semantics were transplanted exactly. No manual
reconciliation was required. The only extension was the addition of
three new static-source regression tests in
`tests/pi/test_pi_authorized_failure_diagnostics.py` to enforce the
post-reconciliation invariant that the readiness rail does not
construct bare `new AuthStorage()` and uses
`AuthStorage.create()` / backend-supplying Pi API instead.

## Canonical implementation

Final path ownership after canonicalization:

| Concern | Path |
| --- | --- |
| Bounded failure tokens (`PiAuthorizedFailureClass`, `PI_AUTHORIZED_FAILURE_CLASSES`, `normalize_pi_authorized_failure_class`) | `guardian/pi/tokens.py` |
| Adapter propagation (bounded `failure_classification`, `failure_stage`, `runtime_identity_established`, `session_initialized`, `provider_request_started`, `oauth_available`, `return_code`) | `guardian/agents/adapters/base.py` |
| Wrapper / adapter failure classification (BoundedText helper, `_classify_authorized_failure`, `_failure_stage_for_class`) | `guardian/agents/adapters/pi_codex_runner.py` |
| Guardian propagation (`invoke_guardian_authorized_pi`, `preflight_guardian_authorized_pi`, `_run_preflight_with_pi_adapter`) | `guardian/pi/invocation.py` |
| Wrapper readiness mode (`checkGuardianAuthorizedReadiness`, `AUTHORIZED_FAILURE_CLASSES`) | `codex_runner/src/agent-wrapper.js` |
| Diagnostic + regression tests | `tests/pi/test_pi_authorized_failure_diagnostics.py` |

## AuthStorage construction result

The readiness path uses Pi's normal backend-supplying public construction
API:

```text
AuthStorage.create()
```

at three call sites in `codex_runner/src/agent-wrapper.js` (lines 221, 295,
363). The third call site (line 363) is the one exercised by the readiness
mode `checkGuardianAuthorizedReadiness`. The reconciliation proof isolated
the historical TypeError discriminant as a `new AuthStorage()` (no-args)
construction error at `auth-storage.js:203:26`; this canonicalization
preserves the correct construction path and the regression tests assert
that the misuse is not re-introduced.

- Bare `new AuthStorage()` does not appear anywhere in
  `codex_runner/src/agent-wrapper.js` or `guardian/pi/invocation.py`.
- `AuthStorage.create()` is the only AuthStorage construction pattern
  used in the readiness path.
- No Pi package was modified. No Pi source was patched.
- No `auth.json` was touched. No credential was mutated.

## Redaction result

Static + dynamic checks confirm:

- The wrapper / adapter never returns raw stderr, stdout, exception
  messages, exception stacks, request bodies, response bodies, headers,
  cookies, auth records, access tokens, refresh tokens, credential paths
  containing sensitive values, or environment dumps.
- Token-shaped stderr (`access_token=secret...`), Bearer-shaped stderr
  (`Authorization: Bearer secret...`), and cookie-shaped stderr
  (`Cookie: session=secret...`) are all suppressed by the bounded
  `failure_classification` path. The historical proof's
  `test_authorized_adapter_never_returns_raw_or_secret_shaped_stderr`
  exercises this end-to-end.
- Malformed JSON stderr containing a secret-shaped value is suppressed;
  `test_malformed_authorized_wrapper_json_is_protocol_failure` exercises
  this.
- The diagnostic / readiness output schema exposes only:
  `actual_provider_id`, `actual_model_id`, `actual_harness_id`,
  `actual_harness_version`, `failure_classification`, `failure_stage`,
  `runtime_identity_established`, `session_initialized`,
  `provider_request_started`, `oauth_available`, `return_code`.

## Readiness non-inference result

The `checkGuardianAuthorizedReadiness` body in
`codex_runner/src/agent-wrapper.js`:

1. Loads Pi SDK.
2. Validates the supplied Guardian identity.
3. Verifies the provider id is registered.
4. Verifies the model id is registered.
5. Verifies exact runtime identity (provider / model / harness / version).
6. Calls `AuthStorage.create()` and `modelRegistry.getAvailable()`.
7. Emits one of:
   - `status: "ok"`, `session_initialized: false`, `provider_request_started: false`, `oauth_available: true`, `runtime_identity_established: true`
   - or `failure_class: <bounded_class>`, `failure_stage: <bounded_stage>`, `runtime_identity_established: true | false`

It does **not**:

- call `session.prompt(...)`
- call `modelRegistry.create(...)` followed by inference
- create a durable session
- perform an HTTP request to a provider
- perform a token refresh
- retry
- fallback

The regression test
`test_readiness_wrapper_emits_session_initialized_false_and_no_provider_request`
statically asserts that the readiness body emits
`session_initialized: false`, `provider_request_started: false`,
`runtime_identity_established: true`, and `oauth_available: true`.

## Regression result

| Suite | Result |
| --- | --- |
| `tests/pi/test_pi_authorized_failure_diagnostics.py` | **27 / 27 PASS** (24 historical + 3 new regression) |
| `tests/pi/test_pi_live_invocation.py` | **30 / 30 PASS** (no regression) |
| `tests/pi/` (full suite) | **172 / 172 PASS** |
| `node --check codex_runner/src/agent-wrapper.js` | **PASS** |
| `git diff --check` | **PASS** |

The three new regression tests added in this canonicalization:

1. `test_readiness_wrapper_never_constructs_bare_auth_storage` — asserts
   the readiness body does not contain a bare `new AuthStorage()` call.
2. `test_readiness_wrapper_uses_backend_supplying_auth_storage` — asserts
   the readiness body calls `AuthStorage.create()`.
3. `test_readiness_wrapper_emits_session_initialized_false_and_no_provider_request`
   — asserts the readiness body emits the bounded schema
   (`session_initialized: false`, `provider_request_started: false`,
   `runtime_identity_established: true`, `oauth_available: true`).

The 24 historical diagnostic tests all continue to pass. They cover
(without re-running them here for proof):

- missing/invalid Guardian identity;
- runtime module unavailable;
- provider unresolved;
- model unresolved;
- runtime identity mismatch;
- OAuth/auth unavailable;
- wrapper unavailable;
- timeout;
- session initialization failure classification for authorized execution;
- provider request failure classification;
- provider transport failure classification;
- malformed wrapper protocol;
- actual identity missing;
- unknown failure normalization;
- raw exception suppression;
- token-shaped stderr suppression;
- Bearer-shaped stderr suppression;
- cookie-shaped stderr suppression;
- retry count remains zero;
- fallback count remains zero;
- readiness prompt is empty;
- readiness does not initialize a session;
- readiness does not start a provider request;
- successful authorized result regression remains intact;
- filesystem/Git posture remains authoritative over an adapter success
  claim where governed.

## Live activity ledger

| Count | Value |
| --- | --- |
| Provider inference requests | `0` |
| Model prompts | `0` |
| OAuth login attempts | `0` |
| OAuth refresh attempts | `0` |
| Credential mutations | `0` |
| Retries | `0` |
| Fallbacks | `0` |
| Automatic retries | `0` |
| Automatic fallbacks | `0` |

## Current non-claims

This proof does NOT establish:

- current OAuth token validity (the `oauth_available` boolean reports only
  storage presence, not validity, reachability, or entitlement);
- provider reachability;
- provider entitlement;
- successful OpenAI Codex Executor execution;
- release support;
- any successful adapter turn.

The reconciliation proof at `4acb7c5c7c23dc4913a90bba9b86b46bec0bc241`
established that the current `AuthStorage.create()` path can load the
stored `openai-codex` record structurally; it did **not** establish
token validity.

## Next gate

`NEXT_GATE: run a fresh non-mutating OpenAI Codex Executor preflight qualification proof`

That task must independently establish the operational health of the Pi
OAuth flow against the operator's existing `openai-codex` record, using
the canonical `guardian-authorized-readiness` rail canonicalized here.

## Documentation follow-through

Only this focused canonicalization proof was tracked. No change was
made to `docs/architecture/00-current-state.md`. No provider-support
document, release document, or ADR was modified. No historical proof
artifact was rewritten. The new proof supersedes only the question of
whether the diagnostic / readiness implementation is canonical source.

## ADR impact

`No ADR impact`

Aligned with existing ADR(s):

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract
- Guardian delegation contracts

The readiness rail improves bounded operator diagnostics and provides a
non-inference readiness seam inside already-accepted Guardian execution
authority. It does not create new execution authority. It does not change
provider routing. It does not change credentials. It does not change
persistence. It does not change release support.

No ADR was created or modified.

## Security ledger

| Count | Value |
| --- | --- |
| Provider inference requests | `0` |
| Model prompts | `0` |
| OAuth logins | `0` |
| OAuth refreshes | `0` |
| Credential mutations | `0` |
| Real package mutations | `0` |
| Credential-value outputs | `0` |
| Credential-file hashes emitted | `0` |
| Retries | `0` |
| Fallbacks | `0` |
