# Codexify Release Tier Index (v1)

Date: 2026-05-10  
Owner: Resonant Jones (solo operator)  
Status: Baseline strategic index for open-source release tiering

## Purpose
This document maps Codexify capability slices to release tiers so we can:
- publish high-trust open surfaces quickly,
- keep high-risk operations private until hardened,
- attach paid service offers to real operator pain.

This is not a hype summary. It is a practical release and business control map.

## Evidence Anchors
- `README.md`
- `docs/architecture/00-current-state.md`
- `docs/Codexify/RELEASE.md`
- `docs/architecture/README.md`

## Scoring Rubric
Each capability slice is scored 1-5 across:
- `User Value`: direct user outcome.
- `Differentiation`: unique hard-to-copy value.
- `Support Burden`: expected support load if public.
- `Security Exposure`: misuse/blast risk if misconfigured.
- `Ops Intensity`: ongoing runtime/operator work.

Interpretation:
- Higher `User Value` and `Differentiation` push toward open core.
- Higher `Support Burden`, `Security Exposure`, and `Ops Intensity` push toward managed/internal.

## Tier Legend
- `Tier O (Open Core)`: publish now; required for trust/adoption.
- `Tier M (Managed Advantage)`: code can be visible, but paid value is reliability, setup, and operations.
- `Tier I (Internal Only for now)`: keep private until safer defaults and guardrails exist.

## Capability Index
| Capability Slice | User Value | Differentiation | Support Burden | Security Exposure | Ops Intensity | Tier | Why This Tier | Monetizable Edge |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Core chat runtime (thread -> completion -> persistence) | 5 | 4 | 3 | 3 | 3 | O | Core trust surface; must be inspectable. | Integration tuning, prompt policy hardening. |
| Identity-boundary rules (account/user/thread ownership semantics) | 5 | 5 | 4 | 5 | 4 | O | Security and trust are product-critical; keep visible. | Identity migration and boundary audits. |
| Provider governance (registry/catalog/health truth alignment) | 4 | 4 | 3 | 4 | 4 | O | Credibility requires transparent support/availability claims. | Provider posture hardening for target environments. |
| Retrieval broker and source-mode policy (`conversation/project/personal/workspace`) | 5 | 5 | 4 | 4 | 4 | O | This is a signature Codexify behavior layer. | Retrieval policy tuning + validation proofs. |
| Document/media ingest + embedding lifecycle | 4 | 3 | 4 | 3 | 4 | O | Essential default workflow; needs broad test feedback. | Data-path reliability services. |
| Task queue + event stream spine (Redis, task events, workers) | 4 | 4 | 4 | 3 | 5 | M | Valuable but operationally heavy in real installs. | Queue sizing, failure recovery, SLO ops. |
| Coding-result return path (worker -> Guardian -> source thread) | 4 | 5 | 4 | 4 | 5 | M | Strategic differentiator; high operational sensitivity today. | Agent-run governance and reliability packaging. |
| Command bus and bounded tool policy wall | 5 | 5 | 4 | 5 | 5 | M | High trust/power surface; publish carefully with strong docs. | Policy authoring, secure tool profiles, audits. |
| Cron/automation routes and worker orchestration | 3 | 4 | 4 | 4 | 4 | M | Useful, but requires disciplined runtime governance. | Managed automation setup and lifecycle ops. |
| Frontend shell surfaces (Guardian, Persona Studio, Trace Workbench) | 4 | 3 | 3 | 2 | 3 | O | Needed for adoption and contributor feedback. | UX integration and domain-specific configuration. |
| Supported local install path (Docker Compose) | 5 | 3 | 5 | 4 | 5 | M | Most likely user pain point and biggest paid-service opportunity. | Install, hardening, and maintenance retainers. |
| Packaged desktop distribution path (tester-facing) | 3 | 3 | 4 | 3 | 4 | M | Useful channel, but lifecycle/support overhead is non-trivial. | Packaging, update, and fleet support. |
| Diagnostics surfaces (`/health`, RAG trace, retrieval posture, eval trace) | 5 | 4 | 3 | 4 | 3 | O | Transparency and debuggability are credibility multipliers. | Operational interpretation and incident response. |
| Export/restore and migration seams | 4 | 4 | 5 | 5 | 5 | M | High-risk correctness domain; requires operational discipline. | Upgrade planning, migration execution, rollback support. |
| Connector/federation and extension seams | 3 | 5 | 5 | 5 | 5 | I | Powerful but expands attack and support surface fast. | Future managed ecosystem services. |
| Internal-only/operator routes and partial control-plane surfaces | 2 | 3 | 4 | 5 | 4 | I | Keep private until explicit support contract exists. | N/A (internal reliability instrumentation). |

## Value Thesis (What You Are Actually Selling)
The highest durable value is not licensing access to source code. It is reducing failure and time-to-value in real environments:
- installation and environment alignment,
- identity and permission correctness,
- retrieval correctness under real user data,
- queue/worker reliability under load,
- upgrade-safe operations with explicit rollback.

## Immediate Open-Core Candidate Set (Phase 1)
Recommend publishing now:
- Core runtime, API surfaces, and architecture docs.
- Retrieval broker/source-mode policy and diagnostics surfaces.
- Frontend runtime shell and supported local path docs.
- Test and proof harnesses that validate the supported path.

## Holdback Candidate Set (Phase 1)
Recommend deferring from public support promise:
- Connector/federation runtime enablement.
- Internal operator/control-plane routes without stable contracts.
- Unhardened automation and extension surfaces where defaults are not fail-closed.

## Reclassification Triggers
Move `I -> M` or `M -> O` only when all are true:
- explicit boundary contract documented,
- default-off or fail-closed behavior proven,
- migration/version behavior documented,
- incident playbook exists,
- at least one current-tip live proof artifact exists.
