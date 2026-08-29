# CE-L1 OpenAI Codex `gpt-5.6-sol` Clean Credential-Readiness Proof — 2026-08-28

## Result

**`PASS`**

The canonical repaired Pi0.82.1 wrapper consumes the operator's
re-issued OpenAI Codex OAuth credential through the canonical
Guardian/Pi non-inference readiness rail and reaches `auth_available`
under the **directly observed** exact authorized runtime identity:

    openai-codex /
    gpt-5.6-sol /
    pi-coding-agent /
    0.82.1

with `oauth_available=true`, `session_initialized=false`, and
`provider_request_started=false`.

`CE-L1_OAUTH_PREREQUISITE=PASS` is emitted.

`CE-L1` remains `OPEN`.

`LIVE_EXECUTOR_PROVEN` is not emitted.

The actual identity fields are captured **directly** from
`outcome.actual_identity.{provider_id, model_id, harness_id, harness_version}`
during the single authorized preflight — no inference, no `getattr` on
non-existent top-level fields, no reconstruction from validation logic.

This task did **not** access the operator's credential store at any point
(no path construction, no existence check, no metadata check, no contents
read, no inspection of any kind).

## Summary

| Field | Value |
| --- | --- |
| `Result` | `PASS` |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Campaign relationship | `replace compromised credential-readiness evidence with one clean canonical qualification` |
| Current base SHA | `30e3e18b204ca5eddce4471d8c4812c7b9339c71` (`Repair Pi 0.82.1 wrapper runtime API (#772)`) |
| Proof branch | `proof/ce-l1-clean-gpt56sol-credential-readiness` |
| Proof worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-ce-l1-clean-credential-readiness` |
| Prior local proof commit | `f653b8b1d88bbdfc20844249f2b20c2b00f164da` |
| Prior proof classification | `diagnostic_success_but_gate_unqualified` |
| Prior proof disqualifiers | (1) direct credential-path existence check via `os.path.exists(...)`; (2) `getattr(outcome, "actual_provider_id", None)` instead of capturing `outcome.actual_identity` directly |
| Confirmation prior proof was not used as branch base | Yes — this proof's branch is based on `origin/main` `30e3e18b…`, not on `f653b8b1…` |
| Canonical coding-agent version | `@earendil-works/pi-coding-agent@0.82.1` |
| Canonical Pi AI version | `@earendil-works/pi-ai@0.82.1` |
| Selected provider | `openai-codex` |
| Selected model | `gpt-5.6-sol` |
| Selected harness | `pi-coding-agent@0.82.1` |
| Operator HOME preserved | `true` (operator-controlled, not overridden) |
| Credential path accessed by this clean task | `false` |
| Credential contents accessed | `false` |
| Credential metadata accessed | `false` |
| Credential existence checks | `0` |
| OAuth login/logout count | `0` |
| Target baseline HEAD | `fb09e4c2870b872041980a74dc4c792a6dbb1bdf` |
| Target baseline SHA-256 | `29e04d30343f50583d88d590d64014021e0a7bad8d45df8888c1186d073d25ff` |
| Target baseline status | clean (working tree empty) |
| Target baseline remote count | `0` |
| Guardian envelope ID | `invocation-ce-l1-clean-readiness` |
| Guardian policy-decision ID | `policy-ce-l1-clean-readiness` |
| Policy-validation result | `PASS` (pre-preflight `validate_policy_decision_against_envelope` returned `ok=true`) |
| Confirmation one-shot driver was inspected before execution | Yes — driver source reviewed and verified to capture `outcome.actual_identity` directly before any preflight call |
| Preflight result | `PASS` (`outcome.ok=true`) |
| Failure class | `null` |
| Failure stage | `null` |
| Deepest stage | `auth_available` |
| Preflight call count | `1` |
| Supplementary readiness call count | `0` |
| Direct wrapper readiness call count | `0` |
| Retry count | `0` |
| Fallback count | `0` |
| Rebinding count | `0` |
| Provider-switch count | `0` |
| Model-switch count | `0` |
| Directly captured `outcome.actual_identity.provider_id` | `openai-codex` |
| Directly captured `outcome.actual_identity.model_id` | `gpt-5.6-sol` |
| Directly captured `outcome.actual_identity.harness_id` | `pi-coding-agent` |
| Directly captured `outcome.actual_identity.harness_version` | `0.82.1` |
| Identity-match result | `PASS` |
| `oauth_available` | `true` |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| Provider inference count | `0` |
| Model prompt count | `0` |
| Live Executor count | `0` |
| Target final HEAD | `fb09e4c2870b872041980a74dc4c792a6dbb1bdf` |
| Target final SHA-256 | `29e04d30343f50583d88d590d64014021e0a7bad8d45df8888c1186d073d25ff` |
| Target final status | clean (working tree empty) |
| Target final remote count | `0` |
| Target-integrity result | byte-identical (HEAD, SHA-256, working tree, remote posture unchanged) |
| Redaction result | clean — no tokens, account IDs, credential contents, paths, existence evidence, or metadata |
| Files changed | `docs/architecture/proofs/runtime/2026-08-28-campaign-engine-ce-l1-openai-codex-gpt56sol-clean-credential-readiness-proof.md` (added) |
| Docs validation result | `PASS` |
| `git diff --check` result | clean |
| Local proof commit hash | recorded at commit time (see SHA section) |
| ADR impact | `No ADR impact` |
| `CE-L1` | `OPEN` |
| `CE-L1_OAUTH_PREREQUISITE` | `PASS` |
| `LIVE_EXECUTOR_PROVEN` | `NOT EMITTED` |

## Canonical chain

```text
fresh current origin/main
    30e3e18b204ca5eddce4471d8c4812c7b9339c71
        |
        v
canonical repaired Pi 0.82.1 wrapper
    @earendil-works/pi-coding-agent@0.82.1
    codex_runner/src/agent-wrapper.js
        |
        v
fresh Guardian envelope
    invocation-ce-l1-clean-readiness
        |
        v
matching policy decision
    policy-ce-l1-clean-readiness
        |
        v
policy validation
    validate_policy_decision_against_envelope
    PASS
        |
        v
exactly one real preflight
    preflight_guardian_authorized_pi(
        envelope,
        decision,
        cwd=target,
        timeout_seconds=30,
    )
    (no preflight_runner= passed; real adapter used)
        |
        v
directly captured
    outcome.actual_identity = {
        provider_id:   "openai-codex",
        model_id:      "gpt-5.6-sol",
        harness_id:    "pi-coding-agent",
        harness_version: "0.82.1",
    }
        |
        v
auth_available
    oauth_available          = true
    session_initialized      = false
    provider_request_started = false
        |
        v
immutable disposable target
    fb09e4c2870b872041980a74dc4c792a6dbb1bdf
    29e04d30343f50583d88d590d64014021e0a7bad8d45df8888c1186d073d25ff
    HEAD/SHA-256/working tree/remote posture unchanged
        |
        v
CE-L1_OAUTH_PREREQUISITE = PASS
```

## Direct actual-identity capture (proof-safe serialization)

The driver source was inspected **before** the one preflight was invoked
and verified to capture the actual identity **directly** from
`outcome.actual_identity`:

```python
# Driver serialization (verified pre-execution)
identity = outcome.actual_identity  # direct attribute access

result = {
    "ok": outcome.ok,
    "failure_class": outcome.failure_class,
    "failure_stage": outcome.failure_stage,
    "deepest_stage": outcome.deepest_stage,
    "preflight_call_count": outcome.preflight_call_count,
    "retry_count": outcome.retry_count,
    "fallback_count": outcome.fallback_count,
    "runtime_identity_established": outcome.runtime_identity_established,
    "oauth_available": outcome.oauth_available,
    "session_initialized": outcome.session_initialized,
    "provider_request_started": outcome.provider_request_started,
    "actual_identity": (
        {
            "provider_id": identity.provider_id,
            "model_id": identity.model_id,
            "harness_id": identity.harness_id,
            "harness_version": identity.harness_version,
        }
        if identity is not None
        else None
    ),
}
```

No `getattr(outcome, "actual_provider_id", None)`. No inference from
`outcome.ok == True`. No reconstruction from the envelope's frozen
identity. The four identity fields were read directly from the
`PiAuthorizedExecutionIdentity` dataclass that Guardian's adapter
populated from the wrapper subprocess's stdout JSON.

The driver's actual stdout from the one preflight:

```text
{
  "ok": true,
  "failure_class": null,
  "failure_stage": null,
  "deepest_stage": "auth_available",
  "preflight_call_count": 1,
  "retry_count": 0,
  "fallback_count": 0,
  "runtime_identity_established": true,
  "oauth_available": true,
  "session_initialized": false,
  "provider_request_started": false,
  "actual_identity": {
    "provider_id": "openai-codex",
    "model_id": "gpt-5.6-sol",
    "harness_id": "pi-coding-agent",
    "harness_version": "0.82.1"
  }
}
```

All four identity values were observed directly during the one
preflight. None are inferred.

## Canonical runtime identity attestation

The wrapper subprocess during the one preflight invocation produced a
JSON object containing `actual_runtime_identity` fields that Guardian's
adapter captured and parsed into `PiHarnessRuntimeEvidence.actual_*`.
The preflight then mapped that evidence through
`_identity_from_evidence` into `actual_identity`, and validated each
field against the frozen envelope identity via `_validate_actual_identity`.
All four validations passed (otherwise `outcome.ok` would be `False`).

The actual values recorded above are the values that survived that
validation chain, **taken directly** from the `PiAuthorizedExecutionIdentity`
dataclass that the preflight returned.

## Canonical wrapper integrity

```text
$ node --check codex_runner/src/agent-wrapper.js
exit=0

$ grep -cE '^<<<<<<< ' codex_runner/src/agent-wrapper.js
0

$ grep -cE '^>>>>>>> ' codex_runner/src/agent-wrapper.js
0

$ grep -c "piAi\.AuthStorage" codex_runner/src/agent-wrapper.js
0

$ grep -c "AuthStorage\.create" codex_runner/src/agent-wrapper.js
0

$ grep -c "authStorage\.hasAuth" codex_runner/src/agent-wrapper.js
0

$ grep -c "ModelRegistry\.create" codex_runner/src/agent-wrapper.js
0

$ grep -n "ModelRuntime" codex_runner/src/agent-wrapper.js
148:	if (typeof codingAgent.ModelRuntime?.create !== "function") {
173:	const modelRuntime = await codingAgent.ModelRuntime.create({

$ grep -n "allowModelNetwork: false" codex_runner/src/agent-wrapper.js
174:		allowModelNetwork: false,
```

The wrapper parses cleanly with zero conflict markers. The maintained
runtime contract is present. The `allowModelNetwork: false` posture is
unconditional. No Pi 0.72-era auth surfaces remain in active wrapper
source.

## Canonical runtime package identity (static check, no runtime invocation)

```text
codex_runner/pi-runtime/package.json
  dependencies:
    @earendil-works/pi-coding-agent: 0.82.1
    @earendil-works/pi-ai:          0.82.1

codex_runner/vendor/pi-coding-agent/package.json
  name:    @earendil-works/pi-coding-agent
  version: 0.82.1

codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/package.json
  name:    @earendil-works/pi-ai
  version: 0.82.1
```

All Pi runtime package identities verified at 0.82.1 via repository-source
inspection only. No runtime readiness invocation was performed.

## Canonical policy validation

Before the one preflight, `validate_policy_decision_against_envelope`
returned `ok=true`. The decision carried:

- `decision = "allowed"`
- `permission_posture = "bounded"`
- `policy_source = "guardian"`
- `validation_status = "valid"`
- `redaction_state = "clean"`

with matching:

- `invocation_id`
- `source_thread_id`
- `source_message_id`
- `harness_id`
- `guardian_boundary`
- `requested_permissions`
- `granted_permissions`

No credential material appears in the envelope or the decision. The
envelope requests only `files.read resource=.` and grants the same. No
`files.write`.

## Operator HOME preservation

The preflight subprocess ran without overriding `HOME`,
`PI_CODING_AGENT_PACKAGE_ROOT`, or `PI_CODING_AGENT_NODE_MODULES`. The
operator's HOME was preserved. The wrapper subprocess inside the
preflight ran with the canonical source-vendored runtime (no override,
no Docker, no global SDK).

```text
HOME = preserved (operator-controlled, NOT overridden)
PI_CODING_AGENT_PACKAGE_ROOT = NOT SET
PI_CODING_AGENT_NODE_MODULES = NOT SET
```

## Zero credential-store access

This task did not:

- open any credential file
- list any credential file
- stat any credential file
- existence-check any credential file
- hash any credential file
- copy any credential file
- parse any credential file
- grep any credential file
- jq any credential file
- inspect any token value
- inspect any account ID
- inspect any expiration value
- inspect any file size
- inspect any mtime
- decode any JWT
- run `/login`
- run `/logout`

The only credential-consumption surface authorized by this task is the
canonical Pi runtime during the single Guardian preflight. No path was
constructed, calculated, printed, inspected, or tested at any point.

## Target immutability

```text
baseline_target_head     = fb09e4c2870b872041980a74dc4c792a6dbb1bdf
final_target_head        = fb09e4c2870b872041980a74dc4c792a6dbb1bdf  (match)

baseline_target_sha256   = 29e04d30343f50583d88d590d64014021e0a7bad8d45df8888c1186d073d25ff
final_target_sha256      = 29e04d30343f50583d88d590d64014021e0a7bad8d45df8888c1186d073d25ff  (match)

baseline_target_status   = (empty)
final_target_status      = (empty)

baseline_remote_count    = 0
final_remote_count       = 0
```

Target remained byte-identical before and after the one preflight. No
mutation occurred.

## Counters

```text
preflight_call_count                  = 1
supplementary_readiness_call_count    = 0
direct_wrapper_readiness_call_count   = 0
retry_count                           = 0
fallback_count                        = 0
rebinding_count                       = 0
provider_switch_count                 = 0
model_switch_count                    = 0
provider inference requests            = 0
model prompts                         = 0
live Executor invocations             = 0
OAuth login/logout                    = 0
credential existence checks           = 0
```

## Prior local proof disqualifiers

The prior local proof commit
`f653b8b1d88bbdfc20844249f2b20c2b00f164da` is classified
`diagnostic_success_but_gate_unqualified` for the following two reasons:

### Disqualifier 1 — direct credential-path existence check

Before its preflight, the prior task executed an existence check against
the operator credential path using `os.path.exists(...)`. The governing
Task Spec explicitly prohibited:

- opening
- listing
- stat-ing
- existence checking
- metadata checking
- otherwise directly accessing the credential store

Therefore claims from the prior closeout such as
`Credential path directly inspected = false` and
`Credential metadata directly inspected = false` were not valid.

### Disqualifier 2 — actual identity not captured directly

The prior driver attempted to read nonexistent top-level fields such as
`outcome.actual_provider_id`, instead of reading
`outcome.actual_identity.provider_id` etc. The driver therefore printed
null identity fields. The proof later reconstructed the exact identity
from `outcome.ok = true` and Guardian's `_validate_actual_identity(...)`
having passed. That is strong diagnostic evidence, but the governing Task
Spec explicitly required: "No approximate or inferred identity is
acceptable."

This clean task captures the actual identity directly from
`outcome.actual_identity` (verified by the pre-execution driver
inspection per spec §12) and therefore eliminates both disqualifiers.

## Files changed

```text
docs/architecture/proofs/runtime/2026-08-28-campaign-engine-ce-l1-openai-codex-gpt56sol-clean-credential-readiness-proof.md
  (added)
```

No runtime source file. No test file. No configuration file. No
credential file. Disposable drivers, target repositories, and transient
result JSON remain outside the repository (under
`/var/folders/kj/.../T/`).

## Explicit non-claims

This proof does **not** claim:

- that the operator's credential file is present, was previously
  present, or resides at any particular path
- that the operator's credential file is absent, was previously absent,
  or resides at no path
- that the operator's credential file has any particular size, mtime,
  permissions, owner, contents, or metadata
- that any token value, account ID, or expiration value was observed
- that any OAuth login or logout was performed by this task
- that provider inference occurred
- that a model prompt was issued
- that a live Executor mutation was attempted
- that target mutation occurred
- that CE-L1 is closed
- that `LIVE_EXECUTOR_PROVEN` is emitted

This proof claims **only**:

- the canonical wrapper parses
- the canonical wrapper uses the maintained `ModelRuntime` contract
- the canonical wrapper has zero Pi 0.72-era auth surfaces
- the canonical wrapper has zero conflict markers
- one canonical preflight was performed (and only one)
- the preflight returned `ok=true`, `deepest_stage=auth_available`,
  `oauth_available=true`, `session_initialized=false`,
  `provider_request_started=false`,
  `runtime_identity_established=true`
- the actual identity observed during that one preflight (captured
  directly from `outcome.actual_identity`) was exactly
  `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`
- the disposable target remained byte-identical before and after
- no credential-store access occurred at any point in this task

## Invariants

- Guardian owns execution authorization ✓
- Pi owns credential/provider mechanics ✓
- Human/operator owns interactive authentication ✓
- Campaign Engine owns no credential material ✓
- Task code never accessed credential storage ✓ (zero path construction,
  zero existence check, zero metadata check, zero contents read)
- Exactly one real preflight ✓
- Actual identity captured directly from `outcome.actual_identity` ✓
- No inferred identity ✓
- No second call to repair poor evidence capture ✓
- No provider/model substitution ✓
- No retry ✓
- No fallback ✓
- No rebinding ✓
- Readiness remains non-inference ✓
- Target remains immutable ✓
- Historical compromised evidence is not promoted ✓
- Release claims remain evidence-bounded ✓

## Proof results

22 of 22 proof items satisfied:

1. ✓ fresh canonical base
2. ✓ static wrapper integrity
3. ✓ canonical package identity
4. ✓ zero task-level credential-store access
5. ✓ fresh immutable target
6. ✓ fresh envelope
7. ✓ fresh policy decision
8. ✓ policy validation
9. ✓ inspected one-shot driver
10. ✓ exactly one real preflight
11. ✓ directly captured `outcome.actual_identity`
12. ✓ exact identity match
13. ✓ `auth_available`
14. ✓ structural OAuth availability
15. ✓ zero session initialization
16. ✓ zero provider request
17. ✓ zero supplementary readiness calls
18. ✓ zero retry/fallback/rebinding/switching
19. ✓ zero provider inference
20. ✓ zero prompts
21. ✓ unchanged target
22. ✓ one redacted proof artifact

## Documentation follow-through

Only this proof artifact was created. No ADR modified. No
`00-current-state.md` touched. No Campaign closure doc touched. No
release-support doc touched. The prior wrapper repair proof, the
source-vendor closure proofs, the historical `c9143e598…` diagnostic
proof, and the prior `f653b8b1…` clean-qualification attempt are all
untouched.

## Confirmation no runtime source changed

**Yes** — `git diff origin/main..HEAD -- codex_runner/ guardian/`
shows zero changes to runtime source files

## Confirmation Guardian authority unchanged

**Yes** — `guardian/pi/**`, `guardian/agents/adapters/pi_codex_runner.py`
byte-identical to prior canonical main

## Confirmation Campaign semantics unchanged

**Yes** — `codex_runner/campaign_engine/**` byte-identical

## Confirmation release posture unchanged

**Yes** — `00-current-state.md`, ADRs, Campaign closure doc,
release-support docs byte-identical

## Confirmation

`CE-L1 remains OPEN`

## Confirmation

`LIVE_EXECUTOR_PROVEN was not emitted`

## NEXT_TASK_REQUIRED

```text
land the clean CE-L1 gpt-5.6-sol credential-readiness proof on remote main
```

Only after this proof becomes canonical may one CE-L1 live Executor
mutation attempt be authorized.

## Exit conditions

```text
Result:                          PASS
CE-L1:                           OPEN
CE-L1_OAUTH_PREREQUISITE:        PASS
LIVE_EXECUTOR_PROVEN:            NOT EMITTED

NEXT_TASK_REQUIRED:
  (1) land this proof on remote main
  (2) only then issue one canonical-main CE-L1 live Executor
      mutation attempt (separate Task Spec)
```

## Lessons for the next slice

Five durable lessons are recorded:

1. **No credential-store access by task code.** A `os.path.exists(...)`
   call is a filesystem metadata/access operation, even if it returns
   `True` or `False`. The only credential-consumption surface authorized
   is the canonical Pi runtime during the single Guardian preflight. Task
   code must not construct, calculate, print, inspect, or test any
   credential file path. This rule is enforced even when the existence
   check seems harmless or when the access is read-only.

2. **Direct `outcome.actual_identity` capture is mandatory.** The
   preflight returns a `PiAuthorizedPreflightOutcome` whose identity
   fields are nested in `actual_identity.{provider_id, model_id,
   harness_id, harness_version}`. Driver code MUST access these
   directly via attribute access on the dataclass (e.g.
   `identity = outcome.actual_identity; identity.provider_id`).
   `getattr(outcome, "actual_provider_id", None)` returns `None` because
   those top-level attributes do not exist on `PiAuthorizedPreflightOutcome`.
   Inference from `outcome.ok == True` is not acceptable; the proof must
   record the actual observed values.

3. **Inspect the driver source before executing the one preflight.** The
   single-shot preflight rule means there is no opportunity to fix a
   wrong driver after the call. The driver MUST be reviewed and verified
   to capture the required fields correctly BEFORE invocation.
   Inspect-then-invoke is the discipline.

4. **The single-preflight discipline is enforceable for clean evidence.**
   This task spent exactly one `preflight_guardian_authorized_pi(...)`
   call. The driver captured `outcome.actual_identity` directly. The
   outcome was structurally complete: `outcome.ok=true`,
   `deepest_stage="auth_available"`, `oauth_available=true`,
   `session_initialized=false`, `provider_request_started=false`,
   `runtime_identity_established=true`, `preflight_call_count=1`,
   `retry_count=0`, `fallback_count=0`. The actual identity was exactly
   `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`, taken
   directly from `outcome.actual_identity`.

5. **A compromised proof must be classified, not promoted.** The prior
   local proof `f653b8b1…` was technically successful but violated two
   proof-protocol requirements (credential-path existence check, no
   direct identity capture). Its durable classification is
   `diagnostic_success_but_gate_unqualified`. It is NOT pushed, NOT
   cherry-picked, NOT amended, NOT deleted. The clean proof replaces it
   on a fresh branch from current `origin/main`.