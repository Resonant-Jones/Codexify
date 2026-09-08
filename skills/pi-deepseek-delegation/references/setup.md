# Pi Model Delegation setup

Use this guide when Pi delegation preflight fails or the operator asks how the plumbing works. The wrapper is development tooling only: it does not change Guardian runtime provider routing, register a second model catalog, or claim release support.

## Architecture

Astra/Codex invokes the compatibility-named shell wrapper. The wrapper asks the installed Pi executable for its current available model table, validates an exact provider/model pair selected by the supervising agent, restricts Pi's tools by delegation mode, and saves a result artifact only for real inference.

Pi owns provider authentication. The wrapper does not inspect `auth.json`, API-key environment variables, credential payloads, or provider-specific secret state. Catalog and check output contains only the current model table and non-secret selection metadata.

Codex remains responsible for task selection, repository permissions, diff review, testing, and integration.

## Canonical source and installation

The canonical source lives at `skills/pi-deepseek-delegation/` in the Codexify repository. The directory and wrapper names are retained for compatibility with proof tooling and historical receipts.

Install from source:

```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --install
```

Check for drift between installed and canonical copies:

```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --check
```

Re-install after updating the repository to synchronize the installed deployment. The installer is atomic and idempotent.

## 1. Install Pi

Pi requires Node.js. Install it using the current package name shown by the Pi project documentation, then verify the executable:

```bash
pi --version
command -v pi
```

Do not install multiple package names unless troubleshooting requires it.

## 2. Configure the selected provider in Pi

Configure authentication using Pi's documented `/login` flow or the selected provider's documented environment/configuration mechanism. Keep credentials outside the repository, skill directory, prompts, shell history, and committed dotfiles.

The wrapper intentionally does not determine whether a provider is authenticated by reading secret-bearing state. A model appears in Pi's available catalog only when Pi itself considers that model available.

## 3. Inspect the live Pi model catalog

Run the wrapper's non-inference catalog path:

```bash
bash /path/to/skill/scripts/pi_deepseek_delegate.sh --catalog
```

This calls:

```bash
pi --list-models
```

The output is the current Pi provider/model table, including the metadata Pi exposes for context, output limit, reasoning, and image input. No prompt, repository content, or inference is sent. The wrapper does not persist the catalog.

Select an exact pair from the returned table. Do not rely on a preferred model order or the first listed entry.

## 4. Configure generic operator defaults (optional)

For repeated use, configure both generic selection variables together:

```bash
export PI_DELEGATION_PROVIDER="PROVIDER_ID"
export PI_DELEGATION_MODEL="MODEL_ID"
export PI_DELEGATION_THINKING="medium"
export PI_DELEGATION_TIMEOUT="180"
```

`PI_DELEGATION_PROVIDER` and `PI_DELEGATION_MODEL` are an all-or-nothing pair. A half-configured pair fails closed. Task flags `--provider`, `--model`, `--thinking`, and `--timeout-seconds` take precedence over generic settings.

The wrapper resolves selection in this order:

1. explicit task `--provider` plus `--model`;
2. both generic operator defaults;
3. explicitly configured legacy DeepSeek compatibility;
4. fail closed with an instruction to inspect `--catalog`.

Legacy `PI_DEEPSEEK_MODEL` remains accepted as an explicit DeepSeek-bound compatibility selection; `PI_DEEPSEEK_PROVIDER`, when supplied, must be `deepseek`, and provider-only legacy configuration fails. Legacy thinking/timeout variables apply only to a selected DeepSeek pair. No provider/model fallback exists.

## 5. Check an exact pair without inference

Use the pair chosen from `--catalog`:

```bash
bash /path/to/skill/scripts/pi_deepseek_delegate.sh \
  --check \
  --provider "PROVIDER_ID" \
  --model "MODEL_ID"
```

`--check` calls Pi's current catalog, verifies the exact pair, and exits before any task or model invocation. It does not require delegation acknowledgement and does not inspect credentials.

For a planned task, `--dry-run` performs the same exact-pair validation and prints the Pi command without invoking it:

```bash
bash /path/to/skill/scripts/pi_deepseek_delegate.sh \
  --mode analysis \
  --provider "PROVIDER_ID" \
  --model "MODEL_ID" \
  --thinking "medium" \
  --task "Bounded task description" \
  --dry-run
```

## 6. Record consent for real inference

After the operator understands that delegated prompts and explicitly selected context leave the local machine for the selected provider, real inference requires:

```bash
export CODEX_PI_DELEGATION_ACK=1
```

Implementation mode additionally requires:

```bash
export CODEX_PI_WRITE_DELEGATION=1
```

These gates are not needed by `--catalog`, `--check`, or `--dry-run` because those paths do not invoke inference. Legacy `CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK` and `CODEX_DEEPSEEK_WRITE_DELEGATION` may satisfy the corresponding gates only for a DeepSeek selection; they cannot authorize another provider.

## 7. Optional synthetic probe

The compatibility `--probe` path is a real inference operation. It uses a fixed synthetic prompt and sends no repository context, but it still requires the generic acknowledgement (or the legacy DeepSeek acknowledgement for a DeepSeek selection):

```bash
CODEX_PI_DELEGATION_ACK=1 \
  bash /path/to/skill/scripts/pi_deepseek_delegate.sh \
  --probe \
  --provider "PROVIDER_ID" \
  --model "MODEL_ID" \
  --thinking low
```

This task's qualification proof must not run a live inference probe.

## 8. Run preflight and delegation

From any directory, first check the exact pair, then run one bounded delegation only after the supervising agent has approved the task and selection:

```bash
bash /path/to/skill/scripts/pi_deepseek_delegate.sh \
  --mode analysis \
  --provider "PROVIDER_ID" \
  --model "MODEL_ID" \
  --task "One bounded assignment" \
  --selection-rationale "Short reason for this pair and task shape"
```

The default artifact directory is `<cwd>/.codex/delegations/pi`. Metadata records the actual provider, model, thinking level, mode, selection source/rationale, tool allowlist, and artifact path.

## Common failures

### `pi: command not found`

Install Pi or fix the shell `PATH`. Verify with `command -v pi`.

### No provider/model selected

Run `--catalog`, select an exact pair, and pass both `--provider` and `--model`, or configure both `PI_DELEGATION_PROVIDER` and `PI_DELEGATION_MODEL`. The wrapper never silently chooses a provider, preferred model, or first-listed model.

### Only one side of a pair is configured

Remove the half-configured generic/task setting or provide the missing side. Do not combine a generic provider with a legacy model or vice versa.

### Provider/model rejected by catalog preflight

The pair is not currently available to Pi. Re-run `--catalog` and choose an exact row. Do not treat a Pi runtime error or an old model ID as proof of availability.

### Delegation acknowledgement missing

Set `CODEX_PI_DELEGATION_ACK=1` only after the operator has approved sending the bounded prompt/context to the selected provider. A legacy DeepSeek acknowledgement cannot authorize another provider.

### Implementation write acknowledgement missing

Set `CODEX_PI_WRITE_DELEGATION=1` only for an isolated, explicitly scoped implementation worktree. Keep the generic gate separate from the inference gate.

### Sensitive context rejected

Do not pass `.env`, `auth.json`, credential files, private keys, or other secret-bearing context. Prepare a sanitized, bounded artifact instead.

### Installed skill drifted from source

Re-install from the canonical source:

```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --install
```

## Verification boundary

Catalog/check/dry-run prove only Pi availability and command construction at the observed time. A real result requires independent supervising-agent verification. None of these paths changes Guardian runtime routing, Campaign Engine routing, supported profiles, provider adapters, or release truth.
