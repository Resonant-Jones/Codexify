ARTIFACT 5 — Embedding Visualizer Specification
Milestone 2 — Cognitive Legibility Suite
“Show me the shape of thought.”
1. PURPOSE

Modern RAG systems retrieve vectors. Codexify interprets vectors.
Users, however, cannot see vectors.

The Embedding Visualizer reveals the hidden semantic geometry behind Codexify’s cognition:

clusters

semantic neighborhoods

outliers

memory density

recency vs relevance

cross-thread overlaps

dimensional drift between model versions

vector provenance

embedding health (dead vectors, duplicates, noise)

This visualization becomes the Spatial Lens of the Diagnostics Suite.

2. LOCATION IN UI
Settings → Diagnostics → Embeddings

Directly adjacent to:

Memory Browser

Knowledge Graph (pending)

MCP Tool Logs (future)

This keeps all introspection tools strictly separated from the conversational surface.

Rationale:
The chat UI should feel alive and intelligent.
Diagnostics surfaces show why.

3. DATA SOURCES

Backend endpoint (already partially implemented via retriever):

GET /diagnostics/embeddings


Returns:

{
  "vectors": [
    {
      "id": "uuid",
      "text": "original content",
      "metadata": {...},
      "vector": [floats...],        # only in Dev Mode
      "timestamp": ...,
      "silo": "thread|memory|semantic|document|project"
    },
    ...
  ],
  "model": "embedding-model-name",
  "count": 12874
}


Frontend must request without vectors unless Dev Mode is toggled:

GET /diagnostics/embeddings?mode=public


Dev Mode requests full vectors:

GET /diagnostics/embeddings?mode=developer

4. FRONTEND FILE LOCATIONS
frontend/
  src/features/settings/diagnostics/
    EmbeddingVisualizer.tsx
    EmbeddingReducer.ts       # custom hook for DR pipeline
    useEmbeddingData.ts       # fetch, normalize, cache


Optional reusable components:

frontend/src/components/ui/ScatterPlot.tsx
frontend/src/components/ui/Legend.tsx
frontend/src/components/ui/ZoomPanCanvas.tsx

5. SPECIFICATION: UI LAYOUT
5.1 High-Level Structure
Embeddings
──────────────────────────────────────────────
Model: text-embedding-3-large (12,288 dims)
Vectors: 12,874 items
Last Refresh: 2 minutes ago

[Control Panel] [Legend]

──────────────────────────────────────────────
[Main Canvas — 2D/3D projection of vectors]
──────────────────────────────────────────────

[Item Inspector]

6. INTERACTION MODEL
6.1 Controls

Projection Algorithm

PCA

t-SNE

UMAP (default)

Cluster Lens

silo

thread

timestamp buckets

similarity to selected point

Point Size

relevance

recency

uniform

Color Mode

silo-based (default)

thread clusters

heatmap of relevance

Dev Mode

toggle to reveal raw vector arrays

toggle to compute local neighborhood recomputation

6.2 Navigation

Pan: click + drag

Zoom: scroll

Select: click a point

Brush select: hold Shift + drag rectangle

Focus: double-click point = re-center

Details panel updates live

7. ALGORITHMIC PIPELINE
7.1 Preprocessing

Normalize vectors client-side before reduction (if developer mode):

center → length normalize → (optional) local whitening


If not dev mode, backend provides precomputed 2D/3D points:

GET /diagnostics/embeddings?projection=umap

7.2 Dimensionality Reduction

Pipeline:

raw vectors (12k x 4096) →
PCA 50 →
UMAP 2D


UMAP settings:

n_neighbors: 15
min_dist: 0.12
metric: cosine


Justification: preserves semantic structure + cluster integrity.

7.3 Clustering Model

Client-side K-Means (k auto-determined using silhouette score):

k ≈ sqrt(n/2)


Clusters are used for:

color coding (optional)

inspectability

isolating memory silos

8. VISUAL SPECIFICATION
8.1 Canvas

SVG + Canvas hybrid

High-performance rendering of 10–50k points

Uses react-zoom-pan-pinch or internal implementation

Point styles use Codexify tokens:

fill: var(--accent-weak)
stroke: var(--accent-strong)
radius: calc(2px + relevance * 2)


Light mode tokens automatically adapt.

8.2 Hover Behavior

Tooltip:

Text Preview (160 chars)
Score: (if available)
Silo: thread/document/semantic
Timestamp: ISO format

8.3 Selection Inspector

Right-side panel:

────────────────────────────
Selected Vector
────────────────────────────
Text (full)
Metadata (JSON)
Silo
Timestamp
Cluster ID
Nearest Neighbors (top 5)
────────────────────────────

9. PERFORMANCE RULES

Embedding Visualizer must:

lazy-load data

reuse projection results

memoize heavy transforms

downsample if > 20k vectors

avoid blocking the main thread (use WebWorker)

store recent projections in IndexedDB for fast reloads

10. TOKEN CONSTITUTION REQUIREMENTS

All UI components must use:

Color tokens
var(--panel-bg)
var(--panel-border)
var(--accent)
var(--accent-weak)
var(--accent-strong)
var(--text)
var(--muted)

Geometry tokens
var(--radius)
var(--card-radius)
var(--tile-radius)
var(--gutter)
var(--board-edge)

Should NOT use

raw px values except for hairlines

random border radii

custom shadows

inconsistent spacing

This artifact guarantees visual identity across the Diagnostics Suite.

11. TEST PLAN
Cypress Tests

cypress/e2e/diagnostics-embedding-visualizer.cy.ts

Tests:

Panel loads

Fetch endpoint hit

Projection algorithm switch works

Points render (≥ 100)

Hover tooltip appears

Selection panel updates

Dev Mode hides raw vectors

Dev Mode shows raw vectors

Clustering color modes toggle

Canvas zoom/pan works

Memory of last settings persists

12. GIT COMMIT TEMPLATE
feat(diagnostics): add Embedding Visualizer with UMAP projections and vector inspector

13. CLAUDE IMPLEMENTATION NOTES

Claude Code should:

Implement UI + reducer + hooks in isolated modules

Respect token constitution in every component

Not place any diagnostics UI in the chat interface

Reuse the MemoryBrowser styling and card geometry

Implement WebWorker PCA/UMAP only if developer mode requested

Add mock API responses for local testing