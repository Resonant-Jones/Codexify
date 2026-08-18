# Tester Local-Model Authority Reconciliation Proof

**Date:** 2026-08-18
**Branch:** `codex/repair-tester-whooshd-model-resolution`
**Worktree:** `/Volumes/Dev_SSD/Codexify-main`
**Trigger task:** diagnostic packet establishing canonical local-model identity for the
Tester before any configuration or Whoosh'd mutation
**Verdict:** `GO_GEMMA_CANONICAL`
**Workflow:** architecture-impact / proof
**ADR impact:** none (no ADR mutation in this task); recommended ADR posture for the
next task is **explicit architecture-level supersession of ADR-052** if the operator
intends the Tester to canonically serve Qwen, or **runtime reconciliation toward
ADR-052's Gemma topology** otherwise.

---

## 1. Repository identity

| Item | Value |
| --- | --- |
| Branch | `codex/repair-tester-whooshd-model-resolution` |
| HEAD | `ceac02d1654f0e967e15652810595bd299396fb2` ("Restore tester provider health transport") |
| Parent of HEAD | `c3cc44ecbb7800e7216cd2f76bed9a39f0b2712b` (Anthropic work — preserved unchanged) |
| Tracked working tree | clean (no untracked, no unstaged) |
| Transport-fix ancestry | `git merge-base --is-ancestor ceac02d1654f0e967e15652810595bd299396fb2 HEAD` → **PASS** (HEAD equals the named commit) |
| Source identity for the four authorized-file edits from the prior task | byte-equivalent in the Tester root bind-mount and the worktree commit (verified by `git diff` line shift only; content identical) |

No branch switch was required. No merge, rebase, cherry-pick, or fetch into this task
was performed. No runtime or configuration mutation occurred.

---

## 2. Accepted architecture — ADR-052

### 2.1 Resolution

Resolved from the current ADR index (`docs/architecture/adr/adr-index.md`, line 83, and
the curated ADR-Graph entry at line 146–147):

- **ADR number:** 052
- **Filename:** `docs/architecture/adr/ADR-052-whooshd-deepseek-dual-provider-startup-profile.md`
- **Status:** *Accepted for operator-controlled load observation; not a change to the default beta release promise.*
- **Title:** Whoosh'd Gemma and Approved DeepSeek Startup Profile

### 2.2 Decision text (verbatim, ADR-052 §Decision)

> Add `v1-whooshd-deepseek-web` as a named Compose startup profile. It keeps Whoosh'd's
> loopback **Gemma 12B IT QAT** inventory as the only local model, keeps `local` as the
> primary provider, and admits only DeepSeek through `CODEXIFY_EGRESS_ALLOWLIST=deepseek`
> with `deepseek-v4-flash` as its pinned cloud model.

### 2.3 Model/topology meaning

- ADR-052 establishes **Gemma 12B IT QAT** as architectural policy for the
  `v1-whooshd-deepseek-web` supported profile (not merely an evidence observation).
- The "only local model" wording is restrictive: the supported profile is not
  permitted to expose a second local model alongside Gemma.
- DeepSeek `deepseek-v4-flash` is the bounded cloud lane — separate from the
  Gemma lane and thread-selected.

### 2.4 Supersession status

- The ADR index Reading Order lists **no later ADR that explicitly supersedes or
  amends the Gemma model decision in ADR-052.** The ADR-052 entry carries no
  "superseded by" annotation.
- A second physical file `docs/architecture/adr/ADR-051-whooshd-deepseek-dual-provider-startup-profile.md`
  exists with **byte-identical ADR text** to ADR-052 (numbering duplicate, same
  decision body). It is **not listed** in the ADR index Reading Order and
  carries no governance claim. It is a stale duplicate (likely a renumbering
  artifact) and is **not authoritative**. This matches the
  `codexify-architecture-packet-baseline` skill's "ADR-renumber
  reconciliation" pattern — when the canonical index says 052, the 051 file is
  not authoritative architecture.

### 2.5 Convergent accepted sources (all say Gemma)

Every accepted-architecture and operator-document surface inspected agrees with
ADR-052's Gemma decision:

| Source | Class | Statement |
| --- | --- | --- |
| `docs/architecture/adr/ADR-052-whooshd-deepseek-dual-provider-startup-profile.md` (verbatim) | `accepted_architecture` | "loopback Gemma 12B IT QAT inventory as the only local model" |
| `docs/architecture/00-current-state.md` (line 150) | `accepted_architecture` | "A committed live strict-structured qualification receipt exists for the exact `gemma-4-12b-it-qat-4bit` Whoosh'd target" |
| `docs/architecture/00-current-state.md` (line 163) | `accepted_architecture` | "Do not assume DeepSeek tool-turn tests or the Whoosh'd **Gemma** qualification establish supported-provider execution..." |
| `docs/architecture/config-and-ops.md` (lines 322–325) | `accepted_architecture` | "`v1-whooshd-deepseek-web` ... selects the `whooshd-mlx` runtime preset and `gemma-4-12b-it-qat-4bit`" |
| `docs/Ops/friends-family-tester-runtime.md` (line 10) | `operator_documentation` | "Its supported runtime profile is the permanent dual-provider profile from ADR-052: local **Whoosh'd/Gemma** is the global default..." |
| `docs/Ops/friends-family-tester-runtime.md` (line 36) | `operator_documentation` | "Default chat provider ... **Whoosh'd Gemma (`gemma-4-12b-it-qat-4bit`)**" |
| `docs/Ops/friends-family-tester-runtime.md` (line 39) | `operator_documentation` | "The Tester keeps `LLM_PROVIDER=local` and the **Whoosh'd Gemma model** as the global default" |
| `config/supported_profiles/v1-whooshd-deepseek-web.yaml` (line 97) | `runtime_configuration` | `LOCAL_CHAT_MODEL: gemma-4-12b-it-qat-4bit` |
| `scripts/whooshd_deepseek_profile_up.sh` (line 17, line 148, line 155) | `runtime_configuration` | asserts the exclusive local inventory is `[gemma-4-12b-it-qat-4bit]`; fails if the live catalog doesn't match |
| `docker-compose.whooshd-deepseek.yml` (lines 17–25) | `runtime_configuration` | hardcodes 6 model keys = `gemma-4-12b-it-qat-4bit` |
| `.env.tester` (line 15) | `operator_configuration` | `LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit` |
| `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` | `operator_documentation` (operator-owned registry) | declares `gemma-4-12b-it-qat-4bit` as `priority: guest_chat, enabled: true` with `path: /Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit` |

**No accepted-architecture, accepted-current-truth, supported-profile, operator-runbook,
or operator-registry source establishes Qwen as the canonical Tester model.**

---

## 3. Repository-wide Qwen evidence classification

Every Qwen occurrence in `docs/` and in the three tracked Tester runtime files
was classified:

| Location | Class | Notes |
| --- | --- | --- |
| `docs/release/run/2026-03-17-beta-smoke-supported-profile-proof.md` (lines 113–115, 205) | `proof_only` / `historical` | 2026-03-17 beta-smoke proof; pre-dates the Tester supported profile. Not accepted architecture. |
| `docs/release/run/2026-03-18-supported-profile-proof.md` (lines 61, 128, 134, 186, 408) | `proof_only` / `historical` | 2026-03-18 supported-profile proof; pre-dates `v1-whooshd-deepseek-web`. |
| `docs/release/run/2026-03-11-beta-smoke.md` (line 37) | `proof_only` / `historical` | 2026-03-11 beta-smoke run against `100.109.4.57:11434` (an Ollama instance, not Whoosh'd). |
| `docs/release/run/branch-pr-absorption-audit.md` (line 137) | `proof_only` | Audit note about a PR title, not an architecture decision. |
| `docs/DEV_LOG/2026-06-14/Whoosh'd × Codexify Local Inference Signoff — 2026-06-14.md` (lines 30–34) | `proof_only` / `historical` | 2026-06-14 local-inference signoff; references `qwen2-vl-2b-mlx` (vision) and `qwen2.5-0.5b-gguf` (utility) — different model families, different surfaces. |
| `docs/Future-Features/TTS-PLAN.md` (lines 20, 70, 78, 94, 203) | `operator_documentation` (Future-Features) | **TTS surface**, not chat model. Mentions `qwen3_tts` and `qwen_local` TTS adapters. |
| `docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-rerun-after-trace-fix.md` (lines 28, 96) | `proof_only` / `historical` | 2026-05-08 Neo4j proof; uses `qwen3.5:0.8b` via Ollama. |
| `docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md` (line 6) | `proof_only` / `historical` | 2026-05-13 coding-result proof; uses `qwen3-coder:30b` via Ollama. |
| `docs/local-provider-whooshd-live-mismatch-proof-2026-06-15.md` (lines 88, 90) | `proof_only` / `historical` | 2026-06-15 historical local-provider mismatch proof. |
| `docs/specs/examples/persona-studio-voice-preview.example.json` (line 3) | `proof_only` (fixture) | TTS fixture; not a model decision. |
| `docs/specs/examples/persona-studio-voice-providers.example.json` (lines 5, 6, 46, 47, 77) | `proof_only` (fixture) | TTS fixture. |
| WBC proof commit chain (`a87f8c06e`, `a955fc90b`, `3c35fc85c`, `fa2905811`, `c1a736606`, `63842ee74`) referencing `qwen3.8-27b-4bit` | `proof_only` (latest WBC family) | "Repair canonical LLM health projection" (commit `c1a736606`) and "WBC supported Compose proof" commits; the most recent canonical artifact records `qwen3.8-27b-4bit` as a live Whoosh'd observation. **Not accepted architecture.** |

**No Qwen occurrence in any accepted-architecture, supported-profile, ADR, or
operator runbook establishes Qwen as the canonical Tester chat model.** Every
Qwen reference is either (a) historical/proof-only material from before the
Tester supported profile existed, (b) a different surface (TTS, vision, GGUF,
embedding), or (c) a live-runtime observation captured in a recent proof
commit family (WBC).

The live-runtime observations in the WBC family are the most temporally
recent Qwen evidence. They are **proof artifacts**, not accepted architecture
— per the decision method, proof artifacts rank below supported-profile,
operator documentation, and ADR-052 in the authority hierarchy.

---

## 4. History — Gemma introduction and Qwen absence

| Commit | Date | Surface | Action |
| --- | --- | --- | --- |
| `fa47b3ffa` ("feat: add Whooshd DeepSeek startup profile") | 2026-07-26 | `docker-compose.whooshd-deepseek.yml`, `config/supported_profiles/v1-whooshd-deepseek-web.yaml`, `scripts/whooshd_deepseek_profile_up.sh`, `ADR-052`, `guardian/core/ai_router.py` | **Introduced** `v1-whooshd-deepseek-web` with `gemma-4-12b-it-qat-4bit` as the exclusive local model. Single-commit atomic introduction of the entire Tester topology. |
| `d2559f3b6` / `f3e2d2d08` ("admin account observability, whooshd-deepseek profile, settings density") | adjacent to 2026-07-26 | same files | Hardened version of the same introduction (parallel branch + rebase). No model identity change. |

`git log -S'gemma-4-12b-it-qat-4bit' --diff-filter=A` on the three tracked
Tester runtime files returns only the introduction pair. No commit
**adds, removes, or changes** Gemma → Qwen in any of the three tracked
runtime files.

`git log -S'qwen3.8-27b-4bit'` on the same three files returns **zero
commits** — `qwen3.8-27b-4bit` never appears in the Compose overlay, the
supported profile, or the startup script. Its only repository-history
appearances are in the WBC proof family (commits listed in §3).

**Conclusion:** repository history shows the Tester was built atomically
around Gemma on 2026-07-26 and has not been changed at the model-identity
level since. Qwen entered repository material only as live-runtime
observations in WBC proof artifacts.

---

## 5. Configuration precedence and effective value

### 5.1 Tracked declarations (read-only)

| Key | `docker-compose.whooshd-deepseek.yml` | `config/supported_profiles/v1-whooshd-deepseek-web.yaml` | `scripts/whooshd_deepseek_profile_up.sh` | `.env.tester` |
| --- | --- | --- | --- | --- |
| `LOCAL_CHAT_MODEL` | L17: `gemma-4-12b-it-qat-4bit` | L97: `gemma-4-12b-it-qat-4bit` | L17: `EXPECTED_MODEL="gemma-4-12b-it-qat-4bit"` (asserts catalog match) | L15: `gemma-4-12b-it-qat-4bit` |
| `LOCAL_LLM_MODEL` | L18: `gemma-4-12b-it-qat-4bit` | — | — | — |
| `DEFAULT_LOCAL_MODEL` | L19: `gemma-4-12b-it-qat-4bit` | — | — | — |
| `LLM_MODEL` | L20: `gemma-4-12b-it-qat-4bit` | — | — | — |
| `LOCAL_VISION_MODEL` | L24: `gemma-4-12b-it-qat-4bit` | — | — | — |
| `LOCAL_GGUF_MODEL` | L25: `gemma-4-12b-it-qat-4bit` | — | — | — |

The Compose overlay hardcodes all six model keys. `.env.tester` declares only
`LOCAL_CHAT_MODEL`. The Compose literal is **runtime-authoritative** because
Compose literal values override `env_file` interpolation at container
startup (per the standard Compose interpolation rules).

### 5.2 Rendered effective value (sanitized, non-secret)

`docker compose ... config` rendered the model keys for the
`codexify_tester` project as:

```
DEFAULT_LOCAL_MODEL: gemma-4-12b-it-qat-4bit
LLM_MODEL:           gemma-4-12b-it-qat-4bit
LOCAL_CHAT_MODEL:    gemma-4-12b-it-qat-4bit
LOCAL_GGUF_MODEL:    gemma-4-12b-it-qat-4bit
LOCAL_LLM_MODEL:     gemma-4-12b-it-qat-4bit
LOCAL_VISION_MODEL:  gemma-4-12b-it-qat-4bit
```

All six resolved model keys = **`gemma-4-12b-it-qat-4bit`**. Configuration
precedence: Compose literal → `.env.tester` interpolation → supported
profile default. No tracked source supplies a Qwen value to any model key.

### 5.3 Related model aliases — does each affect the chat path?

| Key | Effective value | Chat-path participation |
| --- | --- | --- |
| `LOCAL_CHAT_MODEL` | `gemma-4-12b-it-qat-4bit` | **Yes — primary chat model resolved by `/api/health/llm`** (verified by the prior task's live payload: `details.model = "gemma-4-12b-it-qat-4bit"`, `model_resolution.source = "LOCAL_CHAT_MODEL"`, `model_resolution.failure_kind = "configured_model_not_advertised_by_whooshd"`). |
| `LOCAL_LLM_MODEL` | `gemma-4-12b-it-qat-4bit` | Likely (legacy alias for the chat model). Worth classifying in the next implementation packet; safe to treat as duplicate of `LOCAL_CHAT_MODEL` until proven otherwise. |
| `DEFAULT_LOCAL_MODEL` | `gemma-4-12b-it-qat-4bit` | Likely (default fallback when no explicit chat model is set). Safe to treat as duplicate until proven otherwise. |
| `LLM_MODEL` | `gemma-4-12b-it-qat-4bit` | Possibly (generic LLM key, may be honored by adapters). Safe to treat as duplicate until proven otherwise. |
| `LOCAL_VISION_MODEL` | `gemma-4-12b-it-qat-4bit` | No (vision surface; the Operator-owned model registry file already declares Gemma as multimodal-capable). Not on the chat path. |
| `LOCAL_GGUF_MODEL` | `gemma-4-12b-it-qat-4bit` | No (GGUF backend surface; Whoosh'd MLX path is currently active, GGUF is unused at runtime). Not on the chat path. |

**Truncation note:** the four "Likely / Possibly" rows above describe
runtime participation. The next implementation packet should confirm each
key's read site before any elimination of duplicates. This packet only
catalogs and does not change values.

### 5.4 `.env.tester` cannot repair the running configuration by itself

`.env.tester` declares only `LOCAL_CHAT_MODEL`. The Compose overlay declares
the same key as a literal value. Compose literal values **override** the
`env_file`-interpolated value at container startup. Therefore editing
`.env.tester` alone would not change the running container's model
configuration. Any later implementation packet that intends to change the
running model must edit the Compose overlay (or the supported profile, or
the launch script — the three declarations are coherent today and would
have to be edited in lockstep). This is one of the reasons a single
`Qwen` substitution across three files is not yet a harmless
configuration repair.

---

## 6. Live runtime truth (reconfirmed)

The Codexify Tester containers (`backend`, `frontend`, `db`, `neo4j`) were
observed to have exited 55 minutes prior to this proof (operator-attributable
state change; not a defect of this task). Per invariant #7, no restart was
attempted. Per the dual-checkout skill's "operator-attributable runtime state
changes are re-baselined" rule, the new container state is recorded and
treated as authoritative for this task.

The live runtime facts below are taken from the most recent successful
probes, captured during the prior task (`docs/architecture/proofs/...`
or the prior task closeout carried in this session) and re-confirmed
for this proof by the non-mutating direct Whoosh'd read in §7:

| Surface | Observed value | Source of evidence |
| --- | --- | --- |
| **Whoosh'd advertised model IDs** | exactly one model: `qwen3.8-27b-4bit` (display name "Qwen3.8 27B 4-bit MLX", engine `mlx_vlm`, format `mlx`, modalities `[text, vision]`, `model_lifecycle=unloaded`, `whooshd_version=0.1.0rc1`) | `GET http://127.0.0.1:8000/v1/models` (direct read, not via Codexify) — re-confirmed 2026-08-18 for this proof |
| **Guardian selected provider** | `local` (from `/health` `details.supported_profile.selected_provider`) | prior task live payload |
| **Guardian configured local model** | `gemma-4-12b-it-qat-4bit` (from `/api/health/llm` `details.model` and `model_resolution.source=LOCAL_CHAT_MODEL`) | prior task live payload |
| **Local provider state** | `available=true, authorized=true, enabled=false, disabled_reason="Configured local chat model 'gemma-4-12b-it-qat-4bit' from LOCAL_CHAT_MODEL is not advertised by the reachable local runtime"` | prior task live payload |
| **Model-resolution failure** | `failure_kind="configured_model_not_advertised_by_whooshd"`, `advertised_models=["qwen3.8-27b-4bit"]`, `inventory_source="whooshd:/v1/models"` | prior task live payload |
| **`/health/chat` state** | `ok=false, status="unhealthy"`, `redis="ok"`, `worker.status="fresh"`, `notes=["Configured local chat model 'gemma-4-12b-it-qat-4bit' from LOCAL_CHAT_MODEL is not advertised by the reachable local runtime", "queue empty"]` | prior task live payload |
| **Redis** | `ok` | prior task live payload |
| **Worker heartbeat** | `fresh`, `heartbeat_age_seconds≈2.5` | prior task live payload |
| **DeepSeek posture** | `provider=deepseek, enabled=true, available=true, authorized=true, model_count=1` (from `/api/llm/catalog`) | prior task live payload |
| **Supported profile** | `name=v1-whooshd-deepseek-web, version=1, valid=true, mismatches=[], selected_provider=local, expected_provider=local, supported_profile_approved=true` | prior task live payload |

The mismatch is **purely model-resolution**: every Guardian and Redis/worker
health surface is healthy, but the configured chat model (`gemma`) is not
advertised by Whoosh'd (which advertises `qwen3.8-27b-4bit`). DeepSeek is
fully healthy on the cloud lane and unaffected.

---

## 7. Whoosh'd serving authority — why Qwen is currently served

### 7.1 Direct non-mutating read of the live Whoosh'd runtime

`GET http://127.0.0.1:8000/v1/models` (sampled during this proof):

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen3.8-27b-4bit",
      "object": "model",
      "created": 1700000000,
      "owned_by": "whooshd",
      "metadata": {
        "engine": "mlx_vlm",
        "format": "mlx",
        "modalities": ["text", "vision"],
        "context_window": 65536,
        "display_name": "Qwen3.8 27B 4-bit MLX",
        "priority": "guest_chat",
        "warm_policy": "keep_warm",
        "runtime_provenance": {
          "schema_version": "whooshd.runtime.v1",
          "requested_model_id": "qwen3.8-27b-4bit",
          "advertised_model_id": "qwen3.8-27b-4bit",
          "resolved_model_id": "qwen3.8-27b-4bit",
          "runtime_kind": "mlx_vlm",
          "adapter_name": "mlx-vlm",
          "resolution_source": "authoritative_registry",
          "execution_mode": "managed_sidecar",
          "model_lifecycle": "unloaded",
          "whooshd_version": "0.1.0rc1"
        }
      }
    }
  ]
}
```

### 7.2 Whoosh'd process and operator-owned serving authority

Whoosh'd runs as a **system LaunchDaemon** (`com.resonant.whooshd`) on the
host, outside the Codexify repo and outside the Codexify Compose stack.
Non-secret environment for the LaunchDaemon (read-only inspection):

| Variable | Value | Source of authority |
| --- | --- | --- |
| `WHOOSHD_PORT` | `8000` | LaunchDaemon plist (host-level) |
| `WHOOSHD_HOST` | `127.0.0.1` | LaunchDaemon plist |
| `WHOOSHD_MLX_ENABLED` | `true` | LaunchDaemon plist |
| `WHOOSHD_MLX_VLM_ENABLED` | `true` | LaunchDaemon plist |
| `WHOOSHD_MLX_VLM_PORT` | `8082` | LaunchDaemon plist |
| `WHOOSHD_MLX_VLM_MODEL` | `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit` | LaunchDaemon plist — **this is the source of the Qwen advertisement** |
| `WHOOSHD_MODEL_REGISTRY_PATH` | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml` | LaunchDaemon plist — **operator-owned registry path** |
| `WHOOSHD_ROOT` | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` | LaunchDaemon plist |

The operator-owned registry at the registered path
(`/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd/configs/models.friends-family-guest.yaml`)
declares `gemma-4-12b-it-qat-4bit` as the canonical
`priority: guest_chat, enabled: true` model with the canonical path
`/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`.

The LaunchDaemon env var `WHOOSHD_MLX_VLM_MODEL` points at a different
directory (`/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`) and
takes precedence at Whoosh'd process start. This is the
**operator-side divergence**: the LaunchDaemon env was redirected from the
Gemma path to the Qwen path without a corresponding
accepted-architecture decision in the Codexify repo.

### 7.3 Classification of the Qwen serving state

Per the brief's classification:

- `explicitly configured` — **yes**, in the operator-side LaunchDaemon plist
  (`WHOOSHD_MLX_VLM_MODEL`). But this is **operator-side configuration**,
  not **Codexify-side accepted architecture**.
- `runtime auto-discovered` — no (the model directory was explicitly named).
- `inherited from another configuration source` — no (a single plist env
  var, no inheritance).
- `unknown` — no (the source is identified).

**The Qwen serving state is explicitly configured on the operator side
(Whoosh'd LaunchDaemon) and is in direct conflict with both the operator-owned
model registry file (which names Gemma) and all Codexify-side accepted
configuration (Compose overlay, supported profile, scripts, ADR-052, current-state,
operator runbook, config-and-ops).**

---

## 8. Authority conclusion

### 8.1 Verdict

**`GO_GEMMA_CANONICAL`**

### 8.2 Why this classification follows from the evidence

Per the brief's decision-method precedence:

1. **Later accepted ADR superseding ADR-052** — none. The ADR index lists no
   supersession; the second physical file at `ADR-051-…` is a byte-identical
   stale duplicate and is not in the Reading Order. **Not applicable.**
2. **Accepted current architecture contract explicitly changing the Tester model**
   — none. `00-current-state.md`, `config-and-ops.md`, and the operator runbook
   all say **Gemma** is canonical for the Tester. **Not applicable.**
3. **`00-current-state.md` explicitly resolving the model identity** — yes
   (line 150): "A committed live strict-structured qualification receipt exists
   for the exact `gemma-4-12b-it-qat-4bit` Whoosh'd target". **Gemma is named
   in the current-state document as the Tester's exact target.**
4. **ADR-052** — yes. "Loopback Gemma 12B IT QAT inventory as the only local
   model." **Gemma.**
5. **Supported profile / runtime configuration** — yes, in three tracked
   files. All declare Gemma. **Gemma.**
6. **Operator documentation** — yes, in `friends-family-tester-runtime.md`.
   **Gemma.**
7. **Proof artifacts** — the WBC proof family observes `qwen3.8-27b-4bit`
   in the live runtime. **Qwen, but proof-only — not accepted architecture.**
8. **Task / campaign material** — none mentions Qwen as canonical. **Not
   applicable.**
9. **Live runtime state** — Whoosh'd advertises Qwen; Guardian is configured
   for Gemma; the model-resolution failure disables the local provider.
   **Live state is Qwen, but the live state is not "what is supposed to run"
   by every accepted source.**

The first six precedence levels all name **Gemma**. Levels 7–9 name
**Qwen** but are explicitly subordinated by the decision method to the
accepted-architecture hierarchy.

**Therefore the canonical Tester local model is Gemma.**

### 8.3 What this means for the live Qwen state

The Qwen advertised by the live Whoosh'd runtime is **runtime drift from
accepted architecture**, not a transition. The drift originated in the
operator-side LaunchDaemon plist (a host-managed file outside the Codexify
repo) and was not accompanied by any of:
- A new ADR explicitly superseding ADR-052.
- A change to `00-current-state.md`.
- A change to `config-and-ops.md` or the operator runbook.
- A change to the Compose overlay, the supported profile, or the startup
  script.
- A change to the operator-owned model registry file
  (`models.friends-family-guest.yaml`, which still names Gemma).

The Qwen state is exactly the kind of "runtime state that did not pass
through the architecture decision process" that the brief's decision
method explicitly tells us to subordinate to accepted architecture.

### 8.4 Consequence for the next Task Spec

The next packet must execute **runtime reconciliation toward the accepted
Gemma topology** — not a "change Gemma to Qwen" configuration repair. The
required reconciliation surface is the operator-side Whoosh'd serving
configuration, not the Codexify repo:

- Update the operator-managed `com.resonant.whooshd` LaunchDaemon
  `WHOOSHD_MLX_VLM_MODEL` env var to point at the Gemma weight directory
  (e.g. `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`).
- Or, if the operator prefers a managed-sidecar approach, install
  `gemma-4-12b-it-qat-4bit` as a second MLX-VLM model entry in the
  operator-owned model registry file, and update the LaunchDaemon to
  select it.

The Codexify repo **does not need to change** to recover the canonical
state — it already says Gemma. The fix lives on the operator side.

If, instead, the operator intends the Tester to canonically serve Qwen,
then the next packet must be a **separate, explicit architecture-decision
packet** that:

1. Supersedes ADR-052 with a new ADR (e.g. ADR-068+) explicitly adopting
   `qwen3.8-27b-4bit` as the canonical Tester local model.
2. Updates `00-current-state.md` to declare Qwen as the exact Tester target.
3. Updates the Compose overlay, the supported profile, the startup
   script, and the operator runbook to name Qwen instead of Gemma.
4. Updates the operator-owned model registry file.
5. Re-runs the dual-provider startup proof.

Per the brief, this is the more expensive path and is **only justified if
the operator has decided that Qwen is the intended transition**. No such
decision exists in the current accepted architecture or in any
operator-owned documentation.

---

## 9. ADR impact

- **No ADR mutation in this task.** ADR-052 was read directly. No edits
  were made. The duplicate `ADR-051-…` file was inspected and classified
  as stale (not in the ADR index Reading Order); it was not modified.
- **Recommended ADR posture for the next task:** **none required, by
  default.** The default next task is runtime reconciliation toward Gemma
  (operator-side LaunchDaemon edit), which does not need an ADR change
  because ADR-052 already names Gemma.
- **Conditional ADR posture:** if the operator intends Qwen as the
  canonical Tester model, the next packet must author a new ADR that
  explicitly supersedes ADR-052's Gemma decision. This is a separate
  architecture-decision packet, not a runtime repair, and is **only
  justified by an explicit operator decision**.

---

## 10. Invariants check

1. Did not modify `.env.tester`. ✓
2. Did not modify Compose files. ✓
3. Did not modify the supported profile. ✓
4. Did not modify ADR-052. ✓
5. Did not create a new ADR. ✓
6. Did not restart Whoosh'd. ✓
7. Did not restart Guardian. ✓ (containers were already exited; not restarted.)
8. Did not pull, load, unload, or replace a model. ✓
9. Did not invoke DeepSeek. ✓
10. Did not submit a chat completion. ✓
11. Did not change provider routing. ✓
12. Did not change fallback behavior. ✓
13. Did not alter credentials. ✓
14. Did not print secret-bearing environment state. ✓ (only non-secret model/provider keys inspected.)
15. Did not infer architectural authority from live state alone. ✓ (the verdict is built on the accepted-architecture hierarchy; live state is recorded as evidence but is not the basis of the verdict.)
16. Did not infer architectural authority from a task prompt or proof artifact alone. ✓
17. Treated git history as explanatory, not as architecture supersession. ✓ (no commit merged after `fa47b3ffa` changed the Gemma identity in any tracked runtime file.)
18. Preserved Whoosh'd as one canonical local-provider identity. ✓
19. Preserved DeepSeek as the existing bounded cloud lane. ✓
20. Did not widen release claims. ✓

---

## 11. Validation results

- `git status --short --untracked-files=all` — clean (post-proof, only the
  new proof artifact is staged and committed).
- `git diff --check` — clean.
- `git diff --name-only` (pre-stage) — empty.
- No runtime or configuration file appears in the tracked diff.
- `docs/architecture/proofs/providers/` directory created implicitly by
  adding the new proof file; no other tracked file was created or modified.
- The proof is single-file, single-commit, single-purpose.

`scripts/validate_docs.py` and `make docs` were not run because no
`docs/architecture/adr/`, `docs/architecture/README.md`, or
`00-current-state.md` change was made. The proof lives in
`docs/architecture/proofs/providers/`, which the validators do not gate.

---

## 12. Files changed

| Path | Kind |
| --- | --- |
| `docs/architecture/proofs/providers/2026-08-18-tester-local-model-authority-reconciliation-proof.md` | added |

No other tracked file was created or modified. No untracked files were
left behind. No `.env.tester`, no Compose file, no supported profile, no
ADR, no Guardian source file, no script, no runbook was touched.

---

## 13. Git commit hash

Recorded at closeout. The commit is local-only; not pushed (per brief).

---

## 14. Next prerequisite

The next packet must reconcile the operator-side Whoosh'd LaunchDaemon
(`com.resonant.whooshd`) `WHOOSHD_MLX_VLM_MODEL` env var to the
`gemma-4-12b-it-qat-4bit` weight directory that the operator-owned model
registry file already names as canonical, then re-prove the
dual-provider startup; if the operator instead intends Qwen, a
separate architecture-decision packet must first supersede ADR-052.
