# AxisNode Whoosh'd 12B Prerequisite Proof

Date: 2026-09-23
Tracking: Codexify #815 (parent #813)
Classification: `WHOOSHD_12B_MULTIPLE_BLOCKERS`

## Authority and checkout baseline

This applies the committed `AXISNODE_EXACT_12B` operator decision at
`6718edf97f843c03b09f6b573435534f4b1efc31`; that commit was the current
Codexify `feature/ums-continued` HEAD before this receipt and passed the
ancestor check. The Whoosh'd checkout at
`/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd` was `main` at
`6d02b3fdf846339b3eabd86fcc80874be6507e1a`. The Codexify checkout had
pre-existing untracked pre-commit caches, `.pytest_out.txt`, and Scout files;
Whoosh'd had one pre-existing untracked Pi session HTML file. They were left
untouched.

`docs/architecture/00-current-state.md` remains release truth. ADR-074's
concrete model-precedence rules govern the Tester profile; this receipt applies
the separately recorded AxisNode machine-local choice and creates no general
model-selection rule or new ADR. The supported local profile allows the local
provider posture but does not pin this model ID. Registry YAML is inactive
configuration evidence, not live inventory.

## Machine-local configuration and Compose projection

Codexify `.env` is ignored by `.gitignore`, is not tracked, and was not staged.
Each of its four model keys occurred exactly once with the expected old value.
Only these assignments changed:

| Key | Before | After |
| --- | --- | --- |
| `LOCAL_CHAT_MODEL` | `gemma-4-e4b-it-4bit` | `gemma-4-12b-it-qat-4bit` |
| `LOCAL_LLM_MODEL` | `gemma-4-e4b-it-4bit` | `gemma-4-12b-it-qat-4bit` |
| `LLM_MODEL` | `gemma-4-e4b-it-4bit` | `gemma-4-12b-it-qat-4bit` |
| `DEFAULT_LOCAL_MODEL` | `gemma-4-e4b-it-4bit` | `gemma-4-12b-it-qat-4bit` |

The SHA-256 of `.env` with those four values replaced by `<MODEL>` matched
before and after:
`69bcef6c591b9fca43a4b033fb8c155c98255aa666028c00b38f7864c412b818`.
This byte-level masked comparison covers every other line, including provider,
auth, endpoint, and persistence settings. The inspected non-secret values
remained `GUARDIAN_AUTH_MODE=local`,
`CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`, `LLM_PROVIDER=local`, and
`LOCAL_BASE_URL=http://host.docker.internal:8000/v1`.

`docker compose config --quiet` and the base plus
`docker-compose.whooshd-smoke.yml` `config --quiet` both passed. Filtered
resolved configuration for `backend`, `worker-chat`, and `worker-warmup` in
both projections showed `LLM_PROVIDER=local` and all four aliases set to
`gemma-4-12b-it-qat-4bit`. Compose was not started.

## Whoosh'd bundle inputs

| Input | Static result |
| --- | --- |
| Root | Existing Whoosh'd checkout above. |
| Whoosh'd Python | `/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd/.venv/bin/python` is executable; imports of `fastapi`, `uvicorn`, `pydantic_core._pydantic_core`, and `whooshd.app` passed. |
| Launcher | `.venv/bin/whooshd` exists and its shebang and `whooshd.cli` import resolve to this checkout. It is **not qualified** for the renderer's current plist: the plist supplies top-level `--host` and `--port`, whereas the current CLI accepts those only after `up` or `-d`. A non-executing parser check rejected the plist arguments with argparse exit 2. PATH, `.venv311/bin`, the current user's `.local/bin`, and the historical renderer default contain no other `whooshd` candidate. |
| Registry | Current `.env` names `configs/models.yaml`; that existing file contains enabled `gemma-4-12b-it-qat-4bit`, engine `mlx_vlm`, format `mlx`, text and vision modalities, `warm_on_first_use`, and chat priority. No separate upstream URL is set in this entry; the renderer's paired sidecar targets `127.0.0.1:8082`. |
| Sidecar Python | The existing Whoosh'd `.venv/bin/python` cannot import `mlx_vlm` (`ModuleNotFoundError`). The checkout `.venv311/bin/python` and historical Dev SSD `.venv311/bin/python` do not exist. No existing inspected interpreter qualifies. |
| 12B asset | Both the registry entry and renderer default point to `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`. That path and its configured Dev SSD root are absent. No other 12B cache root is specified by the inspected registry, renderer, runbook, or machine-local environment. No weight presence is proven. |

The renderer accepts explicit `--whooshd-root`, `--whooshd-python`,
`--whooshd-launcher`, `--model-registry-path`, `--mlx-vlm-python`, and
`--mlx-vlm-model-path` arguments, plus loopback hosts and ports 8000/8082. A
later render would use the following fixed inputs, after the three missing
prerequisites are repaired and requalified:

```text
--output-dir /tmp/axisnode-whooshd-12b-launchd
--whooshd-root /Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd
--whooshd-python /Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd/.venv/bin/python
--user resonant_jones
--model-registry-path configs/models.yaml
--whooshd-host 127.0.0.1 --whooshd-port 8000
--mlx-vlm-host 127.0.0.1 --mlx-vlm-port 8082
--mlx-vlm-model-path /Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit
```

The existing `.venv/bin/whooshd` is an incompatible candidate for
`--whooshd-launcher`; no qualified `--mlx-vlm-python` value exists, and the
listed model path is absent. Therefore no complete executable renderer command
can be supplied today. The renderer was not invoked, and no plist was written.

## Classification, safety, and next prerequisite

`WHOOSHD_12B_MULTIPLE_BLOCKERS` is the one classification. The independent
blockers are (1) a launcher compatible with the current plist's top-level
arguments, (2) an existing MLX-VLM-capable Python, and (3) the selected 12B
model asset at a configured usable path. The enabled registry and existing
Whoosh'd Python pass static qualification. The next #815 task should address
only these demonstrated prerequisites, then requalify the bundle before a
separate temporary render and installer dry-run. Model selection remains 12B.

Final `lsof` checks showed no listeners on TCP 8000 or 8082. Both exact system
launchd labels were absent (`launchctl` exit 113). `docker ps` could not read
the Docker socket in this managed session (permission denied), so container
state was not independently confirmed. `tailscale serve status` returned a
preferences-load error, so ingress state was not independently confirmed.
This task created no listener, launchd job, container, Tailscale change,
model download, Python package installation, Guardian/database/worker start,
or Scout action. No Whoosh'd source, registry, model, or launchd file changed.
No live inventory, Guardian route, Scout read, or release readiness is claimed.
#815 remains open.
