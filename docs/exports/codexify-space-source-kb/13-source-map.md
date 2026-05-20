# 13 Source Map

This table maps the exported KB back to the Codexify infrastructure source docs used to build it.

| Path | What it contributed | Confidence | Safe for public-site use | Notes and caveats |
|---|---|---:|---|---|
| `docs/architecture/00-current-state.md` | authoritative short-horizon release truth, supported path, non-promises | high | yes | wins on conflicts inside this export |
| `docs/architecture/README.md` | architecture doc map, truth precedence, product/runtime framing | high | yes | structural context, not release proof by itself |
| `docs/architecture/kb-validity-matrix.md` | doc validity discipline | medium | yes | process guidance more than public copy material |
| `docs/architecture/architecture-atlas.md` | reading order, current-truth model, ADR framing | medium | yes | use as orientation, not marketing evidence |
| `docs/architecture/system-overview.md` | public-safe component inventory and topology | high | yes | topology must stay distinct from website implementation |
| `docs/architecture/flows.md` | acceptance versus completion, retrieval and lineage flow semantics | high | yes | detailed internals should be distilled before public use |
| `docs/architecture/data-and-storage.md` | persistence layers, provenance, restore/lineage obligations | high | yes | avoid exposing unnecessary storage detail |
| `docs/architecture/config-and-ops.md` | supported path, provider posture, runtime boundaries | high | yes | strong source for support-boundary claims |
| `docs/architecture/modules-and-ownership.md` | subsystem boundaries and blast-radius awareness | medium | yes | mainly useful for agent orientation |
| `docs/architecture/tech-debt-and-risks.md` | current risks, operator burden, release caution language | high | yes | risk framing should stay narrow and non-alarmist |
| `docs/architecture/runtime-protocol-token-contract.md` | observable status-token discipline and truth-surface framing | medium | yes | architecture contract, not itself release proof |
| `docs/architecture/chat-runtime-contract.md` | provider-state versus request-state distinction | high | yes | key public honesty doctrine |
| `docs/architecture/account-export-restore-contract.md` | provenance, artifact lineage, restore obligations | high | yes | good source for continuity/provenance language |
| `docs/architecture/agent-protocol-operations.md` | interpretation rules, architecture-impact discipline, proof rules | high | yes | mainly for future agents using this export |
| `docs/architecture/self-extending-agent-plugin-system.md` | bounded extension doctrine and explicit non-promises | medium | yes | do not convert this into shipped plugin claims |
| `docs/architecture/pi-invocation-boundary-contract.md` | mediated coding-agent boundary and non-goals | medium | yes | explicit future-boundary material, not public promise |
| `docs/iddb_policy_v1.md` | identity, diary, deep identity, consent, persona borrowing | high | yes | `docs/guardian/iddb_policy_v1.md` is a duplicate copy |
| `docs/release/public-portal-snapshot-workflow.md` | snapshot publishing doctrine and source-vault/public-repo boundary | high | yes | supports portable-export framing |
| `docs/release/audits/beta-smoke-test.md` | supported-path beta proof expectations | high | yes | release validation doctrine, not front-page copy |
| `docs/release/open-source-tiering/open-core-boundary-v1.md` | public/private surface boundary and trust model | high | yes | useful for non-promise and boundary sections |
| `docs/release/open-source-tiering/codexify-release-tier-index.md` | public/open-core candidate framing and holdback cues | medium | yes | prioritization aid, not direct product proof |
| `docs/release/open-source-tiering/public-readiness-checklist.md` | public-claim hygiene and readiness blockers | high | yes | strong source for claim discipline |
| `docs/release/open-source-tiering/README.md` | tiering-kit interpretation order | medium | yes | contextual support doc |
| `docs/Marketing/README.md` | claim precedence, proof-tier discipline, human-review rule | high | yes | excellent source for public-copy guardrails |
| `docs/Website/README.md` | website-content boundary posture | low | yes | supplementary only |
| `docs/Codexify/README.md` | broad product overview | low | caution | older broad README language should not outrank current truth |
| `docs/Website/dev-blog/README.md` | dev-blog boundary cues | low | yes | supplemental Founder Log context |

## Missing expected files

None of the explicitly required pre-read files were absent in this repo snapshot.

## Caveat

Not every safe-for-public source is appropriate for direct quotation. This export is a distillation layer; agents should adapt language while preserving the source-bound truth and boundaries above.
