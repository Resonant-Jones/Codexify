# Marketing Curation Packet

**Campaign:** CAMPAIGN_2026_05_16_MARKETING_V1  
**Status:** Draft — Human Approval Required  
**Generated:** 2026-05-16

---

## Campaign Source

- **Campaign ID:** CAMPAIGN_2026_05_16_MARKETING_V1
- **Source files reviewed:**
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/evidence-ledger.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/run-metadata.json`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/core-brief.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-website.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-social.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/channel-community.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/ad-copy.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/infographic-spec.md`
  - `docs/Marketing/generated/CAMPAIGN_2026_05_16_MARKETING_V1/review-notes.md`
- **Evidence source documents:**
  - `docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md`
  - `docs/Campaign/CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md`
- **Generated date:** 2026-05-16
- **Purpose:** Translate Codexify's Pi integration progress into evidence-linked marketing artifacts for Local-First AI Builders

---

## Evidence Review

| Evidence ID / Source File | Summary | Proof Strength | Usable for Public Copy | Notes |
|---------------------------|---------|-----------------|------------------------|-------|
| `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | Integration plan: ADR-020 contract, three-layer system (Guardian → Pi → Codex Runner), Redis-backed queue infrastructure | `implemented` | **No** (internal anchor) | Contains implementation breadcrumbs; not suitable for verbatim public copy |
| `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | Live execution log documenting task completions, runtime drift, missing migrator revision, and return-path failure | `implemented` | **No** (risk evidence) | Runtime blockers present; return path not release-ready |
| `evidence-ledger.json` | Normalized claim ledger with 24 items: 12 marketable, 12 non-marketable | `varies` | **Partial** | Only `public_copy_seed` + `copy_ready: true` items may appear in public prose |
| `core-brief.md` | Single verified claim: "Codex Runner provides campaign/audit infrastructure" | `verified` | **Yes** (copy-ready) | Only production-ready claim in this campaign |
| `run-metadata.json` | Campaign metadata: 12 marketable claims, 12 non-marketable claims | n/a | **No** | Metadata only |
| `channel-website.md` | Draft website copy anchored to Codex Runner claim | `verified` | **Maybe** | Thin; needs expansion before use |
| `channel-social.md` | Draft social copy anchored to Codex Runner claim | `verified` | **Maybe** | Thin; needs expansion before use |
| `channel-community.md` | Draft community update anchored to Codex Runner claim | `verified` | **Maybe** | Thin; needs expansion before use |
| `ad-copy.md` | Three ad concepts; only one backed by verified claim | `mixed` | **Maybe** (Concept 1 only) | Concepts 2–3 use `implemented` tier; do not inflate to verified |
| `infographic-spec.md` | Spec/prompt pack only; no media generated | `implemented` | **Spec only** | Visual direction is sound; data points need supplementation |

**Evidence Triage Summary:**

- Copy-ready claims (verified tier): **1** — Codex Runner campaign/audit infrastructure
- Implementation-level claims (not copy-ready): **11** — task completions, queue wiring, adapter skeleton, integration contract
- Risk/blocker evidence: **6** — return path not release-ready, idempotency blocked, migrator drift
- Metadata references: **1** — proof artifact pointer
- Internal anchors: **5** — ADR dependencies, pipeline contracts

---

## Claim Ledger

| Claim | Source Evidence | Status | Reason | Safest Public Wording |
|-------|-----------------|--------|--------|----------------------|
| Codex Runner provides campaign/audit infrastructure | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **use** | Single verified-tier claim with clean language | "Codex Runner provides campaign tracking and audit infrastructure" |
| Define the coding-task envelope schema | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **defer** | Task instruction, not public-facing copy | "Structured task definitions enable reliable delegation" |
| Wire into existing Guardian queue infrastructure | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **defer** | Implementation breadcrumb; internal architecture | "Redis-backed task routing with SSE events" — *if* framing as capability |
| Existing queue: Redis-backed with task events via SSE | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **revise** | Copy-ready form available, but context-dependent | "Task queue with real-time event delivery" |
| guardian/queue/ — Task definitions for delegation | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **reject** | Internal path; not public language | Do not use |
| ADR-020 defines Guardian as identity/persistence owner | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **reject** | Internal architecture contract; not customer-facing | Do not use |
| Depends on ADR-020 (Guardian Mediated Coding Agent Execution Contract) | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION.md` | **reject** | Dependency notation; not public language | Do not use |
| Queue: codexify:queue:coding-execution | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Internal queue name; not customer-facing | Do not use |
| Task completions (commit hashes: 1dae1662d, 207c850ab, 7fdb0c63d, 9a280aead) | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Git hashes; not public language | Do not use |
| Full 9-target live rerun executed | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **defer** | Valid evidence anchor, but not copy-ready phrasing | "Integration tests were run against nine targets" |
| Additional runtime drift / missing migrator revision | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Blocker evidence; not suitable for public copy | Do not use |
| Current outcome not release-ready | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Blocker evidence; not suitable for public copy | Do not use |
| Idempotency remains blocked / no source-thread result delivered | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Blocker evidence; not suitable for public copy | Do not use |
| Coding-result return path not release-ready | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Blocker evidence; not suitable for public copy | Do not use |
| Re-run the live Compose proof after blocker is fixed | `CAMPAIGN_2026-05-01_001_PI_CODER_INTEGRATION_EXECUTION_LOG.md` | **reject** | Task instruction; not public language | Do not use |

**Claim Ledger Summary:**

- **use:** 1 (Codex Runner campaign/audit infrastructure — verified)
- **revise:** 1 (Redis-backed queue — reframe as capability, not internal breadcrumb)
- **defer:** 2 (schema framing, test evidence — needs copy craft before use)
- **reject:** 11 (implementation breadcrumbs, task instructions, blocker evidence, internal paths)

---

## Narrative Hooks

### trust / proof

- **Hook:** "Proof-backed updates for builders who distrust hype"
- **Supporting claim:** Codex Runner provides campaign/audit infrastructure (verified)
- **Risk level:** Low
- **Best channel:** Social, community

### local-first ownership

- **Hook:** "Boundaries, failure visibility, and operator truth as first-class engineering outcomes"
- **Supporting claim:** Codex Runner provides campaign/audit infrastructure (verified) + Redis-backed queue framing (needs revision)
- **Risk level:** Low-Moderate (depends on rewrite; avoid collapsing Docker and desktop paths)
- **Best channel:** Website, community

### continuity

- **Hook:** "Every draft claim points to concrete artifacts in the repository"
- **Supporting claim:** Evidence-ledger tracks copy-ready status and proof tiers
- **Risk level:** Low (process claim, not capability claim)
- **Best channel:** Community, social

### workflow clarity

- **Hook:** "Structured task definitions enable reliable delegation"
- **Supporting claim:** Schema framing (defer — needs copy craft)
- **Risk level:** Moderate (needs verification that framing holds under operator scrutiny)
- **Best channel:** Community, website

### developer/operator usefulness

- **Hook:** "Task queue with real-time event delivery"
- **Supporting claim:** Redis-backed SSE queue (revise — reframe as capability)
- **Risk level:** Moderate (needs clean public wording)
- **Best channel:** Website, community

### emotional resonance

- **Hook:** "Build AI operations on evidence, not assumptions"
- **Supporting claim:** Codex Runner provides campaign/audit infrastructure (verified)
- **Risk level:** Low
- **Best channel:** Social, ad copy

---

## Copy Layers

### 1. Internal Positioning

| Item | Content | Supporting Claims | Tone Notes | Readiness |
|------|---------|-------------------|-----------|-----------|
| IP-01 | "Codexify's three-layer system (Guardian, Pi, Codex Runner) routes AI operations through explicit contracts." | ADR-020 contract evidence (internal only) | Precise, process-oriented | **hold** — internal framing not ready for external use |
| IP-02 | "Codex Runner provides campaign tracking and audit infrastructure." | Codex Runner campaign/audit infrastructure (verified) | Factual, understated | **ready** |

### 2. Website Copy

| Item | Content | Supporting Claims | Tone Notes | Readiness |
|------|---------|-------------------|-----------|-----------|
| WEB-01 | "Codexify runs AI operations on local infrastructure with explicit policy surfaces." | Redis-backed queue framing (revise needed) | Calm, operator-focused | **needs review** — framing too abstract; needs concrete claim |
| WEB-02 | "Codex Runner provides campaign tracking and audit infrastructure." | Codex Runner campaign/audit infrastructure (verified) | Factual | **ready** |
| WEB-03 | "Structured task definitions enable reliable delegation." | Schema framing (defer) | Needs copy craft | **needs review** — defer until framing is verified |

### 3. Social Copy

| Item | Content | Supporting Claims | Tone Notes | Readiness |
|------|---------|-------------------|-----------|-----------|
| SOC-01 | "Codexify update: structural reliability work is being tracked with explicit proof tiers and source-linked claims." | Codex Runner campaign/audit infrastructure (verified) | Process transparency tone | **ready** |
| SOC-02 | "Every draft claim points to concrete artifacts in the repository." | Evidence-ledger process (metadata only) | Meta-commentary; safe but thin | **ready** |

### 4. Community Update Copy

| Item | Content | Supporting Claims | Tone Notes | Readiness |
|------|---------|-------------------|-----------|-----------|
| COM-01 | "This cycle focused on operator trust: visible boundaries, bounded claims, and evidence-led progress artifacts." | Codex Runner campaign/audit infrastructure (verified) | Warm, reflective | **ready** |
| COM-02 | "Integration tests were run against nine targets." | Full 9-target live rerun (defer) | Factual but needs context | **needs review** — defer until copy craft provides narrative frame |

### 5. Short Ad-Style Copy

| Item | Content | Supporting Claims | Tone Notes | Readiness |
|------|---------|-------------------|-----------|-----------|
| AD-01 | "Build AI operations on evidence, not assumptions." | Codex Runner campaign/audit infrastructure (verified) | Direct, benefit-forward | **ready** |
| AD-02 | "Local-first control with explicit policy surfaces." | Redis-backed queue framing (revise needed) | Aspirational but needs backing | **needs review** — claims require proof |
| AD-03 | "Marketing copy that can be audited." | Evidence-ledger process (metadata only) | Meta; self-referential | **needs review** — thin; may read as insider joke |

---

## Artifact Spec Candidates

### Infographic Candidate

- **Objective:** Show the relationship between campaign receipts, evidence-linked claims, and operator governance
- **Source claims:** Codex Runner campaign/audit infrastructure (verified)
- **Required proof:** Additional verified-tier claims needed to fill diagram; current campaign has only 1
- **Visual direction:** Left-to-right flow: source artifacts → evidence ledger → proof-tier labels → marketing outputs; restrained engineering aesthetic
- **Do-not-say constraints:** Do not imply release-readiness beyond verified claims; do not collapse Docker and desktop paths; do not use implementation breadcrumbs as visible labels
- **Readiness:** **blocked** — insufficient verified-tier data points for coherent infographic; recommend next sampling pass yield additional claims

### Slide Candidate

- **Objective:** Present Codexify's evidence-first approach to Local-First AI Builders
- **Source claims:** Codex Runner campaign/audit infrastructure (verified) + evidence-ledger process (metadata)
- **Required proof:** At least 3 verified-tier claims recommended for slide credibility
- **Visual direction:** Proof-tier hierarchy visual, claim source mapping, risk flag transparency table
- **Do-not-say constraints:** Do not present as product feature pitch; maintain evidence-first posture; do not inflate proof tiers
- **Readiness:** **draft** — single verified claim limits slide depth; needs supplementation

### Short Video Candidate

- **Objective:** Narrate Codexify's trust model for operators who prioritize reliability over hype
- **Source claims:** Codex Runner campaign/audit infrastructure (verified)
- **Required proof:** Narrative needs at least 3 verified-tier claims to sustain video arc
- **Visual direction:** Screen-record of claim-to-evidence mapping; voice-over narration; demo of evidence ledger filtering
- **Do-not-say constraints:** Do not narrate as product demo; frame as transparency-first approach; do not claim release-readiness beyond evidence
- **Readiness:** **blocked** — insufficient material for video arc

### Website Visual Candidate

- **Objective:** Anchor homepage in evidence-first positioning
- **Source claims:** Codex Runner campaign/audit infrastructure (verified)
- **Required proof:** Visual needs homepage hero context (existing: homepage-hero-mockup-packet.md)
- **Visual direction:** Artifact-to-claim flow diagram; proof-tier badge system; minimal UI chrome
- **Do-not-say constraints:** Do not overclaim local-first without supporting evidence; do not collapse platform support claims
- **Readiness:** **review** — visual direction is sound; review against homepage hero mockup for alignment

---

## Curation Notes

### Strongest Material

1. **Codex Runner campaign/audit infrastructure** — Single verified-tier claim; clean language; ready for public copy without modification
2. **Evidence-ledger process framing** — "Proof-backed updates for builders who distrust hype" is resonant and accurate
3. **Social and community channel copy** — Thin but accurate; requires minimal risk management
4. **Ad Concept 1** — "Build AI operations on evidence, not assumptions" is the most audience-ready artifact

### Weakest Material

1. **Ad Concepts 2–3** — Use `implemented`-tier language inflated toward `verified`; not ready without revision
2. **Infographic spec** — Only 1 verified claim; visual spec is sound but data-starved
3. **Website copy** — Abstract framing ("explicit policy surfaces") not backed by verified claims; needs concrete anchoring
4. **Video and slide candidates** — Insufficient verified-tier material for coherent artifacts

### Claims to Avoid

- Any claim referencing ADR-020, task IDs, commit hashes, queue names, or migrator revisions
- Any claim implying release-readiness for the coding-result return path
- Any claim collapsing "local-first" into a single capability without specifying what is actually local-first per campaign evidence
- Any claim framed as hype ("revolutionary", "game-changing", "best-in-class") — no evidence supports such language

### Language That Feels Too Inflated

- "explicit policy surfaces" — sounds like enterprise compliance; campaign evidence does not back this level of abstraction
- "every draft claim points to concrete artifacts" — close to true but "concrete artifacts" is meta-commentary; may confuse non-technical audiences
- "structural reliability work" — accurate but clinical; consider warmer framing for community channels

### Recommended Next Sampling Pass

1. **Prioritize verification** of the Redis-backed queue capability — if this can be verified (not just implemented), it becomes a second verified-tier claim
2. **Sample task-delegation framing** — structured delegation framing may yield a second or third copy-ready claim
3. **Hold infographic/video** until at least 3 verified-tier claims are available
4. **Expand social copy** — current social copy is thin; small iteration could yield stronger hooks without additional evidence

---

## Final Recommendation

**revise claims first**

**Rationale:** This campaign contains 1 verified-tier claim and 11 implementation-level claims. The evidence-ledger correctly separates them, but the marketing artifacts (especially ad-copy concepts 2–3, infographic spec, and website copy) do not consistently respect proof-tier boundaries. Before any visual artifact or ad campaign is rendered, the claims must be audited for tier accuracy, and at least 2–3 additional verified-tier claims should be generated from the next evidence sampling pass.

**Immediate next step:** Run a targeted evidence audit against the Redis-backed queue capability and task-delegation framing to determine whether these can be elevated from `implemented` to `verified`. If so, update the claim ledger and regenerate channel copy with the additional claims.

---

## Validation

- **git diff --check:** Passed (no whitespace or merge conflicts)
- **scripts/validate_docs.py:** No automated docs validation exists in this project.

**No automated tests apply.**

---

*This curation packet is a derived output from Codexify's marketing pipeline. It is draft-only until human approval. All claims are evidence-anchored per the claim-truth-model contract. Approval state: `draft`.*