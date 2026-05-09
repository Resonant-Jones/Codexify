# Supersession Notice

This artifact recorded a prior PASS on 2026-05-07.

Later testing invalidated treating this PASS as current release evidence for workspace-local Obsidian retrieval.

Use `/docs/proofs/2026-05-07-workspace-obsidian-e2e-supersession.md` for the current interpretation.

---

# Workspace Obsidian E2E Proof

## Artifact
- Artifact date: `2026-05-07`
- Proof class: `workspace-local retrieval completion proof`
- Runtime path: `supported local Docker Compose`
- Commit under test: `a5d6239ef26105ab45125e9f43d22fd2078d9584`
- Scope: release-evidence for the supported local Compose path only; not a release signoff or install-mode widening.

## Proof Command
```bash
BASE=http://localhost:8888 GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)" ./.venv/bin/python scripts/proofs/prove_workspace_obsidian_e2e.py
```

## Validation Commands
```bash
./.venv/bin/pytest -v tests/proofs/test_workspace_obsidian_e2e_contract.py
./.venv/bin/pytest -v tests/routes/test_chat_profile_trace.py
./.venv/bin/python scripts/validate_docs.py
git diff --check
```

## Observed Proof Result
- `obsidian_count=1`
- `obsidian_injected=True`
- `VERDICT: PASS`

## Evidence Interpretation
- Substrate searchability is necessary but not sufficient.
- Broker selection is necessary but not sufficient.
- Completion-context injection is necessary.
- The worker-visible completion payload is the canonical proof surface for this seam.
- The debug trace remains diagnostic-only.

## Explicit Non-Goals
- No sync automation
- No first-class Obsidian connector UX
- No non-Compose install claim
- No global retrieval widening
- No replacement of thread, project, or personal-knowledge source modes

## Release-Readiness Conclusion
Workspace-local Obsidian retrieval is now release-evidenced on the supported local Compose path for the tested commit.

Broader beta release still depends on the remaining current-state release checklist.
