

# Codexify Audit Ledger

This ledger is the canonical index of **all audit outputs** (Claude/Codex/other) and the **single source of truth** for:

- where each audit artifact lives
- which branch/commit it was produced against
- whether it is *authoritative*, *superseded*, or *forensics-only*
- the “throughline” mapping from audit findings → campaigns/tasks/commits

---

## How to use this ledger

### Add a new audit run
1) Create a dated folder: `artifacts/audit-runs/YYYY-MM-DD/<agent>/...`
2) Drop raw outputs in the agent folder (do not edit them in place).
3) Add a new entry in **Audit Runs** (below).
4) If you curate/merge conclusions across runs, add a new **Throughline Snapshot** entry.

### Status definitions
- **canonical**: the current best-curated view you would hand to a new contributor
- **superseded**: older/incorrect relative to current codebase (kept for history)
- **forensics**: useful for reconstructing what a model believed at the time
- **draft**: incomplete; should not drive work directly

---

## Audit Runs

### 2026-01-23 (session artifacts)
> Note: Some files were renamed during cleanup. Treat these as *session outputs*.

| Date | Agent | Artifact | Path | Status | Notes |
|---|---|---|---|---|---|
| 2026-01-23 | (mixed) | System Audit | `docs/work/reports/codexify-system-audit-2026-01-23.md` | forensics | Older run; keep as reference. |
| 2026-01-23 | (mixed) | System Audit (renamed from “systems audit”) | `docs/work/reports/codexify-system-audit-2026-01-23.md` | forensics | If both exist, prefer the non-deleted path. |

### 2026-01-25 (organized runs)

| Date | Agent | Artifact | Path | Status | Notes |
|---|---|---|---|---|---|
| 2026-01-25 | Claude | MVP Implementation Plan | `artifacts/audit-runs/2026-01-25/claude/codexify-mvp-implementation-plan-2026-01-25.md` | forensics | Claude’s snapshot; may lag behind current branch changes. |
| 2026-01-25 | Codex | MVP Roadmap (alt name) | `artifacts/audit-runs/2026-01-25/codex/codexify-mvp-roadbanana-2026-01-25.md` | forensics | Kept verbatim; use for diffs only. |
| 2026-01-25 | Codex | MVP Roadmap | `artifacts/audit-runs/2026-01-25/codex/codexify-mvp-roadmap-2026-01-25.md` | forensics | Codex snapshot; compare to campaign reality. |
| 2026-01-25 | Codex | System Audit | `artifacts/audit-runs/2026-01-25/codex/codexify-system-audit-2026-01-25.md` | forensics | Codex snapshot; compare to throughline. |

---

## Canonical Throughline

### Canonical Throughline Snapshot: 2026-01-25
- **Path:** `docs/work/reports/codexify-audit-throughline-2026-01-25.md`
- **Status:** canonical
- **Intent:** Merge the best-supported conclusions across agents, but only where they match repo evidence and/or are validated by executed tasks.

---

## Executed Remediation Campaigns (audit-driven)

### CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION
- **Path:** `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md`
- **Status:** canonical
- **Notes:** Security-hardening and reliability closure (secrets hygiene, embeddings endpoint, doc embed pipeline + status, UI status, image/doc gen wiring tests, context broker tests, Neo4j decision, docs drift cleanup).

### CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP
- **Path:** `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`
- **Status:** canonical
- **Notes:** Core loop closure plan executed/validated via tasks on `chore/post-skip-hook-fixes`.

---

## Known Reconciliation Issues (keep honest)

These are recurring audit failure modes. When something feels contradictory, check here first.

1) **Branch drift:** audits often assume `main` while work is happening on `chore/post-skip-hook-fixes`.
2) **Endpoint path drift:** e.g. `/api/...` vs non-`/api` variants (frontend vs backend contracts).
3) **Auth drift (dev proxy vs prod):** Vite proxy may inject headers in dev; production requires explicit auth.
4) **“Stub provider” false positives:** some providers exist as placeholders; don’t mark the feature “missing” if the core loop is wired.
5) **Worker vs inline behavior:** a loop can be “complete” but async; tests may need to assert state transitions rather than immediate outputs.

---

## Quick commands (for future audits)

```bash
# Repo identity
git rev-parse HEAD
git branch --show-current

# Show audit run tree
find artifacts/audit-runs -maxdepth 4 -type f | sort

# Find campaigns + tasks
ls -1 docs/work/campaigns | sort
ls -1 docs/work/tasks | sort

# Grep common contract points
rg -n "/api/" guardian/routes frontend/src -S
rg -n "X-API-Key|require_api_key" guardian frontend/src -S
```

---

## Append-only notes

- 2026-01-26: Ledger created to prevent Claude/Codex outputs from overwriting each other and to keep a stable narrative.