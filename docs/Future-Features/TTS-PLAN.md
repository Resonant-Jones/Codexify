# Codexify Voice Interaction Plan (Turn-Based, Docker-Compatible, Distributable)

## Summary
Implement a dedicated voice pipeline with:
1. Turn-based STT → assistant inference → TTS in one synchronous API call.
2. Per-message audio attachment for instant replay (no regeneration).
3. Configurable cloud/local TTS providers via `.env`.
4. Docker-compatible “fat image” distribution flow with versioned model manifest.
5. Frontend voice controls (mic input + per-message play + auto-read toggle).

This plan is decision-complete and aligned to your selected constraints:
- Dedicated voice service architecture.
- Single distributable fat image strategy.
- Whisper `small.en`.
- Synchronous `/api/voice/turn`.
- Per-message play + auto-read toggle.
- Explicit message→audio link table.
- Fail-fast provider behavior.
- Cloud: ElevenLabs + Google full, MiniMax scaffold.
- Local adapters first: Qwen + LFM via OpenAI-compatible speech API.
- Docker compatibility prioritized over MLX-first runtime.

## Current State (Grounded Findings)
1. Backend TTS routes exist in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:438` and `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:506`.
2. Frontend currently has no TTS/STT UI wiring in TS/TSX files (no `/tts` route usage and no mic/speech controls in `frontend/src`).
3. Existing TTS providers are only `elevenlabs`, `google`, `local` in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/tts/providers/__init__.py:12`.
4. Current `local` provider is a mock tone generator in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/tts/providers/local_provider.py:18`.
5. No Whisper/STT route exists in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes`.
6. Compose currently has no `tts`/`voice` service in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml`.
7. `tts_outputs` table exists but is thread-level, not explicitly message-linked in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/models.py:625`.
8. Chat messages have no metadata/audio fields in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/models.py:127`.

## Public API and Interface Changes
1. Add backend endpoint `POST /api/voice/turn` (synchronous):
   - Input: audio file, thread_id, project_id, user_id, selected assistant/provider, voice options.
   - Output: transcript text, assistant text, message IDs, attached audio metadata.
2. Add backend endpoint `POST /api/voice/read`:
   - Input: `message_id` or `{thread_id, text}`, `provider`, `voice`.
   - Output: linked or newly-generated audio metadata.
3. Add backend endpoint `GET /api/voice/messages/{message_id}/audio`:
   - Output: cached attached audio list for that message.
4. Keep existing `/api/media/tts/synthesize` and `/api/media/tts/{tts_id}` for compatibility, but route new UI flows through `/api/voice/*`.
5. Extend chat message list payload to include optional `audio` attachment metadata for assistant messages.

## Data Model and Migration Plan
1. Add table `message_audio_assets`:
   - `id`, `message_id` (FK `chat_messages.id`), `tts_output_id` (FK `tts_outputs.id`), `provider`, `voice`, `text_hash`, `created_at`.
   - Unique constraint on `(message_id, provider, voice)`.
2. Add table `voice_inputs`:
   - `id`, `thread_id`, `user_id`, `src_url`, `mime_type`, `duration_ms`, `transcript_text`, `stt_provider`, `model`, `created_at`.
3. Optional extension to `tts_outputs`:
   - `status`, `error`, `sample_rate_hz`, `codec`, `checksum` (for integrity/debug).
4. Migration adds indexes:
   - `ix_message_audio_assets_message_id`
   - `ix_message_audio_assets_text_hash`
   - `ix_voice_inputs_thread_id`

## Voice Service Architecture
1. New dedicated container service: `voice-service`.
2. Responsibility split:
   - `voice-service`: STT + TTS execution and model/runtime concerns.
   - backend: orchestration, chat persistence, assistant inference orchestration, attachment persistence.
3. Voice service endpoints:
   - `POST /v1/stt/transcribe`
   - `POST /v1/tts/synthesize`
   - `GET /v1/tts/voices`
   - `GET /healthz`
4. Provider adapter contracts inside `voice-service`:
   - STT adapters: `whisper_local`.
   - TTS adapters: `qwen_local`, `lfm_local`, `elevenlabs`, `google`, `minimax` (scaffold).
5. Fail-fast behavior:
   - No implicit cross-provider fallback.
   - Return structured provider error with actionable diagnostics.

## Local and Cloud Runtime Profiles
1. Local profile:
   - STT: Whisper `small.en` in voice-service.
   - TTS: Qwen + LFM adapters via OpenAI-compatible speech API endpoints.
2. Cloud profile:
   - TTS: ElevenLabs and Google fully implemented.
   - MiniMax adapter scaffolded behind feature flag, explicit “not fully configured” response until enabled.
3. Mode switch:
   - `.env` selects profile and provider explicitly per request or global defaults.

## Configuration Design (`.env`)
1. Core voice switches:
   - `CODEXIFY_VOICE_ENABLED=true`
   - `CODEXIFY_VOICE_MODE=turn|text_read`
   - `CODEXIFY_VOICE_SERVICE_URL=http://voice-service:8090`
2. STT:
   - `CODEXIFY_STT_PROVIDER=whisper_local`
   - `CODEXIFY_STT_MODEL=whisper-small.en`
3. TTS default selection:
   - `CODEXIFY_TTS_PROVIDER=qwen_local|lfm_local|elevenlabs|google|minimax`
   - `CODEXIFY_TTS_DEFAULT_VOICE=<voice_id>`
4. Cloud credentials:
   - `ELEVENLABS_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS`
   - `MINIMAX_API_KEY` (feature-flagged scaffold)
5. Local model runtime target:
   - `CODEXIFY_LOCAL_TTS_API_BASE=<openai_compatible_url>`
   - `CODEXIFY_LOCAL_TTS_API_KEY=<key_or_local>`

## Versioned Model Manifest (Deterministic Build)
1. Add manifest file (versioned): `docker/voice/model-manifest.yaml`.
2. Manifest fields per model:
   - `provider`, `engine`, `model_id`, `revision`, `source_url_or_registry`, `sha256`, `target_path`, `enabled`.
3. Build script behavior:
   - Validates checksums.
   - Fails build on mismatch.
   - Emits manifest summary into image labels for auditability.

## Docker and Distribution Plan
1. Add `voice-service` image build path with baked local model artifacts from manifest.
2. Update compose:
   - Add `voice-service`.
   - Wire backend to `CODEXIFY_VOICE_SERVICE_URL`.
3. Distribution workflow:
   - Build: `docker compose build voice-service backend frontend`.
   - Export: `docker save <images> -o codexify-voice-bundle.tar`.
   - Compress: `gzip codexify-voice-bundle.tar`.
   - Import on target machine: `gunzip -c codexify-voice-bundle.tar.gz | docker load`.
   - Start: `docker compose up -d`.
4. Add explicit size expectations and disk requirements in docs to avoid surprises.

## Backend Orchestration Flow (`/api/voice/turn`)
1. Receive audio upload + routing params.
2. Call `voice-service /v1/stt/transcribe` (Whisper `small.en`).
3. Persist transcript as user chat message.
4. Run assistant inference synchronously using shared completion service logic.
5. Persist assistant message.
6. If `auto_read=true` or turn mode:
   - Call `voice-service /v1/tts/synthesize`.
   - Persist `tts_outputs`.
   - Link `chat_messages.id -> tts_outputs.id` via `message_audio_assets`.
7. Return:
   - `transcript`
   - `assistant_text`
   - `user_message_id`
   - `assistant_message_id`
   - `audio_attachment` (id + URL + provider + voice)

## Read-Aloud (Text Mode) Plan
1. Add per-assistant-message play button in chat bubble.
2. Add header/settings toggle `Auto-read assistant messages`.
3. On assistant message create:
   - If auto-read enabled, backend generates and links audio once.
4. Replay behavior:
   - If attachment exists, play instantly from stored URL.
   - If missing and manual play is clicked, synthesize once then cache/link.

## Frontend Plan
1. Composer:
   - Add mic button for turn-based recording and upload.
2. Chat bubble:
   - Assistant messages show play control and playback state.
3. Settings:
   - Voice mode toggle: `off`, `read-aloud`, `turn-based`.
   - Provider/voice selector.
4. Thread reload:
   - Use message payload audio metadata to avoid extra fetches when available.
5. Error UX:
   - Clear provider-specific failures (no silent fallback).

## Testing and Validation
1. Unit tests:
   - Provider adapter selection and fail-fast behavior.
   - Model manifest parsing and checksum validation.
2. Integration tests:
   - `/api/voice/turn` full path with mocked voice-service.
   - `/api/voice/read` cache-hit vs cache-miss behavior.
   - Message-audio attachment persistence and retrieval.
3. End-to-end tests:
   - Turn-based voice: upload audio → transcript → assistant text → audio attachment.
   - Read-aloud mode: assistant text message gets playable cached audio.
4. Manual smoke scripts:
   - Health checks for backend + voice-service.
   - Provider-specific synth/transcribe calls.
   - Replay verification after restart (no regeneration).

## Rollout Phases
1. Phase 1: Backend/DB contracts + voice-service skeleton + Whisper + local adapters.
2. Phase 2: UI controls (mic, play, auto-read), cached playback linkage.
3. Phase 3: ElevenLabs + Google production-ready cloud adapters.
4. Phase 4: MiniMax scaffold behind feature flag with readiness checklist.
5. Phase 5: Distribution docs, bundle scripts, operator runbook.

## Risks and Mitigations
1. Model artifact size explosion:
   - Mitigation: strict manifest curation and documented disk budget.
2. Provider API drift:
   - Mitigation: adapter version pinning and contract tests.
3. Audio codec incompatibility:
   - Mitigation: standardize WAV internally, optional MP3 transcode layer.
4. Sync turn latency:
   - Mitigation: timeout budgets + explicit errors + optional future async endpoint.

## Assumptions and Defaults
1. Turn-based mode is non-streaming and synchronous by default.
2. Audio attachments are mandatory for assistant playback reuse.
3. Provider failures are surfaced immediately; no implicit fallback.
4. Docker-compatible runtime is prioritized.
5. Qwen/LFM local adapters target OpenAI-compatible speech APIs.
6. Whisper baseline is `small.en`.
7. Cloud rollout starts with ElevenLabs and Google, MiniMax scaffolded.
