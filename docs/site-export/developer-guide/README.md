# Codexify Developer Guide Export Bundle

This directory is the expanded first-wave site-ready Developer Guide export bundle for Codexify.
It is intended to be copied into, transformed for, or used as a content source for `Codexify.Space.git`.

Suggested destination path:

- `/developer-guide/`

## What this bundle contains

- `index.md` for the main landing page
- `core-doctrines.md` for the operating doctrines that shape implementation decisions
- `runtime-truth.md` for current supported runtime reality
- `decentralized-infrastructure.md` for the product and architecture direction beyond the current supported runtime
- `architecture-map.md` for how to read the full guide set
- `runtime-topology.md` for the implemented runtime component map
- `chat-runtime.md` for queue-backed chat semantics and request-state boundaries
- `data-and-storage.md` for storage systems, entities, lineage, and restore obligations
- `config-and-ops.md` for operator truth, health, and provider governance surfaces
- `retrieval-and-context.md` for retrieval posture and orchestration boundaries
- `workspace-surface.md` for the Workspace design canon and supported views
- `identity-and-personas.md` for identity doctrine and persona boundaries
- `canonical-tokens.md` for canonical token doctrine across UI and runtime semantics
- `extension-boundaries.md` for bounded plugin and extension governance
- `pi-invocation-boundary.md` for the Pi invocation boundary contract
- `operator-truth.md` for release truth surfaces and known risks
- `proof-and-validation.md` for what counts as proof in this repository
- `export-manifest.json` for bundle metadata and publishing guardrails

## Source document anchors

This bundle is grounded in the following repo documents:

- `/docs/architecture/00-current-state.md`
- `/docs/architecture/README.md`
- `/docs/architecture/architecture-atlas.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- `/docs/architecture/data-and-storage.md`
- `/docs/architecture/config-and-ops.md`
- `/docs/architecture/modules-and-ownership.md`
- `/docs/architecture/runtime-diagrams-v1.md`
- `/docs/architecture/ui-diagrams-v1.md`
- `/docs/architecture/chat-runtime-contract.md`
- `/docs/architecture/runtime-protocol-token-contract.md`
- `/docs/architecture/account-export-restore-contract.md`
- `/docs/architecture/router-decision-table.md`
- `/docs/architecture/self-extending-agent-plugin-system.md`
- `/docs/architecture/agent-tool-loop-contract.md`
- `/docs/architecture/pi-invocation-boundary-contract.md`
- `/docs/architecture/codexify_workspace_surface_spec_v_1.md`
- `/docs/architecture/canonical-token-philosophy.md`
- `/docs/architecture/persona-studio-spec.md`
- `/docs/architecture/tech-debt-and-risks.md`
- `/docs/architecture/agent-protocol-operations.md`
- `/docs/dev/ARTIFACT1—UI-Token-Constitution.md`
- `/docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md`

## Publishing note

Do not publish unsupported claims from this bundle or from downstream site transforms.
In particular, do not publish autonomous execution claims, cloud-provider support claims, federation-as-shipped claims, or broader release promises unless those claims are later proven and reflected in the governing source documents.
