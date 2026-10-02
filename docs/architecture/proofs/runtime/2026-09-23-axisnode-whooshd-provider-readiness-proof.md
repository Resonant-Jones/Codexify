# AxisNode Whoosh'd Provider Readiness Qualification

Date: 2026-09-23
Tracking: Codexify #815
Classification: `WHOOSHD_INSTALLATION_NOT_FOUND`

## Scope and baseline

The canonical Codexify checkout was `feature/ums-continued` at
`1fa25d23ba6c9d7902042663bce75e67285c9533` before this receipt commit.
The provider-target correction commit is in its ancestry. Pre-existing untracked
files were left untouched. `.env` remained ignored and was read only through a
non-secret field projection. It still selected `GUARDIAN_AUTH_MODE=local`,
`CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`, `LLM_PROVIDER=local`,
`LOCAL_RUNTIME_PRESET=whooshd-mlx`, `LOCAL_PROVIDER_VENDOR=whooshd`, and
`LOCAL_BASE_URL=http://host.docker.internal:8000/v1`.

The supported profile requires the local Whoosh'd provider target on host port
8000. Current runbooks identify `/health` and `/v1/models` as host health and
inventory surfaces. The profile explicitly leaves model IDs to runtime
discovery; it does not require a `local-chat` model ID.

## Service and source inventory

Read-only AxisNode host checks found no TCP listener on port 8000 or the
upstream port 8082, no Whoosh'd or MLX process, no loaded
`com.resonant.whooshd` launchd job in the system or user domain, and no
Whoosh-named plist in the standard launch agent/daemon directories. No
`whooshd` executable was found on `PATH` or at `~/.local/bin/whooshd`.

A Whoosh'd **source checkout** exists at
`/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd`, on `main` at
`6d02b3fdf846339b3eabd86fcc80874be6507e1a`. Its `.venv/bin/whooshd`
executable exists. The checkout had a pre-existing unrelated untracked HTML
file, which was not touched. No installed launchd definition or running
process binds this checkout, interpreter, registry, model, and port into an
authoritative AxisNode service. The existing launchd installation procedure
would write persistent service definitions, outside this task's authority.
The Codexify `whooshd_ensure.sh` helper can launch a new daemon bound to
`0.0.0.0:8000`; it was not used as a substitute for the missing managed
service identity.

## Model routing and proof limits

AxisNode's machine-local `LOCAL_CHAT_MODEL` and `LOCAL_LLM_MODEL` both select
`gemma-4-e4b-it-4bit`. The Whoosh'd checkout's candidate `configs/models.yaml`
contains a `gemma-4-e4b-it-4bit` entry but no `local-chat` entry. No active
service definition establishes that this candidate registry would be loaded.
The task's expected stable `local-chat` route therefore conflicts with the
current Codexify model selection and is not established by the supported
profile. No physical model was observed running or advertised.

Final `lsof -nP -iTCP:8000 -sTCP:LISTEN` returned no listener. Health and
`/v1/models` were not queried because no identified Whoosh'd service was
listening. There is no live provider identity, inventory, model-route, or
readiness proof. No service logs were available from an installed Whoosh'd
job. The final `docker ps` listed only the pre-existing
`codexify-redis-1` container, and `tailscale serve status` returned
`No serve config`.

No Codexify or Whoosh'd configuration/source, model registry, alias, model,
launchd definition, or ingress state was changed. No provider, Guardian,
PostgreSQL, worker, or Scout process was started; no model was downloaded;
and no inference, migration, or database operation was run.

## Next #815 prerequisite

Identify or establish the authoritative AxisNode Whoosh'd service definition
and its selected registry through a separate authorized host setup task.
Resolve the `local-chat` expectation against current source and the intended
logical route before startup or readiness claims. Then qualify the service's
listener, Whoosh'd health identity, and live model inventory without swapping
models or silently changing routing. Guardian startup, private HTTPS, and
Scout's protected continuity read remain separate gates. This receipt does
not close #815 or change current-state, ADR, or release support claims.
