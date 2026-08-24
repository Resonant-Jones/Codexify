# GitHub Watchdog Control Plane

## Status and scope

This is the accepted architecture contract for the Guardian-owned GitHub
Watchdog under [ADR-073](./adr/073-github-watchdog-review-and-dispatch-control-plane.md).
The implemented preparation boundary provides exact raw-body HMAC
authentication, normalized bounded metadata, durable Postgres delivery
receipt/idempotency handling, and one receipt-bound automatic review attempt
for each accepted automatic PR-review delivery. Each attempt binds the receipt
head SHA to an immutable system-default policy snapshot and initially records
either `prepared` or a bounded policy block. A newer
`pull_request.synchronize` head supersedes older prepared or running attempts
for the same repository and PR.

Repository and installation/account policy persistence, invocation overrides,
comment-command parsing, automatic webhook-to-capture/dispatch orchestration,
GitHub Check Runs or PR review comments, Build Loop mutation dispatch, auto-fix,
and merge authority remain deferred.

The Watchdog extends rather than replaces [ADR-050](./adr/050-event-driven-campaign-control-plane.md).
ADR-050 remains the GitHub-native deterministic, read-only, dry-run Campaign
Control Plane. The Watchdog adds a future model-backed advisory review and
explicit Guardian mutation-dispatch boundary; it does not make model opinion
deterministic eligibility, merge authorization, or release truth.

`docs/architecture/00-current-state.md` remains authoritative for current
release reality. This preparation boundary is not a supported Watchdog workflow
or a release claim.

## Implemented installation-auth read boundary

Guardian now has a narrowly scoped GitHub App authentication primitive: it
creates a short-lived RS256 App JWT from server-side Watchdog configuration,
exchanges it for an ephemeral installation token, and exposes a read-only
client that retrieves bounded PR metadata and validates the immutable expected
`headSha`. The webhook HMAC secret and App private key remain separate
credentials. App JWTs and installation tokens are never persisted, logged, or
returned through a route.

This is an operator-configured bridge, not a second Connections credential
truth. It honors the existing egress gate and exposes no GitHub write methods.
It is not invoked from webhook intake or the captured-review execution service.

The client itself remains uncoupled from runtime invocation, queues, model
execution, GitHub Check publication, PR comments or reviews, and Build Loop
mutation dispatch.

## Implemented immutable review-input snapshots

A callable Watchdog service can now capture one bounded, immutable PR
review-input snapshot for an eligible `prepared`, policy-resolved
`automated_review` attempt. It reads PR metadata before and after paginated
GitHub App changed-file retrieval; the initial live head must equal the
attempt's immutable `headSha`, and the post-read head and base SHA must match
the pre-read source identity. A stale head or source change produces a terminal
`blocked_stale` record, never a mixed-state captured snapshot.

Captured snapshots include normalized PR title/body, base/head identity,
author/draft metadata, normalized changed-file metadata and available patches,
aggregate change counts, and a deterministic SHA-256 digest of the canonical
review input. Files are canonically sorted by filename then previous filename.
Missing GitHub patches remain `null`; they are counted rather than fabricated.

The model-neutral v1 capture limits are 300 changed files and 1,000,000 UTF-8
patch bytes. Exceeding either produces a terminal `blocked_limits` record with
bounded observed facts and no silently truncated captured content. Postgres
enforces one terminal snapshot record per review attempt; repeated callers
converge on that immutable record.

Still deferred: automatic webhook-to-capture/dispatch orchestration, GitHub
Check publication, PR comments or reviews, command parsing, Build Loop
dispatch, mutation, and merge authority. No snapshot capture is wired into
webhook intake.

## Implemented captured-review execution

A separate callable service can now execute one eligible captured review attempt
without entering the ordinary chat-completion service. It first commits the
single Postgres-backed result claim and changes the attempt from `prepared` to
`running`; only then can it invoke the canonical `chat_with_ai` inference
boundary. A unique result row per attempt prevents a concurrent caller from
spending inference and returns the already-durable execution state instead. If
a process dies after that claim, the durable `running` state is deliberately
left unrecovered: automatic reclaim/retry could double-spend an uncertain
upstream invocation and is deferred.

The executor consumes only the captured snapshot and the attempt's immutable
provider, model, and inference-mode policy snapshot. Before inference it
re-enforces current provider governance, local-only, cloud-enable, credential,
and canonical egress controls. A newly disallowed choice becomes
`blocked_runtime_policy`; it is not rerouted, retried, escalated, or replaced
with an ambient chat model. The strict router invocation preserves the exact
provider/model, sends no tools, uses temperature zero, and sets a 4096-token
output ceiling. No fallback, repair call, second model, or escalation model is
used.

`github-watchdog-review-v1` deterministically binds the immutable snapshot ID
and digest, review operation, and v1 review schema into the exact submitted
messages. The system instruction treats PR title/body, filenames, patches, and
code as untrusted evidence rather than instructions; snapshot content appears
only in the user/evidence message. The result stores the prompt version/digest,
snapshot digest, requested and invoked provider/model, inference mode, bounded
raw-output digest/byte count, trustworthy provider usage/request metadata when
available, and a strict provider-neutral JSON result when valid. Raw output is
limited to 131072 UTF-8 bytes; oversized or malformed responses terminally
become `failed_output_contract` without a repair call.

The v1 result has only `no_findings` or `findings` assessments, up to 50
bounded findings, canonical severity/category values, nullable positive line
numbers, confidence from 0.0 through 1.0, and file paths limited to files in
the captured snapshot. No GitHub approval/request-changes or publication token
exists in this result contract.

Newer `pull_request.synchronize` receipts can now supersede both `prepared`
and `running` older attempts. The executor does not cancel upstream HTTP. If a
running model call returns after supersession, it stores the response evidence
as `discarded_superseded`, preserves the attempt's `superseded` state, and
makes the result permanently non-current for any future publication path.

Still deferred: automatic webhook-to-capture/dispatch orchestration,
stale-running recovery, retry/rerun, escalation execution, GitHub Check
publication, PR review/comment publication, command parsing, Build Loop
dispatch, mutation, and merge authority. Nothing in this callable seam
publishes to GitHub.

## Implemented durable dispatch and dedicated worker

An explicit caller may now dispatch one eligible, already-captured review
attempt. The dispatcher first locks and revalidates the immutable attempt and
captured snapshot, creates the unique Postgres dispatch record in
`pending_enqueue`, and commits it before attempting Redis. The durable record
binds the attempt, snapshot ID/digest, reviewed head SHA, queue task ID,
enqueue count, worker provenance, lifecycle, terminal error, and review-result
correlation. It never copies a prompt, PR body/patch, provider credential, or
review findings.

Redis is transport only. Its `github_watchdog_review` envelope contains just a
queue task ID, dispatch ID, attempt ID, and creation timestamp. A successful
enqueue changes the durable record to `queued`; a failure remains visible as
`enqueue_failed` with a bounded error code and leaves the review attempt
`prepared`. `queued` proves only Redis accepted the envelope. It does not prove
dequeue, model execution, result persistence, or GitHub publication. Redis
loss cannot erase the durable Postgres dispatch record.

The opt-in `worker-watchdog-review` Compose profile consumes only that queue.
It treats every Redis field as untrusted transport input, reloads and locks the
canonical Postgres record, verifies envelope/dispatch/attempt identity, then
changes a valid `queued` dispatch to `running` before calling the existing
`GitHubWatchdogReviewExecutionService`. The review model remains the sole
author of review findings and assessment; the worker never authors or rewrites
them. The executor remains the sole model-execution and result-persistence
boundary, and its unique Postgres result claim is the final
duplicate-inference-spend guard. Duplicate delivery therefore makes at most one
model call and one result.

Completed, runtime-blocked, provider/output failure, and superseded execution
results map to `completed`, `blocked`, `failed`, and `discarded_superseded`
dispatch truth respectively, with the result ID retained separately from
structured findings. Supersession before dequeue makes no model call; if it
arrives during execution, the existing executor returns discarded evidence and
the worker mirrors that state. A process interruption after dispatch claim
leaves durable `running` state. There is deliberately no automatic retry,
replay, stale-running reclaim, dead-letter path, or model fallback.

The worker performs no GitHub read or write, snapshot capture, webhook wiring,
Command Bus call, coding-worker dispatch, Build Loop invocation, mutation, or
publication. Webhook intake still ends after receipt and attempt preparation;
capture and dispatch remain separate explicit calls.

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
| Postgres | Durable receipts, attempts, snapshots, dispatch lineage, correlations, and results. | Ephemeral queue coordination. |
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

- older `prepared` or `running` automatic-review attempts for that repository and PR are
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

`github_watchdog_review_input_snapshots` is a distinct Postgres-owned terminal
evidence entity with one unique row per review attempt. It records capture
state, expected/observed source identity, base identity, normalized bounded PR
input, aggregate facts, missing-patch count, and a captured-only digest. It
never stores GitHub credentials, model prompts, or model output.

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

The implemented slices define bounded intake, GitHub App, review-input capture,
review-execution/result, and dispatch/worker error codes; event/action tuples;
Watchdog operation, attempt, snapshot-capture, review-result, dispatch-state,
policy-resolution, model-selection-source, escalation-mode, and policy-block
vocabularies. The dedicated queue task type is `github_watchdog_review`.
Publication and worker-retry tokens remain deferred until their owning runtime
slices exist.

## Release and implementation boundary

This contract does not alter `00-current-state.md`, supported-profile claims,
or Beta posture. The implemented boundary is limited to HMAC verification,
bounded metadata normalization, durable Postgres receipt/idempotency, local
policy evaluation, GitHub App read authentication, callable immutable
review-input capture, callable one-attempt model review/result persistence, and
an opt-in Postgres-first dispatch/worker seam. It does not establish automatic
dispatch or publication behavior:

- webhook receipt is not model-review completion;
- model-review completion is not mutation completion;
- coding-worker completion is not merge approval; and
- GitHub publication is not live-runtime or release proof.

No GitHub App registration, default-topology worker, OAuth/install flow,
credential storage, coding-worker dispatch, PR comment, Check Run, branch
mutation, commit, push, merge, auto-fix,
auto-merge, Settings UI, Connections implementation, or provider-registry
change is introduced by this slice.

## Current implementation boundary

The webhook path still ends after an authenticated automatic PR webhook has a
durable receipt and one durable review attempt with a resolved or blocked
immutable policy snapshot. Separately, a caller may capture a complete bounded
review-input snapshot, explicitly dispatch it, and allow the opt-in worker to
call the one-attempt execution service. Neither capture nor dispatch is wired
to webhook intake. `prepared` means policy resolved and a durable attempt
exists; it does not mean queued or dispatched. A successful explicit execution
is advisory evidence, not GitHub publication, mutation, merge approval,
live-runtime proof, or release support.
