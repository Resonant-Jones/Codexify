# 2026-09-08 Canonical-Main DLG ADR-053 Retirement and ADR-083 Renumber Reconciliation Proof

## Status

- Architecture-governance receipt (NOT a runtime proof).
- No CE-L1 claim is made in this receipt.
- The repair executes an already-approved human disposition; it does not invent, broaden, or revisit that disposition.

## Frozen canonical base

- `SOURCE_BASE_SHA=091216aefa1af970728bda87702147bf1a76e174`
- Source canonicalization parent SHA: `091216aefa1af970728bda87702147bf1a76e174`
- Source canonicalization commit SHA: `7b8a0239707f66dfb2aebc40e9fc6566d3d790bb`
- Proof commit SHA: `<this commit>`

## Human disposition contract — implemented verbatim

Three human dispositions, restated in substance:

1. **ADR-053**: The Node-Hosted Room Access Boundary (`docs/architecture/adr/053-node-hosted-room-access-boundary.md`) **retains ADR-053**. The historical ThreadSpace/WhisperMesh artifact at `docs/architecture/adr/053-threadspace-whispermesh-managed-service-boundary.md` is the stale duplicate of the ThreadSpace/WhisperMesh decision now represented at ADR-055; it is retired outside the active numeric ADR namespace with provenance preservation.
2. **ADR-076 / ADR-083**: Archive Before Delete and Built-In Project Roles (`docs/architecture/adr/076-archive-before-delete-and-built-in-project-roles.md`) **retains ADR-076** unchanged. Round-Trip-Stable Governed-Schema Equivalence is renumbered from `docs/architecture/adr/076-round-trip-stable-governed-schema-equivalence.md` to `docs/architecture/adr/083-round-trip-stable-governed-schema-equivalence.md`. Canonical number after this task: **ADR-083**. Semantic status, architecture meaning, and governed-schema equivalence contract remain unchanged.
3. **DLG hash repair**: The three previously classified stale canonical DLG node/source pairs are refreshed in-place so the existing 10-node corpus validates at `DLG_NODE_COUNT=10` and `DLG_SOURCE_HASH_MATCH_COUNT=10`. No new DLG node is created for ADR-053, ADR-076, or ADR-083.

## Source canonicalization — exact paths

### ADR-053 retention

- Retained (retains ADR-053): `docs/architecture/adr/053-node-hosted-room-access-boundary.md`
- Stale duplicate original path: `docs/architecture/adr/053-threadspace-whispermesh-managed-service-boundary.md`
- Retired stale 053 archive path: `docs/architecture/adr/retired/053-threadspace-whispermesh-managed-service-boundary.md`
- Canonical ThreadSpace/WhisperMesh decision (retains ADR-055): `docs/architecture/adr/055-threadspace-whispermesh-managed-service-boundary.md`

The retired file has a markdown-HTML-comment retirement / provenance notice prepended to its historical body. The historical body bytes are preserved below the notice. The file is no longer in the active numeric ADR namespace; the validator's collision scan filters by `Path(line).parent.as_posix() == "docs/architecture/adr"`, so the archived subdirectory path is correctly excluded from the scan.

### ADR-076 / ADR-083

- Retained (retains ADR-076 unchanged): `docs/architecture/adr/076-archive-before-delete-and-built-in-project-roles.md`
- Old Round-Trip ADR-076 path: `docs/architecture/adr/076-round-trip-stable-governed-schema-equivalence.md`
- New Round-Trip ADR-083 path: `docs/architecture/adr/083-round-trip-stable-governed-schema-equivalence.md`

Inside the moved 083 file: the heading was changed from ADR-076 to ADR-083; the `Date` line records the renumbering; a markdown-blockquote renumbering-provenance note was inserted between the heading block and the `## Context` section, recording the historical ADR-076 path, the new ADR-083 path, the renumbering date 2026-09-08, the disposition authority, and the explicit preservation of the retained `076-archive-before-delete-and-built-in-project-roles.md` ADR. The historical body, the Accepted status, the architecture meaning, the governed-schema equivalence contract, the evidence posture, and all architecture-release claims are preserved unchanged.

`ADR_076_ARCHIVE_BEFORE_DELETE_RETAINED=true` — the file is byte-identical to the frozen base (verified via `git show SOURCE_BASE_SHA:docs/architecture/adr/076-archive-before-delete-and-built-in-project-roles.md | diff - <file>` returning no output).

### ADR index

`docs/architecture/adr/adr-index.md` was updated so that:

- Node-Hosted Room Access Boundary remains ADR-053.
- ThreadSpace/WhisperMesh canonical entry remains ADR-055.
- The stale historical 053 ThreadSpace/WhisperMesh artifact is NOT represented as a second active ADR-053 entry in the index.
- Archive Before Delete / Built-In Project Roles remains ADR-076.
- Round-Trip-Stable Governed-Schema Equivalence becomes ADR-083 with link target `083-round-trip-stable-governed-schema-equivalence`; status remains Accepted.
- The prior "ADR-083 — Unissued / retired historical MemoryOS slot" block was replaced with a compact cross-reference to the new ADR-083 entry, recording the supersession of the prior reservation, the unaffected posture of ADR-082 and ADR-084, and the renumbering date.

`docs/architecture/00-current-state.md` and `docs/architecture/README.md` were NOT edited in this commit. Their canonical source bytes are authoritative and contain no current/normative reference to the moving ADR paths that required semantic update.

`CURRENT_STATE_SOURCE_EDIT_COUNT=0`
`KB_ENTRYPOINT_SOURCE_EDIT_COUNT=0`

## Reference-closure disposition

The pre-edit reference scan classified the following:

- Class B (historical proof, do NOT rewrite): `docs/architecture/proofs/2026-08-09-dlg-phase4b-adr-number-collision-human-adjudication.md`, `docs/architecture/proofs/2026-08-08-dlg-architecture-control-plane-phase0-inventory.md`, `docs/architecture/proofs/2026-08-08-dlg-phase4a-adr-number-collision-canonicalization-review.md`, `docs/architecture/proofs/runtime/2026-09-03-private-preview-live-alembic-upgrade-proof.md`, `docs/architecture/proofs/2026-08-28-round-trip-stable-governed-schema-equivalence-proof.md`. These files remain byte-identical to the frozen base; their historical references to `053-threadspace-whispermesh-managed-service-boundary` and `076-round-trip-stable-governed-schema-equivalence` remain true as historical records of the prior state.
- Class C (generated DLG projection, do NOT hand-edit): `docs/knowledge-graph/generated/collisions.json`. Remains unchanged in this commit; the projection set is deliberately not regenerated as part of this task.

`EXISTING_HISTORICAL_PROOF_MUTATION_COUNT=0`
`GENERATED_DLG_EDIT_COUNT=0` (after the source-canonicalization commit; the subsequent DLG-metadata commit does not touch the generated directory either)

## DLG metadata repair — scope

The DLG metadata repair commit (Commit 3, on top of this proof commit) refreshes the three existing canonical DLG node records:

- `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json`
- `docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json`
- `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json`

It does NOT create any new DLG node for ADR-053, ADR-076, or ADR-083. The 10-node DLG corpus is preserved.

`NEW_DLG_NODE_COUNT=0`

For each of the three existing nodes, the refresh:

- Computes the SHA-256 of the exact current UTF-8 source bytes referenced by the node's `path`.
- Sets `content_hash` to that exact SHA-256.
- Sets `freshness.verified_commit` to the source-canonicalization commit SHA.
- Sets `freshness.verified_at` to one shared current UTC ISO-8601 timestamp recorded in the DLG-metadata commit.
- Updates `freshness.reason` minimally so the reason accurately reflects what was re-reviewed; in particular, the existing ADR-index node's `freshness.reason` text describes the ADR-053 and ADR-076 numeric collisions as remaining — that statement becomes false after the source canonicalization, so it is updated to a state consistent with the new canonical corpus.
- Keeps `freshness.state=current`.
- Preserves `document_id`, `path`, `kind`, `authority_class`, `authority_scopes`, `relations`, `retrieval_policy`, `owners`, `governing_adr_posture`, and release semantics.

## Non-repair confirmations

This proof confirms the following explicit non-changes:

- No historical proof file under `docs/architecture/proofs/**` was modified. The single new file added in this proof commit is `docs/architecture/proofs/2026-09-08-dlg-adr-053-retirement-and-083-renumber-reconciliation-proof.md` itself, which is the new architecture-governance receipt explicitly authorized by the canonical-main DLG disposition task.
- No file under `tests/config/**` or any supported profile / configuration source was modified.
- No file under `docs/knowledge-graph/generated/**` was modified or committed.
- No file under `codex_runner/`, `guardian/`, or `frontend/` was modified.
- No PR #797 commit (branch `fix/guardian-required-tool-selection`, head `8228bc45ff18b49493f183a7915287200de9be09`, eight commits) was modified.
- No supported profile was modified.
- No new DLG canonical node was created.
- No DLG schema was modified.
- No new ADR number outside the human disposition contract was allocated; specifically, no ADR-085 or any other trailing number was introduced.
- No provider invocation, no Pi readiness, no OAuth action, no credential inspection, no live Executor, no CE-L1 control, and no new live budget were performed.
- No runtime, Guardian, Campaign Engine, Pi, or vendor code was modified.

## Required closeout tokens

- `STALE_053_RETIREMENT=PASS`
- `STALE_053_PROVENANCE_PRESERVED=true`
- `ADR_076_ARCHIVE_BEFORE_DELETE_RETAINED=true`
- `ADR_076_ROUND_TRIP_OLD_PATH_ABSENT=true` (from the active direct-root ADR namespace after `git mv`)
- `ADR_083_ROUND_TRIP_NEW_PATH_PRESENT=true`
- `ADR_083_RENUMBER=PASS`
- `ADR_083_STATUS=Accepted`
- `DLG_NODE_COUNT=10`
- `NEW_DLG_NODE_COUNT=0`
- `DLG_SOURCE_HASH_MATCH_COUNT=10` (after Commit 3)
- `ADR_NUMBER_COLLISION_COUNT=0` (after Commit 3)
- `CONTENT_HASH_MISMATCH_COUNT=0` (after Commit 3)
- `DOCUMENT_ID_COLLISION_COUNT=0`
- `GENERATED_DLG_EDIT_COUNT=0`
- `EXISTING_HISTORICAL_PROOF_MUTATION_COUNT=0`
- `SUPPORTED_PROFILE_EDIT_COUNT=0`
- `TEST_CONFIG_EDIT_COUNT=0`
- `PR_797_MUTATION_COUNT=0`
- `PROVIDER_BACKED_INVOCATION_COUNT=0`
- `PROVIDER_REQUEST_COUNT=0`
- `LIVE_EXECUTOR_RUN_CALL_COUNT=0`
- `REAL_PROVIDER_SESSION_PROMPT_COUNT=0`
- `PI_READINESS_PROBE_COUNT=0`
- `OAUTH_LOGIN_COUNT=0`
- `OAUTH_LOGOUT_COUNT=0`
- `MANUAL_TOKEN_REFRESH_COUNT=0`
- `DIRECT_OPERATOR_CREDENTIAL_INSPECTION_COUNT=0`
- `NEW_LIVE_CONTROL_COUNT=0`
- `NEW_LIVE_BUDGET_COUNT=0`
- `NEW_SELECTION_REPAIR_LIVE_BUDGET=NOT_AUTHORIZED`

## Required campaign state preservation

`SOL_ATTEMPT_BUDGET=SPENT`, `LUNA_COMPARISON_BUDGET=SPENT`, `SPARK_COMPARISON_BUDGET=SPENT`, `ANTHROPIC_CONTROL_BUDGET=SPENT`, `NEW_ANTHROPIC_CONTROL_BUDGET=SPENT`, `NEW_ANTHROPIC_REATTEMPT_BUDGET=SPENT`, `ORIGINAL_CONTROL_REUSABLE=false`, `ANTHROPIC_OPERATOR_AUTH_READINESS=PASS_PROVIDER_FREE`, `CE_L1_REQUIRED_MUTATION_SELECTION_GAP=PROVEN_PROVIDER_FREE`, `GUARDIAN_PI_REQUIRED_TOOL_SELECTION_REPAIR=PASS_PROVIDER_FREE_LOCAL`, `CE-L1=OPEN`, `LIVE_EXECUTOR_PROVEN_CANONICAL=NOT_EMITTED`, `SINGLE_TASK_SUPERVISED_USABLE=NOT_EMITTED`, `SOURCE_THREAD_READBACK=NOT_PROVEN`, `NEW_SELECTION_REPAIR_LIVE_BUDGET=NOT_AUTHORIZED`.

## Next gate

The DLG metadata refresh (Commit 3) follows on top of this proof commit. The post-DLG-metadata validator output is recorded in the canonical revalidation closeout.
