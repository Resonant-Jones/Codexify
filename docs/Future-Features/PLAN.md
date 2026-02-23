# Codexify Studio v1 Plan (Paid Add-On, Local-First, Reaper-Canonical)

## Summary
Codexify Studio v1 will be a separate paid add-on product surface, backed by a new Node/TypeScript harness that sits between Codexify backend and Reaper.  
Codexify remains the intent/planning/identity brain; Reaper remains the source of truth for DAW state; Studio harness executes deterministic actions and streams status/events back.  
The MVP focuses on flow essentials: session bootstrap, Strudel MIDI generation with optional audio print, sample/preset retrieval, macro-bank plugin control with 5 curated plugin maps, and stem export profiles.

## 1. Scope and Product Boundaries
1. In scope: Text + MIDI hardware interaction, project/session setup, Strudel pattern operations, plugin/macro control, exports, full action ledger, persona-aware permissions, add-on licensing.
2. In scope: Codexify project-level binding to Reaper project, multiple threads per project, active-thread execution context with shared project DAW state.
3. Out of scope for v1: Full DAW clone parity, voice execution path, multi-persona concurrent command execution, external billing integration, cross-platform parity beyond macOS-first.
4. Principle: No hardcoded values; all paths, ports, plugin lists, compatibility versions, and feature toggles come from config.

## 2. Target Architecture
1. `Codexify Backend` (existing core + new Studio module): Intent parsing, persona/permission enforcement, command validation, orchestration, IDDB persistence.
2. `Studio Harness` (new Node/TS service): Reaper bridge, Strudel engine runtime, asset indexing/search adapters, command execution engine, ack/state/error events.
3. `Reaper Add-On Bundle` (ReaPack package): ReaScripts + OSC config templates + MIDI mapping helpers for deterministic control and state extraction.
4. `Codexify Studio UI` (separate add-on frontend package): Studio workspace focused on immediacy, nested controls, chat/controller-first workflow.
5. `Data Stores`: Postgres for operational records, Chroma/FAISS for semantic asset/action recall, Redis for async events/tasks when needed, Neo4j optional graph enrichment where enabled.

## 3. Public APIs / Interfaces / Types

### 3.1 Backend REST Endpoints (new)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/studio/commands` | Submit a parsed/validated Studio command against active thread context |
| GET | `/api/studio/projects/{project_id}/state` | Retrieve latest mirrored Reaper project snapshot + session context |
| POST | `/api/studio/projects/{project_id}/activate-thread` | Set active execution thread for project-scoped DAW actions |
| POST | `/api/studio/assets/index` | Start/restart indexing for configured sample/preset paths |
| GET | `/api/studio/assets/search` | NLP/semantic retrieval over indexed assets |
| POST | `/api/studio/macros/learn/start` | Begin MIDI learn capture flow |
| POST | `/api/studio/macros/learn/commit` | Persist macro binding for plugin parameter/action |
| POST | `/api/studio/exports` | Start export job with profile and target format bundle |
| GET | `/api/studio/exports/{export_id}` | Poll export state + artifact manifest |
| GET | `/api/studio/compatibility` | Return Reaper/Strudel compatibility checks and status |
| POST | `/api/studio/license/activate` | Activate local perpetual add-on license token |
| GET | `/api/studio/license/status` | Verify local entitlement status and integrity |

### 3.2 Backend ↔ Harness WebSocket Topics (new)
| Direction | Topic | Payload |
|---|---|---|
| Backend -> Harness | `studio.command.execute` | `StudioCommandEnvelope` |
| Harness -> Backend | `studio.command.ack` | accepted/rejected with reason |
| Harness -> Backend | `studio.command.result` | success/failure + outputs/artifacts |
| Harness -> Backend | `studio.state.snapshot` | normalized Reaper project/session snapshot |
| Harness -> Backend | `studio.asset.index.progress` | indexing progress and errors |
| Harness -> Backend | `studio.export.progress` | export lifecycle events |
| Both | `studio.health` | heartbeat + capability status |

### 3.3 New Canonical Types
```ts
type StudioActionFamily =
  | "session"
  | "routing"
  | "plugin_control"
  | "asset_search"
  | "render"
  | "file_io"
  | "destructive_ops";

type StudioCommand = {
  command_id: string;
  project_id: number;
  thread_id: number;
  persona_id: number | null;
  action_family: StudioActionFamily;
  action: string;
  params: Record<string, unknown>;
  requires_confirmation: boolean;
  correlation_id: string;
};

type StudioStateSnapshot = {
  project_uid: string;
  project_name: string;
  bpm: number | null;
  key_signature: string | null;
  time_signature: string | null;
  tracks: Array<{ track_id: string; name: string; type: "audio" | "midi" | "bus" }>;
  fx_summary: Array<{ track_id: string; plugin: string; enabled: boolean }>;
  updated_at: string;
};

type StudioActionLedgerEntry = {
  id: string;
  project_id: number;
  thread_id: number;
  persona_id: number | null;
  provider: string | null;
  action_family: StudioActionFamily;
  action: string;
  intent_text: string;
  params_json: Record<string, unknown>;
  result_json: Record<string, unknown>;
  status: "accepted" | "completed" | "failed" | "cancelled";
  latency_ms: number | null;
  created_at: string;
};
```

## 4. Data Model Additions (Postgres)
1. `studio_project_bindings`: binds Codexify project to Reaper project identity and harness connection metadata.
2. `studio_active_thread`: tracks active execution thread per project; supports many threads per project with one active executor context.
3. `studio_action_ledger`: full audit trail for all Studio commands, outcomes, persona/provider attribution, and artifact references.
4. `studio_plugin_maps`: user-selected curated plugin maps and semantic parameter aliases.
5. `studio_macro_bindings`: MIDI learn bindings (CC/channel/plugin/action/scale/curve).
6. `studio_asset_index_jobs`: indexing lifecycle and diagnostics.
7. `studio_assets`: normalized sample/preset metadata records with tags, source path hash, and availability flags.
8. `studio_exports`: export job records, profile, outputs, manifest path/hash.
9. `studio_license_tokens`: local entitlement token fingerprints and activation metadata (perpetual local mode).

## 5. Permission and Persona Model
1. Execution model: Single active persona for command execution; explicit persona switch required.
2. Scope model: Action-family permissions (`session`, `routing`, `plugin_control`, `asset_search`, `render`, `file_io`, `destructive_ops`).
3. Enforcement point: Backend pre-execution gate; harness never executes unscoped commands.
4. Destructive confirmation policy: Required for delete/overwrite/render-replace/mass-routing-reset/export-overwrite actions only.
5. Memory policy: Log everything; every action written with persona/project/thread tags and embedded for recall.
6. Thread model: Active thread executes commands; project state is shared; rationale and logs remain thread-scoped.

## 6. Command Pipeline
1. User input arrives in Studio UI/chat/controller event.
2. Codexify intent parser generates structured `StudioCommand`.
3. If parser uncertainty or provider unavailable: deterministic DSL fallback parser runs.
4. If required params missing: ask minimal clarification; else proceed.
5. Persona/tool-scope + destructive confirmation checks run.
6. Backend emits `studio.command.execute` to harness.
7. Harness executes via ReaScript/OSC/MIDI chain and returns result/snapshot.
8. Backend writes ledger, emits outbox events, updates thread/project context summaries.

## 7. Reaper + Strudel Integration Design
1. Primary control path: ReaScript command execution with OSC telemetry and MIDI fallback.
2. Strudel default mode: MIDI generation to configured virtual MIDI bus; optional on-demand audio print into Reaper.
3. Audio print flow: Arm print track, set bar window, record aligned region, annotate artifact in ledger.
4. Plugin control strategy: Macro bank first, direct params when stable, fallback to MIDI CC learn where direct mapping is fragile.
5. Curated mappings: User-selectable top 5 plugins in Studio settings, map templates generated/edited per plugin version.
6. Compatibility: Pinned matrix file for supported Reaper + Strudel versions; startup compatibility check endpoint blocks unsafe execution.

## 8. Add-On Packaging and Licensing
1. Studio UI ships as separate add-on package, not merged into free Codexify UI runtime.
2. Entitlement model: Local perpetual license token after activation; backend integrity checks are advisory, not hard requirement for offline usage.
3. Activation flow: one-time activation endpoint returns signed token; token stored locally with integrity fingerprint.
4. Failure policy: if backend unavailable post-activation, Studio remains fully functional offline.

## 9. Implementation Milestones

1. **Milestone A: Studio Contracts + Skeleton**
- Deliverables: New Studio API surface, WS topic schemas, config loader, compatibility endpoint, empty harness with health events.
- Exit criteria: End-to-end command echo path works with correlation IDs and ledger writes.

2. **Milestone B: Reaper Bridge Core**
- Deliverables: ReaPack bundle scaffolding, command executor subset (`create_track`, `set_tempo`, `route_bus`, `insert_fx`, `arm_record`), state snapshot extraction.
- Exit criteria: Deterministic project bootstrap from command payloads with round-trip state verification.

3. **Milestone C: Strudel Engine Path**
- Deliverables: Strudel runtime in harness, MIDI emission bridge, optional audio print command, bar-aligned recording flow.
- Exit criteria: Prompt -> Strudel pattern -> MIDI in Reaper -> optional printed audio clip with ledger artifact record.

4. **Milestone D: Asset Retrieval + Maps**
- Deliverables: User-configured path indexing, NLP/semantic asset search, macro learn capture/commit, curated plugin map management.
- Exit criteria: “Find X sample/preset” and “map macro Y” commands work reliably on configured libraries/plugins.

5. **Milestone E: Export + Packaging**
- Deliverables: export profiles (`WAV24`, `MP3 ref`, `Stem pack`), manifest generation, separate Studio add-on UI package, license activation/status flow.
- Exit criteria: One-click exports produce all artifacts and complete manifest; add-on entitlement enforced in UI/backend.

6. **Milestone F: Persona + IDDB Deepening**
- Deliverables: action-family permission policies, active-thread project execution gates, session rehydration payload builder with depth-aware detail expansion.
- Exit criteria: Thread resume reliably restores context without token bloat and honors persona scopes.

## 10. Testing and Acceptance

### 10.1 Automated Tests
1. Unit tests: command schema validation, DSL fallback parser, permission gate logic, destructive confirmation rules, compatibility matrix checks.
2. Integration tests: backend↔harness WS contracts, ledger persistence, outbox event emission, active-thread project binding behavior.
3. Integration tests: macro learn persistence, curated map resolution, asset indexing/search ranking basics.
4. API tests: Studio endpoints auth and error envelopes.
5. Contract tests: ReaScript adapter interface with mock Reaper executor.
6. Licensing tests: activation, token tamper detection, offline perpetual behavior.

### 10.2 Manual / System Tests (macOS-first)
1. Empty project bootstrap under 60 seconds from first command to audible output.
2. Multi-thread same-project behavior: active thread executes; non-active threads remain non-executing but fully conversational.
3. Strudel MIDI generation and optional audio print for fixed bar ranges.
4. Plugin mapping fallback: when direct param unavailable, macro/CC path still controls target.
5. Export profile validation: full mix WAV24, MP3 reference, stems with manifest.
6. Failure drills: harness offline, Reaper closed, incompatible version, missing asset paths, permission-denied persona.

### 10.3 Acceptance Criteria
1. `Time-to-first-sound <= 60s` on supported setup.
2. `>= 90%` of top command catalog executes without manual cleanup in test corpus.
3. `100%` of destructive ops require confirmation.
4. `100%` of Studio actions create ledger entries with persona/project/thread attribution.
5. Session rehydration includes project summary + depth-aware detail expansion with no unbounded prompt growth.

## 11. Assumptions and Defaults Locked
1. Product name remains `Codexify Studio`; harness internal name can be `Studio Harness`.
2. v1 target platform is macOS first.
3. Reaper-side install uses ReaPack bundle.
4. Harness runtime is Node/TypeScript.
5. Interaction priority is Text + MIDI hardware; voice is deferred adapter work.
6. Reaper is canonical for DAW/timeline state.
7. Strudel default is MIDI with optional audio print.
8. Intent parsing lives in Codexify backend; harness executes deterministic actions.
9. Backend↔harness uses WebSocket topic protocol.
10. Full action ledger persistence is mandatory.
11. Studio ships as separate paid add-on package.
12. Entitlement model is perpetual local license after activation.
13. Curated plugin maps are user-selectable initial 5.
14. Asset indexing is user-configured paths only.
15. Compatibility policy is pinned Reaper/Strudel matrix.
16. Mapping model is Codexify Project ↔ Reaper Project with many threads; active thread executes commands and project state is shared.
17. Design requirement: modular configuration only, no hardcoded operational values.
