# Codexify Audit Throughline

**Throughline Date:** 2026-01-25  
**Repo:** `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify`  
**Primary Branch (session):** `chore/post-skip-hook-fixes`  

This document is the **canonical narrative** that reconciles multiple audits (Claude + Codex) into a single, evidence-anchored story:

- **What was claimed** (audits)
- **What was actually executed** (campaign tasks + commit mappings)
- **What remains uncertain** (needs discovery)

> **Ground rule:** When audits disagree, the campaign task artifacts + campaign mappings are treated as the closest thing to “reality,” because they correspond to executed work.

---

## 1) Source Inventory

### 1.1 Audit runs (2026-01-25)

**Claude**

- `artifacts/audit-runs/2026-01-25/claude/codexify-mvp-implementation-plan-2026-01-25.md`

**Codex**

- `artifacts/audit-runs/2026-01-25/codex/codexify-system-audit-2026-01-25.md`
- `artifacts/audit-runs/2026-01-25/codex/codexify-mvp-roadmap-2026-01-25.md`
- `artifacts/audit-runs/2026-01-25/codex/codexify-mvp-roadbanana-2026-01-25.md` *(variant/draft — keep for archaeology)*

### 1.2 Reports directory (2026-01-23 legacy + renamed)

- `docs/work/reports/codexify-system-audit-2026-01-23.md` *(current name)*
- `docs/work/reports/codexify-systems-audit-2026-01-23.md` *(old name — renamed in this session)*

### 1.3 Campaigns that actually drove changes

These are the “execution ledgers” that close the loop between audit claims and repo reality.

- `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md`
- `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`

---

## 2) Canonical Truth Hierarchy

When interpreting findings, use this precedence order:

1. **Campaign file mappings** (`docs/work/campaigns/...`) — source of truth for “what landed.”
2. **Task artifacts** (`docs/work/tasks/...`) — source of truth for intent + allowed-files + checks.
3. **Git history** (`git log`, `git show`) — source of truth for exact diffs.
4. **Audit narratives** (Claude/Codex prose) — hypotheses and interpretations.

---

## 3) The Big Throughline

### 3.1 What we were trying to do

Two parallel tracks happened in the same date window:

- **Security & audit hardening** (reduce secret leakage risk, stabilize embedding/document pipelines, validate memory wiring).
- **Core loop closure** (make the six “core loops” demonstrably end-to-end, with runner-safe tasks).

### 3.2 Why the audits disagreed

The Claude/Codex audits were produced at different moments and (likely) different snapshots of the branch. The repo changed significantly via runner campaigns, so older audit claims can become stale within hours.

**Rule of thumb:**

- If an audit says “missing,” but a campaign task later landed that feature, treat the audit as **historically true but presently outdated**.

---

## 4) Reconciled Core Loops (Audit claims vs executed reality)

This section consolidates what Claude claimed (as of 2026-01-25) and what the campaigns appear to have closed.

### 4.1 Document upload + embedding reliability

**Audit claims (convergent):**

- Document upload existed, but embedding reliability and status visibility needed tightening.

**Executed changes (campaign-grounded):**

- Upload status tracking was added (embedding_status + timestamps + error surface) and propagated to UI.
- A worker-based pipeline exists in the repo (note: confirm worker process is actually enabled/started in compose/runtime).

**Primary evidence to consult:**

- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md` (Tasks 003–005)  
- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md` (Tasks 003–005)

**Residual uncertainty:**

- Is the worker actually running in the default dev compose profile, and is the queue wired in a way that’s deterministic under load?

### 4.2 Image generation UI wiring

**Audit claims:**

- Earlier audits suggested UI wiring gaps; later work shows UI is wired and tests exist.

**Executed changes:**

- Modal tests and UI wiring tasks were executed in both campaigns (names differ; confirm the latest state is the one in Core Loop Roadmap).

**Primary evidence:**

- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md` (Task 006)

### 4.3 Document generation UI wiring + doc_type

**Audit claims:**

- Doc generation backend existed; UI wiring and doc_type payload needed closure.

**Executed changes:**

- Doc gen button/event wiring landed.
- `doc_type` selector was added and the payload updated to include `doc_type`.

**Primary evidence:**

- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md` (Tasks 007–008)

### 4.4 Memory store initialization + ContextBroker integration test

**Audit claims:**

- Memory wiring is mostly present; integration tests needed to reduce ambiguity.

**Executed changes:**

- Verification task documented memory store wiring.
- A deterministic ContextBroker integration test exists.

**Primary evidence:**

- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md` (Tasks 009–010)

### 4.5 Neo4j / graph context decision

**Audit claims:**

- Neo4j exists but graph context is not required for core loop MVP; ambiguity should be resolved explicitly.

**Executed changes:**

- Decision task defers graph-context for core loop.

**Primary evidence:**

- Campaign: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md` (Task 011)

---

## 5) Campaign Execution Summary

This section is intentionally lightweight: the **authoritative mappings live in the campaign docs**.

### 5.1 AUDIT_HARDENING_FOUNDATION campaign

**What this campaign primarily accomplished:**

- Secrets hygiene in compose.
- Embeddings endpoint verification.
- Embed status schema + worker pipeline + UI status surfacing.
- Context broker/memory tests and explicit Neo4j decision.

**Canonical mapping:**

- See: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md`

### 5.2 CORE_LOOP_ROADMAP campaign

**What this campaign primarily accomplished:**

- Re-did (or re-asserted) several hardening tasks in a “core loop closure” frame.
- Focused on UI wiring, payload correctness (`doc_type`), and deterministic tests.

**Canonical mapping:**

- See: `docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md`

---

## 6) Known Process Friction (so we don’t repeat it)

### 6.1 “Record finalize hash” created extra commit loops

The runner protocol’s extra “record finalize hash” step is useful for strict traceability, but it can create awkward multi-commit loops when:

- the task artifact is created early (untracked) and later needs to be rewritten,
- or the campaign path references drift (typos like `CAMPAIGN_2026_01_23_001_...`),
- or `.git/index.lock` friction forces manual cleanup.

**Operational rule going forward:**

- Create task artifacts *either* (a) intentionally untracked until Commit B, *or* (b) tracked immediately but always listed as allowed-files for the task.

### 6.2 `.git/index.lock` environment limitation

This repo routinely hits `Operation not permitted` creating `.git/index.lock`.

**Mitigation that worked in-session:**

- `rm -f .git/index.lock` before git operations.
- Avoid runner steps that rely on rapid checkout/revert loops.

---

## 7) The One-Page “What’s True Right Now” Checklist

These are the things you can validate quickly to confirm that the audits match current reality.

### 7.1 Validate doc embedding pipeline

```bash
# backend API health
curl -sS http://localhost:8888/health || true

# list docs and confirm embedding_status fields exist
curl -sS http://localhost:8888/api/media/documents | head -c 4000

# run the specific worker test (if present)
pytest -q guardian/tests -k "document_embed_worker or embed" || true
