# Documents API authenticated-access proof

- Date: 2026-07-21
- Tested commit: `63c085b9d5d3e1a5313466a23ce09b55bf248bd6`
- Runtime profile: local Docker Compose, `v1-local-core-web-mcp`, local auth, local-safe exposure defaults
- Execution lane: architecture-impact; bounded auth-contract repair
- ADR impact: **Aligned with existing ADR(s)**; no authorization or exposure contract was changed
- Final outcome: **BLOCKED**

## Blocking result

The reported browser `403 Forbidden` could not be reproduced or attributed to
FastAPI, the public-exposure middleware, a proxy, or a route-level ownership
decision. The supported backend exits with code 3 during Uvicorn lifespan
startup and never listens on port 8888. The frontend dev server is also not
running. No authenticated browser replay is therefore valid evidence.

No code or focused test repair was applied. This preserves the fail-closed
authentication and authorization contract until the exact request and issuing
layer are observable.

## Before-state request record

The task reports a browser-origin failure, but does not include a captured
request trace. The exact failing method, path, response body, and issuing layer
are therefore **unknown**.

The reported/expected Documents UI candidate is:

| Field | Recorded value |
| --- | --- |
| Browser origin | `http://localhost:5173` (reported runtime context) |
| Candidate method | `GET` |
| Candidate path | `/api/media/documents?limit=1` |
| Frontend call site | `AppShell.tsx` calls `api.get("/media/documents", ...)` |
| API client | canonical `frontend/src/lib/api.ts` |
| Runtime base | web default `/api`; direct backend diagnostic target `http://127.0.0.1:8888` |
| Credential mechanism | local `X-API-Key` or Bearer session token, value not recorded |
| Reported status | `403 Forbidden`; exact response content type/body not captured |
| Issuing layer | unknown: browser/proxy/FastAPI middleware/route |

The direct supported-runtime probe returned no HTTP response because the host
port was closed:

```text
GET http://localhost:8888/api/media/documents?limit=1
curl: failed to connect to localhost port 8888
HTTP status: 000
```

## Trace and seam comparison

### Frontend

The primary Documents load in `frontend/src/components/persona/layout/AppShell.tsx`
uses the shared Axios instance from `frontend/src/lib/api.ts`. The client owns
runtime URL resolution, `withCredentials`, and local `X-API-Key`/Bearer header
injection. Its response interceptor preserves a `403` as an error; it only
clears auth state on `401`.

Known protected comparison calls in the same component also use the canonical
client (`/chat/threads` and `/api/projects`). No Documents-only credential
path was found in the reported AppShell call.

An exported `buildThreadDocumentsPath` helper is stale relative to the backend
route, but no current frontend component calls it. It is not evidence for the
reported browser failure and was not changed.

### Backend

The media Documents route is:

```text
GET /api/media/documents
```

It is mounted from `guardian/routes/media.py` under the `/api/media` prefix,
uses the canonical media API-key dependency, and resolves the request user
scope. `guardian/routes/documents.py` separately exposes:

```text
GET /api/threads/{thread_id}/documents
```

with `Depends(require_api_key)` and `Depends(get_request_user_scope)`.

`guardian/core/public_exposure.py` remains default-deny for public-allowlist
profiles and does not make Documents public. The supported local-safe profile
includes the media and Documents routes. No route-specific bypass, dependency
weakening, or ownership change was found.

## Root cause and issuing layer

- Root cause: **unproven**.
- Original `403` issuing layer: **unproven**.
- Authentication failure, authorization failure, exposure-policy rejection,
  CORS/proxy rejection, route mismatch, and stale client state remain
  distinguishable hypotheses, not established facts.

The supported runtime failure is independently evidenced as a startup/config
coherence failure after route registration, not as a Documents authorization
response. The startup logs expose no usable HTTP response or route-level
decision for the reported request.

## Runtime and contract results

### Supported runtime

**BLOCKED.** Docker Compose dependencies reached the following state during
the diagnostic window:

- PostgreSQL: healthy
- Redis: healthy
- Neo4j: unhealthy due to existing authentication failure
- backend: exited with code 3 during Uvicorn lifespan initialization
- frontend dev server: not listening on port 5173

No volume reset or destructive credential/database action was taken.

### Existing focused auth/document tests

These isolated tests execute against the backend runtime image and do not
constitute supported end-to-end runtime proof:

- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -q tests/routes/test_thread_documents.py -k 'auth or allows_local or allows_bearer or denies_unauthenticated'` — **PASS** (3 selected)
- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -q tests/routes/test_documents_account_scope.py -k 'thread_documents or conflicting_user_id' tests/routes/test_media_account_scope.py -k 'documents or account or unauthorized'` — **PASS** (13 selected)
- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -q tests/auth/test_private_preview_access.py tests/core/test_multi_user_auth_mode.py tests/core/test_public_allowlist_exposure.py` — **PASS** (9 selected)

A broader baseline command also exposed an unrelated pre-existing failure:

- `docker compose run --rm --no-deps --entrypoint python backend -m pytest -q tests/routes/test_thread_documents.py tests/routes/test_media_account_scope.py tests/routes/test_documents_account_scope.py` — **FAIL**; one legacy test expects a response without `embedding_status`/`embedding_error`, while the current route includes those fields. No task file was changed to hide this baseline failure.

The requested new `tests/test_documents_auth_contract.py` was not created:
no narrow repair was proven, so adding a repair-specific contract test would
assert an unverified premise.

### Frontend tests

Not run. No frontend file was changed, and the frontend dependencies are not
installed in this worktree.

### Diff hygiene

- `git diff --check` — **PASS**.
- Authorized staged diff review — **PASS**; only this proof artifact is staged.

## Files changed

- `docs/release/run/2026-07-20-documents-auth-403-proof.md` — bounded
  investigation and blocked proof artifact only.

No files under the frontend auth client, runtime configuration, Guardian auth,
exposure, router composition, document routes, or focused test paths were
modified.

## Authorization and privacy checks

- Authorized caller result: **not proven in the supported runtime**; isolated
  route tests pass for the canonical auth path.
- Unauthenticated result: **preserved and covered by passing isolated tests**;
  no unauthenticated request was made public.
- Unauthorized cross-user/project result: **preserved and covered by passing
  isolated scope tests**.
- Secrets scan: **PASS**; this artifact contains no API-key values, tokens,
  cookies, authorization values, or credentials.
- Private document-content scan: **PASS**; this artifact contains no document
  bodies, parsed text, private filenames, source URLs, or content values.

## Invariants check

1. Documents endpoints were not made public.
2. Existing authentication dependencies were not removed or weakened.
3. No Documents-only token or authorization mechanism was added.
4. No component-local auth behavior was added.
5. Ownership, project scope, and thread scope were not changed.
6. Parsing, embedding, queueing, retrieval, and completion behavior were not changed.
7. Image upload, vision routing, and image generation behavior were not changed.
8. No parallel authentication truth surface was created.

## ADR and current-truth anchors

This remains aligned with accepted **ADR-005: Runtime Mode and Account
Boundary Invariants**. The proposed **ADR-039: Operator / User Access
Boundary** was reviewed as context only; it is not a shipped auth contract and
was not changed. Current-truth anchors confirmed were:

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/authState.ts`
- `frontend/src/lib/runtimeConfig.ts`
- `guardian/guardian_api.py`
- `guardian/routes/documents.py`
- `guardian/routes/media.py`
- `guardian/core/dependencies.py`
- `guardian/core/public_exposure.py`

## Remaining limitation and next proof required

The task remains blocked until the supported runtime reaches a listening state
and the original browser request is captured with a redacted HAR/network
record or equivalent. The next run must compare the Documents request with a
known-working protected request from the same browser session, including path,
origin, credentials mode, auth mechanism name, response content type, and
issuing layer. Only then should a narrow repair be selected. If that evidence
shows a raw-fetch bypass in workspace components outside this task's authorized
paths, the repair requires a separately authorized task.

## Final outcome

**BLOCKED** — no authenticated Documents access repair is claimed, and
fail-closed behavior remains intact.
