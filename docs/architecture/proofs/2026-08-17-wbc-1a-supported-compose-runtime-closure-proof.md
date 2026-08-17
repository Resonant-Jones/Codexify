# WBC-1A — Supported Compose Runtime Closure Proof

## Result

**BLOCKED** — no eligible current-tip, local-only supported Compose project was
available for observation or for the required live chat lifecycle. The only
complete running project was the isolated Tester topology, whose mounted source
does not contain the WBC baseline and whose cloud-capable profile is explicitly
outside the default local-only supported posture. It was not used as a
substitute.

First blocking boundary: target runtime selection and source provenance. The
canonical collector could not obtain status for the selected
`codexify-audit` project, and the separately observed running Tester project
was mounted from a different, dirty source tree.

## Scope and authority

- WBC target baseline: `eb6bdc530245fdffeff23589c98389be4102b564`.
- Preflight fetch found `origin/main` still at that baseline; no post-G0
  origin drift was observed.
- Proof workspace at collection time:
  `08c9e8ae64bb4239a600e00beb5db041da1025b0`
  (`codex/freeze-workspace-baseline-truth`). This contains the frozen WBC-G0
  documentation above the target baseline, but the collector correctly
  reported it as provisional rather than canonical evidence authority.
- Machine/authority snapshot: machine id `local`, role
  `provisional_development_host`, authority basis `operator_not_asserted`;
  canonical-machine authority was not asserted.
- This is a bounded proof receipt, not release approval, a canonical manifest,
  a trusted latest pointer, or a runtime configuration change.

## Supported-profile and runtime preflight

The required WBC-1A posture is the default
`v1-local-core-web-mcp` Compose profile: local-only enabled, cloud providers
disabled, selected provider `local`, and a local Whoosh'd-compatible endpoint.
Its declared required services are `frontend`, `backend`, `db`, `redis`,
`worker-chat`, `worker-document-embed`, and `migrator`.

The selected canonical observation inputs were resolved from the checked-in
Compose name and collector contract, rather than inferred from a running
alternative project:

| Input | Resolved value |
| --- | --- |
| Compose file | `docker-compose.yml` |
| Selected project / role | `codexify-audit` / `audit` |
| Audit project | `codexify-audit` |
| Supported profile | `v1-local-core-web-mcp` |
| API / frontend loopback origins | `http://127.0.0.1:8888` / `http://127.0.0.1:5173` |
| Environment file | none supplied; no environment values were read by the collector |

The observed Docker project inventory contained only `codexify_tester` and
`codexify_private_preview`; there was no `codexify-audit` project. The
`codexify_private_preview` inventory exposed only Redis and was not a complete
supported Compose candidate.

The complete `codexify_tester` project was observed solely to rule out an
unsafe substitution:

- its configuration declares the isolated Tester overlay and
  `v1-whooshd-deepseek-web`, with cloud capability enabled and local-only mode
  disabled;
- its effective health posture reported `release_hold: true` because cloud
  capability was present;
- its local endpoint remained a local Docker-host endpoint (no credentials
  recorded), Redis remained an in-project Redis target, and persistence was a
  PostgreSQL-family target; and
- its configured local chat model was `gemma-4-12b-it-qat-4bit`, while the
  observed local inventory advertised `qwen3.8-27b-4bit`. Chat health therefore
  reported the configured-model-not-advertised condition.

These are diagnostic facts about the ineligible Tester runtime, not WBC-1A
completion evidence and not authorization to change its profile or model.

## Source-mount provenance gate

The running Tester backend was bound to `/Volumes/Dev_SSD/Codexify-main` for
`/app/guardian`, `/app/backend`, and `/app/config` (with the Docker Desktop
host-mount prefix on the first two paths). Its Compose labels also named that
external source root and the three Tester compose files.

At observation time that source tree was:

- `235cb159b6913d8cc4cba96e28e2c43acec85f86` on
  `codex/workspace-baseline-convergence`;
- dirty in its own pre-existing Tester OOM characterization proof artifact; and
- not a descendant of the WBC target baseline (`git merge-base --is-ancestor`
  for the target and this source returned nonzero).

Consequently, the running project cannot prove the target tip. No container
restart, profile switch, source remount, migration, model change, or cleanup
was attempted.

## Canonical collector receipt

The required collector was invoked read-only with the selected local-only
target inputs:

```text
make PYTHON=.venv/bin/python canonical-audit-live-proof-receipt \
  repo=. machine_id=local machine_role=provisional_development_host \
  authority_basis=operator_not_asserted compose_file=docker-compose.yml \
  compose_project=codexify-audit project_role=audit \
  audit_project=codexify-audit profile_name=v1-local-core-web-mcp \
  api_base=http://127.0.0.1:8888 frontend_base=http://127.0.0.1:5173 \
  command_timeout=10 http_timeout=5
```

The schema-valid receipt result was `BLOCKED`:

- receipt id:
  `live-proof-receipt-sha256-a7a7be1f0fa8ef517a63b9ea3d4af9ac3a1b32a369288337120ed6bffc28df88`;
- Docker client/server versions were both `29.7.2`;
- no service or HTTP probe was recorded, because Compose status was unavailable
  for the selected project; and
- normalized reason codes were `compose_status_unavailable`,
  `canonical_machine_authority_not_asserted`, `missing_upstream`,
  `wrong_branch`, and `git_command_failed`.

The receipt itself was schema-valid. Its `BLOCKED` outcome is not converted to
`FAIL`: no current-tip supported project reached live observation, and the
available Tester project failed the source/topology eligibility gate before a
WBC-1A lifecycle could begin.

## Runtime-chain evidence

The following required live milestones were not attempted after the target
runtime block. There is intentionally no fabricated thread, task, turn,
assistant-message, queue, Redis-key, or database identifier.

| Required milestone | WBC-1A evidence |
| --- | --- |
| Supported runtime identity and healthy required services | BLOCKED: `codexify-audit` status unavailable |
| Local model inventory | Not run on an eligible target runtime |
| Authored user message and completion acceptance | Not run |
| Redis enqueue, worker dequeue/running, and task events | Not run |
| Turn-lock acquire, duplicate rejection, and release | Not run |
| Local provider terminal completion and task terminal state | Not run |
| Assistant-message persistence, API source-thread readback, and PostgreSQL readback | Not run |

The Tester’s health observation is not a substitute for any row above. It
reported a fresh worker heartbeat and successful queue health subchecks, but
also an unhealthy chat surface caused by the local-model mismatch and a held
cloud-capable release posture.

## Static contract evidence

The following focused, current-worktree test command was run after the runtime
block as static contract evidence only:

```text
.venv/bin/python -m pytest -q \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/routes/test_chat_complete_enqueue_error_tagging.py \
  guardian/tests/test_chat_memory.py::test_chat_complete_turn_lock_blocks_parallel_requests \
  tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_denies_recovery_when_worker_fresh \
  tests/routes/test_chat_routes.py::TestChatCompletePost::test_complete_denies_recovery_on_unknown_terminal_state \
  tests/routes/test_health_endpoints.py::test_health_chat_surfaces_stale_worker_heartbeat \
  tests/routes/test_health_endpoints.py::test_health_chat_keeps_queue_round_trip_truth_with_fresh_heartbeat \
  tests/core/test_completion_terminal_integrity.py::test_persistence_gate_rejects_missing_or_incomplete_evidence \
  guardian/tests/workers/test_chat_worker_completion_semantics.py::test_generation_success_but_persistence_failure_is_non_authoritative \
  tests/test_chat_worker_turn_integrity.py
```

Result: 20 selected tests passed and one failed:

```text
guardian/tests/test_chat_memory.py::test_chat_complete_turn_lock_blocks_parallel_requests
```

The failing test still patches the old route-level `enqueue` seam and expected
one direct enqueue. The current route returned `200` with
`accepted_degraded`, but the patched list remained empty. This is a scoped
static-test failure, not a live duplicate-turn proof and not repaired in this
proof-only task. The remaining passing tests cover queue-failure rejection and
lock release, duplicate/in-flight handling, stale/unknown-lock fail-closed
behavior, degraded heartbeat and queue health, terminal gating before
persistence, and non-authoritative persistence failure.

## Validation and scope check

- `git fetch origin` completed before proof collection; `origin/main` remained
  at the WBC target baseline.
- `make tester-status` observed the existing Tester project without changing
  it; it is recorded only as an ineligible diagnostic runtime.
- The canonical machine/Git identity collector and the canonical live receipt
  collector both produced bounded, nonzero `BLOCKED` results as described
  above.
- The focused static test command failed as described above; no code or test
  repair was attempted.
- No live chat lifecycle, direct Redis operation, database query, migration,
  runtime start/stop, image build, provider invocation, or credential output
  occurred for WBC-1A.

## Non-goals honored and handoff

Only this proof artifact was added. No runtime code, Compose configuration,
environment file, ADR, current-state claim, WBC ledger, migration, profile,
model setting, or external runtime state was modified.

**WBC-1A BLOCKED — prerequisite resolution required before G1.** The next
authorized action must establish a clean current-tip local-only supported
Compose project with attributable source mounts; it must not reuse the
cloud-capable Tester topology as a release-proof substitute.

BLOCKED
