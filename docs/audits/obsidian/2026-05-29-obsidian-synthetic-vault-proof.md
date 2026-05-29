# Obsidian Synthetic Vault Proof

## Scope

This is the first synthetic-vault proof attempt for `/obsidian` workspace-context behavior on the primary Guardian chat surface.

This proof does not use the operator's real Obsidian vault. It does not promote Obsidian as required for normal chat completion, and it does not widen Codexify release posture.

Result: `PARTIAL`. The live proof stopped at host preflight because Obsidian was not installed on the host machine.

## Repository and Runtime

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before proof: `a7fbc789f0fb2d0567df77922cf15be247f09e41`
- Dirty/untracked files before proof: none
- Docker Compose services used: none. The live Compose proof was not started because host preflight failed.
- Proof timestamp/window: `2026-05-29T19:02:17Z`; stopped during host preflight.

Safety gate commands run before proof:

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
```

Safety gate result: repository root matched `/Volumes/Dev_SSD/Codexify-main`; status was clean.

## Host Preflight

Host Obsidian install checks:

```bash
test -d /Applications/Obsidian.app && echo "Obsidian app found"
mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'"
```

Observed result:

- `/Applications/Obsidian.app` was not present.
- Spotlight returned no `md.obsidian` bundle paths.

Obsidian was not already installed on the host machine. Per the preflight requirement, the live synthetic-vault proof stopped here.

## Synthetic Vault

No synthetic vault was created or ingested during this run because host Obsidian preflight failed before runtime proof setup.

The intended safe vault path for the next run remains:

- `/tmp/codexify-obsidian-synthetic-vault-2026-05-29`

The intended synthetic files remain:

- `plumbing-fixture-note.md`
- `codexify-architecture-note.md`
- `boundary-note.md`

The intended sentinel strings remain:

- `SENTINEL_OBSIDIAN_FIXTURE_2026_05_29`
- `SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29`
- `SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29`

No personal notes, secrets, client material, screenshots, or local vault contents were used. No vault files were committed.

## Ingestion / Linking Path

Ingestion/linking was not run.

Current supported path identified from the pre-read:

- Configure Obsidian vault root with `PUT /api/obsidian/config`.
- Trigger indexing with `POST /api/obsidian/index`.
- Verify search/readiness through `/api/health/retrieval`.
- Run queue-backed chat completion and inspect persisted assistant messages plus task-event retrieval posture.

No project/thread binding, document IDs, or readiness evidence were produced in this blocked run.

## Slash Command Proof

The `/obsidian` chat questions were not submitted because the proof stopped at host preflight.

Planned questions for the next run:

- `/obsidian What is the correct answer for SENTINEL_OBSIDIAN_FIXTURE_2026_05_29?`
- `/obsidian According to SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29, what remains the canonical user-facing transcript?`
- `/obsidian According to SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29, what does /obsidian grant?`

No source message IDs, task IDs, assistant message IDs, or assistant answer summaries exist for this run.

## Trace / Retrieval Evidence

No task event evidence, persisted assistant metadata, debug RAG trace, or retrieval readback evidence was produced.

Evidence caveat: the absence of trace evidence is expected for this run because no runtime proof was started after host preflight failed.

## Negative Control

The normal non-Obsidian control prompt was not submitted.

No behavior was observed for the negative control in this run.

## What This Proof Does Not Prove

- Not a real personal vault proof.
- Not broad MCP/tool access.
- Not command-bus activation.
- Not GitHub context.
- Not release promotion.
- Not complete connector ecosystem proof.
- Not proof that every vault shape or indexing mode works.
- Not proof that `/obsidian` completion succeeds on this host.

## Caveats

- Host Obsidian was missing, so the proof is preflight-blocked.
- No Docker Compose runtime services were started for the live proof.
- No synthetic vault was indexed.
- No worker, queue, provider, retrieval, or completion behavior was exercised.
- No debug trace limitations were encountered because no task ran.
- No known unrelated runtime failures were introduced or observed by this docs-only artifact.

## Validation

Validation commands for this docs/proof artifact:

```bash
./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash
python3 scripts/validate_docs.py
git diff --check
```

Validation results:

- `./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py` - 11 passed.
- `./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py` - 11 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash` - 6 passed, 12 deselected, 4 warnings.
- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

## Final Result

`PARTIAL`

The proof cannot reach `PASS` because Obsidian host preflight is not satisfied. The operator must download and install Obsidian on the host machine before rerunning the synthetic-vault workspace-context proof.
