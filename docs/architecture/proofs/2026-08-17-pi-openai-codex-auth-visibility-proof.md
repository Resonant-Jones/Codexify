# Pi OpenAI Codex OAuth credential visibility proof — 2026-08-17

## 1. Scope

This proof reconciles the earlier Pi-managed openai-codex OAuth availability
result with the current Guardian-authorized, provider-prompt-free diagnostic
result. It is a read-only runtime-boundary investigation. It records only
non-secret process identity, runtime-root, path, file-metadata, and supported
Pi readiness observations.

No raw auth-file content was opened by the investigation. The Pi
AuthStorage API necessarily loaded its configured store internally; the
investigation did not inspect, parse, print, copy, hash, or persist any
credential material.

No source, configuration, test, provider, environment, ownership, permission,
or credential state was changed by this task. The only authorized tracked
write is this proof artifact.

## 2. Workflow classification

    EXECUTION_LANE: architecture-impact
    TASK_KIND: investigation + proof
    EVIDENCE_POSTURE: fail-closed runtime-boundary reconciliation
    PROVIDER_SCOPE: openai-codex only
    MODEL_SCOPE: gpt-5.3-codex only for diagnostic identity checks

This task did not authorize a live Executor qualification, a model prompt, a
provider request, a login, a refresh, a logout, a revoke, a fallback, or a
retry.

## 3. ADR impact

    ADR_IMPACT: NONE

The proof establishes operator-local credential visibility truth. It does not
change credential ownership, provider authority, execution authority,
persistence semantics, or release support.

The result is aligned with the existing Guardian-mediated execution,
runtime-recovery, and live-role contracts. No ADR was created or modified.

## 4. Governing contracts

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

The governing boundary remains Guardian-owned authorization and identity
verification. Pi owns local provider/auth readiness. A readiness result is
not a live execution result, and an unavailable readiness result is not
permission to repair credentials inside the Executor path.

## 5. Evidence lineage

The prerequisite proof paths were discovered from the named commits rather
than guessed:

| Evidence | Commit | Discovered path or result |
| --- | --- | --- |
| Canonical Guardian/Pi seam | eb6bdc530245fdffeff23589c98389be4102b564 | Guardian/Pi seam anchor; observed origin/main equals this commit |
| Pi runtime/materialization proof | 954ada259ccef247002c6df12f73f4948d93bf1d | docs/architecture/proofs/2026-08-17-pi-codex-subscription-executor-binding-proof.md |
| OAuth binding proof | be0ddd905e2806846e486ad5ff68176d58a68457 | docs/architecture/proofs/2026-08-17-pi-openai-codex-oauth-binding-proof.md |
| Failed live qualification | 0a5f125f987594278e71f63a903b709b6f2c68b6 | docs/architecture/proofs/2026-08-17-openai-codex-executor-live-qualification-proof.md |
| Failure-diagnostic implementation | 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e | codex_runner/src/agent-wrapper.js; guardian/agents/adapters/pi_codex_runner.py; guardian/pi/invocation.py; tests/pi/test_pi_authorized_failure_diagnostics.py; proof artifact |

The current observed upstream ref is:

    OBSERVED_ORIGIN_MAIN: eb6bdc530245fdffeff23589c98389be4102b564

The canonical Guardian seam is an ancestor of the task HEAD. A prior linked
worktree operation recorded that managed Git metadata prevented writing the
shared FETCH_HEAD; this task did not repeatedly retry that operation. The
existing observed origin/main ref was used for the ancestry gate.

## 6. Diagnostic implementation canonical/local status

    TASK_BASE_HEAD: 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e
    TASK_BRANCH: proof/pi-openai-codex-auth-visibility
    DIAGNOSTIC_COMMIT_IN_HEAD: YES
    DIAGNOSTIC_COMMIT_IN_ORIGIN_MAIN: NO
    DIAGNOSTIC_IMPLEMENTATION_STATUS: LOCAL_ONLY

The diagnostic implementation is present in the checkout used for this
investigation, but the observed canonical origin/main ref remains at
eb6bdc530245fdffeff23589c98389be4102b564. This proof does not claim that the
diagnostic implementation is merged into canonical main.

## 7. Prior OAuth PASS

The prior OAuth proof at commit
be0ddd905e2806846e486ad5ff68176d58a68457 recorded:

    PROVIDER: openai-codex
    AUTH_MECHANISM: OAuth subscription
    OFFICIAL_PI_LOGIN_ATTEMPTS: 1
    AUTHSTORAGE_HAS_OPENAI_CODEX: true
    AUTH_SOURCE: stored
    AUTHENTICATED_OPENAI_CODEX_MODEL_COUNT: 10
    MODEL_INCLUDING_CURRENT_CANDIDATE: gpt-5.3-codex
    MODEL_PROMPTS: 0
    PROVIDER_INFERENCE_REQUESTS: 0
    GUARDIAN_LIVE_INVOCATIONS: 0

The prior proof states that no deliberate logout or revocation followed that
proof. It also states that the prior proof stopped before Guardian
authorization and live model execution.

The prior OAuth proof did not record its effective username, UID, HOME,
working directory, computed Pi config root, resolved auth path, or auth-file
metadata. Those historical values are therefore not invented here. The
current comparison distinguishes the historical proof result from the
faithful current reconstruction of the materialization worktree it recorded.

## 8. Current preflight OAuth failure

The current diagnostic wrapper was run once in its non-inference readiness
mode with the already materialized Pi runtime and the exact authorized
identity:

    PI_PROVIDER: openai-codex
    PI_MODEL: gpt-5.3-codex
    PI_GUARDIAN_AUTHORIZED: 1
    PI_GUARDIAN_HARNESS_ID: pi-coding-agent
    PI_GUARDIAN_HARNESS_VERSION: 0.72.1
    PI_DISABLE_TOOLS: 1

The bounded result was:

    status: error
    failure_class: oauth_auth_unavailable
    failure_stage: oauth_readiness
    actual_provider_id: openai-codex
    actual_model_id: gpt-5.3-codex
    actual_harness_id: pi-coding-agent
    actual_harness_version: 0.72.1
    runtime_identity_established: true
    session_initialized: false
    provider_request_started: false

The wrapper reached the exact runtime identity and stopped at local OAuth
readiness. It did not call session.prompt, create an inference session, or
contact the provider.

## 9. OAuth-proof execution context

The prior materialization proof identifies the runtime worktree as:

    /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization

The OAuth proof states that it reused that existing ignored Pi materialization
and records the normalized package-root shape. Its historical process identity
fields were not persisted in the proof, so the historical OAuth process is
marked as not directly recorded rather than reconstructed by assertion.

A fresh, non-secret reconstruction was executed from the recorded
materialization worktree using the same installed runtime:

    RECONSTRUCTED_OAUTH_CONTEXT_CWD: /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization
    RECONSTRUCTED_OAUTH_CONTEXT_USER: chriscastillo
    RECONSTRUCTED_OAUTH_CONTEXT_UID: 501
    RECONSTRUCTED_OAUTH_CONTEXT_HOME: /Users/chriscastillo
    RECONSTRUCTED_OAUTH_CONTEXT_OS_HOMEDIR: /Users/chriscastillo

The reconstruction is current evidence about what that context resolves now;
it is not a claim that the omitted historical HOME/UID fields were recorded
at the time of the original OAuth proof.

## 10. Diagnostic execution context

The current diagnostic context was the linked checkout used for this task:

    DIAGNOSTIC_CONTEXT_CWD: /Users/chriscastillo/.codex/worktrees/aaba/Codexify-main
    DIAGNOSTIC_CONTEXT_USER: chriscastillo
    DIAGNOSTIC_CONTEXT_UID: 501
    DIAGNOSTIC_CONTEXT_HOME: /Users/chriscastillo
    DIAGNOSTIC_CONTEXT_OS_HOMEDIR: /Users/chriscastillo

The Guardian Pi adapter copies the parent environment into the child
subprocess and adds only the authorized provider/model/harness/read-only
identity fields. The wrapper resolves the explicitly materialized package
roots from PI_CODING_AGENT_PACKAGE_ROOT and PI_CODING_AGENT_NODE_MODULES.
Neither the adapter invocation nor the diagnostic command set a different
Pi auth directory or XDG config root.

## 11. Effective user/uid comparison

| Field | OAuth-proof current reconstruction | Diagnostic context | Result |
| --- | --- | --- | --- |
| OS username | chriscastillo | chriscastillo | SAME |
| UID | 501 | 501 | SAME |
| HOME | /Users/chriscastillo | /Users/chriscastillo | SAME |
| os.homedir() | /Users/chriscastillo | /Users/chriscastillo | SAME |

The original OAuth proof did not persist these fields. The table therefore
proves the two current contexts used for reconciliation, not an unrecorded
historical process identity.

## 12. Effective HOME comparison

    OAUTH_RECONSTRUCTED_HOME: /Users/chriscastillo
    DIAGNOSTIC_HOME: /Users/chriscastillo
    HOME_MISMATCH: NO
    PI_CODING_AGENT_DIR: UNSET in both current contexts
    XDG_CONFIG_HOME: UNSET in both current contexts

The resolved Pi config root is the same in both contexts. No HOME override,
XDG override, or explicit Pi config-directory override was introduced to make
the contexts agree.

## 13. Pi runtime-root comparison

Both current contexts loaded the same already materialized runtime:

    PI_CODING_AGENT_PACKAGE_ROOT:
    /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules/@mariozechner/pi-coding-agent

    PI_CODING_AGENT_NODE_MODULES:
    /Volumes/Dev_SSD/Codexify-worktrees/pi-runtime-materialization/codex_runner/pi-runtime/node_modules

The only current-context difference in the matrix is working directory. Pi
AuthStorage path resolution is based on HOME or PI_CODING_AGENT_DIR, not on
the repository working directory.

## 14. Pi version comparison

    @mariozechner/pi-coding-agent: 0.72.1 in both contexts
    @mariozechner/pi-ai: 0.72.1 in both contexts
    HARNESS_ID: pi-coding-agent
    HARNESS_VERSION: 0.72.1
    PI_RUNTIME_VERSION_MISMATCH: NO

The OAuth proof and the current diagnostic proof both identify the pinned
0.72.1 materialization. No installed-runtime resolution difference was
observed.

## 15. AuthStorage path-resolution semantics

The installed source was inspected at the materialized
@mariozechner/pi-coding-agent 0.72.1 runtime. Its behavior is:

1. The package config name is pi and its config directory name is .pi.
2. The path override variable is PI_CODING_AGENT_DIR.
3. If that variable is absent, getAgentDir() returns os.homedir()/.pi/agent.
4. AuthStorage.create() uses join(getAgentDir(), auth.json) when no explicit
   path is passed.
5. ModelRegistry.create(authStorage) receives the same AuthStorage instance
   and defaults its models path to join(getAgentDir(), models.json).
6. AuthStorage.hasAuth() checks runtime overrides, loaded stored data,
   provider environment keys, and fallback resolver state. It does not refresh
   OAuth credentials.
7. AuthStorage.getAuthStatus() reports non-secret configured/source state and
   explicitly does not refresh.
8. ModelRegistry.getAvailable() filters models through hasAuth() and is
   documented as a fast non-refreshing check.
9. AuthStorage.getApiKey() is the separate path that examines OAuth expiry and
   can enter the locked OAuth refresh path.

The source therefore rules out a pure "expired OAuth token makes
hasAuth=false" explanation. If an OAuth record were successfully loaded into
AuthStorage.data, hasAuth(openai-codex) would still return true regardless of
its expiry value. Expiry is evaluated only when getApiKey() is requested.

No getApiKey(), refreshOAuthTokenWithLock(), login(), logout(), get(), or
getAll() call was made by this task.

## 16. OAuth-proof auth path

The historical OAuth proof did not record the absolute auth path. The
faithful current reconstruction from the recorded materialization worktree
resolved:

    RECONSTRUCTED_OAUTH_AUTH_PATH: /Users/chriscastillo/.pi/agent/auth.json
    RECONSTRUCTED_OAUTH_CONFIG_ROOT: /Users/chriscastillo/.pi/agent

This was obtained from the installed getAgentDir() path API and path
composition, not by reading the auth file.

## 17. Diagnostic auth path

The actual diagnostic context resolved:

    DIAGNOSTIC_AUTH_PATH: /Users/chriscastillo/.pi/agent/auth.json
    DIAGNOSTIC_CONFIG_ROOT: /Users/chriscastillo/.pi/agent

The wrapper called AuthStorage.create() with no explicit path, so this is the
installed runtime's default path.

## 18. Auth path identity result

    AUTH_PATH_IDENTITY: SAME
    OAUTH_RECONSTRUCTION_PATH: /Users/chriscastillo/.pi/agent/auth.json
    DIAGNOSTIC_PATH: /Users/chriscastillo/.pi/agent/auth.json
    PATH_RESOLUTION_CAUSE: NONE OBSERVED

This SAME result applies to the current reconstruction and the diagnostic
context. The original OAuth proof omitted the absolute path, so historical
path identity is not claimed beyond the recorded materialization and the
current reproducible resolution.

The current evidence does not support HOME mismatch, XDG config mismatch,
sandbox HOME isolation, container HOME isolation, or a Pi runtime-root
mismatch as the explanation for the current discrepancy.

## 19. Auth path existence metadata

The metadata-only probe used lstat/access checks and did not read file bytes.
Both current contexts reported:

    AUTH_PATH_EXISTS: true
    AUTH_PATH_IS_REGULAR_FILE: true
    AUTH_PATH_READABLE: true
    AUTH_PATH_WRITABLE_BY_CURRENT_CODEX_PROCESS: false

The false write result is a current managed-Codex process capability
observation. No write was attempted. Readability is the relevant visibility
property for the non-refreshing readiness check, and it passed.

## 20. Auth path ownership metadata

    AUTH_PATH_OWNER_UID: 501
    CURRENT_EFFECTIVE_UID: 501
    OWNER_MATCH: YES

No ownership change was attempted or performed.

## 21. Auth path permission metadata

    AUTH_PATH_PERMISSION_MODE: 0600
    AUTH_PATH_READABLE: true
    AUTH_PATH_WRITABLE_BY_CURRENT_CODEX_PROCESS: false

The mode and metadata were obtained without reading auth-file contents. The
path is a regular readable file owned by the effective user. The current
write restriction did not prevent AuthStorage from loading the path and does
not explain the false non-secret provider status.

## 22. Host operator hasAuth result

From the current operator-owned host shell context, fresh AuthStorage and
ModelRegistry instances reported:

    HOST_OPERATOR_HAS_AUTH_OPENAI_CODEX: false
    HOST_OPERATOR_AUTH_STATUS: configured=false, source=none

The check used only AuthStorage.hasAuth() and AuthStorage.getAuthStatus().
No credential value or provider request was obtained.

## 23. Host authenticated-model count

The fresh host ModelRegistry.getAvailable() result reported:

    HOST_OPERATOR_AVAILABLE_MODEL_COUNT_OPENAI_CODEX: 0
    MODEL_REGISTRY_LOAD_ERROR: none

The count is filtered by actual provider identity openai-codex. It is not a
static model-inventory count.

## 24. Diagnostic-context hasAuth result

From the current diagnostic environment, with the exact authorized identity
variables and the same materialized runtime:

    DIAGNOSTIC_CONTEXT_HAS_AUTH_OPENAI_CODEX: false
    DIAGNOSTIC_CONTEXT_AUTH_STATUS: configured=false, source=none

This agrees with the actual wrapper result
failure_class=oauth_auth_unavailable at failure_stage=oauth_readiness.

## 25. Diagnostic authenticated-model count

The fresh diagnostic-context ModelRegistry.getAvailable() result reported:

    DIAGNOSTIC_CONTEXT_AVAILABLE_MODEL_COUNT_OPENAI_CODEX: 0
    MODEL_REGISTRY_LOAD_ERROR: none

The result is not caused by a provider request. The installed registry's
availability check delegates to the same AuthStorage.hasAuth() result.

## 26. Refresh behavior observation

    HAS_AUTH_REFRESH_ATTEMPTS: 0
    GET_AUTH_STATUS_REFRESH_ATTEMPTS: 0
    GET_AVAILABLE_REFRESH_ATTEMPTS: 0
    GET_API_KEY_CALLS: 0
    OAUTH_REFRESH_ATTEMPTS: 0
    LOGIN_ATTEMPTS_IN_THIS_TASK: 0
    LOGOUT_ATTEMPTS_IN_THIS_TASK: 0
    REVOCATION_ATTEMPTS_IN_THIS_TASK: 0

The source-level behavior is decisive: an expired but successfully loaded
OAuth record would remain visible to hasAuth() and getAvailable(). Only the
separate getApiKey() path can examine expiry and initiate refresh. Since this
task did not call that path, it proves current non-refreshing readiness state,
not token validity.

## 27. Provider inference requests

    CURRENT_TASK_PROVIDER_INFERENCE_REQUESTS: 0
    CURRENT_TASK_PROVIDER_REQUESTS: 0
    CURRENT_TASK_AGENT_INFERENCE_SESSIONS: 0

The Guardian diagnostic preflight stopped before session initialization and
reported provider_request_started=false. The host and diagnostic checks were
local AuthStorage/ModelRegistry operations.

The earlier OAuth proof's single official login/callback flow is historical
authentication traffic, not a model inference request. No authentication
flow was started by this task.

## 28. Model prompts

    CURRENT_TASK_MODEL_PROMPTS: 0
    CURRENT_TASK_GUARDIAN_LIVE_INFERENCE_INVOCATIONS: 0
    CURRENT_TASK_TOOLS_EXPOSED_TO_MODEL: 0

No provider/model qualification attempt was made. The current
guardian-authorized-readiness command has no prompt argument and the wrapper
readiness path does not call session.prompt().

## 29. Credential exposure review

    RAW_AUTH_FILE_CONTENT_READ_BY_INVESTIGATION: NO
    ACCESS_TOKEN_EXPOSED: NO
    REFRESH_TOKEN_EXPOSED: NO
    API_KEY_EXPOSED: NO
    CREDENTIAL_VALUE_HASHED: NO
    CREDENTIAL_RECORD_COPIED: NO
    AUTH_LOGIN_OR_LOGOUT_STARTED: NO
    RAW_PROVIDER_RESPONSE_EXPOSED: NO

Only the following were recorded: booleans, model counts, provider/model
identity strings, package roots, Pi versions, HOME, UID, path names, regular
file status, owner UID, permission mode, and process access results. No auth
file size, content, token field, or credential-shaped value was emitted.

## 30. Final classification

    FINAL_CLASSIFICATION: OAUTH_BINDING_PRESENT_BUT_NOT_CURRENTLY_USABLE

This is the single selected classification.

The prior proof established that Pi had a stored openai-codex OAuth binding
and ten authenticated available models at that earlier point. The current
reconstruction and the current Guardian diagnostic context resolve the same
readable auth path with the same user, HOME, runtime, and Pi version, yet
fresh supported readiness checks report no configured auth and zero
authenticated openai-codex models. The discrepancy is therefore current
binding/state availability, not a current execution-context path split.

The exact internal credential-state subcause is intentionally not selected:
the allowed evidence cannot distinguish external removal, malformed or
unloadable record state, revocation, or another state transition without
reading credential material or initiating a supported auth flow. The
classification above is the narrowest supported bounded class that explains
the prior PASS/current UNAVAILABLE transition without inventing one of those
subcauses.

## 31. Confidence

    CLASSIFICATION_CONFIDENCE: HIGH
    CURRENT_CONTEXT_PATH_COMPARISON_CONFIDENCE: HIGH
    HISTORICAL_OAUTH_PROCESS_IDENTITY_CONFIDENCE: NOT_ASSERTED (not recorded)
    EXACT_CREDENTIAL_STATE_SUBCAUSE_CONFIDENCE: NOT_ASSERTED

High confidence applies to the selected bounded classification and the
current path/runtime comparison. The original OAuth proof's omitted
HOME/UID/path fields prevent a stronger claim about its historical process
identity. That omission does not change the current fact that both
reconstructed and diagnostic contexts now report the same unavailable state.

## 32. Root cause

The previously proven Pi-managed openai-codex binding is no longer recognized
as currently usable by fresh AuthStorage/ModelRegistry readiness checks at
the same readable default auth path. The current failure is not explained by
different HOME values, an XDG root, a sandbox-only auth path, a container
mount, a Pi version, a package-root resolution difference, ownership, or read
permission.

The installed implementation also rules out "non-refreshing readiness
mistook an otherwise loaded expired record for no auth": hasAuth() checks
loaded provider presence without checking expiry. The evidence proves the
bounded state transition, but not the credential-state subcause inside the
operator-owned file.

## 33. Narrowest prerequisite

    EXACT_NEXT_OPERATIONAL_PREREQUISITE:
    Perform one explicit operator OAuth refresh/login qualification through the
    official Pi flow before live execution, from the approved execution context.

That prerequisite is not implemented here. It must not copy credentials,
symlink stores, alter HOME, alter ownership or permissions, or introduce an
API-key fallback. After the operator flow, a fresh non-secret check must
report:

    hasAuth("openai-codex") == true
    available authenticated openai-codex model count >= 1

Only then may Axis consider authorizing a new, separate one-attempt live
Executor qualification.

## 34. What this proves

This proof establishes all of the following:

- The current host and diagnostic contexts use the same user, UID, HOME,
  Pi config root, auth path, materialized package root, and Pi versions.
- The auth path exists as a regular readable 0600 file owned by UID 501.
- Both fresh supported Pi contexts report openai-codex auth unavailable and
  zero authenticated openai-codex models.
- The Guardian diagnostic wrapper reaches exact provider/model/harness
  identity and stops at OAuth readiness without a prompt or provider request.
- AuthStorage.hasAuth(), getAuthStatus(), and ModelRegistry.getAvailable() do
  not refresh OAuth credentials.
- A loaded expired OAuth record would still be visible to hasAuth(), so
  expiration alone cannot explain the observed false result.
- The single selected classification is
  OAUTH_BINDING_PRESENT_BUT_NOT_CURRENTLY_USABLE.
- The single next operational gate is explicit operator OAuth
  refresh/login qualification.

## 35. What this does not prove

This proof does not prove:

- the original OAuth proof's unrecorded historical HOME, UID, or absolute
  auth path;
- whether the prior credential record was externally removed, malformed,
  revoked, or otherwise changed;
- current account entitlement or provider reachability;
- a successful OAuth refresh or login;
- an authenticated provider request;
- a valid inference session or model response;
- Guardian authorization for live execution;
- Executor receipt/result persistence;
- tool enforcement during inference;
- Campaign Engine live role execution;
- provider support or release readiness.

No live Executor requalification is authorized by this artifact.

## 36. Documentation follow-through

Only this proof file was added. The following remained unchanged:

- docs/architecture/00-current-state.md
- provider-support documentation
- release/support claims
- ADR files
- Guardian/Pi source
- wrapper source
- tests
- credential/configuration state

Validation performed for this proof task:

    PYTHONPATH="" .venv/bin/python -m pytest -v \
      tests/pi/test_pi_invocation_contracts.py \
      tests/pi/test_pi_live_invocation.py \
      tests/pi/test_pi_authorized_failure_diagnostics.py \
      tests/ops/test_worker_coding_pi_runtime_contract.py
    Result: 71 passed, 1 warning
    node --check codex_runner/src/agent-wrapper.js: PASS
    make docs PYTHON=.venv/bin/python: PASS
    docs/validate_docs.py: PASS
    scripts/check_diagram_freshness.py: PASS

The required git diff --check is run after this proof artifact is staged in
the final closeout sequence.

## 37. Exact next gate

    RETURN_TO_AXIS: YES
    LIVE_EXECUTOR_REQUALIFICATION_AUTHORIZED_BY_THIS_TASK: NO

Axis must inspect this proven classification. The next authorized action is
the single operator OAuth refresh/login prerequisite above. After that
prerequisite, Axis must require a fresh report showing
openai-codex auth available and at least one authenticated available model.
Only that fresh report can authorize a new one-attempt live OpenAI Codex
Executor qualification.

Final proof outcome:

    FINAL_OUTCOME: PASS
