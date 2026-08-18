# Workspace Baseline Convergence Campaign Sweep

**Status:** G0 truth freeze completed — `CAMPAIGN_SWEEP_FROZEN`
**Campaign class:** Architecture-impact
**Primary program:** `codexify:program:digital-cognitive-workspace`
**Supporting program:** `codexify:program:node-runtime`
**Release effect:** None until separately proven and recorded
**Comparative inputs:** DeepSeek Harness mechanical reconnaissance; Hermes administrative inspection
**Execution rule:** One dependency-ordered atomic Task Spec at a time

> **Campaign thesis:** Converge Codexify’s supported workspace into a durable, authority-safe, recoverable agent runtime with an administratively legible provider and integration control plane—then stop.

## 1. Campaign Decision

Proceed with **one bounded convergence Campaign**, composed of two mutually supporting tracks:

| Track                                    | Source emphasis         | Purpose                                                                                                      |
| ---------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Execution Foundation**                 | DeepSeek reconnaissance | Make execution durable, recoverable, scoped, attributable, and composable.                                   |
| **Operator & Integration Control Plane** | Hermes inspection       | Make providers, accounts, credentials, integrations, health, and onboarding understandable and configurable. |

The tracks must not run independently.

```text
Execution Foundation creates governed capabilities
                         ↓
Operator Control Plane exposes canonical configuration
                         ↓
Onboarding guides the operator through that same configuration
                         ↓
Revalidation determines whether the baseline is complete
```

DeepSeek’s transferable pattern is:

```text
durable event log
→ scoped capabilities
→ guarded execution
→ replaceable providers
→ derived projections
```

Its recommended dependency order places durable execution history first, followed by capability contracts, approvals, one proven persistent execution path, delegation, and only then compaction, skills, telemetry, workflows, or dynamic extensions. 

Hermes does not materially overturn that sequence. It adds the missing administrative expression:

```text
provider families
→ connection instances
→ credentials and scopes
→ integration registry
→ health and activity
→ settings
→ onboarding
```

### Freeze posture

G0 reconciled this sweep at `eb6bdc530245fdffeff23589c98389be4102b564`
(`origin/main`). The canonical findings, per-capability evidence labels,
admission decisions, deferred register, dependency order, and singular next
Task Spec candidate are now in [the capability ledger](./capability-ledger.md)
and [deferred-capabilities register](./deferred-capabilities.md).

The reconciliation removed the false premise that Codexify lacks durable
execution records. It has domain-owned chat, Command Bus, delegation/agent,
and Campaign Engine records; it does not have one universal execution ledger.
Existing seams must be correlated and extended before any new durable primitive
is considered. Current-tip supported runtime closure, complete model-context
provenance, frozen authority snapshots, persistent process ownership, and
provider-account instances remain genuine gaps or proof gates.

---

# 2. Bounded Objective

The Campaign succeeds when Codexify has a proven, Codexify-native baseline for:

1. supported local runtime execution;
2. durable execution lifecycle and result closure;
3. model-visible context provenance;
4. capability and permission snapshots;
5. guarded tool/process execution;
6. persistent jobs, outputs, cancellation, and recovery;
7. idempotent source-thread result return;
8. bounded delegation;
9. provider connection instances;
10. a general integration registry and populated Connector Bay;
11. guided onboarding over canonical configuration;
12. operator-visible health and failure truth.

This Campaign is **not** approval to:

* clone DeepSeek Harness;
* clone Hermes;
* implement every Hermes connector;
* create a general autonomous agent loop;
* rewrite all chat persistence as event sourcing;
* broaden cloud-provider release support;
* reopen Browser Host, Hosted Room, ThreadSpace, Atlas, federation, or Home Presence work;
* turn every mature-UX preference into runtime architecture.

---

# 3. Current-Truth Entry Boundary

The attached current-state document identifies the supported posture as local Docker Compose with local-only inference. Chat, upload-to-readback, and workspace retrieval are supported paths; Coding Loop route registration and guards exist, but successful adapter execution and durable terminal results are not established there. It also identifies current-tip live proof, queue behavior, configuration drift, and Coding Loop terminal/readback proof as active blockers. 

Accordingly, this Campaign starts with three evidence rules:

1. **Repository presence is not support.**
2. **Route acceptance is not terminal completion.**
3. **A document, schema, test, or proof receipt establishes only its declared evidence level.**

The existing Command Bus already persists runs and ordered events, enforces policy and idempotency, and owns the bounded internal command lane. The one-turn chat tool path already uses it and hard-stops after one command. The Campaign must extend or compose that authority rather than create a competing tool universe. 

---

# 4. Reconciled Capability Baseline

WBC-0 reconciled the hypotheses below at `eb6bdc5`. The canonical current-main
classification, evidence posture, owner, disposition, prerequisites, and proof
requirements are in [the capability ledger](./capability-ledger.md). The
historical table remains only to preserve the original Campaign input; it must
not be used as current truth.

| Capability                                      | Baseline class                     |                         Provisional posture | Campaign disposition                     |
| ----------------------------------------------- | ---------------------------------- | ------------------------------------------: | ---------------------------------------- |
| Supported Compose completion path               | Expected                           |                     Unproven at current tip | **Admit**                                |
| Queue → worker → terminal → persistence closure | Expected                           |                          Partial / unproven | **Admit**                                |
| Canonical execution event spine                 | Expected                           |                                     Partial | **Admit after reconciliation**           |
| Explicit turn/request/step/tool lifecycle       | Expected                           |                                     Partial | **Admit**                                |
| Model-visible context provenance                | Expected                           |                               Gap / partial | **Admit**                                |
| Typed capability contracts                      | Expected                           |                                     Partial | **Admit**                                |
| Frozen run capability snapshot                  | Expected                           |                          Partial / unproven | **Admit**                                |
| Guarded command/tool execution                  | Expected                           |                      Existing bounded slice | **Preserve and prove**                   |
| Durable approvals and permission presets        | Expected                           |                                     Partial | **Admit**                                |
| Persistent terminal/process session             | Expected                           |                              Unproven / gap | **Admit if reconciliation confirms**     |
| Unified Job/Run/output contract                 | Expected                           |                                     Partial | **Admit**                                |
| Spill or durable large-output references        | Expected                           |                           Gap / distributed | **Admit only as golden-path dependency** |
| Idempotent source-thread result return          | Expected                           |                    Partial / path-dependent | **Admit**                                |
| Restart recovery and replay invariants          | Expected                           |                                     Partial | **Admit**                                |
| Bounded subagent/delegation seam                | Expected workspace capability      |                          Partial / unproven | **Admit after golden path**              |
| Context compaction with provenance              | Expected workspace capability      |                                     Partial | **Conditional admit**                    |
| Session queries and projections                 | Mature baseline                    |                                     Partial | **Conditional admit**                    |
| Trusted skill catalog and progressive loading   | Mature baseline                    |                                     Partial | **Conditional admit**                    |
| Provider connection instances                   | Expected administrative capability |                                     Partial | **Admit**                                |
| General Integration Registry                    | Expected administrative capability |                        Partial / unresolved | **Admit**                                |
| Connector Bay inventory and health              | Expected administrative capability | UI shell exists; runtime population unclear | **Admit**                                |
| Guided first-run onboarding                     | Mature UX                          |                               Gap / partial | **Admit after canonical APIs**           |
| Attachments and uploads                         | Expected                           |                          Existing / partial | **Preserve; no expansion by default**    |
| Governed web access                             | Mature baseline                    |                                     Partial | **Park unless it blocks admitted work**  |
| Dynamic self-extension                          | Advanced                           |                       Partial control plane | **Park**                                 |
| General workflow/autonomy engine                | Advanced                           |                             Draft / partial | **Park**                                 |
| LSP/navigation provider                         | Advanced                           |                     No canonical seam found | **Park**                                 |
| Identity, provenance, portability               | Differentiator                     |             Existing doctrine and substrate | **Preserve as invariants**               |

The plugin system is a good example of why classification matters: proposal persistence, install decisions, capability registry entries, scoped bindings, effective resolution, and bounded command dispatch already exist, while sandbox runtime, autonomous dispatch, and general activation do not. That makes it an **advanced partial capability**, not an urgent missing runtime baseline. 

---

# 5. Campaign-Wide Invariants

These rules apply to every phase and every atomic Task Spec.

## Authority and persistence

1. **PostgreSQL remains canonical durable authority** for Codexify-owned runtime state.
2. **Redis remains coordination and transport**, not canonical execution truth.
3. **Guardian owns authorization, lineage, result validation, and result publication.**
4. **Command Bus remains the internal command authority lane.**
5. Providers, connectors, sandboxes, terminals, and external harnesses remain subordinate execution boundaries.

## Identity and provenance

6. Authored message, request attempt, execution step, tool call, job, provider invocation, and result identities must remain distinguishable.
7. Provider accounts and connector accounts are not Codexify user identity.
8. Personas may use capabilities but do not own identity or permission state.
9. No durable trait inference or memory mutation is introduced by this Campaign.
10. Every delegated or externally produced result must preserve source-thread and source-message lineage.

## Runtime truth

11. Acceptance must never be represented as completion.
12. Event publication must never be represented as UI receipt.
13. Execution success must never be represented as user-visible success until durable result return succeeds.
14. Model-visible context must be attributable to persisted or reconstructable context evidence.
15. Retryable side effects require idempotency.
16. Unknown permission, scope, credential, or lineage state fails closed.

## Administrative truth

17. Settings and onboarding must project and mutate canonical backend configuration; neither may create a parallel configuration store.
18. Secret values must not be returned to the frontend after storage.
19. Connector and provider health must distinguish:

    * configured;
    * credential present;
    * authorized;
    * reachable;
    * capability-qualified;
    * actively selected;
    * release-supported.
20. UI presence, catalog presence, and health presence remain separate claims.

## Scope discipline

21. Existing seams must be extended or normalized before parallel abstractions are created.
22. Each phase may remove proposed tasks when current-main evidence proves the capability already exists.
23. No new comparative remapping occurs before Campaign revalidation unless a discovery passes the intake gate.
24. Release claims change only after current-tip supported-path proof.

---

# 6. Dependency-Ordered Campaign Sweep

## WBC-0 — Freeze Current Truth and the Capability Ledger

**Result:** Completed at `eb6bdc5` as `CAMPAIGN_SWEEP_FROZEN`. The canonical
record is [the capability ledger](./capability-ledger.md).

### Objective

Reconcile the DeepSeek and Hermes findings against **actual current `main`**, producing the definitive Campaign capability ledger and eliminating false gaps before implementation.

### Required inspection boundary

At minimum, inspect:

* current `00-current-state.md`;
* current ADR index and accepted governing ADRs;
* architecture KB entrypoint;
* chat/runtime contracts;
* Command Bus records and events;
* chat task/turn lifecycle;
* agent and Coding Loop runs;
* Campaign Engine / Execution Ledger surfaces;
* provider registry, runtime catalog, and health state;
* OAuth and provider-account storage;
* connector definitions, instances, runs, channels, and frontend Connector Bay;
* Settings and onboarding code;
* current tests and live-proof receipts.

The storage map already shows substantial existing control-plane material—including `events_outbox`, `event_graph_events`, provider inventory/runtime rows, command runs/events, tool jobs, sync jobs, and encrypted OAuth connection state. Those structures must be reconciled before any new ledger, job, or provider-account table is proposed. 

### Required outputs

* Canonical Campaign README.
* Capability ledger.
* Dependency graph.
* Evidence posture for every admitted capability.
* `reuse | extend | replace | retire | no-action` decision for every overlapping seam.
* Deferred-capability register.
* Exact first implementation slice.

### Proof Gate G0 — **Truth Freeze**

Pass only when every capability has:

* baseline classification;
* present Codexify owner;
* current implementation status;
* governing contract or ADR;
* evidence level;
* admitted or parked disposition;
* prerequisite relationships;
* explicit non-goals.

### Failure behavior

If current code and current documentation conflict, record the conflict. Do not normalize it by narrative.

### Exit condition

The exact task sequence is human-approved and frozen. After G0, new items enter only through the Campaign intake gate.

---

## WBC-1 — Close the Supported Runtime Baseline

### Prerequisite

G0 passed.

### Objective

Establish a stable supported foundation before introducing new execution semantics.

### Admitted work

* Fresh current-tip local Compose proof.
* Provider inventory and selected-runtime proof.
* Queue enqueue/dequeue/worker-heartbeat proof.
* Turn-lock and terminal-event proof.
* Persisted assistant readback.
* Migration and upgrade integrity relevant to the supported path.
* Canonical-versus-legacy configuration reconciliation or explicit fencing.
* Coding Loop classification:

  * prove the enabled path end to end, or
  * quarantine it until later Campaign work makes it provable.

The current release authority explicitly lists these as unresolved or required current-tip evidence. 

### Proof Gate G1 — **Supported Runtime Closure**

A supported run must prove:

```text
authenticated authored message
→ accepted completion request
→ Redis enqueue
→ worker dequeue
→ provider execution
→ terminal task event
→ durable assistant persistence
→ independent source-thread readback
```

Required negative proofs:

* duplicate in-flight turn fails correctly;
* worker absence is observable;
* enqueue failure is not reported as accepted;
* restart does not manufacture a terminal result;
* unsupported provider posture is not shown as supported.

### Exit condition

The supported runtime is either:

* **proven ready as a foundation**, or
* **explicitly held with one bounded blocker**.

No execution-spine implementation begins on a runtime whose baseline truth remains ambiguous.

---

## WBC-2 — Establish the Canonical Execution Spine

### Prerequisite

G1 passed or one explicitly accepted bounded blocker remains unrelated to this phase.

### Objective

Make one authored turn and all of its execution consequences durably enclosed and reconstructable.

### Important constraint

This phase is **not authorization for a wholesale event-sourcing rewrite**.

WBC-0 must decide whether the requirement is satisfied by:

* extending existing messages and request records;
* extending task and command-run records;
* composing existing event families through a canonical envelope;
* adding one narrowly scoped append-only execution ledger;
* or some combination with a single declared authority.

### Required semantic model

The runtime must distinguish at minimum:

```text
Authored Turn
Request Attempt
Context Snapshot
Provider Invocation
Step
Tool Call / Command Run
Job or Process Run
Terminal Outcome
Published Result
Source-Thread Return
```

### Required execution facts

* Every attempt has one source turn.
* Every step belongs to one attempt.
* Every tool call has a paired terminal observation.
* Every terminal attempt closes explicitly.
* Every model-visible input is represented in a persisted context manifest or reconstructable canonical projection.
* Derived SSE/UI views identify their durable source.
* Failure and cancellation remain terminal facts, not absent data.

### Proof Gate G2 — **Execution Enclosure**

After a backend and worker restart, Postgres-backed readback must reconstruct:

* source message;
* request identity;
* effective context references;
* provider/model attempt;
* tool or command correlation;
* terminal outcome;
* persisted result;
* return status.

No Redis-only or process-local state may be required to determine what happened.

### Exit condition

One canonical execution truth exists. No parallel “agent transcript,” “terminal transcript,” or “UI transcript” may independently redefine the result.

---

## WBC-3 — Freeze Capability, Provider, and Permission Authority

### Prerequisite

G2 passed.

### Objective

Make runtime authority explicit and immutable for each attempt.

### Required contracts

A run-start snapshot must resolve:

* selected provider connection;
* exact model or model target;
* available tools/commands;
* filesystem scope;
* process/sandbox policy;
* network/egress policy;
* retrieval/context posture;
* approval mode;
* permission preset;
* output limits;
* active connector capabilities;
* effective profile/project/account bindings.

### Provider connection identity

Introduce or confirm the separation between:

```text
Provider Definition
    └── Provider Connection Instance
            ├── owner
            ├── auth mode
            ├── account label
            ├── credential reference
            ├── endpoint
            ├── scopes
            ├── health
            └── selectable models
```

The existing storage map shows encrypted OAuth connection state keyed by user, provider, and mode. That supports the direction, but it does **not by itself prove** arbitrary named multi-account instances or multiple same-mode accounts. WBC-0 must determine whether that storage can be extended or whether a distinct connection-instance record is needed. 

### Approval contract

At minimum:

```text
approval.asked
approval.decided
```

Decision states must distinguish:

* allowed once;
* allowed for this run;
* rejected;
* cancelled;
* expired;
* unavailable;
* policy-blocked.

Named presets may include read-only, workspace-write, and elevated access, but the exact token set must be reconciled against existing permission profiles rather than invented casually.

### Proof Gate G3 — **Frozen Authority**

Prove that:

* effective capability state is snapshotted before execution;
* later account or Settings changes do not rewrite the historical attempt;
* unknown capabilities fail closed;
* provider/connector credentials do not grant command authority;
* one provider connection cannot silently substitute another;
* Command Bus policy cannot be bypassed;
* requested and granted permissions are inspectable.

### Exit condition

Every execution attempt has a durable, attributable authority posture.

---

## WBC-4 — Prove the Persistent Execution Golden Path

### Prerequisite

G3 passed.

### Objective

Prove one complete, useful execution path through a persistent process or job abstraction.

### Golden path

```text
authored turn
→ durable attempt identity
→ frozen capability snapshot
→ local provider decision
→ approval or policy resolution
→ guarded command/process execution
→ persistent job/process state
→ bounded output capture
→ durable terminal result
→ idempotent source-thread return
→ independent readback
```

### Persistent execution requirements

WBC-0 determines whether the native abstraction is named `TerminalSession`, `ExecutionSession`, or an extension of an existing run entity. Regardless of name, it must support:

* owner and source-thread identity;
* bounded working directory/worktree;
* process identity;
* start and terminal timestamps;
* cancellation and signal posture;
* bounded incremental output reads;
* output truncation disclosure;
* durable output locator or spill reference;
* cleanup state;
* terminal exit status;
* recovery classification after worker restart.

### Output doctrine

Large output must not be silently:

* stored in oversized message metadata;
* injected wholesale into later prompts;
* lost when a worker exits;
* represented as complete after truncation.

A spill reference may be introduced only if required by the proven golden path.

### Proof Gate G4 — **Golden Path**

A supported local proof must demonstrate:

* exactly one guarded execution;
* durable progress state;
* cancellation before and during execution;
* restart recovery;
* terminal result persistence;
* source-thread result return;
* duplicate return suppression;
* bounded output retrieval;
* no second unrestricted shell authority;
* no recursive autonomous loop.

The current tool path already has persisted Command Bus runs, policy, idempotency, and a bounded one-command continuation. This phase should compose those strengths rather than replace them. 

### Exit condition

Codexify can reliably perform and explain one useful model-mediated action beyond plain text generation.

This is the Campaign hinge.

---

## WBC-5 — Add Recovery, Replay, and Bounded Delegation

### Prerequisite

G4 passed.

### Objective

Make the execution foundation resilient and reusable without widening it into autonomous orchestration.

### Required work

#### Recovery and replay

* Canonical replay fixtures derived from durable execution records.
* Fault injection at:

  * before enqueue;
  * after enqueue;
  * after dequeue;
  * during provider invocation;
  * before tool dispatch;
  * during process execution;
  * after terminal persistence;
  * before source-thread return.
* Invariant checks for:

  * event enclosure;
  * tool-call pairing;
  * terminal closure;
  * authority snapshot immutability;
  * duplicate side effects;
  * orphaned results;
  * provenance loss.

#### Result-return integrity

Guardian’s current doctrine already requires coding-agent results to return to the source thread with source thread, source message, and job lineage; a failed return must remain an operator-visible handoff failure. 

This Campaign must prove that rule across restart and retry boundaries.

#### Bounded delegation

Introduce or normalize:

```text
SubagentStartRequest
SubagentRun
SubagentResult
```

Each delegated run must:

* inherit a frozen bounded authority snapshot;
* preserve the originating turn and message;
* identify the external executor/provider;
* return through Guardian;
* remain idempotent;
* fail publication when lineage cannot be proven.

External harnesses may execute bounded work, but must not bypass Guardian policy, Command Bus authority, transcript ownership, or result validation. 

#### Conditional maturity items

Only after the mandatory recovery work passes:

* evented context compaction;
* bounded session queries;
* projection change feeds;
* trusted skill metadata and progressive loading;
* non-blocking telemetry/redaction stages.

These items remain in the phase only when WBC-0 confirms an actual baseline gap.

### Proof Gate G5 — **Recovery and Delegation**

Pass when:

* deterministic replay detects malformed or incomplete execution histories;
* duplicate delivery causes no duplicate durable effect;
* failed source-thread return remains visible and retryable;
* delegated results cannot publish without source lineage;
* compaction, if included, never rewrites the authoritative transcript;
* telemetry, if included, distinguishes handed-off from delivered.

### Exit condition

The runtime remains explainable after normal distributed-systems failures.

---

## WBC-6 — Establish the Operator & Integration Control Plane

### Prerequisite

G4 mandatory; G5 delegation work may continue separately if it does not alter connection authority.

### Objective

Create one canonical administrative answer to:

> What external systems can this Codexify instance currently use, through which account, with what authority, and in what health state?

Current operator documentation requires the provider registry, supported profile, catalog, provider health, and chat health to be read together; no single integrated released surface currently explains every routing decision, downgrade, inventory mismatch, or queue-to-UI causal chain. 

### 6.1 Provider account registry

Support:

* one provider family;
* multiple independently selectable connection instances;
* API-key and OAuth modes where the provider supports them;
* multiple named accounts without pretending they are different provider families;
* custom compatible endpoints;
* enabled/disabled state;
* policy eligibility;
* credential presence without secret disclosure;
* account-scoped and optional project/profile selection;
* last successful use and bounded failure state.

Example target behavior:

```text
MiniMax
├── Personal OAuth
├── Work OAuth
└── Project API Key
```

The UI may display those as independent choices while the runtime still recognizes one provider family.

### 6.2 Integration Registry

Normalize the administrative layer around:

```text
Integration Definition
    id
    category
    display metadata
    supported auth modes
    credential schema
    capability declarations
    scopes
    health contract
    configuration schema

Integration Instance
    owner
    definition id
    account label
    auth mode
    credential reference
    granted scopes
    enabled state
    health
    last activity
    last error
    sync or webhook posture
```

### 6.3 Connector categories

The registry should support categories without flattening their runtime semantics:

| Category                 | Representative examples                   |
| ------------------------ | ----------------------------------------- |
| Messaging channels       | Discord, Matrix, iMessage                 |
| Communications services  | Twilio                                    |
| Social platforms         | X                                         |
| Knowledge and notes      | Apple Notes, Google Drive, Notion         |
| Media services           | Spotify                                   |
| Agent protocols          | A2A                                       |
| Tool protocols           | MCP                                       |
| Repositories and storage | GitHub, Drive                             |
| Inference providers      | OpenAI, MiniMax, DeepSeek, local runtimes |

### 6.4 Connector Bay

The existing Connector Bay becomes a projection of the canonical registry and instances.

It must show:

* available integration definitions;
* connected instances;
* missing configuration;
* credential state;
* granted scopes;
* enabled state;
* health;
* last activity;
* sync posture;
* actionable failure reason.

It must not:

* contain raw secrets;
* derive truth from hardcoded frontend cards;
* report a connector healthy merely because a definition exists;
* imply a connector is release-supported because it is configurable.

### Representative proof boundary

This Campaign does **not** require X, Discord, Matrix, A2A, iMessage, Twilio, Apple Notes, Spotify, and every other desired connector to be implemented.

It requires the general architecture to be proven with the smallest representative set available in the current repository:

* preferably one OAuth-backed service;
* preferably one API-token, webhook, or channel-backed service;
* or one existing connector plus contract fixtures for the second auth family when a second live connector would open unnecessary scope.

### Proof Gate G6 — **Administrative Legibility**

Pass when an operator can determine, without inspecting environment files or containers:

* which provider connections exist;
* which account is selected;
* whether credentials are present;
* what scopes/capabilities are granted;
* which integrations are active;
* whether each is healthy;
* what failed and where;
* which state is supported, internal, preview, disabled, or unavailable.

### Exit condition

Codexify has a general provider and integration control plane. Individual connector acquisition becomes ordinary product backlog work.

---

## WBC-7 — Guided Onboarding and Campaign Revalidation

### Prerequisite

G6 passed.

### Objective

Make a fresh Codexify installation reach a usable baseline through one guided flow over canonical APIs.

### Onboarding sequence

```text
Deployment/operator posture
→ Codexify account
→ local runtime or provider connection
→ default model
→ workspace/repository boundary
→ safety and permission preset
→ memory/identity posture
→ optional integrations
→ health verification
→ ready
```

### Onboarding invariants

* Onboarding owns no independent configuration truth.
* Every completed step writes through the same canonical service used by Settings.
* Interrupted onboarding resumes from canonical state.
* Optional steps remain optional.
* Provider secrets and connector secrets are opaque after submission.
* Local-first setup does not pressure the user into cloud connectivity.
* Identity-depth and memory decisions remain explicit.
* A failed health check does not erase valid configuration.
* “Ready” is based on actual minimum-path evidence, not completed form fields.

### Proof Gate G7 — **Workspace Baseline Revalidation**

Re-run the capability ledger and classify every row:

* `existing and proven`;
* `existing with accepted limitation`;
* `deferred mature UX`;
* `advanced`;
* `differentiator`;
* `blocked`.

The Campaign closes only when no unresolved **Expected** capability remains an unclassified structural gap.

---

# 7. Campaign Decision Gates

| Gate                               | Decision                                                                          |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| **G0 — Truth Freeze**              | Do we know what actually exists on current `main`?                                |
| **G1 — Runtime Closure**           | Is the supported local runtime stable enough to build upon?                       |
| **G2 — Execution Enclosure**       | Can one attempt be reconstructed durably without Redis or worker memory?          |
| **G3 — Frozen Authority**          | Is effective capability and permission state attributable and immutable?          |
| **G4 — Golden Path**               | Can Codexify complete one guarded persistent action and return the result?        |
| **G5 — Recovery & Delegation**     | Does the path survive restart, retry, duplicate delivery, and bounded delegation? |
| **G6 — Administrative Legibility** | Can the operator understand providers, accounts, integrations, and health?        |
| **G7 — Maturity Revalidation**     | Are remaining gaps refinement rather than missing runtime structure?              |

A failed gate blocks downstream work unless the failure is explicitly classified as unrelated and bounded.

---

# 8. Deferred Observatory

The following remain visible but **outside the active Campaign critical path**.

## Individual connector expansion

* X
* Discord
* Matrix
* A2A
* iMessage
* Twilio
* Apple Notes
* Spotify
* additional app-specific connectors

The Campaign builds the substrate and representative proof. Each connector later receives its own atomic implementation and proof task.

## Advanced runtime work

* recursive autonomous agent loops;
* generalized workflow execution;
* arbitrary dynamic extension activation;
* self-modifying runtime behavior;
* runtime plugin forge sandbox;
* multi-agent scheduling;
* automatic repair and rebinding;
* LSP/navigation integration;
* generalized external agent protocol support beyond the bounded delegation seam.

## Existing side fronts

* Browser Host expansion;
* Hosted Room release qualification;
* federation and cross-node sync;
* Atlas implementation;
* Home Presence;
* ThreadSpace network work;
* Campaign Engine expansion not required by this execution spine;
* email product work;
* packaged desktop replacement of Compose.

## Product refinement

* billing;
* extensive themes;
* terminal-font preferences;
* completion sounds;
* keyboard-shortcut expansion;
* update and uninstall UX;
* broad voice configuration;
* notification polish.

These can be good work without being Campaign dependencies. The Helsinki toggle remains under observation. 🧐

---

# 9. Explicit Connector Decision

The desired app-connector universe is accepted as a **valid product direction**, but not as one giant Campaign deliverable.

The Campaign admits:

* the Integration Registry;
* connector definition and instance semantics;
* auth-mode handling;
* credential custody;
* capability/scopes;
* health and activity;
* Connector Bay population;
* onboarding and Settings integration;
* representative connector proof.

The Campaign does **not** admit:

> “Implement all connectors visible in Hermes.”

That is feature parity disguised as infrastructure.

Once G6 passes, adding Apple Notes or Spotify should be an ordinary adapter task, not an architectural expedition.

---

# 10. Known Campaign Risks

## Risk: Parallel execution truth

Codexify already has messages, outbox events, command events, task events, agent runs, eval snapshots, and Campaign Engine concepts.

**Mitigation:** WBC-0 requires a reuse/extend decision before any ledger schema.

## Risk: Event-sourcing rewrite by enthusiasm

The DeepSeek pattern may be interpreted as requiring the entire application to become event-sourced.

**Mitigation:** The requirement is durable execution enclosure and derivable projections—not ideological purity.

## Risk: Admin UI ahead of canonical semantics

A polished Provider or Connector screen could become a decorative truth surface backed by inconsistent environment variables.

**Mitigation:** WBC-3 and WBC-6 establish canonical instance semantics before UI completion.

## Risk: Connector buffet scope explosion

Every connector has different authentication, webhook, polling, sync, rate-limit, and authority semantics.

**Mitigation:** Prove the registry using representative connector families; defer individual adapters.

## Risk: Provider account identity confusion

Provider family, model, endpoint, OAuth account, API key, and Codexify user identity can collapse into one picker.

**Mitigation:** Provider definition, connection instance, model target, and Codexify identity remain distinct contracts.

## Risk: Mature UX becomes architecture

Hermes exposes many useful settings that are not runtime prerequisites.

**Mitigation:** Only onboarding, account connections, integration administration, and health legibility enter this Campaign.

## Risk: Release claim expansion

A successful internal provider or connector test may be mistaken for supported beta behavior.

**Mitigation:** Current-state changes occur only after current-tip supported-path proof.

---

# 11. Campaign Stop Rule

Close **Workspace Baseline Convergence** when all of the following are true:

* [ ] The supported local Compose path has fresh terminal and persistence proof.
* [ ] Queue, worker, turn-lock, and terminal semantics are current-tip proven.
* [ ] Canonical-versus-legacy configuration ambiguity is resolved or explicitly fenced.
* [ ] One durable execution attempt can be reconstructed after restart.
* [ ] Every model-visible context input has attributable provenance.
* [ ] Effective capabilities and permissions are snapshotted per attempt.
* [ ] Guarded tool/process execution cannot bypass Command Bus or Guardian policy.
* [ ] One persistent execution golden path completes and returns durably.
* [ ] Cancellation, retry, duplicate delivery, and restart behavior are proven.
* [ ] Source-thread result return is idempotent and operator-visible on failure.
* [ ] Bounded delegation preserves authority and lineage.
* [ ] Provider connection instances support account-level selection without identity conflation.
* [ ] The Integration Registry and Connector Bay expose canonical state.
* [ ] Onboarding configures the minimum usable workspace through canonical APIs.
* [ ] Every **Expected** capability is proven, explicitly bounded, or accepted as a documented limitation.
* [ ] Remaining gaps are primarily Mature UX, Advanced capabilities, differentiators, or individual adapters.
* [ ] `00-current-state.md` and release posture accurately reflect the final proof.

The Campaign must then close even though additional improvements remain possible.

Runtime maturity does not mean Codexify contains everything. It means adding the next useful capability no longer requires inventing another foundation underneath it.

---

# 12. Sole Next Task

## **WBC-1A — Capture current-tip supported-Compose runtime closure evidence**

**Execution lane:** Architecture-impact
**Task kind:** Proof
**Evidence posture:** Current-tip supported-path live-runtime proof needed

### Bounded outcome

Exercise the supported local Compose profile at the reconciled current tip and
record independent evidence for health, model inventory, queue acceptance and
dequeue, turn locking, terminal completion, assistant persistence, source-thread
readback, and the configuration values actually consumed.

### Proposed owned artifacts

The ledger is the governing Campaign reconciliation record. This proof task
must not create a new ledger, terminal abstraction, provider-account schema, or
release claim merely because an acceptance route or focused test passes.

### It must answer

1. Does the supported profile start and report healthy with its intended local model inventory?
2. Does one chat completion separately prove enqueue, dequeue, turn-lock
   handling, terminal evidence, durable assistant persistence, and independent
   source-thread readback?
3. Which canonical and legacy configuration values were actually consumed, and
   do they agree?
4. Which observed failures are configuration, queue/worker, provider,
   persistence, or readback failures rather than a collapsed "chat failed" claim?

### Non-goals

* No new runtime feature, migration, event table, provider-account schema,
  connector, UI behavior, ADR, or release-claim update.
* No Coding Loop qualification unless the task is separately expanded after the
  ordinary supported path has current-tip evidence.

### WBC-1A proof result

The closeout must record a bounded G1 result and update current-state release
truth only through a separately authorized documentation task if the evidence
supports a change.

---

## Final Campaign Posture

**G0 outcome:** `CAMPAIGN_SWEEP_FROZEN`. The next candidate is
**WBC-1A current-tip supported-Compose runtime closure evidence**. See the
[capability ledger](./capability-ledger.md) for the frozen admission set and
dependency order.

**Admit:** runtime closure, execution spine, capability authority, approvals, persistent execution, result return, recovery, bounded delegation, provider connection instances, integration registry, Connector Bay, and onboarding.

**Conditionally admit:** compaction, session projections, skills, spill storage, and telemetry only where WBC-0 or the golden path proves they are necessary.

**Park:** individual connector proliferation, autonomous workflows, dynamic runtime extension, LSP, and unrelated product fronts.

**Stop comparative remapping after WBC-0.**

The map is sufficient. Now the work is to close the seams—one proven slice at a time.
