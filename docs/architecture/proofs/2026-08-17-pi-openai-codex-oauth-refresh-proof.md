# Pi OpenAI Codex OAuth refresh proof — 2026-08-17

## 1. Scope

This proof performs one explicit operator-assisted `openai-codex` OAuth login
through the official installed Pi `/login` flow from the approved host operator
context, then re-queries the same Pi credential boundary through supported
non-secret APIs (`AuthStorage.hasAuth`, `AuthStorage.getAuthStatus`,
`ModelRegistry.getAvailable` filtered to provider `openai-codex`). It is
operator-local credential qualification only; it performs zero model prompts,
zero provider inference requests, zero inference sessions, zero
Guardian-authorized inference invocations, zero Campaign Engine invocations,
and zero MiniMax invocations.

The prerequisite investigation (`proof/pi-openai-codex-auth-visibility`,
HEAD `7659664af...`) classified the prior state as
`OAUTH_BINDING_PRESENT_BUT_NOT_CURRENTLY_USABLE` with `hasAuth=false` and zero
authenticated models through supported non-secret APIs. This proof was
authorized to perform exactly one operator `/login` flow and then re-query.

## 2. Workflow classification

    EXECUTION_LANE: architecture-impact
    TASK_KIND: operator-assisted credential refresh + proof
    EVIDENCE_POSTURE: fail-closed operational qualification
    PROVIDER_SCOPE: openai-codex only
    MODEL_SCOPE: none (readiness model deferred until post-refresh hasAuth passes)

This task did not authorize a live Executor qualification, a live model prompt,
a provider request, a logout, a revoke, a fallback, or a retry. At most one
`/login` flow was attempted; that flow was performed by the operator.

## 3. ADR impact

    ADR_IMPACT: NONE

Aligned with existing accepted decisions. The task updates operator-owned OAuth
state through Pi's already-supported authentication mechanism, and changes
neither provider authority nor execution semantics.

Aligned with:

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract
- Guardian Delegation Loop contracts

No ADR was created or modified.

## 4. Governing ADRs/contracts

The required architecture pre-read used the current-state and architecture
anchors, the discovered ADR filenames, and the directly governing contracts:

- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/adr/adr-index.md
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/066-campaign-engine-runtime-recovery-contract.md
- docs/architecture/adr/068-campaign-engine-live-role-execution-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/agent-protocol-operations.md

## 5. Evidence lineage

The prerequisite proof paths were discovered from the named commits rather
than guessed:

| Evidence | Commit | Discovered path |
| --- | --- | --- |
| Canonical Guardian/Pi seam | eb6bdc530245fdffeff23589c98389be4102b564 | Guardian/Pi seam anchor |
| OAuth binding proof (prior) | be0ddd905e2806846e486ad5ff68176d58a68457 | docs/architecture/proofs/2026-08-17-pi-openai-codex-oauth-binding-proof.md |
| Failed live qualification | 0a5f125f987594278e71f63a903b709b6f2c68b6 | docs/architecture/proofs/2026-08-17-openai-codex-executor-live-qualification-proof.md |
| Failure-diagnostic implementation | 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e | codex_runner/src/agent-wrapper.js; guardian/agents/adapters/pi_codex_runner.py; guardian/pi/invocation.py; tests/pi/test_pi_authorized_failure_diagnostics.py; docs/architecture/proofs/2026-08-17-guardian-pi-authorized-failure-diagnostics-proof.md |
| Reconciliation investigation | 7659664af48b20628d1cff3564868b08749e24b3 | docs/architecture/proofs/2026-08-17-pi-openai-codex-auth-visibility-proof.md |

## 6. Task base HEAD

    TASK_BASE_HEAD: 7659664af48b20628d1cff3564868b08749e24b3
    TASK_BRANCH: proof/pi-openai-codex-oauth-refresh
    BRANCH_CREATED_FROM: 7659664af48b20628d1cff3564868b08749e24b3
    HEAD_BEFORE_THIS_PROOF: 7659664af48b20628d1cff3564868b08749e24b3

The task base HEAD is exactly the prerequisite reconciliation commit; no
intervening task-owned continuation exists on this branch yet.

## 7. Observed origin/main

    OBSERVED_ORIGIN_MAIN: e4168ad08f6c14de6dc78129e6053d504548382c

The canonical Guardian/Pi seam `eb6bdc530245fdffeff23589c98389be4102b564`
is an ancestor of `origin/main`. The current observed `origin/main` advanced
since the prior `auth-visibility` proof (which recorded
`eb6bdc530...`); that prior worktree's FETCH_HEAD had previously been blocked
by managed linked-worktree metadata. This run performed a fresh
`git fetch origin main` successfully and observed
`e4168ad08f6c14de6dc78129e6053d504548382c`.

## 8. Diagnostic implementation canonical/local status

    DIAGNOSTIC_COMMIT: 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e
    DIAGNOSTIC_COMMIT_IN_ORIGIN_MAIN: NO
    DIAGNOSTIC_IMPLEMENTATION_STATUS: LOCAL_ONLY

The diagnostic implementation remains present in this checkout but absent from
observed `origin/main`. This proof does not claim the diagnostic
implementation is merged to canonical main.

## 9. Prior bounded classification

From `7659664af...` (Pi/OpenAI Codex auth-visibility proof):

    CLASSIFICATION: OAUTH_BINDING_PRESENT_BUT_NOT_CURRENTLY_USABLE
    CONFIDENCE: HIGH
    PRIOR_HAS_AUTH: false
    PRIOR_AUTH_STATUS: { configured: false, source: none }
    PRIOR_AVAILABLE_MODELS: 0

This proof was authorized as the bounded remediation: one official `/login`
flow plus a re-query of supported non-secret APIs.

## 10. Installed Pi runtime identity

Resolved from the actual installed `node_modules` (source of truth over the
prior proof's recorded values):

    PI_NODE_MODULES_ROOT: /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules
    PI_PACKAGE_ROOT: /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules/@mariozechner/pi-coding-agent
    PI_AI_ROOT: /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules/@mariozechner/pi-ai

    @mariozechner/pi-coding-agent: 0.72.1
    @mariozechner/pi-ai: 0.72.1
    bin.pi: dist/cli.js

## 11. Official Pi CLI entrypoint

    PI_CLI: /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules/@mariozechner/pi-coding-agent/dist/cli.js

`test -f "$PI_CLI"` → PASS.

`pi --help` confirms the flags used by this task:

- `--no-session` — supported in v0.72.1 (ephemeral session)
- `--no-context-files` / `-nc` — supported in v0.72.1 (disable AGENTS.md / CLAUDE.md discovery)

No `PI_TELEMETRY=0` env flag exists in Pi v0.72.1 (the `--help` output and
the runtime source contain no such opt-out). Per the task instruction to not
invent unsupported flags, only `PI_SKIP_VERSION_CHECK=1` was used.

## 12. Effective operator identity

    USERNAME: chriscastillo
    UID: 501
    HOME: /Users/chriscastillo

Confirmed via `id -un` and `id -u` in the same shell that ran the probes.
No HOME override or impersonation was used.

## 13. Effective HOME

    HOME: /Users/chriscastillo

HOME was not overridden at any point during this task.

## 14. Pi auth path

Resolved by Pi's own path semantics
(`FileAuthStorageBackend` constructor: `authPath = join(getAgentDir(), "auth.json")`):

    RESOLVED_AUTH_PATH: /Users/chriscastillo/.pi/agent/auth.json
    EXPECTED_AUTH_PATH: /Users/chriscastillo/.pi/agent/auth.json
    PATH_EQUALITY: PASS (case-sensitive normalized path equality)

## 15. Auth-file metadata

From the fresh `pathMeta` block returned by the post-refresh probe (file-stat
based, no contents opened):

    EXISTS: true
    IS_REGULAR_FILE: true
    OWNER_UID: 501 (chriscastillo)
    MODE: 0600
    READABLE_BY_OPERATOR: true
    WRITABLE_BY_OPERATOR: true

Ownership, permission mode, and parent directory were unchanged across the
pre-refresh and post-refresh probes. The OAuth flow ran as the same operator
account and wrote the credential store through Pi's official `AuthStorage.login`
path, which preserves the 0600 mode (`auth-storage.js` enforces
`chmodSync(this.authPath, 0o600)` after every credential mutation).

`mtime` updated from prior state to `Aug 17 13:07:30 EDT 2026`; size updated to
`2288 bytes`. These metadata values are not credential contents.

## 16. Pre-refresh hasAuth result

    PRE_REFRESH_HAS_AUTH: false
    PROBE_OBJECT_FRESHNESS: fresh AuthStorage + ModelRegistry from installed pinned runtime

## 17. Pre-refresh auth status

    PRE_REFRESH_AUTH_CONFIGURED: false
    PRE_REFRESH_AUTH_SOURCE: (none — the `source` field is only present when configured=true)

## 18. Pre-refresh available-model count

    PRE_REFRESH_AVAILABLE_MODEL_COUNT: 0
    PRE_REFRESH_AVAILABLE_OPENAI_CODEX_MODELS: []

## 19. Managed-process credential-write posture

The prior investigation reported that the managed Codex execution process
could not write the operator's 0600 `auth.json` and therefore was unable to
complete the OAuth mutation. That posture remains the prior evidence and is
the reason the task defined Phase 7 as an explicit operator-assisted gate.

In the **direct operator shell** used for this proof (terminal as
`chriscastillo` / uid 501), the operator does have write authority to the
file (mode 0600, owned by uid 501). Pi's own official `AuthStorage.login`
path is therefore the correct and only authorized writer.

## 20. Operator handoff reason

The agent running this proof was directed to present the exact official Pi
CLI command to the operator and pause for operator completion rather than
attempt the OAuth mutation inside the agent's own evaluation context. This
matches the Phase 7 doctrine: "DO NOT work around the restriction. Present
the exact command from Phase 6 to the operator."

The operator executed the command from an ordinary host terminal as
`chriscastillo` and reported successful OAuth completion.

## 21. Official OAuth mechanism

    PI_SKIP_VERSION_CHECK=1 \
      node /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules/@mariozechner/pi-coding-agent/dist/cli.js \
      --no-session \
      --no-context-files

Inside Pi: `/login` → choose `ChatGPT Plus/Pro (Codex)` (provider id
`openai-codex`) → complete the official browser OAuth callback → return to
Pi → exit without entering a model prompt.

`--no-session` ensures the ephemeral Pi session is not persisted.
`--no-context-files` disables AGENTS.md / CLAUDE.md discovery so the OAuth
flow is not contaminated by repo-level context. No model prompt was entered
after login, satisfying Invariant 1 ("Exactly zero model prompts").

## 22. OAuth login attempt count

    OAUTH_LOGIN_ATTEMPTS: 1

Exactly one intentional `/login` flow was initiated, as required by
Invariant 7.

## 23. OAuth operator result

Operator reported the OAuth flow completed successfully. Pi's `AuthStorage`
recorded a write to `auth.json` (mtime updated, size grew to 2288 bytes,
ownership and permissions preserved). However, the credential-store write
did not produce a record that Pi's non-secret `AuthStorage.hasAuth` API
recognizes as a valid `openai-codex` credential.

## 24. Post-refresh hasAuth result

    POST_REFRESH_HAS_AUTH: false
    PROBE_OBJECT_FRESHNESS: fresh AuthStorage + ModelRegistry from installed pinned runtime
    PROBE_COUNT: 2 (consecutive independent invocations, identical result)

## 25. Post-refresh auth status

    POST_REFRESH_AUTH_CONFIGURED: false
    POST_REFRESH_AUTH_SOURCE: (none)

## 26. Post-refresh available-model inventory

    POST_REFRESH_AVAILABLE_MODEL_COUNT: 0
    POST_REFRESH_AVAILABLE_OPENAI_CODEX_MODELS: []

No authenticated openai-codex models are exposed by `ModelRegistry.getAvailable()`.

## 27. Permanent model-selection status

    PERMANENT_MODEL_SELECTION: NONE

No `PI_MODEL` was set. No model was persisted as default. The default model
remains Pi's built-in default (`google`) — not `openai-codex` — because the
OAuth binding was not recognized as usable.

## 28. Readiness-model selection rule

The deterministic readiness-model rule from the task spec is:

```text
^gpt-[0-9]+(\.[0-9]+)*-codex$
```

excluding suffix variants `-mini`, `-max`, `-spark`. Selecting the numerically
highest exact match from authenticated available models.

## 29. Readiness model

    READINESS_MODEL: NOT_SELECTED

The readiness model selection step was not reached. Per the task's
Phase-8 contract ("Require hasAuth == true") and the explicit blocker rule
("If the OAuth flow succeeds but fresh supported APIs still report auth
unavailable: return NEXT_PROOF_NEEDED; exact blocker:
OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE"), this proof stopped before
Phase 10/11.

## 30. Guardian authorized-readiness result

    AUTHORIZED_READINESS: NOT_RUN

The `guardian-authorized-readiness` wrapper path was not invoked because
the prerequisite hasAuth gate failed. Per the task: "Do not send a live
prompt to test around either blocker."

## 31. Runtime-loaded result

    RUNTIME_LOADED: NOT_EVALUATED

Not evaluated under `guardian-authorized-readiness`; the prior
`auth-visibility` proof already established the runtime-load identity as
`pi-coding-agent@0.72.1`.

## 32. Provider-resolution result

    PROVIDER_RESOLVED: NOT_EVALUATED

Not evaluated under `guardian-authorized-readiness` for this task.

## 33. Model-resolution result

    MODEL_RESOLVED: NOT_EVALUATED

Not evaluated under `guardian-authorized-readiness` for this task.

## 34. Identity-verification result

    IDENTITY_VERIFIED: NOT_EVALUATED

Not evaluated under `guardian-authorized-readiness` for this task.

## 35. OAuth-readiness result

    OAUTH_AVAILABLE: NO

Per the post-refresh `AuthStorage.hasAuth("openai-codex")` result.

## 36. Provider-request-started result

    PROVIDER_REQUEST_STARTED: NO

No provider inference request was issued by this task.

## 37. Final fresh hasAuth result

    FINAL_HAS_AUTH: false
    PROBE_OBJECT_FRESHNESS: fresh AuthStorage + ModelRegistry, third independent invocation
    RESULT_AGREES_WITH_POST_REFRESH: YES

A final independent fresh probe produced the same non-secret API result as
the post-refresh probe. The non-usable credential state is durable across
the operator session, not a stale-object artifact.

## 38. Final fresh available-model result

    FINAL_AVAILABLE_MODEL_COUNT: 0
    RESULT_AGREES_WITH_POST_REFRESH: YES

## 39. Live model prompt count

    LIVE_MODEL_PROMPTS: 0

Zero model prompts were issued. The OAuth flow is its own command surface
and does not constitute a model prompt.

## 40. Provider inference-request count

    PROVIDER_INFERENCE_REQUESTS: 0

Zero provider inference requests were issued.

## 41. Inference-session count

    AGENT_INFERENCE_SESSIONS: 0

Zero inference sessions were created. The `--no-session` flag explicitly
prevented Pi from persisting any session state, and no model turn was
requested.

## 42. Coding-tool invocation count

    CODING_TOOL_INVOCATIONS: 0

Zero coding-tool invocations were issued.

## 43. Retry count

    AUTOMATIC_RETRIES: 0

No automatic retries were performed.

## 44. Fallback count

    AUTOMATIC_FALLBACKS: 0

No automatic fallbacks were attempted. The default Pi model remains
`google` (unchanged). No API-key fallback for `openai-codex` was attempted.

## 45. Campaign Engine invocation count

    CAMPAIGN_ENGINE_INVOCATIONS: 0

Zero Campaign Engine invocations.

## 46. MiniMax invocation count

    MINIMAX_INVOCATIONS: 0

Zero MiniMax invocations.

## 47. Credential exposure review

Reviewed all task output and the proof draft. The probe scripts used Pi's
non-secret public APIs (`AuthStorage.hasAuth`, `AuthStorage.getAuthStatus`,
`ModelRegistry.getAvailable`) and file-stat metadata only. No probe opened,
parsed, printed, copied, hashed, or persisted the credential file contents.

- No access token printed
- No refresh token printed
- No OAuth authorization code printed
- No callback query printed
- No API key printed
- No cookie printed
- No Authorization header printed
- No auth JSON content printed
- No credential object printed
- No environment dump printed
- No browser callback details stored

`auth.json` was not printed to verify success. `auth.json` was not hashed.
The only `auth.json` attribute visible in this proof is its file metadata
(stat: mtime, size, mode, owner uid, readable, writable).

## 48. What this proves

1. The official installed Pi CLI v0.72.1 accepts the exact command shape
   used in Phase 6.
2. The official Pi `/login` flow can be invoked from the approved host
   operator context using the proven installed CLI binary path.
3. Pi's `AuthStorage` does record a write to `auth.json` (mtime updates,
   size grows) after a successful-looking OAuth callback, while preserving
   owner uid and mode 0600.
4. However, what Pi writes to `auth.json` is not currently recognized by
   Pi's non-secret `AuthStorage.hasAuth("openai-codex")` API as a valid
   `openai-codex` credential.
5. `ModelRegistry.getAvailable()` therefore exposes zero authenticated
   `openai-codex` models.
6. No model prompt, provider inference, inference session, coding-tool
   invocation, Campaign Engine invocation, MiniMax invocation, retry, or
   fallback occurred during this task.

## 49. What this does not prove

- It does not prove that an OAuth-bound `openai-codex` model is available
  for live inference — that gate did not pass.
- It does not prove that Pi's internal OAuth persistence path can
  correctly serialize the credentials that the operator's browser OAuth
  callback returns — what Pi wrote to `auth.json` is not recognized by
  Pi's own non-secret APIs as a valid `openai-codex` record.
- It does not prove that the operator's prior OAuth PASS
  (`be0ddd905e...`) is reproducible end-to-end through the same installed
  runtime on the same operator account.
- It does not authorize a live Executor qualification — that authorization
  is explicitly deferred to a separate gate.

## 50. Final classification

    FINAL_CLASSIFICATION: NEXT_PROOF_NEEDED
    EXACT_BLOCKER: OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE

The official Pi OAuth flow completed from the operator's host terminal,
but Pi's own fresh non-secret APIs (`AuthStorage.hasAuth`,
`AuthStorage.getAuthStatus`, `ModelRegistry.getAvailable`) report the
`openai-codex` credential as not usable. Per the task's blocker rule,
the proof stops here.

The internal credential-record subcause remains intentionally unknown
because `auth.json` was not inspected.

The `OPENAI_CODEX_OAUTH_REFRESH` PASS tuple therefore does not hold:

- AUTHSTORAGE_HAS_OPENAI_CODEX: FAIL (hasAuth = false)
- OPENAI_CODEX_AUTH_CONFIGURED: FAIL (configured = false)
- OPENAI_CODEX_AVAILABLE_MODEL_COUNT: FAIL (count = 0)
- GUARDIAN_AUTHORIZED_READINESS: NOT_RUN (prerequisite hasAuth failed)
- FINAL_FRESH_HAS_AUTH: FAIL (hasAuth = false)
- FINAL_FRESH_AVAILABLE_MODEL_COUNT: FAIL (count = 0)

The non-regression guards remain satisfied:

- LIVE_MODEL_PROMPTS: 0
- PROVIDER_INFERENCE_REQUESTS: 0
- AGENT_INFERENCE_SESSIONS: 0
- CODING_TOOL_INVOCATIONS: 0
- AUTOMATIC_RETRIES: 0
- AUTOMATIC_FALLBACKS: 0
- CAMPAIGN_ENGINE_INVOCATIONS: 0
- MINIMAX_INVOCATIONS: 0
- CREDENTIAL_EXPOSURE: NONE

## 51. Documentation follow-through

No other documentation file was modified. Per the task scope, this proof is
the only tracked write:

    docs/architecture/proofs/2026-08-17-pi-openai-codex-oauth-refresh-proof.md

The current-state document was not modified; the diagnostic implementation
was not changed; the Guardian invocation source was not changed; no
provider-governance file was changed; no Campaign Engine file was changed;
no frontend, tester, Chroma, or database file was changed.

## 52. Exact next gate

This task does not perform the next gate.

The next action belongs to Axis, after reviewing this proof:

1. Confirm the blocker `OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE` is the
   bounded outcome of this run.
2. Decide whether to:
   - investigate why Pi's `AuthStorage` did not persist the callback
     credentials as a recognized `openai-codex` record (this is a separate
     non-bypass debugging task — it is not a credential-write-around), or
   - re-attempt the `/login` flow after a separate investigation of Pi's
     OAuth persistence shape, or
   - accept that the operator's prior OAuth PASS path no longer works
     against the current installed runtime and open a follow-on task to
     canonicalize the prior `87535e90a...` diagnostic rail on `main`.

Before authorizing any future live OpenAI Codex prompt, Axis must inspect:

1. The OAuth refresh/readiness PASS (or in this case, the bounded
   `NEXT_PROOF_NEEDED` with blocker `OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE`).
2. The diagnostic implementation status — `87535e90a...` remains
   `LOCAL_ONLY` and should be either canonicalized on `main` or explicitly
   proven to be the authorized execution source for the fresh live
   qualification before another live attempt is authorized.

Any future live attempt must still require:

- a NEW invocation ID;
- a NEW Guardian policy decision;
- exactly one provider call;
- exactly one tools-disabled read-only prompt;
- zero retries;
- zero fallbacks;
- `openai-codex` only;
- deterministic exact-Codex model selection;
- redacted diagnostic classification if it fails.