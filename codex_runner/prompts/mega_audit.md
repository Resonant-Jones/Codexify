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
- Audit against the intention packet, but separate repo-grounded findings from unsupported intention claims.
- Prefer discovery-only output when the repo does not support the intention.

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
