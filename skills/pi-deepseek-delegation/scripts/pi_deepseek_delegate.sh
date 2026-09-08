#!/usr/bin/env bash
set -euo pipefail

# The filename and directory retain their pi_deepseek_delegation compatibility
# names. Selection itself is provider-neutral and is always explicit.

MODE="analysis"
TASK=""
TASK_FILE=""
CWD="$PWD"
OUTPUT_DIR=""
SELECTION_RATIONALE=""

TASK_PROVIDER=""
TASK_MODEL=""
TASK_THINKING=""
TASK_TIMEOUT=""
PROVIDER_ARG_SET=0
MODEL_ARG_SET=0
THINKING_ARG_SET=0
TIMEOUT_ARG_SET=0

PROVIDER=""
MODEL=""
THINKING=""
TIMEOUT_SECONDS=""
SELECTION_SOURCE=""

CHECK_ONLY=0
CATALOG_ONLY=0
PROBE_ONLY=0
DRY_RUN=0
JSON_OUTPUT=0
CONTEXT_FILES=()

MODEL_LIST=""
PI_PATH=""
CATALOG_TABLE=""
CATALOG_COUNT=0

usage() {
  cat <<'USAGE'
Usage:
  pi_deepseek_delegate.sh --catalog
  pi_deepseek_delegate.sh --check --provider PROVIDER --model MODEL
  pi_deepseek_delegate.sh --task "..." --provider PROVIDER --model MODEL [options]
  pi_deepseek_delegate.sh --probe --provider PROVIDER --model MODEL [options]

Options:
  --mode analysis|review|test|implementation
  --task TEXT
  --task-file PATH
  --context-file PATH       Repeatable. Passed to Pi as an @file argument.
  --cwd DIR                 Delegated working directory. Default: current directory.
  --provider PROVIDER       Exact Pi provider ID. Must be paired with --model.
  --model MODEL             Exact Pi model ID. Must be paired with --provider.
  --thinking LEVEL          off|minimal|low|medium|high|xhigh|max. Default: high.
  --timeout-seconds N       Timeout for the delegation. Default: 180.
  --selection-rationale TEXT
                            Short supervising-agent rationale recorded in metadata.
  --output-dir DIR          Default: <cwd>/.codex/delegations/pi
  --catalog                 Print Pi's current available provider/model table.
  --check                   Validate the exact selection against Pi's catalog only.
  --probe                   Minimal live inference with a synthetic prompt.
  --dry-run                 Print the planned command without invoking Pi.
  --json                    Output machine-readable JSON where supported.
  -h, --help

Generic operator defaults:
  PI_DELEGATION_PROVIDER and PI_DELEGATION_MODEL must both be configured.
  PI_DELEGATION_THINKING and PI_DELEGATION_TIMEOUT are optional.

Real inference requires:
  CODEX_PI_DELEGATION_ACK=1

Implementation mode additionally requires:
  CODEX_PI_WRITE_DELEGATION=1

Legacy compatibility:
  PI_DEEPSEEK_PROVIDER, PI_DEEPSEEK_MODEL, PI_DEEPSEEK_THINKING,
  PI_DEEPSEEK_TIMEOUT, CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK, and
  CODEX_DEEPSEEK_WRITE_DELEGATION are honored only for a DeepSeek selection.
  They never authorize or select another provider.
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
      TASK_PROVIDER="$2"
      PROVIDER_ARG_SET=1
      shift 2
      ;;
    --model)
      [[ $# -ge 2 ]] || fail "--model requires a value"
      TASK_MODEL="$2"
      MODEL_ARG_SET=1
      shift 2
      ;;
    --thinking)
      [[ $# -ge 2 ]] || fail "--thinking requires a value"
      TASK_THINKING="$2"
      THINKING_ARG_SET=1
      shift 2
      ;;
    --timeout-seconds)
      [[ $# -ge 2 ]] || fail "--timeout-seconds requires a value"
      TASK_TIMEOUT="$2"
      TIMEOUT_ARG_SET=1
      shift 2
      ;;
    --selection-rationale)
      [[ $# -ge 2 ]] || fail "--selection-rationale requires a value"
      SELECTION_RATIONALE="$2"
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || fail "--output-dir requires a value"
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --catalog)
      CATALOG_ONLY=1
      shift
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

if [[ $CATALOG_ONLY -eq 1 ]]; then
  [[ $CHECK_ONLY -eq 0 ]] || fail "--catalog cannot be combined with --check"
  [[ $PROBE_ONLY -eq 0 ]] || fail "--catalog cannot be combined with --probe"
  [[ $DRY_RUN -eq 0 ]] || fail "--catalog cannot be combined with --dry-run"
  [[ -z "$TASK" && -z "$TASK_FILE" ]] || fail "--catalog does not accept a task"
fi

if [[ $CHECK_ONLY -eq 1 && $PROBE_ONLY -eq 1 ]]; then
  fail "--check cannot be combined with --probe"
fi

if [[ $CHECK_ONLY -eq 1 && $DRY_RUN -eq 1 ]]; then
  fail "--check cannot be combined with --dry-run"
fi

if [[ $PROBE_ONLY -eq 1 ]]; then
  MODE="analysis"
  TASK="Say exactly: PI_DELEGATION_PROBE_OK"
  TASK_FILE=""
fi

case "$MODE" in
  analysis|review|test|implementation) ;;
  *) fail "unsupported mode: $MODE" ;;
esac

resolve_selection() {
  local generic_provider="${PI_DELEGATION_PROVIDER:-}"
  local generic_model="${PI_DELEGATION_MODEL:-}"
  local legacy_provider="${PI_DEEPSEEK_PROVIDER:-}"
  local legacy_model="${PI_DEEPSEEK_MODEL:-}"

  if [[ $PROVIDER_ARG_SET -ne $MODEL_ARG_SET ]]; then
    fail "explicit selection requires both --provider and --model"
  fi

  if [[ $PROVIDER_ARG_SET -eq 1 ]]; then
    [[ -n "$TASK_PROVIDER" && -n "$TASK_MODEL" ]] || fail "--provider and --model must both be non-empty"
    PROVIDER="$TASK_PROVIDER"
    MODEL="$TASK_MODEL"
    SELECTION_SOURCE="explicit-task"
    return
  fi

  if [[ -n "$generic_provider" || -n "$generic_model" ]]; then
    [[ -n "$generic_provider" && -n "$generic_model" ]] || fail "PI_DELEGATION_PROVIDER and PI_DELEGATION_MODEL must be configured together"
    PROVIDER="$generic_provider"
    MODEL="$generic_model"
    SELECTION_SOURCE="generic-environment"
    return
  fi

  if [[ -n "$legacy_provider" || -n "$legacy_model" ]]; then
    if [[ -n "$legacy_provider" && "$legacy_provider" != "deepseek" ]]; then
      fail "PI_DEEPSEEK_PROVIDER only supports the legacy deepseek provider; use generic provider/model settings for another provider"
    fi
    [[ -n "$legacy_model" ]] || fail "legacy DeepSeek selection is missing PI_DEEPSEEK_MODEL; inspect --catalog and choose an exact pair"
    # PI_DEEPSEEK_MODEL is an explicit legacy selection whose namespace binds
    # the provider to deepseek. There is still no model fallback or ranking.
    PROVIDER="deepseek"
    MODEL="$legacy_model"
    SELECTION_SOURCE="legacy-deepseek"
    return
  fi

  fail "no provider/model selected; pass --provider and --model or configure PI_DELEGATION_PROVIDER and PI_DELEGATION_MODEL; inspect --catalog"
}

resolve_thinking_and_timeout() {
  if [[ $THINKING_ARG_SET -eq 1 ]]; then
    THINKING="$TASK_THINKING"
  elif [[ -n "${PI_DELEGATION_THINKING:-}" ]]; then
    THINKING="$PI_DELEGATION_THINKING"
  elif [[ "$PROVIDER" == "deepseek" && -n "${PI_DEEPSEEK_THINKING:-}" ]]; then
    THINKING="$PI_DEEPSEEK_THINKING"
  else
    THINKING="high"
  fi

  case "$THINKING" in
    off|minimal|low|medium|high|xhigh|max) ;;
    *) fail "unsupported thinking level: $THINKING" ;;
  esac

  if [[ $TIMEOUT_ARG_SET -eq 1 ]]; then
    TIMEOUT_SECONDS="$TASK_TIMEOUT"
  elif [[ -n "${PI_DELEGATION_TIMEOUT:-}" ]]; then
    TIMEOUT_SECONDS="$PI_DELEGATION_TIMEOUT"
  elif [[ "$PROVIDER" == "deepseek" && -n "${PI_DEEPSEEK_TIMEOUT:-}" ]]; then
    TIMEOUT_SECONDS="$PI_DEEPSEEK_TIMEOUT"
  else
    TIMEOUT_SECONDS="180"
  fi

  [[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "timeout must be a positive integer number of seconds: $TIMEOUT_SECONDS"
}

read_model_catalog() {
  local catalog_status
  set +e
  MODEL_LIST="$(pi --list-models 2>/dev/null)"
  catalog_status=$?
  set -e
  [[ $catalog_status -eq 0 ]] || fail "unable to read Pi model catalog; pi --list-models exited with $catalog_status"
}

catalog_table() {
  printf '%s\n' "$MODEL_LIST" | awk '
    function safe_token(value) {
      return value ~ /^[[:alnum:]_.:@+\/-]+$/
    }
    tolower($1) == "provider" && tolower($2) == "model" {
      print $0
      header_seen = 1
      next
    }
    header_seen && NF >= 2 && safe_token($1) && safe_token($2) {
      print $0
    }
  '
}

catalog_count() {
  printf '%s\n' "$MODEL_LIST" | awk '
    function safe_token(value) {
      return value ~ /^[[:alnum:]_.:@+\/-]+$/
    }
    tolower($1) == "provider" && tolower($2) == "model" {
      header_seen = 1
      next
    }
    header_seen && NF >= 2 && safe_token($1) && safe_token($2) {
      count++
    }
    END { print count + 0 }
  '
}

validate_model_pair() {
  if ! printf '%s\n' "$MODEL_LIST" | awk -v expected_provider="$PROVIDER" -v expected_model="$MODEL" '
    BEGIN { found = 0 }
    tolower($1) == "provider" && tolower($2) == "model" {
      header_seen = 1
      next
    }
    header_seen && $1 == expected_provider && $2 == expected_model {
      found = 1
    }
    END { exit(found ? 0 : 1) }
  '; then
    fail "selected provider/model is not available in Pi's current catalog: $PROVIDER/$MODEL; run the wrapper with --catalog and choose an exact registered pair"
  fi
}

json_quote() {
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"
}

emit_catalog() {
  CATALOG_TABLE="$(catalog_table)"
  CATALOG_COUNT="$(catalog_count)"

  if [[ $JSON_OUTPUT -eq 1 ]]; then
    printf '{"pi":%s,"catalog_command":"pi --list-models","available_model_entries":%s,"listing":%s}\n' \
      "$(json_quote "$PI_PATH")" \
      "$CATALOG_COUNT" \
      "$(json_quote "$CATALOG_TABLE")"
    return
  fi

  printf 'pi=%s\n' "$PI_PATH"
  printf 'catalog_command=pi --list-models\n'
  printf 'available_model_entries=%s\n' "$CATALOG_COUNT"
  printf '%s\n' 'available_models_begin'
  if [[ -n "$CATALOG_TABLE" ]]; then
    printf '%s\n' "$CATALOG_TABLE"
  else
    printf '%s\n' 'catalog_status=no_available_model_rows'
  fi
  printf '%s\n' 'available_models_end'
}

emit_check() {
  CATALOG_TABLE="$(catalog_table)"
  CATALOG_COUNT="$(catalog_count)"

  if [[ $JSON_OUTPUT -eq 1 ]]; then
    printf '{"pi":%s,"provider":%s,"model":%s,"thinking":%s,"timeout_seconds":%s,"selection_source":%s,"available_model_entries":%s}\n' \
      "$(json_quote "$PI_PATH")" \
      "$(json_quote "$PROVIDER")" \
      "$(json_quote "$MODEL")" \
      "$(json_quote "$THINKING")" \
      "$TIMEOUT_SECONDS" \
      "$(json_quote "$SELECTION_SOURCE")" \
      "$CATALOG_COUNT"
    return
  fi

  printf 'pi=%s\n' "$PI_PATH"
  printf 'provider=%s\n' "$PROVIDER"
  printf 'model=%s\n' "$MODEL"
  printf 'thinking=%s\n' "$THINKING"
  printf 'timeout_seconds=%s\n' "$TIMEOUT_SECONDS"
  printf 'selection_source=%s\n' "$SELECTION_SOURCE"
  printf 'available_model_entries=%s\n' "$CATALOG_COUNT"
  printf '%s\n' 'available_models_begin'
  if [[ -n "$CATALOG_TABLE" ]]; then
    printf '%s\n' "$CATALOG_TABLE"
  else
    printf '%s\n' 'catalog_status=no_available_model_rows'
  fi
  printf '%s\n' 'available_models_end'
}

PI_PATH="$(command -v pi 2>/dev/null || true)"
[[ -n "$PI_PATH" ]] || fail "pi is not installed or not on PATH"

if [[ $CATALOG_ONLY -eq 1 ]]; then
  read_model_catalog
  emit_catalog
  exit 0
fi

[[ -d "$CWD" ]] || fail "working directory does not exist: $CWD"
CWD="$(cd "$CWD" && pwd)"

resolve_selection
resolve_thinking_and_timeout
read_model_catalog
validate_model_pair

if [[ $CHECK_ONLY -eq 1 ]]; then
  emit_check
  exit 0
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

if [[ $DRY_RUN -eq 0 ]]; then
  if [[ "${CODEX_PI_DELEGATION_ACK:-0}" != "1" ]]; then
    if [[ "$PROVIDER" == "deepseek" && "${CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK:-0}" == "1" ]]; then
      :
    elif [[ "$PROVIDER" != "deepseek" && "${CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK:-0}" == "1" ]]; then
      fail "generic delegation acknowledgement missing; CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK only authorizes a DeepSeek selection; set CODEX_PI_DELEGATION_ACK=1 after user consent"
    else
      fail "delegation acknowledgement missing; set CODEX_PI_DELEGATION_ACK=1 after user consent"
    fi
  fi

  if [[ "$MODE" == "implementation" && "${CODEX_PI_WRITE_DELEGATION:-0}" != "1" ]]; then
    if [[ "$PROVIDER" == "deepseek" && "${CODEX_DEEPSEEK_WRITE_DELEGATION:-0}" == "1" ]]; then
      :
    elif [[ "$PROVIDER" != "deepseek" && "${CODEX_DEEPSEEK_WRITE_DELEGATION:-0}" == "1" ]]; then
      fail "generic write acknowledgement missing; CODEX_DEEPSEEK_WRITE_DELEGATION only authorizes a DeepSeek selection; set CODEX_PI_WRITE_DELEGATION=1"
    else
      fail "implementation mode requires CODEX_PI_WRITE_DELEGATION=1"
    fi
  fi
fi

SYSTEM_PROMPT=$(cat <<PROMPT
You are a bounded engineering worker invoked by the supervising agent through the Pi coding-agent harness.

The supervising agent selected provider: $PROVIDER
The supervising agent selected model: $MODEL
Selection rationale: ${SELECTION_RATIONALE:-not recorded}

Complete only the assigned subtask. Do not broaden scope, conceal uncertainty, or claim success without direct evidence.

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
  OUTPUT_DIR="$CWD/.codex/delegations/pi"
fi

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$OUTPUT_DIR"
  OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
elif [[ "$OUTPUT_DIR" != /* ]]; then
  OUTPUT_DIR="$CWD/$OUTPUT_DIR"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_MODE="$(printf '%s' "$MODE" | tr -cd '[:alnum:]_-')"
RESULT_FILE="$OUTPUT_DIR/${STAMP}-${SAFE_MODE}.md"
META_FILE="$OUTPUT_DIR/${STAMP}-${SAFE_MODE}.meta"

CMD=(pi --provider "$PROVIDER" --model "$MODEL" --thinking "$THINKING" --tools "$TOOLS" --no-session -p --append-system-prompt "$SYSTEM_PROMPT")
if ((${#PI_FILES[@]})); then
  CMD+=("${PI_FILES[@]}")
fi
CMD+=("$TASK")

if [[ $DRY_RUN -eq 1 ]]; then
  printf 'provider=%s\n' "$PROVIDER"
  printf 'model=%s\n' "$MODEL"
  printf 'thinking=%s\n' "$THINKING"
  printf 'selection_source=%s\n' "$SELECTION_SOURCE"
  printf 'cwd=%q ' "$CWD"
  printf '%q ' "${CMD[@]}"
  printf '\n'
  printf 'result_file=%s\n' "$RESULT_FILE"
  exit 0
fi

SAFE_RATIONALE="$(printf '%s' "$SELECTION_RATIONALE" | tr '\r\n' '  ')"
{
  printf 'timestamp_utc=%s\n' "$STAMP"
  printf 'mode=%s\n' "$MODE"
  printf 'provider=%s\n' "$PROVIDER"
  printf 'model=%s\n' "$MODEL"
  printf 'provider_model=%s/%s\n' "$PROVIDER" "$MODEL"
  printf 'thinking=%s\n' "$THINKING"
  printf 'timeout_seconds=%s\n' "$TIMEOUT_SECONDS"
  printf 'selection_source=%s\n' "$SELECTION_SOURCE"
  printf 'selection_rationale=%s\n' "$SAFE_RATIONALE"
  printf 'cwd=%s\n' "$CWD"
  printf 'tools=%s\n' "$TOOLS"
  printf 'artifact_dir=%s\n' "$OUTPUT_DIR"
  printf 'artifact_path=%s\n' "$RESULT_FILE"
  printf 'result_file=%s\n' "$RESULT_FILE"
} > "$META_FILE"

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
  printf 'Pi delegation for %s/%s timed out after %s seconds.\n' "$PROVIDER" "$MODEL" "$TIMEOUT_SECONDS" >&2
  printf 'stderr_file=%s\n' "${RESULT_FILE}.stderr" >&2
  exit 124
fi

if [[ $STATUS -ne 0 ]]; then
  printf 'status=worker_failed\n' >> "$META_FILE"
  printf 'Pi delegation for %s/%s failed with exit code %s.\n' "$PROVIDER" "$MODEL" "$STATUS" >&2
  printf 'stderr_file=%s\n' "${RESULT_FILE}.stderr" >&2
  exit "$STATUS"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  printf 'status=empty_result\n' >> "$META_FILE"
  fail "Pi returned an empty result for $PROVIDER/$MODEL: $RESULT_FILE"
fi

printf 'status=success\n' >> "$META_FILE"
printf 'selected_provider=%s\n' "$PROVIDER"
printf 'selected_model=%s\n' "$MODEL"
printf 'delegation_result=%s\n' "$RESULT_FILE"
printf 'delegation_metadata=%s\n' "$META_FILE"
if [[ -s "${RESULT_FILE}.stderr" ]]; then
  printf 'delegation_stderr=%s\n' "${RESULT_FILE}.stderr"
fi
