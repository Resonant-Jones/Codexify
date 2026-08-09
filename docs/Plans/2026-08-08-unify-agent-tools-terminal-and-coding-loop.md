# Unify Agent Tools, Terminal, and Coding Loop — Implementation Plan

> **Status:** Draft for review (2026-08-08). No code has been changed. Awaiting go-ahead before execution.
> **Companion doc:** `docs/research/codexify-vs-hermes-architecture-comparison-2026-08-08.md`
> **Source truth checked at:** commit `68f080029368395dd77a18df0ca724c24ea51a04` (branch `codex/reconcile-dlg-pao-history`).

**Goal:** Give the Codexify chat agent a real, safe tool surface — sandboxed terminal, file read/search, and (later) the existing coding loop — so the agent can act on its own repo and Codexify can improve Codexify.

**Architecture:** The command-bus manifest (`guardian/command_bus/manifest.py`) already produces `ToolSpec`s (`guardian/tools/derive.py`, `spec.py`) with risk/effect/approval metadata. The chat completion path (`guardian/core/chat_completion_service.py`) already has a dormant tool loop that calls `execute_invoke` in the `"tools"` lane. The missing pieces are: (1) attach a curated tool list to every completion call, (2) generalize the loop, (3) back `terminal:*` and file commands with the existing sandbox (`guardian/core/orchestrator/cli_sandbox.py` — whitelist + workspace-root containment + output caps + network gate), and (4) expose the coding work-order surface as tools.

**Tech stack:** Python, FastAPI, pydantic, Click/Typer, `subprocess`, pytest (repo `.venv`), the repo's existing `guardian/tests/` layout.

---

## Stage 0 — Baseline (prove where we stand)

### Task 0.1: Snapshot current truth and run the suite

**Objective:** Establish the pre-change baseline so every later claim is provable.

**Files:**
- Read: `docs/architecture/00-current-state.md`
- Read: `pytest.ini`, `conftest.py`

**Steps:**
1. Note `git status` / `git rev-parse HEAD` (dirty-worktree awareness per AGENTS.md).
2. Run the relevant core test subset:
   `cd /Volumes/Dev_SSD/Codexify-main && .venv/bin/pytest guardian/tests/core -q`
3. Record pass/fail counts in the plan's execution log.

**Verify:** Exit code 0 and a written baseline note. Do not proceed past a failing suite without flagging it.

### Task 0.2: Write the failing integration test that proves tools are absent

**Objective:** A red test that documents the current gap — the chat completion path attaches no tools to the LLM request.

**Files:**
- Create: `guardian/tests/core/test_chat_completion_tools_plumbing.py`

**Test sketch (red first):**
```python
# guardian/tests/core/test_chat_completion_tools_plumbing.py
"""Prove the chat completion path attaches curated tools to the model call."""
import pytest

from guardian.command_bus.manifest import build_manifest
from guardian.tools.allowlist import curated_tool_specs  # Stage 1 module (not yet present)


def test_manifest_produces_tools():
    """The command manifest must yield ToolSpecs (already true today)."""
    # build_manifest requires a FastAPI app; use the test app fixture from conftest.
    ...


@pytest.mark.xfail(reason="task.tools is never populated today (chat_completion_service.py:1272)")
def test_chat_completion_attaches_tools():
    """The completion task must carry the curated tool list for EVERY provider."""
    ...
```

**Verify:** Task 0.2's plumbing test FAILS for the expected reason (documented in the `xfail`), proving the gap.

---

## Stage 1 — Attach tools to the chat loop

### Task 1.1: Curated tool allowlist module

**Objective:** One explicit, configurable list of which command-bus commands become agent tools — no more all-or-nothing manifest.

**Files:**
- Create: `guardian/tools/allowlist.py`
- Modify: `guardian/tools/__init__.py` (export)

**Sketch:**
```python
# guardian/tools/allowlist.py
"""Curated mapping from command-bus command_ids to agent-visible tools.

Controlled by env vars (defaults safe for the local-first beta posture):
  CODEXIFY_AGENT_TOOL_GROUPS=memory,terminal,files,coding
"""
from guardian.tools.spec import ToolSpec

# group -> set of command_ids (or prefixes). Start read-only + memory:
DEFAULT_GROUPS = {
    "memory": {"memory:*"},          # existing memory tool surface
    "files": {"file:read", "file:search"},   # Stage 2
    "terminal": {"terminal:run"},    # Stage 2
    "coding": {"coding:*"},          # Stage 3
}

def enabled_groups() -> list[str]: ...

def curated_tool_specs(manifest_commands) -> list[ToolSpec]: ...
```

**Verify:** Unit test: given a manifest with a write command and a read command, the allowlist returns only the configured subset, and write commands carry `requires_confirmation=True`.

### Task 1.2: Populate `task.tools` for every provider

**Objective:** Remove the `provider == "deepseek"` gate so all providers receive the curated tool list.

**Files:**
- Modify: `guardian/core/chat_completion_service.py:1272` (the `tools=` conditional)
- Modify: wherever `ChatCompletionTask` is constructed in the chat path (likely `guardian/routes/chat.py` and `guardian/workers/chat_worker.py`) to set `task.tools` from `curated_tool_specs(...)`
- Modify: `guardian/core/ai_router.py` (`chat_with_ai`) — ensure `tools` is forwarded for all providers that support function calling; keep a per-provider capability flag

**Steps:**
1. Add `tools: list[dict] | None = None` default handling on `ChatCompletionTask` (already read via `getattr(task, "tools", None)`).
2. In the chat-route/worker task construction, call `curated_tool_specs(build_manifest(app))` once per request (cache by manifest hash) and set `task.tools` to `[t.to_openai_function_tool() for t in specs]`.
3. Change `chat_completion_service.py:1272` to pass `tools=task.tools` unconditionally (provider capability check moves into `chat_with_ai`, where non-function-calling providers can ignore it).
4. Un-xfail the Task 0.2 plumbing test; keep the deepseek tool-call normalization in `ai_router.py:44`.

**Verify:** `pytest guardian/tests/core/test_chat_completion_tools_plumbing.py -v` — the plumbing test now passes. Manual: one chat turn against a real provider returns tool schemas in the request (observable via existing request-correlation/trace fields).

### Task 1.3: Generalize the tool loop

**Objective:** The loop currently demands exactly one tool call (`chat_completion_service.py:5266`) and stops there. Support multiple tool calls per turn and a bounded turn budget.

**Files:**
- Modify: `guardian/core/chat_completion_service.py` (the `_execute_with_tool_turn` region, `:5085–5438`)
- Modify: `guardian/protocol_tokens.py` if new loop-stop reasons are needed (e.g. `TOOL_LOOP_MAX_TURNS`)

**Sketch:**
```python
TOOL_TURN_BUDGET = 5  # module constant; overridable via env CODEXIFY_TOOL_TURN_BUDGET

# loop shape:
for turn in range(TOOL_TURN_BUDGET):
    normalized = normalize_completion_output(attempt.output)
    if normalized.kind != "tool_decision":
        return plain_answer_result(...)
    results = [await execute_tool_call(tc) for tc in normalized.tool_calls]  # parallel-safe, ordered
    messages_for_llm.append(assistant_tool_calls_message(normalized.tool_calls))
    messages_for_llm.append(tool_results_message(results))
    attempt = await _execute_completion_attempt(...)
raise ToolLoopExecutionError("tool_turn_limit_reached", ...)
```

**Constraints (keep from today):** every turn still records `tool_turn_id` / `tool_turn_state` / `loop_stop_reason`; every tool result is capped; a `tool_call_count != 1` no longer errors for non-deepseek providers.

**Verify:** Unit tests with a fake provider that emits N tool calls then a plain answer — assert: N turns executed, results fed back in order, loop stops on plain answer, budget exceeded raises `ToolLoopExecutionError` with `TOOL_TURN_LIMIT_REACHED`.

### Task 1.4: Write-approval gate for tools

**Objective:** Writes stay gated. Default remains `allow_write_execution=False`; the allowlist can opt commands into confirmation-token approval (existing `guardian/tools/approval_tokens.py`).

**Files:**
- Modify: `guardian/core/chat_completion_service.py` (tool-turn execution path, `:5315–5322`)
- Modify: `guardian/tools/policy.py` (consume allowlist write flags)

**Verify:** Test: a `terminal:run` command with `effect=write` returns `status="blocked"` / `approval_required=true` and never executes the subprocess until a valid `ToolApproveRequest` clears it. Read-only commands execute without confirmation.

---

## Stage 2 — Sandboxed terminal + file tools

### Task 2.1: Extend the command catalog (read-only additions)

**Objective:** Grow `CommandCatalog.default()` (`guardian/core/orchestrator/cli_sandbox.py:111`) with the minimal read-only set the agent needs: `git log`, `git show`, plus a `read`/`search` file surface.

**Files:**
- Modify: `guardian/core/orchestrator/cli_sandbox.py` (`CommandCatalog.default()`)

**Additions:**
```python
"git_log":   CommandDefinition("git_log", "git", ("log", "--oneline", "-n", "{n}"),
                              allowed_params={"n"}, timeout_seconds=30, max_output_kb=512),
"git_show":  CommandDefinition("git_show", "git", ("show", "--stat", "{ref}"),
                              allowed_params={"ref"}, timeout_seconds=30, max_output_kb=1024),
```
File read/search are better served by dedicated Python tools (Task 2.3) than shell commands — keep the catalog for *executable* verbs only.

**Verify:** `pytest guardian/tests/core/orchestrator/test_cli_sandbox.py -v` (extend existing tests) — new commands resolve, reject unknown params, enforce path/root rules.

### Task 2.2: Register `terminal:*` ToolSpecs in the tools lane

**Objective:** The chat agent can invoke sandboxed commands through the existing `execute_invoke` lane.

**Files:**
- Modify: `guardian/command_bus/manifest.py` (append terminal command specs, mirroring `build_guardian_bridge_command_specs()`)
- Modify: `guardian/command_bus/invoke.py` or a new handler `guardian/tools/handlers/terminal_handler.py` — route `terminal:run` to `CommandExecutor.execute()`
- Modify: `guardian/tools/allowlist.py` — include `terminal` group

**Handler sketch:**
```python
# guardian/tools/handlers/terminal_handler.py
from guardian.core.orchestrator.cli_sandbox import CommandCatalog, CommandExecutor, WorkspaceRootManager

def handle_terminal_run(command_id: str, params: dict) -> dict:
    executor = CommandExecutor(WorkspaceRootManager(), CommandCatalog.default())
    proc = executor.execute(command_id, params, allow_network=False)
    return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
```

**ToolSpec registration:** `command_id="terminal:run"`, `method="POST"`, `effect="write"`, `risk="mutating"`, `requires_confirmation=True`, `input_schema` = `{command_id: string enum of catalog ids, params: object}`.

**Verify:** End-to-end test through `execute_invoke`: read-only command succeeds; unknown `command_id` → `KeyError` surfaced as `status="error"`; network-flagged command with `allow_network=False` → `PermissionError`; output over `max_output_kb` → `RuntimeError`.

### Task 2.3: File tools (read/search first, write gated)

**Objective:** `file:read` and `file:search` as ToolSpecs backed by `WorkspaceRootManager` containment; `file:write` gated by the Task 1.4 approval path.

**Files:**
- Create: `guardian/tools/handlers/file_handler.py`
- Modify: `guardian/command_bus/manifest.py`, `guardian/tools/allowlist.py`

**Sketch:**
```python
def handle_file_read(path: str) -> dict:
    resolved = WorkspaceRootManager().resolve_under_root(path)   # raises PermissionError outside root
    with open(resolved, "r", encoding="utf-8") as f:
        return {"content": f.read()[:MAX_READ_CHARS]}
```
`file:search` — ripgrep if available (`shutil.which("rg")`), else a bounded recursive scan, always rooted under the workspace. `file:write` — `effect="write"`, `requires_confirmation=True`, refuses `.env`/credentials paths and anything outside root.

**Verify:** Unit tests: read within root works; `../` escape raises; write without approval is blocked; `.env` write refused. Test under `guardian/tests/core/orchestrator/`.

### Task 2.4: Sandbox tool-surface test sweep

**Objective:** One consolidated test file proving the Stage 2 surface end-to-end (containment, params, caps, network, approval).

**Files:**
- Create: `guardian/tests/core/orchestrator/test_sandbox_tool_surface.py`

**Verify:** Full file green; run `pytest guardian/tests/core/orchestrator -q`.

---

## Stage 3 — Coding loop as tools (Codexify improves Codexify)

### Task 3.1: Work-order ToolSpecs

**Objective:** Expose the existing coding surface (`guardian/routes/coding_work_orders.py`, `guardian/agents/work_orders.py`) as `coding:*` commands in the tools lane.

**Files:**
- Modify: `guardian/command_bus/manifest.py` (append `coding:create_work_order`, `coding:run`, `coding:read_result` specs from the existing stores/contracts)
- Modify: `guardian/tools/allowlist.py` (`coding` group, default off until Stage 3 proof lands)

**Verify:** Specs appear in `/manifest`; `coding:create_work_order` writes a work order via `work_order_store`; `coding:read_result` returns the execution-ledger/test-result readback. Tests mirror existing `guardian/tests/agents/`.

### Task 3.2: Wire readback through the ledger + commit gate

**Objective:** The chat agent can observe outcomes, not just spawn work.

**Files:**
- Modify: handler for `coding:read_result` to return `execution_ledger_store` entries, `test_results`, and `commit_gate` state for the work order.

**Verify:** Test: run a work order against a scratch fixture worktree; assert ledger rows, test summary, and gate state come back as tool result.

### Task 3.3: End-to-end proof — the acceptance test

**Objective:** The literal "Codexify improves Codexify" proof: the chat agent fixes a small, seeded bug in a scratch worktree of this repo, runs the relevant tests through the sandbox, and reports a passing result.

**Steps:**
1. Seed a tiny bug in a fixture worktree (not the live repo).
2. Ask the agent (via the chat API with tools enabled) to locate, fix, and test it.
3. Record the full tool-turn trace (already supported via `tool_turn_observability`) as proof.

**Verify:** Bug fixed, tests green, trace shows `terminal:run` → `pytest` → plain-answer closeout. Update `docs/architecture/00-current-state.md` only after this proof (per its own interpretation rule).

---

## Stage 4 — Borrow from Hermes (optional, deferred)

- **T4.1 Skills system** — `guardian/skills/` as procedural memory (skill packs; maps onto imprint-zero personas).
- **T4.2 Toolset composition** — group tools per surface (mirror `toolsets.py` composition instead of flat manifest).
- **T4.3 MCP** — replace the `gm:show-mcp-map` "not available" stub with a native MCP client for external tool servers.

---

## Risks, tradeoffs, open questions

1. **Prompt-injection surface.** Tool *results* are untrusted input to the model (e.g. `git log` output, file contents). Mitigations already present: output caps (`max_output_kb`), read-only defaults, write approval. Do not feed raw tool results into future prompts without the existing redaction policy (`guardian/command_bus/redaction_policy.py`).
2. **Provider tool-calling reliability.** The loop was constrained to one call for deepseek — presumably a reliability decision. Relaxing it (Task 1.3) needs the turn budget + per-provider capability flag; verify with the local provider (`whooshd-mlx`) before claiming support.
3. **Approval UX.** Where does the user click "approve"? Frontend modal, CLI prompt, or API-only for now? This decides how `approval_tokens.py` is surfaced. **Open question for Chris.**
4. **Local-first beta posture.** `00-current-state.md` says terminal execution is unproven — Stage 3 proof must land before any release claim widens. Do not let Stage 1–2 changes imply shipped coding-loop support.
5. **Redis queue coupling.** Chat flows through the queue; verify the tool loop behaves under queue worker semantics (turn-lock, terminal events) — the current state doc flags this as needing fresh evidence.
6. **Two registries.** The CLI-walker manifest (`guardian/runtime/tools/registry.py`) is a parallel universe. Decide: delete it, or make it the *source* for the bus. Recommended: delete once the curated allowlist is live (it is only consumed by a TUI diag app today).

---

## Execution notes (for whoever implements)

- Follow AGENTS.md: task-scoped changes, validation per task, commit hash in closeout, no `.env` commits.
- Work from the canonical repo (`/Volumes/Dev_SSD/Codexify-main`), preferably a feature worktree, per the worktree convention.
- TDD: every task starts red, ends green, commits after each task.
- Test commands run from repo root: `.venv/bin/pytest <target> -q`.
