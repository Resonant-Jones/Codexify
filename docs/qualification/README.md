# Codexify Qualification Registry

## Purpose

This directory is the canonical human-readable and machine-projectable source of truth for **Codexify qualification status**.

It answers:

- What has actually been tested?
- Against which version of Codexify?
- Under what conditions?
- By whom?
- What passed, failed, remains blocked, or has not yet been proven?
- What evidence supports that conclusion?

This directory is intended to be readable directly in GitHub and suitable as the source for future Codexify tester, visitor, operator, or public-preview dashboards.

It does **not** replace detailed architecture proofs, automated test suites, Ops runbooks, or release authority. Instead, it indexes and normalizes qualification evidence.

## Authority boundary

Qualification truth is separated into four layers:

```text
Rubric
  ↓
defines what must be proven

Run
  ↓
records what was actually attempted

Evidence
  ↓
supports each observation

Registry
  ↓
projects current qualification status
```

A feature is never considered qualified merely because:

- its code exists;
- unit tests pass;
- a route is enabled;
- a mock browser test succeeds;
- an architecture document describes it;
- somebody remembers trying it successfully;
- a previous commit passed.

Qualification is tied to evidence.

## Relationship to existing repository evidence

Existing detailed evidence may remain in locations such as:

```text
docs/architecture/proofs/
docs/Ops/
tests/
frontend test artifacts
runtime proof artifacts
```

Those files remain valid evidence sources.

However, **current qualification status must be represented here**.

A qualification entry should link back to the exact detailed proof rather than duplicating a large proof packet.

This directory is therefore the **status projection**, while detailed proofs remain the **evidence record**.

## Directory structure

```text
docs/qualification/
├── README.md
├── registry.json
│
├── rubrics/
│   ├── onboarding-and-people.md
│   ├── guardian-chat.md
│   ├── documents-and-retrieval.md
│   ├── account-and-auth.md
│   └── ...
│
├── runs/
│   ├── YYYY-MM-DD-<surface>-<tester-or-context>.md
│   └── ...
│
├── metrics/
│   ├── definitions.md
│   └── baselines.md
│
└── schemas/
    └── qualification-registry.schema.json
```

Do not create a separate proof universe inside this directory.

Large screenshots, Playwright traces, database dumps, or runtime artifacts should remain in the appropriate existing evidence location. The run receipt should link to them.

## Qualification vocabulary

### Check-level results

Every required check uses exactly one of:

- **PASS** — the stated criterion was directly observed under the recorded conditions.
- **FAIL** — the stated criterion was attempted and did not behave as required.
- **UNPROVEN** — there is insufficient evidence to say PASS or FAIL.
- **N/A** — the criterion genuinely does not apply to this configuration. N/A must include a reason.

### Overall qualification verdict

Every qualification run uses exactly one of:

- **PASS** — every required blocking criterion passed for the explicitly stated scope.
- **HOLD** — successful observations may exist, but required evidence is missing, blocked, mixed, or stale.
- **FAIL** — at least one required blocking criterion produced a reproducible failure that contradicts the expected contract.

Avoid ambiguous overall statuses such as:

```text
mostly passed
partial pass
basically working
good enough
seems fine
probably fixed
```

Individual successful observations may be recorded inside a HOLD or FAIL run.

## Qualification identity

Every run must identify:

- date and time window;
- tester;
- tester role;
- commit SHA;
- branch;
- runtime profile;
- deployment/environment;
- device class;
- browser/client;
- relevant provider/model where applicable;
- whether the tester had prior familiarity;
- whether the test was assisted;
- rubric version;
- resulting verdict.

Example:

```text
Date: 2026-09-30
Tester: Zac
Tester role: invited private-preview user
Prior Codexify familiarity: limited
Commit: <exact SHA>
Profile: v1-friends-family-web
Surface: desktop web
Rubric: onboarding-and-people v1
Assistance: none during first attempt
Verdict: HOLD
```

## Tester independence

Human qualification must record how much intervention was required.

| Level | Meaning |
| --- | --- |
| 0 — Independent | Tester completed the action without operator guidance. |
| 1 — Self-recovery | Tester became confused but recovered using visible UI, Tips, or normal exploration. |
| 2 — Clarification | Tester asked what a concept meant, but was not given exact UI steps. |
| 3 — Navigation hint | Operator told tester where to look or which surface to open. |
| 4 — Directed | Operator provided exact steps or effectively walked the tester through the task. |

A Level 4 completion proves that the underlying feature can work. It does **not** prove that the interface is independently usable.

## Human feedback rules

Tester feedback should preserve the tester's own language whenever practical.

Record separately:

```text
Observed behavior
Tester interpretation
Operator interpretation
```

Example:

```text
Observed:
Tester opened Guardian when asked to message another person.

Tester comment:
"I thought all conversation happened here."

Operator interpretation:
People versus Guardian distinction was not understood.
```

Do not rewrite confusion into a cleaner explanation before recording it. Confusion is evidence.

## Metrics philosophy

Codexify qualification uses both:

### Contract metrics

Binary or directly observable facts.

Examples:

- message persisted;
- username survived restart;
- skip state remained skipped;
- wrong account could not read state;
- conversation reopened with the same ID.

These can block qualification.

### Experience metrics

Human usability signals.

Examples:

- time to locate People;
- intervention level;
- navigation mistakes;
- comprehension;
- perceived privacy pressure;
- confidence after onboarding.

These help prioritize product changes. They should not be converted into arbitrary PASS thresholds without an explicit baseline.

See [metrics/definitions.md](metrics/definitions.md).

## Privacy-sensitive testing

Never ask a tester to disclose:

- legal name;
- private email beyond what account setup already requires;
- private credentials;
- API keys;
- private conversation content;
- unrelated personal information

for the purpose of product qualification.

Test usernames may be pseudonymous.

Tester identity in committed qualification receipts may also use an agreed public/tester alias when appropriate.

## Qualification scope

A PASS must always name its scope.

Good:

> PASS — same-node People messaging between two authenticated private-preview accounts, including durable send/reply and reopen.

Bad:

> PASS — messaging works.

Good:

> PASS — onboarding skip/resume persistence on desktop web for the tested hosted profile.

Bad:

> PASS — onboarding is production ready.

## Evidence freshness

Qualification is commit-bound.

A previous PASS does not automatically qualify a later commit.

The registry should distinguish:

```text
current
stale
superseded
```

A run becomes `stale` when meaningful changes touch its qualification surface.

A later run may supersede it.

Historical runs must not be edited to pretend they tested later code.

## Qualification run files

Run files are receipts.

Once committed, preserve the original observation.

If a conclusion was incorrect, append a correction or supersede the run.

Do not silently rewrite historical evidence.

Recommended filename:

```text
YYYY-MM-DD-<surface>-<tester-or-context>.md
```

Examples:

```text
2026-09-30-onboarding-zac.md
2026-09-30-onboarding-george.md
2026-10-02-people-two-user-live.md
```

## Machine-readable registry

`registry.json` is the current dashboard-facing projection.

It contains one entry per qualification surface, not every historical run.

The registry must summarize evidence. It must never manufacture it.

## Dashboard contract

A future qualification dashboard may project:

- current verdict;
- latest tested commit;
- last qualification date;
- tester count;
- automated test status;
- human qualification status;
- known blockers;
- relevant metrics;
- evidence links.

The dashboard is a view.

The repository remains authority.

```text
Repo qualification registry
          ↓
     dashboard API
          ↓
     visitor/tester UI
```

The dashboard must never become the only location where qualification state exists.

## Release relationship

Qualification status and release status are related but distinct.

A feature may be:

```text
implementation complete
qualification PASS
release unsupported
```

or:

```text
implementation complete
qualification HOLD
private preview available
```

`docs/architecture/00-current-state.md` remains authoritative for overall release and supported-path claims.

Nothing in this directory independently widens Beta or production support.

## Initial qualification areas

The registry should eventually cover at minimum:

- account activation and authentication;
- onboarding and Tips;
- People and direct messaging;
- Guardian ordinary chat;
- Projects and Threads;
- Documents;
- retrieval;
- imports;
- Gallery/media;
- provider/model routing;
- local runtime;
- private-preview runtime;
- persistence and restart recovery;
- backup/restore;
- account isolation;
- mobile shell;
- desktop shell;
- connectors;
- execution/coding surfaces where exposed.

Only create a qualification area when there is a defined rubric.

A feature with no rubric is:

```text
UNPROVEN
```

not implicitly passing.

## Governing principle

> **Qualification is an evidence ledger, not a confidence statement.**

The goal is not to make Codexify look green.

The goal is to make the exact boundary between:

```text
built
tested
observed
qualified
supported
```

inspectable by anyone.
