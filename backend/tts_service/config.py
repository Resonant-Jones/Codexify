"""TTS service configuration."""

# Provider registry
# Each provider specifies a backend type and model configuration
TTS_PROVIDERS = {
    "qwen3_0.6b_base": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    },
    "qwen3_1.7b_base": {
        "backend": "huggingface",
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
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
