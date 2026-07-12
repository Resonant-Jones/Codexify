# Guardian Evidence Fixture Freshness — Post-Merge Scope Audit (PR #539)

> Classification: post-merge proof/audit surface
> Status: scoped audit — no runtime implementation, no rollback, no release approval
> Last updated: 2026-07-11

## 1. Purpose

Document exactly which files landed through PR #539, classify each changed-file group, and determine whether the Guardian Evidence fixture freshness task scope was contained or contaminated by unrelated merged changes. This audit is a classification surface only. It does not revert, approve, widen release claims, or alter runtime behavior.

## 2. Scope

- Source commit range for audit: `cc18a4dab..2ee6862b2`
- Base before PR #539: `cc18a4dab` (Merge PR #538 — Add Guardian evidence generated packet fixture)
- Merge commit: `2ee6862b2` (Merge PR #539 from `codex/guardian-evidence-fixture-freshness`)
- Head commit of merged branch: `f52932962` (Refresh Guardian evidence packet fixtures)
- Ancestor commits pulled in by the branch: `b4190df4c`, `aceb0517b`, `369f9f810`

## 3. Source Commits and Refs

| Ref | SHA | Description |
|-----|-----|-------------|
| Base commit | `cc18a4dab` | Merge PR #538 (main before PR #539) |
| PR #539 merge | `2ee6862b2` | GitHub merge of PR #539 into main |
| PR #539 head | `f52932962` | "Refresh Guardian evidence packet fixtures" (intended task) |
| Ancestor 1 | `b4190df4c` | "Isolate tester access with Tailscale sidecar" (unrelated to fixture freshness) |
| Ancestor 2 | `aceb0517b` | "Add Codexify Peekaboo demo packet" (unrelated to fixture freshness) |
| Ancestor 3 | `369f9f810` | "Daily Audits" (unrelated to fixture freshness; routine audit artifacts) |

## 4. Expected Closeout Scope

The task closeout for the fixture freshness branch stated that the intended work was limited to:

- Refresh `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json`
- Refresh `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`
- Update `tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py`
- Update `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py`
- Update related evidence-packet fixture assertions for refreshed `matched_count` values
- No runtime, UI, API, Makefile, demo, Docker, Tailscale, audit, or media-route changes
- No unrelated dirty state at start

## 5. Observed Merged Scope

The PR #539 branch (`codex/guardian-evidence-fixture-freshness`) was created from a HEAD at `369f9f810`, which itself depended on `aceb0517b` and `b4190df4c`. None of those three ancestor commits were in `cc18a4dab` (main's base). Therefore the PR pulled in four commits, not one:

| Commit | Intended for fixture freshness? | Files |
|--------|---------------------------------|-------|
| `f52932962` — Refresh Guardian evidence packet fixtures | **Yes** | 8 files (fixtures + tests) |
| `369f9f810` — Daily Audits | **No** | 6 audit files |
| `aceb0517b` — Add Codexify Peekaboo demo packet | **No** | 28 files (demo assets, scripts, Makefile, frontend, media route) |
| `b4190df4c` — Isolate tester access with Tailscale sidecar | **No** | 5 files (ops, config, compose, tests) |

Only commit 1 of 4 belonged to the intended Guardian Evidence fixture freshness task. The merged PR was therefore scope-contaminated even though the intended fixture changes appear self-contained.

## 6. Changed-File Classification Table

| File path | Category | Intended for fixture freshness? | Runtime/UI/Ops/Docs/Test/Asset impact | Recommended disposition | Notes |
|-----------|----------|---------------------------------|--------------------------------------|-------------------------|-------|
| `docs/architecture/fixtures/guardian-evidence-bounded-read.local-tooling.v1.json` | test/fixture | yes | Test — fixture refresh | Accept as intended | Intended work |
| `docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json` | test/fixture | yes | Test — fixture refresh | Accept as intended | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_fixture.py` | test | yes | Test — refreshed fixture assertions | Accept as intended | Intended work |
| `tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py` | test | yes | Test — timestamp normalization/assertions | Accept as intended | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read.py` | test | yes | Test — matched_count update | Accept as intended | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_contract.py` | test | yes | Test — matched_count update | Accept as intended | Intended work |
| `tests/evidence_packets/test_guardian_evidence_bounded_read_make_target.py` | test | yes | Test — matched_count update | Accept as intended | Intended work |
| `tests/architecture/test_guardian_evidence_packet_batch_validator.py` | test | yes | Test — matched_count update | Accept as intended | Intended work |
| `docs/audits/daily/morning/2026-07-11-audit.json` | docs/audit | no | Docs/Audit — daily audit artifact | Separate review/validation | Unrelated; routine audit cycle |
| `docs/audits/daily/morning/2026-07-11-audit.md` | docs/audit | no | Docs/Audit — daily audit artifact | Separate review/validation | Unrelated; routine audit cycle |
| `docs/audits/daily/morning/latest.json` | docs/audit | no | Docs/Audit — latest pointer update | Separate review/validation | Unrelated; routine audit cycle |
| `docs/audits/daily/morning/latest.md` | docs/audit | no | Docs/Audit — latest pointer update | Separate review/validation | Unrelated; routine audit cycle |
| `docs/audits/latest.json` | docs/audit | no | Docs/Audit — latest pointer update | Separate review/validation | Unrelated; routine audit cycle |
| `docs/audits/latest.md` | docs/audit | no | Docs/Audit — latest pointer update | Separate review/validation | Unrelated; routine audit cycle |
| `.env.demo.example` | config | no | Ops/Demo — demo env template | Separate review/validation | Unrelated; demo ops |
| `.env.tester.example` | config | no | Ops/Config — tester env template | Separate review/validation | Unrelated; tester ops |
| `config/tailscale/codexify-test-serve.json` | config | no | Ops/Config — Tailscale serve config | Separate review/validation | Unrelated; tester ops |
| `docker-compose.tester.yml` | ops/deploy | no | Ops/Deploy — tester compose changes | Separate review/validation | Unrelated; tester ops |
| `docs/Ops/friends-family-tester-runtime.md` | docs/ops | no | Docs/Ops — tester runtime doc update | Separate review/validation | Unrelated; tester ops |
| `tests/ops/test_tailscale_tester_compose_contract.py` | test/ops | no | Test/Ops — tester compose contract tests | Separate review/validation | Unrelated; tester ops |
| `Demo-Assets/peekaboo-demo/README.md` | asset/docs | no | Asset/Docs — demo readme | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/launch-brief.md` | asset/docs | no | Asset/Docs — demo document | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/onboarding-observations.txt` | asset/docs | no | Asset/Docs — demo document | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/documents/workspace-notes.txt` | asset/docs | no | Asset/Docs — demo document | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/assets/images/*.png` | asset/img | no | Asset/Image — demo images | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/demo-manifest.json` | asset/config | no | Asset/Config — demo manifest | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/renders/*.mp4` | asset/media | no | Asset/Media — demo video | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/review-notes.md` | asset/docs | no | Asset/Docs — demo review notes | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/video-spec.md` | asset/docs | no | Asset/Docs — demo video spec | Separate review/validation | Unrelated; demo assets |
| `Demo-Assets/peekaboo-demo/work/*.jpg` | asset/img | no | Asset/Image — demo working files | Separate review/validation | Unrelated; demo assets |
| `scripts/demo/demo-content.json` | script | no | Script — demo content data | Separate review/validation | Unrelated; demo scripts |
| `scripts/demo/render_peekaboo.sh` | script | no | Script — demo render script | Separate review/validation | Unrelated; demo scripts |
| `scripts/demo/reset_demo_workspace.py` | script | no | Script — demo reset script | Separate review/validation | Unrelated; demo scripts |
| `scripts/demo/seed_demo_workspace.py` | script | no | Script — demo seed script | Separate review/validation | Unrelated; demo scripts |
| `scripts/demo/verify_demo_workspace.py` | script | no | Script — demo verify script | Separate review/validation | Unrelated; demo scripts |
| `frontend/src/components/persona/layout/AppShell.tsx` | frontend/UI | no | UI — default gallery switches to localhost Peekaboo demo assets and changes fallback behavior | Separate review/validation | Unrelated; can affect non-local shells because default image URLs target `localhost:5173` |
| `frontend/src/public/peekaboo-demo/*.png` | frontend/asset | no | UI/Asset — frontend demo images | Separate review/validation | Unrelated; supports AppShell gallery defaults |
| `guardian/routes/media.py` | backend/API | no | Runtime/API — media image-list response payload adds `project_id` | Separate review/validation | Unrelated; changes media listing contract |
| `Makefile` | build/ops | no | Build/Ops — demo make targets added | Separate review/validation | Unrelated; build/tooling surface |

## 7. Intended Guardian Evidence Fixture Freshness Files

All 8 files from commit `f52932962` are within the intended fixture freshness surface:

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

**Commit `b4190df4c` — Tailscale tester isolation (5 files):**
- `.env.tester.example`
- `config/tailscale/codexify-test-serve.json`
- `docker-compose.tester.yml`
- `docs/Ops/friends-family-tester-runtime.md`
- `tests/ops/test_tailscale_tester_compose_contract.py`

**Commit `aceb0517b` — Peekaboo demo packet (28 files):**
- `.env.demo.example`
- `Makefile` (demo targets)
- `Demo-Assets/peekaboo-demo/*` (demo documents, images, video, manifest, notes)
- `frontend/src/components/persona/layout/AppShell.tsx`
- `frontend/src/public/peekaboo-demo/*` (3 images)
- `guardian/routes/media.py`
- `scripts/demo/*` (5 files)

**Commit `369f9f810` — Daily Audits (6 files):**
- `docs/audits/daily/morning/2026-07-11-audit.json`
- `docs/audits/daily/morning/2026-07-11-audit.md`
- `docs/audits/daily/morning/latest.json`
- `docs/audits/daily/morning/latest.md`
- `docs/audits/latest.json`
- `docs/audits/latest.md`

## 9. Runtime/API Impact Review

The file `guardian/routes/media.py` was modified in the audited range. The observed diff adds `project_id` to media image-list response payloads. This is a runtime/API contract change for media listing responses. It is not a Peekaboo demo path allowlist change, and it is not related to Guardian Evidence fixture freshness.

**Finding:** One runtime API file (`guardian/routes/media.py`) changed outside the intended task. Because the change alters media listing response shape, it requires its own review and validation before being treated as accepted runtime behavior.

## 10. UI Impact Review

The file `frontend/src/components/persona/layout/AppShell.tsx` was modified in the audited range. The observed diff replaces the default gallery items with `http://localhost:5173/peekaboo-demo/...` assets and changes fallback behavior so an all-mock stored gallery falls back to those defaults. It does not add navigation items.

**Finding:** One UI file (`frontend/src/components/persona/layout/AppShell.tsx`) changed outside the intended task. The affected UI path is the default gallery state. Because the new default image URLs target `localhost:5173`, the change can be wrong in non-local shells and requires separate UI review/validation.

## 11. Ops/Deployment Impact Review

Files changed:
- `docker-compose.tester.yml` — tester compose modifications (Tailscale sidecar)
- `config/tailscale/codexify-test-serve.json` — new Tailscale config
- `.env.tester.example` — tester env template
- `.env.demo.example` — demo env template
- `Makefile` — demo make targets
- `docs/Ops/friends-family-tester-runtime.md` — tester runtime doc update

**Finding:** Ops/deployment files changed outside the fixture freshness task. They are scoped to tester isolation and demo preparation, not Guardian Evidence fixture freshness. They need separate review/validation if they remain merged.

## 12. Demo/Assets Impact Review

A new `Demo-Assets/peekaboo-demo/` asset directory was added with documents, images, video, manifest, and notes. A new `scripts/demo/` directory was added with demo seed/reset/verify/render tooling. Frontend public demo assets were also added.

**Finding:** Demo assets and scripts changed outside the fixture freshness task. They are unrelated to Guardian Evidence fixture freshness and need separate review/validation if treated as accepted project assets.

## 13. Audit-Artifact Impact Review

Daily audit artifacts for 2026-07-11 were added and `latest` audit pointers were updated. This is part of a routine audit cycle, but it is unrelated to the fixture freshness task.

**Finding:** Routine audit artifacts changed outside the fixture freshness task. Their inclusion in PR #539 should be classified as branch-base contamination, not as proof for the fixture freshness task.

## 14. Release-Truth Impact Review

This audit does not approve or reject release-truth changes. It only classifies the merged scope. The intended Guardian Evidence fixture freshness work is static fixture/test work and does not affect release truth. The unrelated changes include runtime/API, UI, ops/deployment, Makefile, audit, and demo asset surfaces. Those surfaces do not become release-approved merely because they were merged with the fixture freshness PR.

**Finding:** No release-truth expansion is authorized by this audit. Any release-facing claims about the unrelated changes require their own governing task, validation, and current-state follow-through.

## 15. Validation Reviewed

The following validation results were reported in the PR #539 closeout and are accepted only as evidence for the intended Guardian Evidence fixture freshness work:

- Static validation of refreshed generated fixture: `pass_with_warnings`
- Batch validation (`matched_count: 3`): PASS
- All evidence Make targets: PASS
- Focused evidence packet test suite (9+ test files): PASS
- Architecture batch validator test: PASS
- Bridge static suite: PASS
- `python3 scripts/validate_docs.py`: PASS

No validation was provided in that closeout for the unrelated runtime/UI/ops/demo/audit commits. Their acceptance remains a separate concern and cannot be inferred from fixture-focused validation.

## 16. Contradiction with Closeout Claim

The task closeout stated: "No unrelated dirty state was present at start. Clean worktree."

The PR #539 branch (`codex/guardian-evidence-fixture-freshness`) was created from a HEAD at `369f9f810`, which was not on main (main was at `cc18a4dab`). The three ancestor commits (`b4190df4c`, `aceb0517b`, `369f9f810`) were present in the branch but not in main. While the worktree at branch-creation time may have appeared clean (`git status --short` showing no output), the branch was rooted on a non-main HEAD that contained changes not yet in main. The closeout should have noted that the branch base was not main and that unrelated commits would be pulled in at merge time.

**Finding:** The closeout claim of "no unrelated dirty state" may have been technically correct for the worktree, but it was incomplete and misleading for PR merge scope because it omitted the non-main branch base.

## 17. Whether the Guardian Evidence Fixture Chain Can Proceed Safely

The Guardian Evidence fixture files themselves (8 files from commit `f52932962`) are self-contained and do not depend on the unrelated runtime/UI/ops/demo/audit changes. The fixture-focused validation reported in the original closeout applies to those intended files only.

**Finding:** The Guardian Evidence fixture chain can proceed on the strength of the intended fixture/test changes, but that does not validate or approve the unrelated merged surfaces.

## 18. Whether a Follow-Up Revert/Split/Acceptance Task Is Recommended

The unrelated merged changes are:
- Tester ops/config (`b4190df4c`)
- Demo assets, scripts, Makefile additions, AppShell gallery defaults, and media image-list response payload changes (`aceb0517b`)
- Daily audit artifacts (`369f9f810`)

These may represent legitimate work for other tasks, but legitimacy is not the same as validation or release acceptance. Because PR #539 was a post-merge scope-contaminated PR and this audit is explicitly not release approval, this audit should not instruct reviewers to accept those unrelated changes as-is.

**Recommendation:** Do not treat the unrelated commits as accepted by this audit. Open or use separate follow-up review/validation work for the unrelated runtime/API, UI, ops/deployment, demo, Makefile, and audit surfaces. A revert or split decision should be made by that follow-up owner based on validated impact, not by this fixture freshness audit.

## 19. Classification

**fixture freshness: go** — The intended Guardian Evidence fixture freshness changes are correctly classified and can remain the proof basis for the Guardian Evidence fixture chain.

**merge scope: contaminated** — PR #539 included unrelated commits and file groups outside the fixture freshness task.

**unrelated surfaces: unapproved by this audit** — Runtime/API, UI, ops/deployment, demo, Makefile, and audit changes require separate validation/review before acceptance claims.

## 20. Recommendation

**Proceed with the Guardian Evidence implementation chain only for the fixture freshness surface.** Do not use PR #539 as validation or approval for unrelated runtime/UI/ops/demo/audit changes. Future agents should verify branch ancestry against `main`/`origin/main` before creating PR branches and should report non-main ancestry as dirty PR scope even when the worktree is clean.

## 21. Non-Goals

- This audit does not revert any commit.
- This audit does not change runtime behavior.
- This audit does not change UI behavior.
- This audit does not modify fixtures, tests, runtime code, or assets.
- This audit does not approve unrelated merged changes as runtime proof.
- This audit does not widen the supported beta release promise.
- This audit does not supersede `00-current-state.md`.

## 22. Open Questions

- Should a separate follow-up PR validate, accept, split, or revert the unrelated `b4190df4c`, `aceb0517b`, and `369f9f810` surfaces?
- Should `docs/architecture/agent-protocol-operations.md` be updated to require branch-base verification before PR creation?
- Should media listing contract tests explicitly cover `project_id` if that response-field addition is retained?
- Should the AppShell default gallery avoid hard-coded `localhost:5173` URLs or gate them to local tester/demo contexts only?
