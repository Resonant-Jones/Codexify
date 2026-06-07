# Local TTS Adapter Contract

## Purpose

Define Codexify's canonical local text-to-speech adapter surface. This contract
keeps TTS backend selection separate from LLM provider/model routing while
allowing both normal runtime voice synthesis and headless voiceover generation
to use the same configured local backend.

## Current Posture

Codexify is local-first. `CODEXIFY_TTS_BACKEND=qwen3_tts` is the default local
TTS backend id in the adapter layer. Qwen3-TTS is preferred only when the local
runtime is installed, importable, and pointed at local model files.

If Qwen3-TTS is unavailable, the adapter fails explicitly with setup guidance.
It must not silently fall back to cloud TTS or to the mock sine-wave provider.

## Backend Islands

TTS engines are backend islands, not Ollama-style interchangeable chat models.
Each backend can have different model layout, voice controls, sample handling,
startup cost, and inference API shape. Codexify owns the adapter contract in
front of those backend islands:

- backend id, for example `qwen3_tts`
- display name, for example `Qwen3-TTS`
- local-only flag
- health probe
- render request/result shape
- voice id or preset
- optional local voice sample path
- output format
- setup failure reason

## Health States

The adapter distinguishes:

- `installed`
- `model_files_available`
- `importable`
- `healthy`
- `render_succeeded`
- `render_failed`
- `backend_unavailable`

These are TTS-domain tokens in `guardian/tts/contracts.py`. They are bounded to
the local TTS adapter and do not replace provider runtime states used by chat.

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

## Persona Studio Relationship

Persona Studio may configure voice settings, but it is a configuration surface.
It is not chat history, not memory, and not a voiceover execution pipeline. This
adapter gives Persona Studio and runtime voice paths a backend id to point at;
it does not make Persona Studio persist audio or execute conversation turns.

## Privacy Constraints

- No cloud TTS is introduced.
- No voice sample upload is introduced.
- Generated audio stays local.
- Model caches, generated audio, and private voice samples must stay out of git.
- Backend availability checks are local inspectability checks, not network
  discovery.

## Deferred

- End-to-end voice UX release support.
- A generalized TTS backend marketplace.
- Cloud TTS support.
- Automatic Qwen3-TTS install or model download.
- New storage tables or release claims.

## ADR Impact

Classification: aligned with existing ADRs / no new ADR expected.

The change follows the existing local-first provider posture, config/ops
boundary, Persona Studio isolation rules, and canonical token discipline. It
adds a bounded TTS-domain token registry rather than changing the chat runtime
provider state machine.

## Validation Commands

```bash
python -m pytest -q tests/tts
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
