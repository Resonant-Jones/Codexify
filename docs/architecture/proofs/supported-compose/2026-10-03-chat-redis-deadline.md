# Accepted-worker Redis waits inherit the frozen task deadline

Date: 2026-10-03. Baseline: ec35a80a0.
Classification: AUTHORIZED_IMPLEMENTATION; architecture-impact, P1; owner Codex.
Focused repair/proof passed. Full supported qualification remains HOLD.

## Atomic Task Spec and authority

Repair the confirmed Redis child escape using the original immutable accepted
work/terminal timestamps. Bound DNS, TCP/TLS establishment, socket reads/writes,
continuing response bytes, native retry/backoff, application reconnect/backoff
and owner cleanup. Keep accepted clients/pools task-owned and preserve native
authentication, TLS hostname identity, response parsing, visibility results and
unrelated request/queue policy. Use existing terminal paths and bounded
pre-dispatch observation without dropping accepted tasks.

Allowlist: guardian/core/chat_redis_deadline.py,
guardian/queue/redis_queue.py, guardian/workers/chat_worker.py,
tests/queue/test_chat_redis_deadline.py and this receipt. Private evidence,
isolated worker exec processes and exact owned fixtures belong to the task.
The retained task-owned source may refresh only the three runtime files and
restart only idle backend/chat worker after focused proof passes.
Commit subject: fix(chat): inherit Redis waits from accepted deadline.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, ADR-087 and Chat Runtime Contract. Direct bounded execution; no new
architecture, protocol token, recovery disposition, provider/ownership policy,
main merge, push, deployment or release promotion. The original main checkout
remains separate at e992d8e2b.

## Mechanism and causal boundary

The new Redis scope freezes the same wall/monotonic anchor as the existing
worker PostgreSQL scope. Each accepted execution owns one request client/pool;
global request and queue clients are not reset by its reconnect failures.
Existing terminal calls and owner-guarded finally cleanup switch both scopes
to their original terminal reserve. Total exhaustion and malformed snapshots
cannot start a client. A saved accepted client cannot escape its owning scope
or borrow a later task's budget.

Hostname resolution runs in an owned isolated Python child, using the runtime's
actual socket.getaddrinfo. Only host, port and address family cross its input;
authentication data is absent from resolver input/argv. Expiry kills/reaps the
child and closes its pipes. Numeric hosts bypass resolution; zone-qualified
IPv6 retains resolver-derived scope IDs. Address attempts retain the inherited
parent and existing per-connect policy. Native socket options remain intact.

Native Redis parsing and authentication operate on the real socket. Its
adapter clips every send/recv/recv_into to min(existing socket policy, remaining
parent) and checks the frozen deadline after return. Continuing RESP bytes do
not renew it. TLS retains the native context/certificate setup and original
hostname; the socket hands the fresh remaining timeout to native SSL after
context preparation. External OCSP validation fails closed before DNS/TCP
because its extra waits are not bounded here.

Native retry count/error policy and backoff calculation remain intact; native
and application sleeps consume the same remaining parent. Deadline exceptions
are not reconnected into a new budget. Ordinary shorter-policy timeouts retain
their driver disposition. Expiry closes owned sockets; scope exit disconnects
its pool. The existing pytest network shim remains synthetic; real TCP tests
supply native clients explicitly. That shim is not runtime transport proof.

Accepted pre-dispatch heartbeat/cancellation observation is also scoped.
Expired/malformed snapshots enter the same worker lifecycle inline.
Unavailable cancellation observation dispatches the original accepted task
into that lifecycle; it does not discard it or mint another attempt.

## Focused proof and regressions

Host Python 3.12.13 and retained worker Python 3.11.14 both use Redis 7.0.0.
The main host run passed **122 tests**, zero failures/errors/skips: 29 new
transport/scope checks plus worker deadline/tool/lifecycle/stream/model/cancel,
turn-integrity, lock/recovery and immutable-envelope regressions.
The worker container separately passed all **29 new checks**, zero
failures/errors/skips, in 8.410 seconds.

The held-response test was then strengthened to assert terminal publication's
failure visibility classification explicitly. Its four cases passed again on
both host and worker with the exact updated test source; the earlier complete
suite and its copied source are preserved separately.

Real controlled TCP checks covered progress/terminal XADD, canonical release
EVAL and cancellation SISMEMBER. A 0.25-second frozen remainder now interrupts
the wait with the canonical deadline exception, reports failed publication
visibility, and closes the socket before the peer releases a response.
Host and worker held-response waits returned in approximately 0.25 seconds. Continuing bulk-response bytes also ended at the original
deadline. Native two-second backoff started no replacement command; application
reconnect consumed the same remainder.

Held DNS work/terminal cases terminated and reaped their children with closed
pipes. A 0.2-second DNS delay followed by an actual held response consumed one
0.5-second total remainder: host 0.5024 seconds, worker 0.5016 seconds.
Shorter DNS/socket policy controls kept ordinary RedisTimeoutError.
TLS stalls closed at approximately 0.25 seconds. A real local certificate,
hostname verification and encrypted AUTH/PING control passed; the connection
retained localhost as its TLS/authentication host. These are controlled peer
and resolver seams, not a network-level Redis/DNS outage or every TCP fault.

Actual retained Redis separately passed accepted work, accepted terminal and
legacy publication/readback/cancellation controls. Their durations were
0.0165, 0.0130 and 0.0002 seconds. Canonical lock acquisition rejected a foreign
owner, preserved the lock, then allowed the exact owner/token release in
0.0132 seconds. Independent EXISTS checks proved all unique owned keys absent.
A real accepted PING also proved distinct owned pool allocation/closure,
global client identity and unchanged legacy request/queue timeout/retry policy.

The first focused harness run incorrectly treated work expiry as total expiry.
Its one failing assertion was corrected to test the frozen terminal timestamp;
the existing terminal reserve was preserved. The failure log is retained.
TLS setup's initially stale handshake timeout was tightened before the final
host/container runs. Ruff, py_compile and staged git diff --check passed.
Existing Swig/deprecated-linter warnings are outside this task.

## Runtime custody, cleanup and follow-through

After host checks passed, an independent idle gate verified queue zero,
no turn locks and positive idle heartbeat TTL. Exactly the three allowlisted
runtime files differed from the retained task-owned source; only they were
copied. Backend and chat worker were restarted once. All **1,136 tracked
Guardian/backend Python files** then matched checkout, mounted snapshot and
both containers. Health remained ok on the retained v1-local-core-web-mcp
profile; PostgreSQL drivers remain 3.3.6.

The five copied test/bootstrap files were independently hash-verified before
removing each owned container suite, including its generated TLS fixtures.
XML was exported first. Resolver scans found no owned Redis/PostgreSQL DNS
child in either container. Chat queue remained zero, turn locks absent and
worker idle with positive TTL. Evaluation queue stayed 28; system queue
increased 8 to 9 across the idle restart and was preserved.

Fresh SQL/API/receipt/raw-event readback retained thread 31, exact messages 58/59
and its one durable completion. No application message/database mutation or new
browser submission occurred. This preserves the preceding complete-path proof;
a **fresh browser completion/reload after this repair is the next separate
proof obligation**.

Evidence:
 /private/tmp/codexify-chat-redis-deadline-ec35a80a0-20261003/
contains Task Spec, host/container logs/XML, both copied suite/source matrices,
source-refresh/custody, healthy/legacy controls, fixture/resolver cleanup,
health/state, retained SQL/API/event/receipt and independent validated results.
Credentials were not printed or committed. Documentation follow-through is
this receipt; ADR impact is alignment only. No memory update is authorized.

The Goal remains active. Outbox/context bounds, exhausted durable terminal
reserves, remote acknowledgement ambiguity and active-worker drain/loss
recovery remain unfinished. This isolated older-main repair branch does not
qualify newer-main integration, full failure/recovery behavior, supported
Compose release readiness or every Redis configuration.
