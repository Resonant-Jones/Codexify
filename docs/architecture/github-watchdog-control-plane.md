# GitHub Watchdog Control Plane

## Status and scope

This is the accepted architecture contract for the future Guardian-owned
GitHub Watchdog under [ADR-073](./adr/073-github-watchdog-review-and-dispatch-control-plane.md).
It is a documentation contract, not a GitHub App, webhook, worker, database
migration, model invocation, GitHub API mutation, Settings UI, or supported
release surface.

The Watchdog extends rather than replaces [ADR-050](./adr/050-event-driven-campaign-control-plane.md).
ADR-050 remains the GitHub-native deterministic, read-only, dry-run Campaign
Control Plane. The Watchdog adds a future model-backed advisory review and
explicit Guardian mutation-dispatch boundary; it does not make model opinion
deterministic eligibility, merge authorization, or release truth.

`docs/architecture/00-current-state.md` remains authoritative for current
release reality. The Watchdog is not implemented or release-supported.

## Canonical topology and authority

```text
GitHub App
  -> authenticated webhook intake
  -> normalized delivery / durable receipt / idempotency
  -> Guardian Watchdog policy evaluation
  -> Observe | Review | Mutate
       |          |          |
       |          |          +-> existing Guardian Build Loop only
       |          +-> model-backed immutable-PR analysis
       +-> deterministic inspection / ADR-050-compatible evidence
  -> GitHub Check Run and bounded review output
  -> Postgres-backed attempt and result evidence
```

| Component | Owns | Must not own |
| --- | --- | --- |
| Guardian | Authorization, policy, identity/correlation, durable receipt and attempt evidence, dispatch lineage, result ingestion. | A second GitHub-repository truth source or a bypass of human merge authority. |
| GitHub App | Authenticated event/API adaptation and installation/repository context. | Agent authority, provider routing, coding-harness authority, or canonical audit truth. |
| Watchdog policy evaluator | Operation classification and policy snapshot resolution. | A replacement provider registry, adapter registry, command bus, or queue universe. |
| Provider/model | The selected bounded inference execution dependency. | Authority, policy alteration, merge approval, or durable transcript ownership. |
| Coding harness/adapter | The selected Build Loop execution dependency for an authorized mutation. | GitHub-comment authority, direct webhook authority, or Guardian lineage ownership. |
| Postgres | Durable receipts, attempts, correlations, and results. | Ephemeral queue coordination. |
| Redis | Queue transport, locks, cancellation, transient coordination, and progress visibility. | Canonical Watchdog audit/persistence truth. |
| GitHub Check / review output | External advisory publication tied to a SHA. | Human review truth, merge authority, or release proof. |

## GitHub App webhook boundary

### Required intake behavior

The intended integration family is a GitHub App. A future HTTPS webhook
endpoint must:

1. retain the unmodified request body;
2. validate `X-Hub-Signature-256` against that raw body using a server-side
   webhook secret before deserializing or processing the event;
3. capture the canonical GitHub delivery identifier (normally
   `X-GitHub-Delivery`), installation identity, repository identity, event
   type/action, triggering actor, and applicable PR/issue/comment identity;
4. resolve the immutable PR `headSha` before creating a Review or Mutate
   attempt; and
5. durably accept or reject the delivery, then acknowledge promptly.

No model review, coding harness, repository-code execution, long-running
GitHub API fan-out, or live mutation runs inside the delivery HTTP request.

The webhook secret and future App credentials remain server-side. They never
appear in PR-controlled code, GitHub output, browser state, or a Watchdog
receipt payload.

### Initial event scope

The first implementation has only these useful event families:

| Event | Actions | Eligibility |
| --- | --- | --- |
| `pull_request` | `opened`, `synchronize`, `reopened` | Policy may request deterministic Observe or automated Review for an immutable PR head. |
| `issue_comment` | Applicable comment event | Only when the issue is a PR and the comment parses as an approved Watchdog command. |

`pull_request_review_comment`, `check_run`, `check_suite`, and `push` are
explicitly deferred. The Watchdog must not depend on all GitHub event families
to establish this initial boundary.

## Operation and authority classes

### Observe

Observe is deterministic GitHub/repository inspection. It needs no model and
does not mutate the repository. ADR-050-compatible inspection, PR lineage,
policy checks, and evidence classification remain in this class.

### Review

Review is model-backed analysis of exactly one immutable PR snapshot. It may
read PR metadata, the diff, and policy-permitted repository context; generate
findings; publish a GitHub Check Run; and publish bounded PR review comments.

It must not push commits, modify branches, merge, execute arbitrary repository
code, reveal provider/GitHub/production credentials to PR-controlled code, or
use PR content as instruction authority. Review remains advisory unless a
separate future decision gives a deterministic check explicit merge-gating
significance.

### Mutate

Mutate is entered only after an explicit authorized command and Guardian policy
decision. It may request a bounded coding task only through the existing
Guardian Build Loop and ADR-020 coding-agent contract. The GitHub webhook
handler never directly invokes a coding harness and never gains direct
filesystem, branch, or merge authority.

The future Mutate sequence is:

1. authenticate the GitHub delivery;
2. authorize the triggering actor;
3. resolve immutable installation, repository, PR, and `headSha` context;
4. resolve the configured model policy and independent adapter/harness policy;
5. create Guardian-owned execution lineage and a bounded coding-task envelope;
6. dispatch through the existing Guardian Build Loop;
7. preserve its validation, mutation-scope, optional worktree, artifact, and
   result-return controls; and
8. publish only bounded resulting status/evidence to GitHub.

An architecture-impacting or release-impacting fix still needs human review.
Neither a GitHub command, green model review, coding-worker completion, patch
artifact, nor Check Run authorizes merge or release.

## Command grammar and authorization

The first implementation reserves a small grammar shape, without canonizing
its final parser syntax:

```text
@watchdog review
@watchdog review --model <allowed-alias>
@watchdog fix
@watchdog rerun
```

The parser treats comments as untrusted data. It first proves that the comment
is on a PR, matches the approved grammar, and is made by a Guardian-authorized
actor for the requested operation. The `<allowed-alias>` is an input to a
Guardian-controlled alias/policy registry, not a raw provider/model value.
Arbitrary comment text is never passed to a provider/model resolver, an
adapter selector, shell, or coding harness.

The command creates an intent proposal, not direct worker authority. Guardian
resolves actor identity, operation, scope, approval state, and idempotency
before dispatch, consistent with the Intent Spine's no-second-universe rule.

## Provider-neutral model policy

### Policy classes and configuration scope

Model policy is provider-neutral and configuration-driven. It must represent
at least these classes:

- `automated_review`;
- `requested_review`;
- `fix`;
- `escalation`.

The future configuration shape supports system defaults plus
installation/account and repository scopes without code changes. A policy does
not alter current supported-profile provider authorization; actual provider
authorization, egress, credentials, availability, and capability checks remain
separate controls.

### Deterministic precedence

The selection chain is fixed:

1. authorized invocation override;
2. repository Watchdog policy;
3. installation/account Watchdog policy;
4. system Watchdog default.

An invocation override is allowed only when the command is authorized and its
alias resolves through the allowed policy registry. Guardian records the
override and selection source in the attempt. Prompt text, repository files,
PR metadata, comments, and model output never participate in this precedence
or select their own model.

### Immutable policy snapshot and economics

Before the model/harness executes, Guardian records an immutable attempt
snapshot containing at least:

| Field | Meaning |
| --- | --- |
| `policyId`, `policyVersion` | Exact resolved policy identity. |
| `providerId`, `modelId` | Selected inference identity. |
| `reasoningPosture` | Supported reasoning/inference posture when a provider exposes one. |
| `maxAttemptCount` | Bounded attempt ceiling. |
| `fallbackPolicy`, `escalationPolicy` | Allowed recovery and escalation behavior. |
| `modelSelectionSource` | Which precedence level selected the outcome. |
| `trigger` | Event or authorized command that requested the operation. |
| `repositoryScope` | Scope to which the policy was applied. |
| `adapterId` | Separate selected harness/adapter identity, when Mutate applies. |

**No silent expensive-model escalation.** The policy must be able to represent
a cheap routine model, stronger requested-review model, mutation/fix model,
optional expensive escalation model, and escalation-disabled posture. A
provider/model failure cannot automatically select an unrestricted premium
model. Fallback or escalation occurs only under an explicit configured rule or
an authorized human override.

For all fallbacks/escalations, preserve attempted provider/model identity and
final provider/model identity separately. Preserve trustworthy provider
usage/cost metadata where available; do not fabricate cost accounting for
providers that do not expose reliable data.

Provider/model selection is not adapter/harness selection. An adapter does not
receive authority because a model was selected, and a selected model is not an
adapter routing instruction.

## Delivery, attempt, and staleness semantics

### Idempotency

The delivery identity and the attempt identity solve different problems.

```text
delivery identity = GitHub delivery id + installation + repository + event + action
semantic event identity = normalized accepted event context for dedupe/audit
watchdog run identity = Guardian-generated logical Watchdog run
attempt identity = bounded execution attempt inside the Watchdog run
```

The durable delivery identity includes `githubDeliveryId` plus relevant
installation/repository/event context. Redelivery can refresh safe receipt
metadata, but a delivery already accepted must not create another semantic
event, model review, Check Run, or mutation dispatch. A human-authorized rerun
is a distinguishable new Watchdog run/attempt with explicit rerun provenance;
it is not a duplicate delivery.

### Immutable review snapshot and supersession

Every Review attempt binds to an immutable `headSha`. When a
`pull_request.synchronize` advances the head:

- queued old-head work is cancelled or marked superseded where cancellation is
  unavailable;
- running old-head work is marked stale/superseded if it cannot safely stop;
- stale output never becomes the current review truth for the new head;
- all inline findings carry the SHA they reviewed; and
- the current Check surface makes its reviewed SHA and stale/superseded
  condition legible.

Old findings are evidence about an old snapshot, not a claim about the current
PR state.

## Durable correlation vocabulary

Future durable Watchdog entities must be modelled as Postgres-owned evidence,
without prescribing a migration in this contract. They must carry at least:

| Field | Purpose |
| --- | --- |
| `githubDeliveryId` | GitHub delivery correlation, never a model-attempt ID. |
| `githubInstallationId`, `repositoryId` | App and repository scope. |
| `pullRequestNumber`, `headSha` | Immutable PR snapshot identity. |
| `watchdogRunId`, `attemptNumber` | Guardian-owned logical run and bounded attempt identity. |
| `triggerActorId`, `operation` | Actor and requested Observe/Review/Mutate class. |
| `policyId`, `policyVersion` | Resolved policy provenance. |
| `providerId`, `modelId` | Selected/attempted provider-model identity. |
| `status`, `supersededBy` | Lifecycle and stale/supersession relationship. |
| `guardianCodingRunId` | Guardian Build Loop correlation when Mutate is dispatched. |
| `githubCheckRunId`, `githubReviewId` | Published GitHub evidence identifiers after publication. |

The eventual data model may separate durable delivery receipts, semantic
events, Watchdog runs, model attempts, publication references, and Guardian
dispatch links. It must preserve their correlation rather than collapsing them
into a webhook log or Redis state.

## GitHub output and permissions

### Output contract

A GitHub Check Run tied to the reviewed SHA is the preferred canonical review
publication. It may carry queued/in-progress/completed state, overall summary,
conclusion, bounded annotations, reviewed SHA, Watchdog attempt identity,
operator-permitted model identity, and staleness/supersession state. Targeted
PR review comments may add bounded findings.

The Watchdog does not create one top-level comment for every receipt, retry,
or internal event, and it does not overwrite or impersonate human review
truth. Review output is advisory unless another accepted policy explicitly
makes a deterministic check merge-gating.

### Least privilege

Review-only Watchdog permission grants are limited to the repository/PR reads,
selected webhook subscriptions, Check writes, and bounded review/comment
writes needed for that operation. Contents write is not a review prerequisite.
No administration, secrets, workflows, branch mutation, merge, or repository
settings permission is granted by default. A future mutation path needs its
own separately authorized capability review.

## Trust boundaries and safety

PR contents, repository files, diffs, comments, model output, and retrieved
repository context are untrusted input. The Review path must not execute PR
code by default, expose production/provider/GitHub credentials to code from a
PR, allow a repository prompt to override Guardian policy, or turn model
instructions into authority.

Future untrusted-code validation is a separate sandbox decision; it cannot be
smuggled into review simply because a diff asks for tests. The primary threat
model includes malicious PRs/comments, compromised or over-broad GitHub App
configuration, honest-but-buggy policy/adapter providers, duplicate delivery,
stale execution, credential leakage, and an attempted bypass of human merge
review.

## Relationship to existing control planes

### Campaign Control Plane

ADR-050's deterministic proof/eligibility remains distinct from Watchdog
model analysis. A model opinion cannot overwrite deterministic failures, PR
lineage, required checks, protection rules, or human merge authority. The
Watchdog adds an event-adapter path for new operations; it does not duplicate
campaign packet or GitHub truth surfaces.

### Guardian Build Loop and Intent Spine

Mutate reuses the existing Guardian Build Loop and ADR-020 coding execution
contract. It carries GitHub context into Guardian lineage but creates no
parallel coding worker, adapter registry, queue, transcript store, or direct
webhook-to-harness route. The parsed command is a Guardian intent proposal and
must obey ADR-022 policy, approval, provenance, idempotency, dispatch, and
receipt rules.

### Connections and credential authority

Watchdog neither creates a second GitHub credential store nor silently moves
legacy GitHub credentials. GitHub installation/credential ownership must
ultimately align with the canonical Connections authority under ADR-071 when a
separately accepted migration implements that relationship. Until then,
Watchdog may reference only the existing governed GitHub authorization owner.
Catalog visibility, configuration, authorization, and health remain separate
truths.

### Tokens

Before runtime implementation spreads literals, define bounded canonical token
domains for Watchdog operation, run state, review conclusion, supersession
reason, model-selection source, and escalation reason. This docs-only slice
does not add runtime protocol tokens, storage enums, event names, or tests.

## Release and implementation boundary

This contract does not alter `00-current-state.md`, supported-profile claims,
or Beta posture. It accepts architecture only:

- webhook receipt is not model-review completion;
- model-review completion is not mutation completion;
- coding-worker completion is not merge approval; and
- GitHub publication is not live-runtime or release proof.

No GitHub App registration, webhook route, worker, Redis queue, Postgres
schema/migration, OAuth/install flow, credential, provider call, model call,
coding-worker dispatch, PR comment, Check Run, branch mutation, commit, push,
merge, auto-fix, auto-merge, Settings UI, Connections implementation,
provider-registry change, or runtime-token implementation is introduced here.

## First implementation prerequisite

Implement authenticated, idempotent GitHub App webhook intake with no model
execution. That slice must stop after signature verification, bounded event
normalization, durable receipt/idempotency handling, and prompt HTTP
acknowledgement; model review, Check publication, and Guardian coding dispatch
remain separately scoped work.
