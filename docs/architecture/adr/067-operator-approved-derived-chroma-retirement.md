# ADR-067 Operator-Approved Derived Chroma Retirement

**Status:** Accepted

## Context

The current Tester Chroma store located at `/Volumes/Dev_SSD/Codexify-main/.chroma` was created by a non‑stock Chroma migration and is incompatible with the canonical runtime `chromadb==1.0.15`. The diagnostic proof `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md` classifies the failure as a **PERSISTED_STORE_COMPATIBILITY_BOUNDARY** and recommends copy‑first schema reconciliation.

The operator has elected a different resolution: preserve the incompatible store as historical evidence, retire it from the active runtime path, and initialise a fresh supported Chroma index via the canonical runtime.

## Problem Statement

* The active Chroma store cannot be opened by the supported runtime, causing a panic (`range start index 10 out of range for slice of length 9`).
* The store is derived retrieval state – it is not canonical application authority.
* The operator requires an explicit governance decision authorising retirement while preserving the historical bytes.

## Decision

1. **Authority** – Postgres remains the canonical source of truth for application state. The vector store is strictly a retrieval/index artefact.
2. **Derived State Handling** – Derived Chroma indexes are not automatically disposable; retirement must be operator‑approved and documented.
3. **Operator‑Approved Retirement** – The operator may retire an active Chroma index when:
   - The supported runtime cannot consume it.
   - No canonical authority is derived from it.
   - The original bytes are preserved (e.g., copied to a safe archival location).
   - Writer quiescence is proven.
4. **Preserve‑Retire‑Rebuild Semantics** – Three distinct states are defined:
   - `HISTORICAL_CHROMA_PRESERVATION_RETAINED`
   - `ACTIVE_CHROMA_INDEX_RETIRED`
   - `FRESH_CHROMA_INITIALIZED`
   No state implies another.
5. **No Schema Surgery** – The copy‑first schema reconciliation path remains available for forensic recovery but is not required for this retirement.
6. **Fresh Initialise** – A new Chroma store must be created exclusively through the supported Codexify runtime (i.e., by starting the Tester backend with the stock runtime).
7. **Proof Requirements** – The retirement execution must prove:
   - Exact identity of the retired store.
   - Writer quiescence.
   - Preservation of the original bytes.
   - Fresh store initialisation via the canonical runtime.
   - Absence of the Rust panic after retirement.
   - Successful backend health (`/health`, `/health/chat`).
8. **Rollback Boundary** – Restoring the historical store requires a separate, explicitly authorised architecture‑impact task.

## Authority Boundary

- **Postgres** – remains the sole authority for canonical application data.
- **Chroma** – remains a semantic retrieval store; its persisted bytes are never promoted to canonical authority.

## Operator‑Approval Boundary

Retirement may only be performed after explicit operator approval (this ADR) and after the proof steps listed above are satisfied.

## Preservation Requirement

The original `.chroma` directory must be copied to an archival location (e.g., `archive/chroma/<commit‑sha>/`) before any destructive deletion.

## Active‑Retirement Semantics

The active store is removed from the runtime path after preservation; the runtime is then started so it creates a fresh empty store.

## Fresh‑Initialisation Semantics

The fresh store is created by the stock `chromadb==1.0.15` runtime during normal backend start‑up; no manual schema manipulation is performed.

## Provenance Requirement

All records in the fresh store must originate from canonical sources (Postgres) or deterministic supported built‑ins. No records from the retired store may be copied into the fresh store.

## Runtime‑Proof Requirement

The execution must verify backend start‑up without panic, successful health checks, and authenticated Tester viability.

## Rollback/Restoration Boundary

Restoring the historical store is a separate task and requires its own ADR.

## Consequences

- No change to runtime code, tests, Docker compose, or migrations.
- Documentation reflects the new retirement policy.
- Future operators may use this ADR as the governing reference for similar derived‑store retirements.

## Rejected Alternatives

- **Pin/upgrade Chroma** – Rejected because the non‑stock migrations are outside the supported runtime.
- **Mutate old SQLite store** – Not required; operator chose preserve‑retire‑rebuild.
- **Promote records to Postgres** – Forbidden; derived state cannot become canonical authority.
- **Delete without preservation** – Disallowed; derived state must be retained as evidence.
- **Switch vector backend** – Unrelated to the incompatibility; the defect is store‑schema, not backend choice.

## Implementation/Proof Follow‑Through

The execution task will:
1. Verify the active store identity.
2. Ensure writer quiescence.
3. Copy the store to an archival location.
4. Delete the active store.
5. Restart the Tester backend to initialise a fresh store.
6. Run health checks and confirm the panic is gone.

## Current Evidence Anchors

- `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md`
- `docs/architecture/proofs/2026-08-13-preserved-tester-canonical-startup-auth-proof.md`

## Private-preview storage-topology refinement — 2026-09-08

**Decision frozen; implementation and live recovery pending.** This refinement
applies only to the Persona post-C07 private-preview deployment on the diagnosed
Docker host. C07 remains historically closed. It supplies the persistence
substrate for this ADR's existing fresh-initialization policy; it does not
redefine default local Compose storage, change Persona authority under ADR-082,
or widen Beta support. No new ADR is required within this boundary. A change to
repository-wide storage support requires a separate decision.

### Repository and diagnostic evidence

Inspected from a clean worktree on branch `codex/private-preview-chroma-topology`,
based on freshly fetched `origin/main` at
`742d2738f7013a2fc4cd86ada3aea944433d2744`. Values below are source inspection
at that revision, not a new inspection of the live deployment or secret env.

| Surface | Current value | Authority/effect | Relevant to private preview |
| --- | --- | --- | --- |
| `scripts/ops/codexify_private_preview.sh:12-29` | Explicit project directory; project defaults to `codexify_private_preview`; explicit base plus private-preview files | Selects deployment root, env-file location, project and Compose inputs | Yes; env values were not read |
| `docker-compose.yml:265-335` | Backend working directory `/app`; bind `./.chroma:/app/.chroma`; path default `./.chroma` | Resolves host source against deployment root and logical path inside backend | Yes, inherited unchanged by current overlay |
| `docker-compose.yml:465-521` | `worker-chat` uses `/app`, but has no Chroma mount or explicit vector path environment mapping | Shared-store configuration gap; source does not prove shared persistence | Yes; must be corrected in private-preview overlay |
| `docker-compose.yml:713-870` | Document/chat embedding workers and optional `embedding-backfill` bind `./.chroma:/app/.chroma`, with shared path/store/collection defaults | Embedding writers and backfill persistence | Yes; backfill remains opt-in |
| `docker-compose.yml:153-185` | Optional `obsidian-ingest` has the same bind and vector defaults | CLI ingestion writer | Only if separately enabled; must not retain a host-bind route into this store |
| `docker-compose.override.yml:1-16` | Adds a host Chroma bind to `worker-chat` | Default development override | Not loaded by the private-preview script's explicit `-f` pair |
| `docker-compose.private-preview.yml` | Sets preview/provider/auth posture; no Chroma mount override or volume declaration | Inherits base storage | Exact bounded implementation destination |
| `guardian/core/config.py:910-939`; `guardian/vector/store.py:74-100`; `backend/rag/embedder.py:233-239` | `CODEXIFY_CHROMA_PATH` resolves to an absolute path; vector store passes it to `PersistentClient` | Logical path configuration and client construction | Yes; preserve `/app/.chroma`, `chroma`, and `codexify_vault_supported` |
| `config/supported_profiles/v1-whooshd-deepseek-web.yaml` | Named preview route/provider posture; no physical Chroma mount declaration | Exposure contract, not storage substrate | Read-only; no profile amendment needed |
| `docker-compose.yml:1101-1114` | `pg_data`, `neo4j_data`, `hf_cache`, `codexify_models`, `model_store`, frontend/test caches, `codexify_cli_home`, `codexify_pi_auth`; no Chroma volume | Existing independent named volumes | Preserve all unrelated volume identities |
| `docker-compose.runtime.yml`; `docker-compose.webui-runtime.yml` | Separate runtime family declares `codexify_chroma` | Existing named-volume precedent, not preview adoption | Not in preview input pair; do not reuse or edit this topology |
| `scripts/ops/codexify_private_preview.sh:99-105,169-180,213-228` | `up --build`, periodic `up`, intentional shutdown uses `stop`; desired-up marker controls reconciliation | Container lifecycle distinct from volume retirement | Yes; reconciliation stays suspended through recovery qualification |

The [lineage attempt](../proofs/runtime/2026-09-06-persona-private-preview-lineage-proof-r2.md)
records the deployment root as `/Users/chriscastillo/.codex/worktrees/dda8/Codexify-main`
and project `codexify_private_preview`. The [preservation diagnosis](../proofs/runtime/2026-09-06-persona-private-preview-chroma-diagnosis.md)
records the host `.chroma` bind and separately retained immutable preservation.
The [empty control](../proofs/runtime/2026-09-06-persona-private-preview-chroma-empty-control-diagnosis.md)
and [named-volume comparison](../proofs/runtime/2026-09-07-persona-private-preview-chroma-named-volume-comparison.md)
prove first-call initialization on disposable Docker-managed storage with the
exact failed image, while the preserved copy reproduces the historical panic.
The [ADR-067 recovery gate](../proofs/runtime/2026-09-07-persona-private-preview-chroma-adr067-recovery-proof.md)
stopped before retirement. The [host-storage diagnosis](../proofs/runtime/2026-09-07-persona-private-preview-sqlite-host-storage-diagnosis.md)
then reproduced `SQLITE_READONLY_DBMOVED` on three host binds across two APFS
mounts. This remains exact-image/host evidence, not a universal filesystem claim.

### Admissible choices

| Choice | Classification | Reason |
| --- | --- | --- |
| Existing or relocated host bind | `REJECTED_FOR_PRIVATE_PREVIEW_RECOVERY` | Repeated exact-runtime SQLite write failure; no further arbitrary host-path probes or silent fallback |
| One explicit Docker-managed named volume | Selected for this private preview | Qualified disposable SQLite/Chroma substrate; durable identity and operator lifecycle defined below; adoption remains unproven |
| Container writable layer | Rejected for active persistence; diagnostic control only | Successful writes do not survive container replacement as a shared persistent store |
| Anonymous volume | Rejected for active persistence | Potential byte retention does not provide deterministic identity and reattachment across recreation |

### Selected store and lifecycle

The future private-preview overlay must declare Compose key
`private_preview_chroma`, with literal engine name
`codexify_private_preview_chroma` and `external: true`. This is one
Docker-managed local volume without host-bind, network, or other `driver_opts`.
External means operator-managed lifecycle outside Compose, not remote storage.
The engine-local name is independent of checkout path, image tag, and Compose
project interpolation. It is a deployment resource name, not a new runtime token.

Every preview Chroma consumer must mount this same volume root at `/app/.chroma`
using `type: volume` and `volume.nocopy: true`. The consumer set is `backend`,
`worker-chat`, `worker-document-embed`, `worker-chat-embed`, and the existing
optional `obsidian-ingest` and `embedding-backfill` services if invoked.
Keep optional profiles disabled unless separately authorized. Pin the effective
vector configuration uniformly to `CODEXIFY_VECTOR_STORE=chroma`,
`CODEXIFY_CHROMA_PATH=/app/.chroma`, and
`CODEXIFY_COLLECTION=codexify_vault_supported` in this overlay, so inherited
environment settings cannot redirect one consumer to another store.

Compose's [external/name contract](https://docs.docker.com/reference/compose-file/volumes/)
provides exact lookup and fails when the external volume is absent; an ordinary
Compose-managed volume could otherwise be silently recreated after deletion.
[Mount options](https://docs.docker.com/reference/compose-file/services/#volumes)
provide `nocopy` to prevent image-directory contents from seeding the volume.
The [merge contract](https://docs.docker.com/reference/compose-file/merge/)
keys service volumes by target: the follow-on must verify the resolved mount,
not assume that an overlay has replaced every inherited bind.

| Event | Required persistence/lifecycle meaning |
| --- | --- |
| Service restart or container recreation | Reattach the same named volume; never initialize a replacement merely because a container changed |
| Compose reconciliation | Resolve the same external name; absence is a failure, not creation or host-bind fallback |
| Image replacement / rebuild | Retain active volume; validate supported-runtime compatibility before activation; incompatible state returns to ADR-067 gates |
| Host reboot / Docker restart | Retain volume within the same Docker data store/context; resume only after applicable qualification and maintenance gates |
| Intentional preview shutdown / ordinary Compose down | Retain volume; container removal is not retirement ([Docker down semantics](https://docs.docker.com/reference/cli/docker/compose/down/)) |
| Volume deletion, Docker data reset, disk loss, or context change | Persistence is not guaranteed; stop and classify. No automatic empty replacement, alternate volume, or historical restore |

The human deployment operator owns creation, identity acceptance, preservation,
retirement, and any later replacement. Neither a worker nor a reconciler owns
those decisions. First creation belongs to the separately authorized recovery
task, after quiescence, preservation re-verification, and active-store retirement.
An existing volume with this name must be classified before adoption; a name
alone is not evidence of origin, emptiness, or acceptable content. Record engine
context, name, driver/options, creation metadata, and effective mounts in that
task's receipt. Missing or conflicting identity stops activation. Do not change
the preview project/root or run a second project concurrently against the volume;
stable naming does not enforce exclusive access by itself.

The Docker daemon and host operator remain trusted infrastructure. The relevant
failure model is accidental deletion, drift, unexpected content, or split stores;
this decision does not defend against a compromised daemon or grant container
processes Docker administration. Account authorization, Persona revisions and
bindings, canonical Postgres ownership, and existing retrieval consistency remain
unchanged. One shared store is not proof of multiprocess Chroma concurrency;
worker safe-start qualification remains mandatory, with no new replication or
conflict-resolution protocol introduced.

Historical incompatible preservation remains immutable, separately retained
outside the active volume, and never mounted writable or seeded into it.
No historical rows, embeddings, metadata, documents, or SQLite bytes may migrate
to the fresh store. Rebuild inputs are only canonical supported sources or
deterministic supported built-ins. Derived does not mean disposable: future
volume retirement still requires operator approval, writer quiescence, and
separate preservation. Any preservation/backup of an active named volume must
be separately authorized and consistent under writer quiescence, exported to
independent retained storage with a manifest; retention inside Docker alone is
not a backup. Historical restoration remains separately ADR-gated. No backup,
retirement, volume creation, or recovery is performed by this refinement.

### Exact follow-on implementation boundary

The separate implementation slice is limited to:

1. `docker-compose.private-preview.yml`: define the external volume, replace
   the five inherited Chroma binds, add the missing chat-worker mount, and pin
   the common logical configuration for the six consumers above. Preserve all
   other mounts, services, profile activation, providers, and auth settings.
2. `tests/ops/test_private_preview_contract.py`: extend the existing Compose
   rendering contract with inert environment inputs; assert exact shared volume,
   external name, path, collection, `nocopy`, no host/anonymous alternative,
   unchanged optional profiles and unrelated mounts, and no default-local
   topology change. Cover environment attempts to redirect Chroma.

`docker-compose.yml`, `docker-compose.override.yml`, runtime-family Compose,
`scripts/ops/codexify_private_preview.sh`, `.env.private-preview.example`, the
secure environment, supported profiles, and runtime Python are read-only
context for that slice. If these two implementation files cannot meet the
contract, report the exact gap for a separately scoped task; do not expand it.
Static Compose rendering and contract tests must not contact live storage,
create volumes, or start services. This cleanly separates implementation from
live recovery: an absent external volume intentionally prevents activation.
No live retirement/recovery authorization is conveyed by implementation success.

### Frozen post-implementation proof order

```text
storage topology decision
    ↓
Compose/config implementation + static/topology tests
    ↓
writer quiescence
    ↓
historical preservation re-verification
    ↓
ADR-067 active-store retirement
    ↓
fresh named-volume initialization
    ↓
absence of historical Chroma panic
    ↓
backend /health + /health/chat
    ↓
queue/worker safe-start qualification
    ↓
matching Persona application-lineage qualification
    ↓
authenticated /api/persona-profiles proof
    ↓
authenticated browser save/readback
    ↓
periodic reconciliation restoration
```

Fresh initialization includes separately authorized empty-volume creation and
identity checks before supported-runtime backend initialization. Retirement
must remove the old bind from every active path before any new-store writer
starts. Preserve, retire, and fresh-initialize remain distinct states; the
original Tester follow-through above is not permission to bypass these preview
gates. A failed gate stops dependent work and retains the maintenance boundary.
Health is a bounded observation, not completion proof; unavailable worker
readiness remains an open gate, not permission to start queued work blindly.
No Persona browser proof, reconciliation resumption, or release claim follows
from freezing this decision alone.

---

*This ADR documents the governance decision only. No runtime mutation has been performed by this change.*
