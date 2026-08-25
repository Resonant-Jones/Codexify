# Codexify vs Hermes: Architecture Comparison

> **Purpose:** Compare Codexify's agent architecture against Hermes Agent (Nous Research) to explain the "spiky utility" of Codexify's current tooling, answer *how to give the Codexify agent terminal access*, and map a path to *Codexify improving Codexify*.
>
> **Audience:** Chris (founder), and anyone reviewing Codexify architecture with fresh eyes.
>
> **Method & provenance:** Read-only inspection of both source trees on 2026-08-08. Codexify examined at commit `68f080029368395dd77a18df0ca724c24ea51a04` (branch `codex/reconcile-dlg-pao-history`). Hermes examined at the local v0.20.0 source checkout (`/Volumes/Dev_SSD/Hermes Agent Source Code`; not a git repo at that path). Every claim below carries a `path:line` reference.

---

## 1. TL;DR

Codexify is not one agent with disconnected features — it is **three separate agent stacks that do not talk to each other**:

| Stack | Role | Status |
|---|---|---|
| **A. Chat agent** | memory retrieval + context assembly + multi-provider chat | Working, but **the model is never handed a tool list** |
| **B. Command bus / tools lane** | OpenAPI → command manifest → `ToolSpec` → OpenAI function schema, with policy/approval | Fully built, but **not consumed by the chat agent** |
| **C. Coding-agent stack** | sandboxed command executor, worktree leases, execution ledger, commit gate, Codex-runner bridge | Present on `main`, **terminal execution still unproven** (per `docs/architecture/00-current-state.md`) |

The unification problem is plumbing: attach B's manifest to A's completion call, and point both at C's executor. The pieces are all there — including a *safer terminal tool than Hermes's* — they are just not wired together.

---

## 2. The three stacks in detail (with evidence)

### Stack A — The chat agent (working, tool-blind)

- `guardian/core/chat_completion_service.py` (6,119 lines) is the shared completion orchestrator: context assembly, provider routing, persistence, terminal evidence.
- `guardian/core/ai_router.py` handles provider calls, vision routing, and **normalizes DeepSeek tool calls** (`normalize_deepseek_tool_calls`, `ai_router.py:44,614`).
- A tool loop **exists** in the chat path (`chat_completion_service.py:5085–5438`): it inspects the first completion's `finish_reason`, and if the model emitted a `tool_decision`, executes via `execute_invoke(..., execution_lane="tools", allow_write_execution=False)` (`:5315–5322`) and records `ToolTurnState` / `ToolLoopStopReason` observability.
- **But tools are never attached to the request.** `chat_completion_service.py:1272` passes `tools` only `if provider == "deepseek"`, and a repo-wide search found **no code that ever assigns `task.tools`** — so it is always `None`. The loop's entry additionally demands *exactly one* tool call (`:5266`). The loop is dormant: the model is never told tools exist, so it can never emit a tool call.
- Frontend/route layer confirms: no `tools` payload is built in `guardian/routes/chat.py`.

### Stack B — The command bus / tools lane (fully built, unused by chat)

- `guardian/command_bus/manifest.py` builds an **OpenAPI-backed manifest**: every FastAPI route becomes a `CommandSpec` (method, path_template, operation_id, input_schema, risk, effect, idempotency, approval_mode). Served at `GET /manifest` (`guardian/routes/command_bus.py:73`).
- `guardian/tools/derive.py` converts manifest commands into `ToolSpec` objects; `guardian/tools/spec.py` renders them as OpenAI function tools (`to_openai_function_tool()` carries `x_codexify_tool_id`) and defines `ToolCallRequest` / `ToolCallResponse` / `ToolManifestEnvelope` (v2.0).
- `guardian/tools/registry.py` holds the specs and applies per-command overrides (`guardian/tools/overrides.py`).
- Execution: `guardian/command_bus/invoke.py::execute_invoke` dispatches with policy, approval tokens (`guardian/tools/approval_tokens.py`), permission profiles, redaction, and observability (`command_bus/tool_turn_observability.py`).
- `guardian/routes/command_bus.py` exposes the tool-turn execution lane with `allow_write_execution=False` by default in the chat path (`:5322`) — i.e. write commands are policy-blocked today.
- A **second, vestigial tool surface**: `guardian/runtime/tools/registry.py` walks the entire Click/Typer CLI and generates `guardian/runtime/tools/manifest.json` (595 lines of tool schemas: `codemap:query`, `embed`, `memory:*`, `gm:*`, …). Its only consumer is a TUI diagnostics app (`guardian/tui/diag_app.py`). Generated, never fed to the model.

### Stack C — The coding-agent stack (the "improve Codexify" machinery, unproven)

- `guardian/core/orchestrator/cli_sandbox.py` — the standout: `WorkspaceRootManager` (every path resolved and forced under a workspace root; escape raises `PermissionError`, `cli_sandbox.py:55–68`), `CommandCatalog.default()` — a **whitelist** of commands (`git status`, `git diff`, `pytest`, `pnpm test`) each with `timeout_seconds`, `max_output_kb`, `requires_network`, `allowed_paths` (`:111–141`), and `CommandExecutor.execute()` with network-egress gating, param validation, path-prefix validation, and output caps (`:148–266`).
- `guardian/agents/` — coding discipline machinery: `work_orders.py`, `work_order_store.py`, `execution_ledger_*`, `commit_gate.py`, `test_results.py`, `worktree_lease_store.py`, `coding_agent_contracts.py`.
- `guardian/codex_runner_bridge/adapter.py` — JSON-only boundary protocol invoking the `codexrun` binary (subprocess, 30s timeout).
- `codex_runner/` — runner, campaign engine, TUI, prompts (a separate package at repo root).
- Current truth (`docs/architecture/00-current-state.md`, updated 2026-08-08): "successful terminal coding execution remains unproven"; "The bounded Coding Loop lane lacks fresh proof of provider adapter execution, terminal result persistence, and durable source-thread readback."

---

## 3. Head-to-head comparison

| Capability | Hermes | Codexify | Verdict |
|---|---|---|---|
| **Tool registry** | One self-registering `ToolRegistry`; every tool module calls `registry.register(name, toolset, schema, handler, check_fn)` at import (`tools/registry.py:521`); AST-scanned discovery (`discover_builtin_tools`) | Dual: command-bus `ToolSpec` (unwired) + CLI-walker manifest (unread) | Hermes simpler; Codexify's bus abstraction is elegant — just wire it |
| **Tools in the LLM call** | Yes — per-toolset schema injected into every completion | **No** — never attached (deepseek-only gate + `task.tools` never set) | **Codexify's core gap** |
| **Terminal** | `terminal` tool: subprocess, timeout caps (`FOREGROUND_MAX_TIMEOUT=600`), output cap (`max_result_size_chars=100_000`), local/docker/modal backends, interrupt support (`tools/terminal_tool.py:112,3424`) | `cli_sandbox.CommandExecutor`: whitelisted commands, root containment, timeout, output cap, network gate — but only reachable from the orchestrator | Codexify already has a *safer* terminal; expose it |
| **File tools** | `read_file`, `write_file`, `patch`, `search_files` (ripgrep) | None in agent surface; only `codemap:query` (Q&A over a pre-built index) and `embed` (RAG ingest) | Gap for self-improvement |
| **Web** | `web_search`, `web_extract`, browser automation | `browser_host/` exists separately; not agent-accessible | Gap |
| **Memory** | `memory` tool + skills + `session_search` (SQLite FTS5) | **Deeper**: context broker, source modes (conversation/personal-knowledge/project/workspace/Obsidian), retrieval policies, fact-candidate pipeline, memory-os | **Codexify wins** |
| **Connectors** | Gateway channels: Telegram, Discord, Signal, WhatsApp, iMessage, email, webhooks (`gateway/platforms/`, `channel_directory.py`, `hermes_cli/telegram_managed_bot.py`, `tools/discord_tool.py`) | `guardian/connectors/` (github, google, gsuite, notion, slack, oauth) + `channels/` adapters + `integrations/` (google_drive, google_oauth) | Different philosophies: Hermes = messaging channels; Codexify = third-party APIs |
| **Cron** | `cronjob` tool + scheduler | `guardian/cron/` (scheduler, executor, models) + `routes/cron.py` | Parity |
| **Delegation** | `delegate_task` subagents | `delegation_service`, work orders, execution ledger | Parity-ish; Codexify more governed |
| **MCP** | Native MCP client + catalog | `gm:show-mcp-map` → "MCP integration not available" | Gap |
| **Skills** | First-class (`skills_list/view/manage`, curator) — the self-improvement engine | `guardian/skills/` contains only `summarize.py` + a marketing folder | Gap |
| **Self-improvement** | Skills + memory + full coding tools in one loop | `codex_runner` + worktree leases + commit gate — driven by the *Codex CLI*, not Codexify's own agent | The wiring being asked for |

---

## 4. Direct answers

### 4.1 "How do I give my agent access to the Terminal? Just give it a search function as a tool?"

**No — search and terminal are different risk classes; you want both, separately gated.**

- **Search** is read-only (ripgrep over files → matching lines). It is the *see* tool. Cannot hurt anything.
- **Terminal** is arbitrary code execution (`subprocess.run("rm -rf ~")` runs). It is the *act* tool. Needs timeout, output cap, path containment, whitelist-or-approval, and ideally interrupt.

Hermes models this as two tools with separate schemas (`search_files` vs `terminal`, both in `_HERMES_CORE_TOOLS`, `toolsets.py`), and gates the terminal with approval + caps.

**Codexify already has the terminal — `cli_sandbox.CommandExecutor` is a better-designed one for Codexify's needs** (whitelist over arbitrary shell; mandatory root containment). Wiring it into the agent surface is three changes:

1. **Expose as `ToolSpec`s** — add `terminal:*` commands to the command-bus manifest (or the tools lane) with `effect="write"`, `risk="mutating"`, `requires_confirmation=True` (`spec.py` already renders these).
2. **Populate `task.tools`** — build the tool list from the manifest (curated), set it on the completion task, and drop the `provider == "deepseek"` condition (`chat_completion_service.py:1272`).
3. **Dispatch to the sandbox** — the tools lane already runs through `execute_invoke`; the handler for `terminal:*` calls `CommandExecutor.execute()` rather than a FastAPI route. Relax the single-tool-call cap (`:5266`) and route writes through the existing approval-token gate instead of blanket `allow_write_execution=False` (`:5322`).

### 4.2 "I want to use Codexify to improve Codexify"

A coding agent needs five primitives: **read files, search files, write files, run commands, task/memory layer.** Hermes has all five; Codexify has the last one fully, run-commands partially (unwired), and no file read/write tools.

Two viable paths:

- **Path 1 — expose the coding loop as tools (recommended, matches Codexify's governance):** wrap `routes/coding_work_orders.py` + `agents/work_orders.py` as `ToolSpec`s (`coding:create_work_order`, `coding:run`, `coding:read_result`). The chat agent spawns bounded, ledger-audited, commit-gated coding tasks and reads results back. The AGENTS.md discipline (task-scoped changes, validation proof, commit hash in closeout) becomes enforceable *by construction*.
- **Path 2 — direct sandbox tools (Hermes's model):** add `read_file` / `search_files` / `write_file` backed by `WorkspaceRootManager` containment, plus the sandboxed terminal from §4.1. The agent edits the repo itself, tests through the whitelist, commits under the protocol. Faster; discipline is prompted, not enforced.

**Acceptance test (same for both):** give Codexify a real task on its own repo — read code, run tests, fix a bug, commit — and prove it end to end. This is exactly what `00-current-state.md` marks unproven.

---

## 5. What to emulate from Hermes (and what not to)

**Steal:**
- **Toolset composition** (`toolsets.py`): group tools (`web`, `file`, `terminal`, `memory`) and compose per surface. Codexify's manifest is all-or-nothing today.
- **Self-registration**: one registry, one call. Codexify has two registries; consolidate on the command-bus one, or make the CLI-walker the *source* for the bus instead of a parallel universe.
- **Skills-as-procedural-memory**: Hermes's actual self-improvement engine. Maps naturally onto Codexify's imprint-zero / persona system.
- **Approval-gated file writes** (Hermes `write_approval.py`, `path_security.py`); Codexify already has `approval_tokens.py` — reuse it.

**Don't steal:** the ~100-tool sprawl. Hermes ships broad because it targets a dozen surfaces. Codexify's strength is *curation and governance* — constitutional heuristic, risk/effect/approval fields, workspace containment. Keep the narrow waist; widen deliberately.

---

## 6. Recommended unification (staged)

1. **Stage 1 — attach tools to the chat loop.** Curated allowlist from the command manifest; populate `task.tools` for all providers; generalize the tool loop (multi-call turns, turn limit, approval gate for writes).
2. **Stage 2 — sandboxed file + terminal tools.** Extend `CommandCatalog`; register `terminal:*` and file `ToolSpec`s backed by `CommandExecutor` + `WorkspaceRootManager`; write approval via existing tokens.
3. **Stage 3 — coding-loop lanes as tools.** Expose work-order `ToolSpec`s; wire execution ledger, test results, commit gate, worktree leases; prove the end-to-end "Codexify improves Codexify" loop.
4. **Stage 4 — borrow the rest deliberately:** skills system, toolset composition, connector/channel consolidation, MCP.

See the companion implementation plan in `docs/Plans/2026-08-08-unify-agent-tools-terminal-and-coding-loop.md`.
