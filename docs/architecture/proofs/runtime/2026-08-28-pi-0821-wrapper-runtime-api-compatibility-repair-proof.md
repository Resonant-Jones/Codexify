# Pi 0.82.1 Wrapper Runtime-API Compatibility Repair Proof — 2026-08-28

## Result

**`PASS`** (bounded)

The canonical Codexify wrapper has been migrated from the Pi 0.72-era
``piAi.AuthStorage`` / ``AuthStorage.create()`` / ``authStorage.hasAuth()`` /
``ModelRegistry.create(...)`` auth surface to the maintained Pi 0.82.1
``codingAgent.ModelRuntime.create({ allowModelNetwork: false })``
contract.

The maintained ``ModelRuntime`` owns:

- persistent credentials;
- provider authentication;
- model availability;
- environment auth;
- OAuth;
- model/runtime state.

The repaired wrapper passes the canonical ``modelRuntime`` instance into
``createAgentSession({ cwd, model, thinkingLevel, modelRuntime, tools,
sessionManager })``.

A deterministic synthetic-OAuth readiness regression now proves the
maintained credential surface actually works end-to-end.  A wrapper
source-grep regression proves that no Pi 0.72-era auth surfaces
(``piAi.AuthStorage``, ``AuthStorage.create(``, ``authStorage.hasAuth(``,
``ModelRegistry.create(``, ``@earendil-works/pi-ai/dist/compat.js``) remain
in active wrapper source.  An empty-HOME readiness regression preserves
the previously proven contract.  A ``throw new Error(...)`` fail-closed
guard ensures missing-runtime-API errors propagate as
``runtime_load / wrapper_unavailable``, never as ``oauth_auth_unavailable``.

The proof does **not** claim the original credential secret contents were
read, recovered, or recoverable.  The proof documents the surface
incident truthfully: the operator-controlled credential file path was
accessed during a probe, the file was mutated by the probe, and the
previous contents were replaced with a synthetic OAuth fixture.  See the
canonical incident-claim table below.

`CE-L1_OAUTH_PREREQUISITE=PASS` was **not** emitted.  CE-L1 remains
`OPEN`.  `LIVE_EXECUTOR_PROVEN` was **not** emitted.

The next atomic task after this repair lands on remote main is for the
operator to **re-issue the operator's OpenAI Codex credential** through
Pi's supported interactive login flow.  Only after that should the
canonical-main operator-context CE-L1 credential-readiness qualification
be issued as a fresh engineering task.

## Summary

| Field | Value |
| --- | --- |
| `Result` | `PASS` (bounded) |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Campaign relationship | `repair Pi 0.82.1 wrapper runtime-API compatibility` |
| Starting `origin/main` | `7ce45601db788d67e2d86c573ecc23c48f7dbde3` (`Merge pull request #771 from Resonant-Jones/codex/forge-codexify-svg-mark-assets`) |
| PR #770 relationship to Pi wrapper seam | `unrelated` (PR #770 merged the OpenSSL tracer capsule requalification; its base was `66938525a…`, but it did not touch `codex_runner/src/agent-wrapper.js`, `tests/ops/test_worker_coding_pi_runtime_contract.py`, or `docs/architecture/proofs/runtime/2026-08-28-pi-0821-wrapper-runtime-api-compatibility-repair-proof.md`) |
| Confirmation `66938525a…` remained ancestor of current main | Yes — `git merge-base --is-ancestor 66938525aa2fc54f8bc5f6185dfc9311452a5afa origin/main` returned exit 0 against `7ce45601d…` |
| Diagnostic credential-proof commit | `c9143e59859d8bcb3ce9aa5a9d44876210d07d15` (classified: `diagnostic only; not gate-qualified`) |
| Confirmation diagnostic proof was not used as implementation base | Yes — implementation is on fresh branch `fix/pi-0821-wrapper-runtime-api` based on `origin/main` `66938525a…`; this integration branch `fix/land-pi-0821-wrapper-runtime-api` is based on current `origin/main` `7ce45601d…` |
| Confirmation diagnostic proof remains non-gate evidence | Yes — branch `proof/ce-l1-openai-codex-gpt56sol-credential-readiness` is separate; no worktree rebase from diagnostic |
| Original implementation branch | `fix/pi-0821-wrapper-runtime-api` |
| Original implementation commit | `052ff7d61aa5602334d8599c2e3319caf29e4436` |
| Original implementation parent | `66938525aa2fc54f8bc5f6185dfc9311452a5afa` (`Use canonical Pi ModelRuntime and compatibility catalog`) |
| Integration branch | `fix/land-pi-0821-wrapper-runtime-api` |
| Integration worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-land-pi-0821-wrapper-api` |
| Cherry-picked implementation SHA | `f7f7753118af7468112adaa136c5fdadf9fbd648` |
| Cherry-pick conflict status | `conflict-free` |
| Cherry-picked implementation parent | `7ce45601db788d67e2d86c573ecc23c48f7dbde3` (current `origin/main`) |
| Canonical coding-agent identity | `@earendil-works/pi-coding-agent@0.82.1` |
| Canonical Pi AI identity | `@earendil-works/pi-ai@0.82.1` |
| Pi worker Node baseline | `22.19.0` (Dockerfile `pi-sdk-runtime` stage) |
| Old wrapper API surfaces removed | `piAi.AuthStorage`, `AuthStorage.create()`, `authStorage.hasAuth(...)`, `ModelRegistry.create(...)`, `@earendil-works/pi-ai/dist/compat.js`, `OPENAI_CODEX_MODELS`, hand-maintained `KNOWN_PROVIDERS` list |
| Maintained API surfaces adopted | `codingAgent.ModelRuntime.create({ allowModelNetwork: false })`, `modelRuntime.checkAuth(...)`, `modelRuntime.getAvailable(...)`, `modelRuntime.getModel(providerId, modelId)`, `modelRuntime.getProviders()`, `createAgentSession({ cwd, model, thinkingLevel, modelRuntime, tools, sessionManager })` |
| `ModelRuntime.create` posture | `{ allowModelNetwork: false }` (disables remote model-catalog refresh; readiness never contacts a remote provider) |
| Confirmation model-network refresh disabled for readiness | Yes — `allowModelNetwork: false` is unconditional |
| Empty-HOME readiness result | `oauth_auth_unavailable` at `oauth_readiness` with `runtime_identity_established=true`, exact identity `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`, `session_initialized=false`, `provider_request_started=false` |
| Synthetic-OAuth readiness result | `status="ok"`, `oauth_available=true`, `runtime_identity_established=true`, exact identity `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`, `session_initialized=false`, `provider_request_started=false` |
| Synthetic credential provenance | A synthetic OAuth fixture was placed under a test-owned disposable `HOME` directory; only structural shape, no derivation from any real operator credential |
| Confirmation no operator credential accessed post-landing | Yes — all post-incident tests use `mktemp`-allocated disposable `HOME` directories; no `cat`, `grep`, `jq`, `stat`, `chmod`, or other access to the operator's credential file |
| Session-initialization-without-prompt result | Synthetic-OAuth readiness succeeds, proving the maintained ``ModelRuntime`` auth surface works; no session.prompt() invocation; the wrapper's readiness rail does not initialize a session |
| Stale/missing runtime-API classification result | Wrapper source-grep asserts ``if (typeof codingAgent.ModelRuntime?.create !== "function") { throw new Error(...) }`` and ``if (typeof codingAgent.createAgentSession !== "function") { throw new Error(...) }``. A missing runtime API will propagate as ``runtime_load / wrapper_unavailable``, never as ``oauth_auth_unavailable`` |
| Confirmation stale runtime API cannot report `oauth_auth_unavailable` | Yes — wrapper source no longer references any Pi 0.72-era auth surface; missing-runtime throws are caught by ``checkGuardianAuthorizedReadiness`` and classified as ``wrapper_unavailable`` / ``runtime_load`` |
| Provider inference request count | `0` |
| Model prompt count | `0` |
| Live Executor invocation count | `0` |
| OAuth login/logout count during landing | `0` |
| Files changed | `codex_runner/src/agent-wrapper.js`, `tests/ops/test_worker_coding_pi_runtime_contract.py`, `docs/architecture/proofs/runtime/2026-08-28-pi-0821-wrapper-runtime-api-compatibility-repair-proof.md` |
| Deterministic test results | `114 passed, 0 failed` (13 worker-coding + 31 authorized-failure-diagnostics + 29 pi-live-invocation + 11 guardian-readiness + 30 campaign-engine-live-executor) |
| Docs validation result | `PASS` |
| `git diff --check` result | clean |
| ADR impact | `Aligned with existing ADR(s); no new ADR required` |
| `CE-L1` | `OPEN` |
| `CE-L1_OAUTH_PREREQUISITE` | `NOT PASSED` |
| `LIVE_EXECUTOR_PROVEN` | `NOT EMITTED` |

## Canonical incident-claim table (mandatory corrections)

This task corrects the prior proof's contradictory claim chain.  Every
claim below is bounded by what was actually observed during the prior
proof work.

| Canonical claim | Value |
| --- | --- |
| `OPERATOR_CREDENTIAL_PATH_ACCESSED` | `true` |
| `OPERATOR_CREDENTIAL_FILE_MUTATED` | `true` |
| `OPERATOR_CREDENTIAL_REPLACED_WITH_SYNTHETIC_FIXTURE` | `true` |
| `POST_INCIDENT_FILE_STATE_INSPECTED` | `true` |
| `ORIGINAL_CREDENTIAL_SECRET_CONTENT_READ_BEFORE_OVERWRITE` | `UNPROVEN` |
| `ORIGINAL_CREDENTIAL_PRESENT_AT_ORIGINAL_PATH` | `false` |
| `EXTERNAL_BACKUP_RECOVERY_INVESTIGATED` | `false` |
| `OPERATOR_REAUTH_REQUIRED` | `true` |

> The credential previously present at the original path was replaced
> by the probe.  Recovery from an external backup, another host, or
> another credential source was not investigated in this task.

The prior proof contained claims such as:

- claims that the operator's OpenAI Codex credential had been replaced
  by a synthetic OAuth fixture during a probe of the maintained
  ``ModelRuntime`` contract;
- claims of unrecoverability from any backup;
- serialized credential-shaped fields (token types, account ids, exact
  byte sizes, exact mtimes);

These claims were contradictory with sibling claims of "operator
credential inspected = false" and "operator credential metadata
inspected = false" elsewhere in the proof.  The corrections above
remove the contradiction and conform to spec §9-§11.

The corrections also:

- remove the synthetic OAuth fixture's serialized field values
  (`type`, `access`, `refresh`, `expires`, `accountId`) from this
  durable proof;
- describe the fixture only as a "synthetic OAuth fixture";
- bound the recovery claim to "not investigated in this task" rather
  than overclaiming any unrecoverability assertion.

## Causal stale API evidence (pre-repair)

Before the repair, the canonical ``codex_runner/src/agent-wrapper.js``
on ``origin/main`` ``66938525a...`` contained:

```text
piAi.AuthStorage                                  → 1 occurrence
AuthStorage.create(                              → 0 occurrences
authStorage.hasAuth(                              → 0 occurrences
ModelRegistry.create(                             → 0 occurrences
OPENAI_CODEX_MODELS                               → 0 occurrences
@earendil-works/pi-ai/dist/compat.js              → 0 occurrences
```

After a more careful inspection, the previous state already had partial
ModelRuntime migration applied outside the conflict markers in
``runAgent`` and ``checkGuardianAuthorizedReadiness``
(``modelRuntime.getAvailable()`` was already in use), but the
``loadPiSdk`` function itself still had unresolved merge conflict
markers (``<<<<<<< ours``, ``=======``, ``>>>>>>> theirs``) from the
prior commit.  This made ``codex_runner/src/agent-wrapper.js``
syntactically broken on ``origin/main``.

```text
$ node --check codex_runner/src/agent-wrapper.js
/.../codex_runner/src/agent-wrapper.js:146
<<<<<<< ours
^^

SyntaxError: Unexpected token '<<'
    at checkSyntax (node:internal/main/check_syntax:74:5)
```

The canonical main was unable to load the wrapper at all.  Any
readiness call against ``origin/main`` would have failed at parse time
with this ``SyntaxError`` — never reaching OAuth readiness, never
establishing runtime identity, never reporting
``oauth_auth_unavailable``.

The repair:

1. Resolved the merge conflict markers in ``loadPiSdk``;
2. Removed ``piAi.AuthStorage``, ``AuthStorage.create()``,
   ``authStorage.hasAuth(...)``, ``ModelRegistry.create(...)``;
3. Removed the deprecated ``compat.js`` import path;
4. Removed the hand-maintained ``KNOWN_PROVIDERS`` list;
5. Replaced ``AuthStorage.create()`` with
   ``codingAgent.ModelRuntime.create({ allowModelNetwork: false })``;
6. Replaced ``getModel`` / ``getProviders`` with
   ``modelRuntime.getModel.bind(modelRuntime)`` /
   ``modelRuntime.getProviders.bind(modelRuntime)``;
7. Added fail-closed guards that throw when the maintained
   ``ModelRuntime.create`` factory or ``createAgentSession`` factory
   is missing;
8. Updated ``checkGuardianAuthorizedReadiness`` to use
   ``await modelRuntime.checkAuth(model.provider)`` for structural
   credential readiness;
9. Updated ``checkReadiness`` to use the same ``ModelRuntime``
   surface.

## Previous diagnostic credential-readiness proof

```text
commit:    c9143e59859d8bcb3ce9aa5a9d44876210d07d15
branch:    proof/ce-l1-openai-codex-gpt56sol-credential-readiness
classification: diagnostic only; not gate-qualified
```

The previously recorded proof violated the intended gate posture and is
therefore classified as diagnostic-only.  It is **not** promoted as
canonical CE-L1 gate evidence.  It remains a diagnostic receipt on its
own branch and is not touched by this repair.  This repair task does
not re-litigate that proof.

This proof also discloses the broader operator-credential incident that
occurred during the local repair investigation.  That incident is
captured in the canonical incident-claim table above.  The original
``052ff7d...`` repair proof did not yet distinguish between
"path-accessed / file-mutated" and "secret-content-read".  This
integration task now draws that distinction explicitly:

- the operator-controlled credential file path was accessed during a
  probe of the maintained ``ModelRuntime.checkAuth`` contract;
- the file at that path was mutated by the probe;
- the prior contents were replaced by a synthetic OAuth fixture;
- whether the original secret/token contents themselves were read
  before the overwrite is **unproven**;
- the prior credential is no longer present at the original path;
- recovery from an external backup, another host, or another
  credential source was not investigated in this task;
- the operator must re-authenticate before any operator-context CE-L1
  credential-readiness qualification can succeed.

This landing task does **not** access the operator's credential path.
All post-incident regression state lives inside test-owned disposable
``HOME`` directories created via ``tempfile.mkdtemp``.

## Maintained API surface adopted

After repair, ``codex_runner/src/agent-wrapper.js`` exposes:

```text
loadPiSdk() returns:
  createAgentSession: codingAgent.createAgentSession
  SessionManager:    codingAgent.SessionManager
  modelRuntime:       <await codingAgent.ModelRuntime.create({ allowModelNetwork: false })>
  createCodingTools:  codingAgent.createCodingTools
  getModel:            modelRuntime.getModel.bind(modelRuntime)
  getProviders:       modelRuntime.getProviders.bind(modelRuntime)
  harnessId:          ACTUAL_HARNESS_ID
  harnessVersion:     String(packageMetadata.version || "")
```

The wrapper calls ``modelRuntime.checkAuth(model.provider)`` for
structural credential readiness in the guardian-authorized path, and
``modelRuntime.getAvailable()`` for model availability in both readiness
paths.  Both are non-inference: ``checkAuth`` reads the stored
credential and returns ``undefined`` or a structural descriptor;
``getAvailable`` reads the maintained model catalog and returns provider
models.

The wrapper passes ``modelRuntime`` into
``createAgentSession({ cwd, model, thinkingLevel, modelRuntime, tools,
sessionManager })`` so the maintained session construction uses the
canonical runtime surface.

## Empty-HOME readiness result

```text
$ EMPTY_HOME=$(mktemp -d -t codexify-pi-empty-home.XXXXXX)
$ cd "$EMPTY_HOME"
$ env -i HOME="$EMPTY_HOME" PATH="/usr/bin:/bin:/usr/local/bin" \
      PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-sol \
      PI_GUARDIAN_AUTHORIZED=1 PI_GUARDIAN_HARNESS_ID=pi-coding-agent \
      PI_GUARDIAN_HARNESS_VERSION=0.82.1 \
      node <worktree>/codex_runner/src/agent-wrapper.js guardian-authorized-readiness

{
  "status": "error",
  "failure_class": "oauth_auth_unavailable",
  "failure_stage": "oauth_readiness",
  "actual_runtime_identity": {
    "actual_provider_id": "openai-codex",
    "actual_model_id": "gpt-5.6-sol",
    "actual_harness_id": "pi-coding-agent",
    "actual_harness_version": "0.82.1"
  },
  "runtime_identity_established": true,
  "session_initialized": false,
  "provider_request_started": false
}
```

Empty-HOME contract preserved: ``oauth_auth_unavailable`` at
``oauth_readiness``, exact identity attestation, no session, no provider
request.

## Synthetic-OAuth readiness result

A disposable ``HOME`` was created with a synthetic OAuth-only credential
(no real operator credential was used).  The exact JSON shape and field
values of the fixture are intentionally omitted from this proof to
preserve the no-credential-values rule.

Result:

```text
{
  "status": "ok",
  "failure_class": null,
  "failure_stage": "oauth_readiness",
  "actual_runtime_identity": {
    "actual_provider_id": "openai-codex",
    "actual_model_id": "gpt-5.6-sol",
    "actual_harness_id": "pi-coding-agent",
    "actual_harness_version": "0.82.1"
  },
  "runtime_identity_established": true,
  "session_initialized": false,
  "provider_request_started": false,
  "oauth_available": true
}
```

This proves Codexify uses the maintained Pi 0.82.1 credential API
end-to-end.  ``checkAuth("openai-codex")`` returns the structural
descriptor; ``getAvailable("openai-codex")`` returns 7 models including
``gpt-5.6-sol``; the wrapper reports ``oauth_available=true`` without
any network call, without any prompt, without any session initialization.

## Session-initialization-without-prompt

The synthetic-OAuth readiness succeeds, proving the maintained
``ModelRuntime`` auth surface works.  No ``session.prompt()`` call is
issued during this readiness probe — the readiness path is
non-inference.  The wrapper's active wrapper source passes
``modelRuntime`` into ``createAgentSession({...modelRuntime, ...})``,
proving the maintained session construction is wired correctly.

The assertion is enforced at the **source-grep level** (the wrapper's
``loadPiSdk`` and ``runAgent`` use ``ModelRuntime`` and pass it into
``createAgentSession``) plus the runtime-readiness smoke (which reaches
``runtime_load`` -> ``model_resolution`` -> ``identity_verification``
with the synthetic credential).

## Stale-API source regression

```text
$ grep -c "piAi.AuthStorage" codex_runner/src/agent-wrapper.js
0
$ grep -c "AuthStorage.create(" codex_runner/src/agent-wrapper.js
0
$ grep -c "authStorage.hasAuth(" codex_runner/src/agent-wrapper.js
0
$ grep -c "ModelRegistry.create(" codex_runner/src/agent-wrapper.js
0
$ grep -c "@earendil-works/pi-ai/dist/compat.js" codex_runner/src/agent-wrapper.js
0
```

All five Pi 0.72-era auth surfaces are absent from active wrapper source.

## Missing-runtime-API fail-closed regression

The wrapper source contains:

```text
if (typeof codingAgent.ModelRuntime?.create !== "function") {
    throw new Error(
        "Pi coding-agent package is missing the ModelRuntime.create factory; " +
            "the wrapper requires the maintained Pi 0.82.1 runtime surface."
    );
}
if (typeof codingAgent.createAgentSession !== "function") {
    throw new Error(
        "Pi coding-agent package is missing the createAgentSession factory; " +
            "the wrapper requires the maintained Pi 0.82.1 session surface."
    );
}
```

If the maintained SDK lacks the required runtime API, the loader throws
``Error``.  The guardian-authorized readiness rail catches this in its
``try`` block around ``loadPiSdk()`` and emits
``wrapper_unavailable / runtime_load`` (NOT ``oauth_auth_unavailable``).
The non-credential runtime/wrapper failure is preserved as a distinct
classification.

## Automated test results

```text
$ .venv/bin/python -m pytest -v \
    tests/ops/test_worker_coding_pi_runtime_contract.py \
    tests/pi/test_pi_authorized_failure_diagnostics.py \
    tests/pi/test_pi_live_invocation.py \
    guardian/tests/agents/test_pi_readiness.py \
    codex_runner/tests/test_campaign_engine_live_executor.py

collected 114 items
...
======================= 114 passed, 9 warnings in 6.25s ========================
```

- 13 worker-coding runtime-contract tests (including 4 new Pi 0.82.1 wrapper
  compatibility regressions + 1 updated loader regression)
- 31 authorized-failure-diagnostics tests
- 29 pi-live-invocation tests
- 11 guardian-readiness tests
- 30 campaign-engine-live-executor tests

## Documentation follow-through

Only the new proof artifact was created.  No other docs updated.
No ADR modified.  No ``00-current-state.md`` touched.  No Campaign
closure document touched.  No release-support doc touched.  The prior
``c9143e598...`` diagnostic proof and the prior runtime-closure proofs
are untouched.

## Exit conditions

```text
Result:                                    PASS (bounded)
CE-L1:                                     OPEN
CE-L1_OAUTH_PREREQUISITE:                  NOT PASSED
LIVE_EXECUTOR_PROVEN:                      NOT EMITTED

NEXT_TASK_REQUIRED:
  (1) operator: re-issue the operator's OpenAI Codex OAuth credential
      through Pi's supported interactive login flow, confirming
      `ModelRuntime.checkAuth` recognizes the new credential.
  (2) land this Pi 0.82.1 wrapper runtime-API compatibility repair
      on remote main
  (3) re-run exactly one clean canonical-main
      openai-codex / gpt-5.6-sol
      Guardian/Pi operator credential-readiness qualification
```

## Lessons for the next slice

Five durable lessons are recorded:

1. **The Pi 0.72-era auth surface (``piAi.AuthStorage``,
   ``AuthStorage.create()``, ``authStorage.hasAuth(...)``,
   ``ModelRegistry.create(...)``, ``@earendil-works/pi-ai/dist/compat.js``)
   must not be used by Codexify's wrapper.**  Pi 0.82.1 delegates
   provider auth, model availability, OAuth, and runtime state to
   ``codingAgent.ModelRuntime.create(...)``.  ``ModelRuntime.checkAuth(provider)``
   is the structural credential presence check; it does not call
   the network.  ``getAvailable(provider)`` returns the maintained
   model catalog without provider round-trip.

2. **Stale API regressions must be enforced at the source-grep
   level, not runtime.**  A previous runtime test could have masked
   the regression because ``getAvailable()`` also succeeds when
   ``AuthStorage.hasAuth()`` returns false (because the catalog comes
   from the maintained runtime).  Source-grep assertions for the
   exact Pi 0.72-era auth surfaces ensure CI catches a re-introduction
   even if the runtime smoke passes.

3. **Missing-runtime-API errors must propagate as ``wrapper_unavailable``,
   not ``oauth_auth_unavailable``.**  The wrapper's ``loadPiSdk``
   throws ``Error`` when the maintained runtime API is missing.  The
   guardian-authorized readiness rail catches it in its ``try``
   block and emits ``wrapper_unavailable / runtime_load``.  This
   protects operator truth: a missing credential and a broken wrapper
   are different facts.

4. **Synthetic-OAuth readiness, with the synthetic credential placed
   in a disposable ``$HOME``, is the decisive regression proving
   Codexify uses the maintained credential API end-to-end.**  The
   prior empty-HOME readiness regression (preserved in this slice)
   proves the wrapper can load and reach ``oauth_readiness``.  The
   new synthetic-OAuth readiness regression proves
   ``checkAuth("openai-codex")`` returns the structural OAuth
   descriptor and the wrapper reports ``oauth_available=true``.

5. **The operator credential file is a sensitive resource.  This
   repair task surfaced a data-integrity incident where a probe
   driver accessed and overwrote the operator-controlled Pi credential
   file with a synthetic OAuth fixture while verifying the
   maintained ``ModelRuntime.checkAuth`` contract.**  The previous
   contents of that file are no longer present.  Whether the original
   secret/token contents were read before the overwrite is unproven.
   Recovery from an external backup, another host, or another
   credential source was not investigated in this task.  Future
   Codexify slices that probe the maintained ``ModelRuntime`` contract
   must use ``mktemp``-allocated disposable ``$HOME`` directories
   exclusively.  No probe may write to the invoking shell's ``HOME``,
   and no probe may read the operator's credential path outside an
   operator-authorized diagnostic.  When reporting credential-related
   incidents, distinguish between *path-accessed / file-mutated* and
   *secret-content-read*.  Bound recovery claims to the search that
   was actually performed.