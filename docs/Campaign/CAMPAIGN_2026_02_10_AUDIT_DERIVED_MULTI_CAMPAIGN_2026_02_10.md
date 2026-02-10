# Multi-Campaign Receipt

This receipt contains three deterministic campaigns derived from AUDIT_2026_02_10.

- Campaign A: CAMPAIGN_2026_02_10_SECURITY_HARDENING
- Campaign B: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Campaign C: CAMPAIGN_2026_02_10_FOLLOWUP_DRIFT

Each task must enforce:
- Preflight: git status --porcelain -uall must be empty
- Stop on dirty tree with cleanup commands
- Stop on out-of-scope file changes with cleanup commands
