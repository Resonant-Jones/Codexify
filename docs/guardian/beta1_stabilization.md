# Beta-1 Stabilization Runbook

## Scope Lock

Beta-1 is intentionally constrained to:
- Chat completion
- ChatGPT migration import
- Document upload + embedding

Out of scope surfaces are quarantined through router-mount gating and media subfeature guards.

## Required Runtime Flags

Set these for Beta-1 runs:

```env
CODEXIFY_BETA_CORE_ONLY=true
CODEXIFY_ENABLE_MEDIA_GENERATION_ROUTES=false
CODEXIFY_ENABLE_MEDIA_TTS_ROUTES=false
CODEXIFY_LOCAL_ONLY_MODE=true
ALLOW_CLOUD_PROVIDERS=false
CODEXIFY_EGRESS_ALLOWLIST=
```

## Verification Gates

1. Deterministic non-docker gate:

```bash
bash scripts/verification/validate_beta1_core_gate.sh
```

2. Docker smoke gate (target <= 10 minutes):

```bash
GUARDIAN_API_KEY=<your-api-key> bash scripts/verification/smoke_beta1.sh
```

`smoke_beta1.sh` verifies:
- clean bring-up for core services
- `/health/chat` completion-service health (redis + enqueue + worker heartbeat)
- quarantined routes return `404`
- core routes remain mounted

## Failure Behavior Contract

- If queue/redis is unavailable, `POST /api/chat/{thread_id}/complete` fails loudly with structured `503`:
  - `detail.error=completion_service_unavailable`
  - `detail.message="Completion service unavailable — check Docker/Redis."`
- Frontend surfaces:
  - `Completion service unavailable — check Docker/Redis.`
- No silent hangs, no implicit timeout-only failures.

## 7-Day Signal Timeline

- Day 1: freeze scope + enable Beta-1 core-only profile in staging.
- Day 2: run deterministic gate and fix red tests only.
- Day 3: run docker smoke and verify startup docs on a fresh machine.
- Day 4: onboard first external tester; capture first failure signatures.
- Day 5: patch only deterministic breakages within approved surface.
- Day 6: rerun full gate + smoke; confirm quarantines are still closed.
- Day 7: ship Beta-1 to tester cohort with known constraints and rollback plan.
