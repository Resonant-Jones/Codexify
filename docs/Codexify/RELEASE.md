# Release Process

This project follows [Semantic Versioning](https://semver.org/).

## Versioning Guidelines
- Increment **MAJOR** for incompatible API changes.
- Increment **MINOR** for backward compatible functionality.
- Increment **PATCH** for backward compatible bug fixes.

## Steps to Cut a Release
1. Update version numbers in `pyproject.toml`, `setup.py`, and `CHANGELOG.md`.
2. Commit changelog entries for the new version.
3. Tag the commit with the version number, e.g. `v0.1.0`.
4. Push the tag and create a GitHub Release using the tag.
5. Attach built distributions to the release if applicable.

## Security Rewrite Gate (Mandatory for Beta)
1. If history was rewritten for secret remediation, force-push all rewritten refs:
   - `git push --force --all origin`
   - `git push --force --tags origin`
2. Create `SECURITY-REWRITE-NOTICE.md` as a normal post-rewrite commit on default branch.
3. Ensure the notice includes:
   - Rewrite date (UTC ISO-8601)
   - Pre-rewrite baseline hash
   - Post-rewrite default-branch hash
   - Statement that branches and tags were rewritten
   - Required re-clone/reset commands
   - CI/cache invalidation reminder
4. Block release until verification gate passes:
   - `pre-commit run --all-files`
   - `gitleaks dir . --exit-code 1`
   - `gitleaks git . --log-opts="--all" --exit-code 1`

## Beta Readiness Gate (Current State: 2026-03-17)

- Provider governance is an explicit release gate. `guardian/core/provider_registry.py` is the canonical source of truth for provider authorization, availability, and capability decisions consumed by catalog, health, router, and worker code. Beta claims should match that registry-backed behavior and the active supported-profile contract, not just environment intent.
- Operator confidence is still backend-first. The required evidence pack for beta decisions is `GET /health`, `GET /health/llm`, `GET /health/chat`, `GET /api/llm/catalog`, backend/worker logs, and `/metrics`. This is the current shipped path for release validation.
- The Command Center / Observability Deck is not a released end-user beta surface. Partial operator-facing UI work and internal routes may exist in the repo, but they should be treated as internal or dev-only until they are documented as part of the supported release surface.
- Internal routes are release caveats, not product proof. In the current supported profile, `command_bus` is explicitly internal-only, and internal/operator-facing routes should not be used as evidence that a general user-facing operator console has shipped.
- Green boot is not enough for beta confidence. Release confidence depends on accurate alignment between the supported profile, provider registry decisions, catalog output, and live health behavior. If health reads green while the runtime profile, provider posture, or catalog truth is drifting, the release read remains internal-only.
- As of 2026-03-17, the runtime audit posture is still limited internal validation only. Use `docs/release/run/2026-03-17-runtime-stability-audit.md` as the current release-read anchor when deciding whether beta promotion is justified.

### Beta Go / Hold Checklist

Status legend:
- `ready`: documented and supported by the current repo evidence
- `partial`: partly supported, but not enough for beta signoff alone
- `hold`: current repo evidence says beta should not be called ready
- `needs operator validation`: still requires manual multi-surface confirmation

- `[ready]` Provider governance policy is explicit and documented. `guardian/core/provider_registry.py` is the canonical governance source, and the current supported beta contract is documented in `config/supported_profiles/v1-local-core-web-mcp.yaml`.
- `[ready]` Provider registry, supported profile, catalog, and health alignment is an explicit release requirement. The docs already state that none of those surfaces is sufficient alone, and beta claims must match registry-backed runtime truth rather than environment intent.
- `[ready]` Current internal observability status is accurately described. The shipped evidence pack is backend-first: `GET /health`, `GET /health/llm`, `GET /health/chat`, `GET /api/llm/catalog`, backend/worker logs, and `/metrics`.
- `[ready]` Command Center / Observability Deck remains internal or dev-only, not a released beta operator surface. Partial operator UI in the repo is still a release caveat, not proof of a shipped operator console.
- `[partial]` Release confidence is stronger for backend/runtime correctness than for live operator inspectability. The March 17 runtime audit shows strong deterministic test slices and useful live health signals, but diagnosis still depends on stitched backend evidence rather than an integrated operator surface.
- `[hold]` The live Compose beta runtime currently honors the supported-profile contract end to end. The March 17 runtime audit says it does not: Compose still boots with `CODEXIFY_BETA_CORE_ONLY=false`, cloud providers enabled, and non-core routes mounted.
- `[hold]` Provider registry decisions, catalog output, and live health are currently proven aligned on the running supported path. The March 17 runtime audit says they are not yet trustworthy enough for promotion, because health can read green while the supported-profile contract is still invalid.
- `[hold]` Fresh live supported-path evidence exists in the current audit window for assistant completion plus upload -> embed -> retrieve. The March 17 runtime audit says that proof was not refreshed because smoke aborted at the profile gate before the happy-path checks completed.
- `[needs operator validation]` A beta signoff can be made from shipped operator surfaces alone. Current docs say no: operators still need endpoints, logs, metrics, and sometimes direct Compose/container inspection to explain runtime truth.

Current decision as of 2026-03-17: `hold`.
The repo supports a stronger claim for backend/runtime stabilization than for beta promotion. The current blocker set is the supported-profile contract drift plus the missing fresh live supported-path proof in the same audit window.

### Beta Go / Hold Decision Rubric

- `Go` only when the supported-profile contract is active at runtime, quarantined/internal-only routes are not exposed on the supported beta surface, provider registry posture agrees with catalog and health, and the current audit window includes fresh live proof for assistant completion plus upload -> embed -> retrieve.
- `Hold` whenever runtime flags drift from the supported profile, green health masks contract drift, non-core routes remain mounted on the supposed beta surface, or the current audit window lacks fresh supported-path evidence.
- `Tolerable beta limitations` include operating without a shipped Command Center / Observability Deck, using backend endpoints/logs/metrics as the primary operator workflow, and treating RAG trace as a dev-only debugging aid rather than durable release proof.
- `Release blockers` are issues that invalidate release truth itself: the running stack does not honor the documented supported profile, provider policy/catalog/health disagree on the supported posture, or live supported-path happy-path evidence is missing or stale.
