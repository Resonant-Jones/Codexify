# Tester worker Guardian import-coherence diagnosis proof

**Result:** TESTER_WORKER_IMPORT_COHERENCE_CAUSE_IDENTIFIED

**ADR impact:** Aligned with ADR-074 and existing worker/runtime contracts; no
ADR change.

## Scope and stop condition

This was a read-only diagnosis of the first worker-chat startup failure after
the single canonical Tester activation recorded by prerequisite proof commit
451ed101651c05e70c769984135765dce1371a32. The existing codexify_tester stack
was left running. No repair, restart, rebuild, Compose lifecycle command,
source edit, image mutation, authentication, chat, inference, DeepSeek request,
Watchdog action, or manual storage mutation was performed.

The first failed activation remains a failure even though Docker later
auto-restarted the same worker container into a healthy idle process. The later
state is evidence for the diagnosis, not a retroactive activation PASS.

The bounded diagnosis window was:

~~~
DIAGNOSIS_WINDOW_START_UTC=2026-08-27T19:00:25Z
DIAGNOSIS_WINDOW_END_UTC=2026-08-27T19:16:04Z
TESTER_LIFECYCLE_ACTIONS_DURING_IMPORT_DIAGNOSIS=0
~~~

## Prerequisite and repository identity

The required prerequisite was checked before discovery:

~~~
git cat-file -e 451ed101651c05e70c769984135765dce1371a32^{commit}: PASS
git merge-base --is-ancestor 451ed101651c05e70c769984135765dce1371a32 HEAD: PASS
~~~

The proof checkout was:

~~~
root: /Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main
branch: codex/diagnose-tester-fresh-chroma-failure
HEAD: 451ed101651c05e70c769984135765dce1371a32
status: clean; ahead 2 of origin/codex/diagnose-tester-fresh-chroma-failure
~~~

The authoritative Tester source was separately inspected at:

~~~
root: /Volumes/Dev_SSD/Codexify-main
branch: main
HEAD: 1c597042e314a9a409ddd384225a2cbb723f7528
remote: https://github.com/Resonant-Jones/Codexify.git
status: main...origin/main [ahead 3, behind 18]
~~~

The authoritative source had pre-existing unrelated paths and they were left
untouched:

~~~
 D docs/DEV_LOG/2026-08-26/Dev Log - 2026-08-26.md
 M docs/architecture/proofs/2026-08-25-local-immutable-image-retention-classification-proof.md
?? docs/architecture/proofs/2026-08-27-google-drive-oauth-clean-retry-proof.md
~~~

The affected Guardian paths were clean. The proof checkout and authoritative
source were not used interchangeably; all runtime configuration was traced to
the authoritative /Volumes/Dev_SSD/Codexify-main root.

## Current runtime identity

The canonical project is codexify_tester. Read-only Docker inspection at the
end of the window showed:

| Service | Container ID | Image ID | Created (UTC) | Current process start (UTC) | Restart count | State |
| --- | --- | --- | --- | --- | ---: | --- |
| backend | 50cc2735f267f93272f77400f7244d0d24528ca60a964c9b92f8dea7bb8d0d5b | sha256:afaca31e244eed0a9d3b08ed3678b31b3131a5dabdf9d864a43fb09d4342a8d4 | 2026-08-27T18:26:05.508611793Z | 2026-08-27T18:26:19.681424716Z | 0 | running |
| worker-chat | 6228850a7360db07959dc82f16b459aa42314f8dedcc8997a4a1ebd89b9a62df | sha256:afaca31e244eed0a9d3b08ed3678b31b3131a5dabdf9d864a43fb09d4342a8d4 | 2026-08-27T18:26:05.706090043Z | 2026-08-27T18:27:41.850211796Z | 9 | running |

The backend and worker therefore use the same image ID, but the worker has a
restart history that the backend does not. The worker restart policy is
unless-stopped.

Image provenance from docker image inspect and history:

~~~
tag: codexify-backend-runtime:latest
RepoDigest: codexify-backend-runtime@sha256:afaca31e244eed0a9d3b08ed3678b31b3131a5dabdf9d864a43fb09d4342a8d4
created: 2026-08-27T13:40:07.161625295Z
platform: linux/arm64
working_dir: /app
image entrypoint: ["python", "/app/entrypoint.py"]
image command: null
base import environment: PYTHONPATH=/app
relevant labels: com.docker.compose.project=codexify;
  com.docker.compose.service=migrator; com.docker.compose.version=5.4.0
history: COPY guardian /app/guardian
~~~

The labels are provenance from the local image tag (the image was previously
used by another Compose project); they do not identify the current Tester
service. The image bytes relevant to Guardian were compared directly below.

## Rendered Tester ownership contract

The exact Tester Compose rendering was read with docker compose ... config
--format json, without bringing the project up or changing it. The base files
are the authoritative root's docker-compose.yml,
docker-compose.tester.yml, and docker-compose.whooshd-deepseek.yml.

### Backend

~~~
service: backend
image: codexify-backend-runtime:latest
build: context=/Volumes/Dev_SSD/Codexify-main, Dockerfile=backend/Dockerfile,
       target=runtime, network=host
working_dir: /app
entrypoint: ["python"]
command: -c ... runpy.run_path("/app/backend/scripts/docker/run_backend.py")
network_mode: host
~~~

The backend binds the authoritative guardian, backend, config, plugins, tests,
and model/data paths. It has no Guardian named volume.

### Worker-chat

~~~
service: worker-chat
image: codexify-backend-runtime:latest
build: null in the rendered worker service (the shared image is consumed)
working_dir: /app
entrypoint: ["python"]
command: ["-m", "guardian.workers.chat_worker"]
restart: unless-stopped
~~~

The worker depends on healthy Redis/backend and the completed model-prep
one-shot. It has the same import-related environment as the backend:

~~~
PYTHONPATH=/app
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
LLM_PROVIDER=local
LOCAL_CHAT_MODEL=qwen3.8-27b-4bit
LOCAL_PROVIDER_VENDOR=whooshd
LOCAL_BASE_URL=http://host.docker.internal:8000/v1
CODEXIFY_SUPPORTED_PROFILE=v1-whooshd-deepseek-web
~~~

The optional vision/GGUF variables were unset Compose warnings and are not
part of Python import resolution. No secret-bearing environment value is
included here.

### Mount ownership

The relevant mounts are identical for backend and worker:

| Host/source | Container destination | Type/mode | Ownership effect |
| --- | --- | --- | --- |
| /Volumes/Dev_SSD/Codexify-main/guardian | /app/guardian | bind, rw | overlays the image's /app/guardian |
| /Volumes/Dev_SSD/Codexify-main/guardian | /app/codexify | bind, rw | second alias of the same Guardian source |
| /Volumes/Dev_SSD/Codexify-main/backend | /app/backend | bind, rw | live backend source |
| /Volumes/Dev_SSD/Codexify-main/config | /app/config | bind, ro | configuration source |
| /Volumes/Dev_SSD/Codexify-main/plugins | /app/plugins | bind, ro | plugin source |
| codexify_tester_codexify_cli_home | /home/codexify | named volume, rw | CLI home only |
| codexify_tester_hf_cache | /root/.cache/huggingface | named volume, rw | cache only |

The worker additionally binds the BGE/model paths. The backend additionally
binds tests, pytest.ini, data/media/imports, Docker, Chroma, and the complete
models directory. None of those additional mounts owns the Guardian package.

Current mountinfo in both containers reports the same virtiofs source and
device for the two Guardian aliases:

~~~
source: /Volumes/Dev_SSD/Codexify-main/guardian
destinations: /app/guardian and /app/codexify
filesystem: virtiofs host
device: 0:43
mode: rw,nosuid,nodev,relatime
~~~

This establishes the current bind source as the canonical checkout, not an
alternate host path. No mount was changed during this diagnosis.

## Image, host, and container Guardian trees

The runtime image layer itself contains both requested subpackages under
app/guardian/context and app/guardian/utils. The authoritative host source also
contains both directories. The current bind-mounted trees in backend and
worker contain the same files.

The following hashes were computed from the host and from both running
containers; each column agrees:

| Relative file | SHA-256 |
| --- | --- |
| guardian/__init__.py | 8c0ca314b70062bdc563de294093de632c18f6ee6a69c5d629be53153d1a6925 |
| guardian/context/__init__.py | e29f87cae9ae0777140414eecc5af1e38174e7c6a72af49afef2ba61e53e1eab |
| guardian/context/broker.py | a0d3ccb5cd7c05050ac42dc1430666f30c54524d1d84484133bddbd05da15cbd |
| guardian/utils/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| guardian/utils/log_safety.py | 1cc41f21ea583ca3cf7866db45f7f15c312c0ffe667c7b74020886c0c81ba89f |
| guardian/workers/chat_worker.py | c16e66cab3fc77e6e01eaeae0d81aad7a45ac57fc611daf2898a457f131fbbed |

The image-layer copies, authoritative host files, current worker files, and
current backend files all agree on these hashes. The image therefore is not
missing the modules, and the final containers are not importing a different
installed guardian package. A read-only site-packages search found no
guardian package/dist-info/egg-info candidate that could shadow /app.

Host source existence and history checks were:

~~~
/Volumes/Dev_SSD/Codexify-main/guardian/context: exists
/Volumes/Dev_SSD/Codexify-main/guardian/utils: exists
affected paths: Git-clean
context latest path commit: 741a049a8624298ec2f1b8249bce8f2b0d6db124
utils/__init__.py and log_safety.py latest path commit: 2b63c2df1396c3c7505be96dcfff135911a8af65
guardian/__init__.py latest path commit: 2b63c2df1396c3c7505be96dcfff135911a8af65
chat_worker.py latest path commit: 8fe5a4d8c9a0aedcc14b25c70074becb246e059e
~~~

The relevant source mtimes were all before the failure window (for example,
guardian/utils/log_safety.py was 2026-08-19T18:10:30-0400 and
guardian/workers/chat_worker.py was 2026-08-11T12:37:44-0400). There was no
affected-path commit, status transition, or newer affected-path mtime during
the failure/recovery interval.

## Python import and process comparison

Exactly one bounded Python import/spec probe was run in each currently running
container. The probe only inspected interpreter/package resolution; it did not
import an application startup module, access the network, or execute model
work.

Both probes returned the same result:

~~~
sys.executable: /usr/local/bin/python
cwd: /app
sys.path:
  ["", "/app", "/usr/local/lib/python311.zip", "/usr/local/lib/python3.11",
   "/usr/local/lib/python3.11/lib-dynload",
   "/usr/local/lib/python3.11/site-packages"]
guardian.__file__: /app/guardian/__init__.py
guardian.__path__: ["/app/guardian"]
guardian spec origin: /app/guardian/__init__.py
guardian.context spec origin: /app/guardian/context/__init__.py
guardian.utils spec origin: /app/guardian/utils/__init__.py
~~~

The current worker probe also found the expected context and utils trees and
the hashes listed above. The backend probe found the same trees and origins.
This proves current post-recovery coherence only; it is not a claim that the
first failed process saw this complete tree.

The running PID 1 state is also aligned:

~~~
worker cwd: /app
worker executable: /usr/local/bin/python3.11
worker argv: python -m guardian.workers.chat_worker
backend cwd: /app
backend executable: /usr/local/bin/python3.11
backend argv: /usr/local/bin/python -m uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888
~~~

There is no worker/backend PYTHONPATH, cwd, interpreter, or entrypoint
divergence that explains the first failure. The difference is the command
being launched: the worker imports guardian.workers.chat_worker directly,
whereas the backend runs its backend bootstrap command.

## Startup preparation behavior

The runtime image's default entrypoint is not used by either relevant Compose
service. Compose overrides it with entrypoint: ["python"]; the worker then
executes -m guardian.workers.chat_worker directly. The backend executes its
run_backend.py bootstrap command directly.

The image entrypoint's symlink/DB-wait/migration preparation therefore cannot
have copied Guardian files, installed an editable package, synchronized a
directory, or changed PYTHONPATH before the worker import. The inspected
worker
path has no synchronous or asynchronous source-preparation step. This
eliminates an entrypoint preparation race as the first cause.

## Failure and recovery chronology

Existing Docker logs and Docker Desktop VM/volume logs were read; no restart
or reproduction was issued.

1. Backend and worker containers were created at
   2026-08-27T18:26:05Z (the exact nanosecond timestamps are recorded above).
2. Docker Desktop approved and registered the worker's two canonical Guardian
   binds at 2026-08-27T18:26:36.340762Z; the worker start request completed at
   2026-08-27T18:26:36.680080126Z.
3. The first worker process failed at
   2026-08-27T18:26:48.961Z while executing
   guardian/workers/chat_worker.py line 31:

   ~~~
   from guardian.context.broker import ContextBroker
   ModuleNotFoundError: No module named 'guardian.context'
   ~~~

4. The first automatic exit/restart transition was logged at
   18:26:49.572693674Z / 18:26:49.654403341Z, with
   manualRestart=false and restartCount=1. The next process failed at
   18:26:49.851Z during guardian/__init__.py:

   ~~~
   ModuleNotFoundError: No module named 'guardian.utils'
   ~~~

5. Further automatic attempts produced the same guardian.utils failure at
   approximately 18:26:50.133Z, 18:26:50.630Z, 18:26:51.752Z,
   18:26:53.474Z, 18:26:56.798Z, 18:27:03.319Z, and 18:27:16.212Z.
   The Docker Desktop log records restart transitions with
   manualRestart=false for restart counts 2 through 9; the same worker
   container ID remained in use.
6. The last failed attempt finished at 18:27:16.215682006Z. The same
   container's final process started at 18:27:41.850211796Z, logged
   [chat-worker] started queue=codexify:queue:chat concurrency=2 at
   18:27:51.167Z, and subsequently reported a fresh heartbeat with queue
   depth 0 in the prior read-only health observation at 18:30:06Z.

There is no Docker Desktop recreate request for this worker ID after the
initial create in the selected VM log. There is no image replacement, tag
change, or operator lifecycle action in the sequence. The worker's nine
transitions are Docker policy restarts (manualRestart=false), not a second
activation.

## Concrete failed import state and effective transition

The two exception forms identify a specific partial package view rather than a
missing top-level package:

- guardian.context failed from the worker module's direct import while the
  guardian package root was importable.
- On the next process, guardian/__init__.py was found and its
  .utils.log_safety import failed as guardian.utils.

The image layer and the canonical host bind source both contain those
subtrees, with matching bytes. The current worker and backend use the same
PYTHONPATH=/app, cwd /app, interpreter, image ID, and bind source, and the
host affected paths did not change during the interval. The only changing
boundary visible in the evidence is the effective view of the virtiofs bind
mount at process startup: the package root was visible while its subdirectory
entries were temporarily unavailable to successive imports, then the complete
tree became visible to the later process.

The available Docker logs do not persist a separate hypervisor-level virtiofs
"subtree appeared" event. That is a limit on event granularity, not a reason to
attribute the failure to the image, source drift, Python path, cwd, or a
container replacement that the evidence disproves. The concrete import state,
the unchanged container contract, and the same-container automatic transition
support a mount-visibility diagnosis.

## First causal classification

~~~
TESTER_WORKER_BIND_MOUNT_VISIBILITY_RACE
~~~

This is the one primary classification. The following are ruled out as the
first cause by the captured evidence:

- the image contains guardian/context and guardian/utils, with hashes equal
  to the host and current containers;
- the worker bind source is the canonical
  /Volumes/Dev_SSD/Codexify-main/guardian path, not a drifted checkout;
- worker/backend PYTHONPATH, cwd, interpreter, and current package origins
  agree;
- the Compose-overridden worker command bypasses image startup preparation;
- the worker ID and image stayed constant, so recovery was not a container
  recreation;
- affected host source paths were clean and unchanged in Git and timestamp
  evidence during the window.

## Evidence-backed auto-recovery explanation

Docker's unless-stopped policy repeatedly relaunched the same worker process
after each import exit. No operator action, image change, source edit, mount
source change, or container recreation occurred. By the final automatic start,
the same /app/guardian virtiofs bind exposed the complete context and utils
trees, and the worker logged its normal started message. The single current
worker probe then resolved both subpackages from /app/guardian.

Thus the later healthy state is explained by the bind-mounted filesystem
becoming import-visible before a subsequent policy restart—not by a repair or
by a different image. The historical process did not retain a Python snapshot,
so the exact internal virtiofs transition timestamp is unproven; the causal
boundary is nevertheless identified at the mount-visibility race.

## Minimum deferred repair seam (not implemented)

**Owner:** /Volumes/Dev_SSD/Codexify-main/docker-compose.yml, the
worker-chat startup command/entrypoint declaration.

**Defect:** the worker launches -m guardian.workers.chat_worker directly while
the /app/guardian bind overlay has no synchronous readiness gate. A process can
begin importing while the virtiofs-mounted package root is visible but the
required subdirectories are not yet visible.

**Minimum correction for a follow-up task:** make the worker launch command
perform one deterministic, synchronous pre-import check that
/app/guardian/__init__.py, /app/guardian/context/__init__.py,
/app/guardian/utils/__init__.py, and the worker module are visible from the
expected mount before executing the existing worker module command. Keep the
current image and canonical bind ownership unchanged.

For this diagnosed seam, an image rebuild is **not required**: the image
already contains the needed files and the current bind bytes agree. A future
implementation would require container recreation to load the changed command
and then exactly one canonical make tester-up lifecycle proof; neither is
performed here. This readiness-gate correction does not change the accepted
provider/model, queue, persistence, or image/bind ownership contract.

## Runtime and execution boundaries

The existing stack remained running. The following boundaries were held at
zero for this diagnosis:

~~~
TESTER_LIFECYCLE_ACTIONS_DURING_IMPORT_DIAGNOSIS=0
TESTER_IMAGE_MUTATIONS_DURING_IMPORT_DIAGNOSIS=0
TESTER_SOURCE_CONFIG_EDITS_DURING_IMPORT_DIAGNOSIS=0
MODEL_INVOCATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
AUTHENTICATION_OPERATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
THREADS_CREATED_DURING_WORKER_IMPORT_DIAGNOSIS=0
MESSAGES_CREATED_DURING_WORKER_IMPORT_DIAGNOSIS=0
COMPLETION_REQUESTS_DURING_WORKER_IMPORT_DIAGNOSIS=0
DEEPSEEK_REQUESTS_DURING_WORKER_IMPORT_DIAGNOSIS=0
WATCHDOG_ACTIVITY_DURING_WORKER_IMPORT_DIAGNOSIS=0
MANUAL_POSTGRES_MUTATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
MANUAL_REDIS_MUTATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
MANUAL_CHROMA_MUTATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
MANUAL_NEO4J_MUTATIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
WHOOSHD_LIFECYCLE_ACTIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
WHOOSHD_GENERATION_REQUESTS_DURING_WORKER_IMPORT_DIAGNOSIS=0
CAPSULE_BUILDER_ACTIONS_DURING_WORKER_IMPORT_DIAGNOSIS=0
~~~

Whoosh'd was read-only and untouched. The unrelated sleep-only capsule-builder
containers were outside the diagnosis and untouched; no evidence connects
them to Guardian import resolution. No model, database, Redis, Chroma, Neo4j,
GitHub, Command Bus, Build Loop, or Watchdog activity occurred.

## Validation and documentation boundary

The following read-only/runtime checks were completed:

~~~
prerequisite git object and ancestry checks: PASS
proof and authoritative repository identity/status checks: PASS
docker inspect container/image/mount/restart metadata: PASS
docker compose ... config --format json: PASS (optional unset-model warnings only)
docker image inspect/history and read-only image-layer inspection: PASS
Docker Desktop VM/volume log chronology inspection: PASS
one bounded worker Python import/spec probe: PASS (current coherence)
one bounded backend Python import/spec probe: PASS (comparison coherence)
host Guardian existence/Git/history/mtime checks: PASS
~~~

docs/architecture/00-current-state.md was not modified. This proof does not
claim supported release readiness or a successful Tester activation.

## Deferred next slice

The next task may repair only the proven worker-chat bind-mount readiness seam.
It must not include authenticated Qwen inference. After that repair is
committed and validated, a separate task must run exactly one canonical
make tester-up and require a clean first worker startup (no import error,
fresh heartbeat, queue depth 0, backend healthy on 8889, and
local / qwen3.8-27b-4bit) while preserving the Whoosh'd
mlx_vlm / MlxVlmAdapter and zero-inference boundaries. Only that clean
lifecycle proof can precede a later one-attempt authenticated Tester Qwen
completion.
