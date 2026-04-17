# Spec: Pi Integration as a Codexify Native Coding Agent

## Status

Draft

## Classification

Architecture-impacting integration spec

## Purpose

Define how Codexify integrates **Pi** as a native coding-agent substrate without collapsing Codexify’s runtime contracts, identity boundaries, or observability model into Pi’s internal implementation.

This spec treats Pi as an **adapter-backed execution engine** that can power a Codexify coding agent while preserving Codexify’s own control plane, event surfaces, and lineage model.

---

## 1. Goals

Codexify must be able to:

1. expose Pi as a **first-class coding agent option** inside Codexify
2. run Pi in a way that feels native to Codexify users
3. preserve Codexify-native:

   * task lifecycle
   * identity and permission boundaries
   * thread and artifact lineage
   * observability and replay semantics
4. support future extension toward:

   * multiple coding-agent backends
   * per-agent capability policies
   * richer coding session diagnostics

---

## 2. Non-Goals

This spec does **not** require:

* replacing Guardian chat completion with Pi
* making Pi the universal execution engine for all Codexify agents
* exposing Pi’s raw terminal UI directly as the primary Codexify UX
* importing Pi’s internal session model as Codexify truth
* allowing Pi to write directly into Codexify storage without an adapter boundary
* immediate support for every Pi feature, package, extension, or provider

---

## 3. Product Thesis

Pi is integrated as a **native-feeling coding agent**, but **not** as native truth.

Codexify remains the system of record for:

* task/request state
* thread/message ownership
* artifact lineage
* policy decisions
* user-visible observability
* project and identity context

Pi remains an execution substrate for coding work.

That distinction matters. Pi can power the shovel; Codexify still owns the map.

---

## 4. Integration Model

## 4.1 Primary model: adapter-backed subprocess / RPC integration

Codexify should integrate Pi through a **managed adapter boundary**, using one of:

* **RPC mode**
* **print/JSON mode**
* other stable machine-oriented interface Pi exposes

The first supported path should prefer **process-boundary execution** over deep in-process embedding.

### Why

This gives Codexify:

* fault isolation
* cancellation control
* bounded lifecycle ownership
* easier logging and transcript capture
* safer upgrade posture
* less coupling to Pi’s internal TypeScript APIs

---

## 4.2 Deferred model: in-process SDK embedding

Pi’s SDK embedding path may be supported later, but only behind the same Codexify adapter interface.

This is a future optimization path, not the default contract.

Codexify must never let “embedded” become “structurally fused.”

---

## 5. Canonical Runtime Position

Pi sits in Codexify as a **coding-agent execution provider**.

### Canonical flow

1. User invokes Coding Agent from Codexify
2. Codexify creates a native agent task / run record
3. Codexify resolves:

   * project context
   * repo/workspace root
   * permissions
   * model/provider policy
   * tool/file constraints
4. Codexify launches Pi through the Pi adapter
5. Pi performs coding work
6. Adapter translates Pi execution events into Codexify-native events
7. Codexify persists:

   * run metadata
   * summaries
   * output artifacts
   * lineage links
8. Codexify renders the result through native UI surfaces

Pi execution is real, but Codexify presentation and persistence remain canonical.

---

## 6. Required Architectural Invariants

The following must remain true:

### 6.1 Codexify owns user-visible truth

User-visible run state must come from Codexify runtime contracts, not raw Pi labels.

### 6.2 Message identity and task identity remain Codexify-native

Pi session IDs or run IDs must never replace Codexify thread/message/task identity.

### 6.3 Lineage must be preserved

Any generated file, patch, summary, artifact, or codex entry produced through Pi must be attributable to:

* originating thread
* source message or task
* project
* agent backend = `pi`
* execution run / attempt

This aligns with Codexify’s lineage posture. The artifact model already expects thread and source-message linkage.

### 6.4 Identity boundaries remain sovereign

Pi must not become a second identity system.
Persona, imprint, and memory rules remain governed by Codexify’s identity model, where personas borrow identity rather than owning it.

### 6.5 Observability must not depend on Pi internals alone

Codexify must be able to explain:

* accepted
* running
* output received
* persisted
* failed
* cancelled
  even if Pi-side event richness changes over time

### 6.6 Adapter boundary is mandatory

No direct coupling from product surfaces to Pi internals.

---

## 7. UX Model

## 7.1 User-facing presentation

Pi should appear in Codexify as:

* a selectable **Coding Agent backend**
* optionally a **provider/runtime target** for code tasks
* a native run surface within Command Center / agent observability surfaces

The user should experience:

* “Run with Pi”
* “Pi session active”
* “Pi produced patch / files / summary”
* “Open run details”
* “Save result to Codex”

The user should **not** need to understand Pi’s raw CLI contract.

---

## 7.2 Native surfaces

Codexify should provide:

### A. Task launch surface

Where the user starts a coding run from chat, workspace, or command center.

### B. Run status surface

Shows Codexify-native lifecycle state, not just raw terminal output.

### C. Event/log surface

Shows translated execution narrative:

* launched
* scanning repo
* editing files
* running validation
* finished / failed / cancelled

### D. Artifact surface

Displays:

* changed files
* patch summary
* generated docs
* linked outputs
* “save to codex” or “attach to thread”

---

## 8. Execution Modes

## 8.1 Supported V1 mode

**Managed non-interactive or semi-interactive task execution**

Examples:

* apply a focused code change
* write a test
* generate a changelog entry
* inspect or refactor a bounded subsystem
* produce a patch summary

## 8.2 Deferred modes

* full terminal mirroring
* live keyboard passthrough TUI
* shared long-lived Pi interactive shell as the main Codexify UX
* unrestricted multi-package Pi extension management from inside Codexify

---

## 9. Adapter Contract

Codexify must define its own stable adapter interface for coding agents.

Example conceptual contract:

```ts
type CodingAgentBackend = "pi" | "codex" | "claude_code" | "future";

interface CodingAgentRunRequest {
  backend: CodingAgentBackend;
  projectId: string;
  threadId?: string;
  sourceMessageId?: string;
  workspaceRoot: string;
  userIntent: string;
  permissions: {
    filesystem: "scoped" | "full";
    network: boolean;
    git: boolean;
    shell: boolean;
  };
  policy: {
    modelPolicy?: string;
    timeoutSeconds?: number;
    maxSteps?: number;
  };
}

interface CodingAgentRunEvent {
  runId: string;
  phase:
    | "accepted"
    | "launching"
    | "running"
    | "editing"
    | "validating"
    | "completed"
    | "failed"
    | "cancelled";
  detail?: string;
  raw?: unknown;
  createdAt: string;
}

interface CodingAgentRunResult {
  runId: string;
  status: "completed" | "failed" | "cancelled";
  summary: string;
  changedFiles: string[];
  artifacts: Array<{
    type: "patch" | "doc" | "note" | "log" | "report";
    path?: string;
    contentRef?: string;
  }>;
}
```

Pi-specific details must terminate at the adapter.

---

## 10. Session and State Ownership

## 10.1 Codexify-owned state

Codexify must persist:

* run ID
* backend type (`pi`)
* thread/source lineage
* project binding
* policy snapshot
* translated events
* final summary
* artifact references
* timestamps
* cancellation/failure outcome

## 10.2 Pi-owned state

Pi may maintain its own internal session file/tree/history for execution continuity, but that state is **implementation-private** unless explicitly imported through the adapter.

Pi history is not automatically Codexify conversation history.

---

## 11. Artifact and Lineage Rules

Any output created by Pi that becomes visible or durable inside Codexify must support lineage metadata at minimum:

* `thread_id`
* `source_message_id` or initiating task ID
* `project_id`
* `agent_backend = "pi"`
* `agent_run_id`
* timestamp
* artifact type

This aligns with Codexify’s thread-artifact lineage goal, where artifacts must be able to jump back to the originating thread/message.

If an artifact cannot preserve lineage, Codexify must either:

* refuse durable save, or
* mark the save as degraded and explicit

Silent orphaning is not allowed.

---

## 12. Permissions and Security

## 12.1 Codexify remains the policy authority

Permissions must be decided by Codexify before Pi launches.

Pi must receive an already-resolved permission envelope, not invent one.

## 12.2 Minimum V1 controls

Codexify should be able to constrain:

* workspace root
* allowed write scope
* shell access
* git access
* network access
* environment variable exposure
* model/provider selection if relevant

## 12.3 Sensitive identity and memory controls

Pi must not directly read or mutate Codexify identity/memory stores unless that access is explicitly mediated by Codexify policy. This follows Codexify’s identity-separation rule: chat history is not automatically durable identity, and deep identity remains opt-in.

---

## 13. Observability Contract

Codexify must translate Pi execution into native runtime truth surfaces.

At minimum, the user/operator should be able to answer:

* Was the run accepted?
* Did Pi actually launch?
* Is work still in progress?
* Were files changed?
* Did validation run?
* Was output persisted?
* Did the run fail before or after edits?
* Was cancellation user-driven or system-driven?

This follows Codexify’s broader architecture rule that queue acceptance, execution state, and visibility state are distinct truth surfaces and must not be collapsed.

---

## 14. Failure Model

Codexify must distinguish:

### A. Launch failure

Pi process/RPC failed to start.

### B. Execution failure

Pi started, but task execution failed.

### C. Visibility degradation

Pi may have run, but Codexify lost some intermediate event visibility.

### D. Persistence failure

Pi completed, but Codexify failed to persist outputs or lineage.

### E. Policy rejection

Run rejected before Pi launch due to permissions or unsupported scope.

These states must not be conflated.

---

## 15. Storage Model

Codexify should persist Pi run state in a backend-owned table or equivalent durable model, for example:

* `agent_runs`
* `agent_run_events`
* `agent_run_artifacts`

Each run should include:

* backend name
* backend version if available
* execution mode
* workspace root
* initiating thread/message
* policy snapshot
* timestamps
* final status

This keeps Pi integration consistent with Codexify’s existing posture around durable events, command runs, and operational entities. The architecture already treats durable execution records as first-class control-plane data.

---

## 16. API / Control Plane Surface

Potential Codexify-native control plane:

* `POST /api/agents/runs`
* `GET /api/agents/runs/{run_id}`
* `GET /api/agents/runs/{run_id}/events`
* `POST /api/agents/runs/{run_id}/cancel`
* `GET /api/agents/runs/{run_id}/artifacts`

These routes expose Codexify truth, not raw Pi protocol.

---

## 17. UI Integration Points

### V1 recommended surfaces

* Guardian chat action: “Run with Pi”
* Command Center run monitor
* Workspace / Codex artifact save path
* Thread-linked generated patch summary
* Agent-specific run detail panel

### Not required in V1

* embedded Pi terminal as the default interaction surface
* full parity with Pi TUI navigation
* package manager UI for Pi extensions

---

## 18. Backend Selection Doctrine

Codexify should treat Pi as one backend in a multi-backend coding-agent architecture.

Recommended canonical backend token set:

* `codex`
* `claude_code`
* `pi`

This avoids re-hardcoding backend literals across routes, UI, and storage. That follows Codexify’s canonical-token doctrine: repeated contract-bearing literals must graduate into canonical tokens instead of spreading inline.

---

## 19. ADR Impact

### Classification

Requires new ADR

### Governing ADR / contract areas

* runtime/provider/request truth separation
* canonical token doctrine
* artifact lineage
* identity boundary rules
* control-plane observability

### Reason

This integration changes:

* execution-provider semantics
* observability truth surfaces
* agent-run persistence
* artifact lineage requirements
* policy boundary placement

This is dangerous to forget in three months, so it belongs in the architecture lane.

---

## 20. Current Truth Anchors

### True now

* Codexify’s supported path is still local Docker Compose, local-first, with backend-owned runtime truth surfaces.
* Codexify already distinguishes runtime truth surfaces rather than collapsing them into a single binary status story.
* Codexify already has lineage expectations for artifacts tied to threads/messages.

### Not yet true

* No proven Pi adapter is part of Codexify’s supported path yet.
* No live proof currently establishes Pi-backed agent runs in the supported stack.
* No ADR currently anchors Pi as a coding-agent backend.

### Safe assumption for this spec

* Pi may be adopted as a bounded execution substrate
* but only if Codexify remains the control plane and source of truth

---

## 21. Proof Surface Required

Before this is considered supported, Codexify should prove:

1. **Launch proof**

   * Codexify can start a Pi-backed run successfully

2. **Execution proof**

   * Pi can perform a bounded code task in a real repo workspace

3. **Event translation proof**

   * Codexify surfaces accepted/running/completed/failed truthfully

4. **Artifact lineage proof**

   * Outputs can be saved with thread/message/project/run linkage

5. **Cancellation proof**

   * Codexify can cancel an in-flight Pi run cleanly

6. **Failure classification proof**

   * launch failure vs execution failure vs persistence failure are distinct

7. **Policy proof**

   * workspace and permission constraints are enforced by Codexify

---

## 22. Recommended V1 Rollout

### Phase 1

* Pi adapter behind feature flag
* subprocess / RPC execution only
* bounded coding-task support
* translated event stream
* patch summary + artifact save

### Phase 2

* richer run diagnostics
* structured file diff ingestion
* stronger cancellation/replay semantics
* configurable model/provider policy mapping

### Phase 3

* optional SDK embedding
* deeper package/extension interoperability
* advanced interactive session bridging if still justified

---

## 23. Decision

Codexify should integrate Pi as a **native-feeling coding agent backend through an adapter boundary**, with **process-boundary/RPC execution as the first supported path**.

Pi may power execution.
Codexify must retain:

* policy authority
* runtime truth
* lineage ownership
* observability contract
* identity boundaries

That is the whole hinge.
