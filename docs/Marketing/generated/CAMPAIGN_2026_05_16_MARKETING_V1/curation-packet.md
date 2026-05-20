# Marketing Curation Packet

## Campaign Source
- Campaign id: `CAMPAIGN_2026_05_16_MARKETING_V1`
- Source files reviewed:
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/evidence-ledger.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/run-metadata.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/core-brief.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-website.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-social.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-community.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/ad-copy.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/infographic-spec.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/review-notes.md`
- Generated date: `2026-05-17`
- Purpose: Internal evidence-first curation pass that ranks what is safe to use, what must be revised, and what should be deferred or rejected before any publish decision.

## Evidence Review
| Evidence id or source file | Summary | Proof strength | Usable for public copy | Notes |
|---|---|---|---|---|
| `evidence-ledger.json` (`C01-C24`) | 24 total claims; 17 marketable_claim, 6 risk_or_blocker, 1 metadata_reference | Mixed (`implemented` + `verified`) | Maybe | Only `C05` is `public_copy_seed` and `copy_ready=true`. Most others are support-only or internal anchors. |
| `evidence-ledger.json` (`C05`) | "Codex Runner provides campaign/audit infrastructure" | Verified | Yes | Safest current public claim in the packet. |
| `evidence-ledger.json` (`C07`, `C08`, `C11`) | Queue and delegation infrastructure references | Implemented | Maybe | Useful as internal support, not verbatim public copy (`copy_ready=false`). |
| `evidence-ledger.json` (`C18`) | 9-target live rerun executed and proof artifact appended | Implemented | Maybe | Indicates execution effort, not release readiness. Must stay qualified. |
| `review-notes.md` + `evidence-ledger.json` (`C16`, `C17`, `C19`, `C20`, `C21`, `C24`) | Runtime drift, missing revision blocker, explicit not-release-ready outcomes | Implemented with risk flags | No | Required internal context; should suppress overconfident launch language. |
| `run-metadata.json` | Draft mode, human approval posture, claim counts | Metadata-level strong | Yes | Safe governance framing for internal and community transparency copy. |
| `core-brief.md` + channel files | Current message posture is evidence-bound and draft-gated | Derived from ledger | Yes | Good structural baseline; still narrow due single copy-ready claim. |
| `ad-copy.md` | Three draft ad concepts with mixed proof tiers | Mixed (`verified` + `implemented`) | Maybe | Concept 1 is strongest; Concepts 2/3 need tighter proof references. |
| `infographic-spec.md` | Renderer-agnostic spec and prompts for optional visual work | Spec-only | Maybe | Keep as optional candidate only; no media generation yet. |

## Claim Ledger
| Claim | Source evidence | Status | Reason | Safest public wording |
|---|---|---|---|---|
| Codexify has evidence-linked campaign/audit infrastructure via Codex Runner. | `C05` in `evidence-ledger.json`; repeated in `core-brief.md` and all channel files | use | Verified + copy-ready public seed | "Codexify uses source-linked campaign and audit artifacts to keep draft messaging accountable." |
| Codexify tracks reliability work with explicit proof tiers and draft governance. | `run-metadata.json` (`mode=draft`, claim counts), `core-brief.md` governance section | use | Governance truth is explicit and non-inflated | "This campaign is draft-gated and proof-tiered before publish decisions." |
| Guardian queue and delegation seams are in place as implementation evidence. | `C07`, `C08`, `C11` in `evidence-ledger.json` | revise | Supporting evidence only; not copy-ready public prose | "Internal logs show queue/delegation implementation evidence; external copy should keep this high-level until additional verified public seeds exist." |
| A full rerun was executed and documented in proof artifacts. | `C18` + `C23` in `evidence-ledger.json`; `review-notes.md` metadata reference | revise | True but easy to overstate if detached from blockers | "A documented rerun was executed; readiness conclusions remain constrained by open blockers." |
| The path is release-ready now. | `C17`, `C20`, `C21` in `evidence-ledger.json`; `review-notes.md` risk list | reject | Evidence directly contradicts this claim | "Do not use until blocker evidence changes." |
| Idempotent result return path is fully proven. | `C19`, `C20` in `evidence-ledger.json`; `review-notes.md` | defer | Evidence says blocked because no source-thread result was delivered | "Needs proof: idempotent return path remains blocked in current evidence set." |
| Codexify provides local-first control with explicit boundaries. | `ad-copy.md` Concept 2 + `channel-website.md` message posture | revise | Directionally strong but broad relative to copy-ready claim inventory | "Codexify messaging currently emphasizes explicit boundaries and evidence-linked operations." |
| Every draft claim is auditable to repository artifacts. | `ad-copy.md` Concept 3 + `evidence-ledger.json` path coverage + `review-notes.md` | use | Supported as an internal process claim | "Draft claims in this campaign are traceable to repository artifacts." |
| Campaign is ready for broad external launch messaging. | Risk signals `C16`, `C17`, `C19`, `C20`, `C21`, `C24` | reject | Blocked-run and not-release-ready risks remain open | "Do not use until blockers are resolved and claims are re-scored." |

## Narrative Hooks
### trust / proof
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Auditability over hype | `C05`, auditable-process claim (Claim Ledger row 8) | low | website |
| Draft-gated truth posture | Governance claim (Claim Ledger row 2) | low | community |

### local-first ownership
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Boundaries before promises | Revised local-first boundaries claim (Claim Ledger row 7) | medium | website |

### continuity
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Work history is preserved as evidence, not erased by launch pressure | Revised rerun/proof claim (Claim Ledger row 4) | medium | community |

### workflow clarity
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Evidence -> claim gate -> channel draft is visible and repeatable | Governance claim (Claim Ledger row 2), auditable-process claim (Claim Ledger row 8) | low | community |

### developer/operator usefulness
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Blockers are surfaced early so operators can decide before publish | Risk evidence `C16`, `C17`, `C19`, `C20`, `C21`, `C24` | low | community |

### emotional resonance
| Hook | Supporting claim | Risk level | Best channel |
|---|---|---|---|
| Confidence comes from honest boundaries, not big promises | `C05` + rejected overbroad launch claim (Claim Ledger row 9) | medium | social |

## Copy Layers
| Layer | Intended channel | Supporting claims | Tone notes | Readiness | Draft copy |
|---|---|---|---|---|---|
| 1. internal positioning | internal strategy | Claim Ledger rows 1, 2, 8, 9 | Calm, evidence-led, explicit constraints | ready | "This campaign should position Codexify as an evidence-disciplined system: publish only what is verified, keep blockers visible, and use channel copy as a transparent extension of engineering truth." |
| 2. website copy | website | Claim Ledger rows 1, 2, 7 | Clear, practical, non-hype | needs review | "Codexify turns draft messaging into an auditable workflow. Claims are tied to source artifacts, reviewed by proof tier, and published only when they clear governance gates." |
| 3. social copy | social | Claim Ledger rows 1, 2, 9 | Concise, plainspoken, no launch inflation | needs review | "Current Codexify campaign work is proof-tiered and draft-gated: visible evidence first, copy second. We are prioritizing claim quality over announcement velocity." |
| 4. community update copy | community | Claim Ledger rows 2, 4, 6, 8 | Transparent, operator-focused | ready | "Community update: this marketing cycle remains draft-only while we keep claim evidence and blocker notes in sync. Verified infrastructure claims are usable now; readiness-sensitive claims remain deferred." |
| 5. short ad-style copy | ads (internal draft lane) | Claim Ledger rows 1, 8, 9 | Sharp, factual, no superlatives | needs review | "Evidence-backed copy for local-first builders. Traceable claims. Clear boundaries. No release-ready shortcuts." |

## Artifact Spec Candidates
| Candidate | Objective | Source claims | Required proof | Visual direction | Do-not-say constraints | Readiness |
|---|---|---|---|---|---|---|
| infographic candidate | Show the curation chain from evidence to publish gate | Claim Ledger rows 1, 2, 8, 9 | Keep `C16-C21` risk context visible | Left-to-right pipeline: evidence -> claim gate -> channel draft -> hold/release decision | Do not imply release-ready status or resolved runtime blockers | review |
| slide candidate | Internal review deck for go/no-go messaging decisions | Claim Ledger rows 1, 2, 4, 6, 9 | Add latest blocker disposition before review meeting | Three acts: proven now, needs revision, blocked claims | Do not present supporting_evidence or internal_anchor text as public claims | draft |
| short video candidate | Explain why proof-tier discipline improves trust | Claim Ledger rows 1, 2, 8 | Need one additional verified public_copy_seed beyond `C05` | Minimal motion typography; claim cards with proof tags | Do not use "shipping now" or "production-ready" language | blocked |
| website visual candidate | Add a static governance diagram next to website copy | Claim Ledger rows 1, 2 | Confirm updated approved website copy first | Simple system diagram with draft-gate badge and evidence links | Do not depict unresolved pipeline as complete release path | review |

## Curation Notes
- Strongest material: `C05` verified infrastructure claim, draft-governance metadata from `run-metadata.json`, and auditable process framing from ledger path coverage.
- Weakest material: raw task IDs, commit-like identifiers, queue names, and ADR anchors as direct copy candidates (`C11-C15`, `C01`, `C04`, `C09`, `C10`, `C22`).
- Claims to avoid: any statement that implies release-ready status, fully proven idempotent result return, or resolved runtime drift (`C16-C21`, `C24`).
- Language that feels too inflated: "local-first control" or "operator confidence" without explicit qualifier that current public copy seeds are narrow.
- Taste/curation grading:
  - strong: verified and copy-ready (`C05`)
  - usable with guardrails: governance/process claims from `run-metadata.json` and `core-brief.md`
  - weak: implementation breadcrumbs as visible prose (`C06-C15`, `C22-C23`)
  - risky: readiness-adjacent claims contradicted by blocker evidence (`C16-C21`, `C24`)
  - overbroad: launch-toned claims that collapse draft mode into release posture
- Recommended next sampling pass: regenerate claim candidates from the same evidence set but require at least 3 verified `public_copy_seed` claims before new public channel drafts.

## Final Recommendation
`revise claims first`

Reason: the campaign has one clearly safe public copy seed (`C05`) plus strong governance/process framing, but it does not yet have enough verified public-facing claim diversity to support broader publishing without overreach.
