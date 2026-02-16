# Campaign: 2026-02-16 Compiled Audit (Security + MVP Core Loops + DX)

Source audit:
- audit_id: `AUDIT_2026_02_16`
- repo branch: `campaign/2026-02-15-controlplane`
- repo commit: `2136c0a1597e3dddb56e4f17664ef26beb34e61b`
- generated_at: `2026-02-16T03:41:52Z`

## Campaign Goal
Close the highest-risk configuration hygiene issue and make the MVP core loops deterministic and contract-aligned, with runnable validation commands/artifacts.

## Authoritative Findings Included
- RISK: `FINDING-2026-02-16-001` (local `.env` contains hardcoded credentials; `VITE_*` exposure risk)
- WARN: `FINDING-2026-02-16-003` (async RAG queue; frontend expects `response.data.context` but backend returns task metadata)
- WARN: `FINDING-2026-02-16-004` (SettingsView uses legacy migration route without API key)
- WARN: `FINDING-2026-02-16-005` (conditional `/media` mount may be absent; returned `/media/...` URLs 404)
- INFO: `FINDING-2026-02-16-006` (doc-upload loop not closed; depends on `/media` + embed worker)
- INFO: `FINDING-2026-02-16-007` (image-gallery loop not closed; depends on `/media`)
- INFO: `FINDING-2026-02-16-008` (image-gen loop not closed; depends on `/media`)
- INFO: `FINDING-2026-02-16-009` (doc-gen loop closed; add deterministic validation artifact)
- WARN (DX): `FINDING-2026-02-16-002` (model id discovery; `agent.model` is `unknown`)

## Global Runner Constraints (apply to every task)
- Preflight invariant: `git status --porcelain -uall` must be empty.
- If preflight fails, STOP and run cleanup commands exactly (task receipts include them).
- Scope invariant: only modify files listed in each task’s Allowed Files. If out-of-scope files appear in `git status`, STOP and clean them exactly as instructed by the task.

## Task Index
- 001: Security: env/secrets hygiene + safe templates/docs (F001)
- 002: DX: deterministic model-id discovery + prompt guidance (F002)
- 003: Backend: make `/media` serving reliable on fresh runtime (F005)
- 004: Frontend: Settings migration uses canonical authenticated endpoint (F004)
- 005: Fullstack: align async chat completion contract + trace retrieval (F003)
- 006: Tooling/Docs: deterministic RAG loop validation artifact (F003)
- 007: Tooling/Docs: deterministic doc-upload + embed validation artifact (F006)
- 008: Tooling/Docs: deterministic image-gallery + image-gen validation artifact (F007/F008)
- 009: Tooling/Docs: deterministic doc-gen validation artifact (F009)

## Task Mapping

001 -> [c48d3adc2cbe33610fa45516525c8fcbbbe71fc1, a6a7d9a5e4ef495eed8669c201d3e3b05071e6d7]
002 -> [e545e04c071db781d2756a245eba91aab5e9fb72, b3c4d495ee80a42c0cc8531689f7809ad0f59e14]
003 -> [f7f348dd0d056a38d98282be98ccabeb2e779641, e3da9a122b86d27056530e3e41358d8365db0a54]
004 -> [011838c656da427f0374dd0e951f5fc39cc8c661, b895b87d42e96f80a039c1a8557f9987d5c0b458]
005 -> [125f6b7094266d4cdf339e0596af03d408657d14, 208c1ab1efde46f83f8040509731a2a8e94cb975]
006 -> [17b463c5798aefb54ff1a80a21d5f790414e1ac0, 4f7589fdbf0879b52da6e6015a7bbfa5c2f32155]
007 -> [910cb682009f3249051406c4741c39ad99a8d9ec, 80115d93844754c1471ca637c77d6c22a2ae46ea]
008 -> [a3e3b82306999234d74c9158f28dc773534ff790, 9808d061312937b677d89ee4fa5c541415233b61]
