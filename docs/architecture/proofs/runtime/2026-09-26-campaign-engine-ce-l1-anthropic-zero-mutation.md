# CE-L1 Anthropic live Executor control — zero mutation (2026-09-26)

## Gate result

`BLOCKED`: one current-tip, operator-selected Anthropic CE-L1 live Executor
control returned to Campaign Engine, but no allowed-file mutation occurred.
Campaign Engine failed closed with `zero_mutation_executor_turn` before
publishing an Attempt or other Campaign artifacts.

```text
CE-L1=OPEN
CE-L1_EXIT=NOT_EMITTED
LIVE_EXECUTOR_PROVEN=NOT_EMITTED
CE-L2=GATED
```

The narrowest positive observation is that Pi advertised `write` and applied
the required first-request tool selection once, then reported one assistant
message with zero tool-call events and zero tool executions. This does not
identify why no `write` call was produced. It does not authorize a repair,
retry, provider switch, or wider mutation scope.

## Provenance and frozen posture

| Field | Evidence |
| --- | --- |
| Source branch and clean invocation tip | `codex/campaign-engine-closure` at `51600076cf6501477bc66326edb20f38287e9daf` |
| CE-L0 prerequisite | `GUARDIAN_PI_LIVE_READY` at `49cbdb2c6bfc7d0befc470e9d7521e368bcc5fe6` |
| Pre-call diagnostic prerequisite | `51600076` carries bounded timeout phases through CE-L1 errors and passes explicit `medium` effort to Guardian |
| Refreshed `origin/main` | `4041440110a2c9c42fe8898ffafc7eb9b2a4255a`, ancestor of the proof tip |
| Locked Executor RoleBinding | `binding-executor-ce-l1-anthropic-51600076`, revision 1, `anthropic / claude-sonnet-4-6` |
| Pi harness | `pi-coding-agent@0.82.1` |
| Reasoning effort | explicit `medium` through the CE-L1 Guardian invoker; CE-L0's High selection was task-specific |
| Required tool and write grant | `write`; Guardian `files.write` limited to `proof_target.txt` |
| Adapter bound | 300 seconds |
| Single-call guard | `/private/tmp/ce_l1_anthropic_51600076.live_started`, consumed once |
| Disposable target | `/private/tmp/ce-l1-anthropic-o2aa26jw/target`; no remotes or symlinks |
| Campaign artifact root | `/private/tmp/ce-l1-anthropic-o2aa26jw/artifacts`; no files published |

The fixture contained exactly one runnable Task. Its objective was to
replace all bytes of `proof_target.txt` with
`CE_L1_POST_INSTRUMENTATION_DRIVER_PASS_OK` followed by one LF byte. The
target had no other source file. The provider-backed invocation was routed
through `run_live_executor_campaign` and the canonical Guardian/Pi invoker;
the test-only invoker seam was not rebound.

## Preparation and readiness

Before the live call, Campaign Engine preparation validated the Campaign
document, selected the locked Executor binding, froze the prompt and target
baseline, and declared `required_tool_name="write"`. Guardian envelope,
decision, write-scope, and Campaign pre-execution drift checks passed.

Canonical `preflight_guardian_authorized_pi` returned `ok=true`, deepest
stage `auth_available`, exact
`anthropic / claude-sonnet-4-6 / pi-coding-agent@0.82.1` identity, one
preflight call, zero retry/fallback, no session, no provider request, and an
unchanged target. Readiness established structural auth availability, not
provider acceptance. The temporary driver first rejected the scoped npm
package name before readiness; after correcting that local check, the
reported readiness ran once. No live guard or provider call was consumed by
the rejected preparation.

## Single live outcome

The one guarded `run_live_executor_campaign` call raised the bounded
Campaign error:

| Field | Observation |
| --- | --- |
| Failure / stage | `zero_mutation_executor_turn` / `post_invocation` |
| Required-tool selection | `write`, applied `true`, application count `1` |
| Effective coding tools | `read`, `bash`, `edit`, `write` |
| Write tool available | `true` |
| Assistant messages / tool-call events | `1` / `0` |
| Assistant tool calls | `0` |
| Tool execution starts / ends | `0` / `0` |
| Executed tools | none |
| Changed target paths | none |
| Campaign Attempt / Receipt / Harness Result artifacts | absent; publication stopped before promotion |
| Timeout phase trail | null on this terminal, non-timeout outcome |

The Campaign code invokes the Guardian rail once and checked the underlying
outcome's `ok`, zero retry/fallback, Receipt, Harness Result, and expected
provider/model before the zero-mutation invariant fired. Its
`CampaignLiveExecutorError.runner_call_count=0` is an unpopulated default on
this post-invocation failure, **not** evidence of zero runner calls. The
underlying terminal identity and Receipt/Harness Result were not retained in
the published Campaign evidence, so they cannot satisfy the CE-L1 gate.
The applied-selection observation reaches the first provider payload
projection seam; it alone does not prove external provider receipt or
processing.

## Target and repository posture

| Field | Before | After |
| --- | --- | --- |
| Target Git HEAD | `a5c08ae90573293047bfab9a6a4b63b9d637b194` | same |
| Target `git status --porcelain` | clean | clean |
| `proof_target.txt` SHA-256 | `ef30491cd8c5d06872b3545dcb220854d91312b1eb70a29caf14f4f8bd483464` | same |
| Git metadata file hashes | baseline | unchanged |
| Target remotes / symlinks | `0` / `0` | `0` / `0` |

The required after-content SHA-256 would have been
`7022e1705b102a4788d4a2c23148f6f921478d0bf0138ca55b66fb21b0f9391e`;
the observed file did not match it. The Codexify checkout remained clean at
the invocation tip. No target commit, push, merge, deployment, or durable
Codexify ingestion occurred.

## Validation and boundary

- Provider-free CE-L1 regression file: `./.venv/bin/python -m pytest -q
  codex_runner/tests/test_campaign_engine_live_executor.py --tb=short` passed
  (43 tests) on the pre-call repair tip.
- `./.venv/bin/python -m ruff check codex_runner/campaign_engine/errors.py`
  passed. The broader Ruff command over the CE-L1 runtime and historical
  test file failed on pre-existing unused imports, duplicate fixture keys,
  and related unchanged lines; those findings were not repaired here.
- `git diff --check` and the staged diff check passed for the prerequisite.
- The live proof used no fake Pi package, injected runner, retry, fallback,
  provider substitution, or second provider call.

The output is bounded to identity, counts, status, hashes, and canonical
diagnostic tokens. No credential, raw provider response, assistant text,
reasoning content, raw stderr, or environment dump is in this record.
ADR-068 and the Pi Invocation Boundary Contract remain the governing
authority. CE-L1 remains open at the observed tool-call boundary; the Goal
must stop after this spent control rather than proceed to CE-L2.
