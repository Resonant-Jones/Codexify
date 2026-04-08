# Monthly Architecture Audit

Use this template for the monthly deep-dive architecture audit ritual.

---

## Meeting Info

**Date:** <!-- YYYY-MM-DD -->

**Attendees:**

- <!-- Name (Role) -->

**Duration:** 90 minutes

---

## 1. Risk Matrix Re-scoring (15 min)

### Current Distribution
<!-- Before scoring -->

| Band | Count |
|------|-------|
| Critical | <!-- count --> |
| High | <!-- count --> |
| Moderate | <!-- count --> |
| Low | <!-- count --> |
| **Total** | <!-- total --> |

### Score Changes This Month
<!-- List any scores that changed -->

| Risk ID | Old Score | New Score | Delta | Reason |
|---------|-----------|-----------|-------|--------|
| <!-- id --> | <!-- old --> | <!-- new --> | <!-- +/- --> | <!-- why --> |

### New Risks Identified
<!-- Any risks added this month -->

| Risk ID | Area | Initial Score | Source |
|---------|------|---------------|--------|
| <!-- id --> | <!-- area --> | <!-- score --> | <!-- incident/discovery --> |

### Risks Deprecated
<!-- Any risks no longer relevant -->

| Risk ID | Reason for Deprecation |
|---------|------------------------|
| <!-- id --> | <!-- why --> |

---

## 2. "Temporary" Shim Review (10 min)

### Shims Still in Place
<!-- Controls marked as "temporary" or "shim" -->

| Risk ID | Current Control | Age | Decision |
|---------|-----------------|-----|----------|
| <!-- id --> | <!-- control --> | <!-- weeks --> | <!-- Keep/Remove/Replace --> |

### Shim Conversion Plan
<!-- Which shims need to become permanent? -->

- [ ] <!-- Risk ID -->: <!-- action -->

---

## 3. Provider Dependency Drift (10 min)

### Single-Provider Dependencies
<!-- Check for increasing coupling to one provider -->

| Provider | Components Using | Risk Level |
|----------|------------------|------------|
| Anthropic | <!-- count/areas --> | <!-- High/Med/Low --> |
| OpenAI | <!-- count/areas --> | <!-- High/Med/Low --> |
| Google | <!-- count/areas --> | <!-- High/Med/Low --> |
| Local | <!-- count/areas --> | <!-- High/Med/Low --> |

### Adapter Coverage
<!-- Are all provider-specific patterns covered by adapters? -->

- [ ] All provider code in adapters
- [ ] Provider-specific error handling centralized
- [ ] Cross-provider tests passing

---

## 4. Memory Portability Check (10 min)

### Export Path Verification
<!-- Can we still export all user context? -->

| Data Type | Exportable? | Test Date | Notes |
|-----------|-------------|-----------|-------|
| Threads | Y/N | <!-- date --> | <!-- notes --> |
| Documents | Y/N | <!-- date --> | <!-- notes --> |
| Embeddings | Y/N | <!-- date --> | <!-- notes --> |
| Events | Y/N | <!-- date --> | <!-- notes --> |

### Schema Compatibility
<!-- Any breaking schema changes? -->

- [ ] No breaking changes
- [ ] Migration provided for: <!-- what -->

---

## 5. Orchestration Debt Review (10 min)

### Retry Pattern Consistency
<!-- Check for TRAP-8 findings -->

| Subsystem | Retry Strategy | Consistent with Others? |
|-----------|----------------|-------------------------|
| <!-- name --> | <!-- strategy --> | Y/N |

### Error Handling Patterns
<!-- Are error handling patterns consistent? -->

- [ ] Consistent exception hierarchy
- [ ] Consistent logging patterns
- [ ] Consistent fallback behavior

### State Machine Formalization
<!-- Any ad-hoc orchestration that should be formalized? -->

| Flow | Current State | Needs Formalization? |
|------|---------------|----------------------|
| <!-- flow name --> | <!-- ad-hoc/formal --> | Y/N |

---

## 6. Observability Gaps (10 min)

### Recent Failures Analysis
<!-- Can we explain recent failures? -->

| Incident | Root Cause Explained? | Observability Gap? |
|----------|----------------------|--------------------|
| <!-- INC-... --> | Y/N | <!-- what was missing --> |

### Trace Coverage
<!-- End-to-end traces available for key flows? -->

| Flow | Trace ID Present? | Correlation Works? |
|------|-------------------|--------------------|
| Chat completion | Y/N | Y/N |
| Document ingestion | Y/N | Y/N |
| Tool execution | Y/N | Y/N |
| Sync/federation | Y/N | Y/N |

---

## 7. Subsystem Count Review (15 min)

### Current Subsystems
<!-- List all subsystems and their sizes -->

| Subsystem | Files | Complexity | Justified? |
|-----------|-------|------------|------------|
| <!-- name --> | <!-- count --> | <!-- High/Med/Low --> | Y/N - explain |

### Merger Candidates
<!-- Subsystems that could be combined -->

| Candidate 1 | Candidate 2 | Rationale | Effort |
|-------------|-------------|-----------|--------|
| <!-- name --> | <!-- name --> | <!-- why --> | <!-- estimate --> |

### Removal Candidates
<!-- Subsystems that could be removed -->

| Subsystem | Usage | Removal Impact | Effort |
|-----------|-------|----------------|--------|
| <!-- name --> | <!-- how used --> | <!-- impact --> | <!-- estimate --> |

### Decision
<!-- At least one simplification should be identified -->

**Selected simplification:** <!-- what -->

**Owner:** <!-- who -->

**Target completion:** <!-- date -->

---

## Action Items

### This Month
- [ ] <!-- task --> (Owner: <!-- name -->)

### Next Month
- [ ] <!-- task --> (Owner: <!-- name -->)

### Next Quarter
- [ ] Plan migration drill (Owner: <!-- name -->)

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Facilitator | | |
| Architecture Lead | | |
| Platform Lead | | |
| Risk Owners (highest risks) | | |

---

## Appendix: Risk Matrix Snapshot

<!-- Include full risk matrix or link to generated report -->

See: `docs/audits/regression/risk-matrix-*.md`
