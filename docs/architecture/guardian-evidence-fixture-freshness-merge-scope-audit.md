# Guardian Evidence Fixture Freshness — Post-Merge Scope Audit (PR #539)

> Classification: post-merge proof/audit surface
> Status: scoped audit — no runtime implementation, no rollback, no release approval
> Last updated: 2026-07-11

## 1. Purpose

Document exactly which files landed through PR #539, classify each changed-file group, and determine whether the Guardian Evidence fixture freshness task scope was contained or contaminated by unrelated merged changes. This audit is a classification surface only. It does not revert, approve, widen release claims, or alter runtime behavior.

## 2. Scope

- Source commit range for audit: `cc18a4dab..2ee6862b2`
- Base before PR #539: `cc18a4dab` (Merge PR #538 — Add Guardian evidence generated packet fixture)
- Merge commit: `2ee6862b2` (Merge PR #539 from codex/guardian-evidence-fixture-freshness)
- Head commit of merged branch: `f52932962` (Refresh Guardian evidence packet fixtures)
- Ancestor commits pulled in by the branch: `b4190df4c`, `aceb0517b`, `369f9f810`

## 3. Source Commits and Refs

| Ref | SHA | Description |
|-----|-----|-------------|
| Base commit | `cc18a4dab` | Merge PR #538 (main before PR #539) |
| PR #539 merge | `2ee6862b2` | GitHub merge of PR #539 into main |
| PR #539 head | `f52932962` | "Refresh Guardian evidence packet fixtures" (intended task) |
| Ancestor 1 | `b4190df4c` | "Isolate tester access with Tailscale sidecar" (unrelated) |
| Ancestor 2 | `aceb0517b` | "Add Codexify Peekaboo demo packet" (unrelated) |
| Ancestor 3 | `369f9f810` | "Daily Audits" (unrelated — routine audit artifacts) |

## 4. Expected Closeout Scope

The task closeout for the fixture freshness branch stated:

- Refresh `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`
- Refresh `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`
- Update `tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py`
- Update `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py`
- No runtime, UI, API, Makefile, demo, Docker, Tailscale, audit, or media-route changes
- No unrelated dirty state at start

## 5. Observed Merged Scope

The PR #539 branch (`codex/guardian-evidence-fixture-freshness`) was created from a HEAD at `369f9f810`, which itself depended on `aceb0517b` and `b4190df4c`. None of those three ancestor commits were in `cc18a4dab` (main's base). Therefore the PR pulled in four commits, not one:

| Commit | Intended? | Files |
|--------|-----------|-------|
| `f52932962` — Refresh Guardian evidence packet fixtures | **Yes** | 8 files (fixtures + tests) |
| `369f9f810` — Daily Audits | **No** | 6 audit files |
| `aceb0517b` — Add Codexify Peekaboo demo packet | **No** | 28 files (demo assets, scripts, Makefile, frontend, media route) |
| `b4190df4c` — Isolate tester access with Tailscale sidecar | **No** | 5 files (ops, config, compose, tests) |

Only commit 1 of 4 (8 of 47 files, ~170 of 1031+ additions) belonged to the intended Guardian Evidence fixture freshness task.

## 6. Changed-File Classification Table

| File path | Category | Intended for fixture freshness? | Runtime/UI/Ops/Docs/Test/Asset impact | Recommended disposition | Notes |
|-----------|----------|-------------------------------|--------------------------------------|----------------------|-------|
| `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json` | test/fixture | yes | Test — fixture refresh | Accept | Intended work |
| `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json` | test/fixture | yes | Test — fixture refresh | Accept | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py` | test | yes | Test — matched_count update | Accept | Intended work |
| `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py` | test | yes | Test — timestamp normalization | Accept | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read.py` | test | yes | Test — matched_count update | Accept | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py` | test | yes | Test — matched_count update | Accept | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_make_target.py` | test | yes | Test — matched_count update | Accept | Intended work |
| `tests/architecture/test_guardian_evidence_packet_batch_validator.py` | test | yes | Test — matched_count update | Accept | Intended work |
| `docs/audits/daily/morning/2026-07-11-audit.json` | docs/audit | no | Docs/Audit — audit artifact | Accept (routine cycle) | Unrelated; routine |
| `docs/audits/daily/morning/2026-07-11-audit.md` | docs/audit | no | Docs/Audit — audit artifact | Accept (routine cycle) | Unrelated; routine |
| `docs/audits/daily/morning/latest.json` | docs/audit | no | Docs/Audit — audit artifact update | Accept (routine cycle) | Unrelated; routine |
| `docs/audits/daily/morning/latest.md` | docs/audit | no | Docs/Audit — audit artifact update | Accept (routine cycle) | Unrelated; routine |
| `docs/audits/latest.json` | docs/audit | no | Docs/Audit — audit artifact update | Accept (routine cycle) | Unrelated; routine |
| `docs/audits/latest.md` | docs/audit | no | Docs/Audit — audit artifact update | Accept (routine cycle) | Unrelated; routine |
| `.env.demo.example` | config | no | Ops/Demo — demo env template | Accept | Unrelated; demo assets |
| `.env.tester.example` | config | no | Ops/Config — tester env template | Accept | Unrelated; tester ops |
| `config/tailscale/codexify-test-serve.json` | config | no | Ops/Config — Tailscale serve config | Accept | Unrelated; tester ops |
| `docker-compose.tester.yml` | ops/deploy | no | Ops/Deploy — tester compose changes | Accept | Unrelated; tester ops |
| `docs/Ops/friends-family-tester-runtime.md` | docs/ops | no | Docs/Ops — tester runtime doc update | Accept | Unrelated; tester ops |
| `tests/ops/test_tailscale_tester_compose_contract.py` | test/ops | no | Test/Ops — tester compose contract tests | Accept | Unrelated; tester ops |
| `Demo-Assets/peekaboo-demo/README.md` | asset/docs | no | Asset/Docs — demo readme | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/launch-brief.md` | asset/docs | no | Asset/Docs — demo document | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/onboarding-observations.txt` | asset/docs | no | Asset/Docs — demo document | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/workspace-notes.txt` | asset/docs | no | Asset/Docs — demo document | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/images/*.png` | asset/img | no | Asset/Image — demo images | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/demo-manifest.json` | asset/config | no | Asset/Config — demo manifest | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/renders/*.mp4` | asset/media | no | Asset/Media — demo video | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/review-notes.md` | asset/docs | no | Asset/Docs — demo review notes | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/video-spec.md` | asset/docs | no | Asset/Docs — demo video spec | Accept | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/work/*.jpg` | asset/img | no | Asset/Image — demo working files | Accept | Unrelated; demo assets |
| `scripts/demo/demo-content.json` | script | no | Script — demo content data | Accept | Unrelated; demo scripts |
| `scripts/demo/render_peekaboo.sh` | script | no | Script — demo render script | Accept | Unrelated; demo scripts |
| `scripts/demo/reset_demo_workspace.py` | script | no | Script — demo reset script | Accept | Unrelated; demo scripts |
| `scripts/demo/seed_demo_workspace.py` | script | no | Script — demo seed script | Accept | Unrelated; demo scripts |
| `scripts/demo/verify_demo_workspace.py` | script | no | Script — demo verify script | Accept | Unrelated; demo scripts |
| `frontend/src/components/persona/layout/AppShell.tsx` | frontend/UI | no | UI — AppShell navigation update for peekaboo demo | Accept | Unrelated; UI/demo |
| `frontend/src/public/peekaboo-demo/*.png` | frontend/asset | no | UI/Asset — frontend demo images | Accept | Unrelated; demo assets |
| `guardian/routes/media.py` | backend/API | no | Runtime/API — media route allowlist update for peekaboo demo | Accept | Unrelated; API change |
| `Makefile` | build/ops | no | Build/Ops — demo make targets added | Accept | Unrelated; build targets |

## 7. Intended Guardian Evidence Fixture Freshness Files

All 8 files from commit `f52932962`:

1. `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`
2. `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`
3. `tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py`
4. `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py`
5. `tests/evidence_packets/test_guardian_evidence_bounded_read.py`
6. `tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py`
7. `tests/evidence_packets/test_guardian_evidence_bounded_read_make_target.py`
8. `tests/architecture/test_guardian_evidence_packet_batch_validator.py`

## 8. Unrelated or Potentially Unrelated Files

All 39 files from commits `b4190df4c`, `aceb0517b`, and `369f9f810` are unrelated to the fixture freshness task:

**Commit b4190df4c — Tailscale tester isolation (5 files):**
- `.env.tester.example`
- `config/tailscale/codexify-test-serve.json`
- `docker-compose.tester.yml`
- `docs/Ops/friends-family-tester-runtime.md`
- `tests/ops/test_tailscale_tester_compose_contract.py`

**Commit aceb0517b — Peekaboo demo packet (28 files):**
- `.env.demo.example`
- `Makefile` (demo targets)
- `Demo-Assets/peekaboo-demo/*` (all 18 files)
- `frontend/src/components/persona/layout/AppShell.tsx`
- `frontend/src/public/peekaboo-demo/*` (3 files)
- `guardian/routes/media.py`
- `scripts/demo/*` (5 files)

**Commit 369f9f810 — Daily Audits (6 files):**
- `docs/audits/daily/morning/2026-07-11-audit.json`
- `docs/audits/daily/morning/2026-07-11-audit.md`
- `docs/audits/daily/morning/latest.json`
- `docs/audits/daily/morning/latest.md`
- `docs/audits/latest.json`
- `docs/audits/latest.md`

## 9. Runtime/API Impact Review

The file `guardian/routes/media.py` was modified to allowlist peekaboo demo asset paths. This is a runtime API change (media route allowed-path extension). It is not related to Guardian Evidence fixture freshness. The change is scoped to demo asset serving and does not affect evidence processing, packet generation, validation, or command-bus behavior.

**Finding:** One runtime file (`guardian/routes/media.py`) was changed. It is unrelated to the fixture freshness task.

## 10. UI Impact Review

The file `frontend/src/components/persona/layout/AppShell.tsx` was modified to add peekaboo demo navigation items. This is a UI change. Three frontend public asset files were added for the demo.

**Finding:** One UI file (`frontend/src/components/persona/layout/AppShell.tsx`) was changed. It is unrelated to the fixture freshness task.

## 11. Ops/Deployment Impact Review

Files changed:
- `docker-compose.tester.yml` — tester compose modifications (Tailscale sidecar)
- `config/tailscale/codexify-test-serve.json` — new Tailscale config
- `.env.tester.example` — updated tester env template
- `.env.demo.example` — new demo env template
- `Makefile` — new demo make targets
- `docs/Ops/friends-family-tester-runtime.md` — tester runtime doc update

**Finding:** Ops/deployment files were changed. They are unrelated to the fixture freshness task and are scoped to tester isolation and demo preparation.

## 12. Demo/Assets Impact Review

Large new asset directory `Demo-Assets/peekaboo-demo/` was added with ~18 files including images, documents, video, and manifests. New `scripts/demo/` directory with 5 scripts. Frontend assets for the demo were added.

**Finding:** Demo assets and scripts were added. They are unrelated to the fixture freshness task.

## 13. Audit-Artifact Impact Review

Daily audit artifacts for 2026-07-11 were added and the `latest` symlinks/pointers were updated. This is part of a routine audit cycle and is unrelated to the fixture freshness task. Audit truth has been updated; claims from previous audits remain unchanged in substance.

**Finding:** Routine audit artifacts were updated. Unrelated but standard operating procedure.

## 14. Release-Truth Impact Review

None of the unrelated changes expand the supported beta release promise:
- Demo assets are operator-originated presentation material, not runtime evidence.
- Tailscale tester config is ops-scoped, not release-facing.
- Media route allowlist changes serve demo asset paths; they do not authorize evidence ingestion.
- AppShell is a frontend navigation layout; it does not add runtime evidence ingestion, UI for Guardian Evidence, or execution surfaces.
- Makefile demo targets are local tooling; they do not CI-gate or release-gate.
- Audit artifacts are observational.

The Guardian Evidence fixture freshness work (intended task) is purely static fixture/test and does not affect release truth.

**Finding:** No release-truth impact from either the intended or unintended merged changes.

## 15. Validation Reviewed

The following validation results were reported in the PR #539 closeout and are accepted for the intended fixture freshness work:

- Static validation of refreshed generated fixture: `pass_with_warnings`
- Batch validation (`matched_count: 3`): PASS
- All evidence Make targets: PASS
- Focused evidence packet test suite (9+ test files): PASS
- Architecture batch validator test: PASS
- Bridge static suite: PASS
- `python3 scripts/validate_docs.py`: PASS

No validation was provided or expected for the unrelated merged commits. Their acceptance is a separate concern.

## 16. Contradiction with Closeout Claim

The task closeout stated: "No unrelated dirty state was present at start. Clean worktree."

The PR #539 branch (`codex/guardian-evidence-fixture-freshness`) was created from a HEAD at `369f9f810`, which was NOT on main (main was at `cc18a4dab`). The three ancestor commits (`b4190df4c`, `aceb0517b`, `369f9f810`) were present in the branch but not in main. While the worktree at branch-creation time may have appeared clean (`git status --short` showing no output), the branch was rooted on a non-main HEAD that contained changes not yet in main. The closeout should have noted that the branch base was not main and that unrelated commits would be pulled in at merge time.

**Finding:** The closeout claim of "no unrelated dirty state" is technically correct for the worktree at branch-creation time but misleading because it omitted the fact that the branch was created from a non-main HEAD containing other work. The PR should have been retargeted to main or rebased.

## 17. Whether the Guardian Evidence Fixture Chain Can Proceed Safely

The Guardian Evidence fixture files themselves (8 files from commit `f52932962`) are correct and self-contained. The unrelated merged changes do not touch any Guardian Evidence code path, fixture, validator, or test. The fixture freshness work is fully valid.

**Finding:** YES. The Guardian Evidence fixture chain can proceed safely. The intended work is uncontaminated.

## 18. Whether a Follow-Up Revert/Split/Acceptance Task Is Recommended

The unrelated merged changes are:
- Demo assets and scripts — self-contained, no effect on core behavior
- Tester ops/config — self-contained, no effect on core behavior
- Audit artifacts — routine, no effect on core behavior
- Makefile — demo targets only, no effect on existing targets
- AppShell.tsx — demo nav items only
- `guardian/routes/media.py` — media path allowlist extension only

All three unrelated commits (`b4190df4c`, `aceb0517b`, `369f9f810`) represent legitimate work on other features (tester isolation, demo preparation, daily audits). They were not malicious or incorrect. The only issue is they were merged as part of PR #539 instead of through separate PRs.

**Recommendation:** **ACCEPT** the merged changes as-is. Do not revert or split. The unrelated work is legitimate and scoped. The fixture freshness task completed correctly. Future agents should be instructed to verify the branch base is `main`/`origin/main` before creating PR branches.

## 19. Classification

**go** — The Guardian Evidence fixture freshness work is correctly merged. The unrelated ancillary changes are independently valid work. No revert or split is required.

## 20. Recommendation

**proceed** — The Guardian Evidence implementation chain may continue. The fixture freshness is confirmed. Future branches must be created from `main` to avoid scope contamination.

## 21. Non-Goals

- This audit does not revert any commit.
- This audit does not change runtime behavior.
- This audit does not change UI behavior.
- This audit does not modify fixtures, tests, or documentation (except the audit document itself and the README update).
- This audit does not approve the unrelated merged changes as runtime proof.
- This audit does not widen the supported beta release promise.
- This audit does not supersede `00-current-state.md`.

## 22. Open Questions

- Should the `codex/build-peekaboo-demo` branch be closed now that its commits have been merged through PR #539?
- Should `docs/architecture/agent-protocol-operations.md` be updated to require branch-base verification?
