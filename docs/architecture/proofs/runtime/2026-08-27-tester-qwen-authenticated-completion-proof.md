# Authenticated Tester Qwen completion proof

**Result:** `TESTER_QWEN_BACKEND_UNHEALTHY`

**ADR impact:** Aligned with ADR-074, ADR-051, ADR-001, ADR-003, the existing
chat-runtime contract, and the queue/worker persistence contracts; no ADR
change.

## Scope and stop condition

This task was authorized to prove one ordinary authenticated Tester turn using
the normal default provider/model authority. The proof stopped at the first
execution gate because the isolated `codexify_tester` runtime was not present.
No service was started or repaired, and no authenticated or durable chat
operation was attempted.

The bounded preflight window was:

```text
PROOF_WINDOW_START_UTC=2026-08-27T16:34:49Z
PROOF_WINDOW_END_UTC=2026-08-27T16:35:53Z
```

The causal blocker is:

```text
TESTER_QWEN_BACKEND_UNHEALTHY
```

The canonical Tester status surface reported `desired_state=disabled`, no
required `codexify_tester` containers, failed health checks for
`http://127.0.0.1:8889/health` and `/health/chat`, and
`tester_status=degraded`. The expected backend therefore cannot be used for
authentication, thread creation, message persistence, queue acceptance, or
completion proof.

## Repository and prerequisite gate

Codexify task checkout:

```text
root: /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 177c5390ced954e8dd879f99f166e86966dbe706
status: clean; ahead 5 of origin/codex/diagnose-tester-fresh-chroma-failure
```

The required prerequisite was verified before preflight:

```text
git cat-file -e 177c5390ced954e8dd879f99f166e86966dbe706^{commit}: PASS
git merge-base --is-ancestor 177c5390ced954e8dd879f99f166e86966dbe706 HEAD: PASS
```

The unrelated Watchdog worker file and `docs/architecture/00-current-state.md`
were not changed.

## Active Tester source and runtime identity

The configured Tester source root is `/Volumes/Dev_SSD/Codexify-main`.
Read-only source identity was:

```text
remote: https://github.com/Resonant-Jones/Codexify.git
branch: main
HEAD: 1c597042e314a9a409ddd384225a2cbb723f7528
status: main...origin/main [ahead 3, behind 17]
pre-existing dirty paths: one deleted daily log, one modified proof, one
untracked Google Drive proof
```

Those source changes were preserved. The machine-local `.env.tester` exists
with mode `0600`; its contents were not read, printed, or changed. The Tester
desired-up marker is absent:

```text
/Users/chriscastillo/Library/Application Support/Codexify/tester/enabled: absent
```

The canonical read-only status command was run from that active source:

```text
bash scripts/ops/codexify_tester.sh status
```

It identified project `codexify_tester` and reported every required service as
missing: `db`, `neo4j`, `backend`, `redis`, `frontend`, `worker-chat`,
`worker-chat-embed`, `worker-document-embed`, `worker-warmup`,
`worker-account-import`, and `tailscale-codexify-test`.

The Docker label query returned no `codexify_tester` containers. No process was
listening on `127.0.0.1:8889`, and both Tester health requests failed with
connection error. A separate standard Compose stack is listening on `8888`,
but it is not the Tester runtime: its live `/health` response identifies the
`v1-local-core-web-mcp` profile rather than `v1-whooshd-deepseek-web`.

## Execution gates not reached

Because the Tester backend is absent, the following gates were not entered:

- authenticated Tester identity acquisition;
- fresh proof-thread creation;
- user-message persistence and API readback;
- one completion acceptance and task ID;
- worker execution and terminal task event;
- Whoosh'd generation attribution;
- assistant persistence and API/PostgreSQL transcript agreement;
- turn-lock release and queue drain.

No credentials, sessions, thread IDs, message IDs, task IDs, request IDs, or
sentinels were created. There was no reason to invoke the authentication
mechanism, and `TESTER_QWEN_AUTH_UNAVAILABLE` is not the causal classification:
the earlier runtime gate failed first.

## Execution and persistence boundary

No durable proof turn was attempted:

```text
PROOF_THREADS_CREATED=0
PROOF_USER_MESSAGES_CREATED=0
COMPLETION_REQUESTS_SUBMITTED=0
ATTEMPT_COUNT=0
MODEL_INVOCATIONS_DURING_QWEN_COMPLETION_PROOF=0
DEEPSEEK_REQUESTS_DURING_QWEN_COMPLETION_PROOF=0
TOOL_TURNS_DURING_QWEN_COMPLETION_PROOF=0
COMMAND_BUS_INVOCATIONS_DURING_QWEN_COMPLETION_PROOF=0
WATCHDOG_ACTIVITY_DURING_QWEN_COMPLETION_PROOF=0
GITHUB_IO_DURING_QWEN_COMPLETION_PROOF=0
POSTGRES_MUTATIONS_DURING_QWEN_COMPLETION_PROOF=0
REDIS_MUTATIONS_DURING_QWEN_COMPLETION_PROOF=0
CHROMA_MUTATIONS_DURING_QWEN_COMPLETION_PROOF=0
SERVICE_LIFECYCLE_ACTIONS_DURING_QWEN_COMPLETION_PROOF=0
```

No PostgreSQL or Redis writes were performed. No Whoosh'd, backend,
`worker-chat`, Redis, Postgres, Neo4j, or frontend lifecycle command was
issued. Whoosh'd was not restarted or repaired, and no provider/model,
registry, artifact, `.env.tester`, Compose, source, Watchdog, or release-truth
file was changed.

## Validation

Read-only and documentation checks performed:

```text
git status --short --branch --untracked-files=all
git rev-parse HEAD
git cat-file -e 177c5390ced954e8dd879f99f166e86966dbe706^{commit}
git merge-base --is-ancestor 177c5390ced954e8dd879f99f166e86966dbe706 HEAD
git -C /Volumes/Dev_SSD/Codexify-main status --short --branch --untracked-files=all
git -C /Volumes/Dev_SSD/Codexify-main rev-parse HEAD
bash scripts/ops/codexify_tester.sh status
docker ps -a --filter label=com.docker.compose.project=codexify_tester
curl http://127.0.0.1:8889/health
curl http://127.0.0.1:8889/health/chat
python3 scripts/validate_docs.py
git diff --check
```

The status command exited degraded as expected because the required Tester
runtime was absent. The docs and diff checks apply after this artifact is
created and are recorded in the final task closeout.

## Deferred next slice

The Tester stack must be restored by a separately authorized lifecycle task.
After that task proves the backend, Postgres, Redis, `worker-chat`, queue, and
Whoosh'd Qwen gates without configuration drift, this exact task may be
rerun. It must still create one fresh authenticated proof thread and allow
exactly one completion attempt, with no retry, replay, fallback, DeepSeek,
tool turn, Watchdog activity, or service restart inside the completion proof.

`docs/architecture/00-current-state.md` remained unchanged, and this blocked
proof does not widen the current-main supported-Compose or Beta release claim.
