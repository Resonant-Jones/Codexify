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

---

## C06-T002: Surface Contract (2026-06-19 09:10 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `905234bcb` | **Worktree**: clean

### Files Created/Modified
- `surface-contract.md` — created (19 sections)
- `backlog.md` — C06-T002 marked `go`
- `proof-pack.md` — this section added
- `decision-log.md` — C06-D002 appended

### Inputs Read
All 34 required pre-reads available. No missing inputs.

### Surface Contract Result
19-section contract covering: gate, scope, truth after C06-T001, workspace purpose, surface model, source-of-truth mapping, read-only interaction rules, evidence state model, redaction/truth-labeling rules, unavailable/deferred states, non-goals, implementation readiness, backlog, release boundary.

### Surface Model
8 top-level zones: Workspace Header, Work-Order Status Card, Command-Run Evidence Card, Tool-Turn Observability Card, Receipt Evidence Card, Runtime/Health Card, Gaps and Unavailable Card, Safety Boundary Note.

5 safe to compose now, 1 conditional (tool-turn), 2 new (gaps/safety).

### Source-of-Truth Mapping
8-row table mapping each zone to frontend source, backend route, durable store, proof artifact, known limitation.

### Read-Only Interaction Rules
3 allowed interactions (navigate, refresh, copy public IDs). 11 prohibited interactions (dispatch, execute, retry, replay, approve, complete, create artifact/receipt, mutate state, invoke Pi/Coder, invoke tool loops).

### Evidence State Model
7 canonical states: available, unavailable, deferred, loading, error, stale, diagnostic-only. Each with user-facing label, usage rule, and what-not-to-imply.

### Redaction and Truth-Labeling
10 forbidden content types. 5 truth-label templates (tool-turn, command-run, receipt, work-order, health).

### Unavailable/Deferred States
6 items recorded: receipt linkage, assistant_message_id, workspace composition, EventConsole, manifest, latest-run bridge.

### Validation
```
git diff --check              clean
python3 scripts/validate_docs.py passed
```

### Gate Decision
**`go`** — C06-T002 accepted. C06-T003 may proceed.

### Next Task
**C06-T003: Add Guardian Operator Workspace lens scaffold**

---

## C06-T003: Lens Scaffold (2026-06-19 09:15 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `daba74953` | **Worktree**: clean

### Files Created/Modified
- `GuardianOperatorWorkspaceLens.tsx` — created (read-only, static scaffold, 8 cards + safety boundary)
- `CommandCenterUtilityRail.tsx` — `guardian-workspace` lens id added
- `CommandCenterShell.tsx` — import + switch case wired
- `CommandCenterShell.test.tsx` — 5 new tests
- `CommandCenterUtilityRail.test.tsx` — 2 new tests
- `backlog.md` — C06-T003 marked `go`

### Inputs Read
All 35 required pre-reads available. No missing inputs.

### Lens Scaffold Result
`GuardianOperatorWorkspaceLens` component created. Read-only. No fetch, no API imports, no dynamic imports. Renders 8 cards matching C06-T002 surface contract zones + safety boundary note.

### Utility Rail Wiring
New lens id `guardian-workspace` with label "Workspace", icon `Ω`. Test-proven: renders in rail, `onLensChange("guardian-workspace")` fires on click.

### Shell Wiring
New `guardian-workspace` switch case renders `<GuardianOperatorWorkspaceLens />`. Test-proven: workspace renders when clicked.

### Read-Only / No-Fetch
Component has no `fetch` calls, no `api` imports, no dynamic imports. All content is static scaffold text.

### No Mutation Controls
Test-proven: 7 forbidden button labels absent from workspace. No dispatch, execute, retry, replay, approve, complete, create artifact, create receipt.

### Truth-Labeling
Test-proven: tool-turn card truth-labels bounded evidence (scoped to card to avoid duplicate text across cards). Safety boundary lists 6 unsupported claims: no autonomous delegation, no Pi/Coder execution, no recursive tool loops, no artifact creation, no receipt creation, no work-order completion.

### Validation
```
CommandCenterShell.test.tsx      26 passed (5 workspace + 21 existing)
CommandCenterUtilityRail.test.tsx 16 passed (2 workspace + 14 existing)
-t "CommandCenter|GuardianWorkspace" 74 passed, 756 skipped
git diff --check                clean
python3 scripts/validate_docs.py passed
```

### Gate Decision
**`go`** — C06-T003 accepted. C06-T004 may proceed.

### Next Task
**C06-T004: Compose first Guardian Operator Workspace read-only cards**

---

## C06-T004: Compose First Read-Only Cards (2026-06-19 09:30 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `4841081ca` | **Worktree**: clean

### Files Modified
- `GuardianOperatorWorkspaceLens.tsx` — rewritten with props + live HealthOverview + live CodingWorkOrdersPanel
- `CommandCenterShell.tsx` — workspace case passes health props
- `backlog.md` — C06-T004 marked `go`

### Inputs Read
All 32 required pre-reads available. No missing inputs.

### Runtime/Health Composition
`HealthOverview` rendered inside workspace section labeled "Runtime / health" with explanatory copy. Props passed from shell: healthItems, lastCheckedAt, loading, onRefresh. No new fetch — uses existing shell prop pipeline.

### Work-Order Composition
`CodingWorkOrdersPanel` rendered inside workspace section labeled "Work-order status" with explanatory copy. No new fetch — panel uses its own existing data fetching. Panel preserves existing C05 tool-turn observability and C03 receipt evidence behavior.

### Static/Deferred Card Preservation
Command-run evidence (deferred), tool-turn observability (conditional, with note about composed panel), receipt evidence (available/composed + deferred receipt linkage), gaps, safety boundary — all preserved as static/deferred cards.

### Shell Prop Wiring
`GuardianOperatorWorkspaceLens` now accepts `GuardianOperatorWorkspaceLensProps` (healthItems, lastCheckedAt, loading, onRefresh). Shell passes these from existing props. No unrelated shell props passed.

### Read-Only / No-New-Fetch
Workspace wrapper adds no new fetch, no new API imports. Composed panels use their own existing fetch behavior (already test-proven in C03/C05).

### No Mutation Controls
Test-proven: 7 forbidden button labels absent from workspace.

### Truth-Labeling
Safety boundary lists 6 unsupported claims. Tool-turn card truth-labels bounded evidence. Receipt card truth-labels receipt evidence.

### Validation
```
CommandCenterShell.test.tsx  26 passed
-t "CommandCenter|CodingWorkOrders|GuardianWorkspace"  96 passed, 753 skipped
git diff --check              clean
python3 scripts/validate_docs.py passed
```

### Gate Decision
**`go`** — C06-T004 accepted. C06-T005 may proceed.

### Next Task
**C06-T005: Add Guardian Operator Workspace composition proof**

