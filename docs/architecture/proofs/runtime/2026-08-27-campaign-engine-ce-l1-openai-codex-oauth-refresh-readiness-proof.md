# CE-L1 Pi OpenAI Codex OAuth Refresh Readiness Proof — 2026-08-27

## Result

**`BLOCKED`**

The first CE-L1 live proof (PR #761, commit `321ea07c1…` on
remote main) reached the canonical Guardian/Pi rail with one
bounded real wrapper invocation and reported `result_class="success"`
without producing an allowed-path mutation.  The Campaign runtime
correctly rejected nominal transport success with
`zero_mutation_executor_turn`.  Subsequent investigation bounded the
smallest next live-environment blocker to the operator's existing
`openai-codex` subscription OAuth session.

This Task Spec therefore required:

1. an operator interactive `pi /login` to refresh that OAuth session;
2. a single canonical Guardian/Pi non-inference readiness call to
   prove the refreshed credential is structurally consumable.

Both steps have an inherent interactive / operator-dependency that
prevents autonomous completion in this slice.  In addition, the
current Pi provider registry no longer advertises the historical
`gpt-5.1` model, which the spec §8 explicitly forbids silently
substituting.  No retry was attempted.  No provider fallback was
attempted.  No model fallback was attempted.  No OAuth automation was
attempted.  No CE-L1 live Executor invocation was attempted.

The smallest observed repair seam is:

> `NEXT_TASK_REQUIRED=operator must run the canonical interactive pi /login flow for the ChatGPT Plus/Pro (Codex) subscription lane in a human-present terminal, then explicitly select a current openai-codex model identifier (gpt-5.1 has been removed from the current Pi 0.82.0 registry; viable current candidates include gpt-5.3-codex-spark, gpt-5.4, gpt-5.4-mini, gpt-5.5, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra) before re-running this credential-readiness proof and then the CE-L1 live Executor qualification from canonical current main`

`CE-L1_EXIT` is **not** emitted.  `LIVE_EXECUTOR_PROVEN` is **not**
emitted.

## Summary

| Field | Value |
| --- | --- |
| `credential_proof_base_sha` (current `origin/main` at proof time) | `321ea07c19ade38fb898ff8c2a449499c04bf3d9` |
| Starting `origin/main` SHA | `321ea07c19ade38fb898ff8c2a449499c04bf3d9` (= CE-L1 implementation landing PR #761) |
| Proof worktree | `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify-ce-l1-oauth-refresh` |
| Proof branch | `proof/ce-l1-openai-codex-oauth-refresh` |
| Working tree | clean (no tracked modifications; only `docs/architecture/proofs/runtime/2026-08-27-campaign-engine-ce-l1-openai-codex-oauth-refresh-readiness-proof.md` is added by this proof) |
| Files changed by this proof | `docs/architecture/proofs/runtime/2026-08-27-campaign-engine-ce-l1-openai-codex-oauth-refresh-readiness-proof.md` |
| Pi CLI runtime | `0.82.0` (`/Users/resonant_jones/.nvm/versions/node/v22.22.3/bin/pi`) |
| Vendored Pi SDK | `@mariozechner/pi-coding-agent@0.72.1` (unchanged on current `origin/main`) |
| Provider ID recognized | `openai-codex` |
| Historical continuity model `gpt-5.1` | **NOT present** in the current Pi registry (Pi 0.82.0) |
| Viable current openai-codex models | `gpt-5.3-codex-spark`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra` |
| Operator interactive `/login` invoked | **No** — interactive browser/device OAuth flow is operator-only by design and spec §5 |
| Credential material recorded | **No** (`credential_material_recorded=false`) |
| Credential file inspected | **No** (`~/.pi/agent/auth.json` was neither read nor modified during this task) |
| Readiness call performed | **No** — the readiness rail requires the refreshed credential that this task could not obtain |
| Provider inference requests | `0` |
| Model prompts | `0` |

## Why this turned out this way (smallest observed repair seam)

Two genuine BLOCKED conditions, neither of which is autonomously
recoverable in this slice, are recorded in priority order.

### Blocker A — operator-interactive OAuth (must happen)

Per the Task Spec §5, the OpenAI Codex subscription lane is
recovered through Pi's interactive `/login` flow, which Pi exposes
**only** inside the interactive REPL (`pi` without `--print`):

> *start Pi interactive mode*
> *   -> /login*
> *   -> select ChatGPT Plus/Pro (Codex)*
> *   -> complete browser/device OAuth*

The spec further requires the **operator** to complete the
browser/device authorization personally.  Pi's CLI does not expose a
non-interactive OAuth login subcommand (`pi --help` lists no
`login` command; only `install / remove / uninstall / update / list /
config` and the standard model/provider options).  The
`--print` / non-interactive mode does not accept `/login` and cannot
substitute for the human-present OAuth consent flow.

The autonomous operator (this session) cannot:

- enter account passwords;
- complete MFA challenges;
- select the correct browser account among several active sessions;
- consent on behalf of the human account owner;
- read or copy authorization codes from a private device flow page;
- visually inspect a browser-based OAuth consent screen.

Each of these is explicitly forbidden by spec §5 ("Do not automate").
This BLOCKED condition cannot be resolved by additional code, additional
deterministic tests, or additional wrapper workarounds — it requires
human presence at an interactive terminal with browser access to the
operator's OpenAI account.

### Blocker B — model continuity anchor broken (must be resolved before CE-L1 re-runs)

Historical CE-L0 (PR #758, commit `d1463fe85…`) and CE-L1 (PR #761,
commit `321ea07c1…`) used:

```text
provider_id    = openai-codex
model_id       = gpt-5.1
harness_id     = pi-coding-agent
harness_version = 0.72.1
```

The current installed Pi runtime is **0.82.0**.  The current Pi
registry (resolved via the canonical non-secret
`pi --list-models openai-codex` path used by CE-L0) lists the
following openai-codex lane models:

```text
openai-codex  gpt-5.3-codex-spark
openai-codex  gpt-5.4
openai-codex  gpt-5.4-mini
openai-codex  gpt-5.5
openai-codex  gpt-5.6-luna
openai-codex  gpt-5.6-sol
openai-codex  gpt-5.6-terra
```

`gpt-5.1` is no longer a recognized identifier on this Pi runtime.
Spec §8 explicitly forbids silently picking an arbitrary replacement
("Do not silently select an arbitrary replacement for the future
CE-L1 proof").

Spec §8 also explicitly forbids completing this credential-readiness
proof with an operator-unauthorized model selection.  The current
Task Spec is the credential prerequisite slice; model selection
belongs in the subsequent CE-L1 requalification spec authored after
PASS.

Therefore both the readiness check and the subsequent CE-L1
requalification need an explicit current-model choice.  This BLOCKED
condition is recoverable by **operator decision** — not by autonomous
work.

### Blocker C — runtime / vendored SDK drift (informational; non-blocking)

| Surface | CE-L0 / CE-L1 historical | Current Task Spec |
| --- | --- | --- |
| Pi CLI runtime (`pi --version`) | `0.72.1` (no upgrade visible in the historical proofs) | `0.82.0` |
| Vendored Pi SDK at `codex_runner/vendor/pi-coding-agent/package.json` | `0.72.1` | `0.72.1` (unchanged on current `origin/main`) |

The interactive `/login` flow writes the refreshed OAuth credential to
the user-owned `~/.pi/agent/auth.json` consumed by the installed Pi
runtime (`0.82.0`).  The canonical wrapper subprocess
(`codex_runner/src/agent-wrapper.js guardian-authorized-readiness`)
spawns the wrapper with `PI_CODING_AGENT_PACKAGE_ROOT` pointing at the
vendored SDK (`0.72.1`), so the **readiness rail consumes the vendored
0.72.1 SDK** for identity attestation while the **installed Pi runtime
(0.82.0) is responsible for the credential-store lifecycle**.

This is consistent with CE-L0/CE-L1 closeouts and is recorded here
only as situational context.  It is not a blocker; it is an ongoing
observation.  No code change is required for this slice.

## Boundary facts recorded

| Field | Value |
| --- | --- |
| `Result` | `BLOCKED` |
| `Result.failure_reason` | `operator_interactive_oauth_required` (primary); `historical_model_anchor_absent` (secondary, blocks continuity) |
| `Result.failure_class` | `credential_lifecycle_owner_owned` |
| `Result.diagnostic_stage` | `interactive_login` |
| Interactive `/login` invoked | `No` (autonomous session cannot complete browser/device OAuth) |
| `login_provider_id` | `openai-codex` (would-be target if operator chooses to proceed) |
| `login_result` | `not_attempted` |
| `login_interaction` | `operator_required` |
| `credential_material_recorded` | `false` |
| `credential_file_inspected` | `false` |
| OAuth refresh attempted by autonomous process | `0` |
| OAuth refresh attempted via interactive `/login` | `0` (operator not present) |
| Provider fallback attempted | `0` |
| Model fallback attempted | `0` |
| Provider switch attempted | `0` |
| Model switch attempted | `0` |
| Retry attempted | `0` |
| Guardian authorization envelope constructed | `0` |
| `preflight_guardian_authorized_pi` calls performed | `0` (cannot run without refreshed credential and selected current model) |
| `invoke_guardian_authorized_pi` calls performed | `0` |
| `run_live_executor_campaign` calls performed | `0` |
| Provider inference requests | `0` |
| Model prompts | `0` |
| CE-L1 target mutations attempted | `0` |
| `LIVE_EXECUTOR_PROVEN` emitted | `false` |
| `CE-L1_EXIT` emitted | `false` |

## Pi runtime and provider inventory (non-secret)

| Field | Value |
| --- | --- |
| Pi executable path | `/Users/resonant_jones/.nvm/versions/node/v22.22.3/bin/pi` |
| Pi CLI version | `0.82.0` |
| Vendored SDK path (canonical wrapper override) | `codex_runner/vendor/pi-coding-agent` (currently a partial checkout; the canonical full SDK used by the wrapper is `/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/codex_runner/vendor/pi-coding-agent`, reached via the documented `PI_CODING_AGENT_PACKAGE_ROOT` override) |
| Vendored SDK package | `@mariozechner/pi-coding-agent` |
| Vendored SDK version | `0.72.1` |
| OpenAI Codex lane present in current registry | `yes` |
| Current openai-codex model inventory | `gpt-5.3-codex-spark`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra` |
| Historical CE-L0/CE-L1 continuity model `gpt-5.1` | **absent** from current Pi registry |
| Provider directory resolution technique | non-secret `pi --list-models openai-codex` |

## Current-truth status

| Claim | Status |
| --- | --- |
| CE-L0 is PASS | True |
| Guardian/Pi live invocation has previously succeeded | True |
| CE-L1 live record contract is canonical | True (PR #759, `cc78c58f1…`) |
| CE-L1 live Executor runtime is canonical | True (PR #761, `321ea07c1…`) |
| CE-L1's first live attempt reached the real Guardian/Pi rail | True |
| CE-L1's first live attempt used one runner call | True |
| CE-L1's first live attempt retry count | `0` |
| CE-L1's first live attempt fallback count | `0` |
| CE-L1's first live attempt runtime identity matched | True |
| CE-L1's first live attempt Pi Receipt / Harness Result validation | `pass` |
| CE-L1's first live attempt target mutation | **did not occur** |
| `zero_mutation_executor_turn` correctly blocked false Campaign success | True |
| Observed next blocker is the stale/exhausted OpenAI Codex OAuth session | True |
| Pi's supported subscription-auth management surface is interactive `/login` | True |
| A fresh OpenAI Codex OAuth session is proven this slice | **No** |
| Fresh credential issuance is proven this slice | **No** |
| Post-refresh Guardian/Pi readiness is proven this slice | **No** |
| Provider inference entitlement after refresh is proven this slice | **No** |
| A successful CE-L1 target mutation is proven | **No** |
| `LIVE_EXECUTOR_PROVEN` has been emitted | **No** |
| CE-L1 is `OPEN` | True |
| CE-L2 has begun | **No** |

## Deterministic-validation surface

This BLOCKED task is intentionally minimal: no readiness call, no
inference call, no mutation.  The only deterministic validations
performed in this slice are:

| Validation | Result |
| --- | --- |
| `git fetch origin` | succeeded; `origin/main` recorded as `321ea07c19ade38fb898ff8c2a449499c04bf3d9` |
| `git worktree add` from fresh `origin/main` | succeeded; working tree clean |
| `pi --version` | `0.82.0` |
| `pi --list-models openai-codex` (non-secret) | succeeded; current registry inspected |
| `git rev-parse HEAD == origin/main` | satisfied |
| `git status --short --branch` | clean |
| `git diff --check` (after proof written) | clean |
| `git diff --name-only` (after proof written) | exactly `docs/architecture/proofs/runtime/2026-08-27-campaign-engine-ce-l1-openai-codex-oauth-refresh-readiness-proof.md` |
| `PYTHON=.venv/bin/python make docs` | passed (no document drift introduced by this proof) |
| `test_package_imports_no_prohibited_modules_in_clean_interpreter` | not re-run; this slice is a no-source-change proof; the documented pre-existing Python 3.14 stdlib-import drift on unmodified `origin/main` `7ea8bb4ed…` (independently reproduced during the prior landing task) remains the only known deterministic-test surface drift on the unchanged main |

## Why the readiness rail is not exercised

The spec §13–§15 readiness call requires:

```text
fresh credential issued through Pi interactive /login
canonical non-inference readiness rail (preflight_guardian_authorized_pi)
match expected identity against actual identity
```

The first input (fresh credential) requires the operator-interactive
OAuth flow that this slice cannot complete (Blocker A).  The
readiness call therefore would necessarily run against the still-stale
credential; running it would not produce the spec §14
"oauth_available=true" expectation and would only reproduce the
BLOCKED outcome already documented in the prior CE-L1 proof.  No
expected-or-actual identity match can be honestly recorded without
the fresh credential and the explicitly selected current model
(Blocker B).

Running the readiness call now would:

- spend a bounded provider inference attempt against an exhausted
  credential (the same path that produced the prior BLOCKED proof);
- report `oauth_available=false` (or `true` only if the cached
  pre-revoked access token happens to still validate, which has not
  been verified in this slice);
- not establish any new evidence beyond what the prior CE-L1
  proof already documented.

Per spec §25 ("Do not spend a provider call") this BLOCKED task does
not exercise the readiness rail.

## What is preserved

| Constraint | Status |
| --- | --- |
| `LIVE_EXECUTOR_PROVEN` not emitted | preserved |
| `CE-L1_EXIT` not emitted | preserved |
| CE-L1 remains `OPEN` | preserved |
| Historical CE-L1 BLOCKED proof remains immutable | preserved (`docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md` untouched) |
| Historical CE-L0 BLOCKED proof remains immutable | preserved |
| Historical CE-L0 PASS proof remains immutable | preserved |
| `00-current-state.md` untouched | preserved |
| ADRs untouched | preserved (no ADR change) |
| Campaign closure document untouched | preserved |
| Release-support docs untouched | preserved |
| Campaign Engine source untouched | preserved (no `codex_runner/campaign_engine/**` change) |
| Guardian / Pi source untouched | preserved (no `guardian/pi/**` change, no `guardian/agents/**` change) |
| Wrapper untouched | preserved (`codex_runner/src/agent-wrapper.js` unchanged) |
| Provider registry untouched | preserved (no provider routing change) |
| OAuth implementation untouched | preserved (no OAuth implementation change) |
| Provider fallback / model fallback / retry / provider switch / model switch / rebinding | preserved (none added; none attempted) |
| Credentials outside repository evidence | preserved (no credential JSON, no token, no authorization code, no redirect query string, no cookie, no browser session identifier was written into the proof or into any tracked file) |
| Credential store not directly edited | preserved (`~/.pi/agent/auth.json` was not modified during this task) |

## Documentation follow-through

Only this proof artifact is added:

`docs/architecture/proofs/runtime/2026-08-27-campaign-engine-ce-l1-openai-codex-oauth-refresh-readiness-proof.md`

No other file in `docs/architecture/`, `docs/Campaign/`,
`docs/architecture/proofs/`, `docs/architecture/00-current-state.md`,
any ADR, the Campaign closure document, the release-support docs, any
provider-support doc, any `codex_runner/`, any `guardian/`, any
schema, or anywhere else in the repository was modified by this proof.

## What the next slice requires

The next authorized slice has two independent operator actions:

1. **Operator must run the canonical interactive Pi `/login` flow for
   the ChatGPT Plus/Pro (Codex) subscription lane.**  Pi 0.82.0 exposes
   `/login` only inside the interactive REPL.  The operator enters
   `pi`, types `/login`, selects ChatGPT Plus/Pro (Codex), completes
   the browser/device OAuth consent personally, and confirms the
   successful login response inside the Pi UI.  This will refresh
   `~/.pi/agent/auth.json` with a new, currently-valid OAuth session
   for the `openai-codex` lane.

2. **Operator must explicitly select a current openai-codex model
   identifier** from the current Pi 0.82.0 registry, since `gpt-5.1`
   is no longer present.  The current registry is
   `gpt-5.3-codex-spark`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`,
   `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`.  Selection must be
   recorded explicitly in the subsequent credential-readiness proof
   (or in the subsequent CE-L1 requalification proof) — never silently.

After both operator actions:

3. **Re-run this credential-readiness proof from canonical current
   main** with the freshly issued credential and the explicitly
   selected current model.  This will satisfy spec §11–§14 (fresh
   envelope + decision, valid Guardian authorization, one real
   non-inference readiness call, `ok=true`, `preflight_call_count=1`,
   `retry_count=0`, `fallback_count=0`, `oauth_available=true`,
   expected-vs-actual identity match).

4. **Then** re-run the CE-L1 live Executor qualification from
   canonical current main, exactly once, against a disposable
   proof-target with the freshly issued credential and the explicitly
   selected current model.  The qualification must produce a real
   allowed `proof_target.txt` mutation before `LIVE_EXECUTOR_PROVEN`
   is emitted.

## Exit conditions

```text
Result:                                   BLOCKED
CE-L1:                                    OPEN
LIVE_EXECUTOR_PROVEN:                     NOT EMITTED
CE-L1_EXIT:                               NOT EMITTED
CE-L1_OAUTH_PREREQUISITE:                 NOT PASSED
NEXT_TASK_REQUIRED:                       operator must complete pi /login for ChatGPT Plus/Pro
                                          (Codex) interactively in a human-present terminal,
                                          then explicitly select a current openai-codex
                                          model identifier (gpt-5.1 absent in Pi 0.82.0),
                                          then re-run this credential-readiness proof
                                          and then the CE-L1 live Executor qualification
                                          from canonical current main.
```

## Closely related artifacts

* **CE-L0 historical first-attempt (BLOCKED)**:
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-proof.md`
* **CE-L0 requalification (PASS)**:
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l0-guardian-pi-live-invocation-requalification-proof.md`
  (canonical remote-main; PR #758 merged on `d1463fe85…`)
* **CE-L1 record contract landing (canonical on main)**:
  PR #759 (squash `cc78c58f1…`)
* **CE-L1 live Executor runtime landing (canonical on main)**:
  PR #761 (squash `321ea07c19ade38fb898ff8c2a449499c04bf3d9`)
* **CE-L1 first live proof (BLOCKED)**:
  `docs/architecture/proofs/runtime/2026-08-26-campaign-engine-ce-l1-live-executor-proof.md`

The CE-L0 proofs remain `PASS` on the canonical record.  The CE-L1
implementation remains canonical on the canonical record.  The CE-L1
first live proof remains BLOCKED on the canonical record.  This
proof records only the credential prerequisite slice and produces no
new authoritative closeout for any earlier gate.

## Lessons for the next slice

Three durable lessons are recorded:

1. **Pi's OAuth lifecycle is operator-owned and interactive-only.**
   Pi 0.82.0 exposes `/login` exclusively inside the interactive REPL;
   no `login` subcommand exists in non-interactive mode; no
   `--print`-compatible OAuth flow exists.  Any slice that needs a
   fresh subscription OAuth credential must be authored to either
   wait for the operator to complete `/login` or to surface an
   explicit `BLOCKED` with the operator-interactive seam as the
   `NEXT_TASK_REQUIRED`.  Autonomous sessions cannot complete this
   step.
2. **The current Pi registry must be re-resolved at every fresh
   proof.**  The historical model anchor `gpt-5.1` was removed
   between Pi 0.72.1 (the historical CE-L0/CE-L1 runtime) and Pi
   0.82.0 (the current installed runtime).  The current openai-codex
   lane has 7 models in Pi 0.82.0, none of which is `gpt-5.1`.
   Spec §8 forbids silently picking a replacement.  The proof
   artifact must therefore re-resolve the inventory via the canonical
   non-secret `pi --list-models <provider>` path on every slice.
3. **The vendored Pi SDK version is decoupled from the installed Pi
   CLI version.**  The vendored `codex_runner/vendor/pi-coding-agent`
   remains `0.72.1` while the installed Pi runtime is `0.82.0`.  The
   readiness rail consumes the vendored SDK via
   `PI_CODING_AGENT_PACKAGE_ROOT`; the credential-store lifecycle is
   owned by the installed Pi runtime.  This split is by design and
   is consistent with CE-L0/CE-L1 closeouts; it is recorded here as
   ongoing situational context, not as a defect requiring repair.
