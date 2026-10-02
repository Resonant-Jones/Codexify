# Campaign Engine Milestone A — single-Task supervised-usability proof

Date: 2026-09-28
Repository proof tip: `f0d55ddc4d9b7c871b0d86cf500cb35654e1cd0e`
Branch: `codex/campaign-engine-closure`
Active Campaign: `CAMPAIGN-2026-08-26_001_CAMPAIGN_ENGINE_SUPERVISED_USABILITY_CLOSURE`
Governing contract: accepted [ADR-068](../../adr/068-campaign-engine-live-role-execution-contract.md)
Closure: [Campaign Engine Supervised-Usability Closure](../../../../Campaign/campaign-engine-supervised-usability-closure.md)

```text
CE-L0_EXIT=GUARDIAN_PI_LIVE_READY
CE-L1_EXIT=LIVE_EXECUTOR_PROVEN
CE-L2_EXIT=SINGLE_TASK_SUPERVISED_USABLE
MILESTONE_A=SINGLE_TASK_SUPERVISED_USABLE
NEXT_POSTURE=USE_SINGLE_TASK_LIFECYCLE_BEFORE_CE_L3
```

## Result

One fresh single-Task Campaign completed the full supervised live lifecycle:

```text
Campaign -> live Executor -> live Evaluator -> Receipt -> CampaignState
```

The final independent Evaluator verdict was `passed`. The final Evaluation,
Receipt, and completed CampaignState validated. This is live runtime evidence
for single-Task supervised utility only. It does not establish an autonomous
Campaign runner, multi-Task progression, scheduling, background execution,
unattended operation, or release support.

## Identity and frozen Campaign

| Field | Evidence |
| --- | --- |
| Campaign ID | `campaign-ce-l2-high-90dc70da595c` |
| Task ID | `task-ce-l2-high-90dc70da595c` |
| Canonical Campaign input SHA-256 | `7ae23d9424cc52270d66c26a93c102565b9ba5c884cc3d01dd91474c53cbf77c` |
| Repository proof tip | `f0d55ddc4d9b7c871b0d86cf500cb35654e1cd0e` |
| Repository checkout during both live calls | clean; same HEAD before and after |
| RoleBinding posture | fresh Campaign; Auditor, Executor, and Evaluator bindings were locked before execution |

The Auditor used the existing provider-free fixture posture. The live bindings
were:

| Role | Locked provider / model / harness | Locked effort | Authority |
| --- | --- | --- | --- |
| Executor | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` | `off` | one Guardian-authorized invocation; required `write`; one declared allowed file |
| Evaluator | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` | `high` | separate Guardian authorization; read-only; no write, repair, retry, or rebinding authority |

The final Receipt identifies Executor binding
`binding-executor-ce-l2-high-90dc70da595c` and Evaluator binding
`binding-evaluator-ce-l2-high-90dc70da595c`.

## Gate lineage

| Gate | Exit | Durable evidence and qualification |
| --- | --- | --- |
| CE-L0 | `GUARDIAN_PI_LIVE_READY` | [Current-tip Anthropic Guardian/Pi qualification](2026-09-26-campaign-engine-ce-l0-anthropic-live-ready.md) records one matching live call, effective `high`, valid Pi evidence, and an unchanged disposable read-only target. This is a proof binding only, not a production routing choice. |
| CE-L1 | `LIVE_EXECUTOR_PROVEN` | The successful live Executor evidence in this fresh CE-L2 lifecycle, detailed below, directly proves the bounded Executor gate. The older [CE-L1 Anthropic zero-mutation record](2026-09-26-campaign-engine-ce-l1-anthropic-zero-mutation.md) remains a historical blocked attempt and is not treated as this pass. |
| CE-L2 | `SINGLE_TASK_SUPERVISED_USABLE` | This proof records the complete live Executor and independent read-only Evaluator lifecycle plus final Receipt and CampaignState. |

The CE-L2 implementation prerequisite is documented in the
[RoleBinding-driven Evaluator effort repair](2026-09-28-campaign-engine-ce-l2-evaluator-effort-binding-repair.md).
That provider-free repair left CE-L2 open and did not establish effective
live Evaluator effort. This live proof supplies that missing evidence.

## Live Executor evidence

| Requirement | Observed evidence |
| --- | --- |
| Expected identity | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` |
| Terminal actual identity | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1`; matched |
| Requested / effective reasoning effort | `off / off` |
| Executor provider calls | 1 |
| Retry / fallback count | 0 / 0 |
| Required tool selection | `write`; hard selection applied once |
| Write tool execution | available; one tool-call event; one execution start and end; executed tool list was `[write]` |
| Allowed path | `proof_target.txt` only |
| Target before | `CE-L1-BASELINE\n`; SHA-256 `be4f8b7684458ce2586c06ef0c81ba4c89204e5c6069df649d7e636588164b5c` |
| Target after | `CE-L2-EXACT-MARKER\n`; SHA-256 `ec2523ddde12832d1c22eca2f9afa7900017e52bed9abeddca42291b5cd495c0` |
| Changed-file list | exactly `proof_target.txt`; one source mutation; no other target source file changed |
| Disposable target Git HEAD | `295c68145b3fbacd67eede2da14d81275f1b53ef` before and after |
| Live Attempt | `attempt-live-a845c6e248ed0f9fda1e039f`; succeeded and identity matched |
| Pi Receipt | `pi-receipt-inv-70853361b42183f949c5eb96`; canonical Receipt validator passed |
| Pi Harness Result | `pi-result-inv-70853361b42183f949c5eb96`; canonical Harness Result validator passed |
| Campaign boundary validation | all checks passed, including one call, zero retry/fallback, allowlist, unchanged Git HEAD, and present Pi evidence |

The Executor invocation ID was
`inv-70853361b42183f949c5eb96`. Its completed checkpoint was bound into the
Evaluator input and copied evidence. Aggregate checkpoint hash:
`78793039806d6c1f2315f710a5031bb2b3f1ecc3cb94bb3f2879d042769caaa3`.

## Live Evaluator evidence

The real bounded evidence packet hash was:

```text
4c2580928f26a80e64f45d17132105a3f50fb02696ef6a7ca9f29d3979f3f7e7
```

The earlier synthetic provider-free packet hash
`9dea5958321255f8080ab19e210e64acb4eb9657721649d8df87c9bccb0d5988`
belongs only to the repair fixture and is not live lifecycle evidence.

| Requirement | Observed evidence |
| --- | --- |
| Expected identity | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1` |
| Terminal actual identity | `deepseek / deepseek-v4-pro / pi-coding-agent@0.82.1`; matched |
| Requested / effective reasoning effort | `high / high` |
| Evaluator provider calls | 1 |
| Retry / fallback count | 0 / 0 |
| Guardian permissions | `files.read` granted for the declared target file; no `files.write`, process, or command permission |
| Tool execution | zero; write tool unavailable |
| Read-only and mutation assertions | `read_only_assertion=true`; `mutation_performed=false` |
| Independent model judgment | `independent_model_judgment=true` |
| Canonical verdict | `passed`; the sole criterion `exact-marker` returned `pass` |
| Pi Receipt | `pi-receipt-inv-ce-l2-evaluator-47c2f209f6c7425ebceb5d86`; canonical Receipt validator passed |
| Pi Harness Result | `pi-result-inv-ce-l2-evaluator-47c2f209f6c7425ebceb5d86`; canonical Harness Result validator passed |
| Live Evaluation | `evaluation-live-67326436ea9a6b777679619b`; schema-valid and identity match |
| Target after Evaluator | unchanged; target fingerprint `a782de1be1b69a141ef40bc5043d8fd1b630ec5c5d99ce8795a6f23763197f91` |

The Evaluator invocation ID was
`inv-ce-l2-evaluator-47c2f209f6c7425ebceb5d86`. Only the bounded packet,
validated verdict, short summary, criterion result, identity, and validation
metadata are recorded. No unrestricted model response or reasoning content
is persisted.

## Final lifecycle records

| Record | Validation result |
| --- | --- |
| Final Campaign input | `campaign-engine/v0` schema and cross-object validation passed |
| Live Evaluation | schema-valid; verdict and acceptance result validated |
| Final Receipt | `receipt-live-67326436ea9a6b777679619b`; schema-valid; binds both RoleBindings, both actual identities, and both Pi invocation Receipt IDs |
| Final CampaignState | `campaign-state-live-67326436ea9a6b777679619b`; schema-valid; `completed`; ordered Attempt, Evaluation, and Receipt references match |
| Final lifecycle result | 2 provider calls total: Executor 1, Evaluator 1; final verdict `passed` |

`CE-L2_EXIT=SINGLE_TASK_SUPERVISED_USABLE` is recorded only after all
these records and links validated.

## Execution-safety posture

| Counter or action | Result |
| --- | ---: |
| Executor / Evaluator provider calls | 1 / 1 |
| Total retries / fallbacks | 0 / 0 |
| Provider / model / harness substitutions | 0 / 0 / 0 |
| Runtime rebinding / automatic repair | 0 / 0 |
| Execution-time commits / pushes / merges | 0 / 0 / 0 |
| Deployments / durable Codexify ingestion | 0 / 0 |

The Codexify checkout remained clean at
`f0d55ddc4d9b7c871b0d86cf500cb35654e1cd0e` through both calls. The disposable
target retained its baseline Git HEAD and the single declared modified file;
no target commit was made.

### Checkpoint-copy validator discrepancy

One local final-validation helper initially expected every one of the 15
files in the frozen Executor checkpoint to appear in the final Evaluator
artifact copy. The runtime's declared final-copy manifest contains 14
artifacts: its ten fixed checkpoint paths plus the live Attempt, interim
Evaluation, interim Receipt, and CampaignState. The helper therefore failed
when it looked for the unlisted Task-state file in the copy.

All 14 artifacts declared by the runtime manifest were checked against the
frozen original checkpoint and matched. The helper was corrected to validate
that declared manifest; final validation then passed. This was a local
validation-helper expectation mismatch, not evidence of runtime data loss.

## Authority and remaining boundary

This result aligns with accepted ADR-068. Guardian remained execution
authority, Campaign Engine owned orchestration and final state, and Pi
remained the invocation substrate. No runtime, schema, Guardian, Pi, ADR, or
release-support contract changed as part of this proof.

Milestone A requires using the one-Task lifecycle on several real but
disposable Task Specs and observing operational friction before adding
scheduling semantics. CE-L3 was not opened, authorized, or executed.
Milestone B and the overall closure Campaign remain open.

Not established by this proof: autonomous Campaign execution, multi-Task
progression, dependency scheduling, background or unattended execution,
automatic retry or repair, provider failover, generalized repository
execution, automatic Git mutation, production readiness, or any widened
release claim.
