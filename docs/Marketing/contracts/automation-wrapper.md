# Marketing Automation Wrapper (V1)

## Purpose

Provide a stable wrapper around `generate-marketing` for scheduled or repeated runs while preserving draft-only governance and evidence-bound claims.

## Command

```bash
./run-marketing-automation \
  --date 2026-05-12 \
  --campaign-suffix MARKETING_V1 \
  --audience local-first-builders \
  --channels website,social,community \
  --mode draft
```

## Campaign ID Derivation

If `--campaign-id` is not supplied, the wrapper builds:

`CAMPAIGN_<YYYY_MM_DD>_<SUFFIX>`

Example:

`CAMPAIGN_2026_05_12_MARKETING_V1`

This preserves deterministic overwrite semantics for reruns on the same day/suffix.

## Governance Guarantees

- Mode stays `draft` only.
- Approval state remains `draft`.
- No-evidence/no-claim validation is enforced by the underlying generator.
- Run history remains append-only in `docs/Marketing/generated/history/run-history.jsonl`.

## Scheduling Notes

V1 scheduling is manual wrapper invocation or external scheduler invocation (cron/launchd/Codex automation).
The wrapper does not auto-commit, auto-publish, or auto-approve.
