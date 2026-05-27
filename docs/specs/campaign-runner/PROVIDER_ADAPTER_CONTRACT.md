# Campaign Runner Provider Adapter Contract

## Purpose

Define the stable adapter boundary between Campaign Runner core orchestration and any execution backend used to satisfy campaign, audit, compile, or task prompts.

## Scope

This contract governs Campaign Runner and Guardian-owned coding-agent execution for:

- adapter selection
- backend invocation
- backend receipt preservation
- schema-valid structured output handling
- explicit retry and fallback behavior

## Non-goals

- proving live Pi SDK dispatch on every supported path
- redefining global Codexify provider routing
- replacing Guardian ownership of lineage, auditability, or result return
- widening supported release promises beyond current local-first posture

## Boundary model

Campaign Runner core is the stable orchestration architecture boundary.

- Core owns orchestration semantics.
- Provider adapters are replaceable integrations.
- Providers perform the actual inference work behind the adapter boundary.
- A broker adapter such as Pi may resolve multiple downstream provider/model lanes without teaching Campaign Runner core how to invoke each one directly.

## Responsibility split

### Campaign Runner Core responsibilities

- campaign lifecycle
- schema validation
- artifact isolation
- git safety
- checkpoint enforcement
- handoff generation
- forbidden-zone enforcement
- adapter selection by declared contract only
- rejection of schema-invalid outputs
- preservation of backend receipts

### Provider Adapter responsibilities

- prompt execution
- backend invocation
- backend metadata reporting
- retry policy
- structured output mode
- provider-specific configuration
- model routing behind the adapter boundary
- fallback reporting
- backend receipt generation

### Provider responsibilities

- actual inference execution
- provider-native model serving
- provider-native failure responses
- provider-native availability constraints

## Required backend receipt

Every brokered execution path should preserve a backend receipt with at least:

```text
backend_provider:
backend_version:
resolved_provider:
resolved_model:
schema_mode:
execution_mode:
passes:
fallback_chain:
retry_count:
error_code:
```

Backend declaration is mandatory. Provider switching must never be silent.

## Dependency posture

- Campaign Runner must not require direct Codex binaries.
- Campaign Runner must not require direct Claude binaries.
- Campaign Runner must not pin Codex or Claude CLI executables.
- Campaign Runner must not install Codex or Claude packages solely to execute this module.
- Campaign Runner must not expose direct `codex` or `claude` provider choices.
- Codex/Claude may appear only as resolved downstream provider/model identities when Pi reports them in receipts.
- Direct provider adapters are optional only when explicitly added later through ADR-backed contract work.
- For this module, Pi is the preferred provider-broker adapter when available.

## Failure and retry rules

- schema-invalid output must be rejected
- retry behavior must be explicit
- fallback chains must be logged
- backend mismatch must fail closed
- adapters must report when fallback or retry changed the effective backend
- adapters must not mutate Campaign Runner core semantics
- provider-specific assumptions must not enter runner orchestration

## Adapter class policy

Recommended direct adapter classes for this module:

- `pi`
- `noop/manual`

Explicitly excluded direct adapter classes for this module:

- `codex`
- `claude`
- `claudecode`

Direct Codex/Claude execution is forbidden for this module unless a later ADR explicitly reverses this decision.

## Implementation posture

- adapters are integrations, not architecture
- runner orchestration is the stable architecture boundary
- adapter implementations may change without redefining Campaign Runner semantics
- Pi can broker many model/provider lanes without Campaign Runner depending on each one directly
- current release truth still treats Pi invocation as a bounded seam unless code proves live dispatch and receipt preservation on a supported path

## Open questions

- When the live Pi receipt path is fully proven, should Guardian persist the entire receipt verbatim or normalize it into a Campaign Runner receipt schema plus raw attachment?
- Should `pi_sdk` and `pi_codex_runner` remain legacy-compatible aliases indefinitely, or should they be retired after persisted job/state migration?
- What is the smallest supported receipt surface that can preserve downstream transparency without binding core orchestration to Pi internals?
