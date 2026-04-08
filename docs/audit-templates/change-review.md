# Change Review Entry

Use this template when preparing a change for review. Fill out all sections
before requesting review.

---

## Change Description

**Change:** <!-- Brief description of what changed -->

**Layer(s) affected:** <!-- chat, providers, ingestion, tools, federation, etc. -->

**Primary risk introduced:** <!-- Reference risk ID from risk matrix or describe -->

**Failure mode if wrong:** <!-- What happens if this change breaks -->

**Blast radius:** <!-- Low / Moderate / High / Critical -->

**Justification:** <!-- Why this blast radius rating -->

---

## Detection

**How detected if it fails:** <!-- Automated test, monitoring, user report -->

**Observability added:** <!-- What traces/metrics/logs were added -->

---

## Mitigation

**Rollback path:** <!-- How to revert if needed -->

**Eval evidence:** <!-- Tests, benchmarks, manual verification performed -->

**Owner:** <!-- Who is responsible for this change -->

---

## Merge Checklist (Gate 1: Before Merge)

- [ ] Layer identified
- [ ] Blast radius identified and justified
- [ ] Owner assigned
- [ ] Invariants listed (what must remain true)
- [ ] Tests added or updated
- [ ] Traces/logging updated
- [ ] Rollback described
- [ ] Migration impact reviewed (if applicable)

**Manual attestations required:**

- [ ] **Blast radius assessment** - Actual impact scope verified
- [ ] **Rollback path validation** - Rollback can be executed safely

**Manual attestations recommended:**

- [ ] **Identity isolation check** - Boundaries respected (if applicable)

---

## Release Checklist (Gate 2: Before Release)

### Automated Checks

Status from `make audit-gates-pre-release`:

- [ ] Migration tests exist (deterministic)
- [ ] Tool contract files present (best-effort)
- [ ] Identity markers detected (best-effort)
- [ ] Queue health routes present (best-effort)

### Manual Attestations Required

- [ ] **Golden task suite passes** - Core functionality verified
- [ ] **Cross-provider sanity checks pass** - Provider switching works

### Manual Attestations Recommended

- [ ] **Schema migration tested** - Forward and backward migration verified
- [ ] **Retrieval eval suite passes** - RAG quality maintained
- [ ] **Cost budget checks pass** - No unexpected cost spikes
- [ ] **Observability dashboard reviewed** - Metrics look healthy

### Review Requirements

- [ ] One designated reviewer argues against release and fails to break it

---

## Post-Release Review (Gate 3: After Release)

Review within 24-48 hours of release:

- [ ] Error rates monitored
- [ ] Task completion rates normal
- [ ] Retrieval relevance signals stable
- [ ] Cost per successful outcome acceptable
- [ ] Fallback frequency within normal range
- [ ] No user trust incidents reported
- [ ] No unexpected boundary crossings

---

## Risk Matrix Updates

Risks that may need updating based on this change:

<!-- List any risk IDs from scripts/audit/data/risk_matrix_baseline.json -->

- [ ] <!-- e.g., model-routing, schema-drift -->

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | | | |
| Reviewer | | | |
| Tester | | | |
