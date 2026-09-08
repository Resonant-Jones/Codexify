# UMS-03H-R — Reconciled-Main Rebaseline Proof

- **Slice:** UMS-03H-R (rebaseline prerequisite for UMS-03H)
- **Date:** 2026-09-08
- **Execution lane:** Architecture-Impact
- **Task kind:** architecture revalidation / campaign prerequisite proof
- **Starting HEAD:** `091216aefa1af970728bda87702147bf1a76e174`
- **Branch:** `main`
- **UMS-03G prerequisite:** `774d71ca0bdf219c714ab2ad2c6f2db837a7081e`
- **UMS-03G ancestry result:** `git merge-base --is-ancestor 774d71ca 091216aef` → exit 0
- **Local `origin/main` ancestry result:** `git merge-base --is-ancestor origin/main 091216aef` → exit 0
- **Ahead/behind:** `0 0` — local `main` is at the same commit as the local `origin/main` tracking ref
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5` → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (untouched)
- **Pi fixture:** `tests/pi/fixtures/fake_pi_package/package.json` remains dirty + unstaged (untouched)

## Preflight

```text
BRANCH:                    main
HEAD:                      091216aefa1af970728bda87702147bf1a76e174
INDEX:                     empty
MERGE/REBASE:              none
UMS-03G (774d71ca) → HEAD: ancestor (exit 0)
HEAD → origin/main:        ancestor (exit 0)
AHEAD/BEHIND (HEAD..origin/main): 0 / 0
ALEMBIC HEAD:              f6b0d3e8c5a2
```

The reconciled `main` is preserved unchanged. No reset, revert, or
cherry-pick was performed.

## Why this rebaseline is necessary

UMS-03H was authorized immediately after UMS-03G. Between the
UMS-03G commit (`774d71ca`) and the start of this task, the local
operator intentionally reconciled local `main` with `origin/main`,
producing 18 intervening commits that span runtime code, tests,
docs, and merge commits. The UMS-03H spec's non-impact gate
correctly fired; the rebaseline resolves it without discarding
valid history.

## Intervening commit inventory (18 commits)

```text
091216aef  Reconcile AxisNode main with origin/main                 (merge)
bd5be33ef  Merge pull request #794 .../fix/restore-current-state-release-classes  (merge)
a67b99459  Reverify current-state architecture DLG metadata
0ef78e03d  Restore current-state release classes
1ce3a735e  Merge pull request #793 .../fix/persist-ce-l1-frozen-objective         (merge)
cfdfa365a  Persist frozen CE-L1 objective control
a5840b751  Generalize Pi model delegation
161f18586  docs: refresh weekly current-state override
76b9b3613  Publish 2026-09-06 daily dev log
e93e2a886  Bridge Tester worker diagnosis to main
db7f45c96  Merge pull request #792 .../fix/reverify-architecture-dlg-three-node   (merge)
c8287b952  Reverify canonical architecture DLG metadata
55e5475a4  Harden ShareSheet async interaction handling
24ec43e7f  docs: refresh weekly current-state override
f82d3b702  Publish 2026-09-05 daily dev log
8aa6acea5  Merge pull request #791 .../feature/persona-studio                 (merge)
73e988478  Execute accepted Persona snapshot
8031b0bb8  Snapshot Persona selection at chat acceptance
```

Merge commits: **5** (`091216aef`, `bd5be33ef`, `1ce3a735e`,
`db7f45c96`, `8aa6acea5`).

### Classification (best-fit bucket per commit)

| Bucket | Count | Commits |
| --- | --- | --- |
| A. governance / docs | 7 | `161f18586`, `76b9b3613`, `24ec43e7f`, `f82d3b702`, `a67b99459`, `c8287b952`, `e93e2a886` (bridge proof) |
| B. runtime | 3 | `0ef78e03d`, `8031b0bb8`, `73e988478` (Persona snapshot plumbing) |
| C. persistence / schema | 0 | none |
| D. retrieval / memory | 0 | none |
| E. Personal Fact / identity | 0 | none |
| F. provider / completion | 1 | `55e5475a4` (ShareSheet async hardening) |
| G. tests / proof infrastructure | 1 | `cfdfa365a` (CE-L1 frozen objective persistence) |
| H. unrelated product / UI / tooling | 1 | `a5840b751` (Pi model delegation generalization) |
| M. merge commits | 5 | `091216aef`, `bd5be33ef`, `1ce3a735e`, `db7f45c96`, `8aa6acea5` |

A commit may occupy more than one class; counts reflect primary
classification. None of the 18 commits touches UMS runtime,
persistence, compatibility, semantic species, protocol tokens,
or canonical-memory consumers.

## Complete changed-path inventory (28 files)

```text
docs/DEV_LOG/2026-09-06/Dev Log - 2026-09-06.md
docs/architecture/00-current-state.md
docs/architecture/README.md
docs/architecture/chat-runtime-contract.md
docs/architecture/completion_pipeline.md
docs/architecture/pi-invocation-boundary-contract.md
docs/architecture/proofs/runtime/2026-09-05-tester-worker-import-diagnosis-lineage-bridge.md
docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json
docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json
docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json
frontend/src/components/share/ShareSheet.test.tsx
frontend/src/components/share/ShareSheet.tsx
guardian/cognition/system_profiles/resolver.py
guardian/core/chat_completion_service.py
guardian/tasks/types.py
guardian/tests/test_persona_profile_runtime.py
guardian/tests/workers/test_chat_worker_provider_resolution.py
guardian/workers/chat_worker.py
skills/pi-deepseek-delegation/SKILL.md
skills/pi-deepseek-delegation/agents/openai.yaml
skills/pi-deepseek-delegation/references/setup.md
skills/pi-deepseek-delegation/scripts/pi_deepseek_delegate.sh
skills/pi-deepseek-delegation/tests/test_pi_deepseek_delegate.py
tests/cognition/test_system_profile_resolver.py
tests/core/test_chat_completion_enqueue_service.py
tests/pi/fixtures/ce_l1/frozen_objective_v1.txt
tests/pi/test_ce_l1_frozen_objective.py
tests/tasks/test_chat_completion_profile_snapshot.py
```

### UMS-relevant subset

```text
docs/architecture/00-current-state.md
docs/architecture/README.md
guardian/cognition/system_profiles/resolver.py
guardian/core/chat_completion_service.py
guardian/tasks/types.py
guardian/tests/test_persona_profile_runtime.py
guardian/tests/workers/test_chat_worker_provider_resolution.py
guardian/workers/chat_worker.py
```

The UMS-implementation surface is **not in this list**:

```text
guardian/core/memory_compatibility.py     UNCHANGED
guardian/protocol_tokens.py               UNCHANGED
guardian/db/models.py                     UNCHANGED
guardian/db/migrations/                   UNCHANGED
tests/core/test_memory_compatibility.py   UNCHANGED
docs/architecture/unified-memory-store-contract.md   UNCHANGED
docs/Campaign/unified-memory-store/README.md          UNCHANGED
docs/architecture/adr/adr-index.md        UNCHANGED
```

## Current ADR-083 / ADR-084 reconciliation

```text
ADR-083:
  current title    : Unissued / retired historical MemoryOS slot
  current status   : tombstone entry only (no accepted document)
  scope            : none (no governing authority)
  authority owned  : none
  runtime state    : no retention doctrine; no source authority
  persistence impl : none
  current evidence : docs/architecture/adr/adr-index.md lines 248–251
                     docs/architecture/00-current-state.md line 128

ADR-084:
  current title    : Unified Account-Owned Memory Store
  current status   : accepted (frozen)
  scope            : canonical UMS memory architecture
  authority owned  : UMS authority (account/Project scope, persona
                     attribution, three semantic species, canonical
                     persistence substrate)
  current evidence : docs/architecture/adr/adr-index.md lines 252–258
                     docs/architecture/unified-memory-store-contract.md
```

### Relationship verdict

```text
ORTHOGONAL
```

ADR-083 carries no governing authority at the canonical registry
level; ADR-084 is the sole controlling UMS memory ADR. The
prior UMS-03F/G interpretation (ADR-083 unissued/retired,
ADR-084 controlling) remains current.

The pre-rebaseline conditional "if current ADR-083 changes UMS
retention, source authority, activation, provenance, imported-
source authority, canonical persistence, or compatibility
semantics" was checked against the canonical registry. It did
not materialize. The conditional ADR-083 retention interaction
check in Requirement #10 therefore returns:

```text
Does retention decide how long source/evidence material exists?
  N/A — no retention doctrine issued
Does retention decide whether something becomes canonical memory?
  N/A — no retention doctrine issued
Does retention grant review or activation authority?
  N/A — no retention doctrine issued
Does retention alter account ownership / Project scope / Persona?
  N/A — no retention doctrine issued
Does retention alter provenance requirements?
  N/A — no retention doctrine issued
Does retention require UMS compatibility coverage?
  N/A — no retention doctrine issued
```

## UMS invariant re-check

The following UMS-03A / §4.13 invariants were re-checked against
current canonical governance:

```text
Account owns.                              UNCHANGED
Project scopes.                            UNCHANGED
Persona attributes.                        UNCHANGED
User approves.                             UNCHANGED
Pinning prioritizes.                        UNCHANGED
Holding suspends decay.                    UNCHANGED
Router widens only on explicit user intent. UNCHANGED
Every borrowed memory keeps its attribution. UNCHANGED
one canonical envelope                      UNCHANGED
three semantic species                      UNCHANGED
legacy compatibility remains projection-only UNCHANGED
canonical tables are not silently authoritative UNCHANGED (see below)
imports / provenance do not mint activation  UNCHANGED
```

No invariant has been superseded by current reconciled
governance.

## UMS implementation drift

| Surface | Verdict |
| --- | --- |
| `guardian/core/memory_compatibility.py` | `UNCHANGED` |
| `tests/core/test_memory_compatibility.py` | `UNCHANGED` |
| `guardian/protocol_tokens.py` | `UNCHANGED` |
| `guardian/db/models.py` | `UNCHANGED` |
| `guardian/db/migrations/` | `UNCHANGED` |
| `docs/architecture/unified-memory-store-contract.md` | `UNCHANGED` |
| `docs/Campaign/unified-memory-store/README.md` | `UNCHANGED` |
| `docs/architecture/adr/adr-index.md` | `UNCHANGED` |

No `CHANGED_RELEVANT` surfaces.

## Legacy memory-authority drift

| Source | Verdict |
| --- | --- |
| `memory_entries` | UNCHANGED — schema, columns, CHECK constraints, indexes, FKs all identical to UMS-03G baseline |
| `personal_facts` | UNCHANGED — schema, columns, CHECK constraints, indexes all identical |
| `personal_fact_evidence` | UNCHANGED — schema and column semantics identical |
| `personal_fact_revisions` | UNCHANGED — schema and column semantics identical |

No memory-authority, status vocabulary, `is_active` meaning,
evidence authority, revision authority, retrieval eligibility,
or provenance rule changed.

## Newly admitted durable memory authority

`Base.metadata.tables` was re-inventoried on the reconciled
`main`. Memory-bearing durable tables:

```text
memory_entries              (legacy UMS-03E compatibility)
memory_records              (UMS-03D canonical substrate, non-authoritative)
memory_provenance           (UMS-03D canonical substrate, non-authoritative)
memory_persona_links        (UMS-03D canonical substrate, non-authoritative)
personal_facts              (legacy UMS-03F/G compatibility)
personal_fact_evidence      (subordinate provenance to personal_facts)
personal_fact_revisions     (historical lineage of personal_facts)
persona_profile_revisions   (Persona Profile audit lineage, per ADR-082)
agent_run_artifacts         (agent run output, NOT memory authority)
```

The canonical UMS substrate tables and the legacy compatibility
sources are unchanged. `persona_profile_revisions` is
PersonaProfile audit lineage per ADR-082 (different from
`personal_fact_revisions`). `agent_run_artifacts` is agent-run
output, not a user-knowledge memory authority.

No new durable memory authority was introduced.

## Canonical persistence runtime-consumer inspection

`rg -l 'MemoryRecord\b|MemoryProvenance\b|MemoryPersonaLink\b' guardian/` returned only `guardian/db/models.py`
(the class definitions themselves). No runtime file outside the
class definitions imports the canonical UMS substrate classes.
The canonical tables remain structural and non-authoritative at
runtime, exactly as the UMS-03D proof established.

## Compatibility-projection runtime-consumer inspection

`rg -l 'read_memory_entry_projection|read_verified_personal_fact_projection|read_candidate_personal_fact_projection|MemoryCompatibilityProjection' guardian/` returned only `guardian/core/memory_compatibility.py` (the
implementation module itself, which defines the symbols and uses
them in the public reader functions). No consumer exists under:

```text
guardian/context/             NOT USED
guardian/memoryos/            NOT USED
guardian/workers/             NOT USED
guardian/core/chat_completion_service.py
                              NOT USED (chats not affected by UMS)
```

`tests/core/test_memory_compatibility.py` is the only test
consumer. Documentation references are not runtime consumers.

The pre-rebaseline state holds exactly: compatibility projections
are definition + test + documentation; they have no live
runtime consumer.

## Compatibility test baseline on reconciled main

```text
tests/core/test_memory_compatibility.py  52 passed in 0.63s
  0 failed
  0 errors
  0 skipped
```

The exact pre-rebaseline count (52) is preserved. No semantic
regression, no skip, no error.

## Adjacent UMS regression on reconciled main

```text
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.47s
```

Pre-rebaseline count (46) is preserved.

## Alembic topology

```text
f6b0d3e8c5a2 (head)
```

Single head, unchanged. No post-UMS-03G migration was added.
No UMS-affecting migration exists after the canonical
persistence slice.

## Rebaseline verdict

```text
REBASELINED_WITH_ORTHOGONAL_MAINLINE_CHANGES
```

Reasoning:

- UMS-03G remains in current `main` ancestry.
- ADR-083 / ADR-084 relationship is `ORTHOGONAL` (current
  registry still says ADR-083 is unissued/retired; ADR-084 is
  the sole controlling UMS memory ADR).
- UMS implementation, persistence, semantic-species, and
  protocol-token surfaces are all UNCHANGED.
- Legacy memory-authority, evidence, and revision schemas are
  UNCHANGED.
- No new durable memory authority was introduced.
- Canonical tables remain structural and non-authoritative at
  runtime.
- Compatibility projections have no live runtime consumer.
- 52/52 compatibility tests pass with zero skips.
- 46/46 adjacent UMS regressions pass.
- Alembic head unchanged at `f6b0d3e8c5a2`.

The post-reconciliation mainline work is orthogonal to UMS:

- `PersonaSelectionSnapshot` and the persona profile snapshot
  flow are ADR-082 / Persona Studio execution work, not UMS.
- The system-profile resolver, chat completion service, and
  chat worker changes are the wiring for that persona snapshot
  flow.
- The ShareSheet async hardening, Pi model delegation, CE-L1
  frozen objective persistence, and Tester-worker bridge are
  orthogonal to UMS authority.
- The knowledge-graph nodes and the doc refreshes reflect the
  same architectural state the UMS contract already encodes.

UMS-03H is reauthorized to resume from current reconciled
`main` without any UMS-contract or implementation change.

## What UMS-03H may resume

UMS-03H is reauthorized to execute as previously written: prove
that every admitted legacy durable memory source/state has a
projection, a subordinate lineage classification, or an explicit
contractual exclusion. UMS-03H may not introduce any new adapter,
any code change, any ORM/migration change, or any retrieval
change. The rebaseline is the only artifact of UMS-03H-R; the
coverage closure is a separate slice and must be authorized by
its own task spec.

## ADR impact

- ADR-081 unchanged.
- ADR-082 unchanged.
- ADR-083 unchanged (still unissued/retired per the canonical
  registry).
- ADR-084 unchanged.
- UMS contract unchanged.
- No new ADR.
- No new architecture decision.

## Confirmed non-claims

- `main` was not reset, reverted, or rewritten.
- The reconciliation merge (`091216aef`) was preserved.
- No production code was changed by UMS-03H-R.
- No test was changed by UMS-03H-R.
- No ORM model or migration was changed by UMS-03H-R.
- No retrieval, retention, or export/restore behavior was
  changed by UMS-03H-R.
- The UMS-03E recovery ref `recovery/ums03e-conflated-71fd9f4d5`
  is preserved unchanged.
- The Pi fixture remains untouched and unstaged.
- Nothing was pushed or merged.

## Required successful state

```
UMS-03D: CLOSED
UMS-03E: CLOSED
UMS-03F: CLOSED
UMS-03G: CLOSED
UMS-03H-R RECONCILED-MAIN REBASELINE: CLOSED
UMS-03H LEGACY MEMORY COMPATIBILITY COVERAGE: AUTHORIZED TO RESUME
UMS-03: OPEN
UMS-03I: NOT AUTHORIZED
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

REPOSITORY BASELINE:
  reconciled main is preserved
  UMS-03G remains in ancestry
  origin/main reconciliation is accepted
  post-UMS mainline changes have been explicitly revalidated

GOVERNANCE:
  current ADR-083 meaning is recorded (still unissued/retired)
  ADR-084 UMS authority is explicitly revalidated
  no stale ADR-083 disposition assumption survives implicitly

UMS AUTHORITY:
  legacy-memory authority is unchanged
  compatibility projections remain read-only
  canonical memory tables remain non-authoritative
  no live compatibility consumer exists

NEXT:
  resume UMS-03H coverage closure from reconciled current main
```
