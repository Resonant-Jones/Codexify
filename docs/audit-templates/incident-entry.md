# Incident / Near-Miss Entry

Use this template to document incidents or near-misses. File in
`docs/audits/regression/incidents/YYYY-MM-DD-{incident-name}.md`

---

## Incident Summary

**Date:** <!-- YYYY-MM-DD -->

**Time:** <!-- HH:MM UTC -->

**Subsystem(s):** <!-- Which subsystem(s) were involved -->

**Severity:** <!-- Critical / High / Medium / Low -->

**Incident ID:** <!-- Generate: INC-YYYY-MM-DD-### -->

**Related Risk(s):** <!-- Risk ID(s) from risk matrix -->

---

## What Happened

### Description
<!-- Detailed description of the incident -->

### User Impact
<!-- How users were affected -->

### Scope
<!-- How many users, requests, data affected -->

---

## Root Cause Analysis

### What Should Have Prevented It
<!-- Expected controls that should have caught this -->

### Why Prevention Failed
<!-- Root cause: which control failed and why -->

### Detection Method
<!-- How was the issue discovered: -->
- [ ] Automated alert
- [ ] User report
- [ ] Manual observation
- [ ] Other: <!-- specify -->

### Was the Issue Silent
<!-- Did it fail loudly or silently -->
- [ ] Obvious immediately
- [ ] Visible with normal QA
- [ ] Required targeted inspection
- [ ] Silent until users reported

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Issue started |
| HH:MM | Issue detected |
| HH:MM | Mitigation applied |
| HH:MM | Resolution confirmed |

---

## Response

### Immediate Actions Taken
<!-- What was done to mitigate/resolve -->

### Rollback Required
- [ ] Yes - describe:
- [ ] No

### Data Recovery Required
- [ ] Yes - describe:
- [ ] No

---

## Remediation

### Invariants/Test/Log Now Required
<!-- Action items to prevent recurrence -->

- [ ] <!-- e.g., Add test for X scenario -->
- [ ] <!-- e.g., Add alert for Y condition -->

### Risk Matrix Updates
<!-- Which risk entries were updated based on this -->

- [ ] <!-- e.g., Updated queue-worker score from 135 to 160 -->

---

## Lessons Learned

1. <!-- What did we learn -->
2. <!-- What will we do differently -->
3. <!-- What should others know -->

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Incident Commander | | |
| Root Cause Analyst | | |
| Risk Owner | | |
