# Luna UIS — Architecture

A spine-native agent: one append-only event log, a reducer that projects
it into context, a model that reads that context and acts through tools,
and a continuity vector the model writes itself. No hidden state. If it
isn't in the log, it didn't happen.

---

## 1. The spine

`uis/world.jsonl` is an append-only JSONL file. One event per line. Events
are never edited — corrections go in as new events. The file rotates at
midnight into immutable daily segments (`world-YYYY-MM-DD.jsonl`), sealed
with a sha256; `seq` and `id` are global and never reset.

### Event envelope

Every event has the same shape:

```json
{
  "schema_version": 1,
  "id": "evt_000345",
  "seq": 345,
  "ts": "2026-07-07T23:33:04+12:00",
  "type": "tool_call",
  "actor": "luna",
  "node": "mac_studio",
  "source": "tool_dispatcher",
  "payload": { "...": "type-specific" },
  "provenance": {
    "trace_id": "trace_000341",
    "parent_event_ids": ["evt_000344"]
  }
}
```

- `id` — stable identity, never reused.
- `seq` — global monotonic ordering across all segments.
- `ts` — wall-clock ISO timestamp, local timezone.
- `actor` — who/what caused it: `zac` (user), `luna` (model), `system` (observer).
- `node` — origin node (`mac_studio` today).
- `source` — the component that wrote it (`model_harness`, `tool_dispatcher`, an observer name, `spine`).
- `provenance.trace_id` — the turn/trace this event belongs to.
- `provenance.parent_event_ids` — strict causal chain: each event points at its immediate predecessor.

### Event types

| type | actor | source | meaning |
|---|---|---|---|
| `user_message` | `zac` | `model_harness` | user input opens a trace |
| `assistant_message` | `luna` | `model_harness` | model reply (intent or synthesis) |
| `tool_call` | `luna` | `model_harness` / `tool_dispatcher` | a tool was invoked |
| `tool_result` | `luna` | `model_harness` / `tool_dispatcher` | the tool's outcome/receipt |
| `system_event` | `system` / `luna` | observer / `spine` / `write_continuity` | automated reality + meta |
| `artifact_created` | `luna` | `tool_dispatcher` | a durable file was written to the archive |

### Examples

**user_message**
```json
{
  "type": "user_message", "actor": "zac", "source": "model_harness",
  "payload": { "text": "whats the weather?", "context_hash": "sha256:..." },
  "provenance": { "trace_id": "trace_000360", "parent_event_ids": [] }
}
```

**assistant_message** (intent — contains a tool request)
```json
{
  "type": "assistant_message", "actor": "luna", "source": "model_harness",
  "payload": {
    "text": "<tool_request>\ntool: read_event\nreason: current weather\nargs:\n  subtype: environment\n  last: true\n</tool_request>",
    "tool_request": { "tool": "read_event", "reason": "current weather", "args": { "subtype": "environment", "last": true } }
  }
}
```

**tool_call** (dispatcher dispatching a real tool)
```json
{
  "type": "tool_call", "actor": "luna", "source": "tool_dispatcher",
  "payload": { "tool": "read_event", "args": { "subtype": "environment", "last": true }, "reason": "current weather", "requires_permission": false }
}
```

**tool_result** (the receipt — note `status`, `result_summary`, `receipt_id`)
```json
{
  "type": "tool_result", "actor": "luna", "source": "tool_dispatcher",
  "payload": {
    "tool": "read_event", "status": "success",
    "result_summary": "read_event: 1 event(s) matched (subtype=environment, last=True, limit=20)",
    "started_at": "2026-07-08T08:01:00+12:00", "finished_at": "2026-07-08T08:01:00+12:00",
    "latency_ms": 3, "result_count": 1, "receipt_id": "sha256:..."
  }
}
```

**system_event** — variety lives in `payload.subtype`:

*heartbeat*
```json
{ "type": "system_event", "actor": "system", "source": "heartbeat",
  "payload": { "subtype": "heartbeat", "cpu_load": 12.3, "memory_used_pct": 62.1,
    "disk_free_gb": 191.2, "disk_total_gb": 460.4,
    "services": { "luna": "up", "whooshd": "up", "codexify": "unavailable" } } }
```

*environment*
```json
{ "type": "system_event", "actor": "system", "source": "environment",
  "payload": { "subtype": "environment", "local_time": "2026-07-08T08:01:00+12:00",
    "daylight": true, "sunrise": "2026-07-08T07:31:00+12:00", "sunset": "2026-07-08T17:21:00+12:00",
    "weather": { "temperature_2m": 10.6, "weather_code": 51, "wind_speed_10m": 12.6 },
    "presence": { "present": false, "confidence": 0.25 } } }
```

*phone_telemetry* (`observed_at` is the phone's observation time; `ts` is write time — they differ)
```json
{ "type": "system_event", "actor": "system", "source": "phone_tailer",
  "payload": { "subtype": "phone_telemetry", "battery": 42, "wifi": "RockyBayStars",
    "lat": -35.60, "lon": 174.53, "device": "iphone", "charging": true,
    "observed_at": "2026-07-08T07:55:00+00:00" } }
```

*segment_sealed* (midnight rotation — first event of a new day, carries the sealed segment's hash)
```json
{ "type": "system_event", "actor": "system", "source": "spine",
  "payload": { "subtype": "segment_sealed", "sealed_segment": "world-2026-07-07.jsonl",
    "sha256": "sha256:...", "sealed_event_count": 350, "sealed_date": "2026-07-07" } }
```

*continuity* (lightweight receipt when the model writes its continuity vector — a pointer, not the vector)
```json
{ "type": "system_event", "actor": "luna", "source": "write_continuity",
  "payload": { "subtype": "continuity", "file": "uis/continuity.jsonl",
    "line_count": 20, "sha256": "sha256:...", "previous_sha256": "sha256:...", "changed": true } }
```

**artifact_created**
```json
{ "type": "artifact_created", "actor": "luna", "source": "tool_dispatcher",
  "payload": { "tool": "create_artifact", "title": "Spine architecture notes",
    "file_path": "/Users/.../artifacts/2026-07-08_spine_notes.md",
    "bytes": 1240, "sha256": "sha256:...", "source_event_id": "evt_000345" } }
```

---

## 2. Tool use and the second model call

A turn is a **decide → act → interpret** loop, not a single call.

1. **Decide.** The harness sends the model its context (system messages + the user message). The model replies. If the reply contains a `<tool_request>…</tool_request>` block, the harness parses it.
2. **Act.** The harness dispatches the tool (`tool_call`), the tool runs, and a `tool_result` is written. Tool results are *temporary working memory* — they exist for this turn.
3. **Interpret.** The harness calls the model a **second time**, with the tool result appended to the conversation, so the model can synthesize a final answer.
4. **Loop.** If the interpret reply *also* contains a tool request, the harness dispatches it and calls again — repeating until the model gives a plain answer, the model errors, or a turn cap is hit (`UIS_HARNESS_MAX_TOOL_TURNS`, default 6).

Spine trace for a one-tool turn:

```
user_message
  → tool_call(call_model)        decide
    → tool_result(call_model)
      → assistant_message        intent (has tool_request)
        → tool_call(read_event)  act
          → tool_result(read_event)
            → tool_call(call_model, phase=interpret)   interpret
              → tool_result(call_model, interpret)
                → assistant_message(phase=interpret)   synthesis — what the user sees
```

The first call is `phase: "initial"`; every following call is `phase: "interpret"`. Each model call and each tool dispatch is its own event on the spine, so the whole loop is replayable.

---

## 3. System events

`system_event` is how the system records reality between user messages — the things that happen while nobody is typing. Variety is in `payload.subtype`. Today, on the single node `mac_studio`:

- **heartbeat** — cpu/memory/disk + service health, every 5 min.
- **environment** — local time, daylight, weather, presence, every 5 min.
- **phone_telemetry** — battery/wifi/GPS, pushed on receipt from the phone.
- **email_received / imessage_received** — stubs (manual injection only, no live watchers yet).
- **segment_sealed** — the rotation's own marker, written by the spine at midnight.
- **continuity** — a receipt when the model rewrites its continuity vector.

All observers push through one dispatcher facade (`uis.dispatcher.dispatch_system_event`); only `_append_event` writes the file. No observer touches the spine directly.

### Multi-node expansion

Every event already carries `node` and `source`. The step from one node to many is mostly routing, not redesign:

- Each node runs its own spine and its own observers. A `node` field on every event disambiguates origin — `mac_studio`, `bruce`, `phone`, a remote node.
- Nodes exchange `system_event`s as the shared sensor layer: a heartbeat from `bruce`, phone telemetry from `phone`, an environment snapshot from a remote node. Each node's dispatcher can accept pushed events from peers (over a authenticated channel) and append them with the peer's `node`/`source`.
- The append-only, hash-chained spine (and the sealed-segment sha256 chain) becomes the shared ledger two nodes can reconcile. Conflicts are resolved by `seq` order under a single-writer-per-node rule; cross-node merges preserve the `node` tag so provenance is never lost.

The boundary today is "one writer per spine." The expansion path is "one writer per node, plus a peer-push ingest" — the event schema and the reducer already don't assume a single node.

---

## 4. Continuity — derived from the stream, updated by the model

Continuity is Luna's self-managed memory: a ~20-line vector of status-tagged threads (`active`, `resolved`, `watching`, `new`, `stale`, `standing`) that the model carries turn to turn. This is the "Luna way" — the model decides what's worth remembering, not the harness.

**Two stores, one per concern:**

- `world.jsonl` records *that* a continuity write happened — a lightweight `system_event` `subtype:"continuity"` receipt (file + hash + line_count, **not** the vector). Queryable with `read_event`.
- `continuity.jsonl` records *what* the vector was — an append-only, hash-chained log. Each entry:
  ```json
  { "ts": "...", "triggered_by": "evt_000345", "vector": ["- [active] ...", "- [standing] ..."],
    "hash": "sha256:...", "prev_hash": "sha256:...", "line_count": 20 }
  ```
  `vector` is an array of strings (diffable line by line). `prev_hash` chains each entry to the previous one; genesis is `null`. Old versions persist forever — for diffing, auditing, or rollback.

**How it flows:**

1. The model calls the `write_continuity` tool with the **whole** vector (never a single line — content is wholesale-replace, storage is append-only). The tool validates (≤20 lines, ≤200 chars/line, valid status tags), skips if the vector is byte-identical to the latest entry ("no change"), else appends a new chained entry to `continuity.jsonl` and emits the `continuity` receipt on the spine.
2. The **reducer** reads the *latest* `continuity.jsonl` entry and the harness injects its vector into context on the next turn.
3. The model sees its own current vector, decides what changed, and rewrites — closing resolved threads, opening new ones, shifting directions, keeping standing constraints. Each rewrite is a new entry; the old one is not lost.

History is queryable: `python -m uis.tools.read_continuity --since … --last N` answers "what did continuity look like last Tuesday?"

---

## 5. The reducer

The reducer is the read-side projection. It never writes the spine; it reads and projects.

`reducer.project(spine_path)` does one forward pass over all spine segments (sealed + live, in chronological order) and returns a dict of the *last* values — because the spine is append-only and `seq`-ordered, the last occurrence of each thing is the current state:

- `last_user`, `last_assistant` — most recent user/assistant text.
- `last_trace_id`, `event_count`.
- `last_tool`, `last_tool_summary`, `last_tool_event_id` — the most recent *dispatcher-level* `tool_result` (excludes the harness's own `call_model` bookkeeping), so the model knows what its tools actually did even after the assistant slot has moved on.
- `last_assistant_event_id`, plus a "meaningful" assistant pointer (excluding the interpret-phase synthesis) for "this"-pointer resolution.

`reducer.get_continuity(spine_path)` reads the latest `continuity.jsonl` entry's vector and returns it as a joined block. (DEBT: a thin reader for now; `project()` can absorb it later without changing the harness call site.)

The harness calls `project()` at the top of every turn, *before* assembling context, so the model always sees fresh state — never a stale file read. The projection is carried forward into the next turn's STATE block.

---

## 6. What the model sees in context

Each turn the harness assembles a `messages` array. The order is fixed; the sections are:

1. **System — identity.** Who the model is, the rules of the house, the tools available at a glance. (One short block; the model's persona and constraints.)
2. **System — tool schemas.** Auto-generated from the tool registry: each tool's name, when to use it, and the exact `<tool_request>` block format. This is how the model knows the syntax for invoking a tool.
3. **System — state recap (from the reducer).** The projected last-values, one line each:
   ```
   last_user: "whats the weather?"
   last_assistant: "It's 10.6°C, light drizzle, wind 12.6 km/h. It's dark out."
   last_trace_id: "trace_000360"
   event_count: 362
   last_tool: "read_event"
   last_tool_summary: "read_event: 1 event(s) matched (subtype=environment...)"
   last_tool_event_id: "evt_000358"
   last_assistant_event_id: "evt_000361"
   ```
4. **System — continuity vector (from `reducer.get_continuity`).** The model's own current threads, exactly as it last wrote them:
   ```
   - [active] Spine architecture: live, tools proven, stability window in progress
   - [active] Taverna: working since July 1, primary income floor
   - [watching] Driftmesh commercial wedge: curator contacts still a gap
   - [resolved] Rebekka: platonic closure, arc complete
   - [standing] Spine rule: if it isn't in the log, it didn't happen
   …
   ```
5. **User — the message.** What the user typed this turn.

On an interpret (second) call, the conversation so far is appended: the assistant's intent, then the tool result as a user-role message, then the model is called again. The system sections stay the same.

The model reads all of this, decides whether to answer directly or invoke a tool, and either way its reply and any tool calls land back on the spine — becoming the next turn's `last_*` state.
