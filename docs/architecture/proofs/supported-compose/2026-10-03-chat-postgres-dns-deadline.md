# Accepted-chat PostgreSQL hostname resolution deadline repair

Date: 2026-10-03. Parent source: `3424fd44d`.
Classification: `AUTHORIZED_IMPLEMENTATION`; architecture-impact, P1; owner: Codex.
Hostname-resolution wait repaired; full supported qualification remains HOLD.

## Atomic Task Spec and authority

Bound the existing accepted PgDB hostname-resolution operation by the original
remaining work/terminal budget, terminate and reap an overdue owned resolver,
and prevent late connection admission. Preserve hostname/TLS identity, driver
host/address/port ordering, shorter connection-policy timeouts, explicit hostaddr,
numeric and local-socket targets, ordinary DNS errors and legacy behavior. Prove
DNS and native handshake share one frozen budget, plus healthy DNS-to-SQL
controls on both exercised drivers.

Authority: explicit ordinary-chat reliability Goal, Codex Development Operator
Goal, Chat Runtime Contract, Runtime Protocol Token Contract and ADR-087. The
[preceding resolver characterization](./2026-10-03-chat-postgres-dns-envelope-gap.md)
proved synchronous DNS can outlive the parent before native polling begins.
This change belongs in `guardian/core/chat_postgres_deadline.py`.

Allowlist: that helper, `tests/db/test_chat_postgres_dns_deadline.py`, and this
receipt. Commit subject: `fix(chat): bound PostgreSQL DNS by accepted deadline`.
Direct bounded operator execution; no new architecture, Campaign progression,
tokens, main merge, push, deployment or release promotion.

## Implementation and boundaries

Within accepted scope, the existing connection subclass prepares unresolved
hostnames before upstream `connect()` enters its synchronous resolver. An owned
local Python subprocess runs the installed driver's `conninfo_attempts` and
native NSS/getaddrinfo behavior. Only host, hostaddr and port cross stdin; DSN,
user, password and database are not resolver inputs or command-line arguments.
The child uses the local interpreter/dependency runtime, not a new service,
queue or persistent worker. No library-global resolver/wait function is patched.

The parent waits for the smaller of the original remaining budget and the
driver's connection timeout. Repeated observations consume that same frozen
time; no child progress can reset it. Actual parent expiry propagates the
canonical accepted-deadline exception. A shorter policy produces ordinary
psycopg `ConnectionTimeout`. After resolution, a deadline check prevents late
admission, and native polling still reads the same parent budget.

The parent kills a still-running owned child and reaps it before returning,
closing its pipes. This replaces an uninterruptible in-process resolver without
discarding a background Python thread. Successful/error exits are reaped too.

Resolved addresses and corresponding ports are expanded in driver order while
the original hostname remains for TLS/authentication. Target-session and random
load-balancing policy are suppressed only during resolution and applied once by
the parent's original driver. Resolution errors retain the driver's operational
error message; a failed hostname still permits the driver's next resolved host.
Numeric, Unix/local and explicit-hostaddr targets bypass the subprocess. Outside
accepted scope, parameter preparation delegates unchanged behavior.

Service-file configuration can hide additional libpq-owned hostname resolution
or configuration work. Accepted scope therefore fails closed with an ordinary
operational error when a service is selected, including through `PGSERVICE`.
Use explicit host/hostaddr configuration for this bounded path. Legacy behavior
is preserved. This is a concrete configuration limitation, not service-file
qualification. The retained supported stack uses direct hostname configuration.

The implementation depends on inspected psycopg parameter/attempt internals and
starts a local subprocess for each new accepted connection needing DNS. Pool
reuse avoids new connection creation. Dependency/interpreter changes need fresh
proof; this task does not qualify Windows or every NSS/authentication backend.
Preserved TLS hostname parameters are structural proof, not certificate-chain
or GSSAPI qualification. Remote commit ambiguity remains separate.

## Proof and validation

Four owned resolver processes held a getaddrinfo call for 20 seconds, exercising
raw/ORM admission in work and terminal phases with a 0.5-second parent. Each
caller returned the canonical deadline error without late admission. Independent
PID checks proved the child was killed/reaped, its pipes closed, and its process
absent while the timeout exception remained retained.

Four further cases delayed resolution, then connected to actual inert TCP peers
that accepted PostgreSQL startup bytes and withheld replies. Each stopped at the
original 0.5-second deadline, with peer EOF before harness release. DNS completion
did not grant native polling another budget. These use controlled resolver seams
and real TCP; they are distinct from a real DNS-network outage.

| Case | Host psycopg 3.2.10 | Worker psycopg 3.3.6 |
| --- | --- | --- |
| Four held-DNS cases, 0.5 s parent | 0.5040–0.5068 s | 0.5020–0.5055 s |
| Four DNS-then-handshake cases | 0.5016–0.5030 s | 0.5011–0.5053 s |
| Shorter DNS policy, 5 s parent | 2.0078 s | 2.0104 s |

The shorter policy retains the driver's two-second minimum and ordinary timeout
disposition while the parent remains unexpired. Actual native hostname resolution
and PostgreSQL `SELECT 1` passed through raw, newly created and reused ORM
connections; ordinary pooled statement timeout remained zero afterward.
Address/TLS/port expansion, explicit addresses/environment, numeric/local targets,
single application of standby/load-balance policy, skipped failed hostname,
normal DNS error and accepted-only service rejection controls passed.

Validation from the repair repository root:

- Private `TEST_DATABASE_URL`, `PYTHONPATH=. .../.venv/bin/python -m pytest
  -o addopts= -q -s tests/db/test_chat_postgres_dns_deadline.py
  tests/db/test_chat_postgres_connect_deadline.py
  tests/db/test_chat_postgres_pool_deadline.py tests/db/test_chat_postgres_deadline.py
  tests/db/test_chat_completion_attempt_migration.py
  tests/workers/test_chat_worker_queue_deadline.py
  tests/workers/test_chat_worker_tool_loop.py
  tests/workers/test_chat_worker_lifecycle_events.py
  tests/test_chat_worker_turn_integrity.py`: **73 passed, zero skips**, 47.70 s.
- Actual retained worker, exact copied test/bootstrap files and private controlled
  test environment, DNS/connect/pool/query deadline files: **47 passed, zero
  skips**, 37.54 s. Eleven real-PostgreSQL cases, eleven real-TCP cases (four also
  use delayed resolver seams), and twenty-five resolver/unit controls.
- Ruff on helper/new test, `python -m py_compile` on both and `git diff --check`:
  passed. Existing configuration, Alembic, ORM-overlap and copied-marker warnings
  remain outside scope. Host and container suites ran serially to avoid the
  existing query observer's cross-database application-label count.

## Runtime custody and follow-through

Retained project `codexify_chat_branch_proof_896387ad2` was verified idle before
copying exactly the helper into its owned mounted source and restarting only
backend/chat worker. All **1,135 tracked Guardian/backend Python files** matched
checkout, mounted source and both containers. Both drivers are 3.3.6; health is
ok with valid supported profile, migration head remains `d4c69e03a712`.

Owned random fixture databases were migrated and dropped, copied-suite hashes
verified, XML exported and the owned suite removed. No fixture database or DNS
resolver process remained. SQL retained thread 30's exact messages 56/57. Final
chat queue was empty, turn locks absent, worker idle with positive heartbeat TTL.
Evaluation queue stayed 27; system queue grew 7 to 8 during idle restart/testing.
No queue consumption or deletion occurred. Application data and unrelated
containers/settings were preserved; credentials were not printed or committed.

Evidence root:
`/private/tmp/codexify-chat-postgres-dns-deadline-3424fd44d-20261003/`
retains runners, exact tests/hashes, logs/XML, source matrices, health/runtime and
cleanup assertions. This receipt is documentation follow-through. ADR impact is
alignment with ADR-087, with no new ADR, current-state promotion or memory update.

Fresh ordinary browser completion/reload is the next required integration proof
after committing this repair. The Goal stays active. Redis/outbox/context bounds,
exhausted terminal reserves, remote commit ambiguity and active-worker drain/loss
recovery remain unfinished. Idle restart here is not active-shutdown proof.
