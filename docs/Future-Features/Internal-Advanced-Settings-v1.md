# V1 Internal Advanced Settings

## Summary
Ship a narrow, internal-only `Advanced Settings` surface as an operator convenience layer, not as a release-grade control plane.

Boundaries:
- Nodes: frontend app, backend API container, shared mounted `guardian/` volume.
- Trust boundaries: admin-authenticated UI to backend; backend to local override files.
- Threat model: local operator / honest-but-buggy admin. This is not a multi-tenant or hardened control surface.

V1 principles:
- No lazy settings proxy.
- No broad editable catalog.
- No `.env` mutation.
- Explicit snapshot-based override loading only in the subsystems we intentionally support first.

## Public Interfaces
Add an admin-only beta API:
- `GET /api/admin/runtime-settings`
- `PATCH /api/admin/runtime-settings`

Response shape:
- `scope: "machine_global"`
- `beta: true`
- `items: Array<{ key, label, kind, value?, source, editable, applyBehavior, description }>`
- `audit_tail?: Array<{ timestamp, actor, changedKeys, liveKeys, restartRequiredKeys, invalidationOk }>` optional, small tail only

Request shape:
- `PATCH` accepts `{ changes: Record<string, string | null> }`
- `null` clears an override for that key
- Reject the patch if it violates supported-profile or supported-path validation

UI access:
- Keep the existing Settings view
- Add a plain `Advanced Settings` link/button there with the shortcut shown inline
- Add one new AppShell primary view: `advanced-settings`
- Global shortcut: `Cmd+,` on macOS, `Ctrl+,` elsewhere

## Implementation Changes
### 1. Override loader and storage
Create a dedicated backend module, for example `guardian/runtime/runtime_settings.py`, with:
- `load_runtime_overrides()`
- `get_effective_runtime_settings()`
- `apply_runtime_overrides(changes, actor)`
- `invalidate_runtime_caches(changed_keys)`

Persistence:
- `guardian/config/runtime_overrides.json`
- append-only audit file: `guardian/config/runtime_overrides.audit.jsonl`

Write behavior:
- atomic write for the JSON override file
- append one audit record per successful patch
- do not touch Docker Compose `.env`

Base settings:
- start from the existing `guardian.core.config.Settings()` snapshot
- overlay only the V1-supported keys
- do not change `settings` import behavior anywhere

### 2. Narrow V1 catalog
Editable in V1:
- `LOCAL_CHAT_MODEL`
- `LOCAL_BASE_URL`

Visible but read-only in V1:
- `LLM_PROVIDER`
- `ALLOW_CLOUD_PROVIDERS`
- `CODEXIFY_LOCAL_ONLY_MODE`

Rules:
- If effective `LLM_PROVIDER` is not `local`, disable all editing and show a plain beta note
- Do not expose or edit:
  - provider API keys
  - auth/admin/session secrets
  - storage paths
  - embedding backend/model
  - websocket limits
  - any bootstrap-sensitive or partially governed setting

Metadata:
- each item carries `editable: boolean`
- each item carries `applyBehavior: "live" | "restart_required" | "n/a"`

For this V1 subset:
- `LOCAL_CHAT_MODEL`: `live`
- `LOCAL_BASE_URL`: `live`
- read-only visibility items: `n/a`

### 3. Narrow backend adoption
Adopt `get_effective_runtime_settings()` only in these supported paths:
- local chat/completion routing path for new requests
- `/api/llm/catalog`
- `/health/llm`
- supported-profile runtime validation helpers that gate the supported local contract

Do not adopt overrides in V1 for:
- voice
- TTS
- embeddings
- MemoryOS singleton construction
- websocket router globals
- boot-time service wiring

### 4. Validation and auditability
Before persisting a patch:
- build the post-change effective snapshot
- run supported-profile/runtime validation for the local path
- reject invalid changes with a clear error

After persisting a patch:
- run targeted cache invalidation only for the supported local-routing surfaces
- record audit fields:
  - changed keys
  - old source and new source
  - apply behavior per key
  - actor identity
  - timestamp
  - cache invalidation success/failure

No silent success:
- if invalidation fails, return success for persistence plus explicit degraded invalidation status
- also append that status to the audit record

## UI
Keep it boring and canon-compliant:
- one `Advanced Settings` link from normal Settings
- one `advanced-settings` primary block
- standard card/token stack only
- plain form/table layout
- no custom geometry/colors beyond existing tokens

Screen contents:
- beta/internal note at top
- small table of visible settings
- editable controls only for `LOCAL_CHAT_MODEL` and `LOCAL_BASE_URL`
- source badge per row: `env`, `override`, or `default`
- apply behavior badge per row
- `Apply changes` and `Reset` actions only

## Test Plan
Backend:
- `GET` returns only the approved V1 keys
- `PATCH` only accepts `LOCAL_CHAT_MODEL` and `LOCAL_BASE_URL`
- invalid keys are rejected
- supported-profile and supported-path validation still pass after valid overrides
- invalid overrides are rejected without changing files
- audit JSONL record is appended with actor, timestamp, sources, apply behavior, and invalidation result
- clearing an override falls back to env/default

Frontend:
- Settings page shows the `Advanced Settings` link with shortcut hint
- shortcut opens the advanced-settings view
- advanced view renders one primary block with plain tokenized controls
- read-only rows are visibly non-editable
- apply/reset flow works and shows validation errors plainly

Proof / regression:
- add tests proving `/api/llm/catalog` and `/health/llm` reflect valid overrides
- add tests proving supported-profile checks still pass on accepted overrides
- explicitly keep this surface out of release-signoff assertions and release-language docs

## Assumptions
- This surface is admin-only and beta/internal by design
- Machine-global scope is acceptable for V1
- In-flight work keeps its original config; only new requests use overrides
- V1 supports only the local provider/runtime path
- This is not the canonical future control plane; it is an internal operator convenience layer
