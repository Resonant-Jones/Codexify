# CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP

## Campaign Metadata
- campaign_id: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
- campaign_slug: docs-and-scope-followup
- campaign_doc_path: docs/work/campaigns/<RUNNER_DETERMINES>.md
- source_findings: FINDING-2026-02-17-009, FINDING-2026-02-17-011
- objective: Remove stale canonical-roadmap ambiguity and keep deferred image-provider scope explicitly documented as MVP-non-blocking.

## Tasks

### Task 001
- task_id: 001
- task_title: Decision task - archive stale canonical roadmap and point to maintained source of truth
- risk: MED
- task_artifact_path: docs/work/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - docs/codexify-mvp-roadmap.md
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP-001"; exit 1; }
  3. rg -n "Date:|NOT registered|PDF|DOCX" docs/codexify-mvp-roadmap.md
  4. violations="$(git diff --name-only | rg -v '^(docs/codexify-mvp-roadmap\\.md)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  5. rg -n "Status: Archived|Superseded by docs/work/reports/mvp-core-loop-closure-matrix.md" docs/codexify-mvp-roadmap.md
  6. if rg -n "NOT registered|missing migration router|PDF parsing gap|DOCX parsing gap" docs/codexify-mvp-roadmap.md; then echo "STOP: stale contradictory claims remain"; exit 1; fi
- expected_outputs:
  - roadmap clearly marked archived with explicit superseding source
  - stale contradictory implementation claims removed or clearly historical/non-authoritative
  - no out-of-scope files are modified
- rollback_commands:
  - git restore docs/codexify-mvp-roadmap.md
- dependencies:
  - command -v rg >/dev/null

### Task 002
- task_id: 002
- task_title: Reassert deferred non-OpenAI image providers as MVP-acceptable in README and env template
- risk: LOW
- task_artifact_path: docs/work/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - README.md
  - .env.template
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP-002"; exit 1; }
  3. rg -n "not implemented|IMAGE_GEN_PROVIDER" guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py README.md .env.template
  4. violations="$(git diff --name-only | rg -v '^(README\\.md|\\.env\\.template)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  5. rg -n "MVP|deferred|503|IMAGE_GEN_PROVIDER" README.md .env.template
- expected_outputs:
  - README and .env.template explicitly state local/stability providers are deferred and may return 503
  - scope statement is consistent with MVP decision and does not mark deferred providers as blockers
  - no out-of-scope files are modified
- rollback_commands:
  - git restore README.md .env.template
- dependencies:
  - command -v rg >/dev/null


## Runner Receipt (Start)

- Campaign: MULTI_CAMPAIGN_2026_02_17

- Task ID: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP

- Head before: 18d94cb09175c89c034f7716b7fa0191aaa97b8f


## Completion Summary (Runner)

- Status: failed

- Summary: (runner error)

- Head before: 18d94cb09175c89c034f7716b7fa0191aaa97b8f

- Implementation commit hash: (none)

- Receipt update commit hash: (pending)

- Notes: codex exec failed
STDERR:
OpenAI Codex v0.101.0 (research preview)
--------
workdir: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
model: gpt-5.3-codex
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: high
reasoning summaries: auto
session id: 019c69dd-f905-70d3-b402-4fb2b958097c
--------
user
Execute CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP in order (Task 001 -> 002). Task 001 is a required decision task; encode the decision in-file, do not leave it implicit.
mcp: playwright starting
2026-02-17T04:31:20.876840Z ERROR codex_core::rollout::list: state db missing rollout path for thread 019c6535-a2ff-7643-aa25-6c9a626f77f7
2026-02-17T04:31:20.904360Z ERROR codex_core::rollout::list: state db missing rollout path for thread 019c631d-6c3e-7c20-922f-e404437b953a
mcp: playwright ready
mcp startup: ready: playwright

thinking
**Planning campaign exploration**
codex
{"status":"success","summary":"I’ll locate the campaign definition for `CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP`, read Task 001 and 002 requirements, then execute them sequentially with Task 001’s decision explicitly encoded in-file.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Clarifying commentary format and inspecting repo**
exec
/bin/zsh -lc "rg --files | rg 'CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP|campaign|Task 001|Task 002|receipt|artifact'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'pwd && ls -la' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
codex_runner/prompts/audit_report_to_campaign_runner.md
codex_runner/schemas/campaign_output.schema.json
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_10_AUDIT_DERIVED_MULTI_CAMPAIGN_2026_02_10.md
tools/codex-runner/src/codex_runner/resources/schemas/campaign_output.schema.json
docs/archive/tasks/legacy/TASK_2026_01_14_deterministic_task_artifact_dedupe_receipt_hash_propagationmd
docs/work/tasks/2026/02/TASK_2026_02_03_001_audit_campaign_docs.md
docs/work/tasks/2026/02/TASK_2026_02_03_002_campaign_task_index.md
docs/work/tasks/2026/02/TASK_2026_02_04_001_validate_campaign_document.md
docs/work/tasks/2026/01/TASK_2026_01_20_020_gitignore_e2e_artifacts.md
docs/work/tasks/2026/02/TASK_2026_02_04_001_build_campaign_audit.md
docs/work/tasks/2026/02/TASK_2026_02_04_001_campaign_audit_scaffold.md
docs/work/tasks/2026/02/TASK_2026_02_03_001_validate_campaign_conventions.md
docs/archive/tasks/legacy/TASK_2026_01_14_CLEAN_001_audit_campaign_docs.md
docs/work/tasks/2026/02/TASK_2026_02_04_002_validate_task_artifacts.md
docs/work/tasks/2026/02/TASK_2026_02_03_002_expand_campaign_doc_audit_checkpoints.md
 succeeded in 50ms:
/Users/resonant_jones/Keep/Resonant_Constructs/Codexify
total 87712
drwxr-xr-x@ 114 resonant_jones  staff      3648 Feb 16 18:17 .
drwxr-xr-x   12 resonant_jones  staff       384 Feb  6 15:41 ..
-rw-r--r--@   1 resonant_jones  staff     20484 Feb 16 05:27 .DS_Store
drwxr-xr-x    4 resonant_jones  staff       128 Feb 16 23:30 .chroma
drwxr-xr-x@   4 resonant_jones  staff       128 Nov 22 14:19 .chroma_test
drwxr-xr-x    3 resonant_jones  staff        96 Nov 22 14:26 .chroma_test_store
drwx------@   3 resonant_jones  staff        96 Jan 30 06:52 .claude
drwxr-xr-x    3 resonant_jones  staff        96 Feb 12 16:52 .codexify
-rw-r--r--@   1 resonant_jones  staff       421 Dec 18 14:26 .dockerignore
-rw-r--r--@   1 resonant_jones  staff      6009 Feb 16 22:42 .env
-rw-r--r--    1 resonant_jones  staff      2690 Feb 15 23:21 .env.example
-rw-r--r--    1 resonant_jones  staff      2689 Feb 15 23:21 .env.template
drwxr-xr-x   29 resonant_jones  staff       928 Feb 16 23:31 .git
-rw-r--r--@   1 resonant_jones  staff       265 Feb 14 12:41 .gitattributes
drwxr-xr-x   12 resonant_jones  staff       384 Feb 14 21:03 .github
-rw-r--r--    1 resonant_jones  staff      2438 Feb 16 00:49 .gitignore
drwxr-xr-x@   9 resonant_jones  staff       288 Feb 16 22:47 .mypy_cache
drwxr-xr-x@   4 resonant_jones  staff       128 Feb  5 06:35 .pnpm-store

thinking
**Searching campaign file locations**
codex
{"status":"success","summary":"I found campaign-related directories; next I’m locating the specific `CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP` definition and its Task 001/002 files.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Switching to plain commentary**
exec
/bin/zsh -lc 'rg -n "CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP|2026_02_17_DOCS_AND_SCOPE_FOLLOWUP|Task 001|Task 002" docs codex_tasks artifacts scripts -S' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
docs/work/tasks/2026/02/TASK_2026_02_03_002_expand_campaign_doc_audit_checkpoints.md:1:# Task 002: Expand Campaign Doc Audit Checkpoints
docs/work/tasks/2026/02/TASK_2026_02_11_202_deterministic_queue_backed_rag_integration_validation.md:1:# Task 001 - Deterministic queue-backed RAG loop validation
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:1:# CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:4:- campaign_id: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:12:### Task 001
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:21:  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP-001"; exit 1; }
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:35:### Task 002
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:45:  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP-002"; exit 1; }
docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md:63:- Task ID: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md:36:### Design Lock (Task 001 Recon Output)
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_16_HARDENING_SECURITY.md:70:Codexify Task Prompt (Task 001)
docs/work/tasks/2026/02/TASK_2026_02_03_001_standardize_activation_prompt_validation.md:1:# Task 001: Standardize Activation Prompt Validation
docs/work/tasks/2026/02/TASK_2026_02_04_001_campaign_audit_scaffold.md:1:# Task 001 — Campaign Audit Scaffold
docs/work/tasks/2026/02/TASK_2026_02_04_001_campaign_audit_scaffold.md:22:  "summary": "Prepared schema-valid campaign_output JSON with required paths and fully populated markdown fields for Task 001 (Codex Runner campaign audit).",
docs/work/tasks/2026/02/TASK_2026_02_11_202_docs_align_image_provider_behavior.md:1:# Task 001 - Align roadmap docs with actual provider behavior
docs/work/tasks/2026/02/TASK_2026_02_11_202_decision_local_only_api_key_and_remote_jwt_boundary.md:1:# Task 002 - Decision Task: local-only API key boundary and remote JWT/session requirement
docs/work/tasks/2026/02/TASK_2026_02_17_001_security_boundary_hardening.md:12:### Task 001
docs/work/tasks/2026/02/TASK_2026_02_17_001_security_boundary_hardening.md:41:### Task 002
docs/work/tasks/2026/02/TASK_2026_02_17_001_security_boundary_hardening.md:107:- Summary: Execution halted during Task 001 at `git rm --cached guardian/secrets/client_secret_oauth.json guardian/secrets/token.json` because this environment cannot write to `.git` (`.git/index.lock: Operation not permitted`). I did not proceed to Task 002 or Task 003.
docs/work/tasks/2026/02/TASK_2026_02_17_001_security_boundary_hardening.md:113:- Tests ran: Task 001 preflight: `git status --porcelain -uall` (passed, clean), Task 001 step 3: `git ls-files guardian/secrets/client_secret_oauth.json guardian/secrets/token.json` (both tracked), Task 001 step 4: `git rm --cached guardian/secrets/client_secret_oauth.json guardian/secrets/token.json` (blocked by `.git/index.lock` permission error), Environment check: `touch .git/_axis_write_test` (operation not permitted), Post-failure check: `git status --porcelain -uall` (still clean)

thinking
**Preparing to inspect task file**
codex
{"status":"success","summary":"Located the exact campaign file at `docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md`; I’m reading it now and then executing Task 001 followed by Task 002 exactly as specified.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Choosing plain text output**
exec
/bin/zsh -lc "sed -n '1,260p' docs/work/tasks/2026/02/TASK_2026_02_17_003_docs_and_scope_followup.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
# CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP

## Campaign Metadata
- campaign_id: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
- campaign_slug: docs-and-scope-followup
- campaign_doc_path: docs/work/campaigns/<RUNNER_DETERMINES>.md
- source_findings: FINDING-2026-02-17-009, FINDING-2026-02-17-011
- objective: Remove stale canonical-roadmap ambiguity and keep deferred image-provider scope explicitly documented as MVP-non-blocking.

## Tasks

### Task 001
- task_id: 001
- task_title: Decision task - archive stale canonical roadmap and point to maintained source of truth
- risk: MED
- task_artifact_path: docs/work/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - docs/codexify-mvp-roadmap.md
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty

thinking
**Checking git status cleanliness**
codex
{"status":"success","summary":"I’ve loaded the campaign checklist. Next I’m running Task 001 preflight and scope guards exactly, then I’ll make only the allowed file edits and verify the postconditions before moving to Task 002.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Planning preflight checks**
exec
/bin/zsh -lc 'rg -n "Date:|NOT registered|PDF|DOCX|Status:|Superseded" docs/codexify-mvp-roadmap.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'git status --porcelain -uall' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
4:**Date:** 2026-01-20
16:**Current Status:** Codexify is **75-85% complete** at MVP level. Most core infrastructure is production-ready, but several critical integration gaps prevent end-to-end workflows from being fully operational.
48:**Status:** 🟡 **85% Complete - Mostly Working**
147:**Status:** 🟡 **85% Complete - Mostly Working with Router Wiring Issue**
156:| **Migration Router** | `guardian/routes/migration.py` | 🔴 Defined but NOT registered | Router exists but not in `app.py` includes |
251:**Status:** 🟡 **85% Complete - Working but Missing PDF/DOCX Parsing**
253:Document upload infrastructure is excellent, but PDF/DOCX text extraction is not implemented.
271:- 🔴 **PDF** (.pdf) - Upload works, NO text extraction
272:- 🔴 **DOCX** (.docx) - Upload works, NO text extraction
289:2. **User Uploads Document** → Drag-drop or file picker (PDF, DOCX, MD, TXT)
313:| **7. Text extraction** | Lines 338-353 in media.py | 🔴 Only TXT/MD, no PDF/DOCX | Add PyPDF2 or pdfplumber for PDF, python-docx for DOCX |
324:**Milestone 3: Add PDF/DOCX Parsing & Chunking**
328:| **DOC-1** | Add PDF parsing library (PyPDF2 or pdfplumber) | `requirements.txt`, `guardian/core/parsers.py` | M | PDF library installation |
329:| **DOC-2** | Add DOCX parsing library (python-docx) | `requirements.txt`, `guardian/core/parsers.py` | M | python-docx installation |
330:| **DOC-3** | Implement PDF text extraction in upload endpoint | `guardian/routes/media.py` lines 340-350 | M | DOC-1 |
331:| **DOC-4** | Implement DOCX text extraction | `guardian/routes/media.py` | M | DOC-2 |
357:- Unit: PDF/DOCX parser functions
367:**Status:** ✅ **95% Complete - Production Ready**
469:**Status:** ✅ **95% Complete - Production Ready with OpenAI**
582:**Status:** 🔴 **40% Complete - Infrastructure Ready, Feature Missing**
 succeeded in 51ms:


thinking
**Planning archival rewrite**
codex
{"status":"success","summary":"Task 001 preflight is clean. I’m now editing only `docs/codexify-mvp-roadmap.md` to explicitly encode the archive decision and superseding source, while removing stale contradictory claims.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Scoping archival update approach**
exec
/bin/zsh -lc "sed -n '1,80p' docs/codexify-mvp-roadmap.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
# Codexify MVP Roadmap & Core Loop Plan

**Document Version:** 2.0 (Complete Codebase Audit)
**Date:** 2026-01-20
**Author:** Technical Product Lead + Staff Engineer Audit (Claude Code)
**Scope:** MVP Feature Completeness Analysis & Implementation Plan

---

## 1. Overview & Goals

### 1.1 Executive Summary

This document provides a comprehensive audit of the Codexify codebase against the six core MVP features, identifies implementation gaps, and defines a concrete roadmap to achieve a fully operational MVP.

**Current Status:** Codexify is **75-85% complete** at MVP level. Most core infrastructure is production-ready, but several critical integration gaps prevent end-to-end workflows from being fully operational.

**Primary Objective:** Close all core feature loops to enable immediate dogfooding and production use.

### 1.2 MVP Philosophy

thinking
**Planning archival in roadmap**
exec
/bin/zsh -lc 'wc -l docs/codexify-mvp-roadmap.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'rg -n "NOT registered|missing migration router|PDF parsing gap|DOCX parsing gap" docs/codexify-mvp-roadmap.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
    1220 docs/codexify-mvp-roadmap.md
 succeeded in 51ms:
156:| **Migration Router** | `guardian/routes/migration.py` | 🔴 Defined but NOT registered | Router exists but not in `app.py` includes |

thinking
**Replacing large file with archive pointer**
exec
/bin/zsh -lc "cat > docs/codexify-mvp-roadmap.md <<'EOF'
# Codexify MVP Roadmap (Archived)

Status: Archived
Decision Date: 2026-02-17
Decision: This document is archived as a planning source and is no longer authoritative for MVP scope or implementation status.
Superseded by docs/work/reports/mvp-core-loop-closure-matrix.md

## Decision Record

This is an explicit scope and documentation decision made on 2026-02-17:
- The former roadmap content in this file is treated as historical audit material only.
- Current MVP closure and loop status must be read from "'`docs/work/reports/mvp-core-loop-closure-matrix.md`.
- Any discrepancy between this file'"'s prior contents and current implementation should be resolved in favor of the superseding report and current code.

## Historical Retrieval

If historical audit detail from the prior version is needed, recover it from Git history for this path:
- "'`git log -- docs/codexify-mvp-roadmap.md`
- `git show <commit>:docs/codexify-mvp-roadmap.md`
EOF' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:


thinking
**Planning preflight and guard commands**
exec
/bin/zsh -lc 'set -e
rg -n "Date:|NOT registered|PDF|DOCX" docs/codexify-mvp-roadmap.md || true
violations="$(git diff --name-only | rg -v '"'"'^(docs/codexify-mvp-roadmap'"\\.md)"'$'"' || true)\"; test -z \""'$violations" || { echo "STOP: out-of-scope files detected"; printf '"'%s\\n' \""'$violations"; exit 1; }
rg -n "Status: Archived|Superseded by docs/work/reports/mvp-core-loop-closure-matrix.md" docs/codexify-mvp-roadmap.md
if rg -n "NOT registered|missing migration router|PDF parsing gap|DOCX parsing gap" docs/codexify-mvp-roadmap.md; then echo "STOP: stale contradictory claims remain"; exit 1; fi
' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
4:Decision Date: 2026-02-17
3:Status: Archived
6:Superseded by docs/work/reports/mvp-core-loop-closure-matrix.md

thinking
**Checking diff before commit**
codex
{"status":"success","summary":"Task 001 edits are in place and pass the scope/staleness guards. I’m verifying the diff, then I’ll create a Task 001 commit so Task 002 can start from a clean tree.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}
exec
/bin/zsh -lc "git status --short && git diff -- docs/codexify-mvp-roadmap.md | sed -n '1,220p'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
 M docs/codexify-mvp-roadmap.md
diff --git a/docs/codexify-mvp-roadmap.md b/docs/codexify-mvp-roadmap.md
index 0845d897..89dffdd6 100644
--- a/docs/codexify-mvp-roadmap.md
+++ b/docs/codexify-mvp-roadmap.md
@@ -1,1220 +1,19 @@
-# Codexify MVP Roadmap & Core Loop Plan
+# Codexify MVP Roadmap (Archived)
 
-**Document Version:** 2.0 (Complete Codebase Audit)
-**Date:** 2026-01-20
-**Author:** Technical Product Lead + Staff Engineer Audit (Claude Code)
-**Scope:** MVP Feature Completeness Analysis & Implementation Plan
+Status: Archived
+Decision Date: 2026-02-17
+Decision: This document is archived as a planning source and is no longer authoritative for MVP scope or implementation status.
+Superseded by docs/work/reports/mvp-core-loop-closure-matrix.md
 
----
+## Decision Record

thinking
**Committing task changes with message**
exec
/bin/zsh -lc 'git add docs/codexify-mvp-roadmap.md && git commit -m "campaign: archive stale MVP roadmap authority (task 001)"' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 437ms:
trim trailing whitespace.............................(no files to check)Skipped
fix end of files.....................................(no files to check)Skipped
check yaml...........................................(no files to check)Skipped
check json...........................................(no files to check)Skipped
check for added large files..........................(no files to check)Skipped
debug statements (python)............................(no files to check)Skipped
check for merge conflicts............................(no files to check)Skipped
check for case conflicts.............................(no files to check)Skipped
check docstring is first.............................(no files to check)Skipped
detect private key...................................(no files to check)Skipped
black................................................(no files to check)Skipped
isort................................................(no files to check)Skipped
flake8...............................................(no files to check)Skipped
mypy.................................................(no files to check)Skipped
bandit...............................................(no files to check)Skipped
pyupgrade............................................(no files to check)Skipped
[campaign/2026-02-16/audit-2026-02-17-derived-campaigns 46b2c824] campaign: archive stale MVP roadmap authority (task 001)
 1 file changed, 14 insertions(+), 1215 deletions(-)

thinking
**Preparing preflight checks and environment inspection**
codex
{"status":"success","summary":"Task 001 is committed (`46b2c824`) and the tree is clean. I’m starting Task 002 preflight now, then updating only `README.md` and `.env.template` to explicitly document deferred non-OpenAI image providers as MVP-non-blocking with possible 503 responses.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Assessing schema enforcement and format**
exec
/bin/zsh -lc 'rg -n "not implemented|IMAGE_GEN_PROVIDER" guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py README.md .env.template' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'test -z "$(git status --porcelain -uall)" && echo "preflight-clean" || { echo "STOP: dirty tree"; git status --short; }' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
guardian/image_gen/providers/stability.py:20:                "Stability image generation is not implemented. "
guardian/image_gen/providers/stability.py:21:                "Configure IMAGE_GEN_PROVIDER=openai or add Stability support."
guardian/image_gen/providers/local.py:20:                "Local image generation is not implemented. "
guardian/image_gen/providers/local.py:21:                "Configure IMAGE_GEN_PROVIDER=openai or add a local provider."
README.md:274:- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
 succeeded in 52ms:
preflight-clean

thinking
**Planning README and env updates**
exec
/bin/zsh -lc "sed -n '220,360p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '1,220p' .env.template" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'rg -n "IMAGE_GEN_PROVIDER|image generation|MVP|deferred|503" .env.template README.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:

**Profiled containers (not started unless enabled)**
- `chatgpt-migrate` (`cli` profile)
- `embedding-backfill`, `graph-backfill` (`backfill` profile)

**Communication summary**
- Backend <-> Postgres (chat threads, messages, memory, outbox, documents, media, etc.)
- Backend <-> Redis (task queues + task event streams)
- Backend <-> Neo4j (only if graph flags enabled)
- Backend <-> Vector store (FAISS/Chroma using local embeddings)
- Frontend <-> Backend (Vite proxy injects `X-API-Key` automatically in dev)

**Startup sequence (Compose)**
1. Postgres + Neo4j start
2. `graph-init` applies constraints (requires `NEO4J_PASS`)
3. `migrator` runs Alembic + `seed_defaults.py`
4. Backend starts, verifies required tables, seeds defaults again, then serves API
5. Workers start (Redis required)

## Repo Structure (Truthful)
 succeeded in 51ms:
# .env.template / .env.example
# Local-only environment configuration. Copy to .env and edit.
# Never commit your real .env. Templates are the source of truth.
#
# Security hygiene:
# - .env is ignored via .gitignore: keep it local-only.
# - Rotate GUARDIAN_API_KEY regularly; prefer short-lived tokens.
# - Never ship VITE_GUARDIAN_API_KEY in any hosted/public build.

# --- Core runtime ---
ENV=development
LOG_LEVEL=INFO
DEBUG=true
PORT=8000

# --- Auth boundary ---
# local  -> static X-API-Key auth is allowed (localhost/dev only)
# remote -> static API keys are rejected; session/JWT is required
GUARDIAN_AUTH_MODE=local
# Backend auth secret. Use a long random value and rotate frequently.
 succeeded in 51ms:
README.md:45:- **RAG upload endpoint** `/upload-chat` requires a missing module (`codexify.rag.enhanced_rag`), so it currently returns 503.
README.md:47:- **Embeddings API** `/api/embeddings` returns **dummy vectors only when explicitly requested** (`embedder=dummy`) or when fallback is enabled; otherwise it returns 503 until a real backend is configured.
README.md:48:- **Local/Stability image generation** is disabled and returns a 503 until a real provider is implemented or configured.
README.md:274:- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
README.md:408:- Local/Stability image generation is disabled; real providers require env setup.
README.md:535:* Local/Stability image generation is disabled; real providers require env setup.

thinking
**Planning README and .env updates**
exec
/bin/zsh -lc "sed -n '220,420p' .env.template" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:


thinking
**Identifying README sections for inspection**
exec
/bin/zsh -lc "sed -n '380,430p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '510,555p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '1,90p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:

Sensitive or architectural areas:
- `guardian/core/` (auth, DB wiring, event bus)
- `guardian/core/config.py` (provider routing rules)
- `guardian/guardian_api.py` (app lifecycle + router wiring)

Safe changes:
- UI components and styling in `frontend/src`
- New API endpoints in `guardian/routes/`
- New migrations under `guardian/db/migrations/versions/`

If you're unsure, open a small PR touching one area (UI or a single route) and ask for guidance.

### Known foot-guns

- Backend exits if `GUARDIAN_API_KEY` is missing.
* `LOCAL_EMBED_MODEL` must be **absolute** or embeddings will fail.
* Default templates use `http://localhost:11434/v1` for `LOCAL_BASE_URL`; update it for Docker (e.g., `http://host.docker.internal:11434/v1`) or your local setup.
* `make dev` runs `guardian.system_init` (not the FastAPI API server).

 succeeded in 52ms:
# Codexify

Codexify is a local-first chat + knowledge workspace built around a FastAPI backend (Guardian) and a React UI. It provides thread-based chat, memory silos, document autosave and sharing, media uploads, vector search, and optional workers for background tasks. Docker Compose is the primary, supported way to run the full stack.

### TL;DR — Start Here

If you want to **run Codexify locally** with the least friction:

* Use **Docker Compose**
* Copy `.env.template → .env`
* `.env` is local-only; never commit it (templates are the source of truth)
* Set `GUARDIAN_API_KEY`, `NEO4J_PASS`, and your local LLM settings
* Run: `docker compose up --build`
* Open:

  * UI: [http://localhost:5173](http://localhost:5173)
  * API docs: [http://localhost:8888/docs](http://localhost:8888/docs)

If you want to **contribute code**, start with:

 succeeded in 52ms:
- `make test` runs `python -m pytest -q guardian/tests tests` and will prompt if pytest is missing.
- You can also run pytest directly:

```bash
pytest guardian/tests
pytest tests
```

### Migrations
- Alembic config: `backend/alembic.ini`
- Migrations live in `guardian/db/migrations/`

```bash
alembic -c backend/alembic.ini revision -m "your change"
alembic -c backend/alembic.ini upgrade head
```

### Known foot-guns
- Backend exits if `GUARDIAN_API_KEY` is missing.
- `LOCAL_EMBED_MODEL` must be **absolute** or embeddings will fail.

thinking
**Clarifying image provider messaging**
exec
/bin/zsh -lc "sed -n '255,290p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
- `NEO4J_PASS` - required by `graph-init` (Compose dependency).
- `LOCAL_BASE_URL` - OpenAI-compatible LLM endpoint (e.g., Ollama).
- `LOCAL_LLM_MODEL` - model name passed to the local endpoint.
- `LOCAL_EMBED_MODEL` - **absolute path inside container** (e.g., `/models/bge-large-en-v1.5`).

### Required if running without Docker
- `DATABASE_URL` (or `GUARDIAN_DATABASE_URL`) - no DB, no chat/memory persistence.

### Common optional settings
- Cloud LLM usage requires all of:
  - `ALLOW_CLOUD_PROVIDERS=true`
  - `CODEXIFY_LOCAL_ONLY_MODE=false`
  - `CODEXIFY_EGRESS_ALLOWLIST=openai` (or `groq`)
  - `OPENAI_API_KEY` (or `GROQ_API_KEY`)
- `CODEXIFY_VECTOR_STORE=chroma|faiss`
- `CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=1` (allow mock embeddings fallback and `/api/embeddings` dummy mode)
- `EMBEDDING_BACKEND=dummy|gpt_oss|nomic` (`stub` is accepted as an alias for `dummy`)
- `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
- `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)

thinking
**Searching duplicate phrases**
codex
{"status":"success","summary":"Task 002 preflight passed. I found the image-provider scope statements in multiple README sections and no explicit image-gen scope block in `.env.template`; I’m patching both files to make the MVP deferral + possible 503 behavior explicit and consistent.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Focusing patch on README and env template**
exec
/bin/zsh -lc "rg -n \"Local/Stability image generation|IMAGE_GEN_PROVIDER \\+ IMAGE_GEN_MODEL|Explicit Non-Goals|Experimental / stubbed\" README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
44:**Experimental / stubbed / partially wired**
48:- **Local/Stability image generation** is disabled and returns a 503 until a real provider is implemented or configured.
403:## Explicit Non-Goals / Deferred Systems
408:- Local/Stability image generation is disabled; real providers require env setup.
530:## Explicit Non-Goals / Deferred Systems
535:* Local/Stability image generation is disabled; real providers require env setup.

thinking
**Adding MVP notes and settings**
file update
M /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md
@@ -47,3 +47,3 @@
 - **Embeddings API** `/api/embeddings` returns **dummy vectors only when explicitly requested** (`embedder=dummy`) or when fallback is enabled; otherwise it returns 503 until a real backend is configured.
-- **Local/Stability image generation** is disabled and returns a 503 until a real provider is implemented or configured.
+- **Local/Stability image generation** is intentionally deferred for MVP and is non-blocking; selecting those providers can return `503` until implementations are added.
 - **TTS**: API uses a **mock local provider** (sine wave). A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
@@ -273,3 +273,3 @@
 - `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
-- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
+- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation; MVP path is `openai`, while `local`/`stability` are deferred and may return `503`)
 - `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` (real TTS)
@@ -407,3 +407,3 @@
 - Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-- Local/Stability image generation is disabled; real providers require env setup.
+- Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 - TTS microservice exists but is not integrated into the main API.
@@ -534,3 +534,3 @@
 * Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-* Local/Stability image generation is disabled; real providers require env setup.
+* Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 * TTS microservice exists but is not integrated into the main API.
apply_patch(auto_approved=true) exited 0 in 23ms:
Success. Updated the following files:
M README.md
file update:
diff --git a/README.md b/README.md
index 43db2c2f53b5cac38d17aa8fcf92dab38c1efd7f..461144fb502bf2377a5a7ea4b6df2958efdab741
--- a/README.md
+++ b/README.md
@@ -45,7 +45,7 @@
 - **RAG upload endpoint** `/upload-chat` requires a missing module (`codexify.rag.enhanced_rag`), so it currently returns 503.
 - **RAG trace debug endpoint** is in-memory only and clears on restart.
 - **Embeddings API** `/api/embeddings` returns **dummy vectors only when explicitly requested** (`embedder=dummy`) or when fallback is enabled; otherwise it returns 503 until a real backend is configured.
-- **Local/Stability image generation** is disabled and returns a 503 until a real provider is implemented or configured.
+- **Local/Stability image generation** is intentionally deferred for MVP and is non-blocking; selecting those providers can return `503` until implementations are added.
 - **TTS**: API uses a **mock local provider** (sine wave). A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
 - **Desktop app** (Tauri) is a skeleton config (`src-tauri`) without a published build pipeline.
 
@@ -271,7 +271,7 @@
 - `EMBEDDING_BACKEND=dummy|gpt_oss|nomic` (`stub` is accepted as an alias for `dummy`)
 - `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
 - `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
-- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
+- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation; MVP path is `openai`, while `local`/`stability` are deferred and may return `503`)
 - `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` (real TTS)
 
 ## Development Workflow (As It Exists)
@@ -405,7 +405,7 @@
 - Full graph context is **off by default** and requires explicit env flags.
 - The `/upload-chat` RAG endpoint is effectively disabled (missing module).
 - Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-- Local/Stability image generation is disabled; real providers require env setup.
+- Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 - TTS microservice exists but is not integrated into the main API.
 - Desktop/Tauri app is not production-ready.
 
@@ -532,6 +532,6 @@
 * Full graph context is **off by default** and requires explicit env flags.
 * The `/upload-chat` RAG endpoint is effectively disabled (missing module).
 * Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-* Local/Stability image generation is disabled; real providers require env setup.
+* Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 * TTS microservice exists but is not integrated into the main API.
 * Desktop/Tauri app is not production-ready.

file update:
diff --git a/README.md b/README.md
index 43db2c2f53b5cac38d17aa8fcf92dab38c1efd7f..461144fb502bf2377a5a7ea4b6df2958efdab741
--- a/README.md
+++ b/README.md
@@ -45,7 +45,7 @@
 - **RAG upload endpoint** `/upload-chat` requires a missing module (`codexify.rag.enhanced_rag`), so it currently returns 503.
 - **RAG trace debug endpoint** is in-memory only and clears on restart.
 - **Embeddings API** `/api/embeddings` returns **dummy vectors only when explicitly requested** (`embedder=dummy`) or when fallback is enabled; otherwise it returns 503 until a real backend is configured.
-- **Local/Stability image generation** is disabled and returns a 503 until a real provider is implemented or configured.
+- **Local/Stability image generation** is intentionally deferred for MVP and is non-blocking; selecting those providers can return `503` until implementations are added.
 - **TTS**: API uses a **mock local provider** (sine wave). A separate HuggingFace TTS microservice exists (`backend/tts_service`) but is not integrated into the main API.
 - **Desktop app** (Tauri) is a skeleton config (`src-tauri`) without a published build pipeline.
 
@@ -271,7 +271,7 @@
 - `EMBEDDING_BACKEND=dummy|gpt_oss|nomic` (`stub` is accepted as an alias for `dummy`)
 - `GUARDIAN_ENABLE_GRAPH_CONTEXT=true` / `GUARDIAN_ENABLE_GRAPH_LOGGING=true`
 - `ENABLE_CONNECTOR_WORKER=true` (and provider tokens like `GITHUB_TOKEN`)
-- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation)
+- `IMAGE_GEN_PROVIDER` + `IMAGE_GEN_MODEL` (image generation; MVP path is `openai`, while `local`/`stability` are deferred and may return `503`)
 - `ELEVENLABS_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` (real TTS)
 
 ## Development Workflow (As It Exists)
@@ -405,7 +405,7 @@
 - Full graph context is **off by default** and requires explicit env flags.
 - The `/upload-chat` RAG endpoint is effectively disabled (missing module).
 - Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-- Local/Stability image generation is disabled; real providers require env setup.
+- Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 - TTS microservice exists but is not integrated into the main API.
 - Desktop/Tauri app is not production-ready.
 
@@ -532,6 +532,6 @@
 * Full graph context is **off by default** and requires explicit env flags.
 * The `/upload-chat` RAG endpoint is effectively disabled (missing module).
 * Embeddings API returns mock vectors only when explicitly requested; otherwise it fails closed until configured.
-* Local/Stability image generation is disabled; real providers require env setup.
+* Local/Stability image generation is deferred for MVP and is non-blocking; these providers may return `503` until implemented.
 * TTS microservice exists but is not integrated into the main API.
 * Desktop/Tauri app is not production-ready.

ERROR: You've hit your usage limit. To get more access now, send a request to your admin or try again at Feb 21st, 2026 3:13 PM.
Warning: no last agent message; wrote empty content to /var/folders/kj/mnb6b7ds2sq__bjhmglf5xyh0000gn/T/tmp6ajscgne/task_result.json
tokens used
67,274
