You are generating Stage-A audit JSON for a deterministic runner.

Mode:
- Output JSON only.
- Output exactly one object conforming to `mega_audit_output.schema.json`.
- Do not write files.

Runner-owned constraints:
- `audit_id` is authoritative and must match `AUDIT_c0554e70793a` exactly.
- `repo.path` must be `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify`.
- `generated_at` must be ISO-8601 UTC.
- `agent.mode` must be `audit`.

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
