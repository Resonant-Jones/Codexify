# Audit Against Regressions and Preventable Traps

## Purpose

This audit exists to prevent the system from drifting into fragile behavior while it grows in power, complexity, and surface area.

It is designed for a system that includes:

* multiple model providers or model families
* retrieval and memory layers
* tool use and external integrations
* persona or identity boundaries
* queue and worker execution
* local and cloud execution paths
* agent or semi-agent orchestration

The goal is not to eliminate all risk.

The goal is to make risk:

* visible
* scored
* owned
* testable
* reviewable before release

---

## Core Principle

Do not ask only whether a feature works.

Ask whether it introduces:

* hidden coupling
* new blast radius
* silent regression paths
* migration debt
* behavioral instability
* ownership confusion
* observability gaps

A working feature can still be a future outage in ceremonial clothing.

---

## The Audit Structure

This audit has four layers:

1. **Risk Matrix**

   * What can go wrong, how bad it is, how likely it is, how hard it is to detect.

2. **Regression Gates**

   * What must be checked before merge, before release, and after release.

3. **Trap Catalogue**

   * A living record of common preventable mistakes.

4. **Operational Ritual**

   * A recurring review cadence so the audit stays alive instead of becoming wall decor.

---

## Scoring Model

Each risk gets scored on four dimensions.

### Impact

* **1** = cosmetic or low consequence
* **2** = annoying but recoverable
* **3** = materially harmful to workflow or trust
* **4** = serious breakage, corrupted behavior, or high support load
* **5** = existential, security-critical, or system-wide damage

### Likelihood

* **1** = unlikely without unusual conditions
* **2** = possible but not expected
* **3** = plausible during normal evolution
* **4** = likely under active development
* **5** = already happening or nearly guaranteed

### Detectability

* **1** = obvious immediately
* **2** = visible with normal QA
* **3** = requires targeted inspection
* **4** = easy to miss until users report it
* **5** = mostly silent until damage accumulates

### Recoverability

* **1** = trivial rollback or repair
* **2** = simple fix, low cleanup cost
* **3** = moderate effort or targeted migration needed
* **4** = painful repair, user-visible fallout
* **5** = irreversible or extremely expensive to repair

### Risk Score

Use:

**Risk Score = Impact × Likelihood × Detectability × Recoverability**

### Risk Bands

* **1-20** = Low
* **21-120** = Moderate
* **121-180** = High
* **181-625** = Critical

---

## Primary Risk Matrix

| Risk Area              | Failure Mode                                                   | Impact | Likelihood | Detectability | Recoverability | Score | Band     | Owner        | Current Controls      | Required Mitigation                                                   |
| ---------------------- | -------------------------------------------------------------- | -----: | ---------: | ------------: | -------------: | ----: | -------- | ------------ | --------------------- | --------------------------------------------------------------------- |
| Model Routing          | Provider change breaks response shape or tool behavior         |      4 |          4 |             3 |              2 |    96 | Moderate | Platform     | adapter abstraction   | add contract tests per provider and fallback snapshots                |
| Retrieval              | Relevant memory is not returned or irrelevant memory dominates |      4 |          4 |             4 |              3 |   192 | Critical | Memory       | manual inspection     | add retrieval eval set, drift alerts, relevance thresholds            |
| Memory Ownership       | Context becomes coupled to one vendor or opaque store          |      5 |          2 |             4 |              4 |   160 | High     | Platform     | local-first posture   | maintain export path, canonical internal schema, migration test       |
| Persona Boundaries     | Cross-persona leakage or identity contamination                |      5 |          3 |             4 |              4 |   240 | Critical | Identity     | conceptual separation | add boundary tests, isolation assertions, trace tagging               |
| Tool Integrations      | Tool API changes silently break execution                      |      4 |          4 |             4 |              2 |   128 | High     | Integrations | wrapper layer         | add tool contract versioning and synthetic health checks              |
| Queue / Worker         | Jobs stall, duplicate, or execute out of order                 |      5 |          3 |             3 |              3 |   135 | High     | Runtime      | idempotency in places | add job state invariants, poison queue policy, replay tests           |
| Orchestration          | Multi-step agent flow fails without recovery path              |      5 |          4 |             4 |              3 |   240 | Critical | Runtime      | ad hoc retry logic    | formalize step state machine, retry taxonomy, human escalation        |
| Cost Control           | Agent loops or retrieval inflation increase spend unexpectedly |      4 |          4 |             3 |              2 |    96 | Moderate | Ops          | manual observation    | add per-run budget guardrails and cost anomaly detection              |
| Eval Coverage          | System changes ship without proving behavior quality           |      4 |          4 |             5 |              2 |   160 | High     | QA           | spot checks           | define golden tasks, scenario packs, pre-release score floor          |
| Schema Drift           | Internal objects evolve without migration discipline           |      4 |          3 |             4 |              4 |   192 | Critical | Platform     | implicit adaptation   | add schema versions, migrators, forward/backward compatibility checks |
| Prompt Coupling        | Logic lives inside prompts and becomes brittle                 |      3 |          4 |             4 |              3 |   144 | High     | Runtime      | prompt iteration      | move logic to typed config or code wherever possible                  |
| Behavioral Coupling    | System quality depends on one model’s temperament              |      4 |          4 |             5 |              3 |   240 | Critical | Platform     | multi-model intent    | add cross-model eval parity and degraded-mode acceptance tests        |
| Observability          | Failures occur but cannot be explained after the fact          |      5 |          3 |             5 |              4 |   300 | Critical | Ops          | scattered logs        | add end-to-end traces, correlation ids, reason codes                  |
| Security / Permissions | Tools exceed intended authority or access wrong data           |      5 |          2 |             4 |              5 |   200 | Critical | Security     | boundary awareness    | enforce scoped permissions, audit logs, deny-by-default tool policy   |
| UX Trust               | User sees inconsistent identity, memory, or action intent      |      4 |          3 |             4 |              3 |   144 | High     | Product      | manual review         | add trust-focused UX acceptance checks                                |
| Migration Debt         | Swapping a backend or provider becomes too painful             |      4 |          3 |             4 |              4 |   192 | Critical | Platform     | modularity intent     | run quarterly swap drills against one subsystem                       |
| Complexity Creep       | Too many moving parts slow delivery and hide defects           |      4 |          5 |             4 |              3 |   240 | Critical | Architecture | intuition             | require simplification review for every net-new subsystem             |
| Data Integrity         | Stored memory, event logs, or documents become inconsistent    |      5 |          3 |             4 |              4 |   240 | Critical | Data         | partial safeguards    | add checksum/invariant checks and repair scripts                      |

---

## What to Treat as Immediate Red Flags

Any proposal should trigger an audit stop if it does one or more of the following:

* introduces a new hidden dependency on one model provider
* stores canonical user context in a vendor-owned black box
* weakens persona or identity isolation
* adds tool power without scoped permissions and logging
* adds orchestration complexity without traceability
* relies on prompt behavior where typed logic should exist
* has no rollback path
* cannot be evaluated before release
* cannot be migrated later without a one-off rescue mission

---

## Preventable Trap Catalogue

### Trap 1: Framework-as-Architecture

**Pattern:** a library decides the system shape.

**Symptoms:**

* business logic buried in chain definitions
* retries and routing hidden inside framework defaults
* difficult to inspect state transitions

**Countermeasure:**

* keep your own execution model and state machine
* frameworks are adapters, not the constitution

### Trap 2: Prompt-as-Orchestrator

**Pattern:** system behavior depends on persuasive wording instead of explicit control flow.

**Symptoms:**

* small wording changes alter routing or safety behavior
* impossible to explain why a path was chosen

**Countermeasure:**

* move routing, budgets, permissions, and fallbacks into code/config

### Trap 3: Silent Retrieval Drift

**Pattern:** retrieval appears fine until the corpus grows or embeddings change.

**Symptoms:**

* answers become vaguer over time
* memory feels haunted by stale facts

**Countermeasure:**

* maintain a fixed eval set for retrieval quality
* compare recall/precision before and after changes

### Trap 4: Identity Bleed

**Pattern:** context crosses boundaries between personas, projects, or users.

**Symptoms:**

* wrong tone, wrong memory, wrong assumptions, wrong permissions

**Countermeasure:**

* hard tag every memory and action with identity scope
* test for boundary violations explicitly

### Trap 5: Tool Power Without Governance

**Pattern:** tools are available because they are useful, not because they are governable.

**Symptoms:**

* unclear authorization model
* hard to reconstruct what happened

**Countermeasure:**

* every tool call must have scope, trace, initiator, and reason

### Trap 6: Evaluation Theater

**Pattern:** a few happy-path demos substitute for evidence.

**Symptoms:**

* release confidence based on vibe
* regressions found by users first

**Countermeasure:**

* create golden tasks, failure tasks, and adversarial tasks

### Trap 7: Adapter Illusion

**Pattern:** code has adapters, but behavior still depends on one provider’s quirks.

**Symptoms:**

* same prompt fails badly across models
* tool behavior differs in ways the system does not absorb

**Countermeasure:**

* design for minimum guaranteed behavior across providers
* add parity tests instead of assuming portability

### Trap 8: Orchestration by Accumulated Exceptions

**Pattern:** system coordination emerges from many local fixes.

**Symptoms:**

* retries, merges, escalations, and cancellations all behave differently

**Countermeasure:**

* define a formal lifecycle for tasks and agents

### Trap 9: No Blast Radius Model

**Pattern:** new actions are added without deciding how much damage they could do.

**Symptoms:**

* one bad output reaches storage, tools, user-facing UI, and background workers

**Countermeasure:**

* classify every feature by blast radius before release

### Trap 10: Complexity Prestige

**Pattern:** complexity is mistaken for sophistication.

**Symptoms:**

* too many optional paths
* too many stores
* too many modes

**Countermeasure:**

* require justification for every new subsystem
* remove at least one thing for every major addition when possible

---

## Regression Gates

## Gate 1: Before Merge

Every meaningful change must answer:

* What layer does this change affect?
* What existing behavior could regress?
* What identity boundary could be crossed?
* What observability was added or updated?
* What rollback path exists?
* What eval or invariant proves this is safe?

### Merge Checklist

* [ ] layer identified
* [ ] blast radius identified
* [ ] owner assigned
* [ ] invariants listed
* [ ] tests added or updated
* [ ] traces/logging updated
* [ ] rollback described
* [ ] migration impact reviewed

---

## Gate 2: Before Release

### Release Checklist

* [ ] golden task suite passes
* [ ] retrieval eval suite passes
* [ ] cross-provider sanity checks pass
* [ ] tool contract checks pass
* [ ] queue/worker replay checks pass
* [ ] identity isolation checks pass
* [ ] cost budget checks pass
* [ ] observability dashboard reviewed
* [ ] schema migration tested forward and backward where applicable
* [ ] one designated reviewer argues against release and fails to break it

---

## Gate 3: After Release

### Post-Release Review

Within a fixed window after release, inspect:

* error rates
* task completion rates
* retrieval relevance signals
* cost per successful outcome
* fallback frequency
* user trust incidents
* unexpected boundary crossings

If any spike occurs, create an incident entry even if the issue self-resolves.

---

## The Audit Ritual

### Weekly

Run a 30-minute regression review.

Agenda:

1. New incidents or near-misses
2. Highest-score risks
3. Any subsystem whose complexity increased this week
4. Any change that shipped without full eval coverage
5. One removal or simplification candidate

### Monthly

Run a deeper architecture audit.

Agenda:

1. Re-score the risk matrix
2. Review whether any “temporary” shim became permanent
3. Review provider dependency drift
4. Review memory portability and exportability
5. Review orchestration debt
6. Review observability gaps

### Quarterly

Run one forced migration drill.

Examples:

* swap embedding model
* disable one provider
* replace one retrieval backend
* stub one integration provider
* simulate queue duplication or worker death

Purpose:
prove the system is actually portable, not merely described that way.

---

## Audit Templates

## 1. Change Review Entry

**Change:**

**Layer(s) affected:**

**Primary risk introduced:**

**Failure mode if wrong:**

**Blast radius:**

**How detected:**

**Rollback path:**

**Eval evidence:**

**Owner:**

---

## 2. Incident / Near-Miss Entry

**Date:**

**Subsystem:**

**What happened:**

**What should have prevented it:**

**Why prevention failed:**

**Was the issue silent or obvious:**

**What invariant/test/log is now required:**

**Risk matrix row updated:**

---

## 3. Forced Migration Drill Entry

**Subsystem tested:**

**Original dependency:**

**Replacement or failure simulation:**

**What broke:**

**What stayed stable:**

**Actual migration cost:**

**What would reduce future cost:**

---

## Initial Priority Order

Do these first.

### Tier 1

* define golden tasks
* define retrieval eval pack
* define identity boundary tests
* define tool contract checks
* add end-to-end trace ids

### Tier 2

* formalize task or agent lifecycle states
* add budget guardrails
* add schema versioning discipline
* create incident and near-miss log

### Tier 3

* run forced migration drills
* review subsystem count and remove one avoidable complexity source
* formalize orchestration failure taxonomy

---

## Non-Negotiable Invariants

These should eventually become enforced checks.

* a memory item must always have clear ownership scope
* a tool action must always have a traceable initiator and reason
* no high-blast-radius action may occur without audit visibility
* no release should rely on a single happy-path demo
* no provider-specific behavior should be treated as universal without proof
* no schema change should ship without migration consideration
* no orchestration path should exist without failure handling

---

## Final Standard

The standard is not:

"Can this system do impressive things?"

The standard is:

"Can this system change shape without losing its mind, its memory boundaries, or its operational truth?"

That is the real audit.
