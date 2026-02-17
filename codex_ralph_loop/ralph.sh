#!/bin/bash
# Ralph Audit Loop (OpenAI Codex) - Long-running autonomous *read-only* audit loop.
# Usage: ./ralph.sh [max_iterations] [--skip-security-check] [--no-search]
#
# Writes all artifacts under `.codex/ralph-audit/` (PRD state, logs, and audit reports).

set -euo pipefail

export CODEX_INTERNAL_ORIGINATOR_OVERRIDE="Codex Desktop"

MAX_ITERATIONS=20
MAX_ATTEMPTS_PER_STORY="${MAX_ATTEMPTS_PER_STORY:-5}"
SKIP_SECURITY="${SKIP_SECURITY_CHECK:-false}"
ENABLE_SEARCH="true"
TAIL_N="${TAIL_N:-200}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-security-check)
      SKIP_SECURITY="true"
      shift
      ;;
    --search)
      ENABLE_SEARCH="true"
      shift
      ;;
    --no-search)
      ENABLE_SEARCH="false"
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

if [[ "$SKIP_SECURITY" != "true" ]]; then
  echo ""
  echo "==============================================================="
  echo "  Security Pre-Flight Check"
  echo "==============================================================="
  echo ""

  SECURITY_WARNINGS=()

  if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
    SECURITY_WARNINGS+=("AWS_ACCESS_KEY_ID is set - production credentials may be exposed")
  fi

  if [[ -n "${DATABASE_URL:-}" ]]; then
    SECURITY_WARNINGS+=("DATABASE_URL is set - database credentials may be exposed")
  fi

  if [[ ${#SECURITY_WARNINGS[@]} -gt 0 ]]; then
    echo "WARNING: Potential credential exposure detected:"
    echo ""
    for warning in "${SECURITY_WARNINGS[@]}"; do
      echo "  - $warning"
    done
    echo ""
    echo "Running an autonomous agent with these credentials set could expose"
    echo "them in logs, commit messages, or API calls."
    echo ""
    echo "See your repo's security docs for sandboxing guidance."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Aborted. Unset credentials or use --skip-security-check to bypass."
      exit 1
    fi
  else
    echo "No credential exposure risks detected."
  fi
  echo ""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PRD_FILE="$SCRIPT_DIR/prd.json"
RUN_LOG="$SCRIPT_DIR/run.log"
EVENT_LOG="$SCRIPT_DIR/events.log"
MODEL_CHECK_LOG="$SCRIPT_DIR/.model-check.log"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"

mkdir -p "$SCRIPT_DIR/audit"

ATTEMPTS_FILE="$SCRIPT_DIR/.story-attempts"
LAST_STORY_FILE="$SCRIPT_DIR/.last-story"

if [ ! -f "$ATTEMPTS_FILE" ]; then
  echo "{}" > "$ATTEMPTS_FILE"
fi

get_current_story() {
  if [ -f "$PRD_FILE" ]; then
    jq -r '.userStories[] | select(.passes == false) | .id' "$PRD_FILE" 2>/dev/null | head -1
  fi
}

get_story_attempts() {
  local story_id="$1"
  jq -r --arg id "$story_id" '.[$id] // 0' "$ATTEMPTS_FILE" 2>/dev/null || echo "0"
}

increment_story_attempts() {
  local story_id="$1"
  local current
  current=$(get_story_attempts "$story_id")
  local new_count=$((current + 1))
  jq --arg id "$story_id" --argjson count "$new_count" '.[$id] = $count' "$ATTEMPTS_FILE" > "$ATTEMPTS_FILE.tmp" \
    && mv "$ATTEMPTS_FILE.tmp" "$ATTEMPTS_FILE"
  echo "$new_count"
}

mark_story_skipped() {
  local story_id="$1"
  local max_attempts="$2"
  local note="Skipped: exceeded $max_attempts attempts without passing"
  jq --arg id "$story_id" --arg note "$note" '
    .userStories = [
      .userStories[]
      | if .id == $id then
          (.notes = $note) | (.passes = true) | (.skipped = true)
        else
          .
        end
    ]
  ' "$PRD_FILE" > "$PRD_FILE.tmp" && mv "$PRD_FILE.tmp" "$PRD_FILE"
  echo "Circuit breaker: Marked story $story_id as skipped after $max_attempts attempts"
}

check_circuit_breaker() {
  local story_id="$1"
  local attempts
  attempts=$(get_story_attempts "$story_id")

  if [ "$attempts" -ge "$MAX_ATTEMPTS_PER_STORY" ]; then
    echo "Circuit breaker: Story $story_id has reached max attempts ($attempts/$MAX_ATTEMPTS_PER_STORY)"
    mark_story_skipped "$story_id" "$MAX_ATTEMPTS_PER_STORY"
    return 0
  fi
  return 1
}

ts() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

log_event() {
  echo "[$(ts)] $*" >> "$EVENT_LOG"
}

get_story_title() {
  local story_id="$1"
  jq -r --arg id "$story_id" '.userStories[] | select(.id == $id) | .title' "$PRD_FILE" 2>/dev/null || true
}

get_story_description() {
  local story_id="$1"
  jq -r --arg id "$story_id" '.userStories[] | select(.id == $id) | .description' "$PRD_FILE" 2>/dev/null || true
}

get_story_notes() {
  local story_id="$1"
  jq -r --arg id "$story_id" '.userStories[] | select(.id == $id) | (.notes // "")' "$PRD_FILE" 2>/dev/null || true
}

get_story_output_relpath() {
  local story_id="$1"
  # Extract the target output file from acceptance criteria, e.g.:
  # "Created .codex/ralph-audit/audit/01-api-routes.md with ALL findings"
  jq -r --arg id "$story_id" '
    .userStories[]
    | select(.id == $id)
    | .acceptanceCriteria[]
    | select(test("^Created "))
    | split(" ")[1]
  ' "$PRD_FILE" 2>/dev/null | head -n 1
}

mark_story_passed() {
  local story_id="$1"
  jq --arg id "$story_id" '
    .userStories = [
      .userStories[]
      | if .id == $id then
          (.passes = true)
        else
          .
        end
    ]
  ' "$PRD_FILE" > "$PRD_FILE.tmp" && mv "$PRD_FILE.tmp" "$PRD_FILE"
}

mark_progress_checked() {
  local story_id="$1"
  if [ ! -f "$PROGRESS_FILE" ]; then
    return 0
  fi

  # Replace: - [ ] AUDIT-001: ...  ->  - [x] AUDIT-001: ...
  sed -i '' "s|^- \\[ \\] ${story_id}:|- [x] ${story_id}:|g" "$PROGRESS_FILE" || true
}

# Pinned by default. Adjust as needed for your Codex access and preference.
REQUESTED_MODEL="gpt-5.2"
REASONING_EFFORT="high"

if [[ -n "${CODEX_MODEL:-}" && "${CODEX_MODEL}" != "$REQUESTED_MODEL" ]]; then
  echo "ERROR: This loop is pinned to CODEX_MODEL=$REQUESTED_MODEL. Unset CODEX_MODEL to continue."
  exit 1
fi

if [[ -n "${CODEX_REASONING_EFFORT:-}" && "${CODEX_REASONING_EFFORT}" != "$REASONING_EFFORT" ]]; then
  echo "ERROR: This loop is pinned to CODEX_REASONING_EFFORT=$REASONING_EFFORT. Unset CODEX_REASONING_EFFORT to continue."
  exit 1
fi

touch "$RUN_LOG" "$EVENT_LOG"

echo "Starting Ralph Audit (OpenAI Codex)"
echo "  Max iterations: $MAX_ITERATIONS"
echo "  Max attempts per story: $MAX_ATTEMPTS_PER_STORY"
echo "  Model: $REQUESTED_MODEL (reasoning_effort=$REASONING_EFFORT)"
echo "  Logs:"
echo "    - events: $EVENT_LOG"
echo "    - full:   $RUN_LOG"
echo "  Tail:"
echo "    tail -n $TAIL_N -f $EVENT_LOG"
echo "    tail -n $TAIL_N -f $RUN_LOG"

log_event "RUN START max_iterations=$MAX_ITERATIONS max_attempts_per_story=$MAX_ATTEMPTS_PER_STORY search=$ENABLE_SEARCH model=$REQUESTED_MODEL reasoning_effort=$REASONING_EFFORT"

# Preflight: verify the requested model works for current Codex auth.
MODEL_CHECK_CMD=(
  codex
  -a never
  exec
  -C "$REPO_ROOT"
  -m "$REQUESTED_MODEL"
  -c "model_reasoning_effort=\"$REASONING_EFFORT\""
  -s read-only
  "Respond with exactly: OK"
)

if ! "${MODEL_CHECK_CMD[@]}" > "$MODEL_CHECK_LOG" 2>&1; then
  echo "ERROR: Model preflight failed for '$REQUESTED_MODEL'. See: $MODEL_CHECK_LOG"
  echo "Fix options:"
  echo "  1) Re-auth with an API key that has access:"
  echo "     printenv OPENAI_API_KEY | codex login --with-api-key"
  exit 1
fi

CODEX_ARGS=(
  -a never
)

if [[ "$ENABLE_SEARCH" == "true" ]]; then
  CODEX_ARGS+=(--search)
fi

CODEX_ARGS+=(
  exec
  -C "$REPO_ROOT"
  -m "$REQUESTED_MODEL"
  -c "model_reasoning_effort=\"$REASONING_EFFORT\""
  -s read-only
)

for i in $(seq 1 "$MAX_ITERATIONS"); do
  echo ""
  echo "==============================================================="
  echo "  Ralph Audit Iteration $i of $MAX_ITERATIONS"
  echo "==============================================================="

  echo "" >> "$RUN_LOG"
  echo "===============================================================" >> "$RUN_LOG"
  echo "Ralph Audit Iteration $i of $MAX_ITERATIONS - $(date)" >> "$RUN_LOG"
  echo "===============================================================" >> "$RUN_LOG"

  log_event "ITERATION START $i/$MAX_ITERATIONS"

  CURRENT_STORY=$(get_current_story)

  if [ -z "$CURRENT_STORY" ]; then
    log_event "RUN COMPLETE (no incomplete stories)"
    echo "No incomplete stories found."
    echo ""
    echo "Ralph audit completed all tasks!"
    echo "<promise>COMPLETE</promise>"
    exit 0
  fi

  LAST_STORY=""
  if [ -f "$LAST_STORY_FILE" ]; then
    LAST_STORY=$(cat "$LAST_STORY_FILE" 2>/dev/null || echo "")
  fi

  if [ "$CURRENT_STORY" == "$LAST_STORY" ]; then
    echo "Consecutive attempt on story: $CURRENT_STORY"
    ATTEMPTS=$(increment_story_attempts "$CURRENT_STORY")
    echo "Attempts on $CURRENT_STORY: $ATTEMPTS/$MAX_ATTEMPTS_PER_STORY"

    if check_circuit_breaker "$CURRENT_STORY"; then
      echo "Skipping to next story..."
      echo "$CURRENT_STORY" > "$LAST_STORY_FILE"
      sleep 1
      continue
    fi
  else
    ATTEMPTS=$(increment_story_attempts "$CURRENT_STORY")
    echo "Starting story: $CURRENT_STORY (attempt $ATTEMPTS/$MAX_ATTEMPTS_PER_STORY)"
  fi

  echo "$CURRENT_STORY" > "$LAST_STORY_FILE"

  STORY_TITLE="$(get_story_title "$CURRENT_STORY")"
  STORY_DESC="$(get_story_description "$CURRENT_STORY")"
  STORY_NOTES="$(get_story_notes "$CURRENT_STORY")"
  OUT_REL="$(get_story_output_relpath "$CURRENT_STORY")"

  if [ -z "$OUT_REL" ] || [ "$OUT_REL" == "null" ]; then
    log_event "ERROR story=$CURRENT_STORY could-not-determine-output-path"
    echo "ERROR: Could not determine output path for story $CURRENT_STORY from prd.json acceptanceCriteria."
    exit 1
  fi

  OUT_FILE="$REPO_ROOT/$OUT_REL"
  mkdir -p "$(dirname "$OUT_FILE")"

  log_event "STORY START id=$CURRENT_STORY attempt=$ATTEMPTS out=$OUT_REL title=$(printf '%s' "$STORY_TITLE" | tr '\n' ' ')"

  PROMPT_FILE="$SCRIPT_DIR/.prompt.md"
  LAST_MESSAGE_FILE="$SCRIPT_DIR/.last-message.md"

  {
    # NOTE: bash printf treats leading '-' as an option unless you pass `--`.
    printf -- "# Ralph Audit (OpenAI Codex)\n\n"
    printf -- "Today's date: %s\n\n" "$(date +%Y-%m-%d)"
    printf -- "Current story: %s — %s\n" "$CURRENT_STORY" "$STORY_TITLE"
    printf -- "Target output file (relative to repo root): %s\n\n" "$OUT_REL"
    printf -- "Hard requirements:\n"
    printf -- "- Do NOT modify any files in the repo.\n"
    printf -- "- Your final response MUST be ONLY the markdown report contents for %s.\n" "$OUT_REL"
    printf -- "  Do not include any extra commentary.\n\n"
    printf -- "Story description:\n%s\n\n" "$STORY_DESC"
    printf -- "Story notes:\n%s\n\n" "$STORY_NOTES"
    printf -- "---\n\n"
    cat "$SCRIPT_DIR/CODEX.md"
  } > "$PROMPT_FILE"

  # Run Codex read-only; persist the model's last message to a file we control.
  codex "${CODEX_ARGS[@]}" --output-last-message "$LAST_MESSAGE_FILE" < "$PROMPT_FILE" 2>&1 | tee -a "$RUN_LOG" || true

  if [ ! -s "$LAST_MESSAGE_FILE" ]; then
    log_event "ERROR story=$CURRENT_STORY codex-empty-last-message"
    echo "ERROR: Codex did not produce a last message file (or it was empty). See: $RUN_LOG"
    echo "Iteration $i complete (failed). Continuing..."
    sleep 2
    continue
  fi

  # Persist the audit report and mark story passed in PRD state.
  cat "$LAST_MESSAGE_FILE" > "$OUT_FILE"
  mark_story_passed "$CURRENT_STORY"
  mark_progress_checked "$CURRENT_STORY"

  log_event "STORY COMPLETE id=$CURRENT_STORY wrote=$OUT_REL bytes=$(wc -c < \"$OUT_FILE\" | tr -d ' ')"

  REMAINING=$(jq -r '.userStories[] | select(.passes == false) | .id' "$PRD_FILE" 2>/dev/null | head -n 1 || true)
  if [ -z "$REMAINING" ]; then
    log_event "RUN COMPLETE (all stories passed)"
    echo ""
    echo "All audit tasks are marked passes:true."
    echo "Ralph audit completed all tasks!"
    echo "<promise>COMPLETE</promise>"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Tail log: tail -f $RUN_LOG"
log_event "RUN STOPPED (reached max iterations without completing all tasks)"
exit 1
