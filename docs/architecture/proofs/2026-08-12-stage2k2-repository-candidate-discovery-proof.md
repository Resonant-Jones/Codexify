# Stage 2K.2 Repository Candidate Discovery Proof

## Date

2026-08-12

## Verdict

`PASS` — the bounded internal discovery seam and its final current-main
architecture validation are complete. The unrelated DLG source-hash drift was
repaired as metadata integrity only; no discovery, authority, runtime, or
release semantics changed. This slice does not establish import, Project,
binding, Workspace, tool, model, provider, or supported-runtime behavior.

## Diagnostic Outcome

`STAGE2K2_ARCHITECTURE_VALIDATION_CLOSED`

## Base Commit

Task-start `origin/main`:
`1ecc9dc386a52c0a008f5528eef598b3cb0d6249`.

During final validation, current main advanced only with
`abaf6141e39e8d93ae1bc34fcd84a35f023e18d4` (`docs: refresh weekly
current-state override`), changing `00-current-state.md` and `README.md`.
It did not alter ADR-065, the repository-onboarding authority contract,
Stage 2K.1 authority, binding semantics, migrations, or Git validation. The
single Stage 2K.2 commit was therefore rebased onto that final parent.

## Branch/Worktree

- Branch: `codex/stage2k2-repository-candidate-discovery`
- Worktree: `/private/tmp/codexify-stage2k2-repository-candidate-discovery`

## Governing ADRs

- ADR-065, Guardian-Managed Repository Onboarding Boundary — primary.
- ADR-061, Capability-Oriented Mesh Architecture — an observation does not
  create an authorized capability or expose infrastructure to a consumer.
- ADR-005, account scoping and user isolation.
- ADR-020 and ADR-024, Guardian-issued filesystem scope and the distinction
  between source evidence and authorized access.

## ADR Impact

`Aligned with existing ADR(s)`. No ADR changed. This is the bounded,
non-authorizing discovery stage selected by ADR-065 and does not alter the
Stage 2K.1 authority chain.

## Stage 2K.1 Prerequisite

The canonical `guardian/core/repository_authority.py` was present unchanged.
The scanner reuses `validate_git_working_tree_root(...)` for its only Git
probe and `resolve_guardian_projects_directory(...)` for the managed-root
factory. `discovery_candidate` remains excluded from binding-eligible source
classes. The Alembic graph was already solely at `6e2b9c4a7d1f`.

## Current Truth Before

Stage 2K.1 provided durable, account-scoped Project-to-working-tree authority
through an active binding. There was no bounded candidate result type, no
scanner, no import/link API, no repository search capability, and no
model-facing repository discovery.

## Discovery Root Authority

`discover_repository_candidates(...)` accepts only a typed
`AuthorizedDiscoveryRoot`, never a naked `Path` or `str`. Factories require a
non-empty authorized actor and an existing canonical directory. They never
derive a root from cwd, a nearby `.git`, or a default scan location.

## Root Provenance Classes

- `guardian_projects_directory`
- `explicit_authenticated_user_selection`
- `evidence_backed_local_root`
- `connector_authorized_root`

Evidence-backed and connector roots additionally require a non-empty bounded
evidence reference. The Guardian Projects Directory factory resolves only
through the Stage 2K.1 resolver and never creates the configured directory.

## Forbidden Broad Roots

Canonical `/`, `/Users`, `/Volumes`, and the complete current home directory
are rejected, including aliases which canonicalize to those paths. An
explicitly selected bounded child below home remains eligible.

## Scanner Limits

The immutable ADR-065 defaults are exactly:

- maximum depth: `4` (root is depth `0`)
- maximum candidates per root: `128`
- maximum root-wide wall-clock budget: `10.0` seconds

Limits are validated as non-negative depth, positive candidate count, and
positive timeout; they are not operator configuration values in this slice.

## Traversal Strategy

The scanner performs deterministic breadth-first traversal using sorted
directory entries. It owns the candidate, depth, and monotonic-deadline
enforcement. Directories at depth four are considered for evidence; children
at depth five are never traversed.

## Symlink Policy

Directory symlinks are counted and never traversed. A `.git` symlink is not
accepted as evidence and is counted as a skipped symlink. The root is
canonicalized before traversal, so aliases cannot widen the authorized root.

## Git Evidence Policy

Only an immediate real `.git` directory or a real `.git` worktree file makes a
directory eligible for Git validation. Ordinary directories never trigger a
Git probe. The scanner reads no arbitrary project source files to classify a
candidate.

## Git Validation Reuse

For eligible evidence only, the scanner calls the Stage 2K.1 exact
working-tree validator with no more than the remaining root-wide deadline.
That helper performs the sole argv-based, read-only `git rev-parse
--show-toplevel` check. The discovery module does not invoke Git commands,
contact remotes, fetch, pull, checkout, inspect status, or modify an index.

## Candidate Representation

Each frozen internal candidate contains the canonical absolute working-tree
root, root-relative observation path, root-provenance class, authorized actor,
Git evidence kind, timezone-aware discovery timestamp, and a fixed
`discovery_candidate` source class. No serializer, HTTP schema, database row,
remote URL, credential, Git configuration, source content, prompt, or private
agent metadata was added.

## Candidate Non-Authority Proof

The candidate type rejects any source class other than
`discovery_candidate`. The new module imports no SQLAlchemy or Guardian DB
surface and has no Project, Workspace, durable-binding, command-bus, chat, or
provider dependency. Results are returned as ephemeral frozen values only.

## Deduplication Behavior

Candidates are deduplicated within one run by canonical validated working-tree
root. The first deterministic observation is retained; later canonical aliases
increment a duplicate counter and do not produce another candidate.

## Candidate Limit Proof

129 lightweight `.git` evidence fixtures and a canonical-validator test seam
proved the scanner returns exactly 128 candidates and stops with
`candidate_limit_reached`.

## Timeout Proof

A deterministic `time.monotonic()` fixture advanced beyond the ten-second
deadline without sleeping. The scanner stopped with `timeout_reached` and
reported an elapsed duration capped at `10.0` seconds.

## Depth Limit Proof

Real temporary Git repositories were discovered at depths zero, one, and four.
A real repository at depth five was not discovered.

## No-Descent-After-Repository Proof

A valid repository with a nested Git repository produced only the outer
candidate. Successfully validated roots are traversal boundaries, including
canonical aliases already observed in the same run.

## Coding-Agent Root Policy

This module has no automatic root provider and no default scan list. It does
not inspect coding-agent state, worktrees, configuration, prompts, or private
metadata. An already-authorized bounded evidence root is the only future
entry point for such a location; this task does not create one.

## Filesystem Mutation Proof

Focused tests snapshot fixture content and modification time before scanning
and verify both remain unchanged afterward. Fixture Git repositories and a
linked worktree are constructed by tests outside the scanner; the scanner has
no creation, deletion, copy, move, clone, initialization, or write operation.

## No Persistence Proof

No model, migration, database session, storage service, or durable record was
added or modified. The canonical Alembic head stays unchanged.

## No Import/Binding Proof

No candidate creates an import, Project, durable binding, or Workspace
projection. Explicit authenticated import/linking remains the next-stage
decision and must revalidate a candidate when introduced.

## No Model/Tool Exposure Proof

No route, command, `repository.search`, ordinary-chat exposure, model payload,
provider change, provider inference, or runtime restart was added or run.

## Unit Test Results

`pytest -v tests/core/test_repository_discovery.py` — `39 passed`.

Coverage includes root authorization and broad-root rejection; default limits;
depth, count, deadline, symlink, worktree-file, invalid-evidence, and
deduplication boundaries; Git-validator reuse; no source execution; no write;
no persistence imports; and no automatic external-location scanning.

## Stage 2K.1 Regression Results

`pytest -v tests/core/test_repository_authority.py` — `32 passed`.

## Alembic Head Result

Before and after this no-schema slice:

`python -m alembic -c backend/alembic.ini heads` —
`6e2b9c4a7d1f (head)`.

`pytest -v tests/migration/test_alembic_revision_uniqueness.py` — `1 passed`.

## Architecture Test Results

On the task-start baseline, `pytest -v tests/architecture` — `394 passed`.

After the unrelated documentation-only `origin/main` advancement and required
rebase, the original final run reported `2 failed, 392 passed`. Both failures
were DLG `content_hash_mismatch` errors for
`docs/architecture/00-current-state.md` and `docs/architecture/README.md`.
The advancement changed those sources without synchronizing their canonical
node records:

- `docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json`
- `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json`

Stage 2K.2A synchronized only each node's `content_hash` from the exact
governed source bytes. All freshness metadata—including current-state
verification metadata and the KB-entrypoint's existing `stale` state—remained
unchanged. The focused DLG suite then passed `38 passed`, and the final full
architecture suite passed `394 passed`.

## Docs Validation

`python3 scripts/validate_docs.py` — passed.

`make docs PYTHON=python3` — passed, including diagram freshness.

## What Was Proven

- Guardian can scan only one explicitly authorized or separately evidenced
  local root at a time.
- Candidate observations are bounded, deterministic, read-only, and
  non-authorizing.
- The Stage 2K.1 exact Git-root validation seam remains the only Git
  validation operation.
- Candidate, depth, time, symlink, and no-descent boundaries are unit-proven.
- The task-start architecture suite passed before the unrelated documentation
  refresh changed the DLG-governed source hashes.
- The two canonical DLG hashes now equal the exact SHA-256 bytes of their
  governed sources, with all non-hash node metadata unchanged.
- Guardian can now perform bounded read-only discovery of Git working-tree
  candidates beneath explicitly authorized or separately evidence-backed roots,
  while discovery candidates remain non-authorizing, ephemeral observations
  with no Project, RepositoryBinding, tool, or model authority.

## What Was Not Proven

- No external repository candidate is automatically imported.
- No candidate creates a Project.
- No candidate creates a RepositoryBinding.
- No Workspace projection is created.
- No automatic coding-agent root discovery exists.
- No `repository.search` Command Bus capability exists.
- No ordinary-chat repository discovery/search capability exists.
- No model receives host paths or candidates.
- No provider inference occurred.
- No supported runtime was restarted.

## Documentation Follow-Through

This proof receipt is the authorized documentation follow-through. ADR-065,
the repository-onboarding authority contract, `00-current-state.md`, database
models, migrations, and runtime configuration were intentionally unchanged.
Stage 2K.2A repaired only the two canonical node source hashes; it did not
re-verify freshness, hand-edit generated DLG projections, or change any
architecture semantics.

## Final File Scope

- `guardian/core/repository_discovery.py`
- `tests/core/test_repository_discovery.py`
- `docs/architecture/proofs/2026-08-12-stage2k2-repository-candidate-discovery-proof.md`

## Stage 2K.2A Closure File Scope

- `docs/knowledge-graph/nodes/codexify:doc:architecture:current-state.json`
- `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json`
- `docs/architecture/proofs/2026-08-12-stage2k2-repository-candidate-discovery-proof.md`

## Commit

Stage 2K.2 implementation commit:
`2c045379a84c68852b7f0595a824e753d0f721e4`.

The Stage 2K.2A integrity-repair commit is recorded in Git history and the
task closeout after all required checks; this receipt does not self-reference a
mutable commit ID.
