# Guardian Native Execution Seam Audit

Date: 2026-08-31

Execution lane: `architecture-impact`

Task kind: `proof`

Evidence posture: code-path only

ADR impact: No ADR impact

## A. Revision identity

- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `main`
- Local `HEAD`: `9fb86d33ea0771d1ec51ebd46cf0ca253e49d243`
- Configured upstream: `origin/main`
- `origin/main`: `3b0c6e8f939a48f2ed96d7baa9dc2f1d25469d92`
- `origin/main` was freshly fetched with `git fetch origin main --prune` during this audit.
- Merge base: `3b0c6e8f939a48f2ed96d7baa9dc2f1d25469d92`
- `git rev-list --left-right --count origin/main...HEAD`: `0 1` (local is one commit ahead and zero behind).
- Local-only commit: `9fb86d33e docs: refresh weekly current-state override`.
- Initial working tree: clean.

The only files different between `origin/main` and the audited local `HEAD` are:

| File | Classification | Effect on this seam |
| --- | --- | --- |
| `docs/architecture/00-current-state.md` | Local-only documentation refresh | Unrelated to implementation reachability. It clarifies that Pi remains internal/qualification-pending and that CE-L1 live execution/result readback remain unproven. |
| `docs/architecture/README.md` | Local-only documentation refresh | Unrelated to implementation reachability. No runtime, permission, worker, route, adapter, or UI behavior changed. |

Therefore all execution-seam implementation files inspected here are identical to the freshly fetched `origin/main` reference. Local and `origin/main` implementation status are the same; only the local current-truth wording is newer.

## B. Executive finding

**Guardian Native Execution is partially present.**

Guardian already owns a substantial end-to-end coding execution seam: an explicit Composer `Coding Loop` selection persists the user message, constructs a Guardian coding-task envelope with source lineage and permission policy, calls `POST /api/agents/coding/execute`, queues a `CodingExecutionTask`, executes it in `worker-coding` through the Pi adapter, persists a structured result, and can inject an assistant result into the source thread. Campaign Engine also has a separate Guardian-authorized Pi invocation path with identity attestation, bounded permission receipts, and tool telemetry.

It is not yet the target native conversational capability. An ordinary chat submission follows `POST /chat/{thread_id}/complete` into `ChatCompletionTask` and the chat worker. It does not route to the coding execution endpoint, `invoke_guardian_authorized_pi`, `PiCodexRunnerAdapter`, Campaign Engine live execution, or `worker-coding`. The user must explicitly select a visible `Coding Loop` mode. No ordinary-turn intent/authorization bridge converts a conversational read/process request into the existing coding envelope.

The present permission vocabulary is also more granular than Pi activation enforcement. `allow_shell`, `allow_network`, and `allow_write` are explicit coding-envelope fields, but the authorized Pi wrapper receives only `read_only`. `files.write`/write-root presence determines that boolean in the Pi invocation rail, and `PI_DISABLE_TOOLS` then selects either no tools or the entire `read`, `bash`, `edit`, `write` set. Thus shell and network intent cannot independently determine Pi tool/runtime authority on this path.

## C. Execution-seam matrix

| Seam | Local status | `origin/main` status | Evidence class | Primary code path | Finding |
| --- | --- | --- | --- | --- | --- |
| Guardian Chat trigger/routing | Partial | Same | proven-code-path | `GuardianChat.tsx` -> chat complete or explicit Coding Loop branch | Ordinary chat and Coding Loop are separate branches; only explicit Coding Loop dispatches execution. |
| Abstract execution contract/broker | Present for coding tasks | Same | documented-contract + proven-code-path | `CodingAgentTaskEnvelope` -> agent orchestration route -> coding queue | This existing Guardian coding contract fulfills most proposed broker responsibilities; no new broker is warranted. |
| Capability/permission vocabulary | Partial | Same | proven-code-path | `CodingAgentPermissionPolicy`; `PiPermissionGrant` | Coding policy names shell/network/write/path/time, while Pi grants commonly use `files.read`, `files.write`, and `network.provider.allowed`; no unified independently enforced vocabulary covers every requested capability. |
| Guardian authorization | Present but lane-specific | Same | proven-code-path | agent orchestration intake; `invoke_guardian_authorized_pi` | Both lanes are Guardian-owned, but ordinary chat does not request or resolve coding authority. |
| Pi/runtime adapter | Present | Same | proven-code-path | `PiCodexRunnerAdapter.execute_authorized()` | Runs a Node wrapper subprocess with invocation-local identity and bounded result parsing. |
| `read` tool activation | Partial | Same | proven-code-path | `agent-wrapper.js` | Read-only authorized Pi sets `PI_DISABLE_TOOLS=1`, producing no tools; read cannot be activated alone. |
| `bash` tool activation | Bundled | Same | proven-code-path | `CONFIGURED_WRITABLE_TOOL_NAMES` | Bash is enabled only as part of the full writable set; no explicit allowed-tool list is passed. |
| `edit`/`write` activation | Bundled | Same | proven-code-path | `CONFIGURED_WRITABLE_TOOL_NAMES` | Both activate with read/bash when tools are enabled; post-execution mutation guards constrain outcomes but do not make activation granular. |
| Coding-worker boundary | Present | Same | proven-code-path + documented-contract | `worker-coding` -> `CodingWorker` -> registered Pi adapter | Dedicated image/queue consumer exists and carries cwd, lineage, permission policy, and result persistence. |
| Sandbox enforcement | Absent on audited Pi path | Same | proven-code-path | adapter `subprocess.run()` | Bubblewrap is installed in the base runtime image, but no `bwrap` invocation wraps this execution path. |
| Network boundary | Partial/incomplete | Same | proven-code-path | Compose env + coding permission policy | `allow_network` is recorded, but no container network isolation or Pi wrapper enforcement was found; provider access necessarily uses network for cloud lanes. |
| Provenance / receipt | Present, split by lane | Same | proven-code-path | Pi receipt/harness result; coding run/result store | Pi records identity/grants/tool telemetry; coding records run/source lineage and result delivery. Ordinary chat does not bind these records because it never enters the lane. |
| Source-thread result return | Present for explicit Coding Loop | Same | proven-code-path | `AgentStore.store_coding_result()` | Terminal success-like coding results can be injected as assistant messages with source thread/message lineage. No live proof was run here. |
| Native continuous Guardian UX | Absent | Same | proven-code-path | Composer mode toggle | Visible `Coding Loop` mode is required; ordinary conversation does not transparently obtain governed execution authority. |

## D. Actual call graph

### Ordinary Guardian Chat

```text
Composer send (executionMode != "coding")
  -> GuardianChat persists user message
  -> POST /chat/{thread_id}/complete
  -> guardian.routes.chat constructs ChatCompletionTask
  -> enqueue_chat_completion
  -> chat queue
  -> guardian.workers.chat_worker
  -> context/retrieval + provider routing
  -> optional single bounded Command Bus tool turn
  -> assistant-message persistence + terminal task event
  -> GuardianChat event/readback refresh
```

The bounded Command Bus turn executes allowlisted backend HTTP commands. It is not a general project shell/process seam and does not call Pi.

### Guardian Composer Coding Loop

```text
Composer send (explicit executionMode == "coding")
  -> GuardianChat persists user message and obtains source_message_id
  -> POST /api/agents/coding/execute with CodingAgentTaskEnvelope
  -> Guardian persists AgentDeployment + queued AgentRun
  -> enqueue_coding_execution(CodingExecutionTask)
  -> worker-coding / CodingWorker
  -> registered pi_codex_runner adapter
  -> Node agent-wrapper subprocess
  -> structured coding result
  -> AgentStore.store_coding_result
  -> durable run/result + source-thread assistant-message injection
  -> GuardianChat coding-run event/readback cards
```

### Campaign Engine / Guardian-authorized Pi

```text
prepare/run live Executor campaign
  -> PiInvocationEnvelope + PiInvocationPolicyDecision
  -> invoke_guardian_authorized_pi
  -> PiCodexRunnerAdapter.execute_authorized
  -> node agent-wrapper.js guardian-authorized-task
  -> Pi session/provider/tools
  -> PiInvocationReceipt + PiHarnessResult + Campaign artifacts
```

The ordinary chat path does not join either execution path. The explicit Coding Loop joins the coding worker and Pi adapter, but it does so through a user-visible mode branch rather than conversational intent. Campaign Engine is a separate caller and is not the chat bridge.

**Missing join:** after an ordinary user message is durable and before normal completion dispatch, Guardian lacks a governed decision that recognizes a project read/process request, obtains explicit authority, constructs the existing `CodingAgentTaskEnvelope`, and awaits/associates its structured result with that same conversational turn.

## E. Capability analysis

| Capability question | Current answer | Classification |
| --- | --- | --- |
| Read files without process execution | Not through active Pi tools: read-only means `tools=[]`. Other backend retrieval/read commands exist, but they are not a general project-files execution grant. | Absent for Pi tool activation |
| Process execution without write authority | Not expressible through authorized Pi activation. Without write roots the invocation is `read_only` and all tools are disabled; with tools enabled bash and write arrive together. | Absent |
| Process execution without network | `allow_network=false` can be stated in the coding envelope, but no enforcement was found in the adapter, wrapper, subprocess, or Compose network namespace. | Explicit but incomplete |
| Scoped file writes | `allowed_paths`, Pi `files.write` resources, pre/post snapshots, Git-head checks, and worker mutation guards constrain mutations. | Explicit and enforced at postcondition/scope checks; tool activation remains coarse |
| Secret denial | Pi rejects credential-shaped envelope/decision keys and receipts omit prompt/tool content. The worker still inherits `env_file` and selected credential variables, so runtime non-access is not independently sandboxed. | Explicit but incomplete |
| Background-process denial | No dedicated capability token or process-tree containment was found. Timeout bounds the parent subprocess but is not a complete background-process denial. | Absent |
| Host inspection | No canonical independent grant was found; visibility follows cwd, mounts, process environment, and container filesystem. | Implicitly bundled |

Two authority domains coexist:

1. `CodingAgentPermissionPolicy`: `allow_shell`, `allow_network`, `allow_write`, `allowed_paths`, `max_runtime_seconds`.
2. Pi invocation grants seen in contracts/tests: `files.read`, `files.write`, and `network.provider.allowed`.

The Pi invocation rail derives writable posture solely from granted `files.write` roots. `files.read` does not activate `read`; process/shell authority has no independent Pi grant; and Guardian grants do not directly select individual Pi tools.

## F. Sandbox analysis

Enforced on the audited code path:

- Guardian policy-decision/envelope equality and allowed decision checks.
- Explicit provider/model/harness identity matching.
- Credential-shaped metadata rejection.
- Cwd existence and resolved write-root validation.
- Pre/post filesystem snapshots, write-root containment, symlink/traversal defenses, and Git `HEAD` posture checks in the one-shot invocation rail.
- Coding-worker mutation checks against `allowed_paths`, with fail-closed result classification when scope cannot be verified or is violated.
- Subprocess timeout.

Available but not enforced on the audited path:

- `bubblewrap` is installed by `backend/Dockerfile` and therefore inherited by `worker-coding-runtime`, but no audited adapter, worker, wrapper, or launch command invokes `bwrap`/`bubblewrap`.

Not established:

- A per-invocation mount namespace, syscall filter, process namespace, network namespace, egress firewall, environment allowlist, secret-free process environment, or background-child cleanup contract.
- The backend base runtime can execute the wrapper source, but only `worker-coding-runtime` installs the pinned Pi SDK/Node 22 closure. Ordinary chat workers do not route into that runtime.

The Compose coding worker sees mounted repository components and `.git`, read-only config, the Pi auth volume, shared service credentials/configuration from the runtime env file, and normal Compose networking. Its `cwd` comes from the task `repo_root`; the explicit Composer path currently sends `repo_root: null`, so a usable project workspace is not established by that UI dispatch itself.

## G. Provenance analysis

For a successful Guardian-authorized Pi invocation, Guardian can truthfully establish from structured evidence:

- authored/source thread and message identifiers carried in the envelope;
- invocation, attempt, receipt, harness-result, and artifact identifiers;
- requested and actual provider/model/harness identity;
- requested and granted permissions;
- active tool names and whether `write` was available;
- tool execution start/end counts, unique executed tool names, and assistant tool-call count;
- target mutation posture and receipt/result validation status;
- zero retry/fallback counts for the one-shot invocation rail.

For explicit Coding Loop execution, Guardian can additionally associate deployment/run/coding-task identity, source thread/message, user/project, adapter kind, bounded result summary, files changed, validation evidence, and result-delivery status. The durable store can inject the result into the source thread.

Guardian cannot make the same disclosure for an ordinary chat turn today because ordinary chat never creates the Pi/coding execution records. The Pi one-shot rail itself is non-persisting; durable association depends on its caller (Campaign Engine artifacts or the coding run/store). Tool telemetry is content-free and does not prove what command arguments or result content were used.

## H. Exact missing delta

The smallest missing delta is a **Guardian-owned ordinary-turn read/exec authorization and routing bridge that adapts into the existing coding execution contract**.

It must:

1. recognize a bounded project inspection/read/process intent from an ordinary Guardian turn without exposing worker/provider selection as conversation mode;
2. resolve the project/repository root and source message identity;
3. request and record explicit read/process authority, defaulting write, network, secrets, and background processes to denied;
4. translate the approved request into the existing `CodingAgentTaskEnvelope`/coding queue rather than introducing a parallel broker;
5. reconcile policy with actual Pi activation so shell/process and network denial are enforced rather than merely recorded;
6. return the structured coding result through the existing source-thread delivery contract and normal Guardian turn lifecycle.

The architecture already accepts Guardian-mediated coding execution under ADR-020. A new ADR is not required merely to connect ordinary turn intake to that accepted contract. Architecture review is still required before implementation because the present Pi binary tool posture cannot enforce the desired independent read/process/write/network authority. If the implementation changes that authority contract or canonical permission vocabulary, it requires an explicit contract/ADR decision rather than an inline token invention.

## I. Recommended next Task Spec boundary

Recommend exactly one slice:

**Guardian Native Execution — Phase 1: Read/Exec Bridge**

Bound it to one ordinary project-thread intent that can request read-only filesystem inspection plus foreground process execution, routes through the existing `CodingAgentTaskEnvelope` and `worker-coding` result-return seam, and proves source-message-to-assistant-result lineage. Before live execution, the slice must define and enforce an allowed-tool/runtime posture that enables only the approved read/process surface while keeping write, network, secrets, and background processes denied. It must not create a new execution broker, expose harness selection, or broaden release claims.

## J. Evidence limitations

### Live-runtime proven

- None by this audit. No provider-backed inference, live worker dispatch, browser flow, or supported-Compose execution was run.

### Test-proven in this checkout

- `codex_runner/tests/test_campaign_engine_live_executor.py`: 33 tests passed under `python3`.
- The two other requested suites were attempted but unavailable because host Python lacks `fastapi`; their source assertions were inspected but are not counted as passed.

### Proven code path

- Ordinary chat request/queue/worker/provider/result flow.
- Explicit Coding Loop route/queue/coding-worker/adapter/result-delivery flow.
- Guardian-authorized Pi identity, permission validation, tool activation, telemetry, and receipt construction.
- Dedicated coding-worker image and Compose mounts/environment.
- Absence of an ordinary-chat call to Pi/Campaign Engine/coding worker.
- Absence of Bubblewrap invocation on the audited path.

### Documented contract

- ADR-020 Guardian-mediated coding-agent execution.
- ADR-068 Campaign Engine live role execution.
- Pi Invocation Boundary Contract.
- Chat Runtime Contract, Completion Pipeline, Critical Flows, and Campaign Engine Contract.

### Working theory

- The recommended bridge is the smallest implementation slice. Exact turn-intake classification and user authorization UX require the next architecture review and Task Spec.
- Container/runtime behavior beyond inspected configuration remains unproven until a supported-path run observes the actual worker filesystem, environment controls, network posture, execution, persistence, and UI readback.

## Validation record

| Command | Result |
| --- | --- |
| `git fetch origin main --prune` | Passed; refreshed `origin/main` to `3b0c6e8f...`. |
| Required revision and diff commands | Passed; clean initial tree, `main`, ahead 1/behind 0, only two docs differ. |
| Required static seam inventory | Passed as discovery; findings are summarized above. |
| `python -m pytest -q tests/pi/test_pi_live_invocation.py` | Unavailable: `python` command not installed. |
| `python -m pytest -q tests/ops/test_worker_coding_pi_runtime_contract.py` | Unavailable: `python` command not installed. |
| `python -m pytest -q codex_runner/tests/test_campaign_engine_live_executor.py` | Unavailable: `python` command not installed. |
| `python3 -m pytest -q tests/pi/test_pi_live_invocation.py` | Unavailable: 32 setup errors, all caused by `ModuleNotFoundError: No module named 'fastapi'`. |
| `python3 -m pytest -q tests/ops/test_worker_coding_pi_runtime_contract.py` | Unavailable: 15 setup errors, all caused by the same missing `fastapi` dependency. |
| `python3 -m pytest -q codex_runner/tests/test_campaign_engine_live_executor.py` | Passed: 33 tests. |

Documentation validation, diff checks, and final staged-scope checks are recorded in the commit closeout.

## Documentation follow-through

- Created only this audit artifact.
- `docs/architecture/00-current-state.md`, existing ADRs, runtime contracts, operator docs, source, tests, schemas, and configuration remain unchanged by this task.
- No current-state discrepancy requires correction: its internal/qualification-pending Pi and missing CE-L1 live-result language is consistent with this audit.

## Governing sources

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md`
- `docs/architecture/adr/068-campaign-engine-live-role-execution-contract.md`
- `docs/architecture/pi-invocation-boundary-contract.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/completion_pipeline.md`
- `docs/architecture/flows.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/campaign-engine-contract.md`

## Axis KB recommendation

Record that current `main` already has a Guardian-owned explicit Coding Loop from Composer through `CodingAgentTaskEnvelope`, coding queue, `worker-coding`, Pi adapter, durable run/result, and source-thread result injection. Ordinary Guardian Chat remains separate. The minimal native-execution delta is an ordinary-turn authorization/routing adapter into this seam, not a new broker. Also record the safety gap: Pi activation is binary (`tools=[]` or `read,bash,edit,write`) and Bubblewrap/network/background-process denial are not enforced on this path.
