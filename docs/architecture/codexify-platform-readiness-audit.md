# Codexify Platform Readiness Audit

This document describes Codexify's platform-readiness audit as an architecture-maturity check rather than a feature checklist. The audit asks whether the repo's current runtime is reliable, observable, durable, extensible, and governable enough to support repeatable platform work.

The audit domains are:

- Core Loop Integrity
- Primitive Stability
- Extension Boundary
- Observability
- Durability & Recovery
- Alternate Surface Readiness
- Federation Readiness
- Governance Readiness

The score model is intentionally conservative:

- `0` means the domain is absent or structurally weak.
- `1` means the domain is partial or fragile.
- `2` means the domain is operational.
- `3` means the domain is extensible or ecosystem-ready.

Platform maturity is determined by the weakest domain, not the average.

Repo-local evidence can justify some narrow score bands, but it cannot truthfully replace architectural judgment. In particular, questions about degraded modes, compatibility discipline, extension authority, and governance enforcement still require human review.

This architecture-facing summary complements the fuller historical audit definitions under:

- `docs/audits/codexify_platform_readiness_audit_v1.md`
- `docs/audits/codexify_platform_rediness_audit_v2.md`

## Audit CLI

`scripts/audit_platform_readiness.py` turns the static readiness audit into a repeatable repo-local evidence pass.

It performs objective checks only:

- repo-relative file existence checks for key runtime and documentation anchors
- lightweight text matching for health, flow, storage, federation, ownership, roadmap, and risk signals
- explicit `PASS`, `WARN`, and `FAIL` reporting for those objective findings

It does not fabricate subjective architectural scores. Where the repo cannot prove a judgment, the CLI prints manual review prompts instead of pretending to know the answer.

Run it from the repo root with:

```bash
python scripts/audit_platform_readiness.py
```

The script exits `0` when no `FAIL` results are found, and exits `1` when any `FAIL` result is present.
