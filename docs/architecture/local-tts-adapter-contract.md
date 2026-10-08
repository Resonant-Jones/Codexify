# Local TTS Adapter Contract

## Purpose

Define Codexify's canonical provider-neutral text-to-speech adapter surface. This contract
keeps TTS backend selection separate from LLM provider/model routing while
allowing both normal runtime voice synthesis and headless voiceover generation
to use the same configured backend. The current executable implementation remains
local-only; this contract normalization implements no remote provider.

## Current Posture

Codexify is local-first. `CODEXIFY_TTS_BACKEND=qwen3_tts` is the default local
TTS backend id in the adapter layer. Qwen3-TTS is preferred only when the local
runtime is installed, importable, and pointed at local model files.

If Qwen3-TTS is unavailable, the adapter fails explicitly with setup guidance.
It must not silently fall back to cloud TTS or to the mock sine-wave provider.

TTS / voice execution remains **Out of Beta** under ADR-069. Backend metadata,
configuration, authorization, health evidence, successful synthesis, and
release support are independent facts. Nothing in this task promotes support.

## Backend Islands

TTS engines are backend islands, not Ollama-style interchangeable chat models.
Each backend can have different model layout, voice controls, sample handling,
startup cost, and inference API shape. Codexify owns the adapter contract in
front of those backend islands:

- backend id, for example `qwen3_tts`
- display name, for example `Qwen3-TTS`
- local-only flag (`true` for a local adapter, `false` for a remote adapter)
- supported output formats
- declared capabilities (`voice_sample_path` currently describes local sample-path input)
- health probe
- render request/result shape
- voice id or preset
- optional local voice sample path
- output format
- setup failure reason

## Canonical Execution Seam

`guardian/tts/contracts.py` owns one `TTSRenderRequest` / `TTSRenderResult`
vocabulary. `guardian/tts/backends/base.py::TTSBackend` is the adapter interface.
`guardian/tts/backends/__init__.py` owns the executable factory registry and
`resolve_tts_backend(...)`, keyed by canonical backend id. Only `qwen3_tts` is
registered in production. Unknown ids fail explicitly without fallback.

`render_voiceover(...)` resolves the selected adapter through this registry;
adding an adapter requires implementing it and adding its factory registration,
not provider-name branches in renderer control flow. The base `render_many(...)`
renders in order via `render(...)`; Qwen retains its optimized batch override.
Adapters must return one result per request in order. Voiceover assembly consumes
WAV chunks and optionally exports MP3 locally; adapter output formats describe
native outputs, not ffmpeg export availability.

The older `tts_service.TTSProvider` / `tts_manager.TTSManager` subsystem predates
this seam. It remains used by legacy media-backed synthesis services; its Qwen
wrapper delegates to `Qwen3TTSBackend`. It does not resolve headless or profile
preview execution and is not a registration authority for this renderer.
Retirement/consolidation is deferred; legacy provider presence enables no new
adapter here.

Existing persisted profiles need no migration. Profile writes retain the
existing local-id allowlist, aligned with the database backend-id CHECK
constraint. Catalog metadata can describe a registered remote adapter without
granting profile persistence. A later remote-provider slice must explicitly
update profile validation and migrate that constraint before persisting remote
profiles; those schema files are outside this normalization task.

The `LocalTTSConfig` / `get_local_tts_config` names remain for compatibility.
They carry current operator-local configuration and Qwen-specific settings,
not remote credentials or egress authority.

## Health Evidence

`TTSHealthProbe` keeps existing Qwen fields and serialized tokens intact. Local
`installed`, `model_files_available`, and `importable` evidence is optional;
a remote adapter leaves these fields `null`, rather than claiming local
installation or model files. `healthy` is also nullable: `null` means
unestablished/not applicable, `false` means explicitly negative evidence.

Independent optional boolean evidence fields are:

- `configured`: adapter configuration has been established;
- `credential_available`: operator-local credential availability only, never its value;
- `egress_allowed`: applicable authority has explicitly allowed egress;
- `reachable`: only established by an actual bounded probe;
- `synthesis_proven`: only established by an actual synthesis attempt (true on success).

All default to `null`. Configuration or credential presence must not imply
authorization, reachability, synthesis success, or release support. A future
remote adapter may report configuration evidence while status is `unknown`;
this new TTS-domain token means no overall health conclusion was established.
It is observational, not a lifecycle transition or permission. Health probes
must not synthesize audio as a side effect. Render results retain their own
per-attempt success/failure evidence; health need not cache past renders.

Qwen continues to report detailed local install/model/import checks, failure
reasons, setup guidance, and local diagnostic details unchanged. Its `healthy`
status proves readiness checks, not successful synthesis.

The existing adapter status tokens remain:

- `installed`
- `model_files_available`
- `importable`
- `healthy`
- `render_succeeded`
- `render_failed`
- `backend_unavailable`

These are TTS-domain tokens in `guardian/tts/contracts.py`. They are bounded to
the TTS adapter and do not replace provider runtime states used by chat.

## Qwen3-TTS Setup Assumptions

The Qwen3 adapter never downloads weights and never executes remote code. A
local operator must provide the runtime and model files.

Recommended local configuration:

```env
CODEXIFY_TTS_BACKEND=qwen3_tts
CODEXIFY_TTS_PROVIDER=qwen3_tts
CODEXIFY_TTS_LOCAL_ONLY=true
CODEXIFY_TTS_QWEN3_MODEL_PATH=/absolute/path/to/qwen3-tts-model
CODEXIFY_TTS_QWEN3_PYTHON=/absolute/path/to/python
CODEXIFY_TTS_QWEN3_RENDER_SCRIPT=/absolute/path/to/local_qwen3_renderer.py
CODEXIFY_TTS_OUTPUT_DIR=storage/tts
CODEXIFY_TTS_DEFAULT_VOICE=default
```

The render script, when used, must be a local operator-owned script accepting:

```bash
--input <text-file> --output <wav-file> --model-path <model-dir> --voice <voice>
```

If no render script is configured, the adapter attempts importable local module
entrypoints such as `qwen3_tts.synthesize_to_file(...)`. This path is strictly
local and fails closed when no compatible module is importable.

## Headless Voiceover Rendering

`scripts/tts/render_voiceover.py` renders standalone voiceover files without
going through chat completion, retrieval, memory, persona execution, or thread
state.

Example:

```bash
python scripts/tts/render_voiceover.py \
  --input /tmp/god-is-a-computer-voiceover.txt \
  --output /tmp/god-is-a-computer.mp3 \
  --backend qwen3_tts \
  --voice default
```

The renderer parses `[pause]` as a long pause and `...` as a short breath pause,
splits long text into safe chunks, renders speech chunks locally, stitches the
chunks with silence, and writes the final output locally.

Dry run:

```bash
python scripts/tts/render_voiceover.py \
  --input /tmp/voiceover.txt \
  --output /tmp/codexify-tts-dry-run.wav \
  --backend qwen3_tts \
  --dry-run
```

Dry-run mode prints the deterministic render plan and does not generate audio.

## MP3 Export

WAV is the minimum local output format. MP3 export requires local `ffmpeg`.
Missing `ffmpeg` should not invalidate the TTS adapter when WAV rendering works;
it should return an MP3 export error with a local dependency hint.

## Runtime Route

`POST /api/tts/render` is a narrow authenticated local route that reuses the
headless renderer. It returns artifact metadata or dry-run plan data and does
not persist a chat message, write memory, run retrieval, invoke persona, or
alter thread state.

Existing media-backed TTS routes remain in place for DB-linked media assets.
Existing `tts_outputs` and `message_audio_assets` tables are preserved.

## TTS Console And Voice Profiles

The TTS Console is the only voice-profile editing surface. Codexify may expose
a launcher inside the main shell, and the main runtime may select saved profile
ids, but chat, Dashboard, Documents, Guardian, and Persona Studio must not grow
inline voice tuning controls.

Persistent profile state lives in `tts_voice_profiles` and is consumed through
the TTS adapter. The profile contract includes:

- stable profile id and name
- backend id
- unique default flag
- voice mode, speaker, voice prompt, style instructions, and language
- Codexify delivery controls such as speed
- generation controls such as temperature, top-k, top-p, repetition penalty,
  max-new-tokens, and sampling flag
- `backend_params` for backend-specific controls
- optional future-safe reference audio/text, sample-rate, output-format,
  loudness, and pause-profile fields

`guardian/tts/profiles.py::resolve_tts_profile(...)` resolves a named or
default profile without running synthesis. Resolution must not mutate chat,
memory, retrieval, persona, thread, queue, command bus, or LLM provider state.

The TTS profile routes are:

- `GET /api/tts/backends`
- `GET /api/tts/profiles`
- `POST /api/tts/profiles`
- `GET /api/tts/profiles/{profile_id}`
- `PATCH /api/tts/profiles/{profile_id}`
- `DELETE /api/tts/profiles/{profile_id}`
- `POST /api/tts/profiles/{profile_id}/set-default`
- `POST /api/tts/profiles/{profile_id}/preview`

Preview uses the existing local renderer and writes local preview artifacts
under the configured TTS output directory. It does not create chat messages,
write memory, run retrieval, execute persona, alter thread state, enqueue work,
or touch LLM provider routing.

## Backend-Specific Controls

Backends expose controls through a backend-aware schema. Qwen3-TTS currently
advertises common controls for `speaker`, `voice_prompt`,
`style_instructions`, `language`, `speed`, `temperature`, `top_k`, `top_p`,
`repetition_penalty`, `max_new_tokens`, and `do_sample`.

Qwen3 conditional controls include `subtalker_dosample`, `subtalker_top_k`,
`subtalker_top_p`, `subtalker_temperature`, `x_vector_only_mode`,
`reference_audio`, `reference_text`, and `non_streaming_mode`.

`speed` is persisted as a Codexify delivery/post-processing control. It is not
advertised as a native Qwen3 generation parameter unless the active backend
explicitly exposes native speed support. Qwen3-specific controls that do not
belong in the shared profile shape remain in `backend_params`.

## Persona Studio Relationship

Persona Studio may configure voice settings, but it is a configuration surface.
It is not chat history, not memory, and not a voiceover execution pipeline. This
adapter gives Persona Studio and runtime voice paths a backend id to point at;
it does not make Persona Studio persist audio or execute conversation turns.

Persona Studio can consume saved profile ids later, but profile editing belongs
to the TTS Console. This keeps persona identity/configuration separate from TTS
backend tuning.

## Privacy Constraints

- No cloud TTS is introduced.
- No voice sample upload is introduced.
- Generated audio stays local.
- Model caches, generated audio, and private voice samples must stay out of git.
- Current backend availability checks are local inspectability checks.
- Profile rows, frontend state, logs, and artifacts must never contain provider
  credentials; health exposes only credential availability.
- A future remote adapter must use existing Codexify egress authority and
  operator-local credentials, with explicit selection and no silent fallback.
  This contract grants no network authority and makes no remote call.
- Deepgram is not implemented or registered by this normalization task.

## Deferred

- End-to-end voice UX release support.
- A generalized TTS backend marketplace.
- Cloud TTS support.
- Automatic Qwen3-TTS install or model download.
- Detached OS/browser plugin-window support beyond the modal-style console.
- Additional storage tables beyond `tts_voice_profiles`.
- Release claims for end-to-end voice UX.

## ADR Impact

Classification: aligned with existing ADRs / no new ADR expected.

Aligned with ADR-062 capability/evidence distinctions (still Proposed),
ADR-069 release boundaries, and ADR-082 authored configuration vs binding
authority. No new ADR is needed for this normalization; new credential
ownership, general egress authority, release support, or cross-provider routing
semantics require a separate decision before implementation.

The change follows the existing local-first provider posture, config/ops
boundary, Persona Studio isolation rules, and canonical token discipline. It
adds a bounded TTS-domain token registry rather than changing the chat runtime
provider state machine.

## Validation Commands

```bash
python -m pytest -q tests/tts
python -m pytest -q tests/routes/test_tts_profiles_routes.py
pnpm test
python scripts/tts/render_voiceover.py --help
python scripts/tts/render_voiceover.py \
  --input /tmp/codexify-tts-small.txt \
  --output /tmp/codexify-tts-dry-run.wav \
  --backend qwen3_tts \
  --dry-run
git diff --check
```

If route or config code changed:

```bash
python -m pytest -q tests/routes tests/core
```
