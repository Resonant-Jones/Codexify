# Public Ingress Authentication Boundary Proof

**Outcome: HOLD**
**Mode: PROOF**
**Checkout:** `/Volumes/Dev_SSD/Codexify-main`
**Branch:** `codex/restore-conversation-import-pipeline`
**HEAD:** `418729f48dab6c67945b9d99853d6ed979f3ec52`

## Scope and evidence boundary

This is a verification-only task. Cloudflare Access, production auth, route
semantics, frontend configuration, Compose, and environment files were not
changed. The boundary defect below was reproduced before creating the proposed
regression suite, so the task follows the specified HOLD path: no deliberately
failing permanent suite was added. This receipt records the exact reproduced
failure and distinguishes it from observations made against the configured
private-preview Compose deployment.

The requested application-level suite and broader route matrix were not run
after the failure was found. The running private-preview origin was not
restarted or reconfigured.

## Orientation receipt

- Current-truth anchor: `docs/architecture/00-current-state.md`.
- Workflow lane: Architecture-Impact; verification only.
- ADR disposition for this verification: aligned; no ADR change.
- Release/support truth was not changed.

## Effective configuration contract

The checked-in private-preview Compose overlay explicitly sets:

| Variable | Configured private-preview value | Source |
| --- | --- | --- |
| `GUARDIAN_EXPOSURE_MODE` | `private_preview` | `docker-compose.private-preview.yml` |
| `GUARDIAN_AUTH_MODE` | `remote` | `docker-compose.private-preview.yml` |
| `CODEXIFY_MULTI_USER_ENABLED` | `true` | `docker-compose.private-preview.yml` |
| `CODEXIFY_SINGLE_USER_ID` | Not set by overlay | not used by `private_preview` identity resolution |
| `GUARDIAN_SESSION_SECRET` | required, value redacted | Compose interpolation fails if missing |
| `GUARDIAN_JWT_SECRET` | required, value redacted | Compose interpolation fails if missing |
| `CODEXIFY_PREVIEW_APPROVED_EMAILS` | required, values redacted | Compose interpolation fails if missing |
| `CODEXIFY_PREVIEW_ADMIN_EMAILS` | required, values redacted | Compose interpolation fails if missing |
| `DEBUG`, `LOCAL_DEV` | no preview override | debug identity override applies only outside `private_preview` |
| API-key behavior | preview dependencies require an approved Guardian session; ordinary remote mode rejects `X-API-Key` | `guardian/core/dependencies.py`, `guardian/core/preview_access.py` |
| Allowed origins | Compose sets `GUARDIAN_ALLOWED_ORIGINS` empty; same-origin shell/API needs no CORS grant | Compose and Guardian initialization |

The configured Compose posture is explicit and the live preview request checks
below were consistent with it. The broader application defaults are not
fail-closed for an accidentally reachable origin: `_exposure_mode()` defaults
to `local_safe`; `_auth_mode()` defaults to `local`; multi-user mode defaults
false; and `get_request_user_id()` then returns `get_single_user_id()`, whose
canonical fallback is `local`.

### Reproduced failure

With `GUARDIAN_EXPOSURE_MODE`, `GUARDIAN_AUTH_MODE`,
`CODEXIFY_MULTI_USER_ENABLED`, `CODEXIFY_SINGLE_USER_ID`, `DEBUG`, and
`LOCAL_DEV` absent, a TestClient endpoint using the real
`require_api_key` and `get_current_user` dependencies was called with a
synthetic test-only `X-API-Key`. A mocked settings object contained only that
synthetic key. The endpoint returned HTTP 200 and `user_id: local`.

Exact command:

```sh
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python - <<'PY'
import os
from types import SimpleNamespace
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from guardian.core import dependencies
for key in ('GUARDIAN_EXPOSURE_MODE','GUARDIAN_AUTH_MODE','CODEXIFY_MULTI_USER_ENABLED','CODEXIFY_SINGLE_USER_ID','DEBUG','LOCAL_DEV'):
    os.environ.pop(key, None)
os.environ['CODEXIFY_DISABLE_DOTENV'] = '1'
dependencies.get_settings = lambda: SimpleNamespace(GUARDIAN_API_KEY='synthetic-test-key', GUARDIAN_API_KEYS=None)
app = FastAPI()
@app.get('/protected')
def protected(_key: str = Depends(dependencies.require_api_key), user_id: str = Depends(dependencies.get_current_user)):
    return {'user_id': user_id}
response = TestClient(app).get('/protected', headers={'X-API-Key':'synthetic-test-key'})
print('status=', response.status_code)
print('resolved_local=', response.status_code == 200 and response.json().get('user_id') == 'local')
print('response_body=', response.json())
PY
```

Result: `status=200`, `resolved_local=True`, `response_body={'user_id': 'local'}`.
No live credential was read or emitted. This proves the application-level
missing-configuration path can accept a valid local API key and resolve the
local account when exposed without the required preview variables. The
configured Compose overlay prevents this exact omission in that one supported
deployment recipe, but the Guardian code path itself does not reject the
degraded posture.

## Current route and runtime observations

| Surface | Evidence | Result |
| --- | --- | --- |
| Private-preview dependencies | `is_private_preview()` routes protected auth through `require_preview_principal()` and uses only the signed Guardian session subject if allowlisted | code-path review; not a new suite |
| Anonymous shell at `http://127.0.0.1:8081/` | live request; HTTP 200, `Cache-Control: no-cache` | observed |
| Anonymous `/api/chat/threads` | live request; HTTP 401 | observed |
| Same request with `X-User-Id: local`, loopback `X-Forwarded-For`, loopback `CF-Connecting-IP`, and plausible Cloudflare email header | live request; HTTP 401 | observed |
| Account/thread mutation, media/document resource, admin route, SSE/event and WebSocket route matrix | not exercised after the defaulting failure | unproven |
| Two-account ownership and invalid/expired/revoked session matrix | not exercised | unproven |
| Login/activation replay and credential mutation matrix | not exercised | unproven |
| Live `X-API-Key` lane | not attempted; no live key was read or logged | unproven live; synthetic missing-config repro above failed closedness |
| Cloudflare cache rules | not inspected; no Cloudflare mutation or connection used | unknown |

## Sixteen failure classes

`PASS` below is limited to the named code path or live probe; it is not a
whole-application qualification. `NOT PROVEN` means this task stopped before
the specified targeted coverage. `FAIL` is the reproduced missing-config
boundary.

| # | Failure class | Result | Evidence / limitation |
| --- | --- | --- | --- |
| 1 | Anonymous request to implicit local-user fallback | **FAIL** | Missing-mode TestClient path plus synthetic valid local API key resolved `local`. Anonymous requests without credentials still normally fail API-key auth. |
| 2 | Source-IP/loopback trust to local fallback | **PASS, narrow** | The identity resolver contains no source-IP selection; local fallback in the reproduced path is unconditional on network appearance. No full route matrix. |
| 3 | Spoofed proxy headers authenticate | **PASS, narrow** | Live thread collection request with local/forwarded/CF IP headers returned 401. |
| 4 | Cloudflare identity headers replace Guardian session | **PASS, narrow** | Same live probe included a plausible Access email header and returned 401. |
| 5 | Local API key accepted through remote ingress | **FAIL for omitted-mode path** | Real dependencies accepted a synthetic configured key when auth/exposure settings were absent and resolved `local`; configured Compose preview explicitly sets preview/remote/multi-user. |
| 6 | Frontend guard is sole protection | **PASS, narrow** | Direct loopback API request without a frontend route guard returned 401. |
| 7 | Direct protected API bypass | **PASS, narrow** | Direct `GET /api/chat/threads` returned 401, including the spoof-header request. Other protected routes not exercised. |
| 8 | Object ID or `user_id` cross-account access | **NOT PROVEN** | Two-account read/mutation tests not run. |
| 9 | Unauthenticated SSE/WebSocket/event stream | **NOT PROVEN** | SSE routes depend on `require_api_key`; actual connection-denial tests and WebSocket route review were not completed. |
| 10 | Admin/dev/debug endpoint exposure | **NOT PROVEN** | Representative admin tests not run in this task. |
| 11 | Open/replayable activation or registration | **NOT PROVEN** | Registration denial is covered by existing tests in preview; activation replay was not exercised here. |
| 12 | Invalid/expired/revoked session accepted | **NOT PROVEN** | Session-invalidity matrix not run. |
| 13 | Wildcard credentialed CORS | **PASS, config/code only** | Guardian origin initialization uses a configured origin list and credentials; private-preview sets the list empty. No hostile-Origin live preflight was run. CORS is browser policy, not the Guardian authentication boundary. |
| 14 | Browser-shipped server secrets | **PASS, contract-source only** | Existing private-preview Compose contract asserts server/provider keys absent from frontend environment; existing suite was not run in this stopped task. |
| 15 | Authenticated/user-specific responses publicly cacheable | **NOT PROVEN** | No cache-control header appeared on the live protected 401, which does not prove successful account responses or Cloudflare cache policy. |
| 16 | Internal backend/service ports reachable outside intended origin | **PASS, contract-source only** | Existing private-preview contract asserts only loopback `127.0.0.1:8081` published; contract suite and rendered Compose were not run here. |

## ADR and future Access posture

This verification changes no accepted contract. ADR-039 and ADR-040 are
currently **Proposed**, not accepted. ADR-005 requires explicit multi-user
identity and account scoping but does not require Cloudflare Access. ADR-051
specifies mutually exclusive local-key and remote-session client modes. ADR-069
preserves the local-first Beta perimeter. ADR-088 identifies Cloudflare Access
as an outer perimeter rather than Guardian identity authority. The inspected
accepted ADRs do not require Access to remain an application admission layer.

The target `Cloudflare edge -> anonymous shell -> Guardian session authority`
is therefore not blocked by an accepted ADR found in this pre-read. That is a
governance reading, not a safety qualification. Access must remain enabled
until the missing-configuration boundary and remaining proof gates are closed.

## Validation record

| Command / action | Result |
| --- | --- |
| `git status --short --branch --untracked-files=all` | Initial checkout was clean on `codex/restore-conversation-import-pipeline`; five commits ahead of its upstream. |
| `docker compose -p codexify_private_preview --env-file .env.private-preview -f docker-compose.yml -f docker-compose.private-preview.yml ps --format json` | Runtime services reported healthy; output was inspected without disclosing environment values. |
| Live `curl` probes to `http://127.0.0.1:8081/` and `/api/chat/threads`, including spoof headers | Shell 200; protected API 401; spoofed protected API 401. |
| Synthetic TestClient missing-mode probe above | **FAIL**: HTTP 200 as `local`; triggers HOLD and ends security-suite execution. |
| `pytest -v tests/identity/test_public_ingress_auth_boundary.py` | **NOT RUN**: stopped before suite creation after reproducing the security defect; no failing permanent test retained. |
| `pytest -v tests/identity/test_identity_boundary_contract.py` | **NOT RUN**: stop-on-failure boundary. |
| `pytest -v tests/ops/test_private_preview_contract.py` | **NOT RUN**: stop-on-failure boundary. |
| `git diff --check` | Passed for tracked diff; the receipt is untracked and Git's index is read-only in this workspace. |
| Python whitespace/final-newline check on the untracked receipt | Passed after removing Markdown hard-break trailing spaces; checked at closeout. |
| `git diff --no-index --check /dev/null docs/architecture/proofs/runtime/2026-09-25-public-ingress-auth-boundary-proof.md` | No whitespace diagnostics; exit 1 is expected because `/dev/null` and the new receipt differ. |
| `git add` / `git diff --cached --check` | Could not stage: Git returned `fatal: Unable to create '.../.git/index.lock': Operation not permitted`; no index state changed. |

## Conclusion and required follow-up

**HOLD.** The configured private-preview Compose posture is explicit and the
bounded live checks rejected unauthenticated protected thread access. However,
Guardian's missing-exposure/missing-auth path remains local/single-user, and a
synthetic valid local API key reaches a protected dependency and resolves the
canonical `local` user. This does not establish safe behavior for a public
origin whose mode configuration is omitted.

No regression suite was retained because the task spec requires stopping at a
security assertion failure rather than committing a deliberately failing
suite. A separate atomic task must define and prove a fail-closed startup or
request boundary for incomplete public/preview configuration. After that
repair, rerun the complete matrix in the task spec while Cloudflare Access
remains enabled. No Access-free canary is authorized by this receipt.

## Follow-up: private-preview bootstrap guard

This section records a follow-up to the original HOLD. The original result and
failure matrix above remain unchanged: the public-ingress authentication proof
did not pass, and its full matrix still requires a fresh rerun.

The reproduced generic missing-mode path reflects intentional local-first
Guardian behavior. The deployment-boundary issue is narrower: a public
private-preview deployment must not reach the backend unless its own
remote-auth/private-preview configuration is effective. Global local defaults
remain unchanged.

The follow-up change adds a Compose-owned Guardian posture mapping and a
one-shot startup check for `private_preview`, `remote`, multi-user enabled,
and `v1-whooshd-deepseek-web`. Backend startup waits for a successful check;
Cloudflare Access and its configuration remain untouched. The full
public-ingress boundary matrix remains required before any Access-removal
decision.

### Follow-up source lineage

- Intended target used for comparison: local `main` at
  `646eaa397c40e1dfa637002bee28c88033be0f50`.
- `origin/main` was `84ffc5b938e964ae3e960f3a503836994776e3ca`; the two refs
  differed by three commits. The task-owned Compose, test, and Guardian auth /
  exposure / config files were identical between this worktree and both refs.
- Implementation checkout: `codex/restore-conversation-import-pipeline` at
  `95a71db50bea14bc98dcb800585168722ad09241` before task edits.

### Follow-up changes and validation

The preview overlay now defines the required Guardian posture once and shares
it between the backend and `private-preview-auth-posture`. The backend waits
for that one-shot check to complete successfully. The check rejects missing,
empty, or contradictory exposure/auth values and also verifies the existing
supported profile and multi-user setting. Guardian source defaults were not
changed. The runbook now documents the mandatory preview posture and preserves
Cloudflare Access.

Validation results:

- Initial focused-suite run: 4 existing service-inventory parametrizations failed because the expected overlay service set did not yet include the new posture checker; the task-scoped assertion was updated and the rerun passed.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v tests/ops/test_private_preview_contract.py` — PASS, 23 tests.
- `bash scripts/private_preview_validate.sh static` — PASS; published port remained `127.0.0.1:8081 -> 8080`.
- The new startup-check fixture passed with the valid posture and failed for missing exposure, missing auth, empty exposure, empty auth, local exposure, and local auth.
- `docker compose --env-file .env.private-preview -f docker-compose.yml -f docker-compose.private-preview.yml config --quiet` — PASS.
- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python scripts/validate_docs.py` — PASS.
- `git diff --check` — PASS for tracked changes; the untracked receipt also passed a Python whitespace/final-newline check.

The original public-ingress proof remains **HOLD**. This follow-up validates
only the private-preview bootstrap guard; it does not rerun or close the
public-ingress boundary matrix. No Cloudflare settings or live preview
containers were changed. Staging and commit were blocked because Git could
not create `/Volumes/Dev_SSD/Codexify-main/.git/index.lock` (`Operation not
permitted`); no staged state was created. The validated worktree is preserved.
