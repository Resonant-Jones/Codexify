#!/usr/bin/env bash
set -euo pipefail

MODE="analysis"
TASK=""
TASK_FILE=""
CWD="$PWD"
MODEL="${PI_DEEPSEEK_MODEL:-}"
PROVIDER="${PI_DEEPSEEK_PROVIDER:-deepseek}"
FALLBACK_MODELS=()
FALLBACK_ON_FAILURE=0
THINKING="${PI_DEEPSEEK_THINKING:-high}"
OUTPUT_DIR=""
CHECK_ONLY=0
PROBE_ONLY=0
DRY_RUN=0
TIMEOUT_SECONDS="${PI_DEEPSEEK_TIMEOUT:-180}"
JSON_OUTPUT=0
CONTEXT_FILES=()

usage() {
  cat <<'USAGE'
Usage:
  pi_deepseek_delegate.sh --check
  pi_deepseek_delegate.sh --probe
  pi_deepseek_delegate.sh --task "..." [options]

Options:
  --mode analysis|review|test|implementation
  --task TEXT
  --task-file PATH
  --context-file PATH       Repeatable. Passed to Pi as an @file argument.
  --cwd DIR                 Delegated working directory. Default: current directory.
  --provider PROVIDER       Pi provider ID. Default: deepseek (built-in).
  --model MODEL             Exact Pi model ID. Overrides PI_DEEPSEEK_MODEL.
  --fallback-model MODEL    Repeatable fallback model (requires --fallback-on-failure).
  --fallback-on-failure     Try listed fallback models after a failed or timed-out run.
  --thinking LEVEL          off|minimal|low|medium|high|xhigh|max. Default: high.
  --timeout-seconds N       Timeout for the delegation. Default: 180.
  --output-dir DIR          Default: <cwd>/.codex/delegations/deepseek
  --check                   Validate local Pi and DeepSeek configuration only.
  --probe                   Minimal live provider inference with synthetic prompt.
  --dry-run                 Print the planned command without invoking Pi.
  --json                    Output machine-readable JSON on stdout.
  -h, --help

Required environment for real calls:
  CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1

Additional requirement for implementation mode:
  CODEX_DEEPSEEK_WRITE_DELEGATION=1
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ $# -ge 2 ]] || fail "--mode requires a value"
      MODE="$2"
      shift 2
      ;;
    --task)
      [[ $# -ge 2 ]] || fail "--task requires a value"
      TASK="$2"
      shift 2
      ;;
    --task-file)
      [[ $# -ge 2 ]] || fail "--task-file requires a value"
      TASK_FILE="$2"
      shift 2
      ;;
    --context-file)
      [[ $# -ge 2 ]] || fail "--context-file requires a value"
      CONTEXT_FILES+=("$2")
      shift 2
      ;;
    --cwd)
      [[ $# -ge 2 ]] || fail "--cwd requires a value"
      CWD="$2"
      shift 2
      ;;
    --provider)
      [[ $# -ge 2 ]] || fail "--provider requires a value"
      PROVIDER="$2"
      shift 2
      ;;
    --model)
      [[ $# -ge 2 ]] || fail "--model requires a value"
      MODEL="$2"
      shift 2
      ;;
    --fallback-model)
      [[ $# -ge 2 ]] || fail "--fallback-model requires a value"
      FALLBACK_MODELS+=("$2")
      shift 2
      ;;
    --fallback-on-failure)
      FALLBACK_ON_FAILURE=1
      shift
      ;;
    --thinking)
      [[ $# -ge 2 ]] || fail "--thinking requires a value"
      THINKING="$2"
      shift 2
      ;;
    --timeout-seconds)
      [[ $# -ge 2 ]] || fail "--timeout-seconds requires a value"
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || fail "--output-dir requires a value"
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --check)
      CHECK_ONLY=1
      shift
      ;;
    --probe)
      PROBE_ONLY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

case "$MODE" in
  analysis|review|test|implementation) ;;
  *) fail "unsupported mode: $MODE" ;;
esac

case "$THINKING" in
  off|minimal|low|medium|high|xhigh|max) ;;
  *) fail "unsupported thinking level: $THINKING" ;;
esac

command -v pi >/dev/null 2>&1 || fail "pi is not installed or not on PATH"
[[ -d "$CWD" ]] || fail "working directory does not exist: $CWD"
CWD="$(cd "$CWD" && pwd)"

AUTH_CONFIGURED=0
if [[ -n "${DEEPSEEK_API_KEY:-}" && "$PROVIDER" == "deepseek" ]]; then
  AUTH_CONFIGURED=1
elif [[ -f "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/auth.json" ]]; then
  if python3 -c "
import json, sys
try:
    with open('${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/auth.json') as f:
        auth = json.load(f)
    if '${PROVIDER}' in auth:
        sys.exit(0)
except Exception:
    pass
sys.exit(1)
" 2>/dev/null; then
    AUTH_CONFIGURED=1
  fi
fi

MODEL_LIST_STATUS=0
MODEL_LIST="$(pi --list-models "$PROVIDER" 2>&1)" || MODEL_LIST_STATUS=$?

AVAILABLE_MODELS="$(printf '%s\n' "$MODEL_LIST" | awk -v provider="$PROVIDER" '$1 == provider && $2 ~ /^[A-Za-z0-9._:\/*-]+$/ { print $2 }' | awk '!seen[$0]++')"

select_model() {
  if [[ -n "$MODEL" ]]; then
    printf '%s' "$MODEL"
    return
  fi

  local preferred_order="deepseek-v4-pro deepseek-v4-flash"
  local candidate

  for candidate in $preferred_order; do
    if printf '%s\n' "$AVAILABLE_MODELS" | grep -Fx "$candidate" >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return
    fi
  done

  # Fall back to first listed model for the provider after the header line
  local first_model
  first_model="$(printf '%s\n' "$AVAILABLE_MODELS" | sed -n '1p')"
  if [[ -n "$first_model" ]]; then
    printf '%s' "$first_model"
    return
  fi

  printf ''
}

MODEL="$(select_model)"

if [[ $CHECK_ONLY -eq 1 ]]; then
  if [[ $JSON_OUTPUT -eq 1 ]]; then
    printf '{"pi":"%s","provider":"%s","auth":"%s","model":"%s"}\n' \
      "$(command -v pi)" \
      "$PROVIDER" \
      "$([[ $AUTH_CONFIGURED -eq 1 ]] && printf 'configured' || printf 'missing')" \
      "${MODEL:-null}"
  else
    printf 'pi=%s\n' "$(command -v pi)"
    printf 'provider=%s\n' "$PROVIDER"
    printf 'deepseek_auth=%s\n' "$([[ $AUTH_CONFIGURED -eq 1 ]] && printf configured || printf missing)"
    if [[ -n "$MODEL" ]]; then
      printf 'deepseek_model=%s\n' "$MODEL"
    else
      printf 'deepseek_model=missing\n'
    fi
    if [[ -n "$MODEL_LIST" ]]; then
      printf '%s\n' 'available_models_begin'
      printf '%s\n' "$MODEL_LIST"
      printf '%s\n' 'available_models_end'
    fi
    printf 'inventory_status=%s\n' "$([[ $MODEL_LIST_STATUS -eq 0 ]] && printf available || printf unavailable)"
    if [[ $MODEL_LIST_STATUS -ne 0 ]] && printf '%s' "$MODEL_LIST" | grep -Eiq 'eperm|permission|lock'; then
      printf 'inventory_remediation=Set PI_CODING_AGENT_DIR to a writable Pi agent directory and authenticate this provider there.\n'
    fi
  fi
  [[ $AUTH_CONFIGURED -eq 1 ]] || exit 2
  [[ -n "$MODEL" ]] || exit 3
  exit 0
fi

[[ -n "$MODEL" ]] || fail "no model selected; run 'pi --list-models $PROVIDER' or pass --model PROVIDER_MODEL"
[[ $AUTH_CONFIGURED -eq 1 ]] || fail "authentication not detected for provider '$PROVIDER'; set its API key or authenticate through Pi"

if [[ $PROBE_ONLY -eq 1 ]]; then
  [[ "${CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK:-0}" == "1" ]] || fail "external-provider acknowledgement missing; set CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1 after user consent"
  TASK="Say exactly: DEEPSEEK_PI_PROBE_OK"
  MODE="analysis"
  TOOLS="read,ls"
fi

if [[ $PROBE_ONLY -eq 0 ]]; then
  [[ "${CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK:-0}" == "1" ]] || fail "external-provider acknowledgement missing; set CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1 after user consent"
fi

if [[ "$MODE" == "implementation" && "${CODEX_DEEPSEEK_WRITE_DELEGATION:-0}" != "1" ]]; then
  fail "implementation mode requires CODEX_DEEPSEEK_WRITE_DELEGATION=1"
fi

if [[ -n "$TASK_FILE" ]]; then
  [[ -f "$TASK_FILE" ]] || fail "task file does not exist: $TASK_FILE"
  [[ -z "$TASK" ]] || fail "use either --task or --task-file, not both"
  TASK="$(cat "$TASK_FILE")"
fi
[[ -n "${TASK//[[:space:]]/}" ]] || fail "a non-empty --task or --task-file is required"

is_sensitive_path() {
  local path="$1"
  local base
  base="$(basename "$path")"
  case "$base" in
    .env|.env.*|id_rsa|id_rsa.*|id_ed25519|id_ed25519.*|credentials.json|secrets.json|auth.json|*.pem|*.key|*.p12|*.pfx)
      return 0
      ;;
  esac
  return 1
}

PI_FILES=()
if ((${#CONTEXT_FILES[@]})); then
  for file in "${CONTEXT_FILES[@]}"; do
  [[ -f "$file" ]] || fail "context file does not exist: $file"
  if is_sensitive_path "$file"; then
    fail "refusing sensitive context file: $file"
  fi
  absolute_file="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
    PI_FILES+=("@$absolute_file")
  done
fi

case "$MODE" in
  analysis|review)
    TOOLS="read,grep,find,ls"
    MODE_RULES="Do not edit files or execute shell commands. Produce evidence-backed analysis only."
    ;;
  test)
    TOOLS="read,grep,find,ls,bash"
    MODE_RULES="Do not edit files. Run only narrow, non-destructive verification commands directly relevant to the task."
    ;;
  implementation)
    TOOLS="read,write,edit,grep,find,ls,bash"
    MODE_RULES="Modify only the explicitly scoped files. Do not commit, push, merge, deploy, alter credentials, or run destructive commands."
    ;;
esac

SYSTEM_PROMPT=$(cat <<PROMPT
You are a bounded DeepSeek engineering worker invoked by Codex through the Pi coding-agent harness (built-in deepseek provider).

Codex is the supervising agent. Complete only the assigned subtask. Do not broaden scope, conceal uncertainty, or claim success without direct evidence.

Mode: $MODE
Rules: $MODE_RULES

Never read or disclose credentials, tokens, private keys, .env files, personal data, or unrelated sensitive material. Never commit, push, merge, deploy, publish, rotate secrets, change permissions, or access production systems.

Return the final response with exactly these headings:
## Summary
## Evidence
## Findings or Changes
## Verification Performed
## Risks and Unknowns
## Files Touched

Use repository-relative file paths and symbol names. Include line references when practical. Distinguish observed facts from hypotheses. If blocked, explain the blocker instead of improvising.
PROMPT
)

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$CWD/.codex/delegations/deepseek"
fi
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_MODE="$(printf '%s' "$MODE" | tr -cd '[:alnum:]_-')"
RESULT_FILE="$OUTPUT_DIR/${STAMP}-${SAFE_MODE}.md"
META_FILE="$OUTPUT_DIR/${STAMP}-${SAFE_MODE}.meta"

if [[ $FALLBACK_ON_FAILURE -eq 0 && ${#FALLBACK_MODELS[@]} -gt 0 ]]; then
  fail "--fallback-model requires --fallback-on-failure"
fi
MODELS_TO_TRY=("$MODEL")
if [[ $FALLBACK_ON_FAILURE -eq 1 ]]; then MODELS_TO_TRY+=("${FALLBACK_MODELS[@]}"); fi
for candidate in "${MODELS_TO_TRY[@]}"; do
  [[ "$candidate" =~ ^[A-Za-z0-9._:/*-]+$ ]] || fail "invalid model identifier: $candidate"
done

run_model() {
  local run_model="$1"
  MODEL="$run_model"
  RESULT_FILE="$OUTPUT_DIR/${STAMP}-${SAFE_MODE}-${run_model//[^A-Za-z0-9._-]/_}.md"
  META_FILE="$RESULT_FILE.meta"
  CMD=(pi --provider "$PROVIDER" --model "$MODEL" --thinking "$THINKING" --tools "$TOOLS" --no-session -p --append-system-prompt "$SYSTEM_PROMPT")
if ((${#PI_FILES[@]})); then
  CMD+=("${PI_FILES[@]}")
fi
CMD+=("$TASK")

{
  printf 'timestamp_utc=%s\n' "$STAMP"
  printf 'mode=%s\n' "$MODE"
  printf 'provider=%s\n' "$PROVIDER"
  printf 'model=%s\n' "$MODEL"
  printf 'thinking=%s\n' "$THINKING"
  printf 'cwd=%s\n' "$CWD"
  printf 'tools=%s\n' "$TOOLS"
  printf 'result_file=%s\n' "$RESULT_FILE"
} > "$META_FILE"

if [[ $DRY_RUN -eq 1 ]]; then
  printf 'cwd=%q ' "$CWD"
  printf '%q ' "${CMD[@]}"
  printf '\n'
  printf 'result_file=%s\n' "$RESULT_FILE"
  exit 0
fi

set +e
(
  cd "$CWD"
  if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT_SECONDS" "${CMD[@]}"
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS: use perl to implement timeout
    perl -e '
      use strict;
      my $timeout = shift @ARGV;
      my $pid = fork();
      die "fork failed: $!" unless defined $pid;
      if ($pid == 0) {
        exec @ARGV;
        exit 1;
      }
      eval {
        local $SIG{ALRM} = sub { kill "TERM", $pid; die "timeout\n" };
        alarm $timeout;
        waitpid $pid, 0;
        alarm 0;
      };
      my $exit = $?;
      if ($@) {
        print STDERR "timeout: delegation exceeded ${timeout}s\n";
        exit 124;
      }
      exit ($exit >> 8);
    ' -- "$TIMEOUT_SECONDS" "${CMD[@]}"
  else
    "${CMD[@]}"
  fi
) > "$RESULT_FILE" 2> "${RESULT_FILE}.stderr"
STATUS=$?
set -e

printf 'exit_code=%s\n' "$STATUS" >> "$META_FILE"

if [[ $STATUS -eq 124 ]]; then
  printf 'status=timeout\n' >> "$META_FILE"
  printf 'Pi delegation timed out after %s seconds.\n' "$TIMEOUT_SECONDS" >&2
  printf 'stderr_file=%s\n' "${RESULT_FILE}.stderr" >&2
  return 124
fi

if [[ $STATUS -ne 0 ]]; then
  printf 'status=worker_failed\n' >> "$META_FILE"
  printf 'Pi delegation failed with exit code %s.\n' "$STATUS" >&2
  printf 'stderr_file=%s\n' "${RESULT_FILE}.stderr" >&2
  return "$STATUS"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  printf 'status=empty_result\n' >> "$META_FILE"
  printf 'Pi returned an empty result for model %s: %s\n' "$MODEL" "$RESULT_FILE" >&2
  return 1
fi

printf 'status=success\n' >> "$META_FILE"
printf 'delegation_result=%s\n' "$RESULT_FILE"
printf 'delegation_metadata=%s\n' "$META_FILE"
if [[ -s "${RESULT_FILE}.stderr" ]]; then
  printf 'delegation_stderr=%s\n' "${RESULT_FILE}.stderr"
fi
return 0
}

for index in "${!MODELS_TO_TRY[@]}"; do
  candidate="${MODELS_TO_TRY[$index]}"
  if run_model "$candidate"; then
    exit 0
  else
    status=$?
  fi
  printf 'model_attempt_failed=%s exit_code=%s\n' "$candidate" "$status" >&2
  if [[ $FALLBACK_ON_FAILURE -eq 0 || $index -eq $((${#MODELS_TO_TRY[@]} - 1)) ]]; then
    exit "$status"
  fi
  printf 'model_fallback_next=%s\n' "${MODELS_TO_TRY[$((index + 1))]}" >&2
done
