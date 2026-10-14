# Campaign Engine optional required-tool selection repair

Date: 2026-09-29

Lane: architecture-impact implementation repair, aligned with ADR-068

Posture: provider-free deterministic proof; no release or CE-L3 claim

## Trigger and boundary

The first real Milestone A Makefile Task used a live Executor with globally
hard-selected `write`. The provider replaced most of the authorized Makefile.
The Campaign's changed-path boundary accepted the edit because only the
allowed file changed. The one authorized `make PYTHON=python3 docs` validation
attempt failed, so the Campaign stopped before Evaluator, Receipt, CampaignState,
and commit. This was a correct safety result; the failed Campaign and its dirty
disposable target were not resumed.

The earlier CE-L1 proof explicitly used `write` to replace a tiny proof file.
It proved bounded mutation capability, not a general repository editing
strategy. The live Executor previously assigned
`LIVE_EXECUTOR_REQUIRED_TOOL_NAME = "write"` to every preparation and prompt.

## Repair

The locked live Executor RoleBinding now has an optional `required_tool_name`.
The only supported explicit value is `"write"`; it retains the existing
mandatory-action prompt and first-provider-turn hard-selection path. Absence
resolves to `None`, omits that prompt clause, and lets Pi choose tools within
the unchanged Guardian grants and allowed-file boundary. Campaign input hashing
covers the field. Pre-invocation drift checks re-read the locked binding and
recompose the prompt from it, rather than trusting a mutable preparation or a
global default. Unknown explicit names fail before provider invocation.

Evaluator checkpoint preflight now compares the preparation selection with
the original locked Executor binding. It requires positive, internally
consistent changed-file evidence in either mode. It no longer requires a
proof-only `"write"` declaration, so a valid ordinary Executor checkpoint can
reach the same read-only Evaluator. Filesystem readback, allowed-path checks,
Git HEAD protection, Task validation, and independent Evaluator judgment remain
in force. This exact Evaluator adjustment and its focused tests were separately
authorized by the operator during the repair.

## Deterministic evidence

Provider-free fixtures keep explicit `"write"` where they reproduce the CE-L1
proof. Focused tests cover optional and explicit schema values, unsupported
names, ordinary prompt and fake-invoker `None`, an allowed mutation, zero
mutation, out-of-scope modification/creation/deletion, both Campaign-input
drift directions, a forged internally consistent preparation, explicit-write
evidence, Task validation sequencing, and a complete ordinary-Executor to
read-only-Evaluator fake lifecycle. The original live Makefile Task was not
rerun. Provider calls: **0**. CE-L3: **not entered**.

## Validation record

| Check | Result |
| --- | --- |
| Focused Campaign schema, live Executor, and live Evaluator tests | Passed together with provider-free fakes |
| Ruff on changed Python surfaces | Passed; existing `pyproject.toml` deprecation advisory only |
| `PYTHON=.venv/bin/python make docs` | Passed: docs and diagram checks; pre-existing duplicate Make target warning |
| `git diff --check` | Passed |

The existing duplicate Make target warning remains expected until the separate
Makefile Task succeeds. These local checks do not establish a successful live
ordinary-tool-selection provider run or a release-support change.
