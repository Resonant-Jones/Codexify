# Public Readiness Checklist (v1)

Date: 2026-05-10  
Scope: Open-source release readiness for Codexify core surfaces

## How to Use
- Mark each item `done`, `partial`, or `blocked`.
- Do not publish as "ready" while any blocker-class item is unresolved.

## 1. Legal and Repository Hygiene
- [ ] License file selected and committed (`Apache-2.0` recommended baseline).
- [ ] `CONTRIBUTING.md` reflects actual maintainer workflow.
- [ ] `SECURITY.md` includes disclosure path and response expectations.
- [ ] Public repo history has no accidental secrets.
- [ ] `.env` and local runtime artifacts are fully ignored.

## 2. Boundary Truth
- [ ] Open-core boundary doc published (`open-core-boundary-v1.md`).
- [ ] Explicit list of internal-only surfaces documented.
- [ ] Supported install path explicitly stated and narrow.
- [ ] Unsupported/experimental surfaces clearly labeled.

## 3. Security Baseline
- [ ] Default setup does not require shipping shared secrets in frontend builds.
- [ ] Identity/ownership boundaries are documented and tested.
- [ ] Tool invocation boundaries are policy-enforced (not prompt-enforced).
- [ ] Egress posture and provider exposure rules are explicit.
- [ ] Sensitive diagnostics routes are authenticated and scoped.

## 4. Reproducible Install and Validation
- [ ] Fresh machine install path succeeds using public docs.
- [ ] Health and critical-path verification commands are documented.
- [ ] At least one current-tip live proof artifact exists for supported path.
- [ ] Failure-mode troubleshooting section exists for common break points.

## 5. Quality and Operations
- [ ] Regression tests exist for release-contract surfaces.
- [ ] Migration/upgrade path is documented.
- [ ] Rollback strategy exists for failed upgrades.
- [ ] Logging/diagnostics surfaces are documented for operators.

## 6. Release Messaging Discipline
- [ ] Public README claims only what current runtime evidence supports.
- [ ] No release copy relies on internal-only routes as product proof.
- [ ] "Implemented" versus "verified" versus "live-proven" language is separated.

## 7. Commercial Readiness
- [ ] Service offers published (`service-offers-v1.md`).
- [ ] Clear statement of what is free versus paid.
- [ ] Initial engagement path exists (install package or discovery call).

## 8. Community and Throughput Guardrails
- [ ] Issue templates split bug reports from feature requests.
- [ ] Reproduction template asks for runtime posture and health evidence.
- [ ] Maintainer response expectations are realistic for solo operation.
- [ ] Contribution acceptance boundaries are explicit.

## Blocker Class (Do Not Launch Publicly Yet)
Any of these should block public launch claims:
- Supported profile and live runtime posture are mismatched.
- Current-tip supported-path proof is missing for core workflows.
- Secret/exposure posture is unclear in default install guidance.
- Boundary between supported and internal-only surfaces is ambiguous.
