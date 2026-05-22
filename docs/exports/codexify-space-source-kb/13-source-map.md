# Source Map

## Notes

- This exported KB is a distillation, not a copy of the source corpus.
- No required pre-read files from the task prompt were absent in this workspace.
- Some legacy or broader docs exist in the repo but were intentionally not used as public truth when the validity matrix or current-state docs marked them as risky.

## Source table

| Path | What it contributed | Confidence | Safe for public-site use | Notes / caveats |
|---|---|---|---|---|
| `docs/architecture/00-current-state.md` | Canonical short-horizon truth, supported posture, blockers, non-promises | high | yes | Highest authority inside this export for current product truth |
| `docs/architecture/README.md` | KB routing, architecture framing, source-anchor discipline | high | yes | Good for orientation, not a release proof artifact by itself |
| `docs/architecture/kb-validity-matrix.md` | Trust rules, doc quarantine rules, separation of current truth from drift | high | yes | Critical for excluding legacy or misleading sources |
| `docs/architecture/architecture-atlas.md` | Reading order, runtime-vs-UI distinction, ADR lane framing | high | yes | Helpful meta-layer, not a capability proof source |
| `docs/architecture/system-overview.md` | Public-safe component map, topology, supported local runtime shape | high | yes | Structural source, not release readiness by itself |
| `docs/architecture/flows.md` | Queue-backed behavior, acceptance semantics, retrieval and ingestion flow truth | high | yes | Needed for runtime honesty and "acceptance is not completion" doctrine |
| `docs/architecture/data-and-storage.md` | Persistence layers, continuity surfaces, provenance-bearing entities | high | yes | Use at conceptual level; do not expose unnecessary storage internals |
| `docs/architecture/config-and-ops.md` | Supported local-only posture, provider governance, health truth surfaces | high | yes | Strong source for public runtime-boundary explanation |
| `docs/architecture/modules-and-ownership.md` | Real subsystem seams and high-coupling areas | medium | yes | Useful for internal understanding; only selectively public-safe |
| `docs/architecture/tech-debt-and-risks.md` | Risk register, operator burden, release caveats | high | yes | Important for honesty surfaces and claim discipline |
| `docs/architecture/runtime-protocol-token-contract.md` | Token-discipline concept for runtime truth surfaces | high | yes | Use as doctrine, not as marketing copy |
| `docs/architecture/chat-runtime-contract.md` | Provider/runtime vs request-state separation | high | yes | Important for public explanation of runtime honesty |
| `docs/architecture/account-export-restore-contract.md` | Artifact lineage, provenance, explicit relationship preservation | high | yes | Strong source for continuity and export doctrine |
| `docs/architecture/agent-protocol-operations.md` | Agent work rules, non-widening discipline, output expectations | high | yes | Shaped exported AGENTS guidance |
| `docs/architecture/self-extending-agent-plugin-system.md` | Bounded extension doctrine and explicit non-goals | medium | limited | Good for roadmap boundaries; not safe as shipped capability claim |
| `docs/architecture/pi-invocation-boundary-contract.md` | Contract-only Pi boundary, provider separation, explicit deferrals | medium | limited | Safe only when clearly labeled as contract-only or exploration |
| `docs/iddb_policy_v1.md` | Memory layers, opt-in deep identity, persona borrowing, sensitive inference bounds | high | yes | Canonical identity-policy source used instead of implying profiling |
| `docs/beta/README-FIRST.md` | Beta posture, supported entry paths, private-beta caution | high | yes | Helpful for beta/download language; do not overgeneralize |
| `docs/release/public-portal-snapshot-workflow.md` | Private source-vault vs public-portal boundary and copy-safe export logic | high | yes | Directly relevant to cross-repo KB export boundary |
| `docs/release/open-source-tiering/public-readiness-checklist.md` | Public-readiness cautions and claim discipline checks | high | yes | Useful for public safety and boundary truth |
| `docs/Marketing/README.md` | Proof-tier precedence and draft-only marketing governance | high | yes | Important claim-governance source |
| `docs/Marketing/messaging/pillars.md` | Proof tier definitions and safe claim directions | high | yes | Strong source for claim labeling and content guidance |
| `docs/Marketing/brand/constitution.md` | Forbidden claim patterns and required language discipline | high | yes | Strong public-story constraint source |
| `docs/Marketing/master-campaign-brief.md` | Continuity narrative, mood lanes, worldbuilding language, safe claim posture ideas | medium | limited | Internal-use source; useful for atmosphere, not direct public proof |
| `docs/Website/README.md` | Website content boundary as derived output, not truth source | medium | yes | Reinforces "derived output" stance |
| `docs/ui/UI-DESIGN-MAP.md` | Transferable app-side visual discipline: slabs, glass, spacing, structural consistency | medium | limited | Visual doctrine only; not runtime truth |

## Sources intentionally treated with caution

- `docs/Codexify/README.md`
  - Present in the repo, but the validity matrix classifies it as misleading identity drift for first-pass current truth work.
- `docs/guardian/iddb_policy_v1.md`
  - Present in the repo, but the canonical path used here was `docs/iddb_policy_v1.md`.
