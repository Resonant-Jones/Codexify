# WBC-1A-P1A — Docker/Compose Prerequisite Recovery Proof

## Purpose

This host-local operational proof follows the WBC-1A-P1 target-readiness
block. It establishes whether Docker Desktop and Docker Compose are available
again on the supported VaultNode proof host so that the already selected
current-tip `codexify-audit` target can be re-qualified. It does not start that
project, run a migration, or exercise any WBC-1A chat, queue, provider,
turn-lock, persistence, or readback behavior.

## Repository, source, and authority preflight

| Item | Observation |
| --- | --- |
| Current GitHub `main` after `git fetch origin` | `eb6bdc530245fdffeff23589c98389be4102b564` |
| G0 baseline | `eb6bdc530245fdffeff23589c98389be4102b564` |
| Proof checkout | `/private/tmp/codexify-wbc-1a-p1-supported-proof` |
| Proof checkout branch / HEAD | `codex/wbc-1a-p1-supported-proof` / `eb6bdc530245fdffeff23589c98389be4102b564` |
| Upstream and merge base | both `eb6bdc530245fdffeff23589c98389be4102b564` |
| Cleanliness / G0 ancestry | clean; G0 is an ancestor of HEAD |
| Runtime machine | `VaultNode.local` (macOS `26.5.2`) |
| Machine role / authority basis | `canonical_evidence_host` / `ADR-041` |

The selected target remains the P1 audit project: base
`docker-compose.yml`, project `codexify-audit`, role `audit`, and supported
profile `v1-local-core-web-mcp`. The pre-existing `codexify_tester` project
was not stopped, changed, relabelled, or used as WBC evidence. Its distinct
dirty source and cloud-capable Tester profile remain excluded.

## Docker/Compose observation before recovery

The Docker CLI was present at `/usr/local/bin/docker`, with current context
`desktop-linux`. `docker compose version` succeeded and reported `v5.3.1`.

The required `docker version --format json` observation exited `1`; its bounded
daemon failure was `Docker Desktop is unable to start`. This was a host Docker
server prerequisite failure, not a Compose, source, profile, migration, or
application failure.

## Authorized normal application recovery

Only the normal Docker Desktop application lifecycle was used:

1. `open -a Docker` launched the installed application normally.
2. Six bounded server observations remained unavailable.
3. One normal application quit and one normal relaunch were performed.

No Docker Desktop reset, daemon/socket/context deletion, Docker data deletion,
prune, image/volume/network deletion, uninstall/reinstall, alternate runtime,
or Codexify Compose command was used.

## Successful Docker and Compose boundary

The first post-relaunch `docker version --format json` readiness observation
reported both client and server `29.7.2` on `linux/arm64`; the current context
remained `desktop-linux`. `docker compose version` still reported `v5.3.1`.

The P1 source and target profile were then checked without creating containers:

```text
docker compose --project-directory <isolated-p1-proof-worktree> \
  --env-file <isolated-p1-proof-worktree>/.env \
  -p codexify-audit -f <isolated-p1-proof-worktree>/docker-compose.yml \
  config --quiet
```

This returned `compose_config=valid`. The command does not start, build, pull,
or otherwise create the `codexify-audit` project.

## Canonical live-proof collector recheck

The current Make target was re-read before collection. From the clean P1 proof
checkout, the bounded read-only collector was invoked with the same target
inputs used by P1:

```text
make PYTHON=<repository-venv>/bin/python canonical-audit-live-proof-receipt \
  repo=. machine_id=vaultnode machine_role=canonical_evidence_host \
  authority_basis=ADR-041 assert_canonical_machine=1 \
  compose_file=docker-compose.yml compose_project=codexify-audit \
  project_role=audit audit_project=codexify-audit \
  profile_name=v1-local-core-web-mcp compose_env_file=.env \
  api_base=http://127.0.0.1:8888 frontend_base=http://127.0.0.1:5173 \
  command_timeout=10 http_timeout=5
```

The collector emitted a schema-valid receipt and returned its expected nonzero
exit for an absent project. Safe receipt summary:

| Field | Observation |
| --- | --- |
| Receipt ID | `live-proof-receipt-sha256-3db4efd5c4448c84b45fa788b1d3a3f4e0d9570621c5fe2cba5e61a99b20e2e0` |
| Collector execution outcome | `BLOCKED` because this task intentionally did not start `codexify-audit` |
| Receipt schema validation | passed; zero issues |
| Authority status | `PROVISIONAL` |
| Docker projection | client and server both `29.7.2` |
| Repository projection | clean `eb6bdc530245fdffeff23589c98389be4102b564`, upstream equal |
| Supported profile / project / role | `v1-local-core-web-mcp` / `codexify-audit` / `audit` |
| Reason codes | `compose_project_missing`, `wrong_branch` |

`docker_server_unavailable` was not present. `compose_project_missing` is
expected and correct: this recovery proof must not start the audit project.
The dedicated proof-worktree branch also remains a bounded provisional-evidence
qualification; it does not alter the clean current-tip source identity.

## Boundaries and limitations

- Docker and Compose availability is restored only as a host prerequisite.
  This does not establish P1 target eligibility, a running supported stack,
  migration/init completion, service health, local-provider reachability from
  containers, model inventory, worker heartbeat, or WBC-1A closure.
- No Compose project was started; consequently no containers, migrations,
  database state, worker state, model request, or chat thread was created.
- The known turn-lock test was not run, diagnosed, or changed.
- No tracked runtime/configuration, profile, Compose, migration, source, test,
  ADR, Campaign, or current-state file was changed. No cloud provider was
  enabled, and no secret value was recorded.

## ADR impact

Aligned with ADR-041 (canonical machine and separate audit runtime), ADR-042
(bounded evidence axes), ADR-052 (Tester dual-provider profile remains
separate), and ADR-069 (local-only supported Beta boundary). No architectural
decision changed.

## Final result

DOCKER_PREREQUISITE_READY
