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
