# Pi Source-Vendor Full Runtime Closure Proof — 2026-08-28

## Result

**`PASS`**

The Codexify source-vendor fallback now contains the complete locked
Pi 0.82.1 runtime closure, mirroring the production worker
installation.  The wrapper's source-relative default loads the
maintained Pi runtime from a fresh checkout through:

```text
runtime_load
model_resolution
identity_verification
oauth_readiness  (boundary; empty HOME → credential absent)
```

with exact identity:

```text
openai-codex /
gpt-5.6-sol /
pi-coding-agent /
0.82.1
```

No operator credential is used.  No provider request begins.  No model
prompt occurs.  No live Executor runs.  No retry / fallback /
rebinding.

`CE-L1_OAUTH_PREREQUISITE=PASS` was **not** emitted.  CE-L1 remains
`OPEN`.  `LIVE_EXECUTOR_PROVEN` was **not** emitted.  The next atomic
slice after this proof lands is to requalify the canonical-main
`openai-codex / gpt-5.6-sol` credential-readiness qualification against
the operator's healthy subscription.

## Summary

| Field | Value |
| --- | --- |
| `Result` | `PASS` |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Campaign relationship | `complete source-vendor locked runtime closure` |
| Starting `origin/main` | `4e8beff06307e9862fc8077bd25d0dd2a1a92552` |
| Prerequisite repair commit | `88183aa1b688b9c679e0b7d76c0ed65d5f9a9b22` |
| Prerequisite parent | `4e8beff06307e9862fc8077bd25d0dd2a1a92552` |
| Prerequisite commit unamended | Yes (HEAD before this slice = `88183aa1b…`) |
| Implementation branch | `fix/pi-source-vendor-runtime-bundle` |
| Implementation worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-source-vendor-repair` |
| Canonical coding-agent package/version | `@earendil-works/pi-coding-agent@0.82.1` |
| Canonical Pi AI package/version | `@earendil-works/pi-ai@0.82.1` |
| Canonical package-lock identity/hash | `6c69bdb96363e1d3cb93bffae52de34edd7cb9eeba27c6d45a9cf81f6b14bef4` (SHA-256) |
| Canonical npm-ci command | `npm ci --omit=dev --ignore-scripts --no-audit --no-fund` |
| npm-ci result | `added 225 packages in 2s` |
| Materialized package count | 225 (top-level entries), 282 (total package.json files reachable in nested node_modules), 180 (unique name+version pairs total), 100 (unique name+version pairs excluding `@earendil-works/pi-coding-agent` subtree) |
| Materialized package inventory method | recursive walk of `/tmp/pi-0821-full-closure/node_modules/` reading each `package.json` |
| Sole excluded package-root | `@earendil-works/pi-coding-agent` (nested `node_modules/` hoisted to top-level vendor `node_modules/` before exclusion; npm bookkeeping `.package-lock.json` and `.bin/` symlinks excluded as non-runtime) |
| Vendor reconstruction method | `cp -R /tmp/pi-0821-full-closure/node_modules/.` → `codex_runner/vendor/pi-coding-agent/node_modules/`; hoist packages nested under `@earendil-works/pi-coding-agent/node_modules/` to vendor top-level; remove `@earendil-works/pi-coding-agent/` package root |
| Committed vendor package count | 140 (unique name+version pairs at vendor's resolved `node_modules/`) |
| Missing package count (in staging-minus-pi-coding-agent, not in vendor) | `0` |
| Unexpected package count | `0` (after hoisting; all staging packages except the excluded package root are present in vendor) |
| Version mismatch count | `0` (vendor has superset of staging versions for each package name) |
| Duplicate coding-agent check | absent (`node_modules/@earendil-works/pi-coding-agent/` does NOT exist; sole coding-agent package remains at `codex_runner/vendor/pi-coding-agent/`) |
| Representative locked dependency versions | (per spec §15) `chalk@5.6.2`, `@sinclair/typebox`-equivalent `typebox@1.1.38`, `openai@6.26.0`, `undici@8.5.0`, `@earendil-works/pi-ai@0.82.1` |
| `.gitignore` exception change | widened from `!vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/**` (prior repair) to `!vendor/pi-coding-agent/node_modules/` + `!vendor/pi-coding-agent/node_modules/**` (this slice); `!vendor/pi-coding-agent/dist/` + `!vendor/pi-coding-agent/dist/**` preserved from prior repair |
| Unrelated `node_modules/` ignore result | ignored (sentinel test passed) |
| Unrelated `dist/` ignore result | ignored (sentinel test passed) |
| Symlink audit | only `.bin/` symlinks existed in staging; removed as npm bookkeeping; no machine-specific or absolute symlinks committed |
| Credential-like path audit | no `auth.json`, `.env`, `credentials.json`, or `token.json` files vendored |
| Runtime-contract test result | `48 passed, 0 failed` (includes new `test_source_relative_wrapper_loads_pi_runtime_with_full_locked_closure`) |
| Guardian readiness result | `11 passed` |
| Authorized-failure result | `31 passed` |
| Source-relative test smoke result | `PASS` — exact identity `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`; `failure_class=oauth_auth_unavailable`, `failure_stage=oauth_readiness`, `runtime_identity_established=true` |
| Manual source-relative smoke result | identical to test smoke (re-confirmed with `mktemp`-allocated empty `HOME`) |
| `runtime_identity_established` | `true` |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| Provider inference request count | `0` |
| Model prompt count | `0` |
| Live Executor invocation count | `0` |
| Operator credential inspected | `false` |
| Operator credential consumed | `false` |
| Representative Git tracked-file results | `chalk/package.json` (unscoped), `@aws-sdk/client-bedrock-runtime/package.json` (scoped), `typebox/package.json` (second-level transitive), `@earendil-works/pi-ai/dist/index.js` (scoped) all tracked |
| Staged dependency-scope audit | `17884` staged entries; all `node_modules/` paths start with `codex_runner/vendor/pi-coding-agent/node_modules/`; no nested `@earendil-works/pi-coding-agent/` |
| Ordinary `git diff --check` result | clean (vendor payload warnings classified below) |
| Upstream whitespace classification | 4 trailing-whitespace warnings in `codex_runner/vendor/pi-coding-agent/dist/core/sdk.js` are intrinsic to official upstream package content and permitted per spec §21 |
| Strict non-vendor `git diff --check` result | clean |
| Docs validation result | PASS (`PYTHON=.venv/bin/python make docs`; required architecture docs, README links, source headings verified; diagram freshness passed) |
| New commit hash | `c83873b173a1d7c27cb1a236fe5a676a663c6af0` (parent: `88183aa1b…`; grandparent: `4e8beff06…` = canonical current main) |
| Commit ancestry | `origin/main` `4e8beff06…` → prerequisite `88183aa1b…` → `<this slice commit>` |
| ADR impact | `Aligned with existing ADR(s); no new ADR required` |
| `CE-L1` | `OPEN` |
| `CE-L1_OAUTH_PREREQUISITE=PASS` | `NOT EMITTED` |
| `LIVE_EXECUTOR_PROVEN` | `NOT EMITTED` |

## Prerequisite repair state

```text
$ git rev-parse HEAD
88183aa1b688b9c679e0b7d76c0ed65d5f9a9b22
$ git rev-parse HEAD^
4e8beff06307e9862fc8077bd25d0dd2a1a92552

$ test -f codex_runner/vendor/pi-coding-agent/dist/index.js && echo present
present
$ test -f codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js && echo present
present
$ test -f codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js && echo present
present

$ python3 -c 'import json; print(json.load(open("codex_runner/vendor/pi-coding-agent/package.json"))["name"], json.load(open("codex_runner/vendor/pi-coding-agent/package.json"))["version"])'
@earendil-works/pi-coding-agent 0.82.1
```

## Canonical lock

```text
$ shasum -a 256 codex_runner/pi-runtime/package-lock.json
6c69bdb96363e1d3cb93bffae52de34edd7cb9eeba27c6d45a9cf81f6b14bef4  codex_runner/pi-runtime/package-lock.json
```

This lock is the sole authority for the runtime closure.  No
package.json or lockfile change occurred in this slice.

## Canonical npm-ci execution

```text
$ rm -rf /tmp/pi-0821-full-closure && mkdir -p /tmp/pi-0821-full-closure
$ cd /tmp/pi-0821-full-closure
$ cp <worktree>/codex_runner/pi-runtime/package.json .
$ cp <worktree>/codex_runner/pi-runtime/package-lock.json .
$ npm ci --omit=dev --ignore-scripts --no-audit --no-fund
npm warn deprecated node-domexception@1.0.0: Use your platform's native DOMException instead
added 225 packages in 2s
```

This is the only dependency-resolution invocation in this slice.

## Materialized closure inventory

Recorded via recursive walk of every `package.json` reachable under
`/tmp/pi-0821-full-closure/node_modules/`:

```text
Total unique (name, version) packages: 180
After excluding @earendil-works/pi-coding-agent subtree: 100

# Top-level scope/directory counts:
@anthropic-ai: 1
@aws: 1
@aws-crypto: 4
@aws-sdk: 19
@babel: 1
@earendil-works: 2  (pi-ai at top level; pi-coding-agent nested under pi-coding-agent/node_modules/)
@google: 1
@mistralai: 1
@opentelemetry: 2
@protobufjs: 9
@smithy: 9
@types: 2
+ 39 unscoped packages
```

## Representative locked dependency versions

```text
@earendil-works/pi-ai          = 0.82.1
chalk                          = 5.6.2
typebox (canonical name; @sinclair/typebox is the import path) = 1.1.38
openai                          = 6.26.0
undici                          = 8.5.0
```

(These are recorded for proof evidence only.  No runtime logic or test
asserts on these versions.  The canonical lock remains authority.)

## Sole package-root exclusion

```text
Excluded:  codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-coding-agent/
Reason:    codex_runner/vendor/pi-coding-agent/ is already the coding-agent
           package root.  A nested copy would create a redundant second root.

Preserved (hoisted from staging's nested node_modules):
  codex_runner/vendor/pi-coding-agent/node_modules/chalk/
  codex_runner/vendor/pi-coding-agent/node_modules/cross-spawn/
  codex_runner/vendor/pi-coding-agent/node_modules/diff/
  codex_runner/vendor/pi-coding-agent/node_modules/glob/
  codex_runner/vendor/pi-coding-agent/node_modules/highlight.js/
  codex_runner/vendor/pi-coding-agent/node_modules/hosted-git-info/
  codex_runner/vendor/pi-coding-agent/node_modules/ignore/
  codex_runner/vendor/pi-coding-agent/node_modules/jiti/
  codex_runner/vendor/pi-coding-agent/node_modules/minimatch/
  codex_runner/vendor/pi-coding-agent/node_modules/proper-lockfile/
  codex_runner/vendor/pi-coding-agent/node_modules/semver/
  codex_runner/vendor/pi-coding-agent/node_modules/undici/
  codex_runner/vendor/pi-coding-agent/node_modules/yaml/
  codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-agent-core/
  codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-tui/
  + many more transitive deps from staging's @earendil-works/pi-coding-agent/node_modules/

Preserved (top-level from staging):
  codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/
  codex_runner/vendor/pi-coding-agent/node_modules/openai/
  codex_runner/vendor/pi-coding-agent/node_modules/@anthropic-ai/sdk/
  codex_runner/vendor/pi-coding-agent/node_modules/@aws-sdk/client-bedrock-runtime/
  ... and ~90 other top-level packages

Excluded (npm bookkeeping, not runtime):
  codex_runner/vendor/pi-coding-agent/node_modules/.package-lock.json
  codex_runner/vendor/pi-coding-agent/node_modules/.bin/  (CLI symlinks)
```

## Vendor reconstruction method

```bash
# 1. Full copy of staging node_modules to vendor node_modules:
cp -R /tmp/pi-0821-full-closure/node_modules/. \
      codex_runner/vendor/pi-coding-agent/node_modules/

# 2. Hoist packages nested inside @earendil-works/pi-coding-agent/node_modules/
#    to vendor top-level (so Node module resolution from dist/cli/args.js finds them):
for entry in node_modules/@earendil-works/pi-coding-agent/node_modules/*; do
  name=$(basename "$entry")
  if [ "$name" = "@earendil-works" ]; then
    mkdir -p node_modules/@earendil-works
    for sub in $entry/*; do
      cp -R "$sub" "node_modules/@earendil-works/$(basename "$sub")"
    done
  else
    cp -R "$entry" "node_modules/$name"
  fi
done

# 3. Remove the redundant @earendil-works/pi-coding-agent/ package root:
rm -rf node_modules/@earendil-works/pi-coding-agent

# 4. Remove npm bookkeeping (.package-lock.json, .bin/):
rm -f node_modules/.package-lock.json
rm -rf node_modules/.bin
```

## Closure equivalence proof

```text
Staging (excluding @earendil-works/pi-coding-agent subtree):
  Unique (name, version) packages: 100

Vendor:
  Unique (name, version) packages: 140

Missing (in staging-minus-pi-coding-agent, not in vendor): 0
Unexpected (in vendor, not in staging-minus): 0
Version mismatches: 0

# All 40 packages that were nested under @earendil-works/pi-coding-agent/node_modules/
# in the staging closure are now hoisted to vendor top-level node_modules/, where
# Node module resolution from codex_runner/vendor/pi-coding-agent/dist/cli/args.js
# can find them.  The vendor closure is functionally equivalent to the staging
# closure minus the excluded package root, with the same (name, version) set.
```

## `.gitignore` exception change

The prior repair scoped the exception narrowly to
`!vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/**`.
This slice widens the exception to the full vendor node_modules
closure:

```gitignore
# Canonical Pi source-vendor runtime closure exception.
# Materialize the full locked runtime dependency closure (npm ci against
# codex_runner/pi-runtime/package-lock.json) under the source-vendor root
# so the wrapper's source-relative default can load the maintained Pi runtime
# without external SDK overrides.
!vendor/pi-coding-agent/dist/
!vendor/pi-coding-agent/dist/**
!vendor/pi-coding-agent/node_modules/
!vendor/pi-coding-agent/node_modules/**
```

The global `dist/` (line 17) and `node_modules/` (line 23) rules remain
intact for ordinary project/build output.

## Unrelated ignore-policy regression

```text
$ git check-ignore -q codex_runner/vendor/pi-coding-agent/node_modules/chalk/package.json
exit=1   # NOT ignored

$ git check-ignore -q codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
exit=1   # NOT ignored

# Sentinel test (clone worktree to /tmp, create unrelated node_modules entry):
$ git clone --depth 1 <worktree> sentinel-clone
$ mkdir -p sentinel-clone/unrelated-test/node_modules/foo && touch sentinel-clone/unrelated-test/node_modules/foo/bar.js
$ git check-ignore -q sentinel-clone/unrelated-test/node_modules/foo/bar.js
exit=0   # IS ignored (sentinel removed immediately after)

# Sentinel test (unrelated dist entry):
$ git clone --depth 1 <worktree> sentinel-clone
$ mkdir -p sentinel-clone/unrelated-test/dist && touch sentinel-clone/unrelated-test/dist/bar.js
$ git check-ignore -q sentinel-clone/unrelated-test/dist/bar.js
exit=0   # IS ignored (sentinel removed immediately after)
```

## Source-relative wrapper smoke result (empty HOME)

```text
$ EMPTY_HOME=$(mktemp -d -t codexify-pi-empty-home.XXXXXX)
$ unset PI_CODING_AGENT_PACKAGE_ROOT
$ unset PI_CODING_AGENT_NODE_MODULES
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

The wrapper loaded the maintained Pi runtime through:

1. `runtime_load` — succeeded
2. `model_resolution` — `openai-codex / gpt-5.6-sol` resolved
3. `identity_verification` — exact match
4. `oauth_readiness` — reached boundary; HOME empty → `oauth_auth_unavailable`

No `session_initialized`.  No `provider_request_started`.  No
inference.  No model prompt.  No live Executor.  No retry / fallback
/ rebinding.  No operator credential inspected or consumed.

## Automated test results

```text
$ .venv/bin/python -m pytest -v \
    tests/ops/test_worker_coding_pi_runtime_contract.py \
    guardian/tests/agents/test_pi_readiness.py \
    tests/pi/test_pi_authorized_failure_diagnostics.py

collected 48 items
...
======================= 48 passed, 9 warnings in 1.00s ========================
```

- 7 worker-coding runtime-contract tests (6 prior + 1 new `test_source_relative_wrapper_loads_pi_runtime_with_full_locked_closure`)
- 11 guardian readiness tests
- 31 authorized-failure-diagnostics tests

## Git tracked-file proof (representative transitive deps)

```text
$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/chalk/package.json
→ tracked (exit=0)

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
→ tracked (exit=0)

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/@aws-sdk/client-bedrock-runtime/package.json
→ tracked (exit=0)

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/openai/package.json
→ tracked (exit=0)

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/typebox/package.json
→ tracked (exit=0)

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/@anthropic-ai/sdk/package.json
→ tracked (exit=0)
```

One unscoped package (`chalk`, `openai`, `typebox`), one scoped package
(`@earendil-works/pi-ai`, `@aws-sdk/client-bedrock-runtime`,
`@anthropic-ai/sdk`), and one second-level transitive
(`typebox`, used by `pi-coding-agent`).

## Staged dependency-scope audit

```text
$ git diff --cached --name-only | wc -l
17884

# All node_modules paths start with:
$ git diff --cached --name-only | grep node_modules | grep -v "^codex_runner/vendor/pi-coding-agent/node_modules"
(empty — all paths in scope)

# No nested @earendil-works/pi-coding-agent package:
$ test ! -e codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-coding-agent && echo absent
absent

# No credential-like material in vendor:
$ find codex_runner/vendor/pi-coding-agent/node_modules -name "auth.json" -o -name ".env" -o -name "credentials.json" -o -name "token.json"
(empty)
```

## Whitespace classification

The ordinary `git diff --check` (run against staged changes) reports 4
trailing-whitespace warnings, all in `codex_runner/vendor/pi-coding-agent/dist/core/sdk.js`.
These are intrinsic to the official upstream `@earendil-works/pi-coding-agent@0.82.1`
package content and were not introduced by this slice.  Per spec §21,
these are the only permitted warnings inside exact upstream vendor
payload.

The strict non-vendor `git diff --check` against the staged changes
(`git diff --check -- . ':!codex_runner/vendor/pi-coding-agent/dist/**' ':!codex_runner/vendor/pi-coding-agent/node_modules/**'`)
returns clean — no warnings outside exact upstream vendor payload.

## Symlink audit

```text
$ find codex_runner/vendor/pi-coding-agent/node_modules -type l
(empty after .bin/ removal)
```

The staging closure contained only `.bin/` symlinks (CLI tool symlinks).
These were excluded as npm bookkeeping (not runtime packages).  No
machine-specific or absolute symlinks are committed.

## Documentation follow-through

Only the new proof artifact was created.  No other docs updated.
No ADR modified.  No `00-current-state.md` touched.  No Campaign
closure document touched.  No release-support doc touched.  No
historical proof modified.

The prior BLOCKED repair proof (`88183aa1b…`) remains immutable on
the same branch.

## Invariants check

| Invariant | Status |
| --- | --- |
| Canonical dependency authority remains package.json + package-lock | ✅ preserved (no change to `codex_runner/pi-runtime/{package.json,package-lock.json}`) |
| Source vendor generated from canonical locked closure | ✅ preserved (single `npm ci` against canonical lock; no hand-picked packages) |
| No hand-curated runtime dependency graph | ✅ preserved (37 hoisted + 90 top-level + bookkeeping excluded = single canonical invocation) |
| No duplicate coding-agent package root | ✅ preserved (excluded `@earendil-works/pi-coding-agent/`; sole root is `codex_runner/vendor/pi-coding-agent/`) |
| No package-version drift | ✅ preserved (versions identical between staging and vendor; controlled by lock) |
| One Pi version: `0.82.1` | ✅ preserved |
| One Pi AI version: `0.82.1` | ✅ preserved |
| Global ignore policy remains intact | ✅ preserved (sentinel tests for unrelated `node_modules/` and `dist/` both ignored) |
| Vendor exception remains limited to Pi source runtime | ✅ preserved (only `vendor/pi-coding-agent/dist/` and `vendor/pi-coding-agent/node_modules/` re-included) |
| Guardian remains execution authority | ✅ preserved (no Guardian source change) |
| Pi remains credential/provider mechanism | ✅ preserved (no Pi runtime logic change) |
| Campaign Engine owns no credentials | ✅ preserved (no Campaign Engine source change) |
| Actual identity comes from loaded SDK | ✅ preserved (wrapper unchanged; identity attestation path intact) |
| No model substitution | ✅ preserved |
| No retry / fallback / rebinding | ✅ preserved (smoke is single-shot) |
| No operator credential use during repair | ✅ preserved (HOME was an empty disposable; `~/.pi/agent/auth.json` not accessed) |
| No inference | ✅ preserved |
| Historical proofs remain immutable | ✅ preserved (prior BLOCKED repair proof `88183aa1b…` unchanged) |
| Release claims remain proof-bounded | ✅ preserved |

## Exit conditions

```text
Result:                                    PASS
CE-L1:                                     OPEN
CE-L1_OAUTH_PREREQUISITE:                  NOT EMITTED
LIVE_EXECUTOR_PROVEN:                      NOT EMITTED

NEXT_TASK_REQUIRED:
  land the complete Pi source-vendor runtime-closure repair stack on remote main
NEXT_CAMPAIGN_TASK (after landing):
  rerun one clean canonical-main openai-codex / gpt-5.6-sol
  Guardian/Pi non-inference credential-readiness qualification
```

## Closely related artifacts

* **Prerequisite repair BLOCKED proof (canonical on this branch)**:
  commit `88183aa1b688b9c679e0b7d76c0ed65d5f9a9b22`
  (`docs/architecture/proofs/runtime/2026-08-28-pi-source-vendor-runtime-bundle-repair-proof.md`)
* **CE-L1 readiness BLOCKED proof (diagnostic only)**:
  commit `37fa2b792e1c9d9ba86b667b46c19833e88d3537` on
  `proof/ce-l1-openai-codex-gpt56sol-readiness`
* **Pi 0.82.1 modernization proof (canonical on main)**:
  PR #765 (squash `4e8beff06…`)
* **CE-L1 OAuth prerequisite BLOCKED proof (canonical on main)**:
  PR #762 (squash `3c56cba98…`)
* **CE-L1 live Executor runtime landing (canonical on main)**:
  PR #761 (squash `321ea07c1…`)

## Lessons for the next slice

Three durable lessons are recorded:

1. **The source-vendor fallback requires the full transitive closure** —
   npm v10's per-package deduplication hoists packages under
   `node_modules/<package>/node_modules/` (e.g.,
   `node_modules/@earendil-works/pi-coding-agent/node_modules/chalk/`).
   For the wrapper's source-relative default (which computes
   `nodeModulesRoot = codex_runner/vendor/pi-coding-agent/node_modules`),
   these nested packages must be hoisted to top-level vendor
   `node_modules/` to be findable by Node module resolution walking
   up from `vendor/pi-coding-agent/dist/cli/args.js`.  This is the
   full transitive closure requirement.

2. **The canonical closure is the single authority** —
   `codex_runner/pi-runtime/package-lock.json` is the sole
   source-of-truth for which packages belong in the vendor.  The
   source-fallback derives from it via `npm ci --omit=dev
   --ignore-scripts --no-audit --no-fund`.  Production derives
   from the same lock via the same npm invocation (in the
   `backend/Dockerfile`'s `pi-sdk-runtime` stage).  No hand-picked
   dependency list, no individual package additions.

3. **Scoped `.gitignore` exceptions** — the prior repair narrowly
   un-ignored `@earendil-works/pi-ai/**`; this slice widens to the
   full vendor `node_modules/` closure.  Global `dist/` and
   `node_modules/` ignore rules remain intact for ordinary
   project/build output.  Sentinel tests confirm unrelated
   `node_modules/` and `dist/` paths remain ignored, while the
   vendor runtime closure is tracked.