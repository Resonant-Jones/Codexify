# Campaign: AUDIT_2026_02_16 security-first closure

Source:
- audit_id: AUDIT_2026_02_16
- branch: campaign/2026-02-15/2026-02-16-compiled-audit
- commit: 1af5e5ec1f35e65a501ae33fa50f3f91142e4ded

Goal:
- Close RISK items first, then MVP core-loop closure gaps, then docs traceability drift.

Finding coverage:
- Security: FINDING-2026-02-16-009, -010, -011
- Core loop: FINDING-2026-02-16-001, -002, -003, -004, -005, -006, -007, -008
- Follow-up/docs: FINDING-2026-02-16-012, -013

Runner invariants:
- Every task starts with preflight clean-tree gate.
- Dirty tree or out-of-scope edits cause immediate STOP + exact cleanup commands.
- Decisions are explicit dedicated tasks (TASK-007, TASK-009).

Execution order:
1) TASK-001..TASK-004 (RISK + blocking correctness)
2) TASK-005..TASK-012 (MVP closure + contract alignment)
3) TASK-013 (matrix/harness traceability)

## Task Mapping

TASK-2026-02-16-001 -> [bd8941f99d2f0e111f6ad850b34be8d2b90905ad, 36de5dca5f96a739a27bdad53cdeb30aa4bf38ef]
