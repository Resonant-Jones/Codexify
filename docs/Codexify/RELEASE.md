# Release Process

This project follows [Semantic Versioning](https://semver.org/).

## Recent Release Notes

### 2026-03-17 - Provider Governance Policy Synchronization

- Documented the canonical provider-governance map now enforced by the registry as the implementation source of truth.
- Recorded the current provider classifications exactly as implemented: `discovery_backed` (`alibaba`, `minimax`), `static_authorized` (`openai`, `groq`), `local_only` (`local`), and `disabled` (`anthropic`, `gemini`).
- Recorded that router-side discovery validation derives from registry policy instead of a duplicated router-local provider list.
- Synchronized release and architecture documentation with the current provider contract without changing runtime behavior.

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
