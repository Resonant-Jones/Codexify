# Dev-Kit Inventory

This is an inventory of existing repo resources a trusted collaborator can use.

**Inventory is not proof. Run the command and record the result.**

## Pick Your Dev Kit

| Kit / Resource | What it is | When to use it | Where it lives | Notes / proof boundary |
| --- | --- | --- | --- | --- |
| Local setup helpers | Scripts and maintenance helpers for preparing a local environment | When you need to bootstrap or repair a local dev setup | [`scripts/dev/`](../../scripts/dev/), [`scripts/maintenance/`](../../scripts/maintenance/), [`scripts/preflight.sh`](../../scripts/preflight.sh) | Helpful for setup, but not runtime proof by itself |
| Docker Compose runtime | The supported local service stack definition | When you need the full local backend stack | [`docker-compose.yml`](../../docker-compose.yml) | Compose shape is runtime topology, not live health proof |
| Backend validation | Repo scripts that validate backend-related paths and supported loops | When you need backend-focused checks or smoke validation | [`scripts/validate_core_loops.sh`](../../scripts/validate_core_loops.sh), [`scripts/validate_doc_upload_embedding.sh`](../../scripts/validate_doc_upload_embedding.sh), [`scripts/verification/`](../../scripts/verification/), [`scripts/dev/run_tests.sh`](../../scripts/dev/run_tests.sh) | Validation output is surface-specific proof only |
| Frontend validation | Frontend package scripts for build, lint, format, and test runs | When you need to verify UI changes | [`package.json`](../../package.json), [`frontend/package.json`](../../frontend/package.json), [`frontend/src/`](../../frontend/src/) | Passing tests prove the checked UI surface, not the entire app |
| Guardian work brief / reporting | Scripts that generate or inspect work briefs for Guardian-oriented work | When you need a task summary or operator-facing brief | [`scripts/guardian_work_brief.py`](../../scripts/guardian_work_brief.py), [`scripts/guardian/generate_work_brief.py`](../../scripts/guardian/generate_work_brief.py) | Reporting aids collaboration; it does not replace source evidence |
| Architecture docs | Current-state and subsystem docs for orientation and boundary checks | When you need to understand how the repo is supposed to hang together | [`docs/architecture/`](../architecture/) | Use these for orientation; `00-current-state.md` is the release-truth anchor |
| Task specs / work packets | Canonical docs for scoped tasks and issue-shaped work packets | When you need to define a bounded task before implementation | [`docs/Ops/codexify-issue-template-contract.md`](../Ops/codexify-issue-template-contract.md), [`docs/tasks/`](../tasks/), [`docs/Campaign/`](../Campaign/) | These describe the packet shape; they do not execute work |
| Git worktree inspection | Native Git worktree commands and workspace metadata | When you need to inspect or reason about parallel working folders | `git worktree list`, `.git/worktrees/` | Native Git toolchain; no dedicated repo wrapper found yet |
| Health checks | Fast checks for supported-path and operator status surfaces | When you need quick runtime signals | [`docs/architecture/config-and-ops.md`](../architecture/config-and-ops.md), [`docs/architecture/00-current-state.md`](../architecture/00-current-state.md), [`scripts/verification/run_supported_path_proof.sh`](../../scripts/verification/run_supported_path_proof.sh), [`scripts/verification/validate_beta1_core_gate.sh`](../../scripts/verification/validate_beta1_core_gate.sh) | Health checks are proof of the checked endpoint or path only |

## Useful Script Families

- `scripts/verification/` for proof-oriented checks
- `scripts/dev/` for local helper flows
- `scripts/maintenance/` for environment and repair tasks
- `scripts/guardian/` for Guardian-oriented reporting and brief generation
- `scripts/docs/` for document-oriented helper flows

## Needed But Not Implemented Yet

- A dedicated collaborator-onboarding runner that packages the reading order and recommended checks into one command.
- A dedicated Git worktree inspection helper inside the repo.
- A single all-in-one health-check bundle for collaborator orientation.

These gaps are normal. The point of the inventory is to make them visible instead of pretending they already exist.
