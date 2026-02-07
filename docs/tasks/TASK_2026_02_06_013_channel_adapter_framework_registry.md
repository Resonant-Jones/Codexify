# TASK-2026-02-06-013 — Channel Adapter Framework + Registry

**Goal:** Build the *foundation* for multi-channel messaging without committing to 40 integrations.

This task creates the minimal “channel adapter” spine: shared types, a registry, allowlist/pairing primitives, and a thin router that can accept inbound messages and emit outbound messages through registered adapters.

---

## Scope

### Deliverables

- `guardian/channels/base.py` — Adapter ABC + shared types (InboundMessage, OutboundMessage, AdapterContext, etc.)
- `guardian/channels/registry.py` — register/get adapters + minimal validation
- `guardian/channels/allowlist.py` — pairing codes + TTL + allowlist enforcement
- `guardian/channels/router.py` — incoming → thread resolution → completion → outgoing

### Security invariants

- Unknown senders are rejected **or** forced into pairing workflow (no silent accept).
- Pairing codes expire (TTL) and are single-use (or explicitly invalidated after use).
- Adapter registry is explicit (no dynamic imports from untrusted input).

### Out of scope

- Real Slack/Discord/Telegram adapters (Task 014)
- Persistent DB models for channels/messages (Task 015)
- WebSocket plumbing/events (other tasks)

---

## Allowed files (STRICT)

Only modify files in this allowlist:

- `guardian/channels/base.py`
- `guardian/channels/registry.py`
- `guardian/channels/allowlist.py`
- `guardian/channels/router.py`
- `guardian/channels/__init__.py`
- `guardian/tests/test_channel_allowlist.py` (create if missing)
- `guardian/tests/test_channel_router.py` (create if missing)
- This task artifact:
  - `docs/tasks/TASK_2026_02_06_013_channel_adapter_framework_registry.md`
- Campaign mapping file (only for Commit B mapping update):
  - `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`

If you discover required changes outside this list: **STOP** and write a short “Blocker” note in this artifact (do not change other files).

---

## Commit mode

Two-phase:

- **Commit A** = implementation + tests
- **Commit B** = docs finalize (task artifact results + campaign mapping)

---

## Dependencies / prereqs

Run these first (copy/paste):

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

python -V
pytest -V || true
```

If `pytest -V` fails, proceed **only** with local module-level validation + `python -m compileall guardian/channels` and record that pytest is unavailable.

---

## Command checklist (deterministic)

### 1) Locate existing patterns

```bash
rg -n "guardian/channels" guardian || true
rg -n "allowlist|pairing" guardian || true
rg -n "router\.include_router\(" guardian | head
```

**Expected:** `guardian/channels` exists (even if minimal), and no existing conflicting registry patterns.

### 2) Implement channel base + registry + allowlist

Edit only allowed files.

Implementation requirements:

- `base.py`
  - Define an `Adapter` ABC with:
    - `adapter_id: str` (stable identifier)
    - `send(outbound: OutboundMessage, ctx: AdapterContext) -> None` (or async, but keep consistent)
    - `parse_inbound(payload: dict, ctx: AdapterContext) -> InboundMessage` (optional if you prefer adapters to supply already-parsed messages)
  - Define minimal dataclasses / pydantic models for:
    - `InboundMessage` (channel_id, sender_id, text, timestamp?, raw)
    - `OutboundMessage` (channel_id, recipient_id, text, thread_id?, raw)
    - `AdapterContext` (request_id, user_id?, metadata)

- `registry.py`
  - Provide:
    - `register_adapter(adapter: Adapter) -> None` (reject duplicate ids)
    - `get_adapter(adapter_id: str) -> Adapter` (raise KeyError)
    - `list_adapters() -> list[str]`

- `allowlist.py`
  - Provide:
    - `is_allowed(sender_id: str, channel_id: str) -> bool`
    - `create_pairing_code(sender_id: str, channel_id: str, ttl_seconds: int = ...) -> str`
    - `redeem_pairing_code(code: str) -> tuple[str, str]` returning (sender_id, channel_id)
  - TTL enforced deterministically (store created_at + ttl; reject expired)
  - Redemption invalidates code (single-use)

### 3) Implement router (thin, minimal)

Edit only allowed files.

Router requirements (keep it boring):

- `router.py` exposes a single function:
  - `handle_inbound(adapter_id: str, inbound: InboundMessage, *, ctx: AdapterContext) -> dict`
- Flow:
  1) Resolve adapter via registry
  2) Enforce allowlist:
     - If not allowed and no valid pairing code flow is present → return a structured rejection result
  3) Minimal “thread resolution” placeholder:
     - For now, thread_id can be `None` or derived deterministically (e.g., `f"{adapter_id}:{channel_id}:{sender_id}"`)
  4) “Completion” placeholder:
     - For now, the router can return a response dict without calling real LLM/chat routes (that wiring belongs in a later task). Keep the interface ready.
  5) Emit outbound message via adapter `send` ONLY if allowed.

**Important:** Do not import or call large subsystems here (keep the router framework-only).

### 4) Add tests

Create tests if missing (allowed list includes them). Prefer pure unit tests without DB/network.

```bash
pytest -q guardian/tests/test_channel_allowlist.py -q || true
pytest -q guardian/tests/test_channel_router.py -q || true
```

Minimum test coverage:

- Allowlist:
  - code creation returns a string
  - redemption succeeds before expiry
  - redemption fails after expiry
  - redemption fails on second use
- Router:
  - rejects inbound when sender not allowed (no outbound sent)
  - allows inbound when sender is allowed (outbound send is invoked on mock adapter)
  - unknown adapter_id raises/returns deterministic error

If pytest is unavailable, run a minimal validation:

```bash
python -m compileall guardian/channels
python - <<'PY'
from guardian.channels.allowlist import create_pairing_code, redeem_pairing_code
code = create_pairing_code('s','c', ttl_seconds=60)
assert redeem_pairing_code(code) == ('s','c')
print('ok')
PY
```

### 5) Sanity check + status

```bash
git status --porcelain -uall
```

---

## Expected outputs (success signals)

- `guardian/channels/*.py` modules exist with clean imports (no side effects on import)
- Registry prevents duplicate adapter registration
- Allowlist pairing codes enforce TTL + single-use
- Router rejects unknown senders unless paired/allowed
- Tests pass (or deterministic non-pytest validation recorded)

---

## Rollback / cleanup

If something goes sideways:

```bash
# discard local changes in allowed implementation files
git restore -- guardian/channels guardian/tests/test_channel_allowlist.py guardian/tests/test_channel_router.py

# verify clean
git status --porcelain -uall
```

---

## Commit plan

### Commit A (implementation + tests)

**Commit message (exact):**

- `TASK-2026-02-06-013_channel_adapter_framework_registry: add channel adapter base + registry + allowlist + router`

Commands:

```bash
git status --porcelain -uall

git add \
  guardian/channels/base.py \
  guardian/channels/registry.py \
  guardian/channels/allowlist.py \
  guardian/channels/router.py \
  guardian/channels/__init__.py \
  guardian/tests/test_channel_allowlist.py \
  guardian/tests/test_channel_router.py

git commit --no-verify -m "TASK-2026-02-06-013_channel_adapter_framework_registry: add channel adapter base + registry + allowlist + router"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)

**Commit message (exact):**

- `TASK-2026-02-06-013_channel_adapter_framework_registry: docs finalize + mapping`

Commands:

```bash
# update this task artifact with commands run + outcomes, then update campaign mapping line

git add \
  docs/tasks/TASK_2026_02_06_013_channel_adapter_framework_registry.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-013_channel_adapter_framework_registry: docs finalize + mapping"

git log -1 --oneline
```

---

## Campaign mapping line

Update the campaign file mapping to the required format:

- `TASK-2026-02-06-013_channel_adapter_framework_registry -> [<commitA>, <commitB>]`

---

## Notes / Results (fill during execution)

### Commands run

- …

### Key outputs

- …

### Deviations

- …

### Final mapping

- `TASK-2026-02-06-013_channel_adapter_framework_registry -> [<commitA>, <commitB>]`

