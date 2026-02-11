"""TTS service configuration."""

# Provider registry
# Each provider specifies a backend type and model configuration.
# "mode" controls the synthesis path:
#   - "custom_voice" (default): predefined speakers, no reference audio needed
#   - "voice_clone": requires ref_audio + ref_text for voice cloning
TTS_PROVIDERS = {
    # -- CustomVoice (recommended: predefined speakers, no reference audio needed) --
    "qwen3_0.6b": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    },
    "qwen3_1.7b": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    },
    # -- Base (voice cloning only; requires ref_audio + ref_text) --
    "qwen3_0.6b_base": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "mode": "voice_clone",
    },
    "qwen3_1.7b_base": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "mode": "voice_clone",
    },
    "chatterbox_tts": {
        "backend": "huggingface",
        "model_id": "REPLACE_WITH_CHATTERBOX_MODEL",
    },
    "lfm_2_5_audio_1_7b": {
        "backend": "huggingface",
        "model_id": "REPLACE_WITH_LFM_MODEL",
    },
}

DEFAULT_PROVIDER = "qwen3_1.7b"
