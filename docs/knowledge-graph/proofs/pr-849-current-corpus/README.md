# PR 849 bounded integration and DLG proof

## Scope and source

Source commit: `b7efce7cf15f5e5a0f4d38c16904cc0d38fe2648` on
`feature/user-messaging-and-discovery`, following reviewed head
`0f305806795742e102b7ae057c4ec13f99512a99`.
Integration merged current main `864f3d127` through #850 without conflicts.
The source commit above includes the three fixes and that current-main basis.

This proof is branch-local integration evidence, not merge, deployment or
post-merge Private Preview qualification. ADR-097 and messaging authority remain
unchanged. Current `origin/main` at reconciliation was
`d384fe74ea50ca6493cf5842e5990c62bfbfc07e`, already an ancestor.

## Review fixes and preservation

- GuardianChat retires the synthetic completion/inference lease when all four
  fast-mode resubmissions receive 429. No replacement task is attached; the user
  can send again without reload. Server-side turn ownership remains unchanged.
  The lifecycle regression proves exhaustion, no false admission, renewed input,
  and preserves existing successful retry/cancellation-race coverage.
- The worker checks authoritative cancellation before executor submission and
  uses the same `_run_chat_task` lifecycle and owner-guarded cleanup. The real
  single-slot executor regression verifies cancellation while an unrelated worker
  is still blocked, unchanged unrelated lock, one correlated cancelled outcome,
  and eventual execution of ordinary queued work. Existing successor-owner tests
  verify fail-closed release.
- Shared direct-message normalization preserves only safe `detail.message`,
  existing string/validation-array forms, error codes and ordinary Error text.
  Tests cover 400/409/429, retained status/code, idempotent normalization and no
  disclosure of unrelated recipient-policy/identifier fields. The request UI
  regression verifies rendered safe text.
- Full UI validation exposed the new-peer draft reset erasing first input after
  render. Reset now runs before paint; the existing consent integration test
  passes in the full suite. Request identity and protocol remain unchanged.

## DLG authority and calibration

The governing `docs/architecture/proofs/2026-08-09-dlg-phase3b-calibration-boundary-repair.md`
defines two separate proof surfaces:

1. Phase 3B freezes six historical Phase 3A projections and four reviewed ARP
   scenarios. It does not freeze living canonical nodes or Markdown.
2. Phase 3A validates current canonical source hashes, metadata and graph integrity.

Commit `0f3058067` incorrectly regenerated the historical calibration locations.
This repair restores all six byte-for-byte from the governing Phase 3A snapshot
`236798baaa3dd1f355232a85fd2f72d0c3715bd1`. No generator revision guard, schema,
scenario, expected identity, test, packet or fail-closed rule was weakened.
The four existing reading packets remain deterministic and internally valid.

The JSON reports alongside this receipt are **fresh Phase 3A current-corpus proof**
for the source commit above. They are generated with the supported Python API's
explicit `output_root`, then byte-checked with `check_generated` at the same
revision and commit timestamp. They do not replace frozen calibration inputs or
claim to be new representative reading packets.

`validation.json` reports PASS: 10 schema-valid canonical nodes, 13 resolved
relations, 10 matching source hashes, no integrity errors or authority conflicts.
Six pre-existing architecture README link warnings and derived freshness findings
remain explicit. Hash validity does not promote stale metadata into verified
release or runtime truth; no freshness window or authority was fabricated.

Reproduce from repository root:

```python
from pathlib import Path
from scripts.knowledge_graph import validate_and_generate_dlg as dlg
root = Path.cwd()
revision = "b7efce7cf15f5e5a0f4d38c16904cc0d38fe2648"
import subprocess
created_at = subprocess.check_output(
    ["git", "show", "-s", "--format=%cI", revision], text=True
).strip()
output = root / "docs/knowledge-graph/proofs/pr-849-current-corpus"
result = dlg.check_generated(root, revision, created_at, output_root=output)
assert not result.has_errors, result.summary()
```

Historical reading-packet check:

```sh
python scripts/knowledge_graph/generate_representative_arps.py check-generated \
  --created-at 2026-08-08T14:27:29-04:00
python -m pytest -q --disable-warnings tests/architecture
```

## Migration skip disposition

The old Guardian CI run `37076314023` detected
`guardian/db/migrations/versions/9e52b1d3c8fa_add_message_request_consent.py`
and emitted `backend_changed=true`, `run_backend=true`.
The migration job requires `[changes, backend-tests, alembic-config-sanity]`.
The failed backend dependency caused GitHub's normal dependency-success guard
to skip migration. Change detection was correct; no CI modification is needed.
The new head must run the migration job after its backend dependency passes.
A subsequent CI run exposed seven stale current-head expectations in migration
regressions. These now expect `9e52b1d3c8fa`; the uniqueness test additionally
asserts its exact `8d41a0c2b7ef` parent and consent-migration filename. Historical
revision IDs, upgrade targets, schema assertions and frozen blobs are retained.
An old skip is not migration proof or a non-applicability claim for this PR.

## Validation and remote boundary

- Focused three-defect UI suite: 100 passed.
- Queued cancellation, queue deadlines and exact Phase 3B suite: 60 passed.
- Actual PostgreSQL migration/race proof and explicit current-head lineage:
  2 passed, no skips.
- Messaging and chat cancellation/deadline preservation suite: 130 passed.
- Exact `tests/architecture` surface: 431 passed.
- Repository `pnpm run lint`: passed, zero errors; existing warnings remain.
- Repository `pnpm run build`: passed, existing chunk-size warning.
- Repository `pnpm run test`: 1,852 application tests plus 84 extension tests
  passed; one pre-existing skipped test. The initial full run failed the draft
  reset case described above; the corrected full run passed.
- Docs validator, current-corpus DLG validator, frozen ARP reproducibility and
  `git diff --check`: passed.
- Local full backend selection initially stopped at a missing declared PyJWT
  dependency. Local environment repair is not remote Guardian CI proof.

New-head Architecture Contracts, Guardian backend/core loops, Frontend Quality,
and Migration Contract status are verified directly on GitHub at closeout.
This receipt does not substitute local subsets for those required remote checks.
No new feature, new ADR, public Beta admission or deployment is included.
