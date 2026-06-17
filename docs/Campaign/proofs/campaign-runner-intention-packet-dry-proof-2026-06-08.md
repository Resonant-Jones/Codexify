# Campaign Runner Intention Packet Dry Proof - 2026-06-08

## Scope

This is a dry planning/materialization proof only for the Campaign Runner Intention Packet path.

The intended proof target was the provider-broker readiness example packet:

- `docs/Campaign/examples/campaign-runner-intention-packet-provider-readiness.md`

The proof checked whether the current runner can safely demonstrate this chain without provider calls:

1. intention packet accepted
2. Stage A audit prompt/output path
3. Stage B campaign prompt/output path
4. materialized campaign and task artifacts
5. review-only `PROMPT_<task_slug>.md` prompt artifacts

Result: the full CLI proof stopped on a safe-mode blocker before running Campaign Runner. The current `--dry-run` path is not provider-free.

## Non-Goals

- This proof did not execute generated task prompts.
- no generated task was executed.
- This proof did not run wet provider execution.
- This proof did not call Pi, Codex, Claude, DeepSeek, Minimax, OpenAI, or any external provider.
- This proof did not prove Pi broker execution.
- This proof did not prove provider support.
- This proof did not change runtime behavior.
- This proof did not change queue, worker, route, database, or UI behavior.
- This proof did not widen release support.
- This proof did not modify `docs/architecture/00-current-state.md`.
- This proof did not create or modify ADRs.

## Pre-Read

Read before selecting the command:

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/campaign-runner-intention-packet-contract.md`
- `docs/Campaign/templates/campaign-runner-intention-packet-template.md`
- `docs/Campaign/examples/campaign-runner-intention-packet-provider-readiness.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/agent-tool-loop-contract.md`
- `codex_runner/README.md`
- `codex_runner/runner.py`
- `codex_runner/prompts/mega_audit.md`
- `codex_runner/prompts/audit_report_to_campaign_runner.md`
- `codex_runner/schemas/campaign_set.schema.json`

Relevant interpretation:

- `docs/architecture/00-current-state.md` remains authoritative for current release truth.
- The Intention Packet is operator-authored planning input, not runtime proof.
- Reviewable task prompt artifacts are not execution authority.
- `--dry-run` must not be treated as no-provider proof unless the runner path actually avoids provider calls.

## Environment

Pre-run workspace state:

```text
Command: git status --short --branch --untracked-files=all
Output:
## codex/add-campaign-intent-packet-seam...origin/codex/add-campaign-intent-packet-seam [ahead 1]
```

```text
Command: git rev-parse --abbrev-ref HEAD
Output:
codex/add-campaign-intent-packet-seam
```

```text
Command: git rev-parse HEAD
Output:
a679b24a0a7fbcdf6a213357181ea54ea10f5e77
```

Worktree clean before proof: yes.

## Commands

Candidate full dry command that was considered but not executed:

```bash
python codex_runner/runner.py \
  --repo-root /Volumes/Dev_SSD/Codexify-main \
  --audit-prompt-file codex_runner/prompts/mega_audit.md \
  --audit-schema-file codex_runner/schemas/mega_audit_output.schema.json \
  --compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
  --campaign-set-schema-file codex_runner/schemas/campaign_set.schema.json \
  --intention-packet-file docs/Campaign/examples/campaign-runner-intention-packet-provider-readiness.md \
  --dry-run
```

Reason it was not executed:

- `codex_runner/runner.py` loads the intention packet and renders Stage A, but then calls `run_provider_exec(...)` for Stage A audit before any Stage A output exists.
- It then calls `run_provider_exec(...)` again for Stage B campaign compilation.
- Materialization happens only after the provider-produced Stage B payload is merged.
- Therefore the CLI `--dry-run` mode is task-execution dry, not provider-free.

Inspection commands used:

```bash
nl -ba codex_runner/runner.py | sed -n '1728,1830p'
nl -ba codex_runner/runner.py | sed -n '1890,2160p'
nl -ba codex_runner/README.md | sed -n '120,190p'
nl -ba tests/codex_runner/test_runner_v2.py | sed -n '309,435p'
```

Safe validation commands run after documentation capture:

```bash
test -f docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
grep -q "dry planning/materialization proof only" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
grep -q "no generated task was executed" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
grep -q "No provider support or Pi execution was proven" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
./.venv/bin/python -m pytest -q codex_runner/tests/test_intention_packet_prompting.py
./.venv/bin/python -m pytest -q tests/codex_runner/test_runner_v2.py
git diff --check
python3 scripts/validate_docs.py
```

## Observed Outputs

Runner inspection showed:

- `codex_runner/runner.py` reads the intention packet with `load_intention_packet(...)`.
- `run_inputs` includes `intention_packet_sha256` when an intention packet file is present.
- Stage A prompt rendering writes `audit_input_prompt.md`.
- Stage A then invokes `run_provider_exec(...)` with `stage="audit"`.
- Stage B prompt rendering writes `compiler_input_prompt.md`.
- Stage B then invokes `run_provider_exec(...)` with `stage="compile"`.
- Campaign and task materialization occurs later through `materialize_campaign_artifacts(...)`.
- `termination_reason = "dry_run_selected_campaign_materialized"` is reached only after provider-backed Stage A and Stage B have completed.

Safe local tests covered the no-provider seams that already exist:

- `codex_runner/tests/test_intention_packet_prompting.py` covers fallback injection, explicit packet injection, canonical packet doctrine, and placeholder isolation.
- `tests/codex_runner/test_runner_v2.py` covers deterministic materialization, sequence-aware task paths, `PROMPT_<task_slug>.md` generation, lane-specific prompt shapes, single fenced prompt artifacts, and missing-lane discovery fallback.

No full runner CLI artifact set was generated in this proof because doing so would require provider-backed Stage A and Stage B execution.

Validation outputs:

```text
Command: test -f docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
Result: passed
```

```text
Command: grep -q "dry planning/materialization proof only" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
Result: passed
```

```text
Command: grep -q "no generated task was executed" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
Result: passed
```

```text
Command: grep -q "No provider support or Pi execution was proven" docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md
Result: passed
```

```text
Command: ./.venv/bin/python -m pytest -q codex_runner/tests/test_intention_packet_prompting.py
Output:
..........                                                               [100%]
```

```text
Command: ./.venv/bin/python -m pytest -q tests/codex_runner/test_runner_v2.py
Output:
....................                                                     [100%]
```

```text
Command: git diff --check
Result: passed
```

```text
Command: python3 scripts/validate_docs.py
Output:
Docs validation passed: required architecture docs, README links, and source headings verified.
```

## Artifact Inventory

Created by this proof slice:

- `docs/Campaign/proofs/campaign-runner-intention-packet-dry-proof-2026-06-08.md`

Clarified because the proof revealed missing guidance:

- `codex_runner/README.md`

`codex_runner/README.md` needed updates: yes. The dry proof revealed that the existing README listed `--dry-run` without explicitly saying that Stage A and Stage B still use the configured provider lane.

Not created by this proof:

- `docs/_audits/...`
- `docs/_campaign_runs/...`
- `docs/Campaign/CAMPAIGN_*.md`
- `docs/tasks/.../TASK_*.md`
- `docs/tasks/.../PROMPT_*.md`

Those artifacts were intentionally not generated because the available CLI path would call the provider lane first.

## Prompt Artifact Inspection

No repo-local `PROMPT_<task_slug>.md` artifact was generated by the full CLI proof.

Existing no-provider tests inspect temporary prompt artifacts and assert:

- prompt artifact path ends with `PROMPT_alpha_2026_03_12.md`
- prompt artifact includes `This is a reviewable Campaign Runner task prompt artifact`
- standard lane prompt includes `Prompt shape: Standard Codexify Task`
- architecture-impact lane prompt includes `ADR impact:`, `Current-truth anchors:`, `Proof surface:`, and `Documentation follow-through:`
- discovery lane prompt says `Read-only investigation first.`
- discovery lane prompt says `Do not commit if no files change.`
- generated prompt content is contained inside exactly one fenced Markdown code block
- missing `task_lane` defaults to discovery with a `TODO(operator):` note

These assertions prove the materialization seam, not an end-to-end provider-backed planning run.

## Release-Truth Boundary

No provider support or Pi execution was proven.

This proof does not prove:

- wet execution
- Pi SDK execution
- provider-broker readiness
- UI dispatch
- lease allocation
- live agent execution
- merge automation
- release-ready autonomous execution

`docs/architecture/00-current-state.md` remains the current release-truth authority. The supported path remains local Docker Compose with local-only provider posture unless separately proven and documented under the current release-truth process.

## Pass / Fail Result

Result: stopped on a safe-mode blocker for the full intention-packet-to-materialized-artifacts CLI proof.

Partial no-provider proof status: passed for existing prompt rendering and materialization seams via focused tests.

The blocker is precise: Campaign Runner does not currently expose a provider-free fixture/materialization command that accepts an intention packet plus prevalidated Stage A/Stage B JSON and then materializes artifacts.

## Known Limitations

- The provider-broker readiness example packet remains illustrative planning input.
- This proof did not produce Stage A audit output from a provider.
- This proof did not produce Stage B campaign output from a provider.
- This proof did not materialize repo-local campaign, task, or prompt artifacts from the full CLI.
- The no-provider materialization evidence comes from unit tests using temporary directories.
- The proof cannot claim provider-broker readiness, Pi execution, or runtime support.

## Follow-Up Tasks

- Add a separate provider-free Campaign Runner proof mode that accepts explicit fixture Stage A and Stage B JSON, validates schemas, injects the intention packet into recorded prompts, and materializes artifacts into a temporary or operator-selected output directory.
- Add documentation for that provider-free proof mode once implemented.
- Capture a passing dry proof artifact after that safe mode exists.
- Capture wet execution proof only as a separate operator-approved task with explicit provider and Pi boundaries.

## Follow-Up Resolution

The original proof stopped because `--dry-run` still invoked the configured provider lanes for Stage A audit and Stage B campaign compilation before materialization.

The follow-up implementation task adds the missing provider-free fixture/materialization mode through `--materialize-from-fixtures`, `--audit-json-file`, and `--campaign-json-file`.

The original proof remains historically accurate. It documented the missing safe-mode seam before this follow-up existed.

A future proof should rerun with fixture Stage A and Stage B JSON using the new mode, confirm schema validation, and inventory the generated campaign, task, and review-only prompt artifacts without claiming wet provider, Pi, runtime, or release support.
