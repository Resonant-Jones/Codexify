# Explicit-model authority requalification

Date: 2026-10-08 (America/New_York). Workflow: architecture-impact.
Disposition: **HOLD — test contradiction reconciled; current-tip live proof blocked.**
Evidence classes: `proven-test`, `proven-code-path`, `documented-contract`.
No production or test change was necessary. No new live chat qualification is
claimed by this receipt.

## Evaluated source and ownership

| Field | Observed value |
| --- | --- |
| Execution host | `VaultNode.local` |
| Evaluated commit | `5c6e2ca76bb9680457594bb5092868338ee5f75a` |
| Branch | `codex/exact-model-requalification-20261008` |
| Isolated physical worktree | `/Volumes/Dev_SSD/offload/codex/worktrees/exact-model-requalification/Codexify-main` |
| Remote-main verification | `git ls-remote origin refs/heads/main` matched evaluated commit |
| Local `main` | `f09d53e211b5ccc1a49d0fca7dd27d9cfcff9d50`, 4 ahead / 9 behind `origin/main` |
| Source checkout | `codex/invocation-scoped-execution-binding` at `82ebfba3d4c29da93abd0eb1f850da07c2bee846`, with unrelated untracked work |
| Checkout holding local `main` | `/Volumes/Dev_SSD/weekly-mainline-release-audit-20261002`, with an unrelated staged Dev Log deletion |

The worktree census also found the existing chat-runtime worktrees and concurrent
embedding work. None was modified, reset, synchronized, or adopted. The verified
remote-main commit was selected without reconciling either active checkout.
The new worktree was clean before validation. Initial status inspection hit a
Git LFS metadata permission error; the same inspection and task-branch creation
succeeded with approved metadata access. No tracked content was repaired for it.

## Source of the disagreement

The [2026-09-22 authority repair](./2026-09-22-explicit-local-model-authority-repair.md)
recorded a neighboring test that omitted `requested_model` and
`selection_source=explicit` and observed an ambient egress-policy error instead
of the intended model-unavailable error. That was a fixture/authority mismatch,
not evidence that a correctly admitted explicit request should fall back.

The implementation repair is already in mainline commit
`7006ecf740e8056a66bc06ae5be312a7bc52fa42` (`Enforce explicit local model authority`).
The fixture correction is already in mainline commit
`20bf69b88b6651b0d1d47916b04f3b684720f743` (`Align chat fixtures with canonical acceptance`):

- settings use `_env_file=None`;
- synthetic catalog validation is controlled by the routing test;
- the unavailable-model task carries its requested model and explicit provenance;
- fallback and context-construction spies must remain unused.

Current-main reproduction did **not** reproduce the historical failure. The
remaining worker/test-contradiction claim in current-state was stale. Production
refactoring or another fixture change would not be justified by this result.

Code inspection confirms `_compat_resolve_task` checks explicit local text
selection against inventory before dispatch, retains the requested model and
explicit provenance on rejection, and supplies false attempted/fallback/executed/
completed truth. The local resolver rejects unavailable inventory or an absent
exact model. Existing non-explicit degraded-selection behavior remains separate.

## Focused validation

Executed from the isolated worktree root with the existing host dependency
environment, Python 3.12.13 and pytest 8.4.2:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q tests/workers/test_chat_worker_explicit_model_authority.py guardian/tests/workers/test_chat_worker_provider_resolution.py tests/test_local_model_default_authority.py tests/core/test_chat_completion_service_model_selection_trace.py
```

**PASS: 23 tests, exit 0.** The repository adds quiet output and an ignore rule
for `guardian/tests`. An explicit collection check with `--collect-only -o
addopts= -q` over the same four files confirmed all 23 cases, including all 11
cases in the named Guardian provider-resolution file. The historical failing
case was therefore exercised, not silently omitted.

The worker regression proves, with synthetic inventory and spies:

- exactly one `task.failed`, no `task.completed`;
- requested model and `selection_source=explicit` survive;
- `failure_kind=local_model_unavailable`;
- accepted true; attempted, fallback attempted, executed, completed, and visible
  output false;
- zero provider-execution, fallback, and assistant-persistence calls;
- turn-lock release with the original owner.

Advertised exact models, the ordinary default `local-chat` selection, neighboring
provider authority, and selection-trace tests also pass. These are focused tests,
not live rejection or successful persisted recovery evidence.

## Live-runtime preflight and stop condition

The [2026-10-02 runtime receipt](./2026-10-02-main-current-tip-chat-runtime.md)
provides earlier bounded ordinary-chat and unavailable-model evidence at
`1c3878697b17cfe830774870494461cc37772a68`. It is not qualification of this
evaluated commit. Its method used isolated stores and six refreshed code
participants with source/mount identity, API events, PostgreSQL readback, and
Redis lock evidence. Its private `/private/tmp` harness directory is no longer
present on VaultNode.

Read-only live observations on 2026-10-08:

| Surface | Observation |
| --- | --- |
| Docker VM | 4 CPUs, 8,320,294,912 bytes RAM (about 7.75 GiB) |
| VM memory snapshot | `MemAvailable=2276668 kB` (about 2.17 GiB), `MemFree=405452 kB` |
| Memory pressure | `some avg60=2.89`, `full avg60=2.43`; active memory stalls already present |
| VM disk | 45.8 GiB available; disk is not the immediate constraint |
| Existing candidate | `codexify_candidate_28c95_20261005`, older `goal-integrated-a165a3447` image |
| Other active workload | Private Preview backend and workers plus disposable PostgreSQL containers |
| Earlier proof project | Four `codexify_chat_proof_f091_20261002` workers restarting; not owned by this task |
| Whoosh'd inventory | `local-chat` advertised, physical display `Gemma 4 12B IT QAT 4-bit`; metadata reported `model_lifecycle=unloaded` |

Comparable observed backend, chat, chat-embedding, document-embedding, warmup,
frontend, PostgreSQL, Redis, and Neo4j services total roughly 2.4 GiB before
additional startup/generation pressure. This is a capacity estimate, not a
measured requirement for a new stack. Available headroom plus current memory
pressure did not establish that the existing proof topology could be started
safely alongside unrelated workloads. The existing candidates also do not prove
the selected source revision. This triggers the task's safe-resource stop
condition; no inference request or new proof stack was started.

No existing service was stopped, restarted, repointed, or adopted. No queue was
cleared and no volume was removed. Inventory reads do not establish provider
execution, provider idleness, or chat readiness.

Sanitized preflight command receipts are retained in
`/private/tmp/codexify-explicit-model-requalification-20261008/` (directory 0700,
files 0600), including refs, containers, memory, disk, inventory, and fixture
history. The later captured resource samples are additional observations, not
the exact earlier snapshot quoted above. No credentials were recorded.

## Gate disposition and smallest prerequisite

| Obligation | Current evaluated-tip evidence |
| --- | --- |
| Reproduce/reconcile worker-test contradiction | PASS; corrected fixture already on mainline |
| Explicit rejection, provenance, no dispatch/fallback/persistence, truthful terminal metadata, lock release | PASS in focused tests; live proof not run |
| Subsequent ordinary local-chat completion and assistant persistence | Not run live |
| Exact-model runtime qualification | **HOLD** |
| Full supported-Compose release qualification | **HOLD**, unchanged |

Smallest prerequisite: provide sufficient independent Docker capacity for a
Goal-owned supported-Compose proof stack, or explicitly assign a quiescent
candidate and authorize adoption of the frozen evaluated source. Capacity
changes or lifecycle operations affecting other workloads require their owner's
authorization. Then run one unavailable explicit request followed by an ordinary
local turn, preserving task/turn/request identities and collecting dispatch,
terminal/outbox, PostgreSQL assistant-count, and Redis lock evidence.

ADR impact: aligned with ADR-069, ADR-074, and ADR-087; no new or superseding ADR.
The supported profile owns provider policy; explicit selection cannot silently
be substituted; Whoosh'd owns physical route resolution; durable task/message
truth is distinct from queue acceptance and event visibility. No deadline,
routing, provider, persistence, ownership, or release semantics changed.

Documentation follow-through is limited to this receipt and the stale
worker/test-contradiction claim in `00-current-state.md`. The live gate remains
unchecked. Browser projection, import-to-recall, restart, broader Beta, and
Goal 02 are deferred. No push or merge is authorized.

`python3 scripts/validate_docs.py` (host Python 3.14.4) and `git diff --check`
passed. No additional runtime tests apply to these documentation-only edits.
The documentation commit identity is reported in the task closeout; the evaluated
source SHA above excludes that commit.
