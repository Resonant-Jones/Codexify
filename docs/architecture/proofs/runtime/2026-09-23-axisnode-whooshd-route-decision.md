# AxisNode Whoosh'd Model Route Decision

Date: 2026-09-23
Tracking: Codexify #815
Classification: `AXISNODE_EXACT_12B`

## Operator decision and scope

For the AxisNode #815 local Guardian/Scout qualification environment, the
operator explicitly selected the concrete Whoosh'd model ID
`gemma-4-12b-it-qat-4bit` in the current execution conversation. This is an
AxisNode machine-local decision, not a universal Codexify default, a change
to ADR-074, or evidence that the model is installed or live.

The active Codexify checkout was `feature/ums-continued` at
`e098e137fb2dc8b965efeccec5beb3df676935a7` before this receipt commit.
That commit contains the preceding
`2026-09-23-axisnode-whooshd-route-authority-reconciliation-proof.md`
receipt. Existing unrelated untracked files were preserved.

## Authority evidence

| Surface | Current checked-out evidence |
| --- | --- |
| `v1-local-core-web-mcp` | Allows the local Whoosh'd provider/runtime posture and endpoint; does not pin a model ID |
| AxisNode `.env` | `LOCAL_CHAT_MODEL`, `LOCAL_LLM_MODEL`, `LLM_MODEL`, and `DEFAULT_LOCAL_MODEL` all equal `gemma-4-e4b-it-4bit` |
| `docker-compose.whooshd-smoke.yml` | The same four chat aliases equal `gemma-4-12b-it-qat-4bit` in that smoke overlay |
| Candidate Whoosh'd `configs/models.yaml` | Both exact IDs are present and enabled as `mlx_vlm` entries; this inactive file is not live inventory |
| Operator decision | `gemma-4-12b-it-qat-4bit` is the intended concrete AxisNode #815 route |

The operator choice makes the current AxisNode `.env` E4B selection stale for
this qualification environment. It does not make the smoke overlay an
authority over `.env`; its 12B value happens to agree with the explicit
decision. ADR-074 supplies a useful separation among provider posture,
operator model selection, Compose transport, and runtime availability, but
its concrete authority rules are Tester-specific. This receipt does not extend
them into a new repository-wide AxisNode doctrine.

The candidate Whoosh'd registry's 12B entry is configuration evidence only.
No live Whoosh'd inventory, model installation, provider readiness, Guardian
runtime, or Scout read was proven. The existing renderer's Gemma 12B sidecar
model choice agrees in name with the operator decision, but its machine-local
launcher, sidecar interpreter, and 12B model paths were absent at the preceding
reconciliation check. A matching default is not a qualified service bundle.

## Single next prerequisite and safety

The next atomic #815 prerequisite is a separate machine-local configuration
and bundle-qualification task: correct the four AxisNode `.env` chat-model
aliases to the operator-approved 12B ID, then qualify the existing 12B
launcher, interpreter, registry, and model paths before rendering or
installing a service bundle. This decision task performs none of those steps.

No `.env`, Compose, supported-profile, ADR, registry, model, or source file was
changed. No model was downloaded, no plist was rendered or installed, and no
Whoosh'd, MLX-VLM, Guardian, database, worker, or Scout service was started.
No Tailscale state changed and no inference ran. #815 remains open; this
receipt does not change current-state or release claims.
