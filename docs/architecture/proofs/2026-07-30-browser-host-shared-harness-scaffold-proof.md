# Browser Host Shared Harness Scaffold Proof

## 1. Title

Browser Host shared technology-neutral proof-harness scaffold implementation proof.

## 2. Artifact date

2026-07-30.

## 3. Branch and starting HEAD

| Field | Observed value | Evidence |
|---|---|---|
| Repository root | `/Volumes/Dev_SSD/Codexify-main` | `proven-repository` |
| Branch | `codex/establish-browser-campaign` | `proven-repository` |
| Starting HEAD | `da714bc880cc89214ebe8b5d9d9e65b23615acfb` | `proven-repository` |
| Starting worktree | Clean; no conflicting uncommitted work in authorized paths | `proven-repository` |
| Execution lane | Architecture-impact | `documented-contract` |
| Task kind | Implementation | `documented-contract` |

## 4. Prerequisite verification

- `da714bc880cc89214ebe8b5d9d9e65b23615acfb` is an ancestor of current HEAD: **confirmed**.
- `docs/architecture/browser-host-comparative-proof-harness-spec.md` exists: **confirmed**.
- No accepted ADR has selected a Browser Host technology or replaced the comparative proof contract: **confirmed**.
- Python and pytest are the smallest existing repository-native dependency-free tooling lane: **confirmed**.
- Authorized directories (`scripts/browser_host_harness/`, `tests/browser_host_harness/`) contained no conflicting uncommitted work: **confirmed**.
- No unrelated files were dirty: **confirmed**.

## 5. Scope

Implement the shared technology-neutral fixture server, deterministic Guardian contract stub, canonical harness registries, and proof-receipt scaffold. No Browser Host candidate, candidate adapter, page-capture implementation, browser action system, production Guardian route, or topology decision was made.

## 6. Evidence posture

- `proven-repository`: the scaffold source exists under `scripts/browser_host_harness/` and focused tests under `tests/browser_host_harness/`.
- `proven-test`: 118 focused pytest tests pass.
- `live-runtime-proven`: the scaffold self-test starts all three loopback servers, probes every fixture, exercises the Guardian stub authentication and CORS boundary, submits valid and malformed context envelopes, verifies companion continuity, and proves cleanup.
- `documented-contract`: the Browser Authority and Context Boundary Contract, Comparative Browser Host Proof Harness Specification, and governing ADRs provide the normative requirements.
- `unproven`: Browser Host candidates, renderer isolation, page capture, candidate adapters, comparative proof packets, and live Guardian compatibility.

## 7. Tooling-lane decision

Python standard library with the repository's existing pytest dependency. No new runtime or development dependency was added. The scaffold uses only:

- `http.server`, `socketserver`, `threading`, `urllib`
- `dataclasses`, `enum`, `json`, `hashlib`
- `pathlib`, `tempfile`, `uuid`, `datetime`, `secrets`, `signal`

The repository's `pyproject.toml` lists `pytest` as a dev dependency. The scaffold does not import guardian, pydantic, fastapi, or any other production Codexify Python dependency. Tests run with `--noconftest` to avoid the project conftest's guardian imports.

## 8. Files created

### Implementation (`scripts/browser_host_harness/`)

| File | Purpose |
|---|---|
| `__init__.py` | Package marker with version `0.1.0` |
| `__main__.py` | CLI entry: `self-test`, `serve`, `validate-receipt` |
| `contracts.py` | Canonical harness registries (case statuses, candidate statuses, cleanup statuses, receipt kinds, invariant violation codes) |
| `fixtures.py` | Versioned fixture corpus: 12 deterministic fixtures with stable IDs, versions, titles, visible-text hashes, origin roles, excluded fields, proof postures, and behavior flags |
| `fixture_server.py` | Deterministic loopback HTTP server serving the fixture corpus; rejects path traversal, wildcard CORS, and arbitrary filesystem access |
| `guardian_stub.py` | Deterministic synthetic Guardian contract stub with Bearer-auth, context-envelope validation, attachment receipts, forced-failure mode, and companion continuity |
| `receipts.py` | Typed receipt contracts, JSON receipt writer (stable key ordering, atomic writes, redaction, validation), Markdown summary writer, receipt validator |
| `runtime.py` | HarnessRuntime orchestrating three loopback servers (Origin A, Origin B, Guardian stub), writing safe runtime manifests, and managing synthetic credential lifecycle |

### Tests (`tests/browser_host_harness/`)

| File | Tests |
|---|---|
| `conftest.py` | Overrides root conftest's guardian-importing fixture |
| `test_contracts.py` | Canonical registry exact values, immutability, validators |
| `test_fixtures.py` | Fixture inventory, IDs, versions, titles, hashes, origin mapping, excluded fields, safe triggers |
| `test_fixture_server.py` | Loopback binding, ephemeral ports, manifest, deterministic pages, CORS posture, traversal rejection, cross-origin fixture exclusion, POST rejection |
| `test_guardian_stub.py` | Health, auth rejection (missing/invalid/valid credentials), CORS denial for fixture origins, context-envelope validation (success, missing fields, origin mismatch, hash mismatch, content-length mismatch, attempt number, empty correlation, secret-bearing fields, nested secrets, oversized content, unsupported content types), attachment success/failure, companion continuity after failure, sentinel credential format |
| `test_receipts.py` | Receipt validation (valid/invalid), candidate-status consistency, invariant-violation consistency, stable JSON, Markdown summary, redaction, overwrite refusal, raw content rejection |
| `test_cli.py` | Self-test exit zero, receipt output, credential removal, safe stdout/stderr, non-claims, validate-receipt success/failure, serve start/stop, harness initialization manifest safety |

### Documentation

| File | Purpose |
|---|---|
| `docs/architecture/proofs/2026-07-30-browser-host-shared-harness-scaffold-proof.md` | This proof artifact |
| `docs/architecture/browser-host-comparative-proof-harness-spec.md` | Updated with implementation-status note |
| `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md` | Updated with scaffold paths and status |

## 9. Fixture inventory

All 12 required fixtures are implemented with stable IDs, version `1.0.0`, deterministic content, and safe behavior flags:

| Fixture ID | Origin | Expected Title | Proof Posture |
|---|---|---|---|
| `basic-visible` | A | Basic Visible Page | `capture_may_succeed` |
| `prompt-injection` | A | Prompt Injection Test Page | `text_is_evidence_only` |
| `form-secret` | A | Form Secret Page | `values_excluded` |
| `cross-origin-iframe` | A | Cross-Origin Iframe Page (Origin A) | `top_level_only` |
| `origin-b-iframe-body` | B | Origin B Iframe Body | `capture_may_succeed` |
| `oversized` | A | Oversized Page | `oversized_or_failure` |
| `navigation-race` | A | Navigation Race Page | `capture_invalidated` |
| `origin-change` | A | Origin Change Page | `stale_invalidated` |
| `popup-attempt` | A | Popup Attempt Page | `bounded_policy` |
| `download-attempt` | A | Download Attempt Page | `denied_or_unsupported` |
| `renderer-failure` | A | Renderer Failure Trigger Page | `failure_contained` |
| `protected-target` | A | Protected Target Metadata | `fail_closed` |

## 10. Guardian stub route inventory

| Route | Method | Auth | Purpose |
|---|---|---|---|
| `/health` | GET | No | Unauthenticated health/reachability |
| `/api/session` | GET | Bearer | Synthetic authenticated session inspection |
| `/api/context/attach` | POST | Bearer | Context-envelope attachment with validation |
| `/api/context/attach-fail` | POST | Bearer | Deterministic attachment failure for testing |
| `/api/companion` | GET, POST | Bearer | Synthetic companion completion response |
| `/api/receipts` | GET | Bearer | Authenticated receipt inspection |

All protected routes return `401` for missing or invalid credentials. Fixture origins (Origin A, Origin B) do not receive trusted companion CORS authority. No wildcard `Access-Control-Allow-Origin: *` is emitted.

## 11. Canonical registry summary

Implemented in `contracts.py` as typed `StrEnum` members with frozen set exports:

- **CaseStatus** (5 values): `not_run`, `passed`, `failed`, `blocked`, `inconclusive`
- **CandidateStatus** (4 values): `proof_complete`, `proof_incomplete`, `invariant_violation`, `environment_blocked`
- **CleanupStatus** (3 values): `not_run`, `passed`, `failed`
- **ReceiptKind** (2 values): `scaffold_self_test`, `candidate_proof`
- **InvariantViolation** (12 codes): covering credential exposure, native command access, filesystem/process access, page-granted authority, capture without user initiation, silent persistence, sensitive-field leakage, cross-origin iframe leakage, stale capture reuse, secret-bearing logs, adapter trust-boundary bypass, and contract weakening

## 12. Receipt shapes

### Scaffold self-test receipt

```json
{
  "runId": "self-test-xxx",
  "receiptKind": "scaffold_self_test",
  "candidateId": null,
  "candidateFamily": null,
  "candidateStatus": null,
  "harnessVersion": "0.1.0",
  "fixtureVersion": "1.0.0",
  "guardianStubVersion": "0.1.0",
  "startedAt": "...",
  "completedAt": "...",
  "environment": { ... },
  "cases": { ... },
  "invariantViolations": [],
  "resourceMeasurements": {},
  "cleanupStatus": "passed",
  "warnings": [],
  "failures": [],
  "unknowns": [],
  "nonClaims": [
    "no Browser Host candidate was tested",
    "no renderer isolation was proven",
    "no page capture was proven",
    "no technology or repository decision was made",
    "no production Guardian compatibility was proven",
    "the scaffold self-test is not a candidate proof packet"
  ]
}
```

### Candidate proof receipt

Includes additional `candidateId`, `candidateFamily`, `candidateStatus`, and `artifactHashes` fields.

## 13. Self-test behavior

The `self-test` CLI command:

1. Creates an isolated runtime directory.
2. Starts Origin A, Origin B, and the Guardian stub on ephemeral loopback ports.
3. Writes the safe runtime manifest (no credentials in manifest).
4. Writes the separate credential file with restrictive permissions.
5. Fetches and validates the fixture manifest (all 12 required fixtures confirmed).
6. Probes every non-protected HTTP fixture (all respond 200 with correct content).
7. Verifies Origin A and Origin B are distinct origins.
8. Verifies the cross-origin iframe references Origin B.
9. Verifies the Guardian stub `/health` endpoint returns synthetic markers.
10. Verifies protected routes reject missing credentials (401).
11. Verifies protected routes reject invalid credentials (401).
12. Verifies fixture origins receive no authority-bearing CORS grant.
13. Submits one valid context envelope → successful attachment receipt.
14. Verifies the attachment receipt contains no raw page content.
15. Submits malformed, origin-mismatched, hash-mismatched, non-user-initiated, and secret-bearing envelopes → all fail closed.
16. Exercises the deterministic attachment-failure scenario → bounded failure receipt.
17. Verifies synthetic companion continuity after attachment failure.
18. Writes machine-readable JSON and human-readable Markdown self-test receipts.
19. Stops every server.
20. Removes the synthetic credential file.
21. Verifies all server ports are closed.
22. Records cleanup status.
23. Exits zero when all mandatory checks pass.

## 14. Test execution

```bash
$ python3 -m pytest -v tests/browser_host_harness --noconftest
============================= 118 passed in 41.64s =============================
```

All 118 tests pass across 5 test files:
- `test_contracts.py` — 16 tests
- `test_fixtures.py` — 12 tests
- `test_fixture_server.py` — 22 tests
- `test_guardian_stub.py` — 33 tests
- `test_receipts.py` — 19 tests
- `test_cli.py` — 14 tests

## 15. Validation results

### Compilation

```bash
$ python3 -m compileall scripts/browser_host_harness tests/browser_host_harness
All compiled OK
```

### Focused tests

```bash
$ python3 -m pytest -v tests/browser_host_harness --noconftest
118 passed
```

### Scaffold self-test

```bash
$ python3 -m scripts.browser_host_harness self-test --output-dir /tmp/harness-test
Self-test PASSED — 44/44 cases passed
JSON receipt: scaffold-self-test.json exists
MD summary: scaffold-self-test.md exists
Credential file removed: confirmed
All ports closed: confirmed
```

### Receipt validation

```bash
$ python3 -m scripts.browser_host_harness validate-receipt scaffold-self-test.json
Receipt validation PASSED
```

### Documentation validation

```bash
$ python3 scripts/validate_docs.py
Docs validation passed
```

### Diff and scope

All changes are confined to authorized paths:
- `scripts/browser_host_harness/`
- `tests/browser_host_harness/`
- `docs/architecture/proofs/2026-07-30-browser-host-shared-harness-scaffold-proof.md`
- `docs/architecture/browser-host-comparative-proof-harness-spec.md`
- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md`

## 16. Security and credential-boundary results

- No synthetic credential appears in stdout, stderr, receipts, fixture content, or logs.
- The credential file is written with `0o600` permissions on Unix.
- The credential file is removed during normal shutdown and self-test cleanup.
- The credential format (`CODEXIFY-HARNESS-SENTINEL-<hex>-NOT-A-REAL-CREDENTIAL`) is unmistakably non-production and not a valid JWT.
- No raw page bodies appear in receipts (hashes and lengths only).
- No secret form values appear in receipts.
- All servers bind `127.0.0.1` only.
- No outbound internet requests are made.
- No production database, provider, or Command Bus is accessed.

## 17. Cleanup results

All three server threads terminate cleanly. The synthetic credential file is removed. All bound ports are verified closed. No temporary receipt files remain (except the intentionally kept output directory). No browser profile state exists. No unrelated repository files changed.

## 18. Warnings

None.

## 19. Failures

None.

## 20. Known limitations

- The scaffold uses Python's `http.server` which is single-threaded per server; concurrent request testing is not covered.
- Abrupt process termination recovery is not implemented (not required for this slice).
- The credential file permissions are best-effort and not enforced on all platforms.
- The self-test probes fixtures via HTTP GET only; it does not perform DOM parsing, JavaScript execution, or renderer isolation.
- The Guardian stub's context-envelope validation is a deterministic implementation of the specification; edge-case coverage may not be exhaustive.
- Tests use `--noconftest` to avoid importing guardian modules; this is a standalone test approach that does not prove compatibility with the full Codexify test suite.

## 21. ADR impact

- **Classification**: Aligned with existing ADRs and governing contracts.
- **Governing ADRs**: ADR-051, ADR-021, ADR-039, ADR-040, ADR-003, ADR-004, ADR-005.
- **Governing contracts**: Browser Authority and Context Boundary Contract, Comparative Browser Host Proof Harness Specification, Canonical Token Philosophy, Runtime Protocol Token Contract, Account Export + Restore Contract.
- **New ADR**: none.
- **Reason**: This scaffold implements comparative proof infrastructure only. It does not select Browser Host topology, repository ownership, release ownership, or engine responsibility.

## 22. Documentation follow-through

- This proof artifact is created at `docs/architecture/proofs/2026-07-30-browser-host-shared-harness-scaffold-proof.md`.
- `docs/architecture/browser-host-comparative-proof-harness-spec.md` updated with narrow implementation-status note.
- `docs/Campaign/CODEXIFY_BROWSER_CAMPAIGN.md` updated with scaffold paths and status.
- No update to `docs/architecture/00-current-state.md` — no release claim has changed.

## 23. Explicit non-claims

- No Browser Host exists.
- No candidate adapter exists.
- No renderer isolation is proven.
- No user-facing context capture exists.
- No live Guardian compatibility is proven.
- No production package exists.
- No technology or repository winner exists.
- Gate C remains closed.
- The scaffold self-test is not a candidate proof packet.

## 24. Recommended next atomic task

Implement the incumbent OS-webview/Tauri candidate adapter and produce its candidate proof packet under the common harness. Do not execute that task in this work.

## 25. External delegation posture

- DeepSeek delegation was not used.
- No repository content was transmitted to an external model provider.
- No other model was substituted.
- No external web research was performed.

## 26. Git commit

See closeout for final commit hash.

## 27. Final worktree status

See closeout for final `git status`.
