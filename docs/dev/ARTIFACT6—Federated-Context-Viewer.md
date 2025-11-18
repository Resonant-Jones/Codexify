ARTIFACT 6 — Federated Context Viewer
Milestone 2 — Task 3
The introspection portal for multi-node, multi-agent cognition.
1. PURPOSE

Codexify’s long-term architecture includes:

multi-node deployments

peer LLMs

distributed MemoryOS stores

cross-device semantic federation

vector routing between nodes

cluster-wide consensus modes

The Federated Context Viewer (FCV) exposes this distributed memory and semantic flow in a single unified diagnostic interface, letting the user see:

which nodes responded

their health

their semantic contributions

their memory contributions

routing latency

vector distances between nodes

which node “won” retrieval

node drift (embedding versions, model mismatch)

cross-node memory overlap

In short:
It shows how Codexify thinks when it thinks as a network.

2. FRONTEND LOCATION

Strict rule:
No federated UI in conversation surfaces.

Location:

Settings → Diagnostics → Federation


Sibling panels:

Memory Browser

Embedding Visualizer

Knowledge Graph (coming)

MCP Tool Inspector (later)

This keeps the cognitive machinery centralized and non-intrusive.

3. BACKEND ENDPOINT
REST Endpoint (initial):
GET /diagnostics/federation


Returns:

{
  "nodes": [
    {
      "id": "alpha",
      "name": "Primary Node",
      "region": "local",
      "status": "online",
      "latency_ms": 4.2,
      "model": "gpt-4.3",
      "embedding_model": "embedding-3-large",
      "vector_count": 288400,
      "recent_queries": 42,
      "health": {
        "cpu": 0.33,
        "ram": 0.58,
        "cache_hit_rate": 0.82
      },
      "contributions": {
        "semantic": 4,
        "memory": 2,
        "messages": 3
      },
      "semantic_vectors": [
        { "score": 0.932, "text": "...", "metadata": {...} },
        ...
      ],
      "memory_vectors": [
        { "score": 0.881, "text": "...", "metadata": {...} }
      ]
    },
    {
      "id": "beta",
      "name": "Auxiliary Node",
      "region": "remote",
      ...
    }
  ],
  "total_nodes": 2,
  "timestamp": "...",
  "thread_id": "42",
  "depth": "deep"
}

Future (Mesh Mode)

Support streaming events:

/diagnostics/federation/stream


But Phase 1 is static snapshots.

4. FRONTEND FILE LOCATIONS
frontend/src/features/settings/diagnostics/
  FederationViewer.tsx
  FederationNodeCard.tsx
  FederationDiagram.tsx
  FederationReducer.ts
  useFederationData.ts


Diagram renderer may live in:

frontend/src/components/ui/ForceGraph.tsx
frontend/src/components/ui/NodeMap.tsx

5. SPECIFICATION: UI LAYOUT
5.1 High-Level Visual
Federation Diagnostics
──────────────────────────────────────────────────

[Header Summary Card]
Nodes: 2 online   |   Thread: 42   |   Depth: deep   |   Snapshot: 1m ago

──────────────────────────────────────────────────
[Federation Diagram]
Graph of nodes with edges weighted by latency + contribution

──────────────────────────────────────────────────
[Node Cards]
Alpha Node (local)      Beta Node (remote)
- status, health, contributions, vectors

──────────────────────────────────────────────────
[Detailed Inspector]
Shows selected node’s semantic / memory contributions

6. COMPONENTS
6.1 FederationViewer.tsx

Root component responsible for:

fetching /diagnostics/federation

managing selected node

rendering diagram + cards + inspector

strictly using design tokens throughout

6.2 FederationNodeCard.tsx

Card layout (Token Constitution compliant):

var(--panel-bg)
var(--panel-border)
var(--text)
var(--muted)
var(--radius)
var(--card-radius)
var(--gutter)


Fields:

Name

Region

Latency

Status (badge: green/yellow/red)

Contribution counts

Embedding model

Vector count

6.3 FederationDiagram.tsx

Graph visualization using:

D3 force simulation

or react-force-graph-2d

or lightweight homebrew (recommended, <300 lines)

Node size: proportional to vector_count
Node color: online/offline + region
Edge thickness: inverse of latency

6.4 FederationInspector.tsx

Shows the clicked node:

health metrics

recent queries

semantic vectors (top 5)

memory vectors (top 5)

full metadata in collapsible JSON viewer

7. INTERACTION MODEL
Node Click:

highlight node in diagram

scroll to its card

open inspector panel

Hover:

Tooltip:

name
region
latency
contributions

Refresh:

Manual refresh button:

<Button onClick={refreshFederation}>


Auto-refresh every 10 seconds (optional).

8. FEDERATION LOGIC

Supports:

Single-node mode (local-only)

Multi-node cluster mode

Multi-region deployments

Experimental mesh-LLM networks

Code must gracefully degrade:

If 1 node → show simplified UI
If 0 nodes → show empty state
If > 20 nodes → auto-cluster nodes visually (force bundling)
9. TOKEN CONSTITUTION REQUIREMENTS

Strict rules:

✓ No hardcoded colors
✓ No raw radii
✓ No custom shadows unless defined via tokens
✓ Use var(--card-radius) for card containers
✓ Use var(--panel-bg) for card backgrounds
✓ Use var(--panel-border) for borders
✓ Use var(--text) and var(--muted) for typography
✓ Diagrams must inherit theme mode (light/dark) automatically

This ensures visual unity across Codexify’s face.

10. TEST PLAN
Cypress File:
cypress/e2e/diagnostics-federation-viewer.cy.ts

Tests:
General

Diagnostics → Federation tab visible

Viewer loads properly

No errors on single-node mode

No errors on empty federation

Diagram

Nodes render

Edges render

Hover tooltip appears

Clicking selects node

Node Cards

All nodes show correct metadata

Status colors render

Contribution counts correct

Inspector

Inspector shows for selected node

Semantic results visible

Memory results visible

Metadata JSON collapsible

Refresh

Manual refresh works

Auto-refresh updates graph

Total cases: ~15

11. GIT COMMIT TEMPLATE
feat(diagnostics): add Federated Context Viewer with node graph + inspector

12. CLAUDE IMPLEMENTATION NOTES

Claude Code should:

Create the new Diagnostics tab section

Implement FederationViewer.tsx with token-compliant styles

Add diagram rendering module

Integrate API fetch + polling

Build inspector pane using MemoryBrowser style

Ensure zero code leaks into conversational UI

Mock API for testing without backend