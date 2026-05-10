# Codexify Open-Core Boundary (v1)

Date: 2026-05-10  
Status: Baseline boundary proposal

## Goal
Define what goes public now versus what stays private for a limited period, without weakening Codexify's trust or long-term business viability.

## Boundary and Trust Model
### Nodes
- Local user machine (desktop/web + local compose runtime).
- Optional home server/self-host node.
- Optional future cloud relay/operator node.
- External provider nodes (LLM vendors, optional integrations).

### Trust Boundaries
- Device boundary: user-controlled local runtime versus any hosted relay.
- User boundary: account/user/thread ownership and scoped data access.
- Network boundary: local-only path versus egress to external providers.

### Threat Model (baseline)
- Honest-but-buggy operator configs.
- Malicious external dependency/provider responses.
- Compromised or misconfigured node leaking secrets/metadata.

## Open-Core Contract
### Public Now (`Tier O`)
- Guardian backend runtime core.
- Frontend runtime surfaces needed for normal usage.
- Retrieval broker/source-mode policy and diagnostics.
- Provider governance truth surfaces.
- Supported local Docker Compose install path.
- Architecture docs and release-truth docs that reflect current state.

### Public But Commercially Leveraged (`Tier M`)
- Queue/worker runtime operations playbooks.
- Coding-result return-path hardening and reliability workflows.
- Command-bus security posture templates and audit workflows.
- Migration/upgrade runbooks and rollback procedures.
- Packaged distribution operations and managed lifecycle support.

### Private for Now (`Tier I`)
- Internal-only operator/control-plane routes not yet public-contract ready.
- Connector/federation activations that widen risk before defaults are hardened.
- Internal incident material that leaks sensitive topology or secrets patterns.

## What Stays Open Even If Service Is Paid
- Core source code and contracts for supported open surfaces.
- Build/install instructions for local self-hosting.
- Public issue tracker for bugs and reproducibility gaps.
- Public architectural constraints and release-truth doctrine.

## What Is Paid
- Fast installation on user-specific hardware/networks.
- Reliability engineering and upgrade-safe maintenance.
- Policy/security hardening for identity, tools, and egress.
- Incident response and operational accountability.

## Release Controls
Any surface promoted into public support must have:
- Explicit API/contract documentation.
- Fail-closed defaults where security applies.
- Upgrade/migration notes.
- Minimal proof harness or reproducible validation path.
- Clear support boundary (what is and is not included).

## 6-Month Boundary Review Cadence
- Monthly: re-score capability slices in `codexify-release-tier-index.md`.
- Every 60 days: evaluate `Tier I` surfaces for promotion to `Tier M`.
- At 6 months: publish `v2` boundary with evidence of what moved and why.

## Licensing and Governance Recommendation
- License baseline: `Apache-2.0` for broad adoption, contributor friendliness, and commercial compatibility.
- Alternative if anti-hosted-fork pressure becomes primary: evaluate `AGPL` tradeoffs before switching.
- Governance: solo-maintainer model with explicit contribution policy and security disclosure process.

## Minimum Public Narrative
Codexify is open where users need trust and reproducibility. Paid offerings exist where users need speed, reliability, and accountable operations.
