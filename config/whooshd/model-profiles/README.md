# Whoosh'd Model Profiles

This directory contains data-only Whoosh'd local model profiles.

A profile is not a routed provider. Profiles describe local runtime expectations,
model-family notes, acceptance gates, and release posture for MLX-backed local
models that may later be proven on the supported Codexify path.

All profiles in this directory must keep `provider_id` as `local` unless a
future ADR explicitly changes provider routing doctrine. Whoosh'd is display and
vendor metadata here, not a new provider identity.

Profiles do not prove runtime support by existing. Live proof still requires
health, catalog, supported-profile, queue/worker, and Guardian completion
evidence before a model can be treated as release-supported.

Profiles intended for travel or offline use should include local probe commands
and must still assume the model artifacts were downloaded before the machine
lost network access.

For Gemma 4 family profiles, the schema uses `capabilities.multimodal` and
`capabilities.image_input` for modality intent, and
`runtime.preferred_local_invocation_path = "mlx-vlm"` plus
`runtime.mlx_vlm_compatible = true` for the preferred local multimodal runtime
hint. The `runtime.offline_probe_command` field can carry an operator-facing
offline check such as `mlx_vlm.generate`; this is a hint, not routing logic,
and can still be overridden by explicit routing or task metadata.

New profiles must include thought/final-answer leakage policy when the model
family supports hidden, reasoning, thinking, or channelized output. Guardian-facing
transcripts must reject hidden process text, prompt-internal channel markers, and
thought-channel leakage before the model is used as a supported chat runtime.
