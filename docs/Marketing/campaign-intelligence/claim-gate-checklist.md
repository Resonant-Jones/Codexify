# Claim Gate Checklist (Pre-Publish, Internal)

Use this checklist before any generated campaign artifact moves from internal draft toward external use.

Primary gate sources:
- `docs/Marketing/chatgpt-project-bundle/01-current-truth-claim-boundary.md`
- `docs/Marketing/chatgpt-project-bundle/11-claim-ledger.md`
- `docs/Marketing/contracts/claim-truth-model.md`
- `docs/architecture/00-current-state.md`

## 1) Safe Claim Confirmation

- [ ] Every outward-facing line is labeled `safe`, `caution`, `future`, or `reject`.
- [ ] Public-facing visible copy includes only lines acceptable under current truth.
- [ ] Any ambiguous line is downgraded to `caution` pending proof.

## 2) Evidence Path Check

- [ ] Each claim has at least one valid evidence path.
- [ ] Evidence paths exist and are reviewable by a human reviewer.
- [ ] Evidence tier is accurate: `implemented`, `verified`, or `live-proven`.
- [ ] No evidence path points to non-existent files or speculative notes only.

## 3) Current Truth Check

- [ ] Claims were compared against `docs/architecture/00-current-state.md`.
- [ ] Claim language does not exceed current support posture.
- [ ] Desktop/runtime path distinctions are preserved when relevant.

## 4) Audience Fit Check

- [ ] One primary audience segment is selected.
- [ ] Pain and desired transformation match that segment.
- [ ] Channel choice matches audience behavior and objection profile.

## 5) Overclaim Scan

- [ ] No line implies fully autonomous, unsupervised operation.
- [ ] No line implies mature hosted SaaS if not currently supported.
- [ ] No line implies broad enterprise readiness by default.
- [ ] No line implies guaranteed outcomes, zero failure, or zero context loss.

## 6) Public/Private Boundary Check

- [ ] Internal evidence breadcrumbs are excluded from public prose.
- [ ] Risk/blocker lines remain in internal notes, not external assets.
- [ ] `approval_state` remains `draft` until explicit human sign-off.

## 7) Free and Open-Core Caution

- [ ] Avoid implying product scope or support commitments not documented.
- [ ] Avoid licensing/pricing claims unless explicitly sourced and current.
- [ ] Separate "available in repo" from "supported as product promise."

## 8) Agents and Automation Caution

- [ ] Do not claim set-and-forget agents or autonomous orchestration as current posture.
- [ ] Do not collapse acceptance, enqueue, and completion into one success claim.
- [ ] Preserve human-governed review posture in messaging.

## 9) Enterprise and SaaS Caution

- [ ] Do not claim broad enterprise or compliance readiness without explicit evidence.
- [ ] Do not claim hosted SaaS maturity unless current truth explicitly supports it.
- [ ] Keep enterprise language conditional or future-facing when uncertain.

## 10) Privacy and Security Caution

- [ ] Do not claim guaranteed privacy or security absolutes.
- [ ] Use scoped language: local-first posture, explicit boundaries, inspectable surfaces.
- [ ] Avoid compliance-language inflation unless sourced and current.

## 11) Final Approval Checklist

- [ ] Campaign packet includes complete `Do-Not-Say List`.
- [ ] Proof assets needed are listed and ownership is assigned.
- [ ] Reviewer confirms claim posture classifications and evidence links.
- [ ] Final asset remains internal draft unless a human explicitly approves release.
