# GitHub Watchdog Control Plane

## Status and scope

This is the accepted architecture contract for the Guardian-owned GitHub
Watchdog under [ADR-073](./adr/073-github-watchdog-review-and-dispatch-control-plane.md).
The implemented preparation boundary provides exact raw-body HMAC
authentication, normalized bounded metadata, durable Postgres delivery
receipt/idempotency handling, and one receipt-bound automatic review attempt
for each accepted automatic PR-review delivery. Each attempt binds the receipt
head SHA to an immutable system-default policy snapshot and records either
`prepared` or a bounded policy block. A newer `pull_request.synchronize` head
supersedes older prepared attempts for the same repository and PR.

Repository and installation/account policy persistence, invocation overrides,
comment-command parsing, model invocation, Redis queueing, model-response
parsing, GitHub Check Runs or PR review comments, Build Loop mutation dispatch,
auto-fix, and merge authority remain deferred.

The Watchdog extends rather than replaces [ADR-050](./adr/050-event-driven-campaign-control-plane.md).
ADR-050 remains the GitHub-native deterministic, read-only, dry-run Campaign
Control Plane. The Watchdog adds a future model-backed advisory review and
explicit Guardian mutation-dispatch boundary; it does not make model opinion
deterministic eligibility, merge authorization, or release truth.

`docs/architecture/00-current-state.md` remains authoritative for current
release reality. This preparation boundary is not a supported Watchdog workflow
or a release claim.

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
| `pull_request` | `opened`, `synchronize`, `reopened` | Creates one automatic-review attempt for an immutable PR head, with a policy snapshot or a durable policy block. |
| `issue_comment` | `created` | The receipt boundary accepts only comments attached to a PR. It creates no review attempt, does not inspect comment text, and does not parse commands. |

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

Model policy is provider-neutral and configuration-driven. The canonical
operation classes are:

- `automated_review`;
- `requested_review`;
- `fix`;
- `escalation`.

Only `automated_review` has a runtime trigger in this slice. Its only active
selection source is the operator-configured system default. `requested_review`,
`fix`, and `escalation` have no runtime trigger. Repository and
installation/account scopes are deferred; their absence does not alter the
eventual precedence. A policy does not alter current supported-profile provider
authorization; canonical provider governance and the existing local/cloud and
egress controls remain separate, stricter authorities.

### Deterministic precedence

The selection chain is fixed:

1. authorized invocation override;
2. repository Watchdog policy;
3. installation/account Watchdog policy;
4. system Watchdog default.

This implementation resolves only level 4 as `system_default`. The other
levels are deferred, not treated as absent or collapsed. Prompt text,
repository files, PR metadata, comments, and model output never participate in
this precedence or select their own model.

### Immutable policy snapshot and economics

Before any future model/harness execution, this implementation records an
immutable attempt snapshot containing:

| Field | Meaning |
| --- | --- |
| `policyFingerprint` | Deterministic fingerprint of the normalized operation, provider, model, inference mode, escalation posture, and selection source. |
| `providerId`, `modelId` | Selected inference identity. |
| `inferenceMode` | Optional configured inference/reasoning posture. |
| `modelSelectionSource` | Which precedence level selected the outcome. |
| `escalationMode`, `escalationProviderId`, `escalationModelId` | Inert `disabled` or explicitly configured `explicit_only` posture. |
| `policyResolutionState`, `policyReasonCode` | The resolved or blocked decision and bounded reason when blocked. |

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

The delivery identity and attempt identity solve different problems.

```text
delivery identity = GitHub delivery id + installation + repository + event + action
delivery receipt identity = durable receipt of one accepted delivery
attempt identity = distinct Guardian-generated review-attempt identity
```

The durable delivery identity includes `githubDeliveryId` plus relevant
installation/repository/event context. A database uniqueness boundary on the
attempt's `triggerReceiptId` makes webhook redelivery reuse the same attempt.
Distinct legitimate deliveries, including an `opened` and later `reopened`
event for the same head, remain distinct attempts. A future human-authorized
rerun will need its own deliberate provenance and attempt numbering; it is not
implemented here.

### Immutable review snapshot and supersession

Every prepared automatic-review attempt binds to an immutable `headSha`. An
accepted automatic PR event missing its head SHA persists a `blocked_policy`
attempt rather than a runnable-looking attempt. When a
`pull_request.synchronize` provides a newer head:

- older `prepared` automatic-review attempts for that repository and PR are
  marked `superseded` and point to the new attempt;
- their original policy snapshots remain unchanged; and
- blocked-policy history is preserved rather than rewritten.

No work is queued, running, or published in this slice. Future execution and
publication must preserve this stale-head relationship.

## Durable correlation vocabulary

The implemented `github_watchdog_review_attempts` entity is Postgres-owned
evidence bound to `github_watchdog_delivery_receipts`. It carries:

| Field | Purpose |
| --- | --- |
| `reviewAttemptId`, `triggerReceiptId` | Distinct attempt identity and unique FK back to its triggering receipt. |
| `githubDeliveryId` | GitHub delivery correlation, never the attempt ID. |
| `githubInstallationId`, `repositoryId` | App and repository scope. |
| `pullRequestNumber`, `headSha` | Immutable PR snapshot identity. |
| `operation`, `attemptNumber`, `attemptState` | This slice's automatic-review operation and lifecycle evidence. |
| `policyResolutionState`, `policyReasonCode`, `policyFingerprint` | Immutable policy decision evidence. |
| `providerId`, `modelId`, `inferenceMode`, `modelSelectionSource` | Immutable selected model-policy identity. |
| `escalationMode`, `escalationProviderId`, `escalationModelId` | Inert escalation configuration, if explicitly present. |
| `supersededByAttemptId` | Immutable-head stale/supersession relationship. |

Future durable Watchdog runs, result records, publication references, and
Guardian dispatch links must preserve their correlation rather than collapsing
them into a webhook log or Redis state.

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

The preparation slice defines bounded intake error codes and event/action
tuples; Watchdog operation, attempt state, policy-resolution state,
model-selection source, escalation mode, and policy-block reasons. Execution,
review conclusion, publication, and retry tokens remain deferred until their
owning runtime slices exist.

## Release and implementation boundary

This contract does not alter `00-current-state.md`, supported-profile claims,
or Beta posture. The implemented preparation is limited to HMAC verification,
bounded metadata normalization, durable Postgres receipt/idempotency, local
policy evaluation, and durable policy snapshots. It does not establish any
downstream control-plane behavior:

- webhook receipt is not model-review completion;
- model-review completion is not mutation completion;
- coding-worker completion is not merge approval; and
- GitHub publication is not live-runtime or release proof.

No GitHub App registration, worker, Redis queue, OAuth/install flow,
credential issuance, provider call, model call, coding-worker dispatch, PR
comment, Check Run, branch mutation, commit, push, merge, auto-fix,
auto-merge, Settings UI, Connections implementation, or provider-registry
change is introduced by this slice.

## Current implementation boundary

The current path ends after an authenticated automatic PR webhook has a durable
receipt and one durable review attempt with a resolved or blocked immutable
policy snapshot. `prepared` means policy resolved and durable attempt exists;
it does not mean queued, dispatched, running, reviewed, or published. No model
or provider API is invoked.
