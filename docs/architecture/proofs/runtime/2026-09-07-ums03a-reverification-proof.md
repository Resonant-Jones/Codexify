# UMS-03A Independent Reverification Proof

Date: 2026-09-07

Status: **REVERIFIED — INDEPENDENT PROOF PASS**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: proof (independent revalidation of a prior commit)
- Evidence posture: read-only inspection of the exact committed UMS-03A
  artifact in an isolated detached worktree; no re-implementation, no
  edit of the original four UMS-03A files
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03A-Q (independent revalidation of UMS-03A)
- Reviewer: second harness (official), distinct from the originating
  Pi harness whose closeout was not inspectable
- Starting HEAD (reverifier-side): `12075540e29077a40a7d578eef315bc4277c0841`
- Target commit prefix: `12075540e`
- Resolved full SHA: `12075540e29077a40a7d578eef315bc4277c0841`
- Original commit subject: `Freeze canonical memory envelope`
- Original commit author: `resonant-jones <jones@resonantconstructs.ai>`
- Original commit date: `2026-09-07 07:43:40 -0400`
- UMS-01 prerequisite state: CLOSED
- UMS-02 prerequisite state: CLOSED (UMS-02C PostgreSQL-qualified)
- UMS-03 prerequisite state: AUTHORIZED
- This proof does not run a live PostgreSQL qualification and does not
  exercise compatibility readers. It validates the *committed* UMS-03A
  contract and proof receipt against the UMS-03A acceptance surface.

## Topology verdict

The reported commit prefix `12075540e` resolves uniquely to the full SHA
`12075540e29077a40a7d578eef315bc4277c0841`. The target is the current
HEAD of the active `main` checkout — `git merge-base --is-ancestor` of
the target against HEAD returns true and the resolved SHAs are equal.
No rebasing, amendment, or topology corruption was required to inspect
the committed artifact.

```text
TARGET = 12075540e29077a40a7d578eef315bc4277c0841
HEAD   = 12075540e29077a40a7d578eef315bc4277c0841
TARGET_IS_ANCESTOR_OF_HEAD  (trivially; target == HEAD)
```

The active `main` branch is diverged from `origin/main` (13 local vs 14
remote); nothing was pushed as part of this revalidation. A push would
*reduce* the divergence; reverification does not change it.

## Original file set (exact)

`git diff-tree --no-commit-id --name-status -r <TARGET>` returns exactly
four UMS-03A-owned files and nothing else:

```text
M  docs/Campaign/unified-memory-store/README.md
M  docs/architecture/00-current-state.md
A  docs/architecture/proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md
M  docs/architecture/unified-memory-store-contract.md
```

Scope check:

- documentation only — no Python, no SQL, no YAML/JSON config;
- no ORM model;
- no Alembic migration;
- no runtime, retrieval, broker, classifier, or import code;
- no account-export or account-restore code;
- no test fixture;
- no unrelated file.

The `A` (added) status correctly distinguishes the new proof receipt
from the three modified files. Total churn per the original commit
stat: 4 files changed, 763 insertions(+), 2 deletions(-).

## Inspected pre-read (UMS-03A-Q spec items 1–11)

The following required pre-reads were inspected during this
reverification:

- `docs/architecture/00-current-state.md` — read in full.
- `docs/architecture/README.md` — read in full.
- `docs/architecture/adr/adr-index.md` — read in full.
- `docs/architecture/adr/081-project-ownership-authority.md` — read in
  full.
- `docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md`
  — read in full (top 80 lines confirm persona-profile-vs-account
  separation; full read of the original 03A contract already covered
  the binding authority sections).
- `docs/architecture/adr/083-memoryos.md` — **NOT PRESENT IN THE
  REGISTRY.** File-system check confirms no `083-*.md` file exists
  under `docs/architecture/adr/`. The ADR index jumps from
  `082-persona-profile-manifest-and-binding-authority` to
  `084-unified-account-owned-memory-store`. The original UMS-03A
  proof receipt documents this gap honestly as a documentation
  omission rather than as an architecture conflict: ADR-084 is the
  controlling memory architecture decision, and the `Memoryos`
  external library is treated as read-only library-internal state
  (§4.6 of the contract, row 7). Per the UMS-03A-Q spec
  instruction "Do not repair or reinterpret the ADR during
  revalidation," this reverification records the gap and does
  *not* create or modify an ADR.
- `docs/architecture/adr/084-unified-account-owned-memory-store.md`
  — read in full (controlling decision; unchanged).
- `docs/architecture/unified-memory-store-contract.md` — read in full
  (1,484 lines); the UMS-03A additions are §4.6 through §4.15.
- `docs/Campaign/unified-memory-store/README.md` — read in full.
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md`
  — read in full.
- Complete diff and metadata for commit `12075540e` — inspected via
  `git show --format=fuller --stat` and `git diff-tree`.

## Cross-check verdicts (UMS-03A-Q spec items 5–17)

The following verdicts are produced by direct cross-check of the
committed contract against the UMS-03A acceptance surface. Line numbers
refer to the file as committed in `12075540e`.

### R5 — durable-memory inventory verdict: PASS

§4.6 of the contract (the inventory table at lines 590–598) covers all
seven admitted current source families and each row identifies every
required column:

- `memory_entries` (row 1, line 592) — `user_id` FK, no Project scope,
  no Persona attribution, episodic/semantic memory organized by
  retention silo, lifecycle = `silo ∈ {ephemeral, midterm, longterm}`
  plus `pinned` (priority), no provenance, retrieval consumers
  `guardian.core.pgdb` / `guardian.routes.memory` /
  `guardian.context.broker`, write authority
  `guardian.routes.memory` + external `Memoryos`, OMITTED from
  `account-export.v3`, canonical for its purpose but lacks envelope
  governance.
- `personal_facts` (row 2, line 593) — `user_id` (`String(255)` NOT
  NULL, no explicit DB-level FK — the contract honestly notes this at
  line 608 as a UMS-03B follow-up), no Project scope, no Persona
  attribution, correctable verified/candidate fact, lifecycle
  `status ∈ {candidate, verified, disputed, archived}` plus
  `is_active` plus `confidence`, provenance indirect via
  `personal_fact_evidence.source_type`, retrieval consumers
  `guardian.routes.personal_facts` and `guardian.context.broker`
  (verified+active only per ADR-013), write authority
  `guardian.services.personal_facts` and
  `guardian.fact_candidate_pipeline`, OMITTED from `account-export.v3`,
  canonical for its purpose under ADR-013 and ADR-084.
- `personal_fact_evidence` (row 3, line 594) — ownership via `fact_id`
  FK, no Project scope, no Persona attribution, evidence backing a
  Personal Fact, append-only lifecycle, `source_type ∈
  {chatgpt_import, runtime_extraction, user_stated, user_corrected,
  claude_import}` provenance, retrieval via Personal Facts service
  and broker evidence rendering, write authority Personal Facts
  service, OMITTED, derived but durable.
- `personal_fact_revisions` (row 4, line 595) — ownership via `fact_id`
  FK, no Project scope, no Persona attribution, append-only audit
  trail, `actor / action / field_changed / old_value / new_value /
  reason / created_at` provenance, retrieval via Personal Facts
  service, OMITTED, canonical audit trail.
- Candidate / unreviewed fact (row 5, line 596) — same
  `personal_facts` ownership and scope, lifecycle `status ∈
  {candidate, disputed, archived}` or `is_active = false`,
  `source_type` distinguishes live-chat (`runtime_extraction`),
  explicit Vault (`user_stated`), and import (`chatgpt_import` /
  `claude_import`), durable candidate per ADR-084 with
  "storage ≠ ambient influence."
- Verified personal fact (row 6, line 597) — same `personal_facts`
  ownership, lifecycle `status='verified' AND is_active=true`, broker
  verified-active filter, canonical for its purpose with Personal
  Facts service review authority.
- `Memoryos` library state (row 7, line 598) — embedded account-keyed
  file paths, library-internal lifecycle, library-internal
  provenance, retrieval via `Memoryos Retriever` and chat completion
  prompt assembly, write authority `Memoryos Updater` and
  `memoryos.mid_term.compute_segment_heat`, not in account export,
  "not currently Postgres-canonical; reconciliation into the
  canonical envelope is deferred to a later contract and proof
  slice."

The inventory also includes the explicit notes (lines 602–624) that
record (a) the four `personal_facts`-family tables' OMITTED export
status, (b) the `personal_facts.user_id` FK gap and the UMS-03B
follow-up obligation, (c) the `Memoryos` library's
"not safely mappable" status, and (d) the absence of the
future `memory_records`, `memory_ordinary_payloads`,
`memory_persona_links`, and `memory_activation_projection` tables at
the current `main` HEAD.

Chat messages, documents, browser episodes, and arbitrary artifacts
are *not* silently reclassified as memory; the prior proof explicitly
excluded them and the contract only invokes them as evidence-bearing
surfaces where they appear in the compatibility matrix.

### R6 — canonical envelope categories verdict: PASS

§4.7 (lines 626–654) freezes the canonical envelope as 11 independent
semantic categories — Identity, Ownership, Scope, Semantic species,
Content / payload, Persona attribution (optional, zero or more),
Provenance, Governance, Lifecycle, Priority / decay control, and
Compatibility. The table at lines 637–647 lists every category with
its conceptual question and required/optional status. The closing
paragraph (lines 649–654) explicitly forbids a single field
(legacy `silo`, legacy `pinned`, comma-separated tag list) from
answering more than one category's question, and pins the legacy
`tags` text column on `memory_entries` as descriptive metadata only
and the legacy `silo` column as retention class only.

### R7 — semantic species verdict: PASS

§4.8 (lines 656–706) freezes the minimum three semantic species
required by current persistence:

1. **Episodic / semantic memory** — `memory_entries` row family with
   `silo ∈ {ephemeral, midterm, longterm}` as retention class.
   Creator authority: user (Vault, explicit remember) or legacy
   ordinary-memory writer. Review before ambient: yes, by default.
   Explicit recall before activation: yes. Provenance: yes (§4.10 →
   §4.11). Content form: mutable in place; revisioned on authority
   transitions. Map from current persistence: `memory_entries` row,
   all silos (table line 703).
2. **Verified personal fact** — `personal_facts` row where
   `status='verified' AND is_active=true`. Creator authority:
   Personal Facts service only. Review before ambient: yes (already
   verified). Explicit recall before activation: yes. Provenance: yes
   (Personal Facts evidence trail). Content form: revisioned,
   append-only mutations. Map from current persistence:
   `personal_facts` row in the verified+active subset (table line
   704).
3. **Candidate / unreviewed fact** — `personal_facts` row where
   `status ∈ {candidate, disputed, archived}` or `is_active=false`,
   plus live-chat `runtime_extraction` and import
   `chatgpt_import` / `claude_import` paths before approval. Creator
   authority: Personal Facts service or import pipeline. Review
   before ambient: required. Explicit recall before activation: yes
   (explicit grant only). Provenance: yes (Personal Facts evidence).
   Content form: revisioned, append-only mutations. Map from current
   persistence: same `personal_facts` row in the
   non-verified-or-inactive subset (table line 705).

The taxonomy is explicitly closed under current persistence
("closed under current persistence. New species must be introduced by
a future ADR / contract slice; this contract does not admit
speculative species for capabilities that have no current evidence")
at lines 686–689. No additional species are admitted by current
evidence; the proof at lines 116–127 records the same three and the
closed-taxonomy decision.

### R8 — ownership / scope / attribution separation verdict: PASS

§4.9 (lines 707–745) freezes the three independent authorities
explicitly:

```text
memory owner         = authenticated account principal
memory scope         = account or one Project (ADR-081 governed)
memory attribution   = zero or more typed links to stable persona
                       subjects (UMS-02 governed; never mutable
                       PersonaProfile)
```

Forbidden anti-patterns (lines 720–729):

- `owner_persona_id` — a persona never owns memory;
- `persona_profile_id` as durable attribution — runtime profile
  configuration is not identity and must not be the attribution
  target;
- `projects.user_id` as the canonical memory owner — Project
  authority scopes but does not own;
- display names, names, prompts, avatars, similarity, Project IDs,
  Persona IDs, or PersonaProfile IDs as identity authority;
- `tags` as governance authority.

The earlier §4.3 (lines 244–282) already forbids
"owner_persona_id" (line 272). The future typed Persona link
vocabulary is `captured_under / suggested_by / associated_with`
(lines 277–279, restated at 735–737) and is declared sufficient to
represent current proven behavior; no additional typed-link value
is required by current evidence. A future slice that needs a new
typed-link value must add it to the canonical token registry before
it crosses the backend, frontend, or persistence boundary (lines
743–745).

### R9 — storage / review / activation / retrieval / influence separation verdict: PASS

§4.10 (lines 747–774) explicitly preserves the independence of
**stored**, **retrievable**, and **ambient-eligible**:

- **stored** — "a row exists and is queryable by its owner through
  a scoped query path" (line 752);
- **retrievable** — "the owner may issue an explicit recall grant
  that resolves the row and renders it into a turn-scoped context"
  (lines 754–755);
- **ambient-eligible** — "the row may enter provider context
  without an explicit recall grant, only after all policy gates
  in §3.5 pass" (lines 756–757).

The contract records that a record may be stored without being
ambient-eligible (every candidate fact), and retrievable without
being ambient-eligible (every imported fact in dormant posture);
ambient eligibility is granted only after both review and activation
authority approve *and* the §3.5 policy gates pass *and* the
explicit user consent state permits collection (lines 758–764). The
governing doctrine is preserved verbatim at lines 769–770:

```text
Automatic capture, explicit activation.
Retrievable != authorized for ambient influence.
```

§3.5 (lines 158–182) freezes the computed eligibility formula and
the read-time ambient-eligibility gate. No client, model, importer,
classifier, or UI writes final ambient eligibility; Guardian
computes it at read time (line 774).

### R10 — provenance doctrine verdict: PASS

§4.11 (lines 776–798) freezes the minimum provenance spine every
canonical memory record must retain, where applicable:

```text
source_system           ∈ {codexify, openai, anthropic, future registered}
source_record_id        stable source identifier when present
source_thread_id        nullable; canonical chat_threads row reference when present
source_message_id       nullable; canonical chat_messages row reference when present
source_import_job_id    nullable; account_import_jobs row reference for imported material
source_export_fingerprint
                         nullable; export hash when material was imported from an export
source_subject_kind     taxonomy of the originating surface
                         (chat, vault, importer, classifier, future registered)
source_subject_id       stable identifier of the originating surface entity
created_at, updated_at  server-generated authoritative timestamps
```

External lineage is preserved: "Imported content may normalize into
Codexify semantic species but must preserve its external lineage.
The presence of external provenance does not confer activation
authority" (lines 796–798). This covers the full §4.10 enumerated
origin taxonomy (Codexify-native creation, chat-derived candidate,
imported ChatGPT source, future Anthropic source, manual
user-authored memory, Persona-associated capture, derived
suggestion). The earlier §4.2 (lines 224–241) freezes typed
evidence and append-only revisions for ordinary memories,
including source user-message or Vault-action receipts and
mutation source (Vault, explicit chat instruction, confirmed
preview, classifier, importer, migration, restore, system decay).

### R11 — compatibility-read matrix verdict: PASS

§4.13 (lines 834–850) contains the full compatibility-read matrix
with one row per admitted legacy source plus explicit
`not safely mappable` rows. Each admitted source row resolves:

- semantic species;
- owner derivation;
- Project scope derivation;
- Persona attribution derivation;
- provenance derivation;
- activation / review interpretation;
- lossless fields (read projection);
- fields that cannot yet be represented;
- fail-closed conditions.

The `not safely mappable` rows (lines 848–850) explicitly cover:

- `Memoryos` library state — "current storage is library-internal,
  has no current account-export coverage, and has no current
  provenance spine; reconciliation into the canonical envelope is
  deferred to a future slice";
- `memory_entries` rows with malformed `silo`, missing `user_id`,
  or `user_id` not resolvable to a real `users.id` — "account
  ownership authority is ambiguous";
- `personal_facts` rows with `user_id` not resolvable to a real
  `users.id`, `status` outside the enumerated set, or evidence
  rows with unknown `source_type` — "review authority is ambiguous;
  provenance spine is incomplete."

§4.12 (lines 822–832) explicitly forbids compatibility reads from
backfilling canonical rows, mutating source rows, upgrading
candidates to approved, inferring Persona attribution, inferring
Project scope, erasing provenance, silently widening retrieval, or
introducing a second permanent source of truth.

### R12 — compatibility authority ordering verdict: PASS

§4.12 (lines 800–820) freezes both halves of the authority order:

Pre-cutover:

```text
legacy source row         = durable authority for that legacy record
compatibility envelope    = normalized read projection only
```

Post-migration (declarative only, not authorized by UMS-03A):

```text
canonical memory row      = durable authority
legacy compatibility path = migration / transition support only
```

UMS-03A explicitly does not authorize the authority transition:
"UMS-03A does not authorize the authority transition. That
transition belongs to a future implementation + migration proof
slice whose acceptance criteria will require UMS-03B's persistence
substrate, UMS-03C's dual-read sequencing, and UMS-04's export /
restore preservation" (lines 816–820).

### R13 — derived-state exclusions verdict: PASS

§4.7 closes the loop on derived state at lines 649–654 (no single
field answers more than one category's question) and §4.11 keeps
the provenance spine to *minimum* lineage, not to derived ranking
data. The later §4.4 "Activation projection" (lines 908–926) is
explicitly a *derived* state and §11 (lines 1279–1294) makes heat
projection rebuildable: "Heat projection can be dropped and
rebuilt without changing canonical truth." §15 (lines 1419–1439)
records that "Projection/index loss degrades ranking only," and
the failure-policy items in §16's proof gates (lines 1443–1464)
include "Heat projection can be dropped and rebuilt without
changing canonical truth" (item 11) and "Retired and dormant
records remain explicitly retrievable until purged" (item 12).
The proof at lines 289–306 records the canonical exclusion list
verbatim: heat, recency score, retrieval score, embedding vector,
ranking score, decay projection, working-set membership,
suggestion ranking, UI grouping. The mapping to UMS-10 as the
owner of derived heat projections is also recorded (line 305).

### R14 — fail-closed doctrine verdict: PASS

§4.14 (lines 852–878) freezes the eight fail-closed cases required
by the UMS-03A acceptance surface, in the exact order the spec
mandates:

1. account ownership cannot be proven (`user_id` not resolvable to
   a real `users.id`);
2. legacy semantic species cannot be determined (`silo`, `status`,
   `source_type`, or `is_active` outside its enumerated set);
3. activation status cannot be mapped safely (e.g. `evidence_meta`
   malformed or self-referential);
4. provenance required for a source cannot be preserved (e.g.
   evidence without a recognized `source_type`);
5. Persona attribution would require heuristic inference;
6. Project scope would require guessing;
7. one source maps ambiguously to multiple incompatible species;
8. normalization would erase revision or evidence semantics.

"A future migration may not 'best effort' any of these cases. The
acceptance criteria for the future migration proof slice must
enumerate the same fail-closed cases and prove each one is honored"
(lines 876–878). The `not safely mappable` rows in §4.13
(lines 848–850) instantiate three of these cases explicitly.

### R15 — physical design deferral verdict: PASS

§4.15 (lines 880–906) records the eleven deferred physical-design
questions:

- exact canonical table name and physical schema;
- exact primary-key representation (server-generated UUID vs.
  current autoincrement integer) and the export-stable identity
  contract;
- JSON column vs. typed columns for species payload;
- normalized provenance tables vs. embedded provenance columns;
- physical design of the Persona-link table, the link-type
  registry, and the half-open validity semantics for attribution
  history;
- exact lifecycle token registries (`active` / `dormant` /
  `retired` / `purged`) and which are physical columns vs. derived
  projections;
- exact revision table physical design;
- canonical migration revision identifier and the data-preservation
  acceptance criteria it must satisfy;
- write adapter surface for the Vault, explicit remember commands,
  classifier, and import paths;
- compatibility reader implementation shape (view, function,
  service);
- cutover and dual-read sequencing.

§4.15 closes with "This contract constrains those later choices
but does not pre-select them. UMS-03B is the next slice authorized
on PASS of UMS-03A" (lines 905–906).

### R16 — Campaign state verdict: PASS

The committed Campaign README (lines 109–113) contains the exact
required checkpoint:

```text
UMS-01: CLOSED
UMS-02: CLOSED
UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: PASSED
UMS-03: OPEN
UMS-03B: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
```

This reverification does *not* modify the Campaign README; the
UMS-03A-Q spec requires that the original Campaign README be left
unchanged. The reverification is *additive evidence* on top of
the existing UMS-03A block.

### R17 — current-state claim-discipline verdict: PASS

The committed `00-current-state.md` (lines 60–63 and 87–111)
records:

- UMS-03A as PASSED with the exact checkpoint quoted in R16;
- a UMS-03A narrative paragraph (lines 87–111) that names the
  frozen surface (memory-bearing source inventory, canonical
  envelope categories, semantic species taxonomy, compatibility
  matrix), the deferred surfaces (no `memory_records`,
  `memory_ordinary_payloads`, `memory_persona_links`, or
  `memory_activation_projection` tables exist; no compatibility
  reader is implemented; no retrieval behavior changed; no export
  implementation changed; no ADR was created or modified; ADR-084
  remains controlling);
- the explicit statement "UMS-03 remains OPEN, UMS-03B is
  authorized to start, UMS-04 is NOT AUTHORIZED. No Beta/release
  claim widened; no canonical memory persistence implementation
  exists yet" (lines 107–109).

The narrative does *not* claim canonical memory persistence
exists, that compatibility readers are implemented, that
retrieval changed, that Persona-aware recall exists, that
export/restore for canonical memory exists, that UMS-04 is
authorized, or that Beta/release support widened. The prior
"Release classes" section is unchanged.

## Isolated exact-commit validation (R18)

A detached worktree was created from the exact target commit and
exercised in isolation:

```bash
VERIFY_DIR=.verify-worktrees/ums03a-reverify
git worktree add --detach "$VERIFY_DIR" "$TARGET"
( cd "$VERIFY_DIR"
  /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/.venv/bin/python \
    scripts/validate_docs.py
  git diff --check HEAD^ HEAD
)
git worktree remove "$VERIFY_DIR"
```

Captured results:

- Detached worktree HEAD = `12075540e29077a40a7d578eef315bc4277c0841`
  (matches target).
- `scripts/validate_docs.py` exit status: 0; stdout:
  "Docs validation passed: required architecture docs, README
  links, and source headings verified."
- `git diff --check HEAD^ HEAD` exit status: 0; no whitespace
  diagnostics.

The worktree was removed after the run; `git worktree list` no
longer contains `ums03a-reverify` and the
`.verify-worktrees/ums03a-reverify` directory does not exist
post-cleanup.

## ADR alignment verdict

- ADR-081 (Project ownership authority) — unchanged. The
  reverification confirms §4.9 honors ADR-081's rule that
  `projects.user_id` is the canonical Project ownership
  authority by *forbidding* `projects.user_id` as the canonical
  memory owner. Memory scope may reference a Project but Project
  authority scopes rather than owns.
- ADR-082 (Persona Profile manifest and binding authority) —
  unchanged. The reverification confirms §4.3, §4.5 (already in
  the contract from UMS-02A), and §4.9 forbid `persona_profile_id`
  as durable attribution identity. Mutable PersonaProfile remains
  configuration, not attribution.
- ADR-083 (MemoryOS) — **not present in the ADR registry.** This
  is a documentation gap honestly recorded by the prior UMS-03A
  proof. Per the UMS-03A-Q spec instruction "Do not repair or
  reinterpret the ADR during revalidation," this reverification
  records the gap and does not create an ADR. ADR-084 is the
  controlling memory architecture decision and is unchanged.
- ADR-084 (Unified Account-Owned Memory Store) — unchanged; the
  governing decision for this entire contract. The reverification
  confirms §4.6, §4.7, §4.8, §4.9, §4.10, §4.11, §4.12, §4.13,
  §4.14, and §4.15 are all consistent with ADR-084's doctrine.
  In particular: account owns; project scopes; persona attributes;
  user approves; pinning prioritizes; holding suspends decay; the
  router widens only on explicit user intent; every borrowed
  memory keeps its attribution. "Automatic capture, explicit
  activation" and "Retrievable != authorized for ambient
  influence" are preserved at §4.10.

No ADR was created or modified in this reverification.

## Unrelated dirty-file preservation

The only working-tree change against the `main` branch at the
start of this revalidation was:

```text
M  tests/pi/fixtures/fake_pi_package/package.json
```

This is a pre-existing test-fixture edit unrelated to UMS-03A
or this revalidation. The reverification did not stage, modify,
or otherwise touch this file. It remains unstaged and is not
part of the revalidation commit.

## Release and runtime impact

```text
UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: REVERIFIED
ORIGINAL COMMIT: 12075540e29077a40a7d578eef315bc4277c0841
UMS-03: OPEN
UMS-03B: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE
```

The reverification is read-only. No SQL schema, no migration, no
ORM model, no runtime reader or writer, no retrieval behavior, no
export implementation, no account export/restore code, and no
Campaign README, current-state, contract, or original 03A proof
receipt was changed. No runtime or release capability changed.
No Beta claim widened. No canonical memory persistence
implementation exists yet.

The reverification *adds* exactly one new proof receipt
(`docs/architecture/proofs/runtime/2026-09-07-ums03a-reverification-proof.md`)
to the repository, staged and committed on top of `12075540e`
with commit message `Reverify canonical memory envelope`.
