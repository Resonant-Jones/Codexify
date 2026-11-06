# Guardian Native Agent Tool Surface — Codexify.Dev as Reference Implementation

> **Status:** Draft for review (2026-11-06). **No tool has been integrated.** Awaiting explicit go-ahead before any implementation.
> **Requested by:** Resonant Jones — "plan out what is needed in order to integrate the tools located inside of the '.Dev' plugin I forked on Github."
> **Companion docs:** `docs/Plans/2026-08-08-unify-agent-tools-terminal-and-coding-loop.md` (prior plan; largely unimplemented — reconciled below, not duplicated) and [`ADR-111`](../architecture/adr/111-operator-controlled-native-execution-postures.md) (Proposed) for the operator-authority and execution-posture model that governs §5 and §6.
> **Reconciled 2026-11-06** with a parallel plan produced by another agent (Axis) and with ADR-111. §5 now defers the isolation question to ADR-111 instead of treating it as a product menu; §6.1 records the parallel-sequencing decision; §8 row 1 records the new dependency. The tool inventory, the architecture analysis, and Stage 4 dispositions are unchanged.
> **Source truth checked at:** commit `806d293e9` (branch `feat/auto-20261106-3676c957`); reconciled against `origin/main` @ `e72464e05`.

---

## 0. Executive summary

The `.Dev` project (upstream `devnoname120/codexify`, forked locally as `Resonant-Jones/codexify.dev`) is a **Rust MCP server** that hands a ChatGPT conversation ~41 tools: file I/O, shell, git, search, memory, skills, diffs, artifacts. It is the closest existing thing to the tool surface you want Guardian to have.

Three findings reframe the request:

1. **Guardian's model-visible tool surface today is three commands** — `op::health_health_get`, `op::repository.search`, `op::history.search` — and only on `deepseek` or `local`+`whooshd` providers (`guardian/tools/chat_exposure.py:28-30, 333-345`). This is not a "add 41 tools" job. It is a "build the native tool lane" job.

2. **Most of `.Dev`'s tools already have a Codexify counterpart.** Guardian has projects, worktrees, memory, skills, personas, diffs, continuity, channels, diagnostics, and a real sandbox. Porting 41 tools would create exactly the duplicate product surface `AGENTS.md` forbids. The honest scope is **~14 genuinely new capabilities**, plus a uniform contract that exposes ~25 existing capabilities to the model.

3. **`.Dev`'s deepest contribution is not the tool list — it is the tool *contract*.** Each `.Dev` tool carries a model-written description, a flat JSON Schema, and a four-axis behavior annotation (`read_only`, `destructive`, `idempotent`, `open_world`) plus a human justification (`src/tool.rs:96-116`). Guardian's `CommandSpec` carries a weaker three-axis equivalent (`risk`, `effect`, `idempotency`) with no `open_world` and no justification. **The contract is the port.**

**Recommendation:** build a native tool family on Guardian's existing command bus using the `layer="internal"` precedent (not HTTP routes), carry `.Dev`'s behavior contract into `CommandSpec`, and treat Codex/Claude Code/Pi strictly as coordination adapters that stay where they already are.

---

## 1. Sources of truth examined

| Source | Provenance | Access |
|---|---|---|
| `Resonant-Jones/codexify.dev` | Your fork | GitHub API, full tree (221 blobs), `main` @ `d1a80c9f5` |
| `devnoname120/codexify` | Upstream (Paul, Zürich) | MIT License, © 2026 devnoname120 |
| `guardian/tools/`, `guardian/command_bus/`, `guardian/core/orchestrator/cli_sandbox.py` | This repo @ `806d293e9` | Read directly |
| `docs/Plans/2026-08-08-unify-agent-tools-terminal-and-coding-loop.md` | This repo | Read directly |

**Identity confirmed:** upstream owner is `devnoname120`, profile name **Paul**, `blog: qwerty-fr.org`, location Zürich, Switzerland. The project describes itself as *"Turn ChatGPT into a Codex-like coding environment — without using your Codex/Work quota."* This matches your account of him exactly.

**License: MIT.** Porting is permitted with attribution — retain the upstream copyright notice in any ported source. No copyleft obligation, no network-copyleft (AGPL) exposure.

**Your fork diverged:** 3 commits ahead / 145 behind upstream, in 9 files (`src/config.rs`, `src/types.rs`, `src/quickstart.rs`, `src/server.rs`, `README.md`, `CHANGELOG.md`, `docs/REFERENCE.md`, `codexify.config.json*`). Branches: `feature/instance-identity` and `contribution/instance-identity-upstream`. **Your fork's contribution is instance identity/naming** (multi-instance deployment, `instanceName` → `AxisNode`/`VaultNode`). That is your work, not his, and it is orthogonal to the tool port — port the **upstream** tool semantics, keep your instance-identity work separate.

---

## 2. Guardian's tool architecture today (PROVEN by direct reading)

### 2.1 The pipeline

```
FastAPI app.openapi()                      guardian/command_bus/manifest.py:22-23
   └─> CommandSpec per HTTP operation      manifest.py:43-60
       + 2 internal bridge commands        manifest.py:62
   └─> execute_invoke(...)                  guardian/command_bus/invoke.py:311
       ├─ policy         guardian/tools/policy.py:73      allow|deny|require_confirmation
       ├─ permission     guardian/command_bus/permission_profiles.py:71
       ├─ redaction      guardian/command_bus/redaction_policy.py:54
       └─ dispatch → loopback HTTP, or internal handler
   └─> model visibility gate                guardian/tools/chat_exposure.py:303
```

### 2.2 Two tool layers exist, and one of them is dead

| Layer | Where | Status |
|---|---|---|
| `layer="raw"` (HTTP) | `manifest.py:43-60` | **Live.** Every FastAPI route is a command. |
| `layer="internal"` | `guardian/codex_runner_bridge/command_bus.py:31-39` | **Live.** 2 commands: `internal::guardian.codex_runner.validate_plan_pack`, `internal::guardian.codex_runner.orchestrate_dry_run_preflight`. `method="INTERNAL"`, `path_template=""`. |

`guardian/tools/registry.py` (`ToolRegistry`), `spec.py:128` (`to_openai_function_tool`), `approval_tokens.py`, and `coercion.py` have **zero call sites**. `guardian/runtime/tools/registry.py` (a second, CLI-walking registry) is consumed only by `guardian/tui/diag_app.py:24` — never fed to a model. The live model-facing tool shape is a flat `{command_id, description, input_schema}` dict (`chat_exposure.py:98-107`).

**Do not revive `guardian/tools/registry.py`.** The repo already retired that abstraction (see `docs/research/codexify-vs-hermes-architecture-comparison-2026-08-08.md:42`, which calls it *"a second, vestigial tool surface… Generated, never fed to the model"*).

### 2.3 The write gate

`invoke.py:558-570` — any command that is not `effect="read"` with a `GET`/`HEAD` method, and is not the Codex Runner bridge, is blocked with `phase1_write_blocked` unless `allow_write_execution=True`. The tools lane *does* pass `allow_write_execution=True` (`routes/command_bus.py:116`, `chat_completion_service.py:2947`). `policy.py:120-135` still marks writes `require_confirmation`, which `apply_policy_mode` (`policy.py:199-201`) converts to a block unless `confirmation_granted`.

**Net:** the plumbing for "read tools today, write tools later" exists. The prior 2026-08-08 plan's Task 1.4 (write approval) was never built; `approval_tokens.py` is unwired.

### 2.4 The sandbox that already works

`guardian/core/orchestrator/cli_sandbox.py` is real and proven:

- `WorkspaceRootManager.resolve_under_root` (`:55-68`) — containment, `PermissionError` on escape.
- `CommandCatalog.default()` (`:108-149`) — **allowlisted verbs**: `git_status`, `git_diff`, `pytest`, `pnpm_test`. Each with `allowed_params`, `timeout_seconds`, `max_output_kb`, `requires_network`, `allowed_paths`.
- `CommandExecutor.execute` (`:167-199`) — `cwd=root`, network egress env gate, output-cap enforcement (`:255-266`).

### 2.5 The harness adapters are already correctly scoped

| Adapter | Requires | Model-visible? |
|---|---|---|
| `guardian/codex_runner_bridge/` | External binary `codexrun`; **hardcoded** `CODEX_RUNNER_ROOT = Path("/Volumes/Dev_SSD/Codex-Runner")` (`contracts.py:23`) | No — `layer="internal"` |
| `guardian/core/executors/registry.py:182-226` | `CODEXIFY_CODEX_BIN` (official), `CODEXIFY_CLAUDE_CODE_BIN` (optional), `CODEXIFY_OPENCODE_BIN` (optional) | No — delegation lane |
| `guardian/pi/` | Injected or Pi-backed harness via `subprocess` | No — optional coordination rail |
| `guardian/mcp_memory/` | Optional MCP SDK | No — stdio MCP **server** for external clients |

**Your point 1 is already architecturally true:** no external harness is load-bearing for Guardian's core chat tool surface. The live path is pure in-process Python plus loopback HTTP. What is missing is not harness removal — it is that Guardian has **no native tools of its own** to replace them with. That is the gap this plan closes.

---

## 3. The `.Dev` tool inventory

41 tool modules in `src/tools/`. 37–39 registered in default configuration; up to ~49 with chat/widget modes enabled (`src/registry.rs:40-140`).

Behavior codes below are `.Dev`'s own: `R`=read_only, `D`=destructive, `I`=idempotent, `W`=open_world.

### 3.1 Filesystem & search

| Tool | Behavior | `.Dev` description (abridged) | Codexify counterpart | Disposition |
|---|---|---|---|---|
| `read_file` | R I | Line-numbered, windowed large files | `repository.search`, `codex_memory` | **New** (native file read) |
| `write_file` | D I | Write/overwrite, project-relative | — | **New** (approval-gated) |
| `glob` | R I | Glob patterns, sorted paths | `whooshd`, `code_graph` | **New** |
| `grep` | R I | Regex, bounded matches, ignore rules | `repository.search` (literal only) | **New** (regex) |
| `tree` | R I | ASCII tree, default depth 3 | — | **New** |
| `list_directory` | R I | Tab-separated entries with sizes | — | **New** |
| `view_image` | R I | Read local image for visual inspection | `image_gen`, `browser_host` | **New** |

### 3.2 Execution

| Tool | Behavior | `.Dev` description (abridged) | Codexify counterpart | Disposition |
|---|---|---|---|---|
| `exec_command` | D W | Shell; `yield-time_ms`; returns `session_id` if still running | `cli_sandbox.CommandExecutor` (allowlisted verbs only) | **Contested — see §5** |
| `write_stdin` | D W | Feed/poll a resident session | — | **Contested — depends on `exec_command`** |
| `clock_curr_time` | R I | Current UTC time | trivial | **New (trivial)** |
| `clock_sleep` | R I | Pause; ends early on new input | — | **Defer** |

### 3.3 Git & diff

| Tool | Behavior | Codexify counterpart | Disposition |
|---|---|---|---|
| `git_status` | R I | `cli_sandbox` catalog `git_status` | **Reuse existing** |
| `git_log` | R I | — | **New** (catalog addition) |
| `git_commit` | D W | Work-order commit gate | **Reuse existing** (route via work orders) |
| `git_push` | D W | — | **Defer** (network + destructive) |
| `show_diff` | R I | `guardian/federation/diff_store.py` | **Reuse existing** |
| `apply_patch` | D — | Codex patch grammar, verified-then-sequential | **New** (highest value) |

### 3.4 Memory, plans, skills, context

| Tool | Behavior | Codexify counterpart | Disposition |
|---|---|---|---|
| `remember` / `update_memory_note` / `forget_memory_note` / `recall` | varies | `guardian/memory`, `memoryos`, `memory_graph`, `personal_facts` — far richer | **Reuse existing** |
| `update_plan` | D I | `guardian/tasks`, work orders, plan packs | **Reuse existing** |
| `skills_list` / `skills_read` | R I | `guardian/skills/registry.py` | **Reuse existing** |
| `get_project_doc` | R I | `AGENTS.md` loader, `cognition/system_docs` | **Reuse existing** |
| `get_agent_brief` | R I | `cognition/personas`, `system_profiles` | **Reuse existing** |
| `get_environment` | R I | — | **New (trivial)** |

### 3.5 Workspace, artifacts, lifecycle

| Tool | Behavior | Codexify counterpart | Disposition |
|---|---|---|---|
| `list_projects` / `set_project_root` | varies | `guardian/routes/projects.py` — **already live routes** | **Reuse existing** |
| `import_host_file` / `export_host_file` | varies | `browser_host` attachment adapter, `export_engine.py`, signed media | **Reuse existing** |
| `continuation` / `continue_task` | — | `guardian/threads`, `continuity` | **Reuse existing** |
| `markdown_chat` (`chat_read`/`chat_write`/`chat_await`) | — | `guardian/channels`, IM routing, `messaging` | **Reuse existing** (different transport) |
| `setup` / `setup_status` / `doctor` / `check_for_updates` / `self_update` / `self_update_status` | varies | `guardian/diagnostics`, `self_check.py` | **Reuse existing** / exclude self-update |
| workspace UI / setup UI / chat UI widgets | — | Codexify frontend | **Exclude** — ChatGPT-widget-specific |

---

## 4. The contract to port (the real payload)

`.Dev`'s `Tool` trait (`src/tool.rs:96-175`) requires:

```rust
fn name(&self) -> &'static str;
fn description(&self) -> String;          // written FOR the model
fn behavior(&self) -> ToolBehavior;        // R / D / I / W + justification
fn input_schema(&self) -> Value;           // flat JSON Schema
fn requires_closed_input_schema(&self) -> bool;  // default true
```

### 4.1 Mapping table — `.Dev` behavior → Guardian metadata

| `.Dev` | Guardian `CommandSpec` | Guardian `InvokePermissionProfile` | Notes |
|---|---|---|---|
| `read_only` | `risk="read_only"`, `effect="read"` | — | direct |
| `destructive` | `risk="mutating"`, `effect="write"` | — | direct |
| `idempotent` | `idempotency="safe"` | — | direct |
| `open_world` | **NO EQUIVALENT** | `network_allowed` | **must add** — this is the axis that separates `git_commit` from `git_push` |
| `justification` | **NO EQUIVALENT** | — | **must add** — becomes the approval reason code shown to the user |
| flat `input_schema` | `input_schema` (wrapped as `{path_params,query,headers,body}` by `derive.py:26-56`) | — | projection happens at `chat_exposure.py`, not in the manifest |
| closed schema | `additionalProperties: false` | — | already the convention |

**Two contract fields must be added to `guardian/command_bus/contracts.py:161-176`:** `open_world: bool` and a justification string. Without them, Guardian cannot distinguish a local read from a network push, and its approval UI cannot explain *why* a tool is gated. This is the single most important schema change in the plan.

### 4.2 Where the tool goes: three options

**Option A — HTTP routes (FastAPI).**
Add a route per tool family → auto-derived into the manifest as `op::<operationId>`.
- ✅ Reuses the *entire* live pipeline with zero changes to policy, permissions, idempotency, redaction, observability.
- ❌ Wrong shape. `.Dev` tools take flat args (`cmd`, `path`, `pattern`); HTTP routes give `{path_params, query, headers, body}`. The model-facing projection already hand-builds flat schemas (`chat_exposure.py:161-187`), so you'd hand-build ~14 more projections anyway.
- ❌ An HTTP round-trip through the loopback adapter is a strange transport for `exec_command` and resident sessions.
- ❌ `/tools/manifest` and `/api/tools/manifest` are **quarantined by test** (`tests/core/test_supported_profile_quarantine.py:376,385-386,432,698` assert 404 and absence from `openapi.paths`). Adding routes under those paths breaks a supported-profile gate.

**Option B — `layer="internal"` native command family. ← Recommended**
Exactly the `codex_runner_bridge` precedent. `CommandSpec.method` is a plain `str`, not an HTTP Literal, so `method="INTERNAL"` is already legal. Declare `layer="internal"`, `path_template=""`, `command_id="native::<family>::<tool>"`.
- ✅ Matches the one existing native-tool precedent — no new abstraction invented.
- ✅ No HTTP round-trip for shell/filesystem work.
- ✅ Carries flat schemas and long-running session semantics naturally.
- ✅ Still gets the full policy / permission / redaction / idempotency / observability treatment, because all of that runs in `execute_invoke` *before* dispatch.
- ⚠️ Requires one new dispatch branch in `invoke.py` alongside the existing `is_guardian_bridge_command` branch (`invoke.py:434-437`).
- ⚠️ Needs `command_id` namespacing to avoid collisions with `op::` route IDs.

**Option C — Run `.Dev` as an external MCP server and add an MCP client to Guardian.**
- ✅ Fastest proof; zero porting; `.Dev` already speaks MCP.
- ❌ **Violates the sovereignty requirement directly.** Guardian would depend on an external Rust binary — exactly the harness-dependency you are removing.
- ❌ Guardian has **no MCP client at all** today. `guardian/mcp_memory/` is a stdio MCP *server*; `mcp.json` at repo root is consumed by nothing in the repo; `guardian/guardian_main.py:197` has the MCP import commented out. This would be net-new architecture, not a reuse.
- ⚠️ Viable only as an **optional, off-by-default adapter** for users who want the long tail of third-party MCP servers.

**Decision: Option B as the target. Option C as an explicitly optional adapter later. Option A only where a tool genuinely maps to an existing Guardian HTTP route** (projects, worktrees, artifacts) — in which case you are *exposing an existing route*, not adding a new one.

---

## 5. The one genuine design conflict: `exec_command`

This needs your ruling, and it is the reason the rest of the plan cannot be fully specified without you.

`.Dev`'s `exec_command` (`src/tools/exec_command.rs`) is **unrestricted shell**: `cmd: String` → platform shell, plain pipes (not PTY), resident sessions (`maxSessions: 8`, `idleTimeoutMs: 300000`), `yield-time_ms` handoff, `write_stdin` for follow-up. Its own description says *"Command execution is unrestricted."*

Guardian's `cli_sandbox.py` is **allowlisted verbs**: `git_status`, `git_diff`, `pytest`, `pnpm_test` — each with a fixed `args_template`, an `allowed_params` whitelist, a timeout, an output cap, and a network gate. A model cannot invent a command; it selects a catalog id.

The prior 2026-08-08 plan chose allowlist (`terminal:run` over `CommandExecutor`). `.Dev` chose free shell. **Both are coherent; they are not the same product.** Three coherent positions:

| | Free shell (`.Dev`) | Allowlisted verbs (current `cli_sandbox`) | **Two-tier (recommended)** |
|---|---|---|---|
| Capability | Total | Narrow | Total for humans, narrow for autonomous agents |
| Guardrail | Prompt + model discipline | Catalog + params + caps | Catalog for autonomous; explicit human-authorized shell for the rest |
| Sovereignty | Full | Full | Full |
| Cost | Must build a real sandbox (seccomp/container/landlock) — no OS-level isolation boundary exists in the runtime today | Already paid | Pay the expensive tier only when used |
| Fits `Doctrine of Legible Responsibility` | Weakly | Yes | Yes, if the escalation is legible |

**Recommendation — two-tier:** keep `cli_sandbox` as the default autonomous lane, and add a second, separately-gated lane for arbitrary shell, reachable only with an explicit per-authorization grant (the `InvokePermissionProfile` already has `shell_allowed`, `shell_read_only`, `allowed_shell_commands`, `network_allowed` — `permission_profiles.py:177-205` — and `guardian/security/path_guard.py` already provides the write-path guard). `shell_read_only=True` is already a first-class concept in your permission vocabulary; the escalation path exists. **It just has no executor behind it yet.**

### 5.1 Update (2026-11-06, after ADR-111) — this section is now governed by an accepted-track ADR

The framing above was right about the product tension but understated the governance. Three corrections:

1. **The isolation question is not a design choice to pick in this plan — it is an architecture decision with an existing Accepted counterpart.** [ADR-077](../architecture/adr/077-sandbox-execution-authority-and-provider-boundary.md) is Accepted and requires provider-neutral sandboxed execution of model-generated commands, with sandbox-construction authority in a Sandbox Provider's own administrative plane. It records a *failed* Bubblewrap attempt under the checked-out worker container and notes that the working configurations would have given the credential-hosting process ambient sandbox-admin authority. An operator-selected unrestricted direct-execution mode is therefore a **deliberate exception to an Accepted ADR**, requiring explicit human acceptance — not a configuration toggle.
2. **There is a provider-neutral sandbox contract in flight, so "no sandbox exists" understates it.** ADR-109 (Pending, PR #1006) defines `guardian/sandbox/contracts.py` (`sandbox.execution.v1`) with posture semantics — read-only workspace, egress deny/allowlist, CPU, memory, storage ceiling, timeout, teardown, secret isolation — plus a posture-capability gate in `guardian/sandbox/policy.py` and a `docker_cloud` adapter. ADR-078 records a **proved** hosted Modal conformance. The honest current truth on `main` is narrower: `guardian/core/guardian_permission_posture.py` states that no sandbox provider is wired into the coding worker and that the adapter runs a subprocess with no OS-level isolation. Both statements are true and they are about different layers.
3. **The existing Guardian Compose container is not automatically an ADR-077 Sandbox Provider**, and no posture may be claimed on its behalf.

**Consequence for this plan:** `exec_command` / `write_stdin` are **gated on the accepted execution-authority decision**, not merely on a product ruling. [ADR-111](../architecture/adr/111-operator-controlled-native-execution-postures.md) (Proposed) now defines that authority model: five distinct authorities, persistent approval-free execution as a valid operator posture, three preserved execution targets (ADR-077-conformant Sandbox Provider, trusted container with disclosed boundaries, operator-authorized host-native in a component separate from Guardian's application process), and a truthful enforcement vocabulary. It proposes the host-native exception; it does not accept it.

`cli_sandbox.py`'s allowlisted-verb model remains the right **default** for autonomous execution under all three targets, because it is the only one that is truthful about what it enforces. The escalation lane needs an executor, not just a flag.

---

## 6. The plan

Staged so each stage is independently provable and ships no partial capability. This **supersedes and reconciles** `docs/Plans/2026-08-08-unify-agent-tools-terminal-and-coding-loop.md`: Stages 1–2 below absorb that plan's Tasks 1.1–2.4 (which were never implemented — `guardian/tools/allowlist.py` does not exist), and its Stage 4 "T4.3 MCP" becomes Option C above.

### 6.1 Sequencing decision (2026-11-06)

The governance track and the tool track run **in parallel**, not in series. Concretely:

| Track | Contents | Depends on the isolation ruling? |
|---|---|---|
| **Governance** | ADR-111 (Proposed) → operator posture resolution → executor selection | — (it *is* the ruling) |
| **Contract** | Stage 1 below — `CommandSpec.open_world` + justification | No |
| **Read-only tools** | Stage 4.1, 4.2, 4.6, 4.7, 4.8, 4.9 — `read_file`, `list_directory`, `tree`, `glob`, `grep`, context, plans, skills, memory, workspace | No |
| **Exec** | Stage 4.10 — `exec_command`, `write_stdin` | **Yes** |
| **Mutation** | Stage 4.3, 4.4 — `apply_patch`, `write_file` | **Yes** — these are filesystem mutations, which ADR-077 treats differently from reads |

**The qualification that makes the read-only track safe to run early:** read-only native tools must enforce authenticated account and Project scope, filesystem path containment including symlink boundaries, and bounded output — reusing the existing ownership and path-security infrastructure (`guardian/security/path_guard.py`, project ownership authority) rather than creating parallel authority. A read-only tool cannot violate ADR-077 invariants 6 or 7 because it neither mutates nor executes a process. **Any mutating or executing tool remains gated** on the accepted execution-authority decision.

This avoids unnecessary dependency serialization without compromising the architecture already accepted.

### Stage 0 — Baseline (prove where we stand)

| # | Task | Files |
|---|---|---|
| 0.1 | Snapshot truth: `git status`, `git rev-parse HEAD`, record the clean/dirty state and the active branch | — |
| 0.2 | Run the baseline suite and record pass/fail counts: `pytest -v tests/command_bus tests/routes/test_command_bus_phase1_manifest.py tests/core/test_chat_tool_exposure.py` | — |
| 0.3 | Write the **red** test that documents the gap: model-visible tool set is exactly 3 commands and contains no filesystem/shell tool | `tests/core/test_chat_tool_exposure.py` (extend) |

**Verify:** exit 0; the red test fails for the documented reason only.

### Stage 1 — Carry the `.Dev` contract into Guardian's schema

| # | Task | Files |
|---|---|---|
| 1.1 | Add `open_world: bool` and `justification: str` to `CommandSpec`; default `open_world=False` for existing raw routes so behavior is unchanged | `guardian/command_bus/contracts.py:161-176` |
| 1.2 | Derive `open_world` for raw routes conservatively (`/external/`, `/webhook`, `http`/`https` paths → `True`) | `guardian/command_bus/manifest.py:112-154` |
| 1.3 | Map `open_world` → `InvokePermissionProfile.network_allowed` check at dispatch | `guardian/command_bus/permission_profiles.py`, `invoke.py:395-411` |
| 1.4 | Thread `justification` into the policy reason code so the approval surface can explain the gate | `guardian/tools/policy.py:117-153` |
| 1.5 | **Decision record:** ADR covering Option B vs A vs C, the two-tier shell position, and the `.Dev` attribution | `docs/architecture/` (new ADR) |

**Verify:** `pytest -v tests/command_bus/test_permission_profiles.py tests/command_bus/test_manifest.py`; existing routes unchanged in derived metadata except the new defaulted field.

### Stage 2 — Build the native command family (the real seam)

| # | Task | Files |
|---|---|---|
| 2.1 | Create the family module. One registry of native tool definitions → `CommandSpec` list, mirroring `build_guardian_bridge_command_specs()` exactly | **Create** `guardian/native_tools/command_specs.py` |
| 2.2 | Append native specs to the manifest | `guardian/command_bus/manifest.py:62` |
| 2.3 | Add the dispatch branch: `layer="internal"` + `is_native_tool_command()` → native handler, mirroring the bridge branch | `guardian/command_bus/invoke.py:434-437`, `invoke.py` dispatch tail |
| 2.4 | Native command IDs namespaced `native::<family>::<tool>` to avoid collision with `op::` route IDs | same |
| 2.5 | Flat model-facing projection: native tools advertise flat JSON Schema (not the HTTP buckets), with `additionalProperties: false` | `guardian/tools/chat_exposure.py` (new projection helper) |
| 2.6 | Redaction + audit: native tool arguments pass through `redact_arguments`; add native-family rules for command text, env, and file paths | `guardian/command_bus/redaction_policy.py:13-26` |

**Verify:** `pytest -v tests/routes/test_command_bus_internal_surface.py` (extend) — native commands appear in the manifest, are invocable, and are auditable; a native command does **not** appear in the OpenAPI paths.

### Stage 3 — Model visibility and the tool loop

| # | Task | Files |
|---|---|---|
| 3.1 | Replace the hardcoded 3-command allowlist with a **curated, group-gated** native tool projection, keeping the existing 3 read tools as-is | `guardian/tools/chat_exposure.py:303-366` |
| 3.2 | Group gating: `CODEXIFY_AGENT_TOOL_GROUPS=fs,search,git,exec` (default `fs,search`) — mirrors the prior plan's `allowlist.py` groups, but backed by native specs rather than HTTP routes | `guardian/tools/allowlist.py` (**create**, as the prior plan intended) |
| 3.3 | Provider gate: the current `deepseek`/`local`+`whooshd` restriction (`chat_exposure.py:333-345`) is a provider-capability question, not a policy question — move the capability check into `chat_with_ai` so any function-calling provider can carry native tools | `guardian/core/chat_completion_service.py:1991-1993` |
| 3.4 | Multi-call support: the loop currently expects exactly one tool call per turn. Support N calls with a bounded turn budget (`CODEXIFY_TOOL_TURN_BUDGET`, default 5) | `guardian/core/chat_completion_service.py` tool-turn region |
| 3.5 | Keep every turn's observability: `tool_turn_id`, `tool_turn_state`, `loop_stop_reason` | `guardian/command_bus/tool_turn_observability.py` |
| 3.6 | **Wire the approval flow** — `approval_tokens.py` is currently dead. Bind it to the write gate so mutating native tools return `status="blocked"`, `approval_required=true`, and execute only after a valid `ToolApproveRequest` | `guardian/tools/approval_tokens.py`, `guardian/tools/policy.py` |

**Verify:** `pytest -v tests/core/test_chat_tool_exposure.py tests/core/test_chat_completion_service_tool_loop.py tests/core/test_chat_tool_admission_deadline.py`; a write tool is blocked without approval and executes after it.

### Stage 4 — Native capability families (ordered by value)

Each family is one native command group plus its handlers.

| # | Family | Tools | Backing | Guardrail |
|---|---|---|---|---|
| 4.1 | **Files (read)** | `read_file`, `list_directory`, `tree`, `glob` | `WorkspaceRootManager.resolve_under_root` (`cli_sandbox.py:55-68`) | read-only; root containment; `maxBytes`/`maxLines` caps mirroring `.Dev` `output` config |
| 4.2 | **Search** | `grep` | ripgrep if present, else bounded scan (prior plan Task 2.3) | root containment; ignore rules; bounded matches — `.Dev` elides long lines around the match; replicate |
| 4.3 | **Patch** | `apply_patch` | port `.Dev`'s Codex patch grammar + verified-then-sequential semantics | `effect="write"` → approval; root containment |
| 4.4 | **Write** | `write_file` | new handler | `effect="write"` → approval; refuse `.env`/credential paths (prior plan Task 2.3); read-before-overwrite advisory |
| 4.5 | **Git** | `git_log`, `git_status`, `show_diff` | extend `CommandCatalog.default()` (`cli_sandbox.py:108-149`) | read-only; `git_commit` routed through the **existing work-order commit gate**, not a raw shell |
| 4.6 | **Context** | `get_project_doc`, `get_agent_brief`, `get_environment` | reuse `cognition/system_docs`, `cognition/personas`, `system_profiles` | read-only; reuse, do not duplicate |
| 4.7 | **Plans & skills** | `update_plan`, `skills_list`, `skills_read` | reuse `guardian/tasks`, `guardian/skills/registry.py` | reuse |
| 4.8 | **Memory** | `remember`, `recall`, `update_memory_note`, `forget_memory_note` | reuse `guardian/memory`, `memoryos` | reuse — Guardian's is richer than `.Dev`'s |
| 4.9 | **Workspace** | `list_projects`, `set_project_root` | **already live routes** — expose, do not re-implement | reuse |
| 4.10 | **Exec** | `exec_command`, `write_stdin` | **blocked on the §5 decision** | two-tier per your ruling |

**Excluded from the port (and why):** `markdown_chat*` / `setup_ui_*` / `workspace_ui` — ChatGPT-widget-specific surfaces with no Guardian equivalent and no value to a self-hosted agent. `self_update` / `self_update_status` — Guardian's release surface is a different mechanism. `git_push` — network + destructive; defer past Stage 4. `import_host_file` / `export_host_file` — Guardian already has an artifact path; expose the existing one rather than porting.

### Stage 5 — Proof

| # | Task |
|---|---|
| 5.1 | End-to-end: in a **scratch worktree**, the agent reads a file, greps for a symbol, applies a patch, runs the project's tests through the sandbox, and reports a passing result — with a full `tool_turn_observability` trace |
| 5.2 | Negative proof: path escape, `.env` write, unapproved write, over-cap output, network-flagged command with `network_allowed=False` — each blocked with a legible reason |
| 5.3 | Provider proof: native tools carried by a function-calling provider other than deepseek/whooshd (requires 3.3) |
| 5.4 | Update `docs/architecture/00-current-state.md` **only after** the proof lands, per its own interpretation rule |

**Verify:** the trace shows `read_file` → `grep` → `apply_patch` → `pytest` → plain-answer closeout, with no harness binary involved anywhere in the chain.

---

## 7. Answers to your two questions

### 7.1 "Guardian sovereign; Codex/Claude/Pi only for coordination"

Already true architecturally. The adapters are: delegation executors (`core/executors/registry.py:182-226`), the Pi rail (`guardian/pi/`), and the Codex Runner bridge (`codex_runner_bridge/`, which needs an **external binary at a hardcoded absolute path**, `contracts.py:23` — worth fixing independently of this plan). None of them is load-bearing for Guardian's core chat tool surface.

This plan **keeps** that separation: harnesses stay in the coordination lane; native tools live in the command bus and need nothing external. The one thing to fix is the *appearance* of dependency — make the harness adapters degrade to "unavailable" rather than "broken" when their binaries are absent, and make sure no native tool's fallback path silently routes through a harness.

### 7.2 "Maintenance burden: manage these tools myself vs. use the external harnesses"

| Dimension | Native tools in Guardian | Delegating to Codex/Claude/Pi harnesses |
|---|---|---|
| **Per-tool upkeep** | You own the semantics. When OpenAI/Claude change a tool contract, you adapt — but *you* decide the contract, so there is no upstream to track. | The harness owns it. You inherit changes, including breaking ones. |
| **Surface to maintain** | ~14 genuinely new capabilities (§3). The other ~25 are already built. | ~0 new, but you inherit the harness's whole surface and its bugs. |
| **Protocol churn** | MCP tool contracts move; the `.Dev` reference is ~41 modules you read once. | Codex CLI's app-server JSON-RPC (`codex_app_server_executor.py`) is a moving private target. |
| **Sovereignty** | Complete; self-hostable; works with the cheapest effective models. | Each harness is a separate binary, license, version, and failure mode; and it constrains you to that harness's provider. |
| **Your token-economics thesis** | Native tools let Guardian route cheap subagents to cheap models and reserve frontier models for planning — exactly your stated model. Harness-mediated tools inherit the harness's model policy. | Direct conflict. |
| **One-time cost** | Build the native lane (Stage 1–3), then ~14 focused tool implementations. | Zero build cost. |
| **Recurring cost** | Test + harden each tool as you add it. | Track and absorb upstream breakage. |

**Honest read:** the *build* cost of native tools is real and front-loaded; the *maintenance* cost is lower than the harness route, and it is the only route compatible with the rest of your thesis. The hybrid that actually fits: native tools for the core loop (files, search, patch, git-read, context, memory), harnesses only where a harness genuinely outperforms (long-horizon autonomous coding), and MCP-client support for third-party tool servers later.

Your frontier-model thesis reinforces this: frontier models are for planning and the voice of the system. That argues for **fewer, better tools** the Main Agent reasons over — not for delegating tool execution to a harness that owns its own model selection.

---

## 8. Risks, and the open decisions that are yours

| # | Risk / Decision | Severity | Recommendation |
|---|---|---|---|
| 1 | **Free shell vs allowlisted verbs** (§5). `.Dev` is unrestricted; Guardian's `cli_sandbox` is a verb catalog. | **Blocking** — now an architecture decision, not a product preference | Two-tier: catalog by default, human-authorized shell lane with a real executor behind it. **Governed by ADR-111 (Proposed); the host-native target is an explicit exception to Accepted ADR-077 requiring human acceptance.** |
| 2 | **Naming collision.** Upstream is literally "Codexify", and `codexify.dev` is *your* product domain (`SECURITY.md:103`; `schemas/knowledge/*.schema.json` `$id`s). A third-party project and your product share a name. | **High** | Never expose upstream's name in Guardian's public surface. Namespace native tools `native::…`, attribute upstream as an MIT reference implementation in source, and never ship upstream's branding, domain, or `instanceName` defaults |
| 3 | Upstream drift. Your fork is 145 commits behind; upstream moves fast (`pushed_at` is recent). | Medium | Port the **contract**, not the code. Re-read upstream's `src/tool.rs` + `src/tools/*.rs` for behavior annotations at each port; pin the reference SHA in the ADR. **The inventory in §3 was read from the fork's `main` @ `d1a80c9f5`**; upstream `main` at the time of writing was `1c7fb1e9` — re-read the behavior annotations against upstream before porting |
| 4 | The provider gate (`chat_exposure.py:333-345`) restricts tools to deepseek/whooshd. | Medium | Stage 3.3 moves capability detection into `chat_with_ai` |
| 5 | `guardian/sandbox/run.py` is a 21-byte stub and `guardian/plugins/sandbox.py` is an unisolated `subprocess.run`. If free shell is ever enabled, this is the hole. | Medium | Do not enable a shell lane before a real isolation story exists |
| 6 | The 2026-08-08 plan remains open and overlaps this one. Two live plans for one subsystem invites drift. | Medium | Mark the 2026-08-08 plan superseded by this one, and link them bidirectionally |
| 7 | `codex_runner_bridge` hardcodes `CODEX_RUNNER_ROOT = Path("/Volumes/Dev_SSD/Codex-Runner")` (`contracts.py:23`). | Low (pre-existing) | Fix independently: env-var with a clear "unavailable" state |
| 8 | Tool-result prompt injection: file contents and command output are untrusted model input. | Medium | Keep the existing redaction policy; cap outputs; treat results as inert evidence with no instruction authority — the pattern `chat_exposure.py:268-273` already uses for history recall |

### Open questions for you

1. **§5 — the shell question.** Two-tier (recommended), or full `.Dev`-parity free shell as the default?
2. **Naming.** Keep upstream's tool names (`read_file`, `exec_command`) for cross-agent familiarity, or rename into Guardian's namespace (`fs.read`, `exec.run`)? Recommendation: keep upstream names — they are already the de-facto vocabulary every coding agent knows, and renaming buys nothing but confusion.
3. **Scope of Stage 4.10.** If the shell question resolves to two-tier, do you want the escalated shell lane in the first delivery, or catalog-only first with the shell lane as a follow-up?
4. **Model-provider exposure.** Should native tools be enabled for frontier providers immediately, or stay behind the deepseek/whooshd gate until the tool loop is proven under multiple providers?
5. **Attribution posture.** MIT requires retaining the upstream copyright notice in ported source. Do you want that in-file, or in a single `THIRD_PARTY_NOTICES` entry?

---

## 9. What I did *not* do

- **No tool was integrated.** No `guardian/` code was modified. This document is the only artifact.
- **No branch, commit, PR, or push.** The plan is uncommitted and local for your review.
- **No harness was removed, configured, or installed.** Codex, Claude Code, and Pi were read, not touched.
- **No external service was contacted** beyond read-only GitHub API calls for the upstream/fork inspection and the MIT license text.
