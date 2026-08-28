# Pi Source-Vendor Runtime Bundle Repair Proof — 2026-08-28

## Result

**`BLOCKED`** (bounded)

The source-vendored Pi 0.82.1 runtime payload
(`codex_runner/vendor/pi-coding-agent/dist/**` and the nested
maintained `codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/**`)
has been restored exactly as the passing modernization
implementation documented.

The runtime-contract regression test
(`test_canonical_pi_source_vendor_runtime_bundle_is_complete`)
now permanently fails CI if the source-vendor bundle is metadata-only.

The empty-HOME source-relative wrapper smoke remains BLOCKED at
`runtime_load` because the source-vendored tree now ships only the
maintained Pi AI runtime and not the **transitive deps**
(`chalk`, `@sinclair/typebox`, `cross-spawn`, `diff`, `glob`,
`highlight.js`, `hosted-git-info`, `ignore`, `jiti`, `minimatch`,
`proper-lockfile`, `semver`, `undici`, `yaml`, `@anthropic-ai/sdk`,
`@aws-sdk/client-bedrock-runtime`, `@google/genai`,
`@mistralai/mistralai`, `@opentelemetry/api`,
`@silvia-odwyer/photon-node`, `@smithy/node-http-handler`,
`http-proxy-agent`, `https-proxy-agent`, `openai`, `partial-json`)
that `@earendil-works/pi-coding-agent@0.82.1` and
`@earendil-works/pi-ai@0.82.1` actually import at runtime.

The **production** Pi 0.82.1 worker is **unaffected**: its
`pi-sdk-runtime` Docker stage already populates the full
225-package closure via `npm ci` against the canonical
`codex_runner/pi-runtime/package-lock.json`.  This slice only
restored the source-vendored fallback that local source-only
executions (CI, local dev, source-only read-only smoke) actually
depend on.

Per spec §11, the BLOCKED outcome is valid and the smallest next
seam is reported below.

`CE-L1_OAUTH_PREREQUISITE=PASS` was **not** emitted.  CE-L1
remains `OPEN`.  `LIVE_EXECUTOR_PROVEN` was **not** emitted.

The next atomic task is:

> extend the source-vendor fallback to include the canonical
> locked transitive closure (the 224 non-`@earendil-works` packages
> that `npm ci` against `codex_runner/pi-runtime/package-lock.json`
> populates today), so that the source-relative wrapper default can
> load the maintained Pi runtime from a fresh checkout.

## Summary

| Field | Value |
| --- | --- |
| `Result` | `BLOCKED` (bounded; runtime-load seam remains) |
| Campaign | `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE` |
| Gate | `CE-L1` |
| Campaign relationship | `repair source-vendor runtime integrity` |
| Starting `origin/main` | `4e8beff06307e9862fc8077bd25d0dd2a1a92552` |
| Repair branch | `fix/pi-source-vendor-runtime-bundle` |
| Repair worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-pi-source-vendor-repair` |
| Historical BLOCKED readiness proof commit | `37fa2b792e1c9d9ba86b667b46c19833e88d3537` (on `proof/ce-l1-openai-codex-gpt56sol-readiness`) |
| Confirmation historical proof not used as base | | Yes — repair branch was created fresh from `origin/main` `4e8beff06…`; the local proof branch was not used as the implementation base |
| Pre-repair `dist/index.js` presence | `false` |
| Pre-repair nested Pi AI runtime presence | `false` |
| Causal `.gitignore` rules | `codex_runner/.gitignore` line 38: `vendor/pi-coding-agent/dist`; line 39: `vendor/pi-coding-agent/node_modules` |
| Canonical coding-agent package/version | `@earendil-works/pi-coding-agent@0.82.1` |
| Canonical Pi AI package/version | `@earendil-works/pi-ai@0.82.1` |
| Canonical Node baseline | `22.19.0` (unchanged) |
| Upstream npm coding-agent identity | name=`@earendil-works/pi-coding-agent`, version=`0.82.1`, integrity=`sha512-zbkAhoIuDPMF3pKuja0ajZabrMWU29FUMV9A/XMXT/XC1yXs5xt6t6t13GogQFsDrDqbFP4DkZQO1w8rWRAzYA==` |
| `npm pack` result | `earendil-works-pi-coding-agent-0.82.1.tgz`, sha512 = `zbkAhoIuDPMF3pKuja0ajZabrMWU29FUMV9A/XMXT/XC1yXs5xt6t6t13GogQFsDrDqbFP4DkZQO1w8rWRAzYA==` (matches) |
| Restored coding-agent `dist/**` file count | `713` |
| Pi AI materialization source | canonical `codex_runner/pi-runtime/package.json` + `package-lock.json` via `npm ci --omit=dev --ignore-scripts --no-audit --no-fund` |
| Restored Pi AI identity/version | `@earendil-works/pi-ai@0.82.1` |
| Restored OpenAI Codex model catalog path | `codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js` |
| `.gitignore` exception added | `codex_runner/.gitignore` lines 41–52 |
| Global `dist/` ignored | Yes (verified sentinel test) |
| Global `node_modules/` ignored | Yes (verified sentinel test) |
| No unrelated `node_modules` vendored | Yes (only `@earendil-works/pi-ai` introduced under `codex_runner/vendor/pi-coding-agent/node_modules/`) |
| Runtime-contract test result | `47 passed, 0 failed` (including new `test_canonical_pi_source_vendor_runtime_bundle_is_complete`) |
| Guardian readiness regression result | `11 passed` |
| Authorized-failure regression result | `31 passed` |
| Source-relative wrapper smoke result | `BLOCKED` at `runtime_load` (transitive closure missing; see below) |
| Smoke expected identity | `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` |
| Smoke actual identity | `null` (wrapper subprocess could not load the SDK) |
| `runtime_identity_established` | `false` |
| `oauth_available` | `null` |
| `session_initialized` | `false` |
| `provider_request_started` | `false` |
| Provider inference count | `0` |
| Model prompt count | `0` |
| Live Executor invocation count | `0` |
| Operator credential inspected | `false` |
| Operator credential consumed | `false` |
| Git tracked-file readback | all three required files (`coding-agent/dist/index.js`, nested `pi-ai/dist/index.js`, `openai-codex.models.js`) tracked |
| Docs validation | PASS |
| `git diff --check` | clean |
| Files changed | 4 tracked (1 commit) |
| Commit hash | `2dc6d72c23f70562ccd2779305b9ef0d28213c57` (parent: `4e8beff06307e9862fc8077bd25d0dd2a1a92552` = canonical current main) |
| ADR impact | `Aligned with existing ADR(s); no new ADR required` |
| `CE-L1` | `OPEN` |
| `CE-L1_OAUTH_PREREQUISITE=PASS` | `NOT EMITTED` |
| `LIVE_EXECUTOR_PROVEN` | `NOT EMITTED` |
| `NEXT_TASK_REQUIRED` | `vendor the canonical locked transitive closure for @earendil-works/pi-coding-agent@0.82.1 and @earendil-works/pi-ai@0.82.1 (the 224 non-@earendil-works packages that npm ci populates today) into codex_runner/vendor/pi-coding-agent/node_modules/, then re-run the empty-HOME source-relative wrapper smoke; after that lands, re-run the canonical-main openai-codex / gpt-5.6-sol Guardian/Pi non-inference credential-readiness qualification` |

## Pre-repair canonical defect reproduction

```text
$ test ! -e codex_runner/vendor/pi-coding-agent/dist/index.js && echo true
true

$ test ! -e codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js && echo true
true

$ ls codex_runner/vendor/pi-coding-agent/
CHANGELOG.md
README.md
docs
examples
npm-shrinkwrap.json
package.json
```

```text
$ git check-ignore -v codex_runner/vendor/pi-coding-agent/dist/index.js
codex_runner/.gitignore:38:vendor/pi-coding-agent/dist	codex_runner/vendor/pi-coding-agent/dist/index.js

$ git check-ignore -v codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
codex_runner/.gitignore:39:vendor/pi-coding-agent/node_modules	codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
```

```text
$ cat codex_runner/vendor/pi-coding-agent/package.json
{
  "name": "@earendil-works/pi-coding-agent",
  "version": "0.82.1",
  ...

$ cat codex_runner/pi-runtime/package.json
{
  "name": "codexify-pi-runtime",
  ...
  "dependencies": {
    "@earendil-works/pi-coding-agent": "0.82.1",
    "@earendil-works/pi-ai": "0.82.1"
  }
}
```

The pre-repair defect was real and reproduced exactly as the
prior BLOCKED readiness proof documented.

## Upstream package identity verification

```text
$ npm view @earendil-works/pi-coding-agent@0.82.1 name version dist.integrity engines
name              = '@earendil-works/pi-coding-agent'
version           = '0.82.1'
dist.integrity    = 'sha512-zbkAhoIuDPMF3pKuja0ajZabrMWU29FUMV9A/XMXT/XC1yXs5xt6t6t13GogQFsDrDqbFP4DkZQO1w8rWRAzYA=='
engines           = { node: '>=22.19.0' }
```

```text
$ npm pack @earendil-works/pi-coding-agent@0.82.1
npm notice total files: 880
earendil-works-pi-coding-agent-0.82.1.tgz

$ sha512(earendil-works-pi-coding-agent-0.82.1.tgz)
zbkAhoIuDPMF3pKuja0ajZabrMWU29FUMV9A/XMXT/XC1yXs5xt6t6t13GogQFsDrDqbFP4DkZQO1w8rWRAzYA==
```

The local tarball's SHA-512 matches the registry integrity exactly.
The bundle was obtained from the official 0.82.1 npm package, not
from another worktree, not from a global install, not from an
arbitrary npm cache.

## `dist/**` restoration

```text
$ tar -xzf earendil-works-pi-coding-agent-0.82.1.tgz -C staging
$ find staging/package/dist -type f | wc -l
713

$ cp -R staging/package/dist codex_runner/vendor/pi-coding-agent/dist
$ find codex_runner/vendor/pi-coding-agent/dist -type f | wc -l
713
```

`codex_runner/vendor/pi-coding-agent/dist/` now contains the exact
713-file runtime bundle from the official 0.82.1 npm package.
No files were regenerated, transpiled, or modified.

## Nested `@earendil-works/pi-ai` restoration

```text
$ mkdir -p /tmp/pi-0821-pi-ai-staging
$ cd /tmp/pi-0821-pi-ai-staging
$ cp <worktree>/codex_runner/pi-runtime/package.json .
$ cp <worktree>/codex_runner/pi-runtime/package-lock.json .
$ npm ci --omit=dev --ignore-scripts --no-audit --no-fund
added 225 packages in 3s

$ cat node_modules/@earendil-works/pi-ai/package.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["name"], d["version"])'
@earendil-works/pi-ai 0.82.1

$ cp -R node_modules/@earendil-works/pi-ai codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/
```

The nested Pi AI runtime was materialized from the canonical
`package-lock.json` (the one already committed at `origin/main`'s
`codex_runner/pi-runtime/package-lock.json`).  No unrelated packages
from the scratch closure were vendored — only the single
`@earendil-works/pi-ai` package was copied into the source-vendor
`node_modules/@earendil-works/`.

## `.gitignore` exception details

```text
# Original (canonical main) — codex_runner/.gitignore
36: # Pi Agent
37: .pirc
38: vendor/pi-coding-agent/dist
39: vendor/pi-coding-agent/node_modules
```

The repair adds scoped exceptions immediately after:

```text
# Canonical Pi source-vendor runtime payload exceptions.
# Restore the previously-proven maintained 0.82.1 runtime bytes into the
# source-vendor fallback so the wrapper's source-relative default can load
# @earendil-works/pi-coding-agent@0.82.1 and the nested maintained
# @earendil-works/pi-ai@0.82.1 without external SDK overrides.
+!vendor/pi-coding-agent/dist/
+!vendor/pi-coding-agent/dist/**
+!vendor/pi-coding-agent/node_modules/
+!vendor/pi-coding-agent/node_modules/@earendil-works/
+!vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/
+!vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/**
```

The global `dist/` (line 17) and `node_modules/` (line 23) rules
remain intact for ordinary project/build dependency output.

Verification — required runtime payload is no longer ignored:

```text
$ git check-ignore -q codex_runner/vendor/pi-coding-agent/dist/index.js ; echo exit=$?
exit=1   # NOT ignored

$ git check-ignore -q codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js ; echo exit=$?
exit=1   # NOT ignored

$ git check-ignore -q codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js ; echo exit=$?
exit=1   # NOT ignored
```

Verification — unrelated `node_modules` content remains ignored:

```text
$ git clone --depth 1 <worktree> sentinel-clone
$ mkdir -p sentinel-clone/unrelated-test/node_modules/foo && touch sentinel-clone/unrelated-test/node_modules/foo/bar.js
$ git check-ignore -q sentinel-clone/unrelated-test/node_modules/foo/bar.js ; echo exit=$?
exit=0   # IS ignored
```

The unrelated sentinel was created and removed; nothing was left in
the repository.

## Runtime-contract regression

The new `test_canonical_pi_source_vendor_runtime_bundle_is_complete`
test asserts:

```text
codex_runner/vendor/pi-coding-agent/dist/index.js exists
codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js exists
codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js exists
@earendil-works/pi-coding-agent = 0.82.1
@earendil-works/pi-ai = 0.82.1
```

This test fails closed if the source-vendor tree ever returns to
metadata-only state.  It also reads file existence and package
metadata directly (no `git` calls inside pytest, per spec §9).

## Automated test results

```text
$ .venv/bin/python -m pytest -v \
    tests/ops/test_worker_coding_pi_runtime_contract.py \
    guardian/tests/agents/test_pi_readiness.py \
    tests/pi/test_pi_authorized_failure_diagnostics.py

collected 47 items
...
======================= 47 passed, 9 warnings in 0.76s ========================
```

- 6 worker-coding runtime-contract tests (5 prior + 1 new `test_canonical_pi_source_vendor_runtime_bundle_is_complete`)
- 11 guardian readiness tests
- 31 authorized-failure-diagnostics tests

## Source-relative wrapper smoke (empty HOME)

```text
$ EMPTY_HOME=$(mktemp -d -t codexify-pi-empty-home.XXXXXX)
$ unset PI_CODING_AGENT_PACKAGE_ROOT
$ unset PI_CODING_AGENT_NODE_MODULES
$ cd "$EMPTY_HOME"
$ env -i HOME="$EMPTY_HOME" PATH="/usr/bin:/bin:/usr/local/bin" \
      PI_PROVIDER=openai-codex PI_MODEL=gpt-5.6-sol \
      PI_GUARDIAN_AUTHORIZED=1 PI_GUARDIAN_HARNESS_ID=pi-coding-agent \
      PI_GUARDIAN_HARNESS_VERSION=0.82.1 \
      node /Users/.../codexify-pi-source-vendor-repair/codex_runner/src/agent-wrapper.js \
        guardian-authorized-readiness

{"status":"error","failure_class":"runtime_module_unavailable","failure_stage":"runtime_load","actual_runtime_identity":null,"runtime_identity_established":false,"session_initialized":false,"provider_request_started":false}
```

The wrapper subprocess could not load the Pi SDK from the source-vendored
`packageRoot` because the coding-agent `dist/index.js` resolves
`chalk` (and other transitive deps) from outside its own bundle,
and the source-vendored tree does not currently ship those
transitive deps.

Per spec §11, this BLOCKED outcome is reported honestly with the
smallest next missing runtime dependency identified.

## Smallest next missing runtime dependency

The wrapper's `loadPiSdk` resolves the source-vendored SDK from
`packageRoot = codex_runner/vendor/pi-coding-agent` and
`nodeModulesRoot = packageRoot/node_modules`.  When it tries to
import `packageRoot/dist/index.js`, that file's transitive
imports must be resolvable.  Direct dep inspection (from the
canonical pinned closure) shows the following 23 direct runtime
deps are **absent** from the source-vendored
`codex_runner/vendor/pi-coding-agent/node_modules/` and therefore
**cannot** be resolved by Node module resolution when running from
the source-relative fallback path:

```text
@anthropic-ai/sdk: MISSING
@aws-sdk/client-bedrock-runtime: MISSING
@google/genai: MISSING
@mistralai/mistralai: MISSING
@opentelemetry/api: MISSING
@silvia-odwyer/photon-node: MISSING
@smithy/node-http-handler: MISSING
chalk: MISSING
cross-spawn: MISSING
diff: MISSING
glob: MISSING
highlight.js: MISSING
hosted-git-info: MISSING
http-proxy-agent: MISSING
https-proxy-agent: MISSING
ignore: MISSING
jiti: MISSING
minimatch: MISSING
openai: MISSING
partial-json: MISSING
proper-lockfile: MISSING
semver: MISSING
typebox: MISSING
undici: MISSING
yaml: MISSING
```

These 23 direct deps bring a transitive closure of ~200 additional
packages.  The canonical pinned closure
(`/tmp/pi-0821-pi-ai-staging/node_modules/` produced by
`npm ci` against the canonical lock) contains **225 packages
total**.  Only the single `@earendil-works/pi-ai` package was
introduced under the source-vendor `node_modules/` in this slice.

The next atomic task is to either:
1. extend the source-vendored `node_modules/` to include the
   canonical pinned closure (224 non-`@earendil-works` packages);
2. or add scoped `.gitignore` exceptions that allow tracking the
   transitive deps individually;
3. or replace the source-relative fallback with a build-time
   `npm ci` step that materializes the full closure (as the
   production Dockerfile already does).

## Git tracked-file readback

```text
$ git add codex_runner/.gitignore \
          codex_runner/vendor/pi-coding-agent/dist \
          codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works \
          tests/ops/test_worker_coding_pi_runtime_contract.py

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/dist/index.js
codex_runner/vendor/pi-coding-agent/dist/index.js
exit=0   # tracked

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js
exit=0   # tracked

$ git ls-files --error-unmatch codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js
codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js
exit=0   # tracked
```

All three required files are tracked in Git.  The discriminant
required by spec §15 passes.

## Staged-path audit

Only the authorized paths were staged:

```text
$ git status --short | wc -l
1428

$ git status --short | grep "vendor/pi-coding-agent/node_modules/" | awk '{print $2}' | cut -d/ -f1-5 | sort -u
codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works
```

Only `codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/`
was introduced under the vendor `node_modules/`.  No unrelated
packages were committed.  The nested `pi-ai` package alone was
copied (712 files); the staging closure's other 224 packages were
NOT vendored.

## Documentation follow-through

Only the durable proof artifact was created.  No other docs updated.
No ADR modified.  No `00-current-state.md` touched.  No Campaign
closure document touched.  No release-support doc touched.  No
historical proof modified.  The local historical readiness BLOCKED
proof commit `37fa2b792…` was NOT included in this repair commit.

`docs/architecture/diagram-governance.md` and
`docs/architecture/module-diagram-coverage-matrix.md` were
**not** modified in this commit.  The repo docs validator passed
without diagram-freshness updates being required (the source
modification is purely vendor-bundle restoration that adds files
without changing runtime topology).

## Invariants check

| Invariant | Status |
| --- | --- |
| One Pi version (`0.82.1`) | ✅ preserved (no version change) |
| One maintained package identity | ✅ preserved (`@earendil-works/*` only) |
| No old/new Pi runtime fork | ✅ preserved |
| Restore only previously-proven runtime artifacts | ✅ preserved (only `dist/**` and nested `pi-ai` restored) |
| Global build/dependency ignore policy intact | ✅ preserved (verified by sentinel test) |
| Only canonical Pi source-vendor runtime receives ignore exceptions | ✅ preserved (exceptions are scoped to `vendor/pi-coding-agent/dist/` and `vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/`) |
| No broad `node_modules` tracking | ✅ preserved |
| No broad `dist` tracking | ✅ preserved |
| Guardian remains execution authority | ✅ preserved (no Guardian source change) |
| Pi remains credential / provider execution mechanism | ✅ preserved (no Pi runtime logic change) |
| Campaign Engine owns no credentials | ✅ preserved (no Campaign Engine source change) |
| Actual runtime identity comes from loaded SDK bytes | ✅ preserved (wrapper unchanged; identity attestation path intact) |
| No model substitution | ✅ preserved |
| No retry | ✅ preserved |
| No fallback | ✅ preserved |
| No rebinding | ✅ preserved |
| No operator credential use during repair | ✅ preserved (HOME was an empty disposable; `~/.pi/agent/auth.json` not accessed) |
| No inference | ✅ preserved |
| Historical proofs remain immutable | ✅ preserved |
| Release claims remain proof-bounded | ✅ preserved |

## Exit conditions

```text
Result:                                    BLOCKED (bounded)
CE-L1:                                     OPEN
CE-L1_OAUTH_PREREQUISITE:                  NOT EMITTED
LIVE_EXECUTOR_PROVEN:                      NOT EMITTED

NEXT_TASK_REQUIRED:
  extend the source-vendor fallback to include the canonical locked
  transitive closure for @earendil-works/pi-coding-agent@0.82.1 and
  @earendil-works/pi-ai@0.82.1, so the source-relative wrapper
  fallback can load the maintained Pi runtime from a fresh checkout;
  after that lands, re-run the canonical-main
  openai-codex / gpt-5.6-sol Guardian/Pi non-inference
  credential-readiness qualification
```

## Closely related artifacts

* **CE-L1 readiness BLOCKED proof (diagnostic only, not landed)**:
  commit `37fa2b792e1c9d9ba86b667b46c19833e88d3537` on
  `proof/ce-l1-openai-codex-gpt56sol-readiness`
* **Pi 0.82.1 modernization proof (canonical on main)**:
  PR #765 (squash `4e8beff06…`)
  (`docs/architecture/proofs/runtime/2026-08-27-pi-runtime-0821-modernization-proof.md`)
* **CE-L1 OAuth prerequisite BLOCKED proof (canonical on main)**:
  PR #762 (squash `3c56cba98…`)
* **CE-L1 live Executor runtime landing (canonical on main)**:
  PR #761 (squash `321ea07c1…`)
* **CE-L0 PASS proof**:
  PR #758 (squash `d1463fe85…`)

## Lessons for the next slice

Three durable lessons are recorded:

1. **The source-vendored Pi runtime was silently incomplete on
   canonical main** because `.gitignore` lines
   `vendor/pi-coding-agent/dist` and
   `vendor/pi-coding-agent/node_modules` in `codex_runner/.gitignore`
   prevented the runtime bytes from being tracked even when they
   existed in working trees.  This slice added scoped exceptions so
   the runtime payload can be tracked.  The runtime-contract test
   now permanently fails CI if the runtime payload disappears again.

2. **The production worker runtime is healthy and unaffected**.
   The `backend/Dockerfile`'s `pi-sdk-runtime` stage continues to
   populate the full 225-package closure via `npm ci` against
   `codex_runner/pi-runtime/package-lock.json`, and the worker's
   Compose env continues to set `PI_CODING_AGENT_PACKAGE_ROOT` and
   `PI_CODING_AGENT_NODE_MODULES` to canonical paths.  Only the
   source-vendored fallback was affected; that fallback is exercised
   by source-only read-only smoke and by CI.

3. **The source-vendored fallback requires the full transitive
   closure to load**.  Even after restoring `dist/**` and the
   maintained `pi-ai` runtime, the wrapper cannot complete
   `runtime_load` because 23 direct deps (`chalk`,
   `@sinclair/typebox`, `cross-spawn`, etc.) and their transitive
   closure are not in `codex_runner/vendor/pi-coding-agent/node_modules/`.
   The next slice must add the canonical locked transitive closure
   to the source-vendor tree (or, alternatively, add a build-time
   `npm ci` step that materializes the closure at the source-vendor
   path).  The smallest seam is reported honestly above; no
   `gpt-5.5` workaround, no silent model swap, no wrapper redesign.