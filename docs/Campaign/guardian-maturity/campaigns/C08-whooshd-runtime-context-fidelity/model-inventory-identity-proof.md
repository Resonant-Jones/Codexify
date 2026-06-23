# C08-T003 Model Inventory Identity Proof: Whoosh'd

## Gate Decision

**`go`** — C08-T004 may proceed by name only.

## Scope

This proves model inventory identity semantics only. It does **not** prove endpoint health, context fidelity, system identity delivery, or operator diagnostics. It does **not** alter runtime behavior.

## Model Profile Source Map

| Element | Source | Detail |
|---------|--------|--------|
| Profile files | `config/whooshd/model-profiles/*.json` | File-backed JSON registry |
| Loading path | `whooshd_model_profiles.py` | `_profile_paths()` + glob |
| Consuming code | TBD (not yet proven) | Profile loading used for sidecar/detect? |
| Default behavior | No profiles → empty list | `_profile_paths` returns `[]` for missing dir |

## Identity Field Map

| Field | Source | Value Example | Canonical? |
|-------|--------|---------------|------------|
| Registry/Profile ID | `profile["id"]` | `gemma-4-12b-it-optiq-4bit` | Yes — registry identity |
| HuggingFace Repo ID | `profile["model"]["repo"]` | `mlx-community/gemma-4-12B-it-OptiQ-4bit` | No — repo path |
| Runtime model ID | TBD | TBD | May be repo, may be endpoint-discovered |
| Display label | `profile["display_name"]` | `Gemma 4 12B Instruct OptiQ 4-bit` | No — human readable only |
| Runtime family | `profile["runtime"]["kind"]` | `mlx` | Yes — MLX marker |
| Provider ID | `profile["provider_id"]` | `local` | Yes — provider marker |

### Key Finding

Registry/profile ID ≠ repo ID. They are distinct fields in the profile schema.

## Inventory Source Map

| Source | Status | Access |
|--------|--------|--------|
| File-backed profiles | ✅ Present | `whooshd_model_profiles.py` |
| Endpoint-discovered `/v1/models` | Called in `whooshd_sidecar.detect()` | Runtime, not inventory |
| Endpoint-discovered `/api/tags` | Called in `whooshd_sidecar.detect()` | Runtime, not inventory |
| Caching | None observed | N/A |

## Truth Table

| Claim | Status |
|-------|--------|
| Profile source known | `true` |
| Registry/profile ID known | `true` |
| Repo ID/path known | `true` |
| Runtime model ID known | `not true` (not proven) |
| Display label known | `true` |
| Runtime family/type known | `true` |
| Endpoint-discovered inventory proven | `not true` (runtime only) |
| `/v1/models` inventory proven | `not true` (called but semantics unproven) |
| `/api/tags` inventory proven | `not true` (called but semantics unproven) |
| Duplicate registry/profile ID handling proven | `not true` (not enforced — gap) |
| Duplicate display label handling proven | `not true` (not enforced — gap) |
| Malformed profile handling proven | `not true` (no validation — gap) |
| Model warming/loading state proven | `not true` |
| Model inventory operator-visible | `not true` |
| Endpoint health proven | `true` (C08-T002) |
| Context fidelity proven | `not true` |
| System identity delivery proven | `not true` |
| Operator diagnostics proven | `not true` |

## Boundary Table

| Boundary | Status |
|----------|--------|
| Model inventory ≠ endpoint health | Explicit |
| Model inventory ≠ context fidelity | Explicit |
| Model inventory ≠ system identity delivery | Explicit |
| Model inventory ≠ operator diagnostics | Explicit |
| Profile existence ≠ model loaded | Explicit |
| Registry ID ≠ repo ID | Test-proven |
| Repo ID ≠ canonical runtime ID | Not proven |
| Display label ≠ canonical identity | Test-proven |
| Runtime family ≠ provider availability | Explicit |

## Gap Register

| Gap | Evidence | Blast Radius | Proposed Task |
|-----|----------|-------------|---------------|
| Duplicate profile IDs not rejected | Test-proven | Operator sees duplicate models | C08-T003-dup (future) |
| Malformed profiles not validated | No validation function exists | Crash on load | C08-T003-validate (future) |
| Runtime model ID not proven | Repo ID vs endpoint ID unresolved | Wrong model routed | C08-T003-runtime-id (future) |
| Model inventory not operator-visible | No UI surface for Whoosh'd models | Operator blind | C08-T005 |

## Risk Register

| Risk | Evidence | Mitigation |
|------|----------|------------|
| Repo ID silently used as runtime ID | Not proven — could be implicit | C08-T003-runtime-id |
| Display label collision causes operator confusion | Duplicate display labels not prevented | C08-T003-dup |
| Profile registry diverges from endpoint inventory | `/v1/models` may return different models | C08-T004 context proof |

## Test Evidence

| Test file | Count | Coverage |
|-----------|-------|----------|
| `tests/core/test_whooshd_model_inventory_identity_semantics.py` | 14 | Profile loading, registry/repo/display identity separation, runtime family, duplicate handling gap, health boundary, context/system identity boundaries |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C08-T004: Prove Whoosh'd context bundle and system identity delivery`
