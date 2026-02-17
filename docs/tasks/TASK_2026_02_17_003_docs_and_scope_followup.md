# CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP

## Campaign Metadata
- campaign_id: CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP
- campaign_slug: docs-and-scope-followup
- campaign_doc_path: docs/Campaign/<RUNNER_DETERMINES>.md
- source_findings: FINDING-2026-02-17-009, FINDING-2026-02-17-011
- objective: Remove stale canonical-roadmap ambiguity and keep deferred image-provider scope explicitly documented as MVP-non-blocking.

## Tasks

### Task 001
- task_id: 001
- task_title: Decision task - archive stale canonical roadmap and point to maintained source of truth
- risk: MED
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
- allowed_files:
  - docs/codexify-mvp-roadmap.md
- command_checklist:
  1. Preflight: git status --porcelain -uall must be empty
  2. test -z "$(git status --porcelain -uall)" || { echo "STOP: dirty tree"; echo "Cleanup: git stash push -u -m preflight-CAMPAIGN_2026_02_17_DOCS_AND_SCOPE_FOLLOWUP-001"; exit 1; }
  3. rg -n "Date:|NOT registered|PDF|DOCX" docs/codexify-mvp-roadmap.md
  4. violations="$(git diff --name-only | rg -v '^(docs/codexify-mvp-roadmap\\.md)$' || true)"; test -z "$violations" || { echo "STOP: out-of-scope files detected"; printf '%s\n' "$violations"; echo "Cleanup: git restore --staged $violations && git restore $violations"; exit 1; }
  5. rg -n "Status: Archived|Superseded by docs/reports/mvp-core-loop-closure-matrix.md" docs/codexify-mvp-roadmap.md
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
- task_artifact_path: docs/tasks/<RUNNER_DETERMINES>.md
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
