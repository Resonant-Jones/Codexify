# Guardian Git Runtime Packaging Proof — 2026-10-22

## Outcome

**PASS** — for the packaging and readiness scope only.

The canonical backend and coding-worker runtime images now carry a working Git
CLI, and the coding worker refuses to consume tasks when that prerequisite is
unavailable. A packaging PASS is **not** a delegated-execution PASS: no
Guardian delegation was attempted in this slice, and no provider request was
made.

## Evaluated source

| Item | Value |
|---|---|
| Branch | `feature/guardian-delegation-acceptance-axis` |
| Evaluated commit | `a70ca14653182539e59f055e6f367dac54b7c941` |
| Preceding Guardian commits present | `9d2dae77f`, `cddee2bb6`, `a70ca1465` |
| Dockerfile | `backend/Dockerfile` |
| Build targets | `runtime`, `worker-coding-runtime` |

## The change

Git is installed once, by `apt-get`, in the canonical `runtime` stage of
`backend/Dockerfile`, alongside the existing `bubblewrap`, `ffmpeg`,
`init-system-helpers`, `nodejs`, and `npm` packages. The existing
`rm -rf /var/lib/apt/lists/*` cleanup is preserved. The `worker-coding-runtime`
stage derives from `runtime` (`FROM runtime AS worker-coding-runtime`), so the
backend image and the coding-worker image ship the same Git. There is no second
installation, no host-mounted Git binary, and no package installation during
worker startup.

The Python base image, the pinned Node runtime, the pinned Pi SDK, the
entrypoints, the filesystem mounts, and the credential-isolation posture are
unchanged.

## Proof image identities

| Image | Tag | Image ID | Size |
|---|---|---|---|
| Backend runtime | `codexify-backend-runtime:git-proof-a70ca1465` | `sha256:891cb0f57f77b6db6ac93e950c20f47ed79f7a00022726ab3d7bc64b158eb267` | 4.69 GB |
| Coding-worker runtime | `codexify-worker-coding-runtime:git-proof-a70ca1465` | `sha256:40e8b035e9b75729516180fd8825ceef85b540081db3b3634e1588ec1083e8e4` | 5.2 GB |

Both images were built with proof-specific tags. **No production tag and no
running container was modified.** The operator's `:latest` images and the live
Private Preview stack were not rebuilt, restarted, or redeployed.

## Git availability in the built images

| Check | Backend image | Coding-worker image |
|---|---|---|
| `docker run --rm --entrypoint git <image> --version` | `git version 2.47.3` | `git version 2.47.3` |
| `shutil.which("git")` inside the image | `/usr/bin/git` | `/usr/bin/git` |
| `subprocess.run([git, "--version"])` (no shell) | succeeded | succeeded |
| Synthetic disposable repository: `git init` | succeeded | succeeded |
| `git rev-parse --show-toplevel` | resolved the synthetic root | resolved the synthetic root |
| `git status --porcelain=v1 -z --untracked-files=all` | — | reported the untracked marker file |

The backend image's `validate_git_working_tree_root()` **accepted** the exact
synthetic repository root produced inside the image.

No production repository and no production `.git` directory was mounted into
any proof container.

## Readiness behaviour

The check was extended in `guardian/agents/pi_readiness.py`. The Git probe
resolves Git through `PATH` and runs `git --version` with a bounded
10-second timeout. It requires no repository access, no provider credential,
no model invocation, and it modifies no workspace. The environment handed to
the probe carries runtime paths only — no provider, model, or credential
variable reaches it.

### Positive — the normal proof image

```
status            : ready
can_consume_tasks : True
reasons           : ()
```

Readiness checks reported `node_executable: available`,
`guardian_pi_wrapper: available`, `pi_sdk_runtime: available`,
`git_executable: available`, `adapter_initialization: available`.

### Negative — Git deliberately unavailable

Run with `PATH=/usr/local/bin`, so the image's Node and Pi SDK remain present
and only Git is off the path. The image was not modified; the condition was
introduced at container scope only.

```
status            : blocked
can_consume_tasks : False
reasons           : ("git_missing",)
```

The Pi checks stayed `available` — `node_executable`, `guardian_pi_wrapper`,
`pi_sdk_runtime`, and `adapter_initialization` all passed — while
`git_executable` was `blocked (git_missing)`. Pi readiness alone does not
produce a ready result.

### Startup refuses queue consumption

The worker entrypoint was run with Git unavailable:

```
container exit code: 78
[worker-coding] Pi coding-worker readiness: blocked
[worker-coding] - node_executable: available
[worker-coding] - guardian_pi_wrapper: available
[worker-coding] - pi_sdk_runtime: available
[worker-coding] - git_executable: blocked (git_missing)
[worker-coding] - adapter_initialization: available
[worker-coding] Pi prerequisites are blocked; exiting before queue consumption.
```

The existing `evaluate_pi_readiness()` → `can_consume_tasks` → startup path
was already correct; the Git prerequisite now feeds it. No queue record is
dequeued on the strength of Pi readiness alone. Redis queue semantics were not
altered.

## Build-context secret exclusion

The build context was assembled from **tracked source only** (`git archive`)
for the paths the Dockerfile copies, with the authorised changes under test
overlaid. It was never an operator checkout.

| Audit | Result |
|---|---|
| Environment or credential-named private files (`.env*`, `*.pem`, `*.key`, `auth.json`, `id_rsa*`, `*.p12`, `*.pfx`), excluding vendored `node_modules` | **0** |
| Root-level `.env*` files in the context | **0** |
| Secret-shaped values (`sk-` + 20+ chars) in tracked non-vendored files | **0** |
| The one credential-shaped string found | a 16-character dummy literal in the tracked fixture `codex_runner/tests/test_campaign_engine_live_evaluator.py` — not a key, and quoted nowhere here |

No private-preview environment file, tester credential, Pi auth store, or
operator credential was present in the build context. `.dockerignore` was not
modified in this slice; its narrower `.env` / `.env.local` coverage is a
separate build-context hardening item, recorded below.

## Resource and isolation posture

The proof images were built sequentially in the shared 7.7 GB Docker VM, never
concurrently with a test suite, and never against the running Private
Preview. The operator's stack kept serving throughout the qualification
(`GET /` → 200, `GET /health` → 200 on the published origin). The disposable
PostgreSQL and Redis pair used for the test suites was isolated on its own
docker network and removed afterwards.

The classic Docker builder silently skips Dockerfile heredoc bodies, so the
`runtime` stage's pre-staged scripts were never created and the build failed
at `COPY --from=builder /app/staging/...`. The native BuildKit builder was
used instead, with its activity file written inside the session's writable
runtime directory. This is a build-harness detail of the proof environment, not
a property of the images.

## Targeted and full-suite validation

| Suite | Baseline (HEAD) | After this change |
|---|---|---|
| `guardian/tests/agents/test_pi_readiness.py`, `tests/ops/test_worker_coding_startup_gate.py`, `tests/ops/test_backend_runtime_dependency_contract.py`, `tests/ops/test_worker_coding_pi_runtime_contract.py` | 7 failures | 7 failures — **identical set** |
| `tests/ops/test_webui_runtime_compose_contract.py` | 2 failures | 2 failures — **identical set** |
| Full `tests/` tree, chunked per top-level directory | 670 failure lines | 670 failure lines |

The seven and two failures above are pre-existing environmental gaps in this
image (the vendored Pi runtime closure and the webui bundle build); they fail
identically before and after. The full suite is **not green** and is not
described as green.

**Red-then-green.** With only the production change reverted and the new tests
kept, 15 new or updated assertions fail: the readiness check is absent, the
Dockerfile installs no Git, and the worker stage would carry no inherited Git.
They pass after the change. The red baseline was produced from a scratch tree,
not a whole-worktree stash.

Every file in `tests/` that depends on the changed code is one of the three
`tests/ops` contract files above, and each was compared exactly. No file
outside those three imports `guardian.agents.pi_readiness` or reads
`backend/Dockerfile`.

## Known limitations

- **This is a packaging qualification, not an execution qualification.** No
  Guardian delegation, no adapter invocation, and no provider request
  occurred.
- **Shipping Git is not a sandbox.** The mutation guard remains a *detective*
  boundary: it observes a mutation after the fact and fails the attempt. It
  prevents no write and provides no filesystem, network, or process isolation
  (ADR-077 rules 6-8). Git availability grants no execution permission.
- The Git probe proves the CLI is present and runnable. It does not prove any
  repository operation succeeds in a particular deployment's filesystem
  layout; that is exercised by the delegated path, not by this slice.
- The build context was assembled by hand for this proof. `.dockerignore`
  still excludes only `.env` and `.env.local`, not every `.env.*`; a broader
  build-context exclusion is a separate hardening item.
- Restart recovery, conversational intake, and provider-enforced
  network/process isolation remain unproven. The release gate remains **HOLD**.

## Required follow-on

The next separate gate is a fresh, isolated, end-to-end Guardian delegation
canary using a genuinely dedicated, explicitly authorized test credential.
The previously mislabeled operator-owned canary credential must not be reused.
That canary must independently establish successful worker execution, persisted
results, correct source-thread delivery, and the existing release and authority
boundaries.
