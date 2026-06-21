# Zac Mac Studio Local Bring-Up

Purpose: provide a narrow operator path for bringing up Zac's Mac Studio on the current beta-supported local Docker Compose deployment.

This runbook reuses existing smoke and proof seams. It does not introduce a new release path, packaged desktop path, Pattern/Instance sync path, federation path, graph-write path, or cloud-provider beta path.

## Supported Scope

Use this path for:

- macOS Apple Silicon host.
- Host-local Whoosh'd runtime on `127.0.0.1:8000`.
- Codexify backend and workers in Docker Compose.
- Local-only provider posture:
  - `LLM_PROVIDER=local`
  - `CODEXIFY_LOCAL_ONLY_MODE=true`
  - `ALLOW_CLOUD_PROVIDERS=false`
  - `LOCAL_BASE_URL=http://host.docker.internal:8000/v1`
- Current beta Docker path validation through existing smoke/proof scripts.

Do not use this path to claim:

- Pattern/Instance sync is shipped.
- Federation is shipped or beta-supported.
- Graph writes are enabled on the supported path.
- Cloud-provider beta use is approved.
- The packaged desktop shell replaces Docker Compose as the supported install path.

## Nodes And Boundaries

| Node | Responsibility |
|---|---|
| Zac's Mac Studio | Owns local files, model cache, Docker Desktop, and host-local Whoosh'd process. |
| Whoosh'd host process | Owns local model inventory, model readiness, and OpenAI-compatible inference API. |
| Docker Compose services | Own Guardian API, frontend dev server, Postgres, Redis, migrations, and workers. |
| Docker host bridge | Lets containers reach Whoosh'd through `host.docker.internal:8000`. |

Trust boundaries:

- Device boundary: this is a trusted single-machine beta operator path.
- User boundary: `.env` and model cache stay local to Zac's machine.
- Network boundary: local-only mode must keep cloud providers disabled.
- Runtime boundary: Whoosh'd is a peer local process, not vendored Codexify code.

Threat model:

- Primary: honest-but-buggy local setup, missing Docker, missing API keys, stale containers, missing Whoosh'd model inventory, queue/worker drift.
- Not covered: malicious peers, compromised local host, remote federation, cross-device sync, or public internet exposure.

## Fast Path

From the repo root:

```bash
bash scripts/ops/zac_mac_studio_bringup.sh --check-only
bash scripts/ops/zac_mac_studio_bringup.sh --prove
```

The first command surfaces missing host prerequisites before starting services. The second command:

1. Checks macOS Apple Silicon, Docker, Compose v2, `curl`, `jq`, `python3`, `.env`, `GUARDIAN_API_KEY`, `VITE_GUARDIAN_API_KEY`, `NEO4J_PASS`, and Whoosh'd availability.
2. Runs `scripts/whooshd_docker_smoke_up.sh minimal --detach`.
3. Reuses `docker-compose.whooshd-smoke.yml` to assert the local-only Whoosh'd Compose contract.
4. Reads `/health`, `/health/chat`, and `/health/llm`.
5. Runs `scripts/verification/run_supported_path_proof.sh` through the same Compose override when `--prove` is set.

For the full stack instead of the minimal smoke stack:

```bash
bash scripts/ops/zac_mac_studio_bringup.sh --full --prove
```

## Manual Seams

If an operator needs to run the seams manually:

```bash
bash scripts/whooshd_docker_smoke_up.sh minimal --detach
```

Then run the supported-path proof against the same Compose override:

```bash
CODEXIFY_COMPOSE_ARGS="-f docker-compose.yml -f docker-compose.whooshd-smoke.yml" \
GUARDIAN_API_KEY="$(scripts/dev/dev-key.sh)" \
bash scripts/verification/run_supported_path_proof.sh
```

The proof artifact is written under:

```text
docs/audits/supported_path/
```

## Failure Modes

| Failure | First check | Boundary |
|---|---|---|
| Docker daemon unreachable | Start Docker Desktop, then run `docker info` | Host tooling |
| `whooshd` CLI missing | `docs/Ops/WHOOSHD_LOCAL_RUNTIME_RUNBOOK.md` | Host local inference |
| Whoosh'd healthy but model missing | `curl http://127.0.0.1:8000/v1/models` | Model inventory |
| Compose contract assertion fails | `/tmp/codexify-whooshd-smoke.compose.yml` | Runtime config |
| `/health/chat` degraded | `docker compose logs --tail=120 worker-chat redis` | Queue and worker |
| Supported-path proof fails at retrieval | document worker logs and `docs/audits/supported_path/` artifact state | Upload/embed/retrieval |

## Operator Interpretation

Passing this path proves only the current local Docker Compose beta surface exercised by the smoke/proof commands: provider posture, backend health, queue/worker health, chat completion, document upload, embedding readiness, and retrieval readback.

It is not proof of federation, Pattern/Instance sync, cross-device replication, graph-write enablement, desktop packaging readiness, or autonomous execution.
