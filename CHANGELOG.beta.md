# Beta Changelog

Evidence-led beta readiness changes only.


## 2026-05-15

### Evidence
- No new commit subjects discovered for this sentinel window.

### Blockers
- None currently listed.

### Warnings
- Core Loop Integrity: Architecture docs still flag chat-loop dependency coupling
- Primitive Stability: Repo-local docs warn about contract drift in tool primitives
- Extension Boundary: Architecture docs describe command bus, cron, and coding-agent seams
- Extension Boundary: Legacy /tools compatibility route status
- Observability: Observability docs leave some logging guarantees unverified
- Durability & Recovery: Roadmap docs warn that sync delivery is not yet durable
- Durability & Recovery: Risk register warns about Redis persistence or replay gaps
- Alternate Surface Readiness: Repo-local docs still describe shell-level coupling
- Federation Readiness: Roadmap docs warn that sync subscriptions are process-local
- Federation Readiness: Risk register warns that federation remains security- and config-sensitive
- Governance Readiness: Ownership authority is still informal in the scanned docs
