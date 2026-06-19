# C06 Proof Pack: Guardian Operator Workspace

---

## C06-T001: Seam Audit (2026-06-19 08:55 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `131197a45` | **Worktree**: clean

### Files Created
- `seam-audit.md` — 8 operator surfaces audited, 5 backend truth surfaces audited, 8 gaps, 9-task backlog
- `backlog.md` — C06-T001 complete, C06-T002 named next
- `proof-pack.md` — this file
- `decision-log.md` — C06-D001 entry

### Inputs Read
All 34 required pre-reads available. No missing inputs.

### Seam Audit Result

**Existing operator surfaces audited (8):**
1. CommandCenterShell — 8-lens shell, no unified workspace lens
2. CodingWorkOrdersPanel — work orders + receipt evidence + tool-turn observability
3. HealthOverview — runtime health verdict
4. HeartbeatStatusPanel — worker heartbeat
5. TraceWorkbench — retrieval posture traces
6. EventConsole — raw event stream
7. CommandCenterUtilityRail — lens navigation
8. CommandCenterBottomDrawer — 4-tab drawer (placeholders)

**Existing backend truth surfaces audited (5):**
1. Command Bus Run Readback — `GET /api/guardian/commands/runs/{run_id}`
2. Command Bus Manifest — `GET /api/guardian/commands/manifest`
3. Tool-Turn Observability Readback — `GET /api/guardian/commands/tool-turns/{message_id}/observability`
4. Work-Order Latest-Run Bridge — `GET /api/coding/work-orders/{id}/latest-run`
5. Receipt Readback — `GET /api/coding/work-orders/{id}/receipts/{receipt_id}`

### Workspace Composition Candidates (10)

| Candidate | Backing Truth | Frontend Surface | Safe Now |
|-----------|--------------|-----------------|----------|
| Work-order status | ✅ C03 | ✅ | ✅ |
| Command-run evidence | ✅ C03 | ❌ | ✅ |
| Tool-turn observability | ✅ C05 | ✅ | ⚠️ Conditional |
| Receipt evidence | ✅ C03 | ✅ | ✅ |
| Runtime/provider status | ✅ C02 | ✅ | ✅ |
| Worker heartbeat | ✅ | ✅ | ✅ |
| Event console | ✅ | ✅ | ❌ (redaction) |
| Command manifest | ✅ C03 | ❌ | ✅ |
| Retrieval posture | ✅ | ✅ | ✅ |
| Bottom drawer receipts | ✅ C03 | ⚠️ Placeholder | ⚠️ Partial |

### Safety and Redaction Boundaries
10 boundaries enumerated — all aligned with C05-T002/C05-T003/C05-T005 proof.

### Gaps Recorded (8)
1. Receipt linkage deferred
2. No unified workspace lens
3. No workspace surface contract
4. Tool-turn conditional on assistant_message_id
5. Event console not redaction-reviewed
6. Command manifest not surfaced
7. Bottom drawer receipts placeholder
8. Latest-run bridge not surfaced

### Recommended C06 Backlog
9 tasks named (C06-T001 through C06-T009).

### Validation
```
git diff --check              clean
python3 scripts/validate_docs.py passed
```

### Gate Decision
**`go`** — C06-T001 accepted. C06-T002 may proceed.

### Next Task
**C06-T002: Define Guardian Operator Workspace surface contract**
