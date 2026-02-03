# Codex Runner

## Naming standards

Campaign path format (required):
- `docs/Campaign/CAMPAIGN_YYYY_MM_DD.md`
- `docs/Campaign/CAMPAIGN_YYYY_MM_DD_<UPPER_SNAKE+_->.md`

Task path format (Task Schema A only; required):
- `docs/tasks/TASK_YYYY_MM_DD_NNN_lower_snake_slug.md` (NNN is 3-digit zero padded)

If any generated path violates these formats, the runner exits non-zero and writes nothing.

## Usage

Generate only:

```
python codex_runner/runner.py \
  --audit-prompt-file codex_runner/audits/sample_audit_prompt.md
```

Generate + execute:

```
python codex_runner/runner.py \
  --audit-prompt-file codex_runner/audits/sample_audit_prompt.md \
  --execute
```

Multiple cycles + branch-per-campaign:

```
python codex_runner/runner.py \
  --audit-prompt-file codex_runner/audits/sample_audit_prompt.md \
  --cycles 2 \
  --branch-per-campaign
```

Notes:
- `codex exec` must be available in your `PATH`.
- Use `--dry-run` to skip task execution even if `--execute` is set.
