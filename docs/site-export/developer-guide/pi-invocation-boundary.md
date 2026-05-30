# Pi Invocation Boundary

This page summarizes the Pi Invocation Boundary doctrine as a governed seam, not as a shipped live integration.

## Current Truth

- the contract and validation seam exists
- no live Pi SDK call is shipped
- no Minimax provider behavior changed
- no provider routing behavior changed
- no autonomous execution was added

## Governance Rule

Guardian owns policy, lineage, transcript handling, and result return.
That ownership does not move to the harness.

## Provider Lane Separation

Minimax stays framed as a provider lane concern.
It is not the invocation-governance layer itself.

## Boundary Meaning

The boundary exists so external or mediated harnesses cannot quietly redefine runtime authority.
Any future invocation must remain bounded, inspectable, and return through governed continuation paths.

## What This Page Does Not Claim

This page does not claim live invocation, sandboxed autonomous harness execution, or a new provider lane.
It only preserves the contract boundary that keeps those things separated.
