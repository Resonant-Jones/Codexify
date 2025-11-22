# Graph vs RAG Evaluation Harness

This repo now ships a small, local-only harness for comparing plain RAG with RAG + Knowledge Graph context.

## Run Neo4j locally

```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/guardian \
  neo4j:5
```

## Required environment

```bash
export NEO4J_BOLT_URL=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=guardian
export GUARDIAN_ENABLE_GRAPH_LOGGING=true
export GUARDIAN_ENABLE_GRAPH_CONTEXT=true
```

## Run the benchmark

```bash
poetry run python -m guardian.eval.run_graph_rag_benchmark --compare
```

Outputs JSONL to `guardian/eval/output/graph_rag_<timestamp>.jsonl` with per-prompt results for `with-graph` and `without-graph` modes.

The harness is optional: if Neo4j is unavailable, normal RAG flows still work; graph context falls back gracefully.
