# Pi Delegation Plugin Repair Handoff

## Task

Repair the canonical `pi-deepseek-delegation` plugin in the `Resonant_Skills` repository so Codex can use Pi as a bounded subagent harness with:

1. exact inventory of the models available through Pi;
2. support for any Pi provider/model that the local Pi runtime exposes;
3. explicit model selection without hard-coding DeepSeek V4 Pro;
4. clear reporting when inventory fails because Pi cannot read its settings or lock files;
5. transparent, operator-approved fallback models when the selected model times out or fails.

Codex remains the supervising authority. Pi/DeepSeek output remains untrusted engineering output and requires independent Codex verification.

## Repository and source of truth

Run this task with the following repository as the writable workspace:

```text
/Users/resonant_jones/Keep/Resonant_Constructs/Resonant_Skills
```

The relevant canonical package is:

```text
plugins/pi-deepseek-delegation/
```

The Codexify repository contains a compatibility shell skill and tests that describe part of the desired behavior:

```text
/Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/skills/pi-deepseek-delegation/
```

Use that implementation as behavioral reference, but do not assume it updates the plugin automatically.

## Current problem

The current plugin implementation is too DeepSeek-specific and too tightly coupled to successful inventory:

- `server/pi-adapter.mjs` parses only model IDs matching `deepseek-*`.
- `server/delegation.mjs` chooses `deepseek-v4-pro`, then `deepseek-v4-flash`, then the first listed model.
- `pi_preflight` reports failure when inventory is empty but does not distinguish an unavailable inventory from an unavailable requested model.
- Pi settings-lock failures such as `EPERM` are not surfaced with a structured remediation.
- `pi_delegate` has no explicit fallback candidate list after a timeout or worker failure.
- A requested model is rejected whenever it is not present in a successful inventory listing, even when the operator explicitly supplied the exact model and inventory itself was unavailable.

Observed failure example:

```text
strict preflight found no exact deepseek/deepseek-v4-pro model
Pi hit EPERM creating its settings lock
```

Do not interpret that as proof that the model does not exist. It may mean that Pi could not read its local state.

## Required behavior

### 1. Generic provider/model inventory

Update the Pi adapter to:

- accept an arbitrary provider ID;
- parse exact provider/model rows from Pi inventory output;
- preserve the provider and model identity separately;
- return structured diagnostics including:
  - `models`;
  - `provider`;
  - `exitCode` when available;
  - bounded stderr;
  - an inventory status such as `available`, `empty`, `timed_out`, or `unavailable`;
  - a safe remediation when stderr indicates `EPERM`, permission, or settings-lock failure.

Do not parse diagnostic prose as a model name. Do not invent a model from a preference list.

### 2. Preflight semantics

Keep `pi_preflight` safe and non-secret. It should report:

- the full exact model inventory returned by Pi;
- the configured provider;
- the selected default model, if one can be determined;
- whether inventory succeeded;
- whether the provider is configured;
- whether external-provider consent is present;
- repository accessibility;
- write-delegation state;
- structured errors and remediation.

Preflight should remain `ready: false` when the runtime cannot safely execute an implicitly selected model. It should not collapse these distinct states into one generic “model unavailable” error:

1. provider authentication missing;
2. inventory returned no models;
3. inventory failed because Pi settings are inaccessible;
4. an explicit requested model is not present in a successful inventory;
5. a model is present but execution later fails.

### 3. Explicit model selection

Allow `pi_delegate.model` to be an exact provider model identifier accepted by the input schema.

Rules:

- If inventory succeeded and the requested model is absent, reject before execution with the available alternatives.
- If inventory failed or is unavailable, allow an explicitly supplied model to be attempted when authentication and other policy gates are satisfied.
- Pi remains the final authority on whether the exact model can run.
- Never silently replace an explicitly requested model during preflight or execution.

### 4. Explicit fallback candidates

Extend `pi_delegate` with an optional ordered fallback list, for example:

```json
{
  "model": "deepseek-v4-pro",
  "fallbackModels": ["deepseek-v4-flash", "deepseek-reasoner"]
}
```

Fallback rules:

- fallback must be explicitly supplied by the caller;
- fallback is attempted only after a failed or timed-out run;
- fallback order is deterministic;
- do not retry on policy rejection, invalid scope, missing consent, missing authentication, or repository-access failure;
- if inventory succeeded, reject fallback models absent from the exact inventory and return available alternatives;
- if inventory failed, allow explicitly supplied fallback models to be attempted, subject to normal model identifier validation;
- never silently substitute a fallback: receipt and MCP response must identify every attempt and the successful model, if any;
- preserve the first failure and each subsequent failure in the durable receipt.

Suggested receipt fields:

```text
requestedModel
attemptedModels[]
successfulModel
fallbackUsed
attemptFailures[]
inventoryStatus
availableModels[]
```

### 5. Settings-lock / `EPERM` handling

When Pi cannot create or access its settings lock:

- do not delete the lock automatically;
- do not bypass Pi’s local state silently;
- report the failure as inventory/runtime infrastructure failure;
- recommend an operator-owned writable `PI_CODING_AGENT_DIR` outside the repository;
- do not expose credentials or auth file contents;
- preserve enough bounded stderr for diagnosis;
- keep the distinction between “inventory unavailable” and “model unavailable.”

## Security and authority constraints

Preserve the existing plugin boundaries:

- external-provider consent remains required before repository content is sent to DeepSeek or another external provider;
- read-only delegation remains the default;
- implementation requires explicit write delegation acknowledgement;
- implementation requires an isolated worktree or disposable copy;
- scope allowlists, sensitive-path rejection, output limits, timeouts, receipts, and independent verification remain enforced;
- no arbitrary shell command or arbitrary environment map may be accepted from the MCP caller;
- no credentials, `.env` files, auth files, private keys, or identity-bearing data may be sent to the worker;
- do not ask Pi to commit, push, merge, deploy, publish, rotate secrets, or change permissions.

## Files to inspect and likely change

```text
plugins/pi-deepseek-delegation/server/pi-adapter.mjs
plugins/pi-deepseek-delegation/server/delegation.mjs
plugins/pi-deepseek-delegation/server/index.mjs
plugins/pi-deepseek-delegation/server/security.mjs
plugins/pi-deepseek-delegation/server/receipts.mjs
plugins/pi-deepseek-delegation/tests/delegation.test.mjs
plugins/pi-deepseek-delegation/tests/security.test.mjs
plugins/pi-deepseek-delegation/tests/receipts.test.mjs
plugins/pi-deepseek-delegation/skills/pi-deepseek-delegation/SKILL.md
plugins/pi-deepseek-delegation/skills/pi-deepseek-delegation/references/setup.md
```

Inspect the current package scripts and Node version requirement before editing. Preserve existing package boundaries and test conventions.

## Required tests

Add or update deterministic tests covering:

1. exact inventory parsing for multiple providers;
2. malformed output and diagnostic prose not becoming model IDs;
3. inventory timeout;
4. inventory `EPERM`/settings-lock diagnostics;
5. explicit model accepted when inventory is temporarily unavailable;
6. explicit model rejected when inventory succeeds and does not contain it;
7. fallback after a failed first model;
8. fallback after timeout;
9. no fallback on policy/auth/scope rejection;
10. receipt records requested, attempted, fallback, and successful model identity;
11. no credentials in preflight, receipt, stderr summary, or worker prompt;
12. existing consent, isolation, scope, output-limit, and write-delegation tests remain green.

Run the package’s documented validation, at minimum:

```bash
npm test
npm run build --if-present
```

Also run any repository-provided plugin validator and inspect the complete diff.

## Acceptance criteria

The task is complete only when:

- the MCP plugin, not only the compatibility shell wrapper, implements the behavior above;
- `pi_preflight` reports exact available provider/model options and actionable inventory failures;
- `pi_delegate` supports an explicitly requested model and explicit ordered fallback candidates;
- no model is silently substituted;
- all attempts and model identity are present in the receipt;
- existing security and consent gates remain intact;
- focused Node tests pass;
- `git diff --check` passes;
- the complete diff contains no credentials, generated auth state, or unrelated files;
- installed plugin/skill copies are synchronized only through the repository’s documented installer or packaging workflow.

## Handoff report required

Return:

- summary of changes;
- files changed;
- exact validation commands and results;
- selected/requested model behavior;
- fallback behavior and receipt example;
- how `EPERM` inventory failures are reported;
- any remaining limitations;
- commit hash if commit authority is available.

Do not claim live Pi/DeepSeek proof unless the runtime was actually exercised. Distinguish static tests, local runtime proof, external provider execution, and installed-plugin synchronization.
