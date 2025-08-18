#!/usr/bin/env bash
set -euo pipefail

# Minimal Batch Orchestrator harness
# - Creates a timestamped run directory under artifacts/runs/
# - Provides paths to the manifest and prompt pack for your agent runtime
# - Captures orchestrator output to summary.md (integration-dependent)

RUN_ID="$(date +%Y%m%d-%H%M%S)"
ART="artifacts/runs/$RUN_ID"
MANIFEST="docs/prompts/run-manifest.yml"
PACK="docs/prompts/infra-codex-pack.md"

mkdir -p "$ART"

echo "Starting batch run $RUN_ID" | tee "$ART/summary.md" >/dev/null
echo "Manifest: $MANIFEST" | tee -a "$ART/summary.md" >/dev/null
echo "Prompt Pack: $PACK" | tee -a "$ART/summary.md" >/dev/null

echo >> "$ART/summary.md"

# Auto-detect an agent CLI if not explicitly set
if [[ -z "${RUN_AGENT_CMD:-}" ]]; then
  if command -v codex-cli >/dev/null 2>&1; then
    RUN_AGENT_CMD="codex-cli run"
    RUN_AGENT_PACK_FLAG=${RUN_AGENT_PACK_FLAG:---prompt-pack}
    RUN_AGENT_MANIFEST_FLAG=${RUN_AGENT_MANIFEST_FLAG:---manifest}
    RUN_AGENT_ARTIFACTS_FLAG=${RUN_AGENT_ARTIFACTS_FLAG:---artifacts}
  elif command -v groq-code-cli >/dev/null 2>&1; then
    # Default to a common subcommand name; override via env if different in your setup
    RUN_AGENT_CMD="groq-code-cli orchestrate"
    RUN_AGENT_PACK_FLAG=${RUN_AGENT_PACK_FLAG:---prompt-pack}
    RUN_AGENT_MANIFEST_FLAG=${RUN_AGENT_MANIFEST_FLAG:---manifest}
    RUN_AGENT_ARTIFACTS_FLAG=${RUN_AGENT_ARTIFACTS_FLAG:---artifacts}
  fi
fi

# Optional: invoke an agent CLI if provided via RUN_AGENT_CMD
# Expected flags (adapt as needed):
#   $RUN_AGENT_CMD --prompt-pack "$PACK" --manifest "$MANIFEST" --artifacts "$ART"
if [[ "${RUN_AGENT_CMD:-}" != "" ]]; then
  echo "Invoking agent: $RUN_AGENT_CMD" | tee -a "$ART/summary.md" >/dev/null
  # Allow customizing flags for different CLIs
  PACK_FLAG=${RUN_AGENT_PACK_FLAG:---prompt-pack}
  MANIFEST_FLAG=${RUN_AGENT_MANIFEST_FLAG:---manifest}
  ARTIFACTS_FLAG=${RUN_AGENT_ARTIFACTS_FLAG:---artifacts}
  EXTRA_ARGS=${RUN_AGENT_EXTRA:-}
  # Build argv as an array to preserve spaces
  IFS=' ' read -r -a CMD_ARR <<< "$RUN_AGENT_CMD"
  ARGV=("${CMD_ARR[@]}" "$PACK_FLAG" "$PACK" "$MANIFEST_FLAG" "$MANIFEST" "$ARTIFACTS_FLAG" "$ART")
  if [[ -n "$EXTRA_ARGS" ]]; then
    # shellcheck disable=SC2206
    EXTRA_ARR=($EXTRA_ARGS)
    ARGV+=("${EXTRA_ARR[@]}")
  fi
  set +e
  "${ARGV[@]}" | tee -a "$ART/summary.md"
  AGENT_RC=${PIPESTATUS[0]}
  set -e
  echo "Agent exit code: $AGENT_RC" | tee -a "$ART/summary.md" >/dev/null
else
  echo "--- Next step (manual integration) ---" >> "$ART/summary.md"
  cat <<'NOTE' | tee -a "$ART/summary.md" >/dev/null
Feed the following to your agent runtime:

1) Orchestrator System Prompt from infra-codex-pack.md (section 11.2 Batch Orchestrator Prompt)
2) Inputs:
   - docs/prompts/infra-codex-pack.md
   - docs/prompts/run-manifest.yml
3) Output target:
   - artifacts/runs/$RUN_ID/summary.md (write PLAN/DIFF/RUN/TEST/ACCEPT per task under subfolders)

Auto-run: set environment variables, e.g. for a generic CLI:

  RUN_AGENT_CMD="codex-cli run" \
  RUN_AGENT_PACK_FLAG="--prompt-pack" \
  RUN_AGENT_MANIFEST_FLAG="--manifest" \
  RUN_AGENT_ARTIFACTS_FLAG="--artifacts" \
  RUN_AGENT_EXTRA="--concurrency 3" \
  ./tools/run-batch.sh

Or for Groq CLI (adjust subcommand/flags if needed):

  RUN_AGENT_CMD="groq-code-cli orchestrate" \
  RUN_AGENT_PACK_FLAG="--prompt-pack" \
  RUN_AGENT_MANIFEST_FLAG="--manifest" \
  RUN_AGENT_ARTIFACTS_FLAG="--artifacts" \
  ./tools/run-batch.sh

Flags are customizable for different tools.
NOTE
fi

echo "Run artifacts: $ART"
