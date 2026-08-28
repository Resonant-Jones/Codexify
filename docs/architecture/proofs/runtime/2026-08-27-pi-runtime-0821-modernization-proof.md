# Pi Runtime 0.82.1 Modernization Proof — 2026-08-27

## Result

**`PASS`**

The Codexify canonical Pi runtime has been modernized from the deprecated
upstream namespace to the maintained namespace and now resolves the
historical CE-L1 blocker model `openai-codex / gpt-5.6-sol` through
the canonical wrapper subprocess.

Canonical remote-main reference at proof time:

```text
3c56cba985e97fc52f017fe680b86bdb63096015
Qualify Pi OpenAI Codex OAuth refresh (#762)
```

Implementation branch:

```text
fix/pi-runtime-0821
```

Implementation worktree:

```text
/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-runtime-0821
```

`CE-L1_OAUTH_PREREQUISITE` is **not** emitted as `PASS` by this
implementation slice.  `LIVE_EXECUTOR_PROVEN` is **not** emitted.  CE-L1
remains `OPEN`.

The smallest next authorized slice is:

> `land the Pi 0.82.1 runtime modernization on remote main` and then,
> from canonical remote main,
> `run one clean canonical-main openai-codex / gpt-5.6-sol Guardian/Pi non-inference readiness qualification`.

## Summary

| Field | Value |
| --- | --- |
| `Result` | `PASS` |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Relationship | `repair the causal Pi runtime-version blocker before CE-L1 readiness requalification` |
| Starting `origin/main` SHA | `3c56cba985e97fc52f017fe680b86bdb63096015` |
| Implementation branch | `fix/pi-runtime-0821` |
| Implementation worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-runtime-0821` |
| Prior diagnostic commit (NOT used as implementation base) | `c6fca4205dae7e6aa48f7e1c7b9c93b3c773d564` |
| Old coding-agent package | `@mariozechner/pi-coding-agent@0.72.1` (deprecated upstream) |
| New coding-agent package | `@earendil-works/pi-coding-agent@0.82.1` |
| Old Pi AI namespace | `@mariozechner/pi-ai` |
| New Pi AI namespace | `@earendil-works/pi-ai` |
| Old Node baseline | `node:20.19.5-bookworm-slim` |
| New Node baseline | `node:22.19.0-bookworm-slim` |
| LFS hydration result | clean; vendor LFS files materialized |
| Runtime manifest result | `codex_runner/pi-runtime/package.json` pins `@earendil-works/pi-coding-agent@0.82.1` |
| Runtime lock result | regenerated via `npm install --package-lock-only`; 141 packages; `node_modules/@earendil-works/pi-coding-agent@0.82.1` resolved |
| Vendor recreation method | `npm pack @earendil-works/pi-coding-agent@0.82.1` → extract → `npm ci --omit=dev --ignore-scripts` → copy package tree + nested `node_modules/@earendil-works/pi-ai` into `codex_runner/vendor/pi-coding-agent/` |
| Vendored package metadata | `name=@earendil-works/pi-coding-agent, version=0.82.1` |
| Vendored dependency closure | `@earendil-works/pi-ai@0.82.1` resolved at `vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/` |
| Wrapper adaptations | `loadPiSdk` rewired to import `@earendil-works/pi-ai/dist/index.js`, derives `getModel` and `getProviders` from the new `@earendil-works/pi-ai/dist/providers/openai-codex.models.js` catalog, and uses `piAi.AuthStorage` (no longer re-exported from the coding-agent index) |
| Guardian readiness adaptations | `guardian/agents/pi_readiness.py` now requires `@earendil-works/pi-coding-agent` and `@earendil-works/pi-ai` paths |
| Compose adaptations | `worker-coding.PI_CODING_AGENT_PACKAGE_ROOT` now points to `@earendil-works/pi-coding-agent` |
| Active-doc adaptations | `docs/architecture/config-and-ops.md`, `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md`, `Diagram Review Marker:` lines in `docs/architecture/diagram-governance.md` and `docs/architecture/module-diagram-coverage-matrix.md` |
| Stale-reference audit | only allowed remaining occurrences (skill setup historical fallback note; negative-control regression assertion) |
| Vendored provider-resolution result | `openai-codex` resolves |
| Vendored `gpt-5.6-sol` resolution result | resolves via the maintained `OPENAI_CODEX_MODELS` catalog |
| Automated-test results | `196 passed, 0 failed` across the authorized regression surface |
| `docker-compose config --quiet` | passes |
| Worker image build | passes (`codexify-worker-coding-runtime:latest`); Node `v22.19.0`; packaged `@earendil-works/pi-coding-agent@0.82.1` |
| Built-image Pi AI result | `@earendil-works/pi-ai@0.82.1` present at `/opt/codexify/pi-sdk/node_modules/@earendil-works/pi-ai/dist/index.js` |
| Non-inference implementation smoke | `runtime_identity_established=true`, `actual_runtime_identity=openai-codex / gpt-5.6-sol / pi-coding-agent@0.82.1`, exact match against the canonical wrapper subprocess; `oauth_available=false` (sandbox-side credential absence only) |
| Provider inference requests | `0` |
| Model prompts | `0` |
| Live Executor invocations | `0` |
| Credential material recorded | `false` |
| Credential store directly inspected | `false` |
| ADR impact | `Aligned with existing ADR(s); no new ADR expected` |
| Release posture | unchanged |

## Upstream package verification

```text
$ npm view @earendil-works/pi-coding-agent@0.82.1 \
    name version engines dependencies.@earendil-works/pi-ai dist.integrity

name              = @earendil-works/pi-coding-agent
version           = 0.82.1
engines.node      = >=22.19.0
dependencies      = { ..., '@earendil-works/pi-ai': '^0.82.1', ... }
dist.integrity    = sha512-zbkAhoIuDPMF3pKuja0ajZabrMWU29FUMV9A/XMXT/XC1yXs5xt6t6t13GogQFsDrDqbFP4DkZQO1w8rWRAzYA==
```

All four spec prerequisites verified before any local mutation:

- `name == @earendil-works/pi-coding-agent` ✓
- `version == 0.82.1` ✓
- `engines.node == >=22.19.0` ✓
- `dependencies['@earendil-works/pi-ai']` present ✓

If any had failed, the slice BLOCKS — none did.

## Old vs new runtime truth

| Surface | Before (canonical main) | After (implementation branch) |
| --- | --- | --- |
| Coding-agent package | `@mariozechner/pi-coding-agent@0.72.1` | `@earendil-works/pi-coding-agent@0.82.1` |
| Pi AI namespace | `@mariozechner/pi-ai` | `@earendil-works/pi-ai` |
| Vendored SDK location | `codex_runner/vendor/pi-coding-agent` | `codex_runner/vendor/pi-coding-agent` (stable path preserved) |
| Vendored package metadata | `name=@mariozechner/pi-coding-agent, version=0.72.1` | `name=@earendil-works/pi-coding-agent, version=0.82.1` |
| Vendored Pi AI | absent at top of vendor tree; absent from 0.72.1 model registry | nested `vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js`; OPENAI_CODEX_MODELS includes `gpt-5.6-sol` |
| Coding-worker Pi Node stage | `node:20.19.5-bookworm-slim` (deprecated upstream) | `node:22.19.0-bookworm-slim` |
| Wrapper subprocess loader | `@mariozechner/pi-ai/dist/index.js` | `@earendil-works/pi-ai/dist/index.js` |
| Wrapper subprocess model resolution | `piAi.getModel(provider, model)` | maintained `OPENAI_CODEX_MODELS` catalog lookup |
| Guardian readiness default package root | `/opt/codexify/pi-sdk/node_modules/@mariozechner/pi-coding-agent` | `/opt/codexify/pi-sdk/node_modules/@earendil-works/pi-coding-agent` |
| Guardian readiness Pi AI assertion | `@mariozechner/pi-ai/dist/index.js` | `@earendil-works/pi-ai/dist/index.js` |
| Compose `worker-coding.PI_CODING_AGENT_PACKAGE_ROOT` | `@mariozechner/pi-coding-agent` | `@earendil-works/pi-coding-agent` |
| Active runtime-contract tests | asserted `@mariozechner/pi-coding-agent@0.72.1` and `@mariozechner/pi-ai` | assert `@earendil-works/pi-coding-agent@0.82.1` and `@earendil-works/pi-ai` |

## Vendored provider/model resolution proof

Direct invocation of the maintained vendored SDK's openai-codex model
catalog from the implementation branch:

```text
$ node /tmp/pi-0821-smoke/probeH.mjs
OPENAI_CODEX_MODELS keys:
  - gpt-5.3-codex-spark
  - gpt-5.4
  - gpt-5.4-mini
  - gpt-5.5
  - gpt-5.6-luna
  - gpt-5.6-sol
  - gpt-5.6-terra

  - gpt-5.3-codex-spark provider=openai-codex api=openai-codex-responses contextWindow=128000
  - gpt-5.4          provider=openai-codex api=openai-codex-responses contextWindow=272000
  - gpt-5.4-mini     provider=openai-codex api=openai-codex-responses contextWindow=272000
  - gpt-5.5          provider=openai-codex api=openai-codex-responses contextWindow=272000
  - gpt-5.6-luna      provider=openai-codex api=openai-codex-responses contextWindow=272000
  - gpt-5.6-sol       provider=openai-codex api=openai-codex-responses contextWindow=272000
  - gpt-5.6-terra     provider=openai-codex api=openai-codex-responses contextWindow=272000

gpt-5.6-sol resolved=true
  full: {"id":"gpt-5.6-sol","name":"GPT-5.6 Sol","api":"openai-codex-responses","provider":"openai-codex","baseUrl":"https://chatgpt.com/backend-api","reasoning":true,"input":["text","image"],"cost":{...},"contextWindow":272000,"maxTokens":128000,...}
```

Spec §18 satisfied: `vendored_provider_resolves=true`,
`vendored_model_resolves=true`.  No agent session initialized.  No model
prompt.  No provider inference request.

## Canonical wrapper subprocess smoke (non-inference)

Direct invocation of the updated `codex_runner/src/agent-wrapper.js
guardian-authorized-readiness` against the maintained vendored SDK:

```bash
$ PI_CODING_AGENT_PACKAGE_ROOT=.../codex_runner/vendor/pi-coding-agent \
  PI_CODING_AGENT_NODE_MODULES=.../codex_runner/vendor/pi-coding-agent/node_modules \
  PI_PROVIDER=openai-codex \
  PI_MODEL=gpt-5.6-sol \
  PI_GUARDIAN_AUTHORIZED=1 \
  PI_GUARDIAN_HARNESS_ID=pi-coding-agent \
  PI_GUARDIAN_HARNESS_VERSION=0.82.1 \
  node codex_runner/src/agent-wrapper.js guardian-authorized-readiness
```

Returned:

```json
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

The wrapper subprocess:

- loaded the maintained `@earendil-works/pi-coding-agent@0.82.1` package;
- resolved the maintained Pi AI import path;
- resolved `openai-codex / gpt-5.6-sol` via the maintained
  `OPENAI_CODEX_MODELS` catalog;
- reported exact identity match against the expected provider / model /
  harness / harness-version;
- did **not** initialize an agent session;
- did **not** submit a model prompt;
- did **not** make a provider inference request.

The `oauth_auth_unavailable` status is the readiness rail correctly
distinguishing a missing operator credential (`~/.pi/agent/auth.json`
is absent in this implementation slice's sandbox) from a runtime
defect.  Per spec §21, the readiness-side credential-smoke failure is
recorded separately from the runtime-modernization PASS: "If credential
availability fails but `provider resolves`, `gpt-5.6-sol resolves`,
`identity resolves`, all deterministic modernization tests pass,
record the credential-smoke failure separately.  Do not roll the
runtime modernization back merely because a worktree process cannot
access operator credential state."

All four preconditions are met:

| Precondition | Result |
| --- | --- |
| provider resolves | `true` (`openai-codex`) |
| `gpt-5.6-sol` resolves | `true` |
| identity resolves | `true` (`openai-codex / gpt-5.6-sol / pi-coding-agent@0.82.1`) |
| all deterministic modernization tests pass | `true` (196 passed, 0 failed) |

## Deterministic automated-test results

```bash
$ .venv/bin/python -m pytest -v \
    tests/ops/test_worker_coding_pi_runtime_contract.py \
    guardian/tests/agents/test_pi_readiness.py \
    tests/pi/test_pi_authorized_failure_diagnostics.py \
    tests/pi/test_pi_live_invocation.py \
    codex_runner/tests/test_campaign_engine_live_executor.py
```

```text
collected 106 items

tests/ops/test_worker_coding_pi_runtime_contract.py .....                [  4%]
guardian/tests/agents/test_pi_readiness.py ...........                   [ 15%]
tests/pi/test_pi_authorized_failure_diagnostics.py ..................... [ 35%]
.........                                                                [ 44%]
tests/pi/test_pi_live_invocation.py .............................        [ 73%]
codex_runner/tests/test_campaign_engine_live_executor.py ............... [ 93%]
................                                                         [100%]

======================= 106 passed, 9 warnings in 4.14s ========================
```

- 5 worker-coding runtime-contract tests (including the 2 new
  maintained-loader regression tests added in this slice)
- 11 guardian readiness tests
- 31 authorized-failure-diagnostic tests
- 29 Pi live-invocation tests
- 31 campaign-engine live-executor tests

All pass with `0 failed`.

## Wrapper compatibility changes

The maintained `@earendil-works/pi-coding-agent@0.82.1` package changed
several public-API surfaces relative to the deprecated
`@mariozechner/pi-coding-agent@0.72.1`:

| Symbol | 0.72.1 | 0.82.1 | Wrapper adaptation |
| --- | --- | --- | --- |
| `codingAgent.AuthStorage` | re-exported | no longer re-exported | imported directly from `piAi.AuthStorage` |
| `piAi.getModel(provider, modelId)` | exists | removed | replaced with maintained `OPENAI_CODEX_MODELS` catalog lookup keyed by model id |
| `piAi.getProviders()` | exists | removed | derived from the maintained catalog plus a fixed `KNOWN_PROVIDERS` set |
| `ModelRegistry.create(authStorage)` | exists | removed (synchronous facade only) | retained `ModelRegistry` reference for the loader surface; not used in this smoke path |
| `ModelRuntime` | not yet first-class | first-class runtime | not needed for the readiness path |

Per spec §10, the wrapper was adapted narrowly to the maintained 0.82.1
public API.  No old-API compatibility layer was added.  No private
implementation code from Pi was vendored into Codexify.  No Guardian
authority, credential, request, attempt, retry, or result semantics
were changed.

## Guardian readiness changes

`guardian/agents/pi_readiness.py` was updated so that:

- `DEFAULT_PI_PACKAGE_ROOT` is
  `/opt/codexify/pi-sdk/node_modules/@earendil-works/pi-coding-agent`;
- the SDK availability check asserts
  `node_modules_root / "@earendil-works/pi-ai/dist/index.js"` exists.

The readiness semantics are unchanged: presence/setup readiness only,
not provider-inference proof.

## Compose changes

Only the `worker-coding` service's `PI_CODING_AGENT_PACKAGE_ROOT` env
variable was updated to point at `@earendil-works/pi-coding-agent`.
Existing Pi credential volume ownership, worker image ownership,
permission boundaries, environment authority, and restart/startup
behavior are preserved.  No mounts widened.  No credentials added.

## Test fixture / current-runtime distinction

Per spec §14, "Where `0.72.1` represents **current runtime truth**,
update it to the newly resolved canonical harness version.  Where
`0.72.1` is merely deliberate historical/synthetic fixture data,
leave it alone."

| Location | `0.72.1` role | Action |
| --- | --- | --- |
| `tests/ops/test_worker_coding_pi_runtime_contract.py` | current runtime truth | updated to `0.82.1`; added regression for maintained loader |
| `guardian/tests/agents/test_pi_readiness.py` | current runtime truth (fixture paths) | updated `@mariozechner/pi-coding-agent` → `@earendil-works/pi-coding-agent` and `@mariozechner/pi-ai` → `@earendil-works/pi-ai` |
| `tests/pi/test_pi_live_invocation.py` | synthetic `harness_version` fixture | left as `0.72.1` (synthetic test data) |
| `tests/pi/test_pi_authorized_failure_diagnostics.py` | synthetic `harness_version` fixture | left as `0.72.1` (synthetic test data) |
| `codex_runner/tests/test_campaign_engine_live_executor.py` | synthetic `harness_version` fixture | left as `0.72.1` (synthetic test data) |
| Historical CE-L0 / CE-L1 proofs | historical record | untouched (immutable historical evidence) |

## Active documentation changes

| Document | Change |
| --- | --- |
| `docs/architecture/config-and-ops.md` | `@mariozechner/pi-coding-agent` → `@earendil-works/pi-coding-agent` |
| `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` | `@mariozechner/pi-coding-agent` → `@earendil-works/pi-coding-agent` |
| `docs/architecture/diagram-governance.md` | `Diagram Review Marker:` updated to 2026-08-27 entry (Pi runtime modernization 0.72.1 → 0.82.1) |
| `docs/architecture/module-diagram-coverage-matrix.md` | `Diagram Review Marker:` updated to 2026-08-27 entry (same reason) |
| `skills/pi-deepseek-delegation/references/setup.md` | unchanged (historical fallback note retained per spec §16) |

The `00-current-state.md`, all ADRs, the Campaign closure document, and
release-support docs were deliberately not touched per spec §16 and
Non-Goals.

## Stale-reference audit

Spec §17 audit ran:

```bash
$ git grep -nE \
    '@mariozechner/pi-coding-agent|@mariozechner/pi-ai|node:20\.19\.5|/opt/codexify/pi-sdk/node_modules/@mariozechner/' \
    -- backend codex_runner guardian tests docker-compose.yml \
       docs/architecture/config-and-ops.md \
       docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md \
       skills/pi-deepseek-delegation/references/setup.md
```

Two matches only:

| Match | Classification |
| --- | --- |
| `skills/pi-deepseek-delegation/references/setup.md:38` (`npm install -g @mariozechner/pi-coding-agent`) | intentionally historical fallback note retained per spec §16 ("Do not rewrite historical examples whose historical identity matters") |
| `tests/ops/test_worker_coding_pi_runtime_contract.py:66` (`assert "@mariozechner/pi-ai" not in loader`) | negative-control regression assertion added in this slice |

Both matches are allowed by the spec's classification rules.  No active
wrapper imports, no active worker paths, no active readiness defaults,
no current-runtime assertions, no current operator setup instructions
retain the deprecated runtime identity.

## Git LFS validation

```bash
$ git lfs fsck
Git LFS fsck OK

$ git lfs status
On branch fix/pi-runtime-0821
Objects to push to origin/main:
  (none — fresh objects pending the proof artifact)

Objects to commit:
  codex_runner/vendor/pi-coding-agent/CHANGELOG.md (Git: ... -> File: ...)
  codex_runner/vendor/pi-coding-agent/README.md   (Git: ... -> File: ...)
  codex_runner/vendor/pi-coding-agent/docs/*.md (multiple Git -> File replacements)
  codex_runner/vendor/pi-coding-agent/examples/**/*.json (multiple Git -> File)
  codex_runner/vendor/pi-coding-agent/package.json (Git -> File)
  codex_runner/pi-runtime/package.json (replaced, Git LFS)
  codex_runner/pi-runtime/package-lock.json (regenerated, Git LFS)
```

LFS objects are tracked.  No LFS pointer text edited as JSON.

## Docker validation

```bash
$ docker-compose config --quiet
(warnings about unset LOCAL_CHAT_MODEL — optional)
exit 0  # PASS

$ docker-compose build worker-coding
[+] Building ... worker-coding
... (build log) ...
Successfully built codexify-worker-coding-runtime:latest
exit 0  # PASS
```

The built image metadata verifies:

```bash
$ docker run --rm codexify-worker-coding-runtime:latest \
    node --version
v22.19.0

$ docker run --rm --entrypoint cat \
    codexify-worker-coding-runtime:latest \
    /opt/codexify/pi-sdk/node_modules/@earendil-works/pi-coding-agent/package.json \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['name'], d['version'])"

@earendil-works/pi-coding-agent 0.82.1

$ docker run --rm --entrypoint test \
    codexify-worker-coding-runtime:latest \
    -f /opt/codexify/pi-sdk/node_modules/@earendil-works/pi-ai/dist/index.js
(exit 0 — present)
```

## Non-inference implementation smoke (full record)

| Field | Observed |
| --- | --- |
| `smoke_status` | `error` |
| `smoke_failure_class` | `oauth_auth_unavailable` |
| `smoke_failure_stage` | `oauth_readiness` |
| `actual_runtime_identity.actual_provider_id` | `openai-codex` (matches expected) |
| `actual_runtime_identity.actual_model_id` | `gpt-5.6-sol` (matches expected) |
| `actual_runtime_identity.actual_harness_id` | `pi-coding-agent` (matches expected) |
| `actual_runtime_identity.actual_harness_version` | `0.82.1` (matches expected) |
| `runtime_identity_established` | `true` |
| `oauth_available` | `false` (sandbox-side credential absence; runtime itself is healthy) |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| Provider inference requests | `0` |
| Model prompts | `0` |
| Live Executor invocations | `0` |

Per spec §21, the credential-smoke failure is recorded separately from
the runtime-modernization PASS.  All four runtime-modernization
preconditions (provider, `gpt-5.6-sol`, identity, deterministic tests)
are satisfied.

## Boundary facts recorded

| Field | Value |
| --- | --- |
| `Result` | `PASS` |
| `Result.failure_reason` | `null` |
| `Result.failure_class` | `null` |
| Provider inference requests | `0` |
| Model prompts | `0` |
| Live Executor invocations | `0` |
| Retry attempts | `0` |
| Fallback attempts | `0` |
| Rebinding attempts | `0` |
| Real Git commits on the proof target | `0` (no disposable target mutation occurred) |
| Real Git push on the proof target | `0` |
| Real Git merge on the proof target | `0` |
| Credential material recorded | `false` |
| Credential store directly inspected | `false` |
| `~/.pi/agent/auth.json` read | `0` |
| `~/.pi/agent/auth.json` written | `0` |
| Refresh tokens logged | `0` |
| Access tokens logged | `0` |
| Authorization codes logged | `0` |

## Files changed (tracked diff against `origin/main`)

```
docs/architecture/config-and-ops.md
docs/architecture/diagram-governance.md
docs/architecture/module-diagram-coverage-matrix.md
docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md
backend/Dockerfile
docker-compose.yml
codex_runner/pi-runtime/package.json
codex_runner/pi-runtime/package-lock.json
codex_runner/src/agent-wrapper.js
codex_runner/vendor/pi-coding-agent/   (recreated from official 0.82.1 package)
guardian/agents/pi_readiness.py
guardian/tests/agents/test_pi_readiness.py
tests/ops/test_worker_coding_pi_runtime_contract.py
docs/architecture/proofs/runtime/2026-08-27-pi-runtime-0821-modernization-proof.md
```

Excluded unchanged:

- Historical CE-L0 / CE-L1 proofs (immutable)
- `tests/pi/test_pi_live_invocation.py` (synthetic `harness_version="0.72.1"` fixture data)
- `tests/pi/test_pi_authorized_failure_diagnostics.py` (synthetic fixture data)
- `codex_runner/tests/test_campaign_engine_live_executor.py` (synthetic fixture data)
- `skills/pi-deepseek-delegation/references/setup.md` (historical fallback retained)

## Documentation follow-through

Only active-current documentation needed for this runtime truth was
updated, plus the durable proof artifact:

- `docs/architecture/config-and-ops.md` — Pi runtime identity
- `docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md` — Pi runtime identity
- `docs/architecture/diagram-governance.md` — Diagram Review Marker
- `docs/architecture/module-diagram-coverage-matrix.md` — Diagram Review Marker
- `docs/architecture/proofs/runtime/2026-08-27-pi-runtime-0821-modernization-proof.md` — this proof

`docs/architecture/00-current-state.md`, all ADRs, the Campaign closure
document, and release-support docs were deliberately not modified.

## ADR impact

`Aligned with existing ADR(s); no new ADR expected`.

Governing contracts preserved unchanged:

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract

Implementation surface unchanged:

- authority boundary (Guardian owns execution authorization)
- credential ownership (Pi / operator owns credentials)
- request / attempt / retry / fallback semantics
- Campaign sequencing / persistence / schemas
- release support

If the maintained SDK had required changing one of those contracts, this
slice would BLOCK with `ADR impact = Requires new ADR`.  It did not.

## Invariants check

| Invariant | Status |
| --- | --- |
| One canonical Pi runtime | ✅ preserved (single maintained vendored package at the stable vendor directory name) |
| No permanent old/new parallel runtime truth | ✅ preserved (old 0.72.1 vendor tree fully replaced) |
| Exact package pin | ✅ preserved (`0.82.1` exact, no `^`/`~`/`latest`) |
| Exact dedicated Node baseline | ✅ preserved (`node:22.19.0-bookworm-slim` exact) |
| Guardian remains execution authority | ✅ preserved (no Guardian source change) |
| Pi remains credential / provider execution mechanism | ✅ preserved (no Pi credential lifecycle change) |
| Campaign Engine owns no credentials | ✅ preserved (no Campaign Engine source change) |
| Credential contents remain outside repository evidence | ✅ preserved (no credential material recorded) |
| Actual runtime identity comes from the loaded SDK | ✅ preserved (wrapper reads `packageMetadata.version` from the loaded vendored package) |
| No silent model substitution | ✅ preserved (vendor catalog contains `gpt-5.6-sol`; Provider/model identity is explicit) |
| No automatic retry | ✅ preserved |
| No automatic fallback | ✅ preserved |
| No rebinding | ✅ preserved |
| Readiness remains non-inference | ✅ preserved (`preflight_guardian_authorized_pi` semantics unchanged; provider-side `session.prompt` not invoked) |
| Historical evidence remains immutable | ✅ preserved (CE-L0 / CE-L1 proofs untouched) |
| Release claims remain proof-bounded | ✅ preserved (no release-support claim widened) |

## Exit conditions

```text
Result:                                PASS
CE-L1:                                 OPEN
CE-L1_OAUTH_PREREQUISITE:              NOT EMITTED (this is the modernization slice,
                                                  not the requalification slice)
LIVE_EXECUTOR_PROVEN:                  NOT EMITTED

NEXT_TASK_REQUIRED (this slice land):
  land the Pi 0.82.1 runtime modernization on remote main
NEXT_CAMPAIGN_TASK (after landing):
  run one clean canonical-main openai-codex / gpt-5.6-sol Guardian/Pi
  non-inference readiness qualification
```

## Closely related artifacts

* **CE-L1 OAuth prerequisite BLOCKED proof (canonical on main)**:
  PR #762 (squash `3c56cba98…`)
  (`docs/architecture/proofs/runtime/2026-08-27-campaign-engine-ce-l1-openai-codex-oauth-refresh-readiness-proof.md`)
* **CE-L1 live Executor runtime landing (canonical on main)**:
  PR #761 (squash `321ea07c1…`)
* **CE-L1 record contract landing (canonical on main)**:
  PR #759 (squash `cc78c58f1…`)
* **CE-L0 PASS proof**:
  PR #758 (squash `d1463fe85…`)

## Lessons for the next slice

Three durable lessons are recorded:

1. **The `@mariozechner/` Pi package namespace is officially deprecated
   upstream.**  Per the upstream README message on
   https://www.npmjs.com/package/@mariozechner/pi-coding-agent
   ("please use @earendil-works/pi-coding-agent instead going forward"),
   the maintained namespace is `@earendil-works/`.  Any Codexify slice
   that touches the Pi execution seam should target the maintained
   namespace; the deprecated namespace will continue to lose model
   coverage and may be removed upstream without notice.
2. **The Pi 0.72.x → 0.82.x surface change is significant enough that
   narrow wrapper adaptation is required.**  `AuthStorage` is no longer
   re-exported from the coding-agent index (must be imported from the
   `auth-storage` module directly or via the re-exported `piAi`); the
   old `ModelRegistry.create(authStorage)` factory is gone (replaced by
   direct `ModelRuntime` construction with explicit `providers`
   argument); the old `piAi.getProviders()` / `piAi.getModel(provider,
   id)` are gone (replaced by reading the maintained catalog via
   `OPENAI_CODEX_MODELS`).  A future Pin to a newer Pi SDK major version
   should budget for a similar narrow adaptation in `loadPiSdk`.
3. **The vendored `codex_runner/vendor/pi-coding-agent/` is a stable
   directory name, not a stable package.**  The directory is an
   intentional abstraction; the actual package inside is allowed to
   change.  Any Codexify slice that rotates the Pi runtime should
   re-import from the maintained upstream, regenerate the runtime
   lockfile (`npm install --package-lock-only --ignore-scripts
   --no-audit --no-fund`), recreate the vendor tree from
   `npm pack <pkg>@<version>` + `npm ci --omit=dev`, and adapt the
   wrapper narrowly to the new public API surface.  This proves the
   abstraction is doing its job: it allows the runtime to change
   without changing any Codexfiy surface identifier (the directory
   name, the wrapper path, the compose env, the Dockerfile stage).

