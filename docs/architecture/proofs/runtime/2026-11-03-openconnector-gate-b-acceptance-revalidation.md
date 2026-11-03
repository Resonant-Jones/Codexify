# OpenConnector Gate B — acceptance revalidation and closure decision

Date: 2026-11-03

## 1. Scope and evaluated commit

This receipt reconciles every original mandatory Gate B criterion against
accumulated implementation and evidence, and adjudicates closure. Evaluated
HEAD: `8154474f3` on branch `mcode/31b4bff7-5ff0-43f7-9879-7e88f1405a8e`.
Documentation-only task: no runtime source, test, configuration, ADR, or
release file was changed for this adjudication, and no trial was rerun.

Evidence posture: committed code and tests at the evaluated HEAD, their
recorded execution results, three live runtime receipts, pinned upstream
source, and accepted ADR/gate decisions. Executor summaries were not relied
on; the plan history, test bodies, and implementation files were inspected
directly. Private Gate A vulnerability details are not reproduced here; only
its acceptance status and disclosure boundary are cited (§6).

## 2. Frozen acceptance basis

Acceptance baseline: commit `31f9dde56` ("accept OpenConnector
delegated-custody amendments"), the commit immediately before Gate B
implementation began (first implementation commit: `85cf884ae`, adapter
core). Verified: `31f9dde56` is an ancestor of HEAD, and the plan's
`--follow` history shows the Gate B Aspect table unchanged in substance
since — later revisions are additive only (guard doctrine clarifications,
the synthetic-bindings test-seam note, slice status records, Slice 5/6
observations). No criterion was removed, weakened, or transferred out;
durable binding/grant persistence was assigned to Gate C in the baseline
itself, not moved later.

Original Gate B criteria (from `Gate B — Guardian read-only adapter and
Command Bus integration`, baseline §§ Purpose / Tests and observable
evidence / Prerequisites / Stopping condition):

- GB-01: adapter discover and execute paths proven against the gateway.
- GB-02: new routes in the manifest as `op::<id>` with
  read / read_only / safe / none.
- GB-03: reviewed, server-controlled read-only allowlist; on-list executes;
  off-list refused with no gateway call; a non-genuinely-read-only entry
  blocks the gate.
- GB-04: Guardian-profile denial and gateway-grant denial produce
  distinguishable bounded outcomes.
- GB-05: two-account Group 2 isolation reproduced through the Guardian
  adapter, not only against the raw gateway.
- GB-06: invocation observable with actor/subject/task lineage and no
  credential material (event stream + tool-turn read model).
- GB-07: redaction scan of run records/logs finds no token, secret, or
  admin token.
- GB-08: `GET /api/connections` projects the new entry with correct states;
  Notion/Drive projections byte-for-byte unchanged.
- GB-09: prerequisites hold (Gate A pass recorded; §4.7(a) amendments
  accepted; §3.1/§3.4 reviewed).
- GB-10: no stopping condition tripped (public route, bypass, credential
  leak, Notion/Drive change, second surface, connectors unquarantined).
- GB-11: authorized surface respected, `internal_only` posture retained.

Out of scope for Gate B by the baseline's own assignment (hence NOT
APPLICABLE, not deferred): durable binding/grant stores and binding-record
migration (Gate C prerequisites and surface); successful authenticated
provider retrieval (Gate D "Provider verification evidence: at least one
real provider API read"); hosted/service-to-service callability (deferred
to a separately authorized review; B mandates `internal_only`); release
qualification (Gate D; gate stays HOLD).

## 3. Accepted amendments and boundary decisions

- §4.7(a), accepted 2026-11-02 (commits `2b4541a9b`, `31f9dde56`):
  delegated custodian admitted as runtime binding only — never a catalog
  entry (B1), never a second identity authority (B2), custody is not
  authority (B3/B4), no second control surface (B6), posture unchanged
  (B7); companion ADR-094 amendment separates credential selection from
  invocation permission. Honored throughout.
- Later plan clarifications (synthetic-bindings test seam, guard doctrine)
  are additive and consistent; Slice 5's live credential-bearing isolation
  satisfies both the original "through the Guardian adapter" wording and
  the clarified seam description.
- §4.7(c) catalog-identity confirmation was a Gate C prerequisite at
  baseline; Slice 6 satisfied it early. Recorded as exceeded, not as a
  boundary change.

## 4. Criterion matrix

Conventions: implementation files are under `guardian/connections/
openconnector/` (`adapter.py`, `authority.py`, `bindings.py`, `policy.py`,
`router.py`, `service.py`), plus `guardian/core/route_visibility.py`,
`guardian/command_bus/manifest.py`, `guardian/connections/catalog.py`.
Commits: S1 `85cf884ae`, route/command `d0ddd7d69`, authority separation
`ce66f82b3`, no-auth mode `3824262ef`, HN crossing receipt `caec5f007`,
isolation `7502a2493` + teardown `16dcfc5aa`, catalog `8154474f3`.
Receipts R-HN (live crossing), R-ISO (credentialed isolation), R-CAT
(Slice 6 projection). Recorded suite results: 287 passed / 7 live-gated
skips; isolation file 12 passed live in trial.

| ID | Requirement | Verdict | Evidence and reasoning |
| --- | --- | --- | --- |
| GB-01 | Adapter discover + execute proven | PASS | Synthetic adapter/service suites (`test_openconnector_adapter.py`, `test_openconnector_service.py`) plus live dispatches: 1 real HN dispatch (R-HN) and 2 real credentialed dispatches with correct selectors (R-ISO). Limitation: none material. |
| GB-02 | Manifest read/read_only/safe/none | PASS | `test_route_is_registered_as_a_read_command`, manifest visibility suite (`test_manifest_internal_command_visibility.py`), live manifest entry captured on the trial app object (R-HN). Public projection exclusion pinned by `test_route_is_absent_from_the_public_document`. |
| GB-03 | Reviewed allowlist; on-list executes, off-list refused silently; genuinely read-only | PASS | `policy.py` holds exactly two reviewed entries with recorded reviews (HN; aeroleads with pinned-source anchors `operationType: read` + provider-side GET, R-ISO §1). On/off-list dispatch tests; no-auth omission and explicit-selection tests; contradictory-entry refusal. No mutation-capable action reviewed. |
| GB-04 | Distinguishable Guardian vs gateway denials | PASS | Synthetic: `missing_profile` / `connection_not_granted` vs transport-mapped gateway codes. Live: Guardian 403s with zero dispatch (N1–N5) vs gateway 403 `connection_not_allowed` for foreign token pairing (R-ISO cases D/I). Layers never substituted for each other. |
| GB-05 | Two-account isolation through the adapter | PASS | Committed synthetic matrix (router + isolation files) and LIVE two-account credentialed isolation through the Guardian route over real HTTP (R-ISO matrix A–J): own-connection authorized/accepted, all cross/empty/revoked/unknown/revalidation cases zero-dispatch denials, gateway grant independently enforced. Exceeds the baseline wording. |
| GB-06 | Observable invocation, no credentials | PASS with limitation | Generic invocation-event recording is tested (`run.created`/`run.blocked` sequences via `store.list_events_after`); the openconnector command completes through that same `execute_invoke` path with actor attribution (`test_command_bus_invokes_the_internal_route`); result/redaction tests assert credential-free bodies; live correlation (`executionId`, `auditPersisted`) observed (R-HN). Limitation: no openconnector-specific event-*content* assertion; the mechanism is generic and tested, the command path is proven through it. |
| GB-07 | Redaction scans clean | PASS with noted history | Committed scans (route bodies, recorded dispatches, live evidence: 0 matches for all trial secrets). History: one trial-harness logging slip printed two trial token values to a session log; contained (trial-only, loopback-only, predecessor revoked, all state destroyed, final scans zero). A passed scan is not claimed as proof nothing was ever logged — the slip is disclosed, not concealed. |
| GB-08 | Catalog projects entry; Notion/Drive unchanged | PASS | `aeroleads` entry (partial/unavailable, existing adapter binding, no setup surface) with projection test at route level; catalog delta exactly +aeroleads over the 59-id baseline; Notion/Drive field-verified unchanged; existing catalog suites green unmodified except the two web-matrix updates the new entry required. |
| GB-09 | Prerequisites hold | PASS | Gate A conditional pass recorded in plan; §4.7(a) amendments accepted 2026-11-02 (`2b4541a9b`, `31f9dde56`); §3.1/§3.4 reviewed in plan. |
| GB-10 | No stopping condition tripped | PASS | No public route (visibility tests); no bypass (auth/permission tests incl. no-authorizer-configured denial); no credential leak (scans); Notion/Drive unchanged (suites); connectors quarantined (profile + quarantine test); no second surface (no frontend/setup-route files changed). |
| GB-11 | Authorized surface respected | PASS | Delivered surface matches the baseline cell (package, GET-only router, allowlist, label `openconnector`, catalog entry, focused tests); label posture retained `internal_only`; binding/permission remain typed interfaces (durable stores untouched, per baseline). |

Counts: 11 criteria, 9 unconditional PASS, 2 PASS-with-limitation (GB-06,
GB-07 — limitations named above, neither conceals missing mandatory
evidence), 0 FAIL, 0 INCOMPLETE, 0 BOUNDARY CONFLICT, 0 NOT APPLICABLE
(the four out-of-scope items are classified in §2/§5, not in the matrix).

## 5. Evidence reconciliation

- Authorization (A): gate sequence inspected in `authority.py` /
  `adapter.py` — profile → binding → selection → token → revalidation →
  dispatch; binding-without-grant and grant-without-binding both denied
  with zero custodian contact (`ce66f82b3` + 6 tests); revocation stops
  retries (revalidation tests, live matrix H). Nothing inferred from
  success cases alone.
- Selection/isolation (B): synthetic matrix, 3 live Guardian dispatches
  with per-account selectors/bearers, 2 live gateway grant denials, and
  provider-side credential rejections are kept as four distinct evidence
  classes (R-ISO §4). No HTTP status is treated as provider success.
- Transport (C): R-HN establishes every listed element (real invoke,
  mounted route, auth + revalidation, real HTTP to the pinned digest,
  scoped Bearer, selector omission, 500 live story ids, bounded sanitized
  5204-byte result). Its limits are stated, not stretched.
- Retrieval vs rejection (D): the original criteria require on-list
  *execution against the gateway* (observed, twice, to provider contact)
  and gateway-enforced isolation — not successful authenticated retrieval,
  which the baseline assigns to Gate D ("at least one real provider API
  read"). No invented prerequisite; reasoning sourced to baseline §§6/Gate
  D above.
- Visibility (E): explicit-marker discovery, canonical-route authority,
  unchanged public surface, `local_safe` qualified as reported, hosted
  unqualified — and hosted was never a Gate B criterion (baseline mandates
  `internal_only`; hosted deferred to separate review). Not moved to Gate D
  by assertion: Gate D's own baseline text owns release/posture review.
- Policy/catalog (F): §4 rows GB-03/GB-08; catalog is visibility, never
  configuration or authorization (B3 honored; projection merges per-user
  state at request time).
- Safety (G): pinned digest inspected on running containers in both trials;
  guard present-asserted; scoped tokens only on execution paths; grants
  explicit; proxies/triggers blocked; loopback-only loopback deviation
  recorded with production target unchanged; teardowns verified (volumes
  destroyed, listings empty, listeners closed); redaction per GB-07.
  Controlled-trial cleanup is not claimed as a shared-deployment lifecycle
  (none exists; per-connection deletion endpoint absent, removal via volume
  destruction — R-ISO §6).
- Boundaries (H): durable stores, lifecycle, setup/OAuth, deletion/
  recovery → Gate C (baseline prerequisites/surface). Hosted invocation,
  private-network production deployment, adversarial multi-user, guard
  rotation, release → Gate D / separate review (baseline). Nothing
  originally assigned to B is left unproven.

## 6. Conflicts and limitations

- No criterion conflicts with another governing contract; no BOUNDARY
  CONFLICT exists.
- Known limitations (all previously recorded, none new): synthetic
  Guardian accounts and injected resolver/authorizer (durable variants are
  Gate C); fake provider credentials (isolation proven, retrieval success
  is Gate D); loopback-only trials (production network is Gate D);
  GB-06/GB-07 limitations as rowed.
- Gate A is cited for acceptance status (conditional pass, plan §6) and
  disclosure boundary (receipt branch-local, verified: no other branch
  contains its commits) only. No vulnerability detail reproduced.
- Release posture verified HOLD (`00-current-state.md` untouched by this
  task and by every Gate B commit).

## 7. Final disposition: CLOSED

Gate B is **CLOSED**. Decision-rule check: (1) all 11 mandatory criteria
PASS (two with named, non-concealing limitations); (2) §4.7(a) honored,
later clarifications additive; (3) no boundary conflict; (4) no invariant
contradicted (Guardian sole authority; custodian grants none; scoped and
deployment credentials separated; fail-closed throughout; Command Bus the
agent surface; catalog a projection; no second identity/authority; public
and release boundaries unchanged); (5) no criterion depends on later-gate
evidence (Slice 5/6 evidence is Gate B evidence); (6) no release claim
widened — closure explicitly does **not** authorize production deployment
or public release.

## 8. Remaining obligations by gate

- Gate C: durable binding + usage-grant stores and migration, user setup
  flow, lifecycle/revocation through the full path, re-run of the isolation
  matrix against durable stores (the baseline requires the re-run rather
  than carrying Slice 5 over as evidence), §4.7(b)/(c) as applicable.
- Gate D: adversarial multi-user, guard rotation, recovery dispositions,
  private-network production deployment, real provider reads, release
  review; gate stays HOLD until its own evidence.
- Standing: branch remains local-only until the Gate A disclosure boundary
  is separately cleared; hosted callability stays under its separate
  review.

## 9. ADR impact

Aligned; no ADR change. ADR-071 (control plane, B1–B7 honored), ADR-075
(web/extract identity, taxonomy untouched), ADR-094 (separated credential
and permission facts), ADR-024 (bounded outcomes), ADR-077 (provider
credentials never entered untrusted environments), ADR-092 (credential
lanes separated). No contradiction found; none needed as BOUNDARY CONFLICT.

## 10. Documentation and release-truth impact

Two files changed by this task: this receipt (new) and the Gate B
disposition note in the integration plan (acceptance section only; slice
records preserved; no ADR, current-state, or release edits). Release truth
remains `00-current-state.md`: HOLD, unchanged.
