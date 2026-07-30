# Dual-Provider Private-Preview Runtime Proof

Proof date: 2026-07-30

## Outcome

`next-proof-needed`

The live proof did not start because two prerequisite-gate items were absent:
the canonical DeepSeek credential was missing from the ignored
`.env.private-preview` file, and no authenticated preview session-token file
was configured. No partial provider proof was attempted.

## Repository identity

- Branch: `main`
- Starting `HEAD`: `e399a9da1143c27cf13fc923d16b5254d6f9a1bc`
- Upstream: `origin/main`
- Starting ahead/behind: `3/0`
- Worktree before proof: clean
- Relevant implementation commits:
  - `f8eee56d0`
  - `e399a9da1143c27cf13fc923d16b5254d6f9a1bc`
- Both relevant commits are ancestors of the tested `HEAD`.

This receipt evaluates the resulting `main` state. It does not attribute the
complete implementation to either relevant commit in isolation.

## Proof scope

The intended live proof was one explicit, authenticated, persisted Whoosh'd
turn and one explicit, authenticated, persisted DeepSeek V4 Flash turn through
the local private-preview origin, with provider/model identity, terminal task
state, fallback posture, and singular transcript persistence checked
independently.

The prerequisite gate closed before Compose startup. The evidence achieved in
this run is therefore limited to repository identity, sanitized prerequisite
posture, direct Whoosh'd inventory and binding, Docker availability, and static
profile/Compose/proof-tool validation.

## Explicit non-goals

This proof did not change runtime code, tests, validation scripts, Compose,
Nginx, supported profiles, egress policy, authentication, fallback behavior,
environment templates, Cloudflare configuration, DNS, Access policies, rate
limits, backups, or existing data. It did not test public internet access,
guest isolation, backup restoration, reboot recovery, or general
cloud-provider beta support. It did not repair any missing prerequisite.

## Environment classification

- Local operator workstation on macOS
- Repository: `/Volumes/Dev_SSD/Codexify-main`
- Candidate profile: `v1-whooshd-deepseek-web`
- Intended origin: `http://127.0.0.1:8081`
- Secret configuration: ignored mode-`600` `.env.private-preview`
- Docker CLI: `29.6.2`
- Docker Compose: `v5.3.1`
- Docker daemon: available
- Preview origin at gate time: stopped (`HTTP 000`, connection refused)

## Prerequisite gate

Secret-bearing checks reported state only; no values were emitted.

| Prerequisite | Result | Evidence |
| --- | --- | --- |
| Clean worktree | pass | `git status --porcelain` was empty |
| Required implementation ancestry | pass | both relevant commits are ancestors of `HEAD` |
| `.env.private-preview` exists | pass | file exists |
| `.env.private-preview` ignored | pass | `git check-ignore` succeeded |
| Secret-file mode | pass | mode `600` |
| `DEEPSEEK_API_KEY` | **missing** | sanitized key-state check |
| `GUARDIAN_SESSION_SECRET` | present | sanitized key-state check |
| `GUARDIAN_JWT_SECRET` | present | sanitized key-state check |
| Approved preview emails | present | sanitized key-state check |
| Preview admin emails | present | sanitized key-state check |
| Authenticated session-token file | **missing** | `PRIVATE_PREVIEW_SESSION_TOKEN_FILE` not configured |
| Whoosh'd endpoint | pass | `GET http://127.0.0.1:8000/v1/models` returned HTTP 200 |
| Whoosh'd loopback binding | pass | listener was `127.0.0.1:8000` |
| Expected local model | pass | `gemma-4-12b-it-qat-4bit` was the sole inventoried model |
| Docker | pass | CLI, Compose, and daemon available |

Gate decision: closed. In accordance with the proof contract, the preview
stack was not started and neither provider completion was attempted.

## Static validation

| Check | Result |
| --- | --- |
| Focused profile, Compose-contract, and proof-helper tests | pass: 33 tests |
| `bash -n scripts/private_preview_validate.sh` | pass |
| Python compilation of the provider-proof helper | pass |
| `scripts/private_preview_validate.sh static` | pass |

The static validator rendered the combined Compose graph to a protected
temporary file and removed it on exit.

## Resolved Compose posture

Static validation confirmed:

| Contract field | Resolved value |
| --- | --- |
| Supported profile | `v1-whooshd-deepseek-web` |
| Default provider | `local` |
| Local-only mode | `false` |
| Cloud providers allowed | `true` |
| Egress allowlist | `deepseek` |
| Local base URL | `http://host.docker.internal:8000/v1` |
| Local vendor | `whooshd` |
| Local runtime preset | `whooshd-mlx` |
| Local model | `gemma-4-12b-it-qat-4bit` |
| DeepSeek model | `deepseek-v4-flash` |
| Browser Guardian API-key variables | empty |
| Browser DeepSeek credential | absent |

These are resolved-configuration facts, not live service or provider-execution
proof.

## Published-port evidence

Static Compose validation found exactly:

`private-preview-origin 127.0.0.1:8081 -> 8080`

No other publication was present in the resolved graph. Live
`docker compose ps` and `docker ps` publication checks were not run because the
prerequisite gate closed before startup.

## Health-surface evidence

The origin was stopped when checked. The following surfaces were not queried
through a running preview stack:

| Surface | Result |
| --- | --- |
| `/health` | not run; origin not started |
| `/health/chat` | not run |
| `/api/health/llm` | not run |
| `/api/llm/catalog?include=all` | not run |
| Active supported profile | unproven at runtime |
| API health | unproven |
| Redis health and bounded queue round-trip | unproven |
| Worker heartbeat and queue depth | unproven |
| Local authorization and availability | unproven through Guardian |
| DeepSeek authorization, availability, and credential posture | credential missing; runtime unproven |
| Unrelated cloud-provider authorization | unproven at runtime |
| Cross-surface agreement | unproven |

Direct Whoosh'd inventory reachability is separate evidence and does not
establish any of these origin health surfaces.

## Whoosh'd proof

| Evidence | Result |
| --- | --- |
| Proof thread ID | not created |
| User-message ID | not created |
| Request/task ID | not created |
| Acceptance status | not run |
| Terminal task state | unproven |
| Attempted provider/model | not run; intended `local` / `gemma-4-12b-it-qat-4bit` |
| Final provider/model | unproven |
| Fallback reason/status | unproven |
| Persisted assistant count | unproven |
| Persisted assistant-message ID | unproven |
| Task/persistence metadata agreement | unproven |

The direct Whoosh'd model inventory was reachable and contained the expected
model. That is not a Guardian completion or persistence proof.

## DeepSeek proof

| Evidence | Result |
| --- | --- |
| Proof thread ID | not created |
| User-message ID | not created |
| Request/task ID | not created |
| Acceptance status | not run |
| Terminal task state | unproven |
| Attempted provider/model | not run; intended `deepseek` / `deepseek-v4-flash` |
| Final provider/model | unproven |
| Fallback reason/status | unproven |
| Persisted assistant count | unproven |
| Persisted assistant-message ID | unproven |
| Task/persistence metadata agreement | unproven |

The missing credential and authenticated session prevented a valid DeepSeek
attempt.

## Fallback evidence

No provider request was accepted or executed, so fallback absence is
unproven. The focused tests passed the proof helper's fail-closed checks for
provider substitution, fallback, missing terminal completion, and duplicate
assistant persistence; those tests are not live evidence.

## Persistence and transcript-integrity evidence

No dedicated proof threads or messages were created. Terminal-event,
single-assistant persistence, message identity, and task-to-persistence
metadata agreement remain unproven for both providers.

## Sanitized warnings and failures

Warnings:

- `main` began three commits ahead of `origin/main`; the proof evaluated the
  local committed `main` state required by the task.
- The preview origin was already stopped, consistent with the prior task
  boundary.

Failures:

- No runtime failure was observed because the live lane was not entered.

Missing prerequisites:

- Canonical DeepSeek credential.
- Authenticated preview session-token file.

No runtime contradiction with ADR-005, ADR-052, or the supported profile was
observed. Static evidence cannot exclude one.

## Exact commands run

Repository and ancestry:

```text
git status --short --branch
git status --porcelain
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
git rev-list --left-right --count HEAD...@{upstream}
git merge-base --is-ancestor f8eee56d0 HEAD
git merge-base --is-ancestor e399a9da1143c27cf13fc923d16b5254d6f9a1bc HEAD
```

Sanitized prerequisites:

```text
test -f .env.private-preview
git check-ignore -q .env.private-preview
stat -f '%Lp' .env.private-preview
awk -F= '<sanitized key-state classifier>' .env.private-preview
test -f "$PRIVATE_PREVIEW_SESSION_TOKEN_FILE"
test -r "$PRIVATE_PREVIEW_SESSION_TOKEN_FILE"
test -s "$PRIVATE_PREVIEW_SESSION_TOKEN_FILE"
docker --version
docker compose version
docker info
curl --silent --show-error --max-time 5 \
  -o /tmp/codexify-private-preview-whooshd-models.json \
  -w '%{http_code}' http://127.0.0.1:8000/v1/models
curl --silent --show-error --max-time 3 \
  -o /tmp/codexify-private-preview-origin-health.json \
  -w '%{http_code}' http://127.0.0.1:8081/health
lsof -nP -iTCP:8000 -sTCP:LISTEN
.venv/bin/python -c '<sanitized expected-model inventory check>'
```

Static validation:

```text
.venv/bin/python -m pytest -v \
  tests/core/test_supported_profile.py \
  tests/ops/test_private_preview_contract.py \
  tests/ops/test_private_preview_provider_proof.py
bash -n scripts/private_preview_validate.sh
.venv/bin/python -m py_compile \
  scripts/ops/private_preview_provider_proof.py
PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
  bash scripts/private_preview_validate.sh static
```

No `docker compose up`, reachability validation, provider validation, log
inspection, or stop command was run. No `docker compose down -v`, volume
deletion, database reset, or data deletion command was run.

## ADR impact

Classification: aligned with existing ADRs.

- Governing: ADR-005 and ADR-052
- Related proposed doctrine: ADR-039 and ADR-040

This proof changed no accepted topology, provider-governance, authorization,
fallback, exposure, queue, worker, or persistence contract.

## Remaining unproven surfaces

- Private-preview origin startup and health
- Redis queue round-trip and fresh chat-worker heartbeat
- Guardian-mediated Whoosh'd terminal completion and singular persistence
- DeepSeek credential recognition, authorization, reachability, terminal
  completion, and singular persistence
- Provider-specific no-fallback and metadata agreement
- Cloudflare Tunnel
- Cloudflare Access
- DNS
- Public hostname behavior
- Guest isolation
- Rate limiting
- Backup restoration
- Reboot recovery
- General cloud-provider beta support

The next controlled gate is to populate the DeepSeek credential in the ignored
environment file, supply a valid mode-`600` authenticated session-token file,
then rerun this proof from its prerequisite gate.

## Secret-handling statement

No secret values, cookies, bearer tokens, credentials, private prompts,
provider payloads, or complete session-token contents are included in this
receipt.
