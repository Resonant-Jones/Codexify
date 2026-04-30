# 2026-04-30 Local Beta Release Evidence

This note records the GHCR pullability state for the local-beta runtime images and the fallback validation path for the webUI bundle.

## Registry Pull Checks

- Clean shell baseline: `docker logout ghcr.io`
- Runtime image pull: `docker pull ghcr.io/resonant-jones/codexify-runtime:local-beta`
  - Result: successful anonymous pull
- WebUI image pull: `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta`
  - Result: `unauthorized` from a clean shell
- GHCR login using the current GitHub identity: `gh auth token | docker login ghcr.io -u Resonant-Jones --password-stdin`
  - Result: login succeeded
- WebUI image pull after login: `docker pull ghcr.io/resonant-jones/codexify-webui:local-beta`
  - Result: `403 Forbidden`
- Package listing probe: `gh api '/users/Resonant-Jones/packages?package_type=container&per_page=100'`
  - Result: `403` with a `read:packages` scope requirement

## Interpretation

- `ghcr.io/resonant-jones/codexify-runtime:local-beta` is publicly pullable from a clean shell.
- `ghcr.io/resonant-jones/codexify-webui:local-beta` is not anonymously pullable.
- The current GitHub identity used in this workspace does not have sufficient package access to pull the webUI image, even after Docker login to GHCR.
- The webUI beta bundle must therefore be documented as GHCR-authenticated for this tester identity unless package access is granted later.

## Fallback Validation Path

- The local bundle validation script remains the supported local-build fallback:
  - `bash scripts/verification/check_webui_runtime_bundle.sh`
- That script validates the Compose bundle and local frontend build, but it does not prove registry pullability.
