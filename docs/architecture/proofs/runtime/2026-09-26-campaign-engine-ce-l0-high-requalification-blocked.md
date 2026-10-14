# CE-L0 current-tip Guardian/Pi requalification — 2026-09-26

## Result

`BLOCKED` at canonical non-inference OAuth readiness. No live provider
invocation occurred, so this record does **not** emit
`CE-L0_EXIT=GUARDIAN_PI_LIVE_READY`. CE-L1 remains gated. Historical CE-L0
proofs are unchanged, and no release claim is widened.

## Source and repair provenance

| Field | Value |
| --- | --- |
| Branch | `codex/campaign-engine-closure` |
| Proof-time HEAD | `5a8f6c33cd10a780d95a5f27c1c6a97d4a20ecf5` |
| `origin/main` at proof time | `4041440110a2c9c42fe8898ffafc7eb9b2a4255a` |
| Working tree before proof | clean; branch ahead of `origin/main` by the scoped repair commit |
| Repair | `5a8f6c33` — Guardian-owned effort and authorized-wide Pi retry suppression |
| Harness package | vendored `pi-coding-agent@0.82.1` |
| Frozen provider/model/harness | `openai-codex / gpt-5.6-sol / pi-coding-agent / 0.82.1` |
| Requested live effort | `high` |

The repair was validated before readiness with
`./.venv/bin/pytest -q tests/pi/test_pi_live_invocation.py tests/pi/test_pi_required_tool_selection.py --tb=short`
(85 passed), `node --check codex_runner/src/agent-wrapper.js`, and
`git diff --check`. Focused fake-Pi tests prove High effort projection and
retry/compaction suppression for read-only authorized sessions. Those tests
are provider-free and are not live CE-L0 proof.

## Disposable target and authorization

The target was a fresh isolated Git repository at
`/var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/ce-l0-current-tip-j5kgjmlp`.
It had no remotes or credentials and contained only `README.md` and
`src/value.py`. Guardian's envelope granted `files.read` on `.` only;
`validate_policy_decision_against_envelope` returned `ok=true`.

| Snapshot | Before | After |
| --- | --- | --- |
| Target HEAD | `408de5a437cce65b152495219b4a44d2633003aa` | same |
| `git status --porcelain` | clean | clean |
| `README.md` SHA-256 | `6ec5e753b4aa74710ea2106131d122052894e2006638bef51019e07adef3c675` | same |
| `src/value.py` SHA-256 | `e13df8c44af5dea1e412403910b99cc5a48f2ccbf68a66b3374d6ab9cef9fc65` | same |

## Canonical readiness and stop

The operator called `preflight_guardian_authorized_pi` once with the frozen
identity and the disposable target. It returned:

| Field | Value |
| --- | --- |
| `ok` | `false` |
| `deepest_stage` | `identity_verified` |
| `failure_class` | `oauth_auth_unavailable` |
| `failure_stage` | `oauth_readiness` |
| `preflight_call_count` | `1` |
| `retry_count` / `fallback_count` | `0` / `0` |

The local `~/.pi/agent/auth.json` was present and parseable but had no
`openai-codex` record. This check inspected only structural presence; no
credential value, token, auth file body, or environment dump was retained.
The reason for the missing record was not established. No login, token
refresh, provider substitution, model substitution, or fallback was attempted.

The proof driver was first launched without its repository Python import
path; it exited at `ModuleNotFoundError` before constructing an envelope or
calling readiness. The corrected launch performed the single readiness call
above. It did not call `invoke_guardian_authorized_pi` because readiness
failed. Therefore live provider invocation count is **zero**, and there is
no current-tip Receipt or Harness Result to validate. The intended prompt
(`Reply with exactly: CE_L0_PI_LIVE_OK`) was never sent.

## Next boundary

Establish a valid `openai-codex` Pi auth record in this execution environment
through the normal operator-controlled authentication path, then run a new
bounded CE-L0 qualification from its then-current committed tip. Do not infer
readiness from the existence of the auth file or from another host. CE-L1
must wait for `GUARDIAN_PI_LIVE_READY` from a real validated live invocation.
