# Provider-free Guardian/Pi timeout phase proof — 2026-09-26

## Result and provenance

The Guardian/Pi adapter now preserves a bounded, ordered phase prefix across
`subprocess.TimeoutExpired`. This is a provider-free diagnostic proof. It is
not CE-L0 live qualification.

| Field | Value |
| --- | --- |
| Branch | `codex/campaign-engine-closure` |
| Tested implementation commit | `adc750a4ddbab53751fe1f35dd725e68026e7577` |
| Governing decision | ADR-068; observational repair, no new ADR |
| Fixture | `tests/pi/fixtures/fake_pi_package/source/index.js`, materialized as an in-memory fake Pi 0.82.1 package |
| Target | Temporary read-only directory containing `proof.txt` |
| Provider/model/harness request | `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1`, fake resolution only |
| Selected effort | `high` |
| Child deadline | 2 seconds per fake timeout case |

The fake Pi package resolves model and authentication availability in memory.
Its timeout modes use a local timer after wrapper setup or after the first
`onPayload` call. They make no network, provider, or OAuth request. No real
provider-backed inference was run for this proof.

## Observed timeout cases

| Fake behavior | Exact recovered phase sequence | Highest phase | Effective effort | `provider_request_started` |
| --- | --- | --- | --- | --- |
| `hang-after-payload` | `wrapper_started`, `runtime_identity_established`, `session_initialized`, `provider_request_started` | `provider_request_started` | `high` | `true` |
| `hang-before-payload` | `wrapper_started`, `runtime_identity_established`, `session_initialized` | `session_initialized` | `high` | unknown (`null`) |

Both cases exercised a real Node child-process timeout through the canonical
Guardian adapter, with `adapter_timeout` / `adapter_execution`, `ok=false`,
one runner call, zero Guardian retries, and zero fallback. Neither produced
a Receipt, Harness Result, or terminal actual identity. The after-payload
case also inspected the raw timed-out child: stdout contained only the fake
SDK diagnostic line and no terminal authorized JSON frame.

Guardian's before/after read-only target check ran for both cases. The sole
target file remained `proof.txt` with the original `unchanged\n` contents.
A separate test changed a read-only target while supplying timeout phase
evidence and confirmed `target_posture_violation` retained precedence; the
phase trail was not surfaced as success.

The strict parser accepted UTF-8 bytes and strings, ignored ordinary
non-sentinel stderr, and rejected malformed, duplicate, skipped,
out-of-order, unsupported, extra-key, and invalid-effort sentinel frames.
Its documented rule invalidates the whole trail on any invalid sentinel
frame. Absence of a later valid phase remains unknown.

## Validation on the tested commit

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/pi` | passed, provider-free |
| `.venv/bin/python -m ruff check guardian/agents/adapters/base.py guardian/agents/adapters/pi_codex_runner.py guardian/pi/invocation.py guardian/pi/tokens.py tests/pi/test_pi_authorized_failure_diagnostics.py tests/pi/test_pi_live_invocation.py` | passed; existing deprecated-linter-setting warning only |
| `node --check codex_runner/src/agent-wrapper.js` | passed |
| `git diff --check` | passed |

The Pi invocation contract now documents the framing, privacy exclusions,
timeout recovery, and evidence-only semantics. ADR-068's Guardian authority,
one-attempt execution, provider/model/harness identity checks, and no-retry
or fallback boundaries are unchanged. Campaign Engine runtime and release
claims are unchanged.

**CE-L0 remains unqualified.** A separately authorized, current-tip live
provider proof is required before `GUARDIAN_PI_LIVE_READY` can be recorded.
CE-L1 remains gated.
