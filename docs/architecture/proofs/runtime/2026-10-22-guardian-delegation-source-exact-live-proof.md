# Guardian Delegation — Source-Exact Live Proof — 2026-10-22

## Outcome

**BLOCKED** — at the mandatory credential preflight, and independently at the
source-exact bootability preflight.

No Guardian delegation was dispatched, no credential was registered, no image
was built for this proof, and no application file was modified. The two
blockers are recorded below with the exact evidence and the specific
prerequisite each one establishes.

A packaging qualification is not a delegated-execution qualification. This
report proves neither.

## Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| HEAD | `7f77c6d413a6325003d802ab64919e528fd278bf` |
| Working tree | clean |
| Foundational delegation commits | `19f6770d4`, `1dccb58b6`, `6d286bd6c`, `08fad9077`, `f14fb118e` — all ancestors of HEAD |
| Guardian repair commits | `9d2dae77f`, `cddee2bb6`, `a70ca1465`, `bd6b5e7a2`, `7f77c6d41` — all ancestors of HEAD |

The proof used a `git archive` extraction of this exact commit as the source
tree. No merge, rebase, reset, cherry-pick, or reconciliation of `main` was
performed, and the older canary tree — whose application files still carried
temporary repairs — was not used as the source.

## Blocker 1 — no conforming test credential exists (requirement 2)

This preflight is mandatory and precedes registering a credential, building an
image, or dispatching work. It fails.

Every DeepSeek key reachable from an authorized source was enumerated and
compared by equality only. **No value, prefix, suffix, or fingerprint is
recorded in this report.** Three distinct key values exist:

| Candidate | Canonical owner | Status in this proof |
|---|---|---|
| Repository `.env` | operator | **Disallowed.** Operator-owned; byte-identical to the operator's Pi auth-store entry, so one operator key under two names. |
| Repository `.env.tester` (and its 2026-08-18 backup, byte-identical) | operator | **Disallowed.** The previously invalid tester credential, already recorded as provider-invalid by the credential-provenance reconciliation. |
| Repository `.env.private-preview` | operator / deployment | **Disallowed.** The Private Preview deployment's own credential. |
| Tracked `.env.*.example` files | repository | Placeholders only — no usable key. |
| Previous canary row `ccr_0c143601f0294888b0e8cbd5bafd8b0f` | operator | **Disallowed.** It was minted from the operator's `.env`, so it inherits that key's ownership. |
| Ambient provider credential | ambient | **Disallowed.** |

There is therefore **no genuinely dedicated, provider-valid, authorized test
credential** available to this proof. No additional operator secret store was
searched for a substitute, and no provider request was made to re-test
candidate validity (a real provider call is a non-goal for this task).

A distinct key is not automatically account-owned, and registering one under an
account scope would be a mislabel, not an authorization. Under ADR-094 an
operator-owned credential may serve an account-scoped invocation only under a
separate, explicit operator grant with matching runtime authority; no such
grant exists for this proof.

**Required prerequisite:** a DeepSeek test credential issued for this
qualification, with recorded ownership, permitted model, funding route, a
restriction to this test, and a revocation disposition — **or** an explicit
ADR-094 operator grant plus the matching runtime authority. Until one exists,
no credential may be registered and no work may be dispatched.

## Blocker 2 — the exact committed source cannot boot (requirement 3)

This preflight also fails, independently of the credential.

At HEAD `7f77c6d41`, `guardian/db/models.py` defines **none** of the four
`MemoryRevision`, `MemoryReviewRevision`, `MemoryLifecycleRevision`, or
`MemoryPurgeTombstone`. The committed application code imports all four:

```
guardian/services/memory_purge.py:89
    from guardian.db.models import (
        MemoryLifecycleRevision,   # <-- absent on this branch
        MemoryPersonaLink,
        MemoryProvenance,
        MemoryPurgeTombstone,      # <-- absent on this branch
        MemoryRecord,
        MemoryReviewRevision,      # <-- absent on this branch
        MemoryRevision,            # <-- absent on this branch
    )
```

This is an **import-time** failure on the backend entrypoint's import graph —
not a route-registration or runtime-ordering question. The chain is:

```
guardian/guardian_api.py:519                    from guardian.routes import (..., memory_vault, ...)
  -> guardian/routes/memory_vault.py:72            from guardian.services.memory_vault_mutation import (...)
    -> guardian/services/memory_vault_mutation.py:41   from guardian.db.models import (MemoryLifecycleRevision,
                                                                                      MemoryReviewRevision,
                                                                                      MemoryRevision, ...)
    -> guardian/services/memory_purge.py:89               from guardian.db.models import (..., MemoryPurgeTombstone, ...)
```

`guardian/guardian_api.py` imports `memory_vault` at **module level**, so the
missing names break `import codexify.guardian_api` before any route is
registered and before any credential, queue, or dispatch path is reached. The
import was run against the **exact committed source**, mounted read-only with
no overlay and no patched application file, using only the already-built
runtime environment for its Python dependencies:

```
$ docker run --rm \
    -v <archive>/guardian:/app/guardian:ro \
    -v <archive>/backend:/app/backend:ro \
    ... --entrypoint sh codexify-backend-runtime:canary-git-20261020 -lc '
      [ -e /app/codexify ] || ln -s /app/guardian /app/codexify   # the image entrypoint step
      python3 -c "import codexify.guardian_api"'

BACKEND IMPORT: FAILED -> ImportError cannot import name 'MemoryLifecycleRevision'
                                    from 'guardian.db.models' (/app/guardian/db/models.py)
```

The same failure is reproduced by importing the route directly
(`guardian.routes.memory_vault` → `ImportError: cannot import name
'MemoryLifecycleRevision'`), and by the direct mapping import
(`from guardian.db.models import MemoryLifecycleRevision` → `ImportError`).

Migration readiness is not the problem: alembic reports a single head
(`f0d7c4b2a198`), and four committed migrations already create the affected
tables (`memory_revisions`, `memory_review_revisions`,
`memory_lifecycle_revisions`, `memory_purge_tombstones`). The branch carries the
**schema** but not the **ORM mappings** that own it. The same gap makes this
branch's own tests fail: `tests/migration/test_memory_lifecycle_revision_persistence_migration.py`
and `tests/services/test_memory_vault_lifecycle_transition.py` both import
`MemoryLifecycleRevision` from `guardian.db.models`.

The fact that `main` has since restored these mappings proves nothing about
this branch, and no mapping was copied from main, another worktree, or a prior
proof environment.

**Required prerequisite:** the feature branch must carry the
`MemoryRevision`, `MemoryReviewRevision`, `MemoryLifecycleRevision`, and
`MemoryPurgeTombstone` ORM mappings (and the migration/table alignment they
require) so that `guardian.services.memory_purge` and the backend entrypoint
import cleanly from the committed source alone.

**Scope of this prerequisite.** A symbol-level sweep of 1,184 application
modules against the committed source found exactly **four** names missing from
`guardian.db.models` — the four above — and no other missing import from that
module. The sweep was re-run against HEAD during receipt finalization and
reproduced the same four-name set. Restricting the sweep to *module-level*
imports (the ones that run at import time) leaves those four plus one
unrelated, pre-existing defect:
`guardian/chat/cli/main.py:22` imports `ImprintZero` from
`guardian/cli/imprint_zero_cli.py`, which defines `ImprintZeroCommand` at line
32. That module is referenced only by `guardian/tests/benchmark_startup.py` and
is **not** in the backend entrypoint's import graph, so it does not block boot;
it is recorded here so the next task does not conflate the two.

## Image identities and digests

No images were built for this proof: requirement 2 stops the run before
building. The images qualified by the immediately preceding Git-packaging
slice are recorded for continuity, and their application source was verified
against the evaluated commit:

| Image | Digest | Size |
|---|---|---|
| `codexify-backend-runtime:git-proof-a70ca1465` | `sha256:891cb0f57f77b6db6ac93e950c20f47ed79f7a00022726ab3d7bc64b158eb267` | 4.69 GB |
| `codexify-worker-coding-runtime:git-proof-a70ca1465` | `sha256:40e8b035e9b75729516180fd8825ceef85b540081db3b3634e1588ec1083e8e4` | 5.2 GB |

A file-level comparison of the backend image's `/app/guardian` and `/app/backend`
against the evaluated commit's trees showed **no production-source difference**;
the single differing file is `guardian/tests/agents/test_pi_readiness.py`, which
is test code and not runtime. The normal `:latest` tags were not rebuilt or
modified:

```
codexify-backend-runtime:latest       sha256:7a08e1defa4351c52e004b13af3d97d39a9d6fc1e5a0fb49914227fdfd853812
codexify-worker-coding-runtime:latest sha256:a3177274d0b5e90e4db762f6723b312ed57b6c1cbf2f2aaa69995ce9ab735229b
```

Git readiness for both images (version 2.47.3 at `/usr/bin/git`, synthetic
repository operations, `validate_git_working_tree_root()` accepting a synthetic
root) is recorded in
`docs/architecture/proofs/runtime/2026-10-22-guardian-git-runtime-packaging-proof.md`.

## Backend and worker readiness

Not reached for a source-exact runtime: no image was built for this proof and
the exact committed source cannot import the backend entrypoint. The Git
prerequisite itself was verified independently in the packaging slice and is
not the blocker here.

## Execution binding, permission posture, and lifecycle

Not reached. No intent was created, no approval established, no credential
resolved, no binding or posture resolved, no deployment specification
persisted, no dispatch prepared, and no `CodingExecutionTask` enqueued. Nothing
was inserted manually to bypass Guardian.

## Provider, model, and reasoning-effort observations

None. No provider request was made and no adapter was invoked. The canonical
runtime inputs this proof would have exercised — provider `deepseek`, model
`deepseek-v4-flash`, harness Pi, Guardian-authorized reasoning effort `off`,
and the explicit repository-root scope `"."` — are the ones established by
commit `cddee2bb6` and `a70ca1465` and are unchanged by this run.

## Result readback and filesystem mutation

None. No result was delivered to any Chat Thread, no coding-result artifact
was produced, and no repository was mutated.

## Environment containment and resource observations

- The Private Preview deployment was never rebuilt, restarted, redeployed, or
  written to. It served `GET /` → 200 and `GET /health` → 200 throughout.
- The `:latest` image tags were not modified, and no container was created
  from them.
- The only Docker activity was read-only inspection of existing images and
  containers running the committed source against an already-built runtime
  environment. No image was built, no network was created, and no volume was
  written.
- Docker VM headroom remained between 3.2 GB and 4.5 GB of 7.7 GB. No
  concurrent full-suite run was started in the shared VM.
- No credential was registered, no lease was issued, no attempt was
  dispatched, and no credential value, prefix, suffix, or fingerprint appears
  in this report.

## Known sandbox limitations (unchanged and still unproven)

The Git mutation guard remains **detective, not preventive**: it observes a
mutation after the fact and fails the attempt. Network and process isolation
are not provider-enforced by the coding worker. Neither is established by this
run, and no such claim is made here.

## Exact validation commands and outcomes

| Command | Outcome |
|---|---|
| `git status --short --branch` / `git rev-parse HEAD` | clean tree at `7f77c6d41` |
| `git merge-base --is-ancestor <commit> HEAD` for all ten commits | all present |
| `git archive HEAD …` → source tree | extracted; byte-identical to the commit, no overlay |
| `git ls-files` → tracked `.env*` inspection | example files only, placeholder values |
| equality comparison of the known DeepSeek key files | three distinct values; all disallowed |
| `import codexify.guardian_api` against the committed source | **ImportError: `MemoryLifecycleRevision`** |
| `import guardian.routes.memory_vault` against the committed source | **ImportError: `MemoryLifecycleRevision`** |
| `from guardian.db.models import MemoryLifecycleRevision` | **ImportError** |
| `python -m alembic -c backend/alembic.ini heads` | single head `f0d7c4b2a198` |
| re-run symbol sweep of 1,184 application modules against HEAD | same four missing names; no other missing `guardian.db.models` import |
| `git diff --check` / `git diff --name-only` | clean; only this receipt |

The repository-wide backend validation default (`pytest -v`) was **not run**:
the run blocked at the preflights, and a monolithic suite run in the shared
7.7 GB Docker VM is not required for this narrow proof and has already been
observed to threaten the Private Preview. The focused suites touched by the
preceding Guardian repairs were validated in the prior slices; this report
introduces no application change and therefore adds no new test surface.

## ADR impact and invariants

No ADR is modified, and none is expected. ADR-020, ADR-065, ADR-069,
ADR-077, ADR-093, and ADR-094 are unaffected by this run. Guardian remains the
sole authority over coding execution; no worker-level authority was added, no
provider or model selection changed, no permission scope changed, no
reasoning-effort authority changed, no credential authority changed, and no
duplicate execution or automatic re-dispatch was introduced — because nothing
was dispatched.

## Remaining blockers and next task

1. **A conforming test credential** (operator action): a dedicated,
   provider-valid DeepSeek key issued for this qualification with recorded
   ownership, permitted model, funding route, test-only restriction, and
   revocation disposition — or an explicit ADR-094 operator grant plus matching
   runtime authority.
2. **The missing ORM mappings** (code change on this branch): `MemoryRevision`,
   `MemoryReviewRevision`, `MemoryLifecycleRevision`, and
   `MemoryPurgeTombstone` must exist in `guardian/db/models.py`, with the
   migration/table alignment they require, so the backend imports from the
   committed source alone.

Both are outside this proof's authorized write surface, which is this report
alone, and **neither alone authorizes a dispatch**: a green boot without an
authorized credential still cannot run a task, and an authorized credential
against an unbootable backend still cannot reach one. They are independent and
can be pursued in parallel.

They are not equally hard. The credential is the harder of the two, because it
is an external operator grant that no in-repo change can supply. The ORM
mappings are a self-contained branch change that can be verified **on its own**
— a clean `import codexify.guardian_api` against the committed source proves
it, with no credential, no provider call, and no dispatch required — which makes
the mapping repair the independently verifiable first step, and the credential
the one that must be in hand before any live qualification can start.

**Confirmed:** source-exact Guardian delegation execution is **not proven**.
Conversational intake remains unavailable. Restart recovery remains unproven.
Provider-enforced sandbox isolation remains unproven. Beta release
qualification remains **HOLD**.
