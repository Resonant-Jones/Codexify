# Campaign Runner Intention Packet Contract

Purpose: Define the bounded operator-authored intention packet seam for Campaign Runner Stage A audit and Stage B campaign compilation.
Last updated: 2026-06-05
Source anchors:
- codex_runner/runner.py
- codex_runner/prompts/mega_audit.md
- codex_runner/prompts/audit_report_to_campaign_runner.md
- codex_runner/schemas/mega_audit_output.schema.json
- codex_runner/schemas/campaign_set.schema.json
- docs/architecture/00-current-state.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md
- docs/architecture/adr/036-campaign-runner-provider-adapter-contract.md
- docs/architecture/adr/037-campaign-runner-pi-provider-broker.md

## Purpose

Campaign Runner has two prompt-governed planning stages:

- Stage A audits the repository and emits `mega_audit_output.schema.json`.
- Stage B compiles Stage-A evidence into campaigns and tasks that conform to `campaign_set.schema.json`.

The Intention Packet gives both stages the same explicit operator-authored objective without requiring ad hoc edits to the prompt templates.

The packet exists to help Campaign Runner produce better bounded campaigns, not broader autonomy.

## Scope

The Intention Packet seam applies only to Campaign Runner prompt assembly for:

- Stage A audit prompting
- Stage B campaign compilation prompting

The packet may constrain:

- audit objective
- scope
- non-goals
- evidence requirements
- campaign-shaping rules
- Codexify task-lane expectations

Nodes in scope:

- operator workstation running `codex_runner/runner.py`
- local repository checkout being audited
- provider adapter lane used by Campaign Runner
- persisted runner artifacts under `docs/_audits/` and `docs/_campaign_runs/`

Trust boundaries:

- operator-authored packet text is trusted only as planning input
- repository evidence remains the source for findings
- runner-owned identifiers and schema validation remain runner authority
- provider output remains untrusted until schema validation passes

Threat model:

- honest-but-buggy operators may overstate the intended target
- provider output may follow packet language beyond repo evidence
- packet text may contain strings that look like runner placeholders
- malicious packet text must not become executable code or override runner-owned values

## Non-Goals

This seam does not:

- add autonomous execution
- add direct Codex or Claude execution paths
- change Pi broker execution semantics
- change provider behavior
- change queue, worker, route, UI, or database behavior
- change schema-required output shapes
- bypass schema validation
- authorize merge automation, lease allocation, or live agent execution
- widen current release support claims
- make the packet an ADR
- make the packet runtime proof

## Contract Shape

The packet is plain UTF-8 markdown text supplied with:

```bash
python codex_runner/runner.py --intention-packet-file /path/to/intention.md
```

When provided:

- the runner reads the file as UTF-8 text
- missing files fail closed
- directory paths fail closed
- the text is treated as inert prompt context
- the same resolved packet text is injected into Stage A and Stage B
- the packet hash is included in deterministic run inputs

When omitted, the runner injects this fallback text:

```text
No explicit intention packet was provided. Use the default repository-grounded audit posture and do not infer a narrower target.
```

The injection placeholder is:

```text
<INTENTION_PACKET>
```

The packet cannot override runner-owned placeholders such as:

- `<AUDIT_ID>`
- `<REPO_ROOT>`
- `<RUN_ID>`
- `<PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>`
- `<AUDIT_JSON>`

The runner replaces placeholders only in the prompt template, not inside inserted packet text or pasted Stage-A JSON.

## Canonical Template and Example

The default operator-facing shape for intention packets is the canonical template:

- [`Campaign Runner Intention Packet Template`](../Campaign/templates/campaign-runner-intention-packet-template.md)

The repo also includes one illustrative example packet:

- [`Provider Readiness Intention Packet Example`](../Campaign/examples/campaign-runner-intention-packet-provider-readiness.md)

Examples are planning artifacts only. They are not proof that a campaign has run, that provider-broker readiness has been validated, or that runtime support exists.

A completed packet must still be read under this contract's invariants, including schema authority, runner-owned constraints, provider governance, Guardian ownership, Pi broker boundaries, and `00-current-state.md`.

## Stage Interpretation Rules

Stage A audits against the packet but must distinguish:

- repo-grounded evidence and findings
- unsupported intention claims
- unknowns requiring discovery

Stage B compiles only from Stage-A evidence. It uses the same packet to filter, prioritize, and constrain campaign synthesis, but the packet cannot create implementation authority by itself.

Discovery-only output is preferred when the packet objective is not repo-supported or when required evidence is missing, contradictory, or only aspirational.

Existing schemas remain authoritative for both stages:

- Stage A must conform to `mega_audit_output.schema.json`.
- Stage B must conform to `campaign_set.schema.json`.
- Packet sections may guide interpretation, but they do not add schema fields, bypass validation, or override runner-owned constraints.

## Example Intention Packet

```markdown
# Campaign Runner Intention Packet

Objective:
- Audit whether Campaign Runner can support an explicit operator-authored planning input for Stage A and Stage B.

Scope:
- codex_runner/runner.py
- codex_runner/prompts/mega_audit.md
- codex_runner/prompts/audit_report_to_campaign_runner.md
- codex_runner/tests/
- docs/architecture/

Non-goals:
- Do not add provider behavior.
- Do not add autonomous execution.
- Do not change schemas unless the audit proves a strict need.

Evidence posture:
- Prefer repo-grounded findings.
- Separate implemented behavior from future planning.
- If the repo cannot support an implementation task safely, produce a discovery task.

Campaign shaping:
- Keep tasks independently mergeable.
- Keep release claims subordinate to docs/architecture/00-current-state.md.
```

## Stage A Responsibilities

Stage A must:

- audit against the intention packet
- keep `mega_audit_output.schema.json` authoritative
- preserve runner-owned constraints
- ground findings in repository evidence
- separate repo-grounded findings from unsupported packet claims
- emit discovery-oriented findings when the repository does not support the requested intention
- avoid presenting packet language as proof of runtime capability

Stage A must not:

- infer runtime support from the packet
- invent findings unsupported by repository evidence
- override `audit_id`, `repo.path`, JSON-only mode, or schema requirements

## Stage B Responsibilities

Stage B must:

- use the packet only to interpret and filter Stage-A findings
- keep `campaign_set.schema.json` authoritative
- preserve independently mergeable task scope
- prefer discovery tasks over speculative implementation when evidence is insufficient
- keep campaign and task output grounded in Stage-A evidence
- avoid widening release claims or runtime support claims

Stage B must not:

- invent campaigns or tasks unsupported by Stage-A evidence
- treat the packet as runtime proof
- add git commit instructions unless the current task artifact contract supports them safely
- bypass task scope, file-path, or schema constraints

## Invariants

- The Intention Packet is an operator-authored planning artifact.
- It is not runtime proof.
- It is not an ADR by itself.
- It cannot override schemas.
- It cannot override runner-owned constraints.
- It cannot override provider governance.
- It cannot override Guardian ownership.
- It cannot override Pi broker boundaries.
- It cannot override `00-current-state.md`.
- It cannot introduce autonomous execution.
- It cannot authorize direct provider CLI execution.
- It cannot mutate pasted Stage-A JSON.
- Existing provider output validation remains authoritative.

## Failure Policy

The runner fails closed when:

- `--intention-packet-file` points to a missing file
- `--intention-packet-file` points to a directory
- the file cannot be decoded as UTF-8 text

The runner does not parse, execute, or transform the packet as code.

If the packet asks for behavior unsupported by repository evidence, Stage A should make that lack of support explicit and Stage B should prefer discovery tasks or no campaign over speculative implementation.

## Relationship to Pi Invocation Boundary

The Intention Packet is upstream planning context. It is not a Pi invocation envelope, Pi receipt, harness artifact, command authorization, or result-return proof.

The Pi Invocation Boundary remains the governing contract for future Pi-like harness invocation, including Guardian ownership, command authority, result return, lineage, and provider-lane separation.

This seam does not:

- implement a Pi SDK call
- change Pi broker behavior
- bypass Guardian-mediated coding-agent execution doctrine
- grant command authority to packet text
- make Campaign Runner depend on Pi internals

## Relationship to Current Release Truth

`docs/architecture/00-current-state.md` remains the short-horizon release truth gate.

The Intention Packet can align Campaign Runner planning around a specific objective, but it cannot prove that the objective is implemented, supported, release-ready, or end-to-end live.

Current release truth still forbids assuming:

- UI dispatch
- lease allocation
- live agent execution
- merge automation
- autonomous self-modification
- provider support beyond the proven supported path

This contract adds a bounded prompt-intention input seam only.
