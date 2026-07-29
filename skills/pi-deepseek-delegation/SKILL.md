---
name: pi-deepseek-delegation
description: Delegate bounded software-engineering subtasks from Codex to DeepSeek through the Pi coding-agent harness. Use when Codex is working in a repository and would benefit from an independent architecture opinion, broad read-only code analysis, parallel debugging hypotheses, code review, test or documentation drafting, or a candidate implementation in an isolated worktree. Also use when asked to set up, diagnose, or govern Codex-to-DeepSeek delegation through the `pi` CLI. Do not use for trivial tasks, destructive operations, secret-bearing context, or as a substitute for Codex's final verification and integration.
---

# Pi DeepSeek Delegation

Canonical source: `skills/pi-deepseek-delegation/` in the Codexify repository.
Installed deployment: `$HOME/.codex/skills/pi-deepseek-delegation/`.

**Install:** `bash skills/pi-deepseek-delegation/scripts/install.sh --install`
**Check drift:** `bash skills/pi-deepseek-delegation/scripts/install.sh --check`

Keep Codex as the supervising agent. Launch Pi as an ephemeral DeepSeek worker for one bounded assignment, collect its result, then independently verify every material claim or change before integration.

Use the bundled script at `{baseDir}/scripts/pi_deepseek_delegate.sh`. This wrapper uses Pi's built-in `deepseek` provider — no custom provider or Pi-core patch is required. Read `{baseDir}/references/setup.md` when Pi or DeepSeek is not configured. Read `{baseDir}/references/delegation-contract.md` when constructing a non-trivial handoff.

## Operating model

Follow this control loop:

1. Inspect the task and repository state.
2. Decide whether delegation creates meaningful leverage.
3. Bound the assignment, context, tools, and expected output.
4. Run Pi once with DeepSeek in an ephemeral session.
5. Inspect the returned evidence and any filesystem changes.
6. Run Codex's own tests, checks, and code review.
7. Integrate selectively or reject the result.
8. Report what was delegated, what was accepted, and how it was verified.

Never treat DeepSeek's output as authoritative. Treat it as an untrusted engineering contribution from a capable external collaborator.

## Decide whether to delegate

Delegate when at least two of these are true:

- The task has a cleanly separable subproblem.
- An independent model perspective could expose blind spots.
- The work requires broad repository scanning or hypothesis generation.
- The result can be verified with a diff, tests, static checks, or cited file evidence.
- Delegation saves Codex context for planning and final integration.
- The subtask is repetitive or parallelizable, such as tests, docs, review, or migration inventory.

Prefer these delegation targets:

- Read-only architecture or dependency mapping.
- A second opinion on a debugging theory or implementation plan.
- Focused review for correctness, regressions, security smells, or unnecessary complexity.
- Candidate tests, documentation, migration notes, or mechanical refactors.
- A candidate implementation inside a dedicated worktree when write delegation is explicitly enabled.

Do not delegate when any of these apply:

- Codex can complete and verify the task directly with little effort.
- The task is underspecified and requires a user decision.
- The context includes credentials, `.env` files, private keys, tokens, regulated data, or identity-bearing personal data.
- The task requires destructive commands, production access, deployment, release, merge, commit, push, secret rotation, or permission changes.
- The task changes authentication, cryptography, authorization, billing, destructive migrations, or identity boundaries. Allow only read-only review unless the user explicitly requests otherwise.
- The result cannot be independently verified.

## Establish external-provider consent

Before the first real delegation in a repository, disclose that selected repository content and prompts will be sent to DeepSeek through Pi. Obtain explicit user approval if that consent is not already clear from the request.

After approval, require `CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1` in the environment. Never set this variable silently on the user's behalf.

For write-capable delegation, also require `CODEX_DEEPSEEK_WRITE_DELEGATION=1`. Prefer read-only delegation by default.

## Preflight

Run:

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh --check
```

If preflight fails, follow `{baseDir}/references/setup.md`. Do not claim delegation occurred.

Model selection order:

1. Use `--model` supplied for the task.
2. Otherwise use `PI_DEEPSEEK_MODEL`.
3. Otherwise the wrapper selects from `pi --list-models deepseek`, preferring:
   - `deepseek-v4-pro`
   - `deepseek-v4-flash`
4. Falls back to the first listed model for the provider.

Never hardcode a stale model ID. Rely on Pi's current registry output.

Provider selection:

1. Use `--provider` supplied for the task.
2. Otherwise use `PI_DEEPSEEK_PROVIDER`.
3. Defaults to Pi's built-in `deepseek` provider.

Do not register a custom provider. Do not patch Pi core.

## Construct the handoff

Make the task independently executable. Include:

- Objective: one concrete outcome.
- Scope: exact modules, files, or behavior to inspect.
- Constraints: interfaces, conventions, non-goals, and forbidden actions.
- Evidence: require file paths, symbols, and line references where practical.
- Verification: tests or checks the worker may run and what Codex will rerun.
- Deliverable: findings, patch, test plan, or structured recommendation.

Do not send the entire conversation transcript. Summarize only the context necessary for the subtask.

Use the contract template in `{baseDir}/references/delegation-contract.md` for complex work.

## Choose a delegation mode

### Analysis

Use for repository mapping, architecture questions, migration inventories, or debugging hypotheses. Keep the worker read-only.

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode analysis \
  --cwd "$PWD" \
  --task "Map the request path from the API route to persistence. Cite relevant files and identify unresolved assumptions. Do not edit files."
```

### Review

Use after Codex has produced a plan or patch. Ask DeepSeek to look for specific failure classes rather than "review everything."

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode review \
  --cwd "$PWD" \
  --context-file /tmp/candidate.diff \
  --task "Review this candidate diff for authorization bypasses, state inconsistencies, and missing tests. Return findings ordered by severity. Do not edit files."
```

### Test

Use to run or propose bounded verification. This mode permits shell execution but not file editing.

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode test \
  --cwd "$PWD" \
  --task "Run the narrowest relevant tests for the parser change. Report exact commands, failures, and likely causes. Do not edit files."
```

### Implementation

Use only in an isolated git worktree or disposable copy. Require explicit write delegation approval.

```bash
git worktree add ../deepseek-candidate -b deepseek/candidate HEAD
CODEX_DEEPSEEK_WRITE_DELEGATION=1 \
  bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode implementation \
  --cwd ../deepseek-candidate \
  --task "Implement the bounded parser change only. Do not commit or push. Run the named unit tests and summarize changed files."
```

Never ask Pi or DeepSeek to commit, push, merge, deploy, or modify production systems.

## Verify the return

After every delegation:

1. Read the saved result path printed by the script.
2. Check every cited file and technical claim against the repository.
3. For write delegation, inspect `git status` and `git diff --check`, then review the complete diff.
4. Re-run relevant tests under Codex control. Do not rely only on worker-reported test output.
5. Reject unrelated edits, unverifiable claims, invented APIs, weakened checks, or unexplained dependency changes.
6. Apply or reproduce only the accepted parts in the intended branch.

For security-sensitive findings, verify with primary documentation or direct code evidence before acting.

## Failure behavior

If Pi is missing, authentication fails, the model is unavailable, the process exits non-zero, or the output is empty:

- Stop the delegation path.
- Preserve the error output.
- Continue with Codex directly when feasible.
- Tell the user that delegation did not occur and why.
- Never fabricate a DeepSeek opinion or imply that a command ran successfully.

If DeepSeek exceeds scope, edits forbidden files, or produces a noisy patch, discard the worktree or revert the candidate changes. Do not spend more integration effort than direct implementation would have required.

## Reporting

In the final engineering summary, include a compact delegation receipt:

- Delegated task and mode.
- DeepSeek model selected by Pi.
- Result or artifact path.
- Accepted and rejected contributions.
- Verification commands Codex ran.
- Remaining uncertainty.

Do not expose API keys, hidden reasoning, or raw credentials in logs or summaries.
