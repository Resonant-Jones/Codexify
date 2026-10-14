# MCP Memory Adapter v1 (read-only)

**Status:** implemented, uncommitted at time of writing.
**Scope:** structural, read-only memory access for local MCP clients.
**Not part of Codexify's supported Beta profile.**

---

## 1. Purpose

`codexify-memory-mcp` is a standalone **stdio** MCP server that lets local MCP clients
(Claude Code, Cursor, Codex) read account-owned Codexify memory through Guardian's existing
authenticated HTTP APIs.

It is an *additional consumer of existing read contracts*. It does not create memory ownership,
retrieval authority, persistence semantics, or mutation semantics, and it is governed by:

- **ADR-084** — Unified Account-Owned Memory Store
- **ADR-069** — Beta runtime support boundary
- **ADR-081** — Canonical project ownership (where project-scoped data appears)

No new ADR is required: the authority boundary is preserved.

---

## 2. Supported v1 scope

Exactly **five read-only tools** are registered:

| Tool | Upstream endpoint | Purpose |
|---|---|---|
| `memory_status` | `GET /health` + bounded probes | Report which read surfaces are usable |
| `vault_list` | `GET /api/memory-vault/items` | List account-owned Vault items |
| `vault_get` | `GET /api/memory-vault/items/canonical/{id}` | Read one canonical item |
| `memory_list` | `GET /api/memory/{silo}` | List a memory silo |
| `list_fact_candidates` | `GET /personal-facts/candidates` | Read unpromoted Personal Fact candidates |

### Explicitly out of scope

Semantic/vector recall, any mutation, purge/erasure, fact promotion, vault governance writes,
OAuth or remote session auth, remote MCP transport, MCP resources/prompts primitives, chat
execution, and supported-Beta qualification.

**The absence of semantic recall is an intentional product boundary, not an incomplete
implementation.** There is no dormant recall code, no `recall.py`, and no configuration switch
that would enable one.

---

## 3. Installation

```bash
pip install -e ".[mcp-memory]"
```

The `mcp-memory` extra exists because the console script is a shipped entrypoint: Python packaging
does not guarantee that a script's imports resolve merely because a `dev` extra was installed.

> **Why the extra pins `starlette<0.49`.** MCP v2 declares only `starlette>=0.27`, so an unbounded
> install resolves starlette 1.x. FastAPI 0.119.1 requires `starlette<0.49.0`. Installing MCP v2
> without the pin **breaks the Guardian application at import time**
> (`Router.__init__() got an unexpected keyword argument 'on_startup'`). The upper bound keeps both
> packages satisfied: starlette 0.48.0 satisfies MCP 2.x *and* FastAPI.

Running the command without the extra installed produces an actionable message naming the extra and
the install command — never a raw `ModuleNotFoundError`.

The adapter itself talks to Guardian using the repository's existing `httpx`. It does **not** use
`httpx2` (which MCP v2 pulls in for its own transport), and no unrelated code was migrated.

---

## 4. Running

```bash
codexify-memory-mcp --help
```

### Configuration

| Variable | Requirement |
|---|---|
| `CODEXIFY_MCP_BASE_URL` | **Required, no default.** Guardian's loopback origin, e.g. `http://127.0.0.1:8010`. Must be `http` on a literal loopback host (`127.0.0.1`, `localhost`, `::1`). No credentials, query, fragment, or path prefix. |
| `CODEXIFY_MCP_API_KEY` | Required. Falls back to `GUARDIAN_API_KEY`. |
| `CODEXIFY_MCP_TIMEOUT` | Optional. Default `10.0` seconds, bounded `0.1`–`120.0`. |
| `CODEXIFY_MCP_USER_ID` | **Unsupported. Rejected when populated** — not silently ignored. |

**There is no implicit port default.** Port 8000 on the Codexify host currently belongs to *Whoosh'd*,
not Guardian; assuming it would point the adapter at the wrong service.

Every rule fails closed at startup with `invalid_configuration`. The adapter refuses to start when
Guardian is configured in a remote-family auth mode (`GUARDIAN_AUTH_MODE` ∈ remote/cloud/hosted/
public/prod/production) or `GUARDIAN_EXPOSURE_MODE=public_allowlist`, because those modes reject
static API keys. v1 supports local API-key auth only.

### Example MCP client configuration

```json
{
  "mcpServers": {
    "codexify-memory": {
      "command": "codexify-memory-mcp",
      "env": {
        "CODEXIFY_MCP_BASE_URL": "http://127.0.0.1:8010",
        "CODEXIFY_MCP_API_KEY": "<your-guardian-api-key>"
      }
    }
  }
}
```

---

## 5. Guardian origin verification

Before any credential is transmitted, the adapter issues an **unauthenticated** `GET /health` and
requires Guardian's fingerprint: a JSON object with `service == "core"` and
`status` ∈ {`ok`, `degraded`, `down`}.

Only then is `X-API-Key` attached to subsequent requests. A non-Guardian listener — including the
Whoosh'd service that currently occupies port 8000 — fails with `wrong_upstream`, and **no request
carrying the API key is ever made**. The result is cached for the process lifetime.

> **Residual risk — this is not server authentication.** Loopback plus a health fingerprint
> protects against *accidental misconfiguration* (a wrong port, a different local service). It is
> **not** cryptographic: a malicious local process could imitate the `/health` response and receive
> the API key. Defending against that would require TLS or a pinned fingerprint, which is out of v1
> scope. Do not describe this mechanism as server authentication.

Note that `memory_status` itself is an *authenticated* probe: once the origin is verified, calling
it transmits the API key to the verified origin and issues `limit=1` reads. Probe bodies are
**discarded**; only reachability and error classification are returned. No memory content, item
fields, or reconstructing counts ever appear in status output.

---

## 6. Authentication assumptions and account scope

Guardian resolves account identity. The adapter:

- sends only `X-API-Key`;
- accepts **no** `user_id` (or any account) tool argument;
- transmits **no** caller-supplied identity;
- performs **no** client-side filtering that could be mistaken for an authorization check;
- imports no Guardian service, ORM, or vector store.

Per read path:

| Read path | Auth | Account scope |
|---|---|---|
| `/api/memory-vault/items` | Router-level `require_api_key` | `RequestUserScope.account_id` only; blank ⇒ 401, **no single-user fallback** |
| `/api/memory-vault/items/canonical/{id}` | Same | Account-bound session; unknown id ⇒ generic 404 with **no cross-account fallback lookup** |
| `/api/memory/{silo}` | Router-level `require_api_key` | `ephemeral` filtered by the authenticated principal; `midterm`/`longterm` pass the principal into the store query |
| `/personal-facts/candidates` | `require_api_key` + `get_current_user` | Handler bound to the current user |

**Single-user boundary.** Codexify currently runs a single-account deployment
(`_DEFAULT_SINGLE_USER_ID = "local"`). The account-scoping behaviour above is established from
**code inspection**, not from live multi-account testing. This adapter makes **no claim** of proven
multi-account isolation; it depends entirely on Guardian, which is the correct authority.

---

## 7. Structural reads vs. absent semantic recall

Every v1 tool is a **structural** read: list, get, or status. There is no relevance-ranked or
vector retrieval.

- `memory_list` reads a silo by name; it does not search within it.
- `vault_list` filters on `VaultListFilter` fields (`semantic_species`, `project_id`,
  `account_scoped_only`, `persona_subject_id`, `review_posture`, `lifecycle_posture`,
  `source_system`, `pinned`, `held`) plus bounded pagination — not on query relevance.
- `POST /api/retrieve`, `POST /codexify/search`, and `POST /chat` are **never** called. These paths
  are named in an explicit forbidden-path guard and asserted unreachable in
  `tests/mcp/test_no_unsafe_retrieval.py`.

### Data classification is preserved, not flattened

Canonical memory, ephemeral memory, and Personal Fact candidates remain distinguishable.
`list_fact_candidates` returns records verbatim, including `status` and `confidence`, and attaches a
note that a candidate is **not** an accepted or verified personal fact. The adapter never promotes,
reinterprets, or invents confidence.

---

## 8. Ephemeral memory caveat

The `ephemeral` silo is held in a **process-local list inside Guardian** and does not survive a
Guardian restart. The upstream route filters it by the authenticated principal, so the read is
account-scoped and permitted — but every `memory_list(ephemeral)` response carries an explicit
warning. Do not treat ephemeral entries as durable memory.

---

## 9. Supported-profile quarantine

Memory routers are `core_surface=False`. Under `CODEXIFY_BETA_CORE_ONLY=true`, or a
supported-profile manifest that marks them quarantined, `/api/memory/*` and
`/api/memory-vault/*` return 404.

This adapter treats quarantine as **authoritative runtime behaviour**. It reports the route as
unavailable (`not_found`, with a message naming `CODEXIFY_ENABLE_MEMORY_ROUTES` /
`CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES`) and never:
- enables those flags;
- bypasses `CODEXIFY_BETA_CORE_ONLY` or any profile policy;
- changes the supported profile.

A 404 is genuinely ambiguous (wrong port, wrong application, missing resource, or quarantine), so
the adapter reports the evidence it has rather than asserting a cause it cannot prove.

---

## 10. `memory_status` classifications

| `error.code` | Meaning |
|---|---|
| `guardian_unreachable` | Nothing accepted a connection at the configured origin |
| `guardian_timeout` | Guardian did not answer within the configured timeout |
| `wrong_upstream` | Origin answered but is not Guardian; **no credential was sent** |
| `auth_required` | Guardian rejected the API key (401) |
| `access_denied` | Guardian denied the authenticated account (403) |
| `not_found` | Resource missing, or the router is quarantined (404) |
| `conflict` | Guardian reported a conflict (409) |
| `upstream_rate_limited` | Guardian rate-limited the request (429) |
| `upstream_error` | Any other 4xx/5xx, or a non-JSON body |
| `invalid_configuration` | Startup refused; see §4 |
| `invalid_request` | Tool arguments failed validation |
| `unsupported_operation` | An operation outside the read-only v1 surface was attempted |

---

## 11. Protocol compatibility

Built against the official **MCP Python SDK v2** (`mcp>=2.3,<3`), using `MCPServer`. Both SDK v2
negotiation paths are exercised by `tests/mcp/test_stdio.py`:

- `mode="legacy"` — forces the classic `initialize` handshake (protocol `2025-11-25`);
- `mode="auto"` — probes `server/discover` and falls back to `initialize` (protocol `2026-07-28`).

Both must advertise the same five tools and be able to execute a tool call. No dual-version
compatibility shim is written; the package targets v2 only.

---

## 12. Privacy implications

Memory travels through **four distinct boundaries**, and it is worth being precise about which:

1. **Local Codexify persistence** — memory lives in Guardian's Postgres-backed store.
2. **Local Guardian → adapter transport** — loopback HTTP, authenticated, never leaving the host.
3. **Authorized disclosure to the MCP client** — the client receives tool results over stdio. This
   is an intentional, operator-authorized disclosure.
4. **The client's subsequent model-provider disclosure** — Claude Code, Cursor, or Codex may forward
   tool results to a remote model provider.

> **Do not claim memory never leaves the machine.** Steps 1–2 are local; step 4 may not be. This
> adapter performs no unsolicited network transmission of memory data, but it cannot control what a
> connected client does with the results it receives. Operators handling sensitive memory should
> account for their client's provider configuration.

Credentials are never placed in query parameters, tool descriptions, error payloads, or logs.

---

## 13. Failure and recovery

- Read failures become **structured tool results** (`ok: false` with an `error.code`). They do not
  raise into the transport, because under MCP v2 an exception escaping a handler surfaces as an
  opaque JSON-RPC error and would strip the client's tool surface.
- The stdio process stays alive through upstream failures. `memory_status` remains callable after an
  outage, which is the intended recovery entrypoint.
- One shared `httpx.AsyncClient` is opened for the process lifetime and closed on shutdown.
- Redirects are not followed (`follow_redirects=False`) and proxy environment variables are not
  inherited (`trust_env=False`), so a credential cannot be re-targeted by either mechanism.
- Transient transport errors on safe GETs may be retried at most once; 401/403/404 responses are
  never retried.

---

## 14. Validation and evidence limits

```bash
python -m pip install -e ".[mcp-memory]"
python -m pip check
python -m compileall -q guardian/mcp_memory
python -m pytest -v tests/mcp/
```

Evidence classes used in this adapter:

- **proven-test** — config validation, allowlisted paths, GET-only dispatch, forbidden-path
  reachability, import hygiene, origin gate (no key sent on failure), status→code mapping,
  argument validation, envelope shape, both SDK negotiation modes, subprocess entrypoint.
- **proven-code-path** — Guardian-side account scoping per read path (verified by source
  inspection of the mounted routers and services, not by live multi-account testing).
- **live-runtime** — only what was actually exercised against a running Guardian. See the
  implementation report for current status; this document makes no live claim on its own.

The adapter is **not** a live proof that Guardian's read surfaces behave correctly under production
data; it is a bounded reader over Guardian's existing contracts.

---

## 15. Recorded security follow-ups (NOT implemented here)

These are **separate work items**. Neither is repaired, worked around, or mitigated by the MCP
adapter, and no MCP workaround exists for either.

### Finding A — `POST /api/retrieve` authorization

`guardian/retrieve/api.py` declares a bare `APIRouter()` with no `require_api_key` dependency, and
`retrieve()` accepts a `user_id` from the request body. If confirmed against the effective mounted
application, any local process could read vector-retrieval results and choose the user scope.

**Follow-up:** verify effective mounted-app protection; if absent, add an auth dependency, derive
identity server-side, and drop the caller-supplied `user_id`.

### Finding B — vector user-scope propagation

`guardian/routes/codexify_router.py` calls `VectorStore.search(...)` without `user_id`, so the
search falls back to the deployment's single-user default. The *namespace* is caller-locked, but
the *user* filter is not derived from the authenticated principal.

**Follow-up:** pass `user_id=current_user` explicitly. This is out of v1 scope, and the adapter does
not call this endpoint at all.