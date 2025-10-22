# Guardian Graph Tests

This project uses Neo4j for graph-backed features. The tests assume a
canonical relationship direction and perform a small deterministic seed at
test start so results are stable across runs.

## Canonical Direction

- Message to User: `(:MessageNode)-[:SENT_BY]->(:UserNode)`

Keep this direction in seed scripts, queries, and neomodel relationships to
avoid confusion.

## Deterministic Seed

`guardian/conftest.py` provides a session-scoped, autouse fixture that:

- Creates uniqueness constraints:
  - `UserNode.uid`
  - `MessageNode.message_id`
- MERGEs one message and one user and MERGEs `(m)-[:SENT_BY]->(u)`

This runs on best-effort basis and logs a warning if Neo4j is unreachable.

Environment variables honored (any of the following):

- `NEO4J_BOLT_URL` or `BOLT_URL` (e.g. `bolt://neo4j:guardian@localhost:7687`)
- `NEO4J_USER` or `NEO4J_USERNAME`
- `NEO4J_PASS` or `NEO4J_PASSWORD`

Start Neo4j for local runs:

```
docker compose up -d neo4j
```

## Diagnostic Endpoint

The API exposes a lightweight self-check endpoint:

- `GET /meta/selfcheck` — performs an epistemic self-check and appends a line to
  `guardian/logs/selfcheck.jsonl`. This endpoint is unauthenticated by design
  (similar to `/healthz`) for quick diagnostics.

## Quick Test Loop

```
export BOLT_URL=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASS=guardian

pytest -q guardian/tests/graph/test_neo4j_connection.py::test_relationships_exist
```

If the seed ran successfully, this should return a passing test.

