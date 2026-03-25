# Release Process

This project follows [Semantic Versioning](https://semver.org/).

## Recent Release Notes

### 2026-03-17 - Provider Governance Policy Synchronization

- Documented the canonical provider-governance map now enforced by the registry as the implementation source of truth.
- Recorded the current provider classifications exactly as implemented: `discovery_backed` (`alibaba`, `minimax`), `static_authorized` (`openai`, `groq`), `local_only` (`local`), and `disabled` (`anthropic`, `gemini`).
- Recorded that router-side discovery validation derives from registry policy instead of a duplicated router-local provider list.
- Synchronized release and architecture documentation with the current provider contract without changing runtime behavior.

### 2026-03-20 - Redis Chat Reliability Docs Alignment

- Updated architecture and release docs to match the current Redis-backed chat completion path.
- Documented Redis responsibilities in the chat lane: queue transport, turn locks, task-event streams, cancellation, worker heartbeat, turn-anchor cache, chat-embed queue, and health-probe/queue-depth observation.
- Clarified that `/health/chat` is a truthful but bounded surface: it combines Redis reachability, a bounded enqueue/dequeue probe, worker-heartbeat freshness, and sampled queue-depth heuristics.
- Clarified that queue-progress is heuristic, not dequeue proof.
- Documented evidence-based stale-turn-lock recovery and explicit fail-closed behavior when task-stream or heartbeat evidence is unknown.
- Documented task-event visibility degradation: publish failure is now surfaced to operators but does not itself prove task failure or UI receipt.
- Clarified route acceptance semantics: acceptance proves lock plus enqueue, while degraded acceptance means execution was accepted with weaker lifecycle visibility than normal.

## Versioning Guidelines
- Increment **MAJOR** for incompatible API changes.
- Increment **MINOR** for backward compatible functionality.
- Increment **PATCH** for backward compatible bug fixes.

## Steps to Cut a Release
1. Update version numbers in `pyproject.toml`, `setup.py`, and `CHANGELOG.md`.
2. Commit changelog entries for the new version.
3. Tag the commit with the version number, e.g. `v0.1.0`.
4. Push the tag and create a GitHub Release using the tag.
5. Attach built distributions to the release if applicable.

## Security Rewrite Gate (Mandatory for Beta)
1. If history was rewritten for secret remediation, force-push all rewritten refs:
   - `git push --force --all origin`
   - `git push --force --tags origin`
2. Create `SECURITY-REWRITE-NOTICE.md` as a normal post-rewrite commit on default branch.
3. Ensure the notice includes:
   - Rewrite date (UTC ISO-8601)
   - Pre-rewrite baseline hash
   - Post-rewrite default-branch hash
   - Statement that branches and tags were rewritten
   - Required re-clone/reset commands
   - CI/cache invalidation reminder
4. Block release until verification gate passes:
   - `pre-commit run --all-files`
   - `gitleaks dir . --exit-code 1`
   - `gitleaks git . --log-opts="--all" --exit-code 1`

## Beta Readiness Gate (Current State: 2026-03-17)

- Provider governance is an explicit release gate. `guardian/core/provider_registry.py` is the canonical source of truth for provider authorization, availability, and capability decisions consumed by catalog, health, router, and worker code. Beta claims should match that registry-backed behavior and the active supported-profile contract, not just environment intent.
- Operator confidence is still backend-first. The required evidence pack for beta decisions is `GET /health`, `GET /health/llm`, `GET /health/chat`, `GET /api/llm/catalog`, backend/worker logs, and `/metrics`. This is the current shipped path for release validation.
- The Command Center / Observability Deck is not a released end-user beta surface. Partial operator-facing UI work and internal routes may exist in the repo, but they should be treated as internal or dev-only until they are documented as part of the supported release surface.
- Internal routes are release caveats, not product proof. In the current supported profile, `command_bus` is explicitly internal-only, and internal/operator-facing routes should not be used as evidence that a general user-facing operator console has shipped.
- Green boot is not enough for beta confidence. Release confidence depends on accurate alignment between the supported profile, provider registry decisions, catalog output, and live health behavior. If health reads green while the runtime profile, provider posture, or catalog truth is drifting, the release read remains internal-only.
- As of 2026-03-17, the runtime audit posture is still limited internal validation only. Use `docs/release/run/2026-03-17-runtime-stability-audit.md` as the current release-read anchor when deciding whether beta promotion is justified.

## Operator Truth Surfaces (Current Runtime)

### `GET /health`

- What it proves:
  - the backend process is up and serving the base health route
  - supported-profile state may be attached if the app has it in process state
- What it does not prove:
  - Redis is reachable
  - the chat worker is alive
  - the active LLM path is reachable
  - the queue-backed completion lane can finish work

### `GET /health/chat`

- What it checks:
  - Redis `PING`
  - a bounded queue round-trip probe using an ephemeral healthcheck queue
  - chat-worker heartbeat presence and age
  - sampled queue depth on `codexify:queue:chat`
- Status meanings:
  - `healthy`
    - Redis is reachable
    - the probe queue round-trip succeeded
    - worker heartbeat is `fresh`
    - queue is either empty or backlog depth is decreasing between recent samples
  - `degraded`
    - some chat truth is present, but not enough for clean confidence
    - examples:
      - worker heartbeat `stale`
      - queue depth unavailable
      - backlog observed but progress not yet established
      - backlog not progressing but not yet in the high-depth unhealthy band
  - `unhealthy`
    - Redis is unreachable, queue probe failed, worker heartbeat is dead/missing, or backlog is high and not progressing
- Worker meanings:
  - `fresh`
    - heartbeat seen and age `<= 10s`
  - `stale`
    - heartbeat seen and age `> 10s` and `<= 60s`
  - `dead`
    - no heartbeat, unparsable/undated heartbeat, or age `> 60s`
- Queue meanings:
  - `progressing`
    - queue is empty, or sampled depth decreased since the previous recent sample
  - `stalled`
    - sampled depth is flat or growing across the recent sample window
  - `unknown`
    - not enough sample history, stale sample state, or queue depth unavailable
- What `/health/chat` does not prove:
  - that a particular queued task has been dequeued
  - that the worker finished a task successfully
  - that task events were received by the UI
  - that the current provider call will succeed

### `GET /api/health/llm` and `GET /health/llm`

- Local-provider mode:
  - actively probes the configured local runtime endpoint and reports `online`, `offline`, or `misconfigured`
- Cloud-provider mode:
  - reports configured runtime posture and provider-registry capability state
  - current status is intentionally `unknown` / `runtime_unprobed` rather than pretending active cloud reachability proof
- What it does not prove:
  - the Redis-backed chat lane is healthy
  - a queued completion will finish
  - the supported-profile contract is satisfied on its own

### Task-event inspection and logs

- Task events:
  - inspect `/api/tasks/{task_id}/events` to see lifecycle breadcrumbs when publication succeeds
  - strongest lifecycle signals are `task.running`, `task.completed`, `task.failed`, and `task.cancelled`
- Logs:
  - backend and `worker-chat` logs are required when task-event visibility degrades or when queue health and provider health disagree
- Visibility-degradation interpretation:
  - progress-event publish failure means execution may still continue but live progress insight is weaker
  - terminal-event publish failure is more serious because terminal observability is degraded
  - neither case proves the UI received or rendered anything

## Acceptance and Degraded States

### `accepted`

- Use this to mean:
  - the route acquired the per-thread turn lock
  - the route enqueued the completion task successfully
- It does not mean:
  - the worker has already started
  - the completion will succeed
  - the UI will see every event

### `accepted_degraded`

- Use this to mean:
  - execution was accepted into the queue-backed path
  - but lifecycle visibility is weaker than normal
- Current concrete example:
  - enqueue succeeded but the route could not publish the `task.created` breadcrumb
- Important constraint:
  - current code does not emit a literal `accepted_degraded` response field
  - operators should interpret it as an operational distinction, not a new guaranteed wire contract

## Stale-Lock Recovery Guidance

- Recovery is allowed only when one of these is true:
  - the old task stream has a terminal event
  - the old task stream is nonterminal and the worker heartbeat is `stale`, `dead`, or `missing`
- Recovery is denied when:
  - task-stream state is `unknown`
  - heartbeat evidence is `unknown`
  - the lock is only old by TTL but evidence is ambiguous
- Operator interpretation:
  - denied recovery on ambiguous evidence is expected fail-closed behavior
  - do not treat it as a bug by itself; inspect task events, worker heartbeat, and worker logs together

## Practical Operator Guidance

1. Start with `GET /health`.
   - If this is down, the backend process itself is unavailable.
2. Check `GET /health/chat`.
   - If `unhealthy`, assume the queue-backed completion path is not trustworthy until Redis/worker state is explained.
   - If `degraded`, read the `notes`, worker status, and queue status before assuming impact severity.
3. Check `GET /api/health/llm`.
   - Use this to separate provider/runtime posture from queue/worker posture.
4. Inspect task events for a specific `task_id`.
   - `task.running` means the worker reached observable execution.
   - `task.completed` / `task.failed` / `task.cancelled` are strongest terminal breadcrumbs when present.
5. Inspect backend and `worker-chat` logs.
   - Required when task events are missing, when `task_event_visibility_degraded` appears, or when route acceptance and task outcome disagree.

Interpret degraded states conservatively:

- `worker=stale` means completion may still be working, but the liveness signal is old enough that operators should not claim the lane is healthy.
- `queue=progressing` means sampled backlog appears to be draining; it is not proof of dequeue for a specific task.
- `queue=stalled` means sampled backlog is not shrinking; it suggests risk, not mathematical proof of a stuck worker.
- `accepted` means the queue-backed lane took the task.
- `accepted_degraded` means the task was accepted but lifecycle visibility is weaker than normal.

### Beta Go / Hold Checklist

Status legend:
- `ready`: documented and supported by the current repo evidence
- `partial`: partly supported, but not enough for beta signoff alone
- `hold`: current repo evidence says beta should not be called ready
- `needs operator validation`: still requires manual multi-surface confirmation

- `[ready]` Provider governance policy is explicit and documented. `guardian/core/provider_registry.py` is the canonical governance source, and the current supported beta contract is documented in `config/supported_profiles/v1-local-core-web-mcp.yaml`.
- `[ready]` Provider registry, supported profile, catalog, and health alignment is an explicit release requirement. The docs already state that none of those surfaces is sufficient alone, and beta claims must match registry-backed runtime truth rather than environment intent.
- `[ready]` Current internal observability status is accurately described. The shipped evidence pack is backend-first: `GET /health`, `GET /health/llm`, `GET /health/chat`, `GET /api/llm/catalog`, backend/worker logs, and `/metrics`.
- `[ready]` Command Center / Observability Deck remains internal or dev-only, not a released beta operator surface. Partial operator UI in the repo is still a release caveat, not proof of a shipped operator console.
- `[partial]` Release confidence is stronger for backend/runtime correctness than for live operator inspectability. The March 17 runtime audit shows strong deterministic test slices and useful live health signals, but diagnosis still depends on stitched backend evidence rather than an integrated operator surface.
- `[hold]` The live Compose beta runtime currently honors the supported-profile contract end to end. The March 17 runtime audit says it does not: Compose still boots with `CODEXIFY_BETA_CORE_ONLY=false`, cloud providers enabled, and non-core routes mounted.
- `[hold]` Provider registry decisions, catalog output, and live health are currently proven aligned on the running supported path. The March 17 runtime audit says they are not yet trustworthy enough for promotion, because health can read green while the supported-profile contract is still invalid.
- `[hold]` Fresh live supported-path evidence exists in the current audit window for assistant completion plus upload -> embed -> retrieve. The March 17 runtime audit says that proof was not refreshed because smoke aborted at the profile gate before the happy-path checks completed.
- `[needs operator validation]` A beta signoff can be made from shipped operator surfaces alone. Current docs say no: operators still need endpoints, logs, metrics, and sometimes direct Compose/container inspection to explain runtime truth.

Current decision as of 2026-03-17: `hold`.
The repo supports a stronger claim for backend/runtime stabilization than for beta promotion. The current blocker set is the supported-profile contract drift plus the missing fresh live supported-path proof in the same audit window.

### Beta Go / Hold Decision Rubric

- `Go` only when the supported-profile contract is active at runtime, quarantined/internal-only routes are not exposed on the supported beta surface, provider registry posture agrees with catalog and health, and the current audit window includes fresh live proof for assistant completion plus upload -> embed -> retrieve.
- `Hold` whenever runtime flags drift from the supported profile, green health masks contract drift, non-core routes remain mounted on the supposed beta surface, or the current audit window lacks fresh supported-path evidence.
- `Tolerable beta limitations` include operating without a shipped Command Center / Observability Deck, using backend endpoints/logs/metrics as the primary operator workflow, and treating RAG trace as a dev-only debugging aid rather than durable release proof.
- `Release blockers` are issues that invalidate release truth itself: the running stack does not honor the documented supported profile, provider policy/catalog/health disagree on the supported posture, or live supported-path happy-path evidence is missing or stale.
