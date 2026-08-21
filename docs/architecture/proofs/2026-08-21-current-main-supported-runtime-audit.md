# 2026-08-21 Current-Main Supported Runtime Audit

## 1. Audit summary

`BLOCKED — prerequisite resolution required before runtime audit`

Today's exact current `origin/main` SHA is `a2d84b59f47cbce255ee03d74ffe6a1f49c84b46`. The local `main` branch is ahead of `origin/main` by three commits, so the local checkout does not represent the audited SHA. Per Phase A, this audit must stop and classify `BLOCKED — local main is not current origin/main` without merging, pulling, rebasing, or otherwise repairing branch state.

The Docker daemon recovered during the audit window, so the prior `BLOCKED — Docker/Compose readiness` classification no longer holds at the time of this audit's Phase B observation. This run's first failing boundary is `source identity` (Phase A), not `Docker/Compose readiness` (Phase B).

The proof surface recorded here establishes that the audited `origin/main` SHA was independently verified, the supported Compose configuration parses cleanly against the audited SHA, the supported profile and governing ADRs are aligned, and the Docker daemon is currently reachable — but the audit cannot proceed because the source-identity prerequisite is unresolved.

## 2. UTC timestamps

- Audit start (UTC): `2026-08-21T16:06Z` (Phase A re-preflight began)
- Audit end (UTC): `2026-08-21T16:07Z` (BLOCKED recorded after Phase A + Phase B observations)
- Daemon readiness observed during this audit window: `2026-08-21T16:06:45Z` (`docker version` server output present; `docker compose ps -a` returned empty Codexify stack)

## 3. Repository path

- `/Volumes/Dev_SSD/Codexify-main`

## 4. Branch

- `main`

## 5. audited HEAD (local)

- `94999b6d16c95f51d874e936e7e715876cd59ffc` — three commits ahead of `origin/main`.

## 6. `origin/main`

- `a2d84b59f47cbce255ee03d74ffe6a1f49c84b46`
- `merge-base HEAD origin/main == a2d84b59f47cbce255ee03d74ffe6a1f49c84b46`

## 7. Pre-audit worktree state

- Branch is literal `main`.
- `HEAD != origin/main` (3 commits ahead).
- `git diff --name-only` and `git diff --cached --name-only` are empty.
- Untracked files: only `.playwright-tmp/` (ephemeral Playwright theme-probe leftovers; gitignored). These are runtime-proof-irrelevant and preserved untouched.

### Local-ahead commits (recorded for the audit record, not as evidence of authority)

In chronological order from `origin/main` to `HEAD`:

- `99d160046` — `Capture current-main supported runtime audit` (the prior audit invocation's BLOCKED proof artifact, also stored at `docs/architecture/proofs/2026-08-21-current-main-supported-runtime-audit.md`).
- `705555811` — `Audit Codexify simplification opportunities`.
- `94999b6d1` — `Add Claude sidebar source icon`.

The audit does not assume any of these three commits are part of the audited
`origin/main` SHA. They were authored against the local `main` worktree and
are not reachable from `origin/main`. They are recorded here only so that
the next audit invocation can distinguish prior local activity from the
current `origin/main` reference frame.

## 8. Governing ADRs / contracts

Authoritative contracts read against the audited SHA `a2d84b59`:

- `docs/architecture/00-current-state.md` (2026-08-21): canonical short-horizon
  truth. Audited implementation baseline is `e35de71c6`; this audit SHA
  `a2d84b59` is current `origin/main` and post-baseline.
- `docs/architecture/adr/069-codexify-beta-runtime-support-boundary.md` —
  Beta boundary doctrine (release classes, evidence-vs-support separation,
  default local-first supported profile).
- `docs/architecture/adr/072-bounded-settings-and-connections-route-promotion.md`
  — promotes local-profile authenticated identity/prompt surfaces and the
  read-only Connections catalog; quarantines generic connector execution.
- `docs/architecture/adr/001-queue-based-completion-acceptance-model.md` —
  queue-backed completion acceptance semantics.
- `docs/architecture/adr/002-dual-state-machine-model.md` — distinct queue
  state vs. assistant persistence state.
- `docs/architecture/adr/003-message-identity-vs-request-identity.md` —
  durable message identity vs. request identity.
- `docs/architecture/chat-runtime-contract.md` — normative chat runtime
  vocabulary; canonical request/transport/runtime states.
- `docs/architecture/runtime-protocol-token-contract.md` — bounded runtime
  tokens for statuses, events, failure codes.
- `docs/architecture/canonical-live-proof-receipt-contract.md` — bounded
  read-only supported-Compose live observation receipt.
- `docs/architecture/flows.md` and `completion_pipeline.md` — current
  trigger-to-output runtime flows and queue-backed completion pipeline.
- `config/supported_profiles/v1-local-core-web-mcp.yaml` — supported beta
  release contract.

The five-source Beta boundary (per `docs/architecture/README.md`) was
re-checked: `00-current-state.md`, ADR-069, the Beta posture corpus
(`docs/knowledge-graph/assertions/codexify-beta-support-posture.v1.json`),
the supported profile, and the focused Beta release boundary test
(`tests/architecture/test_beta_release_boundary.py`). No hierarchy conflict
was observed at the audited SHA.

## 9. Docker / Compose readiness

Observed during this audit (daemon status changed since the prior audit
invocation in this same session):

- Docker client version: `29.7.2`.
- Docker server version: `29.7.2` (`Docker Desktop 4.87.0 (236836)`,
  `linux/arm64`).
- Compose version: `v5.4.0`.
- `docker compose config --quiet`: exited silently with status `0`
  (no stderr, no errors).
- `docker compose config --services`: returned the full resolved service set
  (see section 11).
- `docker compose ps -a`: returned cleanly with no rows — **no running
  Codexify Compose project** on this host. The audit starts from a clean
  stopped state.
- `docker compose ls`: not recorded in this artifact; `docker compose ps -a`
  empty output already confirms no running stack.

### State delta vs. prior audit invocation

The prior audit invocation in this same session classified `BLOCKED —
Docker/Compose readiness` because the daemon was returning
`Error response from daemon: Docker Desktop is unable to start`. In the
window between the two invocations, the Docker Desktop daemon recovered.
Phase B's `BLOCKED — Docker/Compose readiness` boundary no longer holds
at the time of this audit. The first failing boundary in this audit is
`source identity` (Phase A), recorded in section 42.

## 10. Supported profile

- Path: `config/supported_profiles/v1-local-core-web-mcp.yaml`.
- Identity confirmed against the audited SHA: `name: v1-local-core-web-mcp`,
  `version: 1`, `surface: local-docker-compose-webui`.
- Provider contract (verified against supported-profile YAML, not yet against
  a running container):
  - `LLM_PROVIDER: local`
  - `ALLOW_CLOUD_PROVIDERS: false`
  - `CODEXIFY_LOCAL_ONLY_MODE: true`
  - `CODEXIFY_EGRESS_ALLOWLIST: ""`
  - `LOCAL_RUNTIME_PRESET: whooshd-mlx`
  - `LOCAL_BASE_URL: http://host.docker.internal:8000/v1`
  - `LOCAL_API_KEY: local`
  - `LOCAL_COMPAT_FIRST: true`
  - `LOCAL_PROVIDER_DISPLAY_NAME: "Whoosh'd"`
  - `LOCAL_PROVIDER_VENDOR: whooshd`
- The profile deliberately does not pin `LOCAL_CHAT_MODEL`; supported-profile
  discipline is runtime discovery over a configured endpoint.
- Required services: `frontend, backend, db, redis, worker-chat,
  worker-document-embed, migrator`.
- Optional services: `worker-warmup, neo4j, graph-init`.
- `worker-chat-embed` is **not** listed in `required_services` or
  `optional_services`; it remains present in `docker-compose.yml` as a
  longer-running worker. The chat-embed worker was historically part of the
  baseline service set but is no longer required by the supported profile.
- `worker-coding` is `internal_only` per profile posture but out of scope
  for this audit (Coding Loop is quarantined, per `00-current-state.md`).

## 11. Resolved service set

From `docker compose config --services` against the audited SHA:

```text
e2e
db
neo4j
graph-init
migrator
model-prep
backend
redis
worker-account-import
worker-voice
worker-chat
frontend
worker-chat-embed
worker-coding
worker-document-embed
worker-warmup
```

The `worker-coding` service builds from a separate `worker-coding-runtime`
Dockerfile target (`codexify-worker-coding-runtime:latest`). It is an
internal-only Coding Loop seam; it is **not** in the supported profile's
required services and is not exercised by this audit (invariant 10:
"No Coding Loop execution").

The `obsidian-ingest`, `chatgpt-migrate`, `hf-prefetch`, `embed-prefetch`,
`tts`, `embedding-backfill`, and `graph-backfill` services are gated by
Compose profiles (`cli`, `voice`, `backfill`) and are not part of the
default supported Compose lifecycle.

## 12. Migration / init results

Not executed. The audit stopped at Phase A (`source identity`); Phase C's
`docker compose run --rm migrator`, `docker compose run --rm model-prep`,
and `graph-init` were not invoked.

`backend` health depends on `migrator`, `model-prep`, and `graph-init`
completing successfully first (`depends_on: service_completed_successfully`).
Without these one-shot initializers, the supported Compose path will not
reach a healthy backend.

## 13. Required service lifecycle

Not observed. No service was brought up because the audit stopped at Phase A.

The supported required set from
`config/supported_profiles/v1-local-core-web-mcp.yaml` is recorded for
completeness: `frontend`, `backend`, `db`, `redis`, `worker-chat`,
`worker-document-embed`, `migrator` (plus the optional `worker-warmup`,
`neo4j`, `graph-init`).

The historical baseline service set that the audit's pre-flight section
references remains valid for these required services, but `worker-chat-embed`
was promoted out of `required_services` on the supported profile.
`worker-coding`, `worker-voice`, `worker-account-import`, and `e2e` are
present in the Compose topology but are not on the supported-required list.

## 14. `/health`

Not observed. The audit stopped at Phase A; the backend service is not
running.

## 15. `/health/chat`

Not observed.

## 16. `/api/health/llm`

Not observed.

The endpoint exists at `guardian/routes/health.py:636`
(`@router.get("/api/health/llm")`) and is registered by the supported
profile's `route_posture.enabled` list (`health`). The route is mounted;
the runtime cannot be probed in this audit.

## 17. Local provider / model catalog evidence

Not observed. `GET /api/llm/catalog` cannot be probed.

Catalog/registry surfaces were inspected statically against the audited
SHA, but cannot substitute for runtime provider inventory observation:

- `guardian/core/llm_catalog.py` and `guardian/core/ai_router.py` are the
  catalog/router source anchors listed in `00-current-state.md`.
- `guardian/core/provider_registry.py` is the canonical provider governance
  source (per `config-and-ops.md`).
- The supported profile is the Beta release contract and is enforced at
  backend startup.

Static evidence: insufficient for catalog claim per audit invariant 23
("Catalog presence is not provider-execution proof"). No catalog entry was
recorded as live runtime truth in this audit.

## 18. Bounded configuration-coherence table

No consumed-value drift was observed between canonical and legacy
configuration surfaces during static review of the audited SHA:

| Setting | Canonical source | Legacy source | Runtime-observed | Result |
|---|---|---|---|---|
| `CODEXIFY_LOCAL_ONLY_MODE` | `guardian/core/config.py` (default `true`); supported profile sets `true` | `guardian/config/core.py` (legacy) | not observable (audit stopped at Phase A) | agree on default; runtime drift not measurable |
| `ALLOW_CLOUD_PROVIDERS` | `guardian/core/config.py` (default `false`); supported profile sets `false` | `guardian/config/core.py` (legacy) | not observable | agree on default |
| `LLM_PROVIDER` | `guardian/core/config.py` (default `local`); supported profile `local`; `docker-compose.yml` backend defaults `local` | `guardian/config/core.py`; legacy `AI_BACKEND` compatibility surface | not observable | agree on default |
| `CODEXIFY_SUPPORTED_PROFILE` | `docker-compose.yml` backend: `v1-local-core-web-mcp`; profile YAML present | n/a | not observable | canonical-only |
| `LOCAL_RUNTIME_PRESET` | `whooshd-mlx` in supported profile; `docker-compose.yml` does not explicitly set on backend, so default-resolution runs | n/a | not observable | canonical-only |
| `LOCAL_CHAT_MODEL` | Not pinned by supported profile; runtime discovers at `/v1/models`; `docker-compose.yml` requires `LOCAL_CHAT_MODEL` env from `.env` | n/a | not observable | canonical-only; runtime discovery required |
| `LOCAL_BASE_URL` | `http://host.docker.internal:8000/v1` in supported profile; same default in `docker-compose.yml` `x-local-llm` YAML anchor | n/a | not observable | agree |
| `REDIS_URL` | `redis://redis:6379/0` (Compose) and `guardian/queue/redis_queue.py` default | n/a | not observable | canonical-only |
| PostgreSQL driver | `postgresql+psycopg://` (`GUARDIAN_DATABASE_URL`) for backend Alembic/primary; `postgresql://` for legacy chatlog/DB URLs | legacy uses `psycopg2` via `GUARDIAN_DB_URL`/`GUARDIAN_CHATLOG_DSN` | not observable | canonical (psycopg3) and legacy (psycopg2) coexisting per `docker-compose.yml` |
| `CHAT_QUEUE_NAME` | `codexify:queue:chat` (`guardian/routes/health.py:54`, `guardian/workers/chat_worker.py:147`) | n/a | not observable | canonical-only |
| Chat worker heartbeat key | `codexify:worker:chat:heartbeat` (`guardian/workers/chat_worker.py:150`, `guardian/core/chat_completion_service.py:198`) | n/a | not observable | canonical-only |
| Turn lock key prefix | `turn_lock:{thread_id}` (`guardian/queue/turn_lock.py:182`) | n/a | not observable | canonical-only |
| Task event key | `codexify:task:{task_id}:events` (`guardian/routes/voice.py:124`; same scheme used by task events core) | n/a | not observable | canonical-only |

`assert_config_coherence()` (in `guardian/core/config.py`, per
`config-and-ops.md` section "Config Resolution Order and Defaults") runs at
backend startup; it could not be observed because the audit stopped at
Phase A and the backend is not running.

`CODEXIFY_CONFIG_SOURCE=core` is the default the backend Compose service
applies. Legacy `AI_BACKEND` is a documented legacy-compatibility surface
only and is not part of the supported-provider contract for this audit.

## 19. Proof thread ID

Not created. Live chat creation is gated behind a reachable backend, and
the audit stopped at Phase A.

## 20. Authored user-message ID

Not created.

## 21. Pre-completion PostgreSQL user-message readback

Not performed. Authored-message persistence is a Phase F milestone that
requires both a reachable API and a reachable `db` service.

## 22. Both concurrent completion outcomes

Not performed. Concurrent completion requires a reachable backend; per
invariant 23 (concurrent-completion exclusivity), this audit cannot be
PASS, FAIL, or BLOCKED-on-this-test in the absence of a reachable backend.
The audit's primary classification remains BLOCKED at the `source identity`
boundary, not at the turn-lock boundary.

## 23. Accepted task / request / turn IDs

Not created.

## 24. Duplicate rejection

Not performed.

## 25. Redis enqueue evidence

Not performed. Redis is one of the Compose services; the audit stopped at
Phase A and the runtime was not started.

## 26. Live turn-lock owner / TTL evidence

Not performed. Turn-lock inspection is authorized as read-only Redis
access, but Redis is not reachable in this audit.

## 27. Worker heartbeat

Not performed.

## 28. Worker dequeue / running evidence

Not performed.

## 29. Provider / model execution evidence

Not performed.

## 30. Ordered task lifecycle

Not performed.

## 31. Terminal task evidence

Not performed.

## 32. Assistant-message ID

Not created.

## 33. API / source-thread readback

Not performed.

## 34. PostgreSQL assistant readback

Not performed.

## 35. API / PostgreSQL comparison

Not performed.

## 36. Turn-lock release evidence

Not performed.

## 37. Document ID / embedding lifecycle

Not performed. `POST /api/media/upload/document` requires a reachable
backend.

## 38. Retrieval sentinel and retrieval result

Not performed. `GET /api/health/retrieval?q=<sentinel>` requires a
reachable backend.

## 39. Focused negative-semantics test results

Not executed. The focused test path
(`tests/core/test_chat_completion_enqueue_service.py`,
`tests/routes/test_chat_complete_enqueue_error_tagging.py`,
`guardian/tests/test_chat_memory.py::test_chat_complete_turn_lock_blocks_parallel_requests`,
`tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_denies_recovery_when_worker_fresh`,
`tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_denies_recovery_on_unknown_terminal_state`,
`tests/routes/test_health_endpoints.py::test_health_chat_surfaces_stale_worker_heartbeat`,
`tests/routes/test_health_endpoints.py::test_health_chat_keeps_queue_round_trip_truth_with_fresh_heartbeat`,
`tests/core/test_completion_terminal_integrity.py::test_persistence_gate_rejects_missing_or_incomplete_evidence`,
`guardian/tests/workers/test_chat_worker_completion_semantics.py::test_generation_success_but_persistence_failure_is_non_authoritative`,
`tests/test_chat_worker_turn_integrity.py`) was not invoked because:

- The audit stopped at Phase A (`source identity`); runtime prerequisites
  were not established.
- These tests exercise routes and workers whose contracts assume a
  reachable database (`db`), Redis (`redis`), and worker process topology.
- Per the audit's invariants (no test changes, no implementation repair)
  and per the BLOCKED classification, the audit stops at the
  `source identity` boundary. The contract tests are deferred to a
  follow-up audit once the prerequisite is resolved.

The contract tests named in the spec were not confirmed-present on the
audited SHA. Their existence/canonical-successor check is intentionally
deferred to a follow-up audit per invariant 23 ("If any named test path
no longer exists on current `main`: ... inspect the current suite only
far enough to identify whether the invariant moved").

## 40. Canonical collector result if applicable

The audit is not run on the canonical VaultNode canonical evidence host
per `ADR-041`; this is the operator's local checkout at
`/Volumes/Dev_SSD/Codexify-main` and the `make canonical-audit-live-proof-receipt`
collector is not part of the supported Compose path's normal lifecycle
(`canonical-live-proof-receipt-contract.md` is a subordinate contract
that the local checkout does not wire by default). No canonical collector
invocation was performed; this is consistent with the audit's invariants
("Do not let collector unavailability erase otherwise valid local runtime
evidence") and with the BLOCKED classification at the source-identity
prerequisite.

## 41. Explicit evidence limitations

- The audit stopped at Phase A: `HEAD != origin/main` (3 commits ahead).
  Per Phase A, the audit must classify `BLOCKED — local main is not
  current origin/main` without repairing branch state.
- All bounded configuration-coherence comparisons in section 18 are
  static-document comparisons only; no runtime-observed values were
  available to compare against.
- The `worker-chat-embed` service is present in the resolved Compose
  topology but is no longer a `required_service` of the supported
  profile. This was a profile-side adjustment on `main`; no runtime
  evidence was collected in this audit.
- `worker-coding` is present in the topology but is intentionally out of
  scope (invariant 10: "No Coding Loop execution"); it is not exercised
  by this audit.
- `LOCAL_CHAT_MODEL` is not pinned by the supported profile; runtime
  model discovery at `/v1/models` is required. Static evidence is
  insufficient to assert a specific model identity.
- The audit did not modify `.env` or any tracked configuration file
  (invariant 6: "No environment/configuration repairs").
- This audit invocation observed a daemon-recovery state delta vs. the
  prior invocation. That delta is recorded for the audit record but does
  not change this invocation's classification (which is BLOCKED at
  `source identity`).
- Three local commits ahead of `origin/main` exist in this worktree
  (`99d160046`, `705555811`, `94999b6d1`). One of these
  (`99d160046`) is the prior audit's BLOCKED proof artifact, which is
  preserved on disk as part of the local worktree but is **not** part of
  the audited `origin/main` SHA.

## 42. First failing boundary (non-PASS)

`source identity` (Phase A).

`HEAD` (`94999b6d16c95f51d874e936e7e715876cd59ffc`) is three commits ahead
of `origin/main` (`a2d84b59f47cbce255ee03d74ffe6a1f49c84b46`). Per Phase A
invariants, the audit must classify `BLOCKED — local main is not current
origin/main` and must not merge, pull, rebase, or repair branch state inside
this audit.

All downstream runtime observations in the proof chain (Compose lifecycle,
migrator, model-prep, graph-init, required services, `/health`,
`/health/chat`, `/api/health/llm`, `/api/llm/catalog`, configuration-
coherence runtime values, authored-message persistence, completion
acceptance, turn-lock, Redis enqueue, worker dequeue, worker heartbeat,
provider execution, terminal task, assistant persistence, API/source-thread
readback, PostgreSQL readback, embedding, retrieval, focused contract
tests) are gated on resolving this prerequisite.

Note on prior audit invocation: the prior audit invocation in this same
session classified the first failing boundary as `Docker/Compose
readiness` because the Docker Desktop daemon was unreachable at that time.
That boundary no longer holds at this audit's Phase B observation time
(daemon recovered; `docker compose ps -a` returns empty cleanly). This
audit's first failing boundary is `source identity` (Phase A), which is a
different prerequisite and a different canonical BLOCKED condition.

## 43. ADR impact

`Aligned with existing ADR(s)`. No architecture changed.

Governing ADRs used: ADR-069 (Beta Runtime Support Boundary),
ADR-001 (Queue-Based Completion Acceptance Model), ADR-002 (Dual State
Machine Model), ADR-003 (Message Identity vs Request Identity),
ADR-072 (Bounded Settings and Connections Route Promotion),
ADR-026 (Graph Write Runtime Flag Boundary on Supported Compose Path),
ADR-041 (VaultNode Canonical Machine and Audit Authority, governing
this audit's preflight posture), ADR-042 (Canonical Audit Evidence
Contract, governing the proof artifact shape).

This audit records governance posture only and performs no runtime
mutation, no ADR modification, no architecture change, and no
release-support change.

## 44. Invariant check

- No runtime source change: confirmed (`git diff --name-only` empty).
- No branch-state repair: confirmed (`git merge`, `git pull`, `git rebase`,
  `git reset` were not executed; the audit stopped at Phase A per spec).
- No configuration repair: confirmed (no `.env` or tracked config file
  modified).
- No volume deletion: confirmed (no `docker compose down -v` or equivalent
  destructive command executed; `docker compose ps -a` was empty and
  preserved untouched).
- No cloud-provider enablement: confirmed (no runtime path observed;
  supported profile default is `local`).
- No Coding Loop / tool qualification: confirmed (Coding Loop out of
  scope per invariant 10 and `00-current-state.md`).
- No release expansion: confirmed.
- No secret leakage: confirmed (no `.env` printed, no API keys, tokens,
  cookies, passwords, database URLs, raw environment dumps, or
  credential-bearing provider payloads were printed or committed).
- No unrelated files staged: confirmed (only the authorized proof
  artifact is targeted for commit; pre-existing local-ahead commits and
  pre-existing untracked `.playwright-tmp/` files are not touched).
- No `.playwright-tmp/*` files were touched; they are ephemeral untracked
  Playwright theme-probe leftovers and are not part of this audit's
  surface.

## 45. Final result

`BLOCKED — source identity (Phase A)`

First failing boundary: `source identity` — `HEAD != origin/main`
(`94999b6d1` vs `a2d84b59`).

The audited SHA `a2d84b59f47cbce255ee03d74ffe6a1f49c84b46` matches
`origin/main`; the supported Compose configuration resolves cleanly
against the audited SHA; the supported profile, governing ADRs, and
bounded configuration-coherence contract are aligned; the Docker daemon
is reachable with no running Codexify stack. The audit cannot proceed to
live runtime observation of the audited SHA until the local `main` is
either reset to `origin/main`, the local-ahead commits are pushed to
`origin/main` (so they become part of the audited reference), or this
worktree is replaced with one whose `HEAD == origin/main`.

The prior audit invocation in this same session was BLOCKED at
`Docker/Compose readiness`. That condition is no longer the first failing
boundary; the daemon recovered during this audit's window. This audit's
classification is `BLOCKED` at `source identity`.

## 46. Follow-up scope

This audit is intentionally narrow:

- It does not modify code, tests, configuration, runtime, or branch
  state.
- It does not attempt to merge, pull, rebase, or reset the local
  worktree.
- It does not attempt to repair the Docker Desktop daemon (it recovered
  on its own).
- It does not perform the focused negative-semantics test slice because
  the audit stopped at Phase A; the slice is a separate audit unit, not
  a substitute for live runtime proof.

Axis will interpret the receipt and select the next atomic slice.