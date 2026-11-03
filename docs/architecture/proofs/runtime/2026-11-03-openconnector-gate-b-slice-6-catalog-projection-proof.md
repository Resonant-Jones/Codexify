# Gate B Slice 6 — AeroLeads catalog projection receipt

Date: 2026-11-03

Slice under test: catalog projection of the Slice 5–qualified provider onto
branch `mcode/31b4bff7-5ff0-43f7-9879-7e88f1405a8e` (evaluated at `16dcfc5aa`
plus the working-tree slice). No runtime, route, authority, transport, or
profile file was modified. No live gateway, real account, or production
credential was used or needed.

## Verdict

**PASS** — exactly one truthful `aeroleads` entry is projected; all
nineteen applicable acceptance conditions hold (custodian-as-entry,
taxonomy change, and setup-flow conditions were stop-gated, not exercised).

## 1. Identity decision (ADR-075)

- One entry, id `aeroleads`, display name `AeroLeads`. No `openconnector`
  entry (ADR-071 B1: the custodian is a runtime binding, never an identity).
  No second AeroLeads identity; nothing derived from gateway discovery.
- Category `web`: the reviewed operation retrieves structured data about a
  Web resource (a LinkedIn profile URL) through a Web-provider surface —
  ADR-075's stated `web` meaning.
- Capabilities `{extract}` only: the reviewed behavior satisfies the
  existing `extract` meaning; no corpus search exists, so `search` is not
  advertised.
- Not `knowledge`: AeroLeads is not an authenticated, user-scoped content
  repository; `content_search` / `content_read` are not repurposed.
- No category or capability token added to `guardian/protocol_tokens.py`.

## 2. Projection truthfulness

`implementation_state: partial` (adapter + internal-only read route exist;
setup, durable bindings, hosted callability unqualified).
`default_setup_state: unavailable` (no setup path exists). Auth vocabulary
`api_key` (how a future setup could authenticate — not a handler claim).
Runtime binding points at the existing subsystem and adapter; `setup_route`
is None, no OAuth handler, no registry id, no fields, no scopes. Description
and setup help state the limits: reviewed read-only action exists, execution
is internal-only, user setup unavailable, no connected account or
real-provider retrieval established, results are external evidence, and no
Beta support is claimed.

## 3. Before/after comparison

Baseline (parent commit): 59 ids. Current: 60 ids. Delta is exactly
`+aeroleads`; every baseline id still present. Notion and Google Drive
dictionaries verified field-by-field unchanged (implemented,
content_search/content_read, own setup routes).

## 4. Non-regression

- Public OpenAPI: no route added, moved, or re-exposed (this slice touches
  no route, visibility, manifest, adapter, or profile file); the OpenConnector
  route remains internal-only and absent from the public projection.
- Command Bus: command identity and visibility unchanged (existing manifest
  visibility suite passes unmodified).
- Legacy `connectors` route family still quarantined in the supported
  profile (verified in the profile file).
- Catalog construction performs zero network I/O (source scan plus a fresh
  `_build_catalog()` under a refusing socket); serialized entries carry no
  credential material.

## 5. Validation performed

- `pytest -v tests/connections/test_openconnector_catalog.py tests/connections/test_connection_catalog.py` — new file plus updated web-matrix expectations.
- `pytest -v tests/connections/ tests/command_bus/` — full regression.
- `make docs PYTHON=python3`, `git diff --check`, `git diff --name-only`.
- Bare-`python3` note: the declared dependency environment is the repo
  `.venv`; the exact working invocations are recorded in the closeout.

## 6. ADR impact and invariants

Aligned, no new ADR: ADR-071 (one control plane; B1 custodian-not-an-entry;
catalog owns no execution), ADR-075 (identity confirmed above; taxonomy
untouched), ADR-094 (no binding authority created or implied — the entry
confers no grant), ADR-024 (outcomes unchanged), ADR-092 (credential
classes untouched). All nine slice invariants hold; native Notion/Drive
precedence retained; no release claim widened.

## 7. What remains unqualified

Durable account bindings, real-credential provider success, hosted
invocation, Gate B completion, Gate C/D, release support. The next task per
the Slice 5 closeout was this projection; after it, Gate B is reassessed
against its original acceptance criteria without opening follow-on
implementation merely for improvement's sake.

## 8. Sensitive-content confirmation

This receipt contains no secret values, raw provider errors, or Gate A
exploit details: digests, ids, names, statuses, codes, and shapes only.
