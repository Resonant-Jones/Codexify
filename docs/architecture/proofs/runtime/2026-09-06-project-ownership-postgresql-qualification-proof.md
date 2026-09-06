# UMS-01Q Project Ownership PostgreSQL Qualification Proof

Date: 2026-09-06

Status: **PASSED**

## Qualification identity

- Starting implementation checkpoint: `56eab08c30d09f0ae4c94d2903be29638b3d4e0c`
- UMS-01R: `caa875f9b5ca3807f1ec541dc3ab0c97d837ced1`
- UMS-01Q-R1: `a21deb59666439ff0a8c3536b58663a697df6b82`
- UMS-01Q-R2: `086efa26efe382a1ec35bd24026f6ec584b5ce03`
- UMS-01Q-R3: `56eab08c30d09f0ae4c94d2903be29638b3d4e0c`

## Environment and execution

A single explicitly disposable PostgreSQL container, `postgres:17`, was
started as `codexify-ums01q-final-postgres`, bound to loopback port 55437.
The authority database was `codexify_ums01q`; a distinct empty target database
was `codexify_ums01q_target`. PostgreSQL reported version **17.11** on
`aarch64-unknown-linux-gnu`. Credentials are intentionally not recorded.

No live, private-preview, production, persistent local user-bearing, or other
non-disposable database was contacted.

## Proof matrix

| Gate | Result |
| --- | --- |
| R3 focused ORM metadata contract | **19 passed, 0 failed, 0 errors, 0 skipped** |
| R1 uploaded-document migration regression | **5 passed, 0 failed, 0 errors, 0 skipped** |
| Persona/UMS four-file PostgreSQL suite | **33 passed, 0 failed, 0 errors, 0 skipped** (4 + 2 + 5 + 22) |
| Generic PostgreSQL migration smoke | **1 passed, 0 failed, 0 errors, 0 skipped** |
| Project ownership runtime regressions | **47 passed, 0 failed** |

The Persona/UMS suite executed Persona manifest/binding (4), Persona thread
revision (2), UMS-01A convergence (5), and UMS-01B reconciliation (22).
Fail-closed cases executed their expected failure assertions. The generic
migration smoke did not report the R3 unexpected-table failure.

## Alembic replay and topology

A direct `upgrade head` on the empty target succeeded and emitted no
`project_ownership_reconciliation_unresolved` event. `alembic current` reported
`d4e8f1a2b6c9 (head)`. The clean-replay query returned **0 Project rows**, so
no synthetic `General` Project or legacy-`local` owner was created.

A second `upgrade head` succeeded as a no-op and `current` remained
`d4e8f1a2b6c9 (head)`, with no schema error or additional migration state.
Static topology reported exactly one head:

```text
d4e8f1a2b6c9 (head)
```

The final Persona → UMS tail remained linear:

```text
b2c8d0e3f5a7
    ↓
c3d9e1f4a6b8
    ↓
d4e0f2a5b7c9
    ↓
c3d9e4f6a8b1
    ↓
d4e8f1a2b6c9
```

## Boundaries and invariant check

Qualification was proof-only. No migration, ORM, runtime, route, or test
source changed; ThreadSpace metadata remains persistence-only and no
ThreadSpace runtime or release behavior was activated. Project ownership
remains solely `projects.user_id`; names and `system_role` were not treated as
ownership evidence, and no fallback or synthetic owner was introduced.
Revision IDs and topology are unchanged. ADR-076, ADR-081, ADR-082, and
ADR-084 are unchanged and remain governing authority. ADR-055 remains proposed.

The disposable PostgreSQL container and databases were destroyed after the
run, and no credential file or secret was retained.

## Documentation and decision

Documentation validation passed with:

```text
.venv/bin/python scripts/validate_docs.py
```

The task-owned diff check passed for the three authorized documentation files.

Therefore:

```text
UMS-01Q POSTGRESQL QUALIFICATION: PASSED
UMS-01 CAMPAIGN GATE: CLOSED
UMS-01: CLOSED
UMS-02: AUTHORIZED TO START
```

This proof does not claim production or private-preview migration
qualification, all historical-database upgrade paths, full Unified Memory
implementation, UMS-02 implementation, or ThreadSpace runtime/release support.
The overall Unified Memory Campaign remains open pending its later packets.
