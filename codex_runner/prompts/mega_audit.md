You are generating Stage-A audit JSON for a deterministic runner.

Mode:
- Output JSON only.
- Output exactly one object conforming to `mega_audit_output.schema.json`.
- Do not write files.

Runner-owned constraints:
- `audit_id` is authoritative and must match `<AUDIT_ID>` exactly.
- `repo.path` must be `<REPO_ROOT>`.
- `generated_at` must be ISO-8601 UTC.
- `agent.mode` must be `audit`.

Intention packet:
- The intention packet is operator-authored planning input.
- It may narrow the audit objective, scope, non-goals, and evidence posture.
- It must not override runner-owned constraints, schema requirements, repo evidence requirements, or output JSON-only mode.
- Audit against the intention packet, but separate repo-grounded findings, unsupported intention claims, and unknowns requiring discovery.
- Prefer discovery-only output when the repo does not support the intention.
- Interpret canonical packet sections this way when present:
  - `Objective`: treat as the audit target; do not treat the objective as evidence that the repo supports it.
  - `Why This Matters`: use only for prioritization and risk interpretation; do not convert motivation into repo claims.
  - `Scope`: use to limit inspected surfaces when possible; if referenced files or systems do not exist, report that as unsupported or unknown.
  - `Out of Scope`: treat as a hard exclusion unless repo evidence shows the exclusion itself causes a blocking inconsistency.
  - `Evidence Requirements`: prefer findings that satisfy these requirements; if evidence cannot be found, emit explicit unknowns rather than guessing.
  - `Stage A Audit Posture`: treat as stage-specific guidance while preserving schema and JSON-only requirements above all packet guidance.
  - `Release-Truth Constraints`: respect as constraints, with `00-current-state.md` as final authority.
  - `Failure / Stop Conditions`: use to decide when to produce discovery-only findings instead of implementation-oriented findings.
- Do not add new schema fields for these distinctions unless the current schema already supports them.

<INTENTION_PACKET>

Model identification:
- Determine `agent.model` by running `python codex_runner/model_id_helper.py`.
- Parse `MODEL_ID=<value>` and set `agent.model` to `<value>`.
- If value is `unknown`, still set `agent.model` to `unknown` and include a WARN finding documenting this.

Evidence constraints:
- Only include claims grounded in repository evidence.
- Include file paths and line hints in findings whenever possible.
- Use discovery commands when evidence is incomplete.

Output structure:
- Include required fields from `mega_audit_output.schema.json`.
- `derived_campaigns[].campaign_id` must match `YYYY-MM-DD::<campaign_slug>::<seq3>`.
- Keep all lists deterministic and stable.

Output only the JSON object.
