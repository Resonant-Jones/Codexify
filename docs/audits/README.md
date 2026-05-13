# Audits Directory

## Beta Release Sentinel

`scripts/release/beta_release_sentinel.py` generates repo-local, evidence-led beta readiness artifacts.

What it does:
- Collects branch, HEAD, and worktree status.
- Reads the current release-definition checklist from `docs/architecture/00-current-state.md`.
- Tries to run `scripts/audit_platform_readiness.py` and records summary or failure warning.
- Writes deterministic dated artifacts:
  - `docs/audits/generated/YYYY-MM-DD-beta-sentinel.md`
  - `docs/audits/generated/YYYY-MM-DD-beta-sentinel.json`
- Appends an evidence-led dated entry to `CHANGELOG.beta.md`.

What it does not prove:
- It is not release approval by itself.
- It does not widen supported beta scope.
- It does not make cloud-provider support claims.
- It does not claim packaged desktop replaces local Compose.
- It does not claim command bus, delegation, federation, graph writes, or worker-control dispatch are public beta promise.

Manual run:

```bash
python scripts/release/beta_release_sentinel.py \
  --date 2026-05-13 \
  --output-dir docs/audits/generated \
  --changelog CHANGELOG.beta.md
```

Publication boundary:
- Sentinel output is intentionally repo-local and file-output only in this phase.
- Website, email, and Substack publication automation is deferred until the artifact contract stabilizes.
