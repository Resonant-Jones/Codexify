# Tester worker import-diagnosis lineage bridge

**Result:** `TESTER_WORKER_DIAGNOSIS_LINEAGE_BRIDGE_PASS`

**Applicability:**
`TESTER_WORKER_BIND_VISIBILITY_DIAGNOSIS_APPLIES_TO_AUTHORITATIVE_MAIN`

**ADR impact:** Aligned with ADR-074 and existing worker/runtime contracts; no
ADR change.

## Scope and boundary

This is a static lineage-and-code-path bridge. It establishes whether a
historical live-runtime diagnosis may be used as evidence for a later,
separately authorized `worker-chat` startup repair on authoritative `main`.
It does not reproduce the failure, start a Tester service, or change runtime
behavior.

The only tracked change in this task is this proof artifact. No merge, rebase,
cherry-pick, reset, branch force update, source/config edit, container action,
image action, inference, authentication/chat operation, Whoosh'd action,
Watchdog action, or storage mutation was performed.

## Authoritative repository identity

Inspection root:

~~~
root: /Volumes/Dev_SSD/Codexify-main
branch: main
HEAD: 55e5475a4e53ecdb92a3be15e284a370a55ed05f
status: main...origin/main; clean before this proof artifact
origin fetch: https://github.com/Resonant-Jones/Codexify.git
origin push: https://github.com/Resonant-Jones/Codexify.git
~~~

`docs/architecture/00-current-state.md` was read as the short-horizon release
truth and remains unchanged. This bridge is evidence applicability only; it
does not make any supported-Compose, worker-startup, or release qualification
claim.

## Historical live-runtime evidence

The historical object was verified without importing its history:

~~~
git cat-file -e 4601a660c703c4c13907047d2e5222a12ee4bb74^{commit}: PASS
commit: 4601a660c703c4c13907047d2e5222a12ee4bb74
parent: 451ed101651c05e70c769984135765dce1371a32
subject: Diagnose Tester worker import coherence
changed files: docs/architecture/proofs/runtime/2026-08-27-tester-worker-import-coherence-diagnosis-proof.md
~~~

The commit is proof-only: it adds exactly the historical diagnosis artifact.
Its artifact was read directly from the Git object, not copied or cherry-picked:

~~~
path: docs/architecture/proofs/runtime/2026-08-27-tester-worker-import-coherence-diagnosis-proof.md
blob: 781a1105921cf927315d2959ed1e73ceaeb36216
result: TESTER_WORKER_IMPORT_COHERENCE_CAUSE_IDENTIFIED
primary cause: TESTER_WORKER_BIND_MOUNT_VISIBILITY_RACE
~~~

That historical live-runtime evidence established the following facts for its
then-running Tester service:

- Guardian was bind-mounted at `/app/guardian`.
- The same worker container initially resolved `guardian` while failing to
  resolve `guardian.context`, then `guardian.utils`.
- Docker automatically retried the unchanged container; after the virtiofs
  bind became coherent, the worker recovered without an image, source, or
  operator lifecycle change.
- The deferred repair seam was a bounded synchronous predicate that verifies
  the authoritative `/app/guardian` package tree and `guardian`,
  `guardian.context`, and `guardian.utils` importability before
  `python -m guardian.workers.chat_worker` launches.

These are historical observations, not September 2026 runtime observations.

## Current authoritative-main code-path inspection

The current `docker-compose.yml` was inspected directly and rendered with the
canonical Tester Compose file set using `docker compose ... config --format
json`; rendering did not start, create, stop, or restart services. The rendered
`worker-chat` ownership contract is:

| Field | Current authoritative-main value |
| --- | --- |
| Service | `worker-chat` |
| Image owner | `codexify-backend-runtime:latest` (shared backend runtime image) |
| Working directory | `/app` |
| Entrypoint | `python` |
| Command | `-m guardian.workers.chat_worker` |
| Guardian bind source | `/Volumes/Dev_SSD/Codexify-main/guardian` |
| Guardian bind destination | `/app/guardian` (rw bind) |
| Restart policy | `unless-stopped` |

The static command is still the direct worker import boundary:

~~~
entrypoint: ["python"]
command: ["-m", "guardian.workers.chat_worker"]
~~~

There is no current synchronous bind-readiness or import predicate before that
launch. In particular, current `worker-chat` configuration contains no check
for `guardian.context`, `guardian.utils`, a bounded readiness timeout, or a
fail-closed readiness exit. Therefore no independently landed equivalent repair
is present.

The current Tester lifecycle script still assembles this base Compose file with
the Tester and Whoosh'd/DeepSeek overlays, and starts `worker-chat` through its
ordinary lifecycle roster. The lifecycle script and operator runbook were read
only; no lifecycle command was invoked.

## Current test-surface inspection

Current `tests/ops/test_codexify_tester_services.py` covers the Tester service
roster and lifecycle Compose-file selection. The nearby registry-runtime
Compose contract covers the separate packaged-runtime dispatcher form. Neither
test surface asserts a source-bind readiness predicate for `worker-chat`,
`guardian.context`, `guardian.utils`, bounded timeout, or fail-closed startup
behavior. No existing authoritative-main test establishes this repair.

## Applicability decision

The historical diagnosis applies to authoritative `main` because all of its
relevant implementation preconditions remain true:

1. `worker-chat` still owns the same canonical Guardian bind at
   `/app/guardian`.
2. `worker-chat` still directly launches the same
   `guardian.workers.chat_worker` module under Python from `/app`.
3. The Docker-owned `unless-stopped` restart policy is unchanged.
4. No equivalent bind-coherence readiness gate has landed independently.
5. No observed architecture change invalidates the historical causal seam.

Accordingly, the historical evidence supports the constrained future repair
seam, but does not prove a fresh runtime failure or repair success on current
`main`.

## Validation and execution receipt

Completed static validation:

~~~
git status --short --branch: PASS (clean before this artifact)
git rev-parse HEAD: PASS (55e5475a4e53ecdb92a3be15e284a370a55ed05f)
git cat-file -e 4601a660...^{commit}: PASS
git show --stat --oneline 4601a660...: PASS (one proof artifact)
docker compose [canonical Tester files] config --format json: PASS
docker compose [canonical Tester files] config --quiet: PASS
python3 scripts/validate_docs.py: PASS
git diff --check: PASS
~~~

Execution boundaries for this bridge:

~~~
TESTER_LIFECYCLE_ACTIONS_DURING_LINEAGE_BRIDGE=0
TESTER_IMAGE_BUILDS_DURING_LINEAGE_BRIDGE=0
TESTER_CONTAINER_CREATES_DURING_LINEAGE_BRIDGE=0
TESTER_CONTAINER_RESTARTS_DURING_LINEAGE_BRIDGE=0
TESTER_CONTAINER_STOPS_DURING_LINEAGE_BRIDGE=0
MODEL_INVOCATIONS_DURING_LINEAGE_BRIDGE=0
AUTHENTICATION_AND_CHAT_OPERATIONS_DURING_LINEAGE_BRIDGE=0
MANUAL_STORAGE_MUTATIONS_DURING_LINEAGE_BRIDGE=0
WHOOSHD_ACTIONS_DURING_LINEAGE_BRIDGE=0
WATCHDOG_ACTIVITY_DURING_LINEAGE_BRIDGE=0
~~~

## Deferred next slice

This bridge commit replaces cross-lineage ancestry of `4601a660...` as the
prerequisite for one separately authorized repair task. That task may alter
only the current `docker-compose.yml`, the owning Tester worker-startup test
surface, and one repair proof artifact; it must add a bounded, fail-closed,
predicate-based Guardian bind-readiness gate while taking zero container
lifecycle actions. A later, separate task owns one fresh canonical
`make tester-up` proof.
