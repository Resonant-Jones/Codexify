# Whoosh’d × Codexify Local Inference Signoff — 2026-06-14

Tags: #codexify #whooshd #local-inference #mlx #mlx-vlm #gguf #llama-cpp #async-worker #multimodal #architecture #checkpoint #verified

Today marks the completion of the Whoosh’d × Codexify local inference integration sequence.

The work crossed both repositories but preserved their intended boundary. Whoosh’d remains the standalone local inference gateway. Codexify remains the application layer that owns memory, task orchestration, persona/context routing, Docker smoke configuration, async workers, and user-facing workflows. Codexify talks to Whoosh’d over HTTP only. No Whoosh’d internals were imported into Codexify, and Whoosh’d was not merged into Codexify or added as a Codexify container.

## Verified Runtime Lanes

Whoosh’d now supports and has verified:

- MLX text via `mlx_lm_server`
    
- MLX-VLM vision via `mlx_vlm`
    
- GGUF inference via `llama.cpp` / `llama-server`
    
- OpenAI-compatible chat completion routing
    
- Runtime inventory through `/v1/models` and `/api/tags`
    
- Runtime health through `/health/runtime`
    

Codexify has verified local-only inference through Whoosh’d across:

- Sync text: `llama-3.2-3b-mlx` → `mlx_lm_server`
    
- Sync vision: `qwen2-vl-2b-mlx` → `mlx_vlm`
    
- Sync GGUF: `qwen2.5-0.5b-gguf` → `llama_cpp`
    
- Async multimodal: `qwen2-vl-2b-mlx` → `mlx_vlm`
    
- Streaming worker lifecycle
    
- No cloud fallback
    
- Base64 logging safety
    

The async multimodal path was the final major structural seam. It required preserving structured OpenAI-compatible multimodal content through Codexify’s queued worker path instead of flattening image turns into plain text. The worker now detects image content, preserves the structured payload, selects the vision model, and sends the correct model to Whoosh’d.

## Important Fixes

Codexify-side fixes included:

- Durable Whoosh’d smoke Docker configuration
    
- Local-only provider profile enforcement
    
- `LOCAL_CHAT_MODEL`, `LOCAL_VISION_MODEL`, and `LOCAL_GGUF_MODEL` handling
    
- Vision model source correction
    
- GGUF explicit model preservation
    
- Structured multimodal task payload preservation
    
- Async multimodal worker model resolution
    
- Local provider precedence fix so `LOCAL_CHAT_MODEL` beats `LOCAL_LLM_MODEL` for worker async text
    

Whoosh’d-side fixes and confirmations included:

- Multi-runtime adapter routing
    
- Registry-backed model inventory
    
- MLX text adapter support
    
- MLX-VLM adapter support
    
- llama.cpp adapter support
    
- Runtime concurrency guardrails
    
- Codexify compatibility smoke tests
    
- Manual validation reports for MLX, MLX-VLM, and GGUF lanes
    
- Confirmation that all configured runtimes can register together in one Whoosh’d process when environment variables are passed in the same execution context
    

## Commit Checkpoints

Codexify commits:

- `bf51c64a6` — `feat(local): wire Codexify to Whoosh'd local inference`
    
- `ba0fe6eaf` — `feat(memory): add fact candidate review flow`
    
- `2dd6e26d8` — `chore(docs): update generated audits and marketing artifacts`
    

Whoosh’d commits:

- `cd6eafe` — `feat(runtime): add multi-runtime routing and adapters`
    
- `da20fb4` — `feat(codexify): add local provider compatibility smokes`
    
- `c8c34f4` — `docs(validation): add local runtime validation reports`
    

Both work trees were cleaned and committed. No push was performed at the time of this checkpoint.

## Known Limitation

The first async text task after worker restart can remain in `AWAITING_FIRST_TOKEN` while the MLX model warms. This should be treated as `MODEL_WARMING`, not offline or failed behavior. Sync text works once the model is loaded, and subsequent async text tasks should complete normally after warmup. A future worker-warmup service could preload local models to remove this first-use delay.

GGUF currently requires a separate `llama-server` process. Managed llama-server startup may be added later, but it is not required for the verified integration.

## Why This Matters

This checkpoint turns local inference from an experiment into a usable substrate.

Codexify can now operate through Whoosh’d as a local-first inference layer across text, vision, GGUF, sync, async, and multimodal paths while preserving local-only guarantees and avoiding silent cloud fallback.

The architectural boundary is now clear:

- Whoosh’d is the engine room.
    
- Codexify is the memory, workflow, and user-facing cognition layer.
    
- The bridge between them is HTTP, model inventory, runtime health, and OpenAI-compatible message structure.
    

This is the foundation for the next phase of Codexify work: Chronicle, memory, identity-aware workflows, and richer local-first cognition built on top of a verified inference substrate.