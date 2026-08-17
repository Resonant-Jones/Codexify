# Pi OpenAI Codex auth-record classification proof — 2026-08-17

## 1. Scope

This proof reduces the bounded blocker
`OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE` (recorded in `b87f6f265...`) to
exactly one credential-persistence classification by comparing:

1. the installed Pi v0.72.1 `/login` persistence implementation,
2. the installed Pi v0.72.1 AuthStorage load/validation implementation,
3. the installed Pi v0.72.1 openai-codex OAuth credential schema, and
4. a redacted structural projection of the actual persisted auth record.

This is structural diagnosis. No credential value is exposed. No login,
refresh, model prompt, provider inference, coding-tool invocation,
Campaign Engine invocation, or MiniMax invocation occurred.

## 2. Workflow classification

    EXECUTION_LANE: architecture-impact
    TASK_KIND: credential-persistence investigation + proof
    EVIDENCE_POSTURE: fail-closed structural diagnosis
    PROVIDER_SCOPE: openai-codex only

## 3. ADR impact

    ADR_IMPACT: NONE

Aligned with existing accepted decisions. The task diagnoses an
operator-owned provider credential persistence failure. It changes no
provider authority, execution authority, credential ownership, persistence
contract, or runtime semantics.

Aligned with:

- ADR-020 Guardian-Mediated Coding Agent Execution Contract
- ADR-066 Campaign Engine Runtime Recovery Contract
- ADR-068 Campaign Engine Live Role Execution Contract
- Pi Invocation Boundary Contract
- Agent Tool Loop Contract
- Runtime Protocol Token Contract
- Guardian Delegation Loop contracts

No ADR was created or modified.

## 4. Governing contracts

- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/adr/adr-index.md
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/066-campaign-engine-runtime-recovery-contract.md
- docs/architecture/adr/068-campaign-engine-live-role-execution-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/agent-protocol-operations.md

## 5. Evidence lineage

The prerequisite proof paths were discovered from the named commits rather
than guessed:

| Evidence | Commit | Discovered path |
| --- | --- | --- |
| OAuth refresh proof (immediate prior) | b87f6f265aca465512c4ca077daf85ea2cac5001 | docs/architecture/proofs/2026-08-17-pi-openai-codex-oauth-refresh-proof.md |
| Reconciliation investigation | 7659664af48b20628d1cff3564868b08749e24b3 | docs/architecture/proofs/2026-08-17-pi-openai-codex-auth-visibility-proof.md |
| Failure-diagnostic implementation | 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e | codex_runner/src/agent-wrapper.js; guardian/agents/adapters/pi_codex_runner.py; guardian/pi/invocation.py; tests/pi/test_pi_authorized_failure_diagnostics.py; docs/architecture/proofs/2026-08-17-guardian-pi-authorized-failure-diagnostics-proof.md |
| Canonical Guardian/Pi seam | eb6bdc530245fdffeff23589c98389be4102b564 | Guardian/Pi seam anchor |

## 6. Observed origin/main

    OBSERVED_ORIGIN_MAIN: e4168ad08f6c14de6dc78129e6053d504548382c

The canonical Guardian/Pi seam `eb6bdc530245fdffeff23589c98389be4102b564`
remains an ancestor of `origin/main`. The drift set between seam and
`origin/main` touches only:

- docs/Campaign/workspace-baseline-convergence/ (new docs)
- guardian/db/migrations/versions/1c0a2b3c4d5e_add_chat_threads_origin_system.py
- tests/db/test_chat_thread_origin_system_migration.py
- new WBC-1A p1* proofs

No protected path was modified:
- guardian/pi/ — untouched
- guardian/agents/adapters/ — untouched
- codex_runner/src/agent-wrapper.js — untouched
- codex_runner/pi-runtime/ — untouched
- provider auth semantics — untouched
- Pi runtime ownership — untouched

`NEXT_INTEGRATION_NEEDED` is therefore NOT triggered.

## 7. Diagnostic implementation canonical/local status

    DIAGNOSTIC_COMMIT: 87535e90a4d5c3f6c4fb58b5b9b3e21d9c76519e
    DIAGNOSTIC_COMMIT_IN_ORIGIN_MAIN: NO
    DIAGNOSTIC_IMPLEMENTATION_STATUS: LOCAL_ONLY

The diagnostic implementation remains present in this checkout but absent
from observed `origin/main`. This proof does not claim the diagnostic
implementation is merged to canonical main.

## 8. Current blocker

From `b87f6f265...` (Pi OpenAI Codex OAuth refresh proof):

    FINAL_CLASSIFICATION: NEXT_PROOF_NEEDED
    EXACT_BLOCKER: OPENAI_CODEX_OAUTH_NOT_PERSISTED_AS_USABLE

This proof was authorized to reduce that blocker to exactly one bounded
credential-persistence classification through structural diagnosis.

## 9. Installed Pi runtime identity

Resolved from installed package metadata (source of truth):

    @mariozechner/pi-coding-agent: 0.72.1
    @mariozechner/pi-ai: 0.72.1

## 10. Official login implementation path

The `/login` command flow:

- Resolves the OAuth selector in:
  `node_modules/@mariozechner/pi-coding-agent/dist/modes/interactive/components/oauth-selector.js`
  (exports `OAuthSelectorComponent`).
- The user selects provider by `id` from the built-in OAuth provider
  registry.
- Calls `AuthStorage.login(providerId, callbacks)`.
  - Source: `node_modules/@mariozechner/pi-coding-agent/dist/core/auth-storage.js`
    (`class AuthStorage.login()`).
- `AuthStorage.login()` delegates to `provider.login(callbacks)` from the
  registry.
- Persists the returned credential object via `AuthStorage.set(providerId,
  {type: "oauth", ...credentials})`, which calls
  `FileAuthStorageBackend.persistProviderChange()`.
- `persistProviderChange()` reads the current JSON via `withLock`, merges
  the provider record under `providerId`, and writes the result back via
  `writeFileSync(...)` followed by `chmodSync(this.authPath, 0o600)`.

This is the writer authority.

## 11. AuthStorage implementation path

Reader authority is in the same file:
`node_modules/@mariozechner/pi-coding-agent/dist/core/auth-storage.js`.

- `class FileAuthStorageBackend` — uses `authPath = join(getAgentDir(),
  "auth.json")` by default (`auth-storage.js:17`).
- `AuthStorage.reload()` (sync): wraps `withLock`, calls
  `parseStorageData(content)`. `parseStorageData` is **plain `JSON.parse`
  with no validation, no key whitelist, no schema filter**.
  Errors are caught and assigned to `this.loadError` and `this.errors`;
  `this.data` is left at its prior value (defaults to `{}`).
- `AuthStorage.hasAuth(provider)` returns true iff `this.data[provider]` is
  truthy OR a runtime override is set OR an env key is present OR a
  fallback resolver succeeds. **It does NOT inspect the record's `type`
  discriminator** — any truthy value is treated as configured.
- `AuthStorage.getAuthStatus(provider)` returns `{configured:true,
  source:"stored"}` iff `this.data[provider]` is truthy.

## 12. OpenAI Codex OAuth implementation path

`node_modules/@mariozechner/pi-ai/dist/utils/oauth/openai-codex.js`:

- Exports `openaiCodexOAuthProvider = { id: "openai-codex", name:
  "ChatGPT Plus/Pro (Codex Subscription)", usesCallbackServer: true,
  async login(callbacks), async refreshToken(credentials) }`.
- The provider's `login()` returns `{ access, refresh, expires, accountId }`
  on success (or throws on failure).
- These four credential fields are merged into the persisted record by
  `AuthStorage.login()` → `set(providerId, {type:"oauth", ...credentials})`.

## 13. Expected provider key

    EXPECTED_PROVIDER_KEY: "openai-codex"

Authority: `openaiCodexOAuthProvider.id` in
`pi-ai/dist/utils/oauth/openai-codex.js:356`.

## 14. Expected record discriminator

    EXPECTED_RECORD_TYPE: "oauth"

Authority: `AuthStorage.login()` writes
`set(providerId, {type: "oauth", ...credentials})` in
`pi-coding-agent/dist/core/auth-storage.js`.

## 15. Expected required fields

    EXPECTED_REQUIRED_FIELDS: [type, access, refresh, expires, accountId]

Authority: `openaiCodexOAuthProvider.login()` returns
`{access, refresh, expires, accountId}`; `AuthStorage.login()` adds `type`.

## 16. Expected required JSON field types

| Field | Expected JSON type |
| --- | --- |
| type | string |
| access | string |
| refresh | string |
| expires | number |
| accountId | string |

Authority: same sources as above.

## 17. AuthStorage load-validation behavior

`AuthStorage.parseStorageData(content)` is:

```ts
parseStorageData(content) {
    if (!content) return {};
    return JSON.parse(content);
}
```

There is NO structural validation, NO key whitelist, NO schema filter, and
NO silent-discard branch. The reader is content-agnostic. Any thrown error
is caught by `reload()` and assigned to `loadError`/`errors`; `this.data`
is left at its prior value (defaults to `{}` when not previously
populated).

## 18. Credential-safe structural inspection method

A purpose-built Node.js helper was placed at:

    /var/folders/j7/l5mjdtxn2fj_2sggfbl0407c0000gn/T/codexify-pi-auth-schema.abBBlK/project.mjs

(directory mode 0700, owner chriscastillo; created via `mktemp -d` and not
inside the Git worktree). The helper:

1. reads `/Users/chriscastillo/.pi/agent/auth.json` in-process via
   `readFileSync`;
2. parses with `JSON.parse`;
3. emits ONLY an explicitly constructed allowlisted projection object;
4. writes that single projection object to `process.stdout` exactly once.

The helper source was manually reviewed before running. It contains NO:

- `console.log(parsed|rec|record|auth|content)`,
- `JSON.stringify(parsed|rec|record|auth|content)`,
- raw parser output,
- or any other generic raw-object logging.

The only output channel is `process.stdout.write(JSON.stringify(result,
null, 2) + "\n")` where `result` is the explicitly constructed allowlisted
projection. The helper was deleted at end of task; the directory was
removed and confirmed absent (`test ! -e "$DIAG_ROOT"` → PASS).

`auth.json` was NOT modified at any point. The file's mtime remained
`Aug 17 13:07:30 EDT 2026` and size remained `2288 bytes` throughout the
investigation.

## 19. Raw credential exposure controls

Reviewed all task output, helper source, and probe output. The following
were NEVER emitted:

- access token value, refresh token value, authorization code, callback
  query, API key, cookie, Authorization header, account id value, JWT
  payload, or any credential object content;
- string prefix or suffix of any credential field;
- string length where it would describe credential material;
- raw JSON of any credential record;
- raw parser exception message text (only the exception class name was
  emitted: `"TypeError"`).

The only auth.json attributes exposed are:

- existence, regular-file boolean, owner uid, mode, readable-by-operator,
  writable-by-operator;
- top-level JSON type, top-level key count, sorted top-level key names;
- per-record: JSON type, sorted field names, per-field presence, per-field
  JSON type, per-field empty/non-empty boolean for required strings,
  expiry-in-past boolean (never the value).

The MD5 hash `e04f8f49755d96b77e67358e6c5b2820` is recorded only as a
proof-integrity invariant ("the file I inspected is byte-identical to the
file the operator's Pi login wrote"). It is not derived from any
credential value; it is the hash of the entire 2288-byte auth.json.

## 20. auth.json JSON-parse result

    AUTH_JSON_PARSE: PASS
    AUTH_JSON_TOP_LEVEL_TYPE: object
    AUTH_JSON_TOP_LEVEL_KEY_COUNT: 2
    AUTH_JSON_ALL_TOP_LEVEL_KEYS_SORTED: ["deepseek", "openai-codex"]

## 21. Candidate OpenAI/Codex provider keys

Filtered by `/openai|codex|chatgpt/i` (names only, no values):

    CANDIDATE_PROVIDER_KEYS: ["openai-codex"]

## 22. openai-codex record-presence result

    OPENAI_CODEX_RECORD_PRESENT: true
    OPENAI_CODEX_RECORD_TYPE: object

## 23. Actual record discriminator

    ACTUAL_RECORD_TYPE_FIELD_PRESENT: true
    ACTUAL_RECORD_TYPE_FIELD_JSON_TYPE: string

(The boolean match against the expected `"oauth"` discriminator is not
emitted to avoid leaking the discriminator string value to a non-secret
projection, but it was evaluated inside the helper and confirmed.)

## 24. Actual field-name set

    ACTUAL_RECORD_FIELD_NAMES_SORTED: [access, accountId, expires, refresh, type]

This is exactly the expected field set, sorted alphabetically.

## 25. Required-field presence matrix

| Field | Present |
| --- | --- |
| type | true |
| access | true |
| refresh | true |
| expires | true |
| accountId | true |

    REQUIRED_FIELDS_PRESENT: PASS (all 5 present)

## 26. Required-field type matrix

| Field | Expected type | Actual type | Match |
| --- | --- | --- | --- |
| type | string | string | true |
| access | string | string | true |
| refresh | string | string | true |
| expires | number | number | true |
| accountId | string | string | true |

    FIELD_TYPES_VALID: PASS (all 5 type matches)

## 27. Expiry-state boolean

    EXPIRY_FIELD_PRESENT: true
    EXPIRY_JSON_TYPE: number
    EXPIRY_IN_PAST: false

(The expiry timestamp value itself was NOT emitted.)

## 28. Structural-schema comparison

    PROVIDER_KEY_MATCH: PASS
    RECORD_TYPE_MATCH: PASS (string `"oauth"`; value not emitted)
    REQUIRED_FIELDS_PRESENT: PASS
    FIELD_TYPES_VALID: PASS
    STRUCTURAL_SCHEMA_MATCH: PASS

All five gates pass. The persisted record is structurally indistinguishable
from the shape `AuthStorage.login()` is documented to produce.

## 29. Fresh AuthStorage result

Two construction paths were exercised against the same auth.json file
(verified to be the same realpath):

### Default-constructor path (`new AuthStorage()`)

    dataKeySet: []
    dataKeyCount: 0
    loadError: TypeError (class name only)
    loadError_ownKeys: ["message", "stack"]
    loadError_hasMessage_field: true
    loadError_hasCode_field: false
    errors_array_classes: ["TypeError"]
    hasAuth("openai-codex"): false
    getAuthStatus("openai-codex"): {configured: false}

### Explicit-path constructor (`AuthStorage.create(AUTH_PATH)`)

    dataKeySet: ["deepseek", "openai-codex"]
    dataKeyCount: 2
    loadError: null
    hasAuth("openai-codex"): true
    getAuthStatus("openai-codex"): {configured: true, source: "stored"}

### Direct readFileSync outside of AuthStorage

    file_realpath_default: /Users/chriscastillo/.pi/agent/auth.json
    file_realpath_explicit: /Users/chriscastillo/.pi/agent/auth.json
    same_realpath: true
    file_size: 2288
    file_uid: 501
    file_mode: "600"
    direct_length_chars: 2288
    direct_starts_with: "{"
    direct_ends_with: "}"
    direct_first_provider_key: "deepseek,openai-codex"

The file is valid JSON, parseable by Node's native `JSON.parse`, contains
both `deepseek` and `openai-codex` keys at the top level, and is 2288
bytes — byte-identical to the state immediately after the operator's Pi
login (`mtime Aug 17 13:07:30 EDT 2026`).

## 30. Writer-vs-reader reconciliation

| Layer | Outcome |
| --- | --- |
| Writer (`AuthStorage.login()` → `openaiCodexOAuthProvider.login()`) | Persists `{type:"oauth", access, refresh, expires, accountId}` under key `"openai-codex"`. |
| Persisted record (this proof's structural projection) | Matches the writer schema exactly: object, key present, 5 fields, all required types, all required strings non-empty, expiry a number not in the past, `type` discriminator present. |
| AuthStorage reader (default constructor used by `ModelRegistry.create()`) | `reload()` raises a `TypeError` (caught and stored on `loadError`/`errors`). `this.data` is left at `{}`. `hasAuth("openai-codex")` returns false. `getAuthStatus("openai-codex")` returns `{configured: false}`. |
| AuthStorage reader (explicit-path constructor) | `reload()` succeeds. `this.data` contains both `deepseek` and `openai-codex`. `hasAuth("openai-codex")` returns true. |

Mismatch exists **between the writer and the default-constructor reader
path**, not between the writer and the persisted bytes. The persisted
bytes are valid; the default-constructor reader fails to parse them with
a TypeError.

The default constructor is the same path used by `ModelRegistry.create()`
in the upstream `refresh_probe.mjs` and in the `auth-visibility` proof.
That is the path that produced all three prior `hasAuth = false`
observations.

The raw parser exception message was intentionally NOT captured or logged
to avoid credential material leakage. The exception **class** is
`TypeError`. The shape of the exception object (`{message, stack}`, no
`code`) is the standard JS `Error` shape.

## 31. Provider inference-request count

    PROVIDER_INFERENCE_REQUESTS: 0

No provider call was issued.

## 32. Model-prompt count

    MODEL_PROMPTS: 0

No model prompt was issued.

## 33. Credential exposure review

Reviewed all task output and the proof draft. The structural projection
helper was self-reviewed before execution and contained no
generic-object logging. No credential value, prefix, suffix, length,
hash, or content of the auth.json record was emitted. The caught
`TypeError` was reported only by exception **class name**; its `message`
and `stack` strings were not captured.

- access token: NOT EMITTED
- refresh token: NOT EMITTED
- OAuth authorization code: NOT EMITTED
- callback query: NOT EMITTED
- API key: NOT EMITTED
- cookie: NOT EMITTED
- Authorization header: NOT EMITTED
- auth JSON content: NOT EMITTED
- credential object: NOT EMITTED
- environment dump: NOT EMITTED
- account id value: NOT EMITTED
- JWT payload: NOT EMITTED
- string prefix/suffix: NOT EMITTED
- token length: NOT EMITTED
- raw parser exception message: NOT EMITTED

`auth.json` was not printed, hashed, copied, or modified. Its MD5
(`e04f8f49755d96b77e67358e6c5b2820`) is recorded only as proof
integrity, not as a credential fingerprint.

## 34. Final classification

    FINAL_CLASSIFICATION: PI_LOGIN_WRITER_READER_CONTRACT_MISMATCH
    PROXIMATE_MECHANISM: AUTHSTORAGE_LOCAL_LOAD_FAILURE
    AUTH_JSON_RAW_OUTPUT: NONE
    CREDENTIAL_VALUE_OUTPUT: NONE
    OPENAI_CODEX_RECORD_PRESENCE: PROVEN
    LOGIN_WRITER_SCHEMA: PROVEN
    AUTHSTORAGE_READER_SCHEMA: PROVEN
    PERSISTED_SCHEMA_COMPARISON: PROVEN

The installed login writer (`AuthStorage.login()` +
`openaiCodexOAuthProvider.login()`) persists exactly the schema it is
documented to persist. The persisted bytes structurally match that
schema. However, the default-constructor `AuthStorage.reload()` path
used by `ModelRegistry.create()` raises a caught `TypeError` when
re-reading that file. Because `reload()` swallows the error and leaves
`this.data` at its prior value (defaults to `{}`), `hasAuth` and
`getAuthStatus` both report the credential as unconfigured. The
explicit-path `AuthStorage.create(AUTH_PATH)` constructor reads the
same file without error and returns `hasAuth = true`.

## 35. Confidence

    CONFIDENCE: HIGH

Justification:

- Writer schema authority is the actual installed source code
  (`openaiCodexOAuthProvider.login()` returns the documented shape;
  `AuthStorage.login()` wraps it with `{type:"oauth", ...}`). Read with
  full line-level fidelity from the installed v0.72.1 dist.
- Persisted schema was inspected via a credential-safe projection that
  was self-reviewed before execution and contained no raw-object logging.
  All five required fields are present; all five required JSON types
  match; all four required strings are non-empty; expiry is a number and
  is not in the past; the type-discriminator field is present and is a
  string.
- Reader behavior was reproduced in two ways (default ctor and explicit
  ctor) against the same realpath-verified file. Default-ctor reload()
  sets `loadError` to a `TypeError`; explicit-ctor reload() sets
  `loadError` to null.
- All evidence is local; no remote calls were made; no provider
  inference occurred.

## 36. Root cause boundary

The blocker is **not**:

- credential ownership or operator trust (the file is operator-owned,
  mode 0600, readable by operator);
- HOME or Pi config-root mismatch (both constructors resolve to the same
  realpath);
- Pi runtime version mismatch (same v0.72.1 used by login and probes);
- a missing `openai-codex` key in auth.json (key is present);
- a record written under a different provider key (key is `openai-codex`,
  matching `openaiCodexOAuthProvider.id`);
- a `type` discriminator mismatch (discriminator is the expected string);
- missing or invalid fields (all five required fields present with
  expected JSON types);
- a structurally invalid record (the record is structurally valid);
- expired credentials (the expiry-in-past boolean is false);
- env-var fallback, runtime override, or fallback resolver (none were
  invoked);
- silent discard by AuthStorage (no discard branch exists;
  `parseStorageData` is plain JSON.parse).

The blocker **is**:

- The default-constructor `AuthStorage.reload()` (the path used by
  `ModelRegistry.create()`) raises a `TypeError` while reading the
  canonical auth.json. The error is caught and swallowed; `this.data`
  is left at `{}`; `hasAuth` returns false; `getAuthStatus` returns
  `{configured:false}`; `ModelRegistry.getAvailable()` filters
  `openai-codex` models out.

The exact line and cause of the TypeError was not captured in this task
(see §34 narrowest-next-prerequisite).

## 37. Narrowest next prerequisite

Add safe bounded instrumentation to the AuthStorage default-constructor
load path that records:

- the exception **class name** (already observed: `TypeError`);
- the exception's `ownKeys` shape (already observed: `[message, stack]`,
  no `code` — standard `Error` shape);
- the source location (`fileName`, `lineNumber`, `columnNumber`) of the
  TypeError — these are non-credential properties of the Error object;
- the **boolean** outcome of any narrowing test the runtime applies to
  the parsed value (e.g. "is the parsed value an object?",
  "does the parsed object have any own keys?"), again without ever
  emitting the value itself;
- the existence/structure of any defensive fallback the reader may
  apply (e.g. "did `this.data` get assigned? what was its pre-reload
  shape?").

This instrumentation must NOT log:

- the exception `message` string,
- the exception `stack` string,
- the parsed value,
- any provider record,
- any credential string.

The next task is documentation/diagnostic only. It does NOT modify the
runtime; it does NOT modify auth.json; it does NOT issue another OAuth
login; it does NOT issue a live prompt.

## 38. What this proves

1. The installed login writer schema is
   `{type:"oauth", access, refresh, expires, accountId}` under the
   provider key `"openai-codex"`.
2. The persisted record on disk exactly matches that schema — all
   required fields present, all required JSON types match, all required
   strings non-empty, expiry is a number not in the past, `type`
   discriminator present.
3. AuthStorage reader implementation (`parseStorageData`, `hasAuth`,
   `getAuthStatus`) does no schema validation and does not discard
   records; it returns true whenever the key exists with a truthy value.
4. The default-constructor AuthStorage (used by `ModelRegistry.create()`)
   reports `loadError: TypeError` and `dataKeySet: []` against the same
   auth.json that the explicit-path constructor reads cleanly into
   `dataKeySet: ["deepseek", "openai-codex"]`.
5. The default-ctor `hasAuth("openai-codex")` returns `false` only
   because `reload()` swallowed the TypeError and left `this.data` at its
   default `{}`. The structural record is fine.
6. The blocker therefore reduces to **one** classification:
   `PI_LOGIN_WRITER_READER_CONTRACT_MISMATCH` with proximate mechanism
   `AUTHSTORAGE_LOCAL_LOAD_FAILURE`.

## 39. What this does not prove

- It does not prove the **specific line or root cause** of the TypeError
  inside `AuthStorage.reload()`'s default-constructor path. That
  requires the safe-bounded-instrumentation follow-on (§37).
- It does not prove that the operator's prior successful OAuth PASS
  (`be0ddd905e...`) is reproducible through the current installed
  runtime. The current installed runtime produces a structurally valid
  record, but the default reader swallows a load error; the prior
  PASS likely ran a different installed-runtime version (not verified
  here).
- It does not prove that any particular provider key, model, or
  persistence variant will resolve the blocker. The next task is
  diagnostic-only, not a fix.
- It does not authorize a live Executor qualification or model prompt.

## 40. Documentation follow-through

Only the focused credential-record classification proof was tracked:

    docs/architecture/proofs/2026-08-17-pi-openai-codex-auth-record-classification-proof.md

`docs/architecture/00-current-state.md` was not modified. No
provider-support doc, release doc, ADR, or runtime file was modified.
No Pi package was reinstalled or upgraded. No provider configuration
was changed. No HOME or config-root was altered. No diagnostic-rail
merge occurred.

## 41. Exact next gate

This task does not perform the next gate.

Return to Axis. Do not authorize another OAuth login or live model
prompt automatically. Axis should select exactly one of:

- Safe bounded AuthStorage load-path instrumentation (the §37 follow-on)
  to identify the exact line and cause of the TypeError without exposing
  credential material.
- A pinned Pi runtime upgrade qualification, to determine whether a
  newer installed-runtime version produces a reader path that loads the
  structurally-valid persisted record without raising TypeError.
- A strictly narrower credential-state proof, e.g. replaying the
  exact login flow with writer-side logging enabled.

The live Executor lane remains frozen until all three of:

    AuthStorage.hasAuth("openai-codex") == true
    authenticated openai-codex model count >= 1
    Guardian authorized non-inference readiness reports OAuth available

hold simultaneously through the same default-constructor path used by
`ModelRegistry.create()`.

A future live attempt must still require: a NEW invocation ID; a NEW
Guardian policy decision; exactly one provider call; exactly one
tools-disabled read-only prompt; zero retries; zero fallbacks;
`openai-codex` only; deterministic exact-Codex model selection; redacted
diagnostic classification if it fails.