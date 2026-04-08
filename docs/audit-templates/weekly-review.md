# Weekly Regression Review

Use this template for the 30-minute weekly regression review ritual.

---

## Meeting Info

**Date:** <!-- YYYY-MM-DD -->

**Attendees:**

- <!-- Name (Role) -->

**Time:** 30 minutes

---

## 1. New Incidents or Near-Misses (5 min)

### Incidents Since Last Week
<!-- List any incidents or near-misses -->

| Incident ID | Subsystem | Severity | Status |
|-------------|-----------|----------|--------|
| <!-- INC-... --> | <!-- name --> | <!-- Critical/High/Med/Low --> | <!-- Open/Closed --> |

### Risk Matrix Updates Required
<!-- Did any incidents require risk score adjustments? -->

- [ ] No updates needed
- [ ] Updated: <!-- Risk ID -->

---

## 2. Highest Score Risks (5 min)

### Top 3 Risks Needing Attention
<!-- From risk matrix -->

1. **<!-- Risk Area -->** (`<!-- ID -->`)
   - Score: <!-- score -->
   - Owner: <!-- owner -->
   - Action needed: <!-- what -->

2. **<!-- Risk Area -->** (`<!-- ID -->`)
   - Score: <!-- score -->
   - Owner: <!-- owner -->
   - Action needed: <!-- what -->

3. **<!-- Risk Area -->** (`<!-- ID -->`)
   - Score: <!-- score -->
   - Owner: <!-- owner -->
   - Action needed: <!-- what -->

---

## 3. Stale Entries (5 min)

### Risks Past Review Interval
<!-- Risks not reviewed in their interval_days -->

| Risk ID | Area | Days Stale | Owner |
|---------|------|------------|-------|
| <!-- id --> | <!-- area --> | <!-- days --> | <!-- owner --> |

### Decisions
- [ ] Updated review dates
- [ ] Assigned new owners
- [ ] Deprecated obsolete risks

---

## 4. Subsystem Complexity Changes (5 min)

### Changes This Week
<!-- Did any subsystems grow unexpectedly? -->

| Subsystem | Files Changed | Complexity Concern? |
|-----------|---------------|---------------------|
| <!-- name --> | <!-- count --> | <!-- Y/N - explain --> |

### Simplification Opportunities
<!-- Any subsystems that could be merged or reduced? -->

---

## 5. Changes Without Eval Coverage (5 min)

### High-Blast-Radius Changes
<!-- Any changes that skipped evaluation? -->

| Change | Blast Radius | Eval Coverage | Risk |
|--------|--------------|---------------|------|
| <!-- description --> | <!-- radius --> | <!-- coverage --> | <!-- trap? --> |

### Trap Detection Findings
<!-- Review trap-detector output -->

- [ ] No new traps
- [ ] Traps detected (see `docs/audits/regression/traps-*.md`)

---

## 6. Simplification Candidate (5 min)

### This Week's Candidate
<!-- One thing that could be removed or simplified -->

**What:** <!-- description -->

**Why:** <!-- justification -->

**Effort:** <!-- estimate -->

**Owner:** <!-- who would do it -->

---

## Action Items

### Immediate (This Week)
- [ ] <!-- task --> (Owner: <!-- name -->)

### This Sprint
- [ ] <!-- task --> (Owner: <!-- name -->)

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Facilitator | | |
| Risk Owner (highest risk) | | |
| Architecture Rep | | |

---

## Notes

<!-- Free-form notes from the review -->
