# PFP-00 — Personal Fact Pipeline Baseline

- Campaign: Personal Fact Pipeline — parent issue
  <https://github.com/Resonant-Jones/Codexify/issues/889>
- Task: PFP-00 — Establish Personal Fact Pipeline Baseline
- Lane: Architecture-Impact
- Task kind: Diagnostic proof and documentation
- Date: 2026-10-23
- Status: **BASELINE ESTABLISHED — CAMPAIGN REMAINS OPEN / BASELINE PARTIALLY UNPROVEN**

> This is a baseline report. It contains **no** personal fact content, **no**
> source excerpts, **no** credentials, and **no** real user data. Every runtime
> observation used synthetic rows with synthetic keys written to a disposable
> PostgreSQL container that was destroyed after the run.
>
> This task implements **no** repair. It records what exists, what is proven
> broken, and what the single smallest next repair should be.

---

## 1. Inspected revision and working-tree state

```text
Exact inspected Git commit : 94b03e6029ddf457aeed9d7f3ead85f5cde3e954
Branch                     : main
HEAD == origin/main        : not checked in this task
```

Working-tree status at the moment of inspection (`git status --short`) showed
**only untracked paths**, all pre-existing and unrelated to this task:

```text
?? .scratch/acceptance-diag/…
?? .scratch/acceptance-full-baseline/
?? .scratch/acceptance-original-src/
?? .scratch/acceptance-red/
?? _tmp_83371_7102b62d293d70fad0a77086faf62bca
?? sqlite_probe_tmp.db-journal
```

No tracked file was modified by the inspection. No reset, clean, stash, or
staging of unrelated paths was performed. The only newly authored change
attributable to this task is this file.

### Environment used for inspection

```text
Interpreter   : /Volumes/Dev_SSD/Codexify-main/.venv/bin/python  (Python 3.12.13)
pytest        : 8.4.2
DB env vars   : DATABASE_URL unset, GUARDIAN_DATABASE_URL unset,
                TEST_DATABASE_URL unset
```

> Note for reproduction: the repository's `python` is not on `PATH`; the
> project virtualenv at `.venv/` must be used explicitly. The system
> `python3` is 3.14.4 and is not the project's interpreter.

---

## 2. Executive summary

The Personal Fact pipeline is **two pipelines that share one table**, not one
pipeline with two ingestion front-ends.

1. **Live-chat ingestion** (`guardian/fact_candidate_pipeline.py`) and
   **imported-history ingestion**
   (`backend/rag/personal_fact_extraction.py` + `backend/rag/chatgpt_migration.py`)
   both write candidates into the **legacy `personal_facts` table**. They
   differ in exactly one substantive way: the import path runs the guardrail
   classifier and persists a `guardrail_metadata` disposition; the live-chat
   path **never calls the classifier** and therefore writes candidates with
   `guardrail_metadata IS NULL` and no recorded `source_role`.

2. **`GET /personal-facts/candidates` is unreachable.** The route is declared
   and mounted, but an earlier-registered sibling route
   `GET /personal-facts/{fact_id}` shadows it in Starlette's first-match
   dispatch. Every request to the candidates path returns **HTTP 422
   `int_parsing`** before the handler body executes. The MCP adapter's
   `list_fact_candidates` tool targets exactly this path, so it can never
   succeed against a live Guardian.

3. **The pagination ceiling is a hard read ceiling, not a page size.** The
   handler fetches at most 200 rows and then slices in Python. `total` is the
   length of that fetched window, so it **under-reports** the real candidate
   count, and every candidate beyond the first 200 is unreachable through this
   endpoint. Reproduced live: 253 candidate rows for one principal →
   `total` reported **200**; `offset=200` returned **0** rows.

4. **The connector checkpoint failure is independent of Guardian availability.**
   Proven by direct observation in this session: the working-tree checkpoint
   succeeded (every git, pytest, and Python command executed) while **no
   Guardian instance was running at all**. The two conditions are unrelated
   axes.

---

## 3. Pipeline map — source to candidate

### 3.1 Stage ownership table

| Stage | Owning code location | Live chat | Imported history |
|---|---|---|---|
| Extraction | `guardian/fact_candidate_pipeline.py:258` `_extract_candidates_from_text` (inlined regex mirror of `backend/rag/personal_fact_extraction.py:70` `_FACT_RULES`) | yes | — |
| Extraction | `backend/rag/personal_fact_extraction.py:348` `extract_personal_fact_candidates`; `:395` `extract_personal_fact_candidates_third_person` (ChatGPT `model_editable_context`) | — | yes |
| Ingestion seam | `guardian/routes/chat.py:110-112` imports `process_user_message` as `_process_fact_candidates`; invoked after user-message persistence | yes | — |
| Import seam | `backend/rag/chatgpt_migration.py:432-464` `_ingest_canonical_messages` → `persist_personal_fact_candidates` | — | yes |
| Source-role classification | `guardian/personal_facts/guardrail_policy.py:105` `classify_personal_fact_candidate`, called from `backend/rag/chatgpt_migration.py:404` `_classify_import_candidates` | **not called** | yes |
| Guardrail classification | same classifier; disposition attached at `backend/rag/chatgpt_migration.py:422-425`; serialized at `backend/rag/personal_fact_extraction.py:292-310` `_extract_guardrail_metadata` | **not called** | yes |
| Guardrail metadata persistence | `backend/rag/personal_fact_extraction.py:591-600` (`create_fact(..., guardrail_metadata=guardrail_meta)`) | **no argument passed** — `guardian/fact_candidate_pipeline.py:453-459` | yes |
| Retroactive classification (operator-run) | `guardian/personal_facts/guardrail_backfill.py:190` → `scripts/personal_facts/backfill_guardrail_metadata.py` (applies only with `--apply`) | opt-in, not automatic | opt-in |
| Deduplication | live: `guardian/fact_candidate_pipeline.py:416-436` (key-only, read-then-write) / import: `backend/rag/personal_fact_extraction.py:436-460` `_find_existing_fact` (key-only) | key only | key only |
| Evidence persistence | live: `guardian/fact_candidate_pipeline.py:473-503` / import: `backend/rag/personal_fact_extraction.py:644-671` | yes, failure swallowed | yes, failure swallowed |
| Import provenance metadata | `backend/rag/personal_fact_extraction.py:313-345` `_build_evidence_meta` (`source_role`, `source_thread_id`, `source_message_export_id`, `import_source`, `import_profile`, `turn_index`, `source_created_at`) | — | yes |
| Live provenance metadata | `guardian/fact_candidate_pipeline.py:228-252` `_build_evidence_meta` (`source`, `source_type`, `thread_id`, `source_message_id`, `detector_rule`) — **no `source_role`** | yes | — |
| Import replay/idempotency guard | `backend/rag/personal_fact_extraction.py:463-494` `_existing_evidence_matches` (skips duplicate evidence for the same import message) | **none** | yes |
| Candidate storage authority | `personal_facts` table, `guardian/db/models.py:2523-2575` | yes | yes |
| Storage uniqueness | `ix_personal_facts_active_key` — created by `backend/migrations/versions/a1b2c3d4e5f6_add_temporal_and_personal_facts.py:171-177`; **not declared in the ORM model** (`guardian/db/models.py:2564-2574`) | — | — |

### 3.2 The two ingestion paths are not equivalent

`classify_personal_fact_candidate` has exactly two production call sites:

```text
backend/rag/chatgpt_migration.py:404          (imported history)
guardian/personal_facts/guardrail_backfill.py:190   (operator-run backfill)
```

There is **no call site in `guardian/fact_candidate_pipeline.py`** and none in
`guardian/routes/chat.py`. A candidate created by live chat therefore carries:

- `guardrail_metadata = NULL`
- an evidence row whose `evidence_meta` has **no `source_role`**
- no `guardrail_status`, no `reason_code`

The Personal Facts Guardrails Contract requires a resolvable
`guardrail_status` and `reason_code` for every reviewable candidate
(`docs/architecture/personal-facts-guardrails-contract.md:182-196`) and
`source_role` "when available" plus `source_type`/`source_excerpt`/`confidence`
as minimum evidence (`:282-291`). For live chat the role **is** known — it is
the account principal's own message — but it is not recorded.

The import path additionally differs in that it will **not** touch a
non-candidate fact (`backend/rag/personal_fact_extraction.py:579-584`), while
the live path dedupes across *all* active facts of any status
(`guardian/fact_candidate_pipeline.py:414-425`).

---

## 4. Pipeline map — candidate to review

### 4.1 Route mounting and exposure flags

| Concern | Owning code location | Value |
|---|---|---|
| Router prefix | `guardian/routes/personal_facts.py:202` | `/personal-facts` |
| Mount | `guardian/guardian_api.py:1052-1054` `_include_personal_facts_router` | mounted at **both** `/personal-facts` and `/api/personal-facts` |
| Feature flag | `guardian/guardian_api.py:1232-1235` | `CODEXIFY_ENABLE_PERSONAL_FACTS_ROUTES`, `default_enabled=True` (from `_include_router` signature, `guardian/guardian_api.py:257`) |
| Beta-core quarantine | `guardian/guardian_api.py:273-279` | `core_surface=False` (default, `guardian/guardian_api.py:258`) ⇒ `CODEXIFY_BETA_CORE_ONLY=true` **quarantines** the whole personal-facts router |
| Supported-profile quarantine | `guardian/guardian_api.py:260-272` | profile manifest `route_status(label)` |

### 4.2 Authorization

```text
route dependency : guardian/routes/personal_facts.py:18
                   require_account_session as require_api_key
resolver         : guardian/core/dependencies.py:1065 require_account_session
                   → :1012 verify_account_session
                     → local mode  : :690 verify_api_key (static API key)
                     → remote mode : account session token only
principal        : guardian/routes/personal_facts.py:196 get_current_user
                   → guardian/core/dependencies.py:1182 get_account_user_id
                     → :1173 _account_scope_gate
                     → :388  get_request_user_id
```

Principal resolution, in the order actually evaluated
(`guardian/core/dependencies.py:388-440`):

| Condition | Resolved principal | Class |
|---|---|---|
| private preview enabled | `require_preview_principal(request).email` | account principal |
| valid session token present | `resolve_session_user_id(...)` | account principal |
| `CODEXIFY_MULTI_USER_ENABLED=true` | authenticated JWT subject (401 if absent) | account principal |
| `DEBUG`/`LOCAL_DEV` enabled | `X-User-Id` header | **caller-controlled — forbidden as an account substitute** |
| default single-user deployment | `get_single_user_id()` → `CODEXIFY_SINGLE_USER_ID` or `"local"` | **local/operator principal** |

The default single-user principal is the literal string `"local"`
(`guardian/core/dependencies.py:262-267`, `_DEFAULT_SINGLE_USER_ID`).

### 4.3 Item-level account isolation

`GET /personal-facts/{fact_id}`, `PATCH`, `/{fact_id}/confirm`,
`/{fact_id}/dispute`, `/candidates/{fact_id}/approve`, `/candidates/{fact_id}/reject`
all resolve the fact and then compare ownership
(`guardian/routes/personal_facts.py:320-321`, `:334-335`, `:425-426`), returning
a generic `404 fact not found` on mismatch. This is enforced in the
application layer, not by the query.

### 4.4 Legacy Personal Facts compatibility vs. UMS candidate authority

These are **not** competing stores — the legacy table is the durable
authority and the UMS species is a **read-only projection of it**.

```text
legacy source row      = personal_facts row (durable authority)
compatibility envelope = canonical read projection (semantic read object only)
```

- `guardian/core/memory_compatibility.py:117-121` — verified facts project to
  envelope species `verified_personal_fact`.
- `guardian/core/memory_compatibility.py:123-127` — candidate rows project to
  envelope species `candidate_unreviewed_fact`.
- `guardian/core/memory_compatibility.py:141-159` — the canonical candidate
  predicate is `status IN ('candidate','disputed','archived') OR is_active = FALSE`.
- `guardian/core/memory_compatibility.py:35-53` — candidate/unreviewed rows are
  explicitly **out of scope** for the verified-fact reader; the reader returns
  `None` for them, exactly as for not-found.
- `guardian/services/memory_vault_read.py:813-818` — the Vault maps the
  candidate species to `REVIEW_POSTURE_PENDING` and the verified species to
  `REVIEW_POSTURE_APPROVED` / `LIFECYCLE_POSTURE_ACTIVE`.

`candidate_unreviewed_fact` is therefore a **projection label**, not an
independent pre-promotion store. Per `docs/Campaign/unified-memory-store/README.md:118`,
UMS-03G (candidate personal-fact compatibility) is CLOSED; the Campaign README
also records `CURRENT CANONICAL IMPORTED-MEMORY WRITER: NONE`, and the only
canonical-memory writers are direct Vault creation and restore.

### 4.5 MCP adapter authentication restrictions

`guardian/mcp_memory/config.py` fails closed on every rule:

| Rule | Location | Effect |
|---|---|---|
| `CODEXIFY_MCP_BASE_URL` required, no default | `:89-97` | no implicit port default (port 8000 on this host is Whoosh'd, not Guardian) |
| `http` scheme only, bare origin, no credentials in URL | `:102-119` | adapter does not terminate TLS |
| Loopback destination only | `:124-129` | credentials never leave the host |
| `CODEXIFY_MCP_API_KEY` / `GUARDIAN_API_KEY` required | `:133-140` | no default credential |
| `CODEXIFY_MCP_USER_ID` **rejected when populated** | `:161-169` | no identity override is possible |
| `GUARDIAN_AUTH_MODE` in {remote, cloud, hosted, public, prod, production} → refused | `:45-47`, `:172-181` | v1 supports local API-key auth **only** |
| `GUARDIAN_EXPOSURE_MODE=public_allowlist` → refused | `:48`, `:175` | same |

Consequence: the adapter can only ever read the **local/operator single-user
principal**, never a remote account session. There is no configuration of the
v1 adapter that produces an account-scoped read against a hosted account.

Status mapping for upstream errors is `guardian/mcp_memory/client.py:102-134`;
401 → `AUTH_REQUIRED`, 403 → `ACCESS_DENIED`, 404 → `NOT_FOUND`, and **any
other non-2xx (including 422) → `UPSTREAM_ERROR` with the literal message
`"Guardian returned HTTP 422 for /personal-facts/candidates."`**.

### 4.6 Pagination, counting, and ordering

```text
guardian/routes/personal_facts.py:680   limit = max(1, min(limit, 200))
guardian/routes/personal_facts.py:682-687 facts = db.list_facts(current_user,
                                            status=status, active_only=True,
                                            limit=200)          # <-- fixed 200
guardian/routes/personal_facts.py:689-706 thread_id filter (N+1 evidence reads)
guardian/routes/personal_facts.py:708   total = len(facts)      # window length
guardian/routes/personal_facts.py:709   page = facts[offset : offset + limit]
```

`guardian/core/pgdb.py:2155-2169` (`list_facts`) and the mirrored SQLite
implementation `guardian/core/db.py` both:

- filter by `user_id` at the query (`filter_by(user_id=user_id)`),
- accept **no `offset` parameter**,
- order by `PersonalFact.updated_at.desc()` with **no secondary sort key**,
- apply `LIMIT` in SQL only.

`guardian/core/pgdb.py:2171-2192` (`create_fact`) accepts
`guardrail_metadata: dict | None = None` and `guardian/core/pgdb.py:2194-2199`
(`get_fact`) fetches by `id` **without** a `user_id` predicate — the route
compensates with the ownership check described in §4.3.

---

## 5. Verified defects

Every item in this section was reproduced in this session against a real
PostgreSQL instance using the repository's own Alembic-migrated schema and the
repository's own route, service, and pipeline modules.

### V1 — `GET /personal-facts/candidates` is unreachable (HTTP 422)

**Status: VERIFIED DEFECT (integration-level, real PostgreSQL + real router)**

`guardian/routes/personal_facts.py:313` registers `GET /personal-facts/{fact_id}`;
`guardian/routes/personal_facts.py:660` registers `GET /personal-facts/candidates`.
Starlette dispatches on first path match, so the literal segment `candidates`
matches the `{fact_id}` pattern, and FastAPI then fails to coerce `"candidates"`
to `int`.

Observed route registration order (real router, real app):

```text
 6 /personal-facts/{fact_id}          {'GET'}
15 /personal-facts/candidates         {'GET'}
16 /personal-facts/candidates/debug/recent {'GET'}
```

Observed responses:

```text
GET /personal-facts/candidates                       -> 422
    {"detail":[{"type":"int_parsing","loc":["path","fact_id"],
                "msg":"Input should be a valid integer, unable to parse string as an integer",
                "input":"candidates"}]}

GET /personal-facts/candidates?offset=200&limit=50   -> 422   (identical body)

GET /personal-facts/candidates/debug/recent?limit=20 -> 200   (different path, not shadowed)
```

Consequences:

- The MCP adapter's `list_fact_candidates` tool
  (`guardian/mcp_memory/tools/read.py:127-160`, path
  `guardian/mcp_memory/client.py:54`) **can never succeed** against a live
  Guardian. It surfaces as `UPSTREAM_ERROR: Guardian returned HTTP 422 for
  /personal-facts/candidates.`
- Any operator or automation that follows the documented endpoint
  (`docs/architecture/mcp-memory-adapter-v1.md:36`) receives 422.

### V2 — The 200-row ceiling makes rows unreachable and `total` under-report

**Status: VERIFIED DEFECT (integration-level)**

The fetch is capped at 200 rows; `total` is the length of that window; the
offset is applied in Python to the window. Reproduced with 253 candidate rows
belonging to one principal:

```text
requested_offset  requested_limit  returned_count  reported_total
  0                       50               50            200
 50                       50               50            200
199                       50                1            200
200                       50                0            200
400                       50                0            200
```

- `reported_total` is **200** while the principal actually holds **253**
  candidate rows — a 53-row **under-report**.
- `offset >= 200` returns an empty page **even though 53 more candidates
  exist**. Candidates at ranks 201–253 are unreachable through this endpoint.
- The `thread_id` filter (§4.6, `:689-706`) is applied to the same 200-row
  window *before* slicing, so thread-scoped pagination is truncated identically
  and additionally issues one `list_fact_evidence` call per fact (N+1).

Contrast with the correct pattern already present in the Vault read service,
which over-fetches to `offset + limit` and slices afterwards
(`guardian/services/memory_vault_read.py:287-416`).

### V3 — `list_facts` cannot express an offset, and its ordering is not stable

**Status: VERIFIED DEFECT (code-path + integration-level)**

`guardian/core/pgdb.py:2155-2169` exposes `limit` but no `offset`, and orders
by `updated_at DESC` with no tiebreaker. Two consequences:

1. Offset pagination is impossible at the data layer, which is why the route
   had to slice in Python (V2).
2. The order is **not deterministic across equal `updated_at` values**. Any
   candidate whose `updated_at` changes between two page requests shifts
   position, so pages can duplicate or skip rows. Observed ordering was
   monotonically non-increasing, but that is a property of the seeded rows,
   not a guaranteed tiebreak.

### V4 — Live-chat candidates carry no guardrail disposition and no `source_role`

**Status: VERIFIED DEFECT (integration-level)**

`guardian/fact_candidate_pipeline.py:453-459` calls `create_fact` with
`status="candidate"` and `confidence` only — no `guardrail_metadata`
argument — and `_build_evidence_meta` (`:238-252`) omits `source_role`.

Measured on the disposable instance after driving the real
`process_user_message` against the real `PgDB`:

```text
candidate guardrail_metadata presence
  sampled: 5
  with_guardrail_metadata: 0
```

The import path writes the disposition
(`backend/rag/personal_fact_extraction.py:591-600`). The live path has no
classifier call at all (§3.2). The result is that the **majority** of
candidates in a live deployment are unclassified, while the Guardrails
Contract requires a resolvable `guardrail_status` and `reason_code` for every
reviewable candidate, and the live-chat evidence row omits a `source_role`
that is known at the point of extraction.

### V5 — Key-only deduplication plus a partial unique index makes a changed proposition unrepresentable

**Status: VERIFIED DEFECT (integration-level)**

Three independent mechanisms all key on `key` alone:

- live dedup compares `key` only (`guardian/fact_candidate_pipeline.py:419-425`),
- import dedup compares `key` only (`backend/rag/personal_fact_extraction.py:454-459`),
- the database enforces one active fact per `(user_id, key)`
  (`ix_personal_facts_active_key`, partial on `is_active = TRUE`).

Observed:

```text
same key, different value, same principal -> rejected_by_unique_index (IntegrityError)
```

A user who states a changed fact ("I live in Portland" → later "I live in
Seattle") cannot produce a new candidate while the earlier one is active: the
live path's dedup skips it as a duplicate, and a direct write is refused by
the unique index. There is no candidate-vs-candidate contradiction model and
no proposition identity beyond the key. The Guardrails Contract's
`contradiction_possible` fixture class (`personal-facts-guardrails-contract.md:353`)
has no implementation.

### V6 — `list_facts` is called once per candidate during ingestion

**Status: VERIFIED DEFECT (integration-level, measured)**

`guardian/fact_candidate_pipeline.py:418` calls
`list_facts(user_id, active_only=True, limit=1000)` **inside the per-candidate
loop**. Measured on the disposable instance with 253 active facts for the
principal:

```text
candidates_found: 3   candidates_created: 3
list_facts_calls: 3    total_rows_scanned: 753
```

Three candidates from a single message cost three full listings and 753 rows
scanned. The cost scales as *candidates × active facts*, with no upper bound
on `limit` in the import path, which uses `limit=50000`
(`backend/rag/personal_fact_extraction.py:448`) and can call `_find_existing_fact`
**twice** per candidate on the create-failure path (`:576` and `:608`).

### V7 — A failed evidence write leaves a candidate with no evidence

**Status: VERIFIED DEFECT (code-path)**

Both paths create the fact first and then attempt the evidence write inside a
`try/except` that logs and continues:

- live: `guardian/fact_candidate_pipeline.py:485-503`
- import: `backend/rag/personal_fact_extraction.py:654-671`

No rollback occurs, so a candidate can exist with zero evidence rows. The
Guardrails Contract treats missing evidence as a first-class disposition
(`missing_evidence` → quarantine or promotion_blocked,
`personal-facts-guardrails-contract.md:247`, `:355`), but nothing classifies
it at creation time, so the candidate reaches review as an ordinary
unclassified candidate.

### V8 — The ORM model does not declare the unique index the live schema enforces

**Status: VERIFIED DEFECT (schema-level, integration-level)**

Live schema at Alembic head `f0d7c4b2a198`:

```text
ix_personal_facts_active_key => CREATE UNIQUE INDEX ... ON public.personal_facts
                                 USING btree (user_id, key) WHERE (is_active = true)
ix_personal_facts_user_status => CREATE INDEX ... (user_id, status, is_active)
personal_facts_pkey            => PRIMARY KEY (id)
```

ORM model `guardian/db/models.py:2564-2574` declares **only**
`ix_personal_facts_user_status`. The unique index is created solely by
`backend/migrations/versions/a1b2c3d4e5f6_add_temporal_and_personal_facts.py:171-177`.

Consequence: any deployment or test bootstrapped from
`Base.metadata.create_all()` — rather than from the migration chain — has
**no unique constraint**, and therefore neither the dedup guarantee nor the
duplicate-row protection that the migrated schema provides. The schema
authority and the model authority disagree.

### V9 — Fail-open authentication fallback in the personal-facts module

**Status: PROBABLE DEFECT (code-path only; dormant in the observed runtime)**

`guardian/routes/personal_facts.py:13-30` wraps the security-critical import
in `except Exception:` and substitutes:

```python
def require_api_key(api_key: str = "") -> str:  # no-op; api_key becomes a QUERY param
    return api_key

def get_request_user_id() -> str:
    return "local"
```

If `guardian.core.dependencies` fails to import for any reason, every
personal-facts route becomes **unauthenticated** and bound to the constant
`"local"` principal, with no error and no log.

Verified **not** active in the observed runtime: the bound objects were
`guardian.core.dependencies.require_account_session` and
`guardian.core.dependencies.get_account_user_id`. The defect is the existence
of the fail-open branch, not its activation.

---

## 6. Probable defects and unverified concerns

### 6.1 Probable defects (code-path supported, not separately reproduced)

- **The "sensitive candidate" flag is never persisted.**
  `guardian/fact_candidate_pipeline.py:404-412` increments
  `candidates_skipped_sensitive` and logs *"we still store for review, just
  with a flag"* — but no flag is written to the fact or its evidence metadata.
  The comment describes behavior the code does not implement. The Guardrails
  Contract has a `sensitive_identity_like_claim` disposition
  (`personal-facts-guardrails-contract.md:246`).
- **Live-chat ingestion has no replay or concurrency idempotency guard.**
  The import path skips duplicate evidence for the same import message
  (`backend/rag/personal_fact_extraction.py:463-494`); the live path has no
  equivalent. Its protection against duplicate creation is the database's
  unique index (V5/V8), which turns a concurrent duplicate into a logged
  `failures += 1` rather than an idempotent no-op
  (`guardian/fact_candidate_pipeline.py:461-470`).
- **`list_facts` has no total-count query.** Every caller that needs a count
  infers it from a bounded fetch, which is the direct cause of V2.

### 6.2 Unverified concerns

- **Multi-account isolation is unproven at runtime.** The MCP adapter's own
  design document states that account-scoping behaviour is *"established from
  **code inspection**, not from live multi-account testing"*
  (`docs/architecture/mcp-memory-adapter-v1.md:156-159`), and that the adapter
  *"makes **no claim** of proven multi-account isolation"*. No live
  multi-account proof exists in this repository.
- **The `/api/personal-facts/candidates` mount was not separately probed.** It
  is the same router with the same registration order, so V1 applies with
  certainty from code, but the probe was run against the unprefixed mount.
- **Behaviour of `list_facts(active_only=False)` and of the
  `status=None` / `status="verified"` branches of `list_fact_candidates` was
  not exercised.**
- **The MCP adapter's origin gate was not exercised.** `verify_origin`
  (`guardian/mcp_memory/client.py:295`) probes `/health` on the configured
  loopback origin before any request is sent, so a real deployment may fail
  at that gate before the 422 in V1 is reached. The order of failure was not
  observed in a live adapter process.
- **Whether the deployed Guardian in any real environment has the personal-facts
  router mounted at all** is deployment state that this task cannot observe;
  `CODEXIFY_ENABLE_PERSONAL_FACTS_ROUTES`, `CODEXIFY_BETA_CORE_ONLY`, and the
  supported-profile manifest can each quarantine it.

---

## 7. Historical proof and prior receipts

| Artifact | What it proves | What it does **not** prove |
|---|---|---|
| `docs/architecture/proofs/runtime/2026-09-27-generic-auth-consumer-classification.md:122` | The personal-facts router is mounted/flagged, is classified `account_purpose_strict`, uses `get_current_user,require_api_key`, and declares `GET /personal-facts/candidates → list_fact_candidates` | It is a **route inventory**. It asserts declaration and dependency names; it does not assert dispatch reachability. V1 shows the declared route is shadowed. |
| `docs/architecture/proofs/runtime/2026-09-10-ums04b-postgres-test-authority-proof.md` | The established disposable-PostgreSQL qualification pattern (dedicated host-local cluster, `TEST_DATABASE_URL`, non-superuser role with `CREATEDB`) | Not a Personal-Fact-specific proof. This task reproduced the *pattern* on a fresh disposable container. |
| `docs/Campaign/unified-memory-store/README.md:118` | UMS-03G (candidate personal-fact compatibility) is CLOSED | That a *separate* candidate authority exists. UMS-03G delivered a compatibility projection over the legacy table (§4.4). |
| `docs/architecture/mcp-memory-adapter-v1.md:151-154` | The intended per-path auth and account-scope table for the adapter | That the `/personal-facts/candidates` row is accurate — V1 shows the handler it describes never executes. |

---

## 8. Documentation discrepancies (recorded, not corrected)

Per the task's Documentation Follow-Through clause, these are recorded here
only. **No canonical documentation was updated by this task.**

1. **`docs/architecture/mcp-memory-adapter-v1.md:154`** states that
   `/personal-facts/candidates` is guarded by `require_api_key` +
   `get_current_user` and is *"Handler bound to the current user"*. The handler
   never executes; the request is rejected by the sibling `{fact_id}` route
   with HTTP 422 before any personal-facts authorization runs.

2. **`docs/architecture/mcp-memory-adapter-v1.md:36`** advertises
   `list_fact_candidates` → `GET /personal-facts/candidates` as a working
   read path. Against a live Guardian that path returns 422 (V1).

3. **`guardian/db/models.py:2564-2574`** does not declare
   `ix_personal_facts_active_key`, which the migration chain creates
   (`backend/migrations/versions/a1b2c3d4e5f6_add_temporal_and_personal_facts.py:171-177`).
   The ORM model and the live schema disagree about the uniqueness guarantee
   on `(user_id, key)` (V8).

4. **`docs/architecture/personal-facts-guardrails-contract.md:182-196` and
   `:282-291`** require a resolvable `guardrail_status`, `reason_code`, and
   `source_role` for reviewable candidates. The live-chat ingestion path
   satisfies none of these (V4).

5. **ADR-084's amended target versus the current implementation — recorded,
   and explicitly *not* a violation.** ADR-084 states that *"No `personal_facts`
   row is required for candidate review or quarantine"* and that the single
   UMS `candidate_unreviewed_fact` record owns pre-promotion authority. The
   implementation still writes every pre-promotion candidate into
   `personal_facts` and reads `candidate_unreviewed_fact` only as a
   compatibility projection. ADR-084 sanctions exactly this transitional
   arrangement: *"Legacy pre-promotion rows continue to be read through the
   existing compatibility path until a separately authorized, verified
   migration reconciles them into the UMS candidate authority"*, and it
   records that *"the currently installed UMS schema, compatibility readers,
   and Personal Facts runtime behavior have not been migrated to this amended
   target."* **This is a documented transitional gap, not an ADR conflict, and
   no runtime semantics were changed.**

---

## 9. Proof classification

| Evidence | Class | Command / method |
|---|---|---|
| Source-level reading of 19 pipeline, route, service, adapter, and model locations | **Code-path inspection** | — |
| `tests/mcp/test_client.py`, `test_config.py`, `test_tools_read.py`, `tests/test_fact_candidate_pipeline.py` | **Mocked unit tests** (no DB, no HTTP server) | see §10 |
| Route registration order | **Integration-level**, real router in-process | `FastAPI()` + `include_router(pf.router)` |
| V1 (422 on `/personal-facts/candidates`) | **Integration-level** — real router, real FastAPI dispatch, real PostgreSQL schema | HTTP via `TestClient` |
| V2 (pagination ceiling, `total` under-report) | **Integration-level** — real `PgDB` against a migrated disposable PostgreSQL, synthetic rows | handler-level call + HTTP |
| V3 (no `offset`; ordering) | **Code-path + integration-level** | `guardian/core/pgdb.py:2155-2169` + observed ordering |
| V4 (no guardrail metadata / `source_role`) | **Integration-level** — real `process_user_message` + real `PgDB` | measured `guardrail_metadata IS NULL` |
| V5 (key-only dedup + unique index) | **Integration-level** | real `IntegrityError` from a real unique index |
| V6 (`list_facts` amplification) | **Integration-level** — instrumented real pipeline | 3 calls / 753 rows scanned |
| V7 (swallowed evidence failure) | **Code-path only** | `guardian/fact_candidate_pipeline.py:485-503`, `backend/rag/personal_fact_extraction.py:654-671` |
| V8 (ORM vs. schema divergence) | **Integration-level** — `pg_indexes` read from the migrated database | `information_schema` / `pg_indexes` query |
| V9 (fail-open fallback) | **Code-path only**; **verified dormant** in the observed runtime | module-binding introspection |
| Principal resolution under the local lane | **Integration-level** — real dependency functions | `get_request_user_id()` → `"local"` |
| Account isolation across two principals | **Integration-level** — two synthetic principals, scoped reads, cross-account item read → 404 | see §10 |
| Live multi-account isolation | **NOT PROVEN** | — |
| Deployed-runtime behaviour of a real Guardian | **NOT PROVEN** — no Guardian instance was running | §11 |

**No passing unit test was treated as deployed-runtime proof.** No claim in
this report depends on a mocked test.

---

## 10. Validation commands and outcomes

### 10.1 Required source-level validation

```bash
cd /Volumes/Dev_SSD/Codexify-main
PYTHONPATH="$PWD" .venv/bin/pytest -v \
  tests/mcp/test_client.py tests/mcp/test_config.py \
  tests/mcp/test_tools_read.py tests/test_fact_candidate_pipeline.py
```

```text
platform darwin -- Python 3.12.13, pytest-8.4.2, pluggy-1.6.0
rootdir: /Volumes/Dev_SSD/Codexify-main
configfile: pytest.ini
collected 119 items

tests/mcp/test_client.py ............................................... [ 39%]
..                                                                       [ 41%]
tests/mcp/test_config.py ................................                [ 68%]
tests/mcp/test_tools_read.py .................                           [ 82%]
tests/test_fact_candidate_pipeline.py .....................              [100%]

============================= 119 passed in 0.34s ==============================
EXIT_CODE=0
```

The same command was also run with `DATABASE_URL` and `GUARDIAN_DATABASE_URL`
unset (`env -u DATABASE_URL -u GUARDIAN_DATABASE_URL … -o addopts="" -v`):
identical result, **119 passed, exit 0**. Neither variable was set in the
environment at any point during this task, so the two runs are equivalent.

**Coverage note:** these 119 tests never exercise the real route. The MCP
tests use a mocked `httpx` transport whose `/personal-facts/candidates`
handler returns a canned `200` (`tests/mcp/conftest.py:87-89`); the pipeline
tests use a `MagicMock` DB (`tests/test_fact_candidate_pipeline.py:16-30`).
The only other reference to the route is a **route-inventory** assertion in
`tests/identity/test_account_purpose_strict_migration.py:225`, which checks
that the route is declared with the expected dependency names — not that it
dispatches. **This is the coverage gap that let V1 ship.**

### 10.2 Disposable-PostgreSQL qualification

```bash
docker run -d --name pfp00_baseline_pg \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=pfp00 -p 127.0.0.1:55477:5432 postgres:15
# -> PostgreSQL 15.19 (Debian 15.19-1.pgdg13+2)

DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:55477/pfp00" \
  PYTHONPATH="$PWD" .venv/bin/alembic -c backend/alembic.ini upgrade head
# -> EXIT_CODE=0, alembic_version = f0d7c4b2a198, 135 public tables
```

Observations were produced by two read-only probe scripts kept **outside** the
repository (`/tmp/pfp00_probe.py`, `/tmp/pfp00_identity_probe.py`); no
repository file was created or modified by them.

```text
seeded_rows: 253   (250 for principal A, 3 for principal B — synthetic keys only)

GET /personal-facts/candidates                        -> 422 int_parsing (fact_id)
GET /personal-facts/candidates?offset=200&limit=50    -> 422 int_parsing (fact_id)
GET /personal-facts/candidates/debug/recent?limit=20  -> 200

handler offset=0    limit=50 -> 50 rows, total=200
handler offset=50   limit=50 -> 50 rows, total=200
handler offset=199  limit=50 ->  1 row,  total=200
handler offset=200  limit=50 ->  0 rows, total=200
handler offset=400  limit=50 ->  0 rows, total=200
handler principal B         ->  3 rows, total=3, all owned by B
GET /personal-facts/{id_owned_by_A} as B -> 404 "fact not found"

db.list_facts ordering: rows_returned=200, non_increasing=true,
                     distinct_user_ids=[principal A]

live-chat ingestion: candidates_found=3, candidates_created=3,
                     list_facts_calls=3, total_rows_scanned=753,
                     active_facts_for_principal=253
same key + different value -> rejected_by_unique_index (IntegrityError)
candidate guardrail_metadata: sampled=5, with_guardrail_metadata=0
```

Identity-scope probe:

```text
resolved principal (no session, local auth mode)
  resolved_current_user         : "local"
  multi_user_enabled            : false
  auth_mode / exposure_mode     : "local" / "local_safe"
  allow_user_header_override    : false

HTTP debug/recent, default local principal      -> 200, count 0
HTTP debug/recent, principal A configured        -> 200, count 20, distinct_user_ids=[A]
HTTP debug/recent, principal B configured        -> 200, count 3,  distinct_user_ids=[B]
HTTP debug/recent with X-User-Id override, no DEBUG/LOCAL_DEV
                                                -> 200, count 0 (override ignored)
```

### 10.3 Repository hygiene validation

```bash
git diff --check
test -f docs/Campaign/personal-fact-pipeline-baseline.md
git status --short
```

Results are recorded in §13.

### 10.4 What was deliberately NOT done

- No Guardian instance was started, deployed, or configured.
- No production, staging, or shared database was contacted. Every write went
  to a container created for this task and destroyed afterwards.
- No candidate was promoted, approved, rejected, archived, or deleted.
- No migration was authored or applied to any non-disposable database.
- No personal fact content, excerpt, or credential was read, written, or
  reproduced.
- No `X-User-Id` override was used to impersonate an account; the override was
  observed to be *refused*, which is itself the isolation evidence.

---

## 11. Authorized live read access — blocking condition

**No live account-scoped candidate read was performed, and none was
attempted through an unauthorized path.**

### 11.1 Connector checkpoint failure vs. Guardian availability

**The two are independent.** The connector's working-tree checkpoint is a
**command-execution precondition of the harness**, not a Guardian runtime
precondition. Evidence from this session:

| Observation | Result |
|---|---|
| Working-tree checkpoint | **Succeeded** — every `git`, `pytest`, `docker`, and Python command executed without a checkpoint error |
| Guardian availability | **Absent** — nothing was listening on the Guardian port; `GET http://127.0.0.1:8010/health` returned no response; the only service on `127.0.0.1:8000` is **Whoosh'd** (`{"ok":true,"runner":"whooshd",...}`, 19 OpenAPI paths, no personal-facts or memory paths) |
| Conclusion | The command path works with Guardian entirely absent ⇒ the prior checkpoint failure was **not** caused by, and did not imply, Guardian unavailability |

For completeness, `VaultNode` in this repository is **not** the command
gateway and **not** Guardian: it is the local model-runtime container host
(`guardian/core/local_runtime_presets.py:20`, `:33`, `:126` — `VAULTNODE_BASE_URL`
points at the model server, e.g. Whoosh'd on port 8000). ADR-041 governs
"VaultNode Canonical Machine and Audit Authority" as an architecture concept.
The command gateway described in the prior attempt is therefore a
**harness-side** mechanism external to this repository, and its failure is an
independent axis from Guardian runtime state.

**Consequence for PFP-00:** the checkpoint failure is *not* a blocker for this
task. It is recorded here as resolved-by-demonstration. A checkpoint failure
in a future task would likewise not be evidence about Guardian availability,
and vice versa.

### 11.2 Why no account-scoped live read was performed

An authenticated **account** principal requires one of:

| Principal class | Requirement | Present in this environment? |
|---|---|---|
| Private preview | approved email bound to a signed session | no |
| Session token | verified account session (`resolve_session_user_id`) | no |
| Multi-user mode | `CODEXIFY_MULTI_USER_ENABLED=true` **plus** an authenticated JWT subject | `multi_user_enabled: false`; no subject |

The MCP adapter cannot supply one: it refuses remote and session auth modes
outright (`guardian/mcp_memory/config.py:172-181`) and rejects any identity
override (`:161-169`), so it is structurally confined to the local API-key lane
and therefore to the local/operator principal.

**The only principal reachable over HTTP here is the local/operator
single-user principal** — `"local"` by default, or whatever
`CODEXIFY_SINGLE_USER_ID` names. Using it as a stand-in for an authenticated
account principal is exactly what this task forbids, so it was not done.

### 11.3 Recorded blocking condition

```text
BLOCKING CONDITION (recorded, not circumvented)

An authenticated account principal is not available in this environment:
  - no Guardian instance is running on the expected loopback origin
  - no account session token, no approved private-preview principal,
    and multi-user mode is disabled
  - the MCP adapter is restricted to the local API-key lane by design
    (guardian/mcp_memory/config.py:172-181) and cannot address a
    remote account session
  - the UMS-04B disposable PostgreSQL authority host-local cluster
    (127.0.0.1:55432) is not running; the disposable containers that are
    running belong to unrelated harnesses and were not reused

Consequently:
  - NO live account-scoped candidate read was performed
  - NO operator principal was substituted for an account principal
  - NO caller-controlled X-User-Id was used to reach another principal
  - account isolation was evaluated WITHOUT impersonation, using two
    synthetic principals and an application-layer ownership check
```

---

## 12. ADR impact

**No ADR change is authorized and none was made.** The following ADRs were
read and their effect on this baseline recorded.

| ADR | Status | Effect on this baseline |
|---|---|---|
| **ADR-084** (Unified Account-Owned Memory Store, accepted; candidate authority amended 2026-09-25) | Consistent | Its amended target (UMS `candidate_unreviewed_fact` owns pre-promotion authority; *"No `personal_facts` row is required for candidate review or quarantine"*) is **not yet implemented** — candidates are still written to `personal_facts` and the species is a compatibility projection (§4.4). ADR-084 explicitly sanctions this transitional state and states that the installed runtime *"has not been migrated to this amended target"*, so this is a **documented transitional gap, not a violation**. It is recorded in §8.5 for the reconciliation task ADR-084 itself defers to. |
| **ADR-013** (Verified Personal Facts Context Injection) | Consistent | Confirms the invariant this baseline preserves: only verified, active facts may enter provider context. Nothing in this task alters injection. The candidate path remains excluded from ambient context: candidates carry `status='candidate'` and project to `REVIEW_POSTURE_PENDING` (`guardian/services/memory_vault_read.py:816-818`). |
| **ADR-039** (Operator vs. account authority) | Consistent, and load-bearing | The finding that the only reachable principal in the local lane is the operator single-user principal (§11.2) is precisely the distinction ADR-039 draws. V9 (the fail-open fallback) would collapse that distinction if it ever activated; it is dormant in the observed runtime. |
| **ADR-081** (Project ownership boundaries) | Consistent | No Project-scoped memory authority was introduced. `project_id` appears only as evidence metadata on live-chat candidates (`guardian/fact_candidate_pipeline.py:250-251`); no Project scope was inferred or claimed. |
| **ADR-041** (VaultNode canonical machine and audit authority) | Noted | Used only to establish that VaultNode is a model-runtime container host in this repository, not the command gateway (§11.1). No change. |

---

## 13. Invariants check

| Invariant | Result | Basis |
|---|---|---|
| The account owns memory. | **Held in the inspected code** | `guardian/core/pgdb.py:2163` filters every candidate read by `user_id`; item routes enforce ownership (`guardian/routes/personal_facts.py:320-321`). Verified at integration level with two synthetic principals. |
| The operator does not inherit account authority. | **Held, and structurally enforced** | `guardian/core/dependencies.py:1012-1039` requires an account session token in remote/private-preview mode; `guardian/mcp_memory/config.py:161-181` rejects identity overrides and remote auth modes; the `X-User-Id` override was observed to be refused outside DEBUG/LOCAL_DEV. **Exception flagged, not fixed:** V9's dormant fail-open fallback would violate this if `guardian.core.dependencies` ever failed to import. |
| Candidates remain excluded from ambient context. | **Held** | Candidates project to `REVIEW_POSTURE_PENDING` (`guardian/services/memory_vault_read.py:816-818`); the verified-fact compatibility reader explicitly excludes candidate/disputed/archived rows (`guardian/core/memory_compatibility.py:35-53`). |
| Only verified, active, eligible facts enter provider context. | **Held, unchanged by this task** | ADR-013 doctrine; no runtime path was modified. |
| Evidence and revision lineage remain intact. | **Held, with a pre-existing gap recorded** | Revisions are written by `db.update_fact` (`guardian/core/pgdb.py:2201+`). Evidence lineage is intact for the import path; the live path can lose an evidence row while keeping the candidate (V7). |
| Canonical and compatibility stores must not compete. | **Held** | The legacy table is the sole durable authority; `candidate_unreviewed_fact` is a read-only projection (`guardian/core/memory_compatibility.py:1-60`). No second authority was introduced. |
| No unapproved collection or promotion. | **Held by this task** | No candidate was promoted, approved, rejected, or deleted; no production or shared database was contacted; no schema was changed. |
| Personal content stays outside public proof artifacts. | **Held** | Every runtime observation used synthetic keys and synthetic values (`synthetic-value-*`); this report contains no excerpt, credential, or real user datum. |

---

## 14. Recommended next atomic repair — exactly one

### PFP-01 — Restore dispatch reachability of `GET /personal-facts/candidates` and make its pagination truthful

**Why this one first.** V1 makes the endpoint, the MCP adapter's
`list_fact_candidates` tool, and the documented read path non-functional. It
is a one-line ordering defect with a deterministic, self-contained blast
radius. V2 is the second half of the same endpoint's contract: even once
dispatch works, `total` under-reports and rows beyond 200 are unreachable.
Repairing them together is one atomic change to one handler plus one data-access
signature — and repairing V1 alone would ship an endpoint that answers but
lies about its own size.

**Defects addressed:** V1 (primary), V2 (same handler contract), V3 (the
`offset`/`total` data-access gap that causes V2).

**Owning files**

| File | Change |
|---|---|
| `guardian/routes/personal_facts.py` | Move the `GET /candidates` declaration **above** the `GET /{fact_id}` declaration so the literal segment wins first-match dispatch. |
| `guardian/routes/personal_facts.py` | Rewrite the handler body: fetch with a real `offset` and a real `limit`, compute `total` from a genuine count query, and return `{ok, facts, total, limit, offset}` with `total` reflecting the true candidate count for the principal and status filter. |
| `guardian/core/pgdb.py` | Extend `list_facts` with an optional `offset` parameter applied in SQL (`OFFSET`), and add a `count_facts` sibling that returns the filtered row count. Preserve the existing call signature so all current callers are unaffected (default `offset=0`). |
| `guardian/core/db.py` | Mirror the same `offset` / count support in the SQLite implementation so the two stores do not diverge. |
| `guardian/routes/personal_facts.py` | Add a deterministic secondary sort key (e.g. `updated_at DESC, id DESC`) so offset pages are stable under concurrent updates. |

**Explicitly out of scope for PFP-01** (each needs its own authorization):
V4 (guardrail classification on the live path), V5 (proposition identity),
V6 (`list_facts` amplification), V7 (evidence-write rollback), V8 (ORM/schema
divergence), V9 (fail-open fallback).

**Test surface**

1. **New route-dispatch test** (the coverage gap that let V1 ship): a
   `TestClient` request to `GET /personal-facts/candidates` must return **200**,
   not 422 — asserted at the HTTP layer, not via a mocked transport.
2. **New pagination test**: with more than 200 candidate rows for one
   principal, assert that `offset=0` and `offset=200` both return their full
   pages, that the union of pages covers every row exactly once, and that
   `total` equals the true candidate count (not 200).
3. **New ordering-stability test**: two consecutive page requests over an
   unchanged data set return disjoint, identical row sets.
4. **New MCP-adapter integration test**: `guardian/mcp_memory` tests should
   assert against a real in-process Guardian app for at least the
   `list_fact_candidates` path, so a shadowing defect cannot pass the adapter
   suite again. At minimum, add a guard asserting that every path the adapter
   targets is dispatched to its intended handler.
5. **Existing suites must stay green**: `tests/mcp/test_client.py`,
   `tests/mcp/test_config.py`, `tests/mcp/test_tools_read.py`,
   `tests/test_fact_candidate_pipeline.py`,
   `tests/identity/test_account_purpose_strict_migration.py`.

**Acceptance criteria**

- `GET /personal-facts/candidates` returns **200** with a JSON body, and
  `GET /personal-facts/candidates/debug/recent` continues to return 200.
- `GET /personal-facts/{numeric_id}` continues to return the fact, and
  `GET /personal-facts/{non-numeric}` returns a 4xx that is **not** an
  `int_parsing` error on `fact_id`.
- With N > 200 candidate rows for one principal, `total == N`, and the pages
  `offset=0..N` partition the row set exactly once.
- With 0 candidate rows, `total == 0` and `facts == []`.
- A cross-account read returns no rows for the non-owning principal, and the
  item route returns 404 for a fact owned by another principal.
- The MCP adapter's `list_fact_candidates` succeeds against an in-process
  Guardian and returns `facts`/`total`/`limit`/`offset` faithfully.
- The same pytest command recorded in §10.1 reports **119 passed, 0 failed**
  plus the new tests.
- `git diff --check` is clean, and the change set touches only the four
  owning files plus new/updated tests — no migration, no ADR change, no
  promotion, no schema change.

**Proof classification expected for PFP-01:** integration-level (real
PostgreSQL, real router, real adapter). Live-runtime proof against a deployed
Guardian remains a separate step and should not be claimed.

---

## 15. Deferred work

| Item | Why deferred | Suggested owner |
|---|---|---|
| V4 — run the guardrail classifier on the live-chat path and record `source_role` | Changes ingestion semantics and guardrail dispositions; needs its own authorization and a Guardrails Contract alignment decision | PFP-02 |
| V5 — proposition identity and contradiction handling | Requires a candidate-vs-candidate data model and a schema decision | separate design task |
| V6 — hoist the dedup listing out of the ingestion loop | Performance work with a bounded but real change to ingestion | PFP-03 |
| V7 — evidence-write failure policy | Needs a decision on rollback vs. quarantine | with V4 |
| V8 — declare `ix_personal_facts_active_key` in the ORM model | Schema-authority change; may require a migration-parity decision | schema task |
| V9 — remove or fail-closed the import fallback | Security-relevant; small but independent | security task |
| Thread-scoped candidate pagination (N+1 evidence reads, filter-before-slice) | Naturally folded into the PFP-01 pagination rewrite | PFP-01 |
| Persist the "sensitive candidate" flag the code comment promises | Depends on the V4 guardrail disposition model | with V4 |
| Reconcile ADR-084's amended candidate authority with the implementation | Explicitly deferred by ADR-084 to a separately authorized, verified migration | UMS campaign |
| Update `docs/architecture/mcp-memory-adapter-v1.md` | **Not authorized by this task**; must follow a verified repair | after PFP-01 |
| Live multi-account isolation proof | Requires a real two-account deployment | separate proof task |
| Guardian-deployed runtime proof of the candidate read path | Requires a running Guardian instance | separate proof task |

---

## 16. Closeout

- **Summary.** The Personal Fact pipeline is two ingestion paths over one
  legacy table. The live-chat path never classifies candidates, so most
  candidates carry no guardrail disposition and no `source_role`. The
  documented candidate-read endpoint is unreachable (HTTP 422) because an
  earlier-registered `{fact_id}` route shadows it, which also makes the MCP
  adapter's `list_fact_candidates` tool non-functional against a live
  Guardian. Its pagination is a hard 200-row read ceiling whose `total`
  under-reports the real count. The prior connector checkpoint failure is
  independent of Guardian availability and was demonstrated not to have
  blocked this task.
- **Files changed.** `docs/Campaign/personal-fact-pipeline-baseline.md` (new,
  this file). No other repository file was created, modified, or staged.
  Probe scripts were kept in `/tmp`, outside the repository.
- **Exact inspected Git revision.** `94b03e6029ddf457aeed9d7f3ead85f5cde3e954`
  on `main`.
- **Validation commands and outcomes.** §10. Required source-level validation:
  **119 passed, exit 0** (mocked unit tests). Disposable-PostgreSQL
  qualification: Alembic upgrade to head `f0d7c4b2a198`, exit 0; all read-only
  probes exit 0; observations in §10.2. Repository hygiene in §10.3.
- **Confirmed defects.** V1, V2, V3, V4, V5, V6, V8 (verified); V7
  (code-path); V9 (code-path, verified dormant).
- **Unverified risks.** Live multi-account isolation; the `/api` mount's
  dispatch; `active_only=False` and non-candidate status branches; the MCP
  origin gate's ordering relative to V1; whether any deployed environment
  mounts the personal-facts router at all.
- **ADR impact.** No ADR changed. ADR-084, ADR-013, ADR-039, and ADR-081 read
  and assessed in §12. The ADR-084 transitional gap is recorded, not
  "corrected".
- **Invariants check.** §13 — all held for this task; V9 is flagged as the one
  latent risk to the operator/account boundary.
- **Proof classification.** §9 — code-path, mocked unit, integration-level,
  and not-proven, separated. **No deployed-runtime proof is claimed.**
- **Documentation follow-through.** Five discrepancies recorded in §8; **no
  canonical documentation was updated**, per the task's constraint.
- **Commit hash.** Recorded in the closeout message accompanying this report.
- **One recommended next atomic task.** PFP-01 (§14).
- **Deferred work.** §15.
