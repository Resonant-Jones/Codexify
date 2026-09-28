# AxisNode Whoosh'd Route Authority and Bundle Reconciliation

Date: 2026-09-23
Tracking: Codexify #815
Install-readiness classification: `ROUTE_AUTHORITY_CONFLICT`

## Baseline and authority

The Codexify checkout was `feature/ums-continued` at
`48bc4071a07453053d7794598cb2ac2e79e12f35`; that provider-readiness
receipt is in the current ancestry. The Whoosh'd checkout at
`/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd` was `main` at
`6d02b3fdf846339b3eabd86fcc80874be6507e1a`. Both checkouts had
pre-existing unrelated untracked files, left untouched.

| Surface | Authority established by current source |
| --- | --- |
| `v1-local-core-web-mcp` profile | Allowed local Whoosh'd provider/runtime posture and endpoint; no model ID pin |
| `docker-compose.whooshd-smoke.yml` | A smoke-only transport projection with four chat aliases pinned to `gemma-4-12b-it-qat-4bit` |
| Base Compose and AxisNode `.env` | Base Compose transports `LOCAL_CHAT_MODEL`; AxisNode's machine-local concrete selection is `gemma-4-e4b-it-4bit` |
| Whoosh'd registry | Candidate allowed IDs and physical paths, if that registry is selected by an installed service |
| Live Whoosh'd inventory | Current model availability; not observed in this task |
| Guardian health/catalog | Configured-versus-live runtime agreement; not queried in this task |

The packet's proposed `local-chat` authority is not present in these current
sources. `docs/architecture/00-current-state.md` names local inference and the
supported local profile but does not name a `local-chat` logical ID. ADR-074
governs **Tester** provider/model selection: `.env.tester` owns its concrete
local chat model, Compose transports it, and live inventory/Guardian health
must fail closed on disagreement. Its phrase "local-chat-model" describes that
selection role; it does not define a model ID `local-chat` for this AxisNode
profile. The named
`tests/architecture/test_supported_compose_local_model_projection.py` is not
present in this checkout. No current accepted source inspected here confirms
the packet's claim that the supported Compose projection selects `local-chat`;
the checked-in smoke overlay selects Gemma 12B instead.

AxisNode `.env` has matching `LLM_MODEL`, `DEFAULT_LOCAL_MODEL`,
`LOCAL_LLM_MODEL`, and `LOCAL_CHAT_MODEL` values of `gemma-4-e4b-it-4bit`.
Those values show internal alias agreement, but no current AxisNode operator
receipt inspected here explicitly declares this an intentional exact-model
override. The earlier configuration receipts record the value without granting
it that intent. Because the task's claimed normal route conflicts with the
current source and override intent is unproven, route authority cannot be
settled under the packet's proposed `local-chat` versus exact-override choice.
This is a task/source authority conflict, not a finding that ADR-074 and the
current local profile contradict each other. No model selection was changed.

## Candidate registry and launchd bundle shape

The tracked candidate registry is Whoosh'd `configs/models.yaml`. It has
enabled `gemma-4-e4b-it-4bit` and `gemma-4-12b-it-qat-4bit` entries, both with
`mlx_vlm` engines and paths under `/Volumes/Dev_SSD/whooshd/model-weights/`.
It has no `local-chat` entry. Both relevant physical paths were absent on this
AxisNode host during the check. No installed service definition identifies this
registry as active; YAML contents are configuration evidence, not live
inventory or installed-model proof.

The renderer and templates define a paired system launchd bundle:

| Label | Default executable / route |
| --- | --- |
| `com.resonant.whooshd` | Launcher default `/Users/chriscastillo/.local/bin/whooshd`; proxy `127.0.0.1:8000`; explicit Python selection; registry defaults to `configs/models.yaml` |
| `com.resonant.mlx-vlm-gemma12b` | `.venv311` Python under the historical Dev SSD checkout; sidecar `127.0.0.1:8082`; Gemma 4 12B model path under `/Volumes/Dev_SSD/whooshd/model-weights/` |

The Whoosh'd template uses explicit `--host` and `--port` arguments, not
`--codexify` or a wildcard bind. The sidecar default is Gemma 12B and therefore
does not implement an AxisNode E4B selection by itself. No physical model was
substituted to make the bundle render.

The existing AxisNode interpreter
`/Users/resonant_jones/Keep/Resonant_Constructs/Whoosh'd/.venv/bin/python`
was executable and successfully imported `fastapi`, `uvicorn`,
`pydantic_core._pydantic_core`, and `whooshd.app`. Renderer prerequisites were
otherwise absent: the default Whoosh'd launcher, default sidecar Python, and
default Gemma 12B model path do not exist here. Rendering was therefore not
invoked. No plist was generated, so `plutil -lint` and installer dry-run were
not applicable. Nothing was written under
`/tmp/axisnode-whooshd-launchd-reconcile/` or the Whoosh'd checkout.

## Safety and next prerequisite

No `.env`, Compose, profile, ADR, registry, Whoosh'd source, model, or launchd
definition was changed. No bundle was installed or registered, no listener was
created, and no Whoosh'd, MLX-VLM, Guardian, PostgreSQL, worker, or Scout
process was started. No model was downloaded, no inference ran, and no
Tailscale state changed. Final host checks found no TCP 8000 or 8082 listener;
both exact system launchd labels returned absent (exit 113); `docker ps` listed
only the pre-existing `codexify-redis-1`; and `tailscale serve status` returned
`No serve config`. This is static authority and deployment-shape qualification
only; it is not provider readiness or #815 closure.

The next #815 decision must establish from current accepted source or explicit
operator intent which model-selection mode AxisNode should use. If a stable
`local-chat` route is intended, its authority and physical mapping need a
separate scoped source/registry change. If an exact E4B override is intended,
record that operator decision and reconcile the service bundle and existing
model paths without silently changing Codexify routing. Machine-local launcher,
sidecar interpreter, and model-path prerequisites must be qualified before a
later render/install task. No new ADR or current-state/release claim is made by
this receipt.
