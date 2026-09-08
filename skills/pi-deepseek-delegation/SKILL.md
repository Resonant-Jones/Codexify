---
name: pi-deepseek-delegation
description: Delegate bounded software-engineering subtasks from Codex to an explicitly selected Pi provider/model pair. Use when a supervising agent would benefit from an independent architecture opinion, broad read-only code analysis, parallel debugging hypotheses, code review, test or documentation drafting, or a candidate implementation in an isolated worktree. Also use when asked to inspect, set up, diagnose, or govern the Pi delegation control plane. Do not use for trivial tasks, destructive operations, secret-bearing context, or as a substitute for the supervising agent's final verification and integration.
---

# Pi Model Delegation

This skill is the compatibility-preserving source for bounded Pi model delegation. The directory, skill identifier, wrapper filename, and installed path retain the legacy `pi-deepseek-delegation` names because repository proof surfaces reference them. The user-facing capability is provider/model selection through Pi's current registry.

Canonical source: `skills/pi-deepseek-delegation/` in the Codexify repository.
Installed deployment: `$HOME/.codex/skills/pi-deepseek-delegation/`.

**Install:** `bash skills/pi-deepseek-delegation/scripts/install.sh --install`
**Check drift:** `bash skills/pi-deepseek-delegation/scripts/install.sh --check`

Keep Astra/Codex as the supervising agent. Launch Pi as one ephemeral, bounded worker for one explicit assignment, collect its result, and independently verify every material claim or change before integration. Pi is not the model-selection authority, conversation owner, memory owner, or canonical persistence owner.

Use the bundled script at `{baseDir}/scripts/pi_deepseek_delegate.sh`. It reads Pi's current `pi --list-models` catalog, validates an exact provider/model pair, applies the mode-bounded tool allowlist, and saves a local result artifact only for real inference. It does not create a second model registry, inspect provider credentials, or patch Pi core. Read `{baseDir}/references/setup.md` for setup and `{baseDir}/references/delegation-contract.md` for a non-trivial handoff.

## Supervising control loop

Follow this sequence:

1. Inspect the task, repository state, trust boundary, and allowed scope.
2. Decide whether delegation creates meaningful leverage. Do not delegate merely because the task is non-trivial.
3. Run the non-inference catalog path:

   ```bash
   bash {baseDir}/scripts/pi_deepseek_delegate.sh --catalog
   ```

4. Choose one currently registered provider/model pair deliberately for the bounded subtask. Consider reasoning requirement, coding/debugging strength, context volume, latency, known cost, image capability when required, and task shape. These are selection considerations, not a permanent ranking.
5. Supply `--provider` and `--model` explicitly, and choose the thinking level explicitly when it matters.
6. Record the selected pair and a short selection rationale in the supervising delegation receipt. The wrapper can retain the rationale in its metadata through `--selection-rationale`.
7. Run the wrapper's exact-pair `--check` or `--dry-run` preflight, then run Pi once only when the delegation is approved and consent gates are present.
8. Inspect the result and any artifact paths, then verify all material claims independently with the supervising agent's own code, tests, and repository checks.

Never treat Pi output as authoritative. Reject unverifiable claims, unrelated edits, invented APIs, weakened checks, secret-bearing context, or results that exceed the granted scope.

## Provider/model selection policy

The wrapper resolves an exact pair in this order:

1. Task invocation `--provider` plus `--model`.
2. Generic operator defaults `PI_DELEGATION_PROVIDER` plus `PI_DELEGATION_MODEL`, only when both are configured.
3. Narrow legacy DeepSeek compatibility when `PI_DEEPSEEK_MODEL` is explicitly configured. Its variable namespace binds that legacy selection to `deepseek`; `PI_DEEPSEEK_PROVIDER`, when present, must also be `deepseek`.
4. Fail closed and direct the supervising agent to inspect `--catalog`.

Only one side of an explicit task pair or generic pair is an error. A legacy `PI_DEEPSEEK_PROVIDER` without a model is also an error. There is no implicit provider, preferred model order, first-listed-model fallback, model ranking, or autonomous Pi selection. An explicit user-requested pair overrides Astra's preference only after the current Pi catalog confirms that pair is available.

Generic operator settings are:

```text
PI_DELEGATION_PROVIDER
PI_DELEGATION_MODEL
PI_DELEGATION_THINKING
PI_DELEGATION_TIMEOUT
```

Task flags override generic settings. Legacy `PI_DEEPSEEK_THINKING` and `PI_DEEPSEEK_TIMEOUT` are compatibility settings only for a selected `deepseek` pair. The wrapper's non-routing thinking and timeout defaults remain `high` and `180` seconds when no corresponding setting is supplied.

## Consent and preflight gates

`--catalog`, `--check`, and `--dry-run` do not invoke inference and do not require delegation consent. They still require an exact pair for `--check` and `--dry-run`, and they validate that pair against the current Pi catalog.

Real inference requires:

```text
CODEX_PI_DELEGATION_ACK=1
```

Implementation mode additionally requires:

```text
CODEX_PI_WRITE_DELEGATION=1
```

Legacy `CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK` and `CODEX_DEEPSEEK_WRITE_DELEGATION` may satisfy the corresponding gates only when the resolved provider is exactly `deepseek`. They cannot authorize another provider. The supervising agent must never set an acknowledgement silently or treat a preflight as consent.

The catalog and check paths use only Pi's available model listing. They do not read `auth.json`, API-key environment variables, credential payloads, or secret-bearing files. The wrapper rejects sensitive context filenames before a real worker call.

## Decide whether to delegate

Delegate when at least two of these are true:

- The task has a cleanly separable subproblem.
- An independent model perspective could expose blind spots.
- The work requires broad repository scanning or hypothesis generation.
- The result can be verified with a diff, tests, static checks, or cited file evidence.
- Delegation saves supervising-agent context for planning and final integration.
- The subtask is repetitive or parallelizable, such as tests, docs, review, or migration inventory.

Do not delegate when the task is trivial, underspecified, destructive, secret-bearing, production-facing, release/merge/push/deploy work, an authentication/cryptography/authorization change that needs write authority, or a result that cannot be independently verified. This task itself changes the delegation control plane and must not be delegated through Pi.

## Construct the handoff

Make the task independently executable. Include:

- Objective: one concrete outcome.
- Scope: exact modules, files, or behavior to inspect.
- Constraints: interfaces, conventions, non-goals, and forbidden actions.
- Evidence: require file paths, symbols, and line references where practical.
- Verification: tests or checks the worker may run and what Astra/Codex will rerun.
- Deliverable: findings, patch, test plan, or structured recommendation.

Do not send the entire conversation transcript. Summarize only the context necessary for the subtask. Never include credentials, `.env` files, private keys, tokens, personal data, or unbounded repository context.

## Choose a delegation mode

### Analysis

Read-only repository mapping, architecture questions, migration inventories, or debugging hypotheses:

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode analysis \
  --cwd "$PWD" \
  --provider "$PI_PROVIDER" \
  --model "$PI_MODEL" \
  --thinking "$PI_THINKING" \
  --selection-rationale "Chosen for independent architecture mapping at the required context depth." \
  --task "Map the bounded subproblem. Cite relevant files and identify unresolved assumptions. Do not edit files."
```

### Review

Run after Astra/Codex has produced a plan or patch. Ask Pi to look for named failure classes rather than “review everything.” Review remains read-only:

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode review \
  --provider "$PI_PROVIDER" \
  --model "$PI_MODEL" \
  --context-file /tmp/candidate.diff \
  --task "Review this candidate for authorization bypasses and state inconsistencies. Do not edit files."
```

### Test

Run or propose bounded verification. Test mode permits `bash` but not `write` or `edit`:

```bash
bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode test \
  --provider "$PI_PROVIDER" \
  --model "$PI_MODEL" \
  --task "Run only the named narrow tests and report exact commands, failures, and likely causes. Do not edit files."
```

### Implementation

Use only in an isolated git worktree or disposable copy. Require explicit write delegation approval and keep the scope narrow:

```bash
git worktree add ../pi-candidate -b codex/pi-candidate HEAD
CODEX_PI_DELEGATION_ACK=1 CODEX_PI_WRITE_DELEGATION=1 \
  bash {baseDir}/scripts/pi_deepseek_delegate.sh \
  --mode implementation \
  --cwd ../pi-candidate \
  --provider "$PI_PROVIDER" \
  --model "$PI_MODEL" \
  --task "Implement only the explicitly scoped change. Do not commit or push."
```

Never ask Pi to commit, push, merge, deploy, publish, rotate secrets, or modify production systems.

## Mode permissions

Preserve these exact Pi built-in tool allowlists:

| Mode | Tools |
|---|---|
| `analysis`, `review` | `read,grep,find,ls` |
| `test` | `read,grep,find,ls,bash` |
| `implementation` | `read,write,edit,grep,find,ls,bash` |

Tool availability is not authority. The worker remains bounded and untrusted; Guardian, repository policy, and Astra/Codex retain authority over any resulting action.

## Verify and report the return

After every real delegation:

1. Read the saved result path printed by the wrapper.
2. Check every cited file and technical claim against the repository.
3. For write delegation, inspect `git status` and `git diff --check`, then review the complete diff.
4. Re-run relevant tests under Astra/Codex control.
5. Reject unrelated edits, unverifiable claims, invented APIs, weakened checks, or unexplained dependency changes.
6. Apply or reproduce only accepted parts in the intended branch.

Real result metadata records the actual provider, model, thinking level, mode, selection source/rationale, tool allowlist, and artifact path. The default artifact directory is `<cwd>/.codex/delegations/pi`.

If Pi is missing, the catalog cannot be read, the selected pair is unavailable, consent is absent, the process fails, or the result is empty, delegation did not occur. Preserve the bounded error, continue directly when feasible, and report the limitation without fabricating a worker opinion.

## Compatibility naming

The following names are intentionally retained for this slice and are legacy compatibility identifiers:

- directory: `skills/pi-deepseek-delegation/`
- skill identifier: `pi-deepseek-delegation`
- wrapper: `scripts/pi_deepseek_delegate.sh`
- installed target: `$HOME/.codex/skills/pi-deepseek-delegation/`

Renaming them is a separate migration task because repository proof tooling and historical receipts reference them.
