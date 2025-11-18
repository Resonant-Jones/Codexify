ARTIFACT 4 — COGNITIVE DIAGNOSTICS CANON
The Law of Insight Surfaces, Retrieval Transparency, and Mental Model Integrity

Purpose:
To define exactly how Codexify exposes internal cognition — RAG traces, memory retrieval, semantic context, embeddings, sensors, tool calls, and federated context — in a way that is:

Legible

Trustworthy

Non-intrusive

Token Constitution compliant

Architecturally consistent

Future-proof for advanced cognitive modules (Gate 3+)

This canon prevents UX drift, safeguards system clarity, and ensures all developers & agents build cognitive tools correctly.

0. DEFINITIONS (CANON ROOT)

These definitions anchor the canon and prevent ambiguity:

0.1 “Cognitive Surface”

Any UI element that exposes internal reasoning, context retrieval, memory artifacts, embeddings, tool traces, or model introspection.

Not conversation.
Not chat UX.
Not content creation surfaces.

0.2 “Diagnostic Panel”

A dedicated region (Settings → Diagnostics) where all cognitive surfaces live.
This is the only place where system cognition can be inspected directly.

0.3 “Retrieval Trace”

The ephemeral record of semantic search hits and MemoryOS recall chunks returned during a completion.

0.4 “Sensor Readouts”

CPU, memory, model load, active tools, federated peers, depth state.

0.5 “Insight Artifact”

A structured explanation built by the system (e.g., trace explanations, memory provenance, depth ladder summaries).

1. CANON OF LOCATION (WHERE COGNITIVE TOOLS MAY LIVE)
1.1 Chat surfaces must remain clean

No diagnostic elements may appear:

inside the message stream

near the composer

in the sidebar

inside message bubbles

in the thread list

overlaid on chat content

1.2 Cognitive tools belong in exactly three places:
A. Settings → Diagnostics TAB

Primary home for all inspectors and visualizers.

This includes:

Memory Browser (Task 2)

Embedding Visualizer

Knowledge Graph

MCP tool traces

Federated peer map

Model introspection

Context assembly graph

Retrieval score breakdown

Semantic density maps

B. Diagnostics Popovers (optional micro-tools)

Lightweight overlays opened explicitly by the user (e.g., right-click → “Inspect this message”).
Never auto-open.

C. Developer Mode Surfaces

Only activated via developer toggle.
Not exposed in production.

1.3 Never leak diagnostics into the primary interaction loop

The user should never feel the LLM is “thinking noisily.”

Diagnostics are opt-in only.

2. CANON OF SEPARATION (WHAT GOES WHERE)
2.1 Cognitive surfaces must separate conceptual layers:
Layer	Meaning	Surface
Evidence	Raw retrieved text chunks	Memory Browser
Context	Assembled bundle for the LLM	Context Composer View (Diagnostic Only)
Trace	How evidence was ranked and selected	RAG Trace Viewer
Insight	Human-readable explanation	Insight Panel (optional future component)
2.2 Chat should only expose “insight summaries” when requested

Not evidence.
Not raw retrieval.
Not embeddings.

Insights are meta-commentary the model can generate, but must not be auto-rendered.

3. CANON OF TOKEN COMPLIANCE (DESIGN TOKENS APPLY HERE)

All diagnostic surfaces must consume the same tokens as all other surfaces.

3.1 Required token usage

--panel-bg

--panel-border

--radius-tile

--card-pad

--shell-gap

--text

--muted

--bezel

--rim

--chip-bg

This ensures all cognitive surfaces visually match the Codexify aesthetic.

3.2 Glass Protocol Compliance

All cognitive cards must use:

FrameCard aberration={0}
RefractiveGlassCard intensity={0.006}
rounded-[var(--radius)]
clip-path inset(0 round var(--radius))


No exceptions.

3.3 Layout rules

Scrollable column

Max width: 72rem

Grid for multi-dimensional visualizers

Diagnostics surfaces must not overflow horizontally

4. CANON OF TRANSPARENCY (HOW COGNITION MUST BE EXPOSED)
4.1 Retrieval must be shown as-is

No rephrasing.
No rewriting.
No summarization.

4.2 Metadata must always show:

source (file, thread, silo, document)

score

silo

origin (semantic vs memory)

depth used

timestamp

threadId

4.3 Ordering rules

Semantic snippets first, sorted descending by score
Memory recall second, sorted descending by score

4.4 Provenance is mandatory

Every item must show:

Source: xyz.md / thread: 42 / silo: "architecture"

5. CANON OF COGNITIVE SAFETY (WHAT MUST NEVER BE DISPLAYED)
5.1 Never render model weights, logits, tokens, or chain-of-thought

This keeps Codexify safe, compliant, and aligned.

5.2 Do not show raw system prompts or internal system messages

Only sanitized “setup summaries” may be shown.

5.3 Never leak embeddings unless user is in Developer Mode

Embedding vectors are sensitive and must not leak by default.

5.4 No auto-updating diagnostics

User must intentionally navigate to Diagnostics.

6. CANON OF FUTURE EXPANSION (WHAT THIS ENABLES)

The Diagnostics Canon makes it possible to safely add:

6.1 Retrieval Graph

Visual DAG of how semantic and memory layers merge during context assembly.

6.2 Embedding Explorer

3D scatterplot or t-SNE/UMAP projection of memory chunks.

6.3 MemoryOS Silo Visualizer

Tabs for:

personal memory

project memory

thread memory

long-term memory

federated peers

6.4 Peer Node Map (Gate 4 Artifact)

Visual cluster of connected Codexify instances.

6.5 Event Trace Inspector

All MCP calls, tool calls, external API invocations.

7. CANON OF TESTING (WHAT MUST ALWAYS BE VERIFIED)

Every cognitive surface must include tests for:

rendering

empty state

trace load

metadata correctness

depth state correctness

navigation persistence

token compliance

panel behavior

overflow + scroll behavior

dark/light theme

ARTIFACT 4 COMPLETE