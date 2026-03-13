# SOC Alignment - Codexify Pre-Audit Mapping

Status: Pre-SOC Readiness Documentation  
Last Updated: 2026-02-27

This document maps Codexify system components to AICPA Trust Services Criteria (TSC).

---

## CC1 - Control Environment

Artifacts:
- `SECURITY.md`
- `docs/reference/infrastructure/system_integrity_ledger.md`
- `.github/workflows/guardian-ci.yml`

Controls:
- Integrity ledger versioning
- CI validation on main branch
- Explicit environment gating

---

## CC2 - Communication & Information

Artifacts:
- `docs/reference/architecture/system-overview.md`
- `docs/reference/architecture/modules-and-ownership.md`
- `docs/reference/architecture/completion_pipeline.md`

Controls:
- Explicit flow documentation
- Versioned architecture maps
- Dependency anchors

---

## CC3 - Risk Assessment

Artifacts:
- `docs/reference/architecture/tech-debt-and-risks.md`
- `docs/reference/architecture/roadmap-signals.md`

Controls:
- Ranked risk registry
- Evidence-linked mitigation paths

---

## CC4 - Monitoring Activities

Artifacts:
- `.github/workflows/codemap-maintenance.yml`
- `.github/workflows/guardian-ci.yml`
- `docs/reference/infrastructure/system_integrity_ledger.md`

Controls:
- Scheduled/triggered workflow coverage for maintenance and verification
- Runtime and migration contract checks in CI
- CI/CD signal collection for regression detection

---

## CC5 - Control Activities

Artifacts:
- `docs/reference/architecture/config-and-ops.md`
- `guardian/core/dependencies.py`
- `guardian/core/egress.py`

Controls:
- Auth boundary enforcement
- Provider allowlist gating
- Egress restriction defaults

---

## CC6 - Logical & Physical Access

Artifacts:
- `docs/reference/architecture/config-and-ops.md`
- `docs/reference/architecture/data-and-storage.md`

Controls:
- API key requirement at startup
- Local-safe exposure mode default
- JWT/session validation path

---

## CC7 - System Operations

Artifacts:
- `docker-compose.yml`
- `docs/reference/architecture/system-overview.md`
- `docs/reference/architecture/completion_pipeline.md`

Controls:
- Worker separation
- Queue isolation
- Turn-lock concurrency enforcement

---

## CC8 - Change Management

Artifacts:
- `.github/workflows/guardian-ci.yml`
- `docs/reference/infrastructure/system_integrity_ledger.md`

Controls:
- Commit-based integrity logging
- CI gates on pull request and main branch changes
- Explicit migration and schema contract checks

---

## CC9 - Risk Mitigation (Ongoing)

Artifacts:
- `docs/reference/architecture/tech-debt-and-risks.md`
- `docs/reference/architecture/roadmap-signals.md`

Controls:
- Explicit refactor sequencing
- Identified high-coupling hotspots
- Known missing pieces registry

---

## Known Gaps (Pre-SOC)

- No formal access review policy document in-repo
- Incident response playbook exists (`docs/reference/security/INCIDENT_RESPONSE.md`) but no documented drill cadence/evidence in CI
- No documented vendor risk management policy
- Redis persistence is disabled in default development Compose topology
- Encryption-at-rest enforcement depends on host/database infrastructure configuration

These must be formalized before SOC engagement.
