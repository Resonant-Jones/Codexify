# Forced Migration Drill Entry

Use this template to document quarterly migration drills. File in
`docs/audits/regression/drills/YYYY-Q#-{subsystem}.md`

---

## Drill Overview

**Quarter:** <!-- Q1/Q2/Q3/Q4 YYYY -->

**Drill ID:** <!-- DRILL-YYYY-Q#-### -->

**Subsystem tested:** <!-- Which subsystem was targeted -->

**Original dependency:** <!-- What was being replaced or simulated -->

**Replacement or failure simulation:**
<!-- How the drill was conducted: swapped component, failure injection, etc. -->

---

## Objectives

### What We Wanted to Prove
<!-- Specific portability claims being tested -->

### Success Criteria
<!-- How we defined success -->

- [ ] <!-- Criterion 1 -->
- [ ] <!-- Criterion 2 -->

---

## Preparation

### Rollback Plan
<!-- How to undo if things go wrong -->

### Monitoring in Place
<!-- What dashboards/alerts were active -->

### Test Data
<!-- What test scenarios were prepared -->

---

## Execution

### Drill Steps

1. <!-- Step 1 -->
2. <!-- Step 2 -->
3. <!-- Step 3 -->

### What Broke
<!-- Specific failures encountered -->

| Component | Issue | Severity |
|-----------|-------|----------|
| <!-- name --> | <!-- description --> | <!-- High/Med/Low --> |

### What Stayed Stable
<!-- Components that worked as expected -->

---

## Results

### Success Criteria Met
- [ ] All criteria met
- [ ] Partial - describe:
- [ ] None met - describe:

### Actual Migration Cost
<!-- Time, effort, resources required -->

| Resource | Planned | Actual |
|----------|---------|--------|
| Time | | |
| People | | |
| Downtime | | |

### Portability Score
<!-- Rate 1-5: 1 = painful, 5 = trivial -->

- Migration difficulty: <!-- 1-5 -->
- Rollback ease: <!-- 1-5 -->
- Confidence in repeatability: <!-- 1-5 -->

---

## Recommendations

### What Would Reduce Future Cost
<!-- Specific improvements identified -->

1. <!-- Recommendation 1 -->
2. <!-- Recommendation 2 -->

### Risk Matrix Updates
<!-- Risks that should be updated based on findings -->

- [ ] <!-- e.g., Reduced migration-debt score from 192 to 144 due to improved tooling -->

---

## Drill Checklist

- [ ] Drill planned and scope defined
- [ ] Rollback plan prepared
- [ ] Monitoring in place
- [ ] Stakeholders notified
- [ ] Drill executed
- [ ] Results documented
- [ ] Action items created
- [ ] Risk matrix updated if needed

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Drill Owner | | |
| Subsystem Owner | | |
| Architecture Review | | |
