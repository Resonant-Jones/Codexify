# SECURITY REWRITE NOTICE

- Rewrite date (UTC ISO-8601): `2026-02-23T22:10:08Z`
- Pre-rewrite default-branch baseline: `88af0e13`
- Post-rewrite default-branch commit: `PENDING_AFTER_FORCE_PUSH`
- Scope: all local branches and tags were rewritten and force-pushed.

## Required Repository Invalidation

All collaborators and CI runners must invalidate stale refs and local caches after this rewrite.

### Required Re-clone/Reset Commands

```bash
git fetch --all --prune --tags
git checkout main
git reset --hard origin/main
```

If uncertain or diverged: fresh clone required.

### Optional Hard-Reset Fallback

If the local clone behaves unexpectedly after the above reset, delete the clone and create a new one:

```bash
cd ..
rm -rf Codexify
git clone git@github.com:Resonant-Jones/Codexify.git
```

### CI / Cache Invalidation Reminder

- Clear CI workspace caches that may contain old refs or artifacts.
- Re-run secret scanning on active refs:
  - `gitleaks dir . --exit-code 1`
  - `gitleaks git . --log-opts="--all" --exit-code 1`
