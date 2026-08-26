# Active Tester model authority reconciliation proof

## Result

`ACTIVE_TESTER_QWEN_RUNTIME_UNAVAILABLE`

ADR-074 permits the active Tester operator environment to select the concrete
local chat model. The active Tester already selects
`qwen3.8-27b-4bit`, its supported profile permits that historical default, and
Compose transports that one value to the four chat-model aliases. The live
Whoosh'd inventory does not advertise that exact identifier, however: it
advertises a Qwen filesystem path instead. Guardian correctly remains fail
closed with `configured_model_not_advertised_by_whooshd`.

The task explicitly forbids a Whoosh'd host repair. No configuration or host
change can therefore produce the required local-provider health state here.
This receipt records the authority reconciliation and the first causal runtime
blocker; it does not prove a Qwen completion, change current-main release
truth, or qualify Watchdog.

## Source identity and lineage

| Surface | Observation |
| --- | --- |
| Task checkout | `codex/diagnose-tester-fresh-chroma-failure` at `d64ad1db99476052c210d50afd166a017262d14a` |
| Required task lineage | `d64ad1db99476052c210d50afd166a017262d14a` and ADR-074 restoration `45736720aeb7cfa210aeb69b966795a83897fbe5` are ancestors of the task checkout |
| Active Tester project | `codexify_tester` |
| Active source root | `/Volumes/Dev_SSD/Codexify-main` |
| Active source identity | detached `972c348301de68c54c0498c72d236a1e496bee0f`; it contains the ADR-074 restoration commit but is neither an ancestor nor descendant of the task checkout |
| Active source working state | pre-existing `UU docs/architecture/00-current-state.md` and staged `docs/architecture/README.md`; left untouched |
| Active containers | backend `475bb0079346…` and `worker-chat` `7c1fefc7a45…`, each on image `sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf`, restart count `0` |

The active source has the same ADR-074 and ADR-052 file contents as the task
checkout. Its inclusion of the accepted ADR-074 restoration permits applying
that doctrine to the active Tester despite the divergent checkout histories.

## ADR-074 authority determination

ADR-074 partially supersedes ADR-052 for exact local-chat-model pinning and
the precedence between profile, operator environment, and Compose. It states:

1. the supported profile owns allowed/default provider posture;
2. the operator `.env.tester` owns concrete `LOCAL_CHAT_MODEL` selection;
3. Compose transports that selection through `LOCAL_CHAT_MODEL`,
   `LOCAL_LLM_MODEL`, `DEFAULT_LOCAL_MODEL`, and `LLM_MODEL` without an
   independent literal;
4. Guardian owns fail-closed availability reporting; and
5. Whoosh'd `/v1/models` proves runtime availability but cannot rewrite
   configuration.

ADR-052 remains governing for the local Whoosh'd and bounded DeepSeek
topology. ADR-074's restored tracked default is
`qwen3.8-27b-4bit`; it explicitly does not assert that Qwen is currently
advertised or loaded. No ADR amendment is required to recognize the existing
operator selection. No ADR was changed.

## Active authority and configuration transport

The actual active operator file is
`/Volumes/Dev_SSD/Codexify-main/.env.tester`. Its non-secret values include
`LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`, cloud enabled, local-only disabled, and
the `deepseek` egress allowlist. Its `LLM_PROVIDER=deepseek` line does not
select the active global provider: the ADR-074-governed Compose overlay owns
the supported provider posture and explicitly renders `LLM_PROVIDER=local`.

The active supported profile sets `LOCAL_CHAT_MODEL=qwen3.8-27b-4bit`; the
active Compose overlay derives the four chat aliases from
`${LOCAL_CHAT_MODEL}`, keeps `LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL`
independent, and pins `DEEPSEEK_CHAT_MODEL=deepseek-v4-flash`. Its startup
script's `EXPECTED_MODEL` default is Qwen and is documented as an assertion
input rather than another selection authority.

The sanitized active Compose render and both running containers resolved:

| Setting | Backend and `worker-chat` value |
| --- | --- |
| `LLM_PROVIDER` | `local` |
| `LOCAL_CHAT_MODEL` | `qwen3.8-27b-4bit` |
| `LOCAL_LLM_MODEL` | `qwen3.8-27b-4bit` |
| `DEFAULT_LOCAL_MODEL` | `qwen3.8-27b-4bit` |
| `LLM_MODEL` | `qwen3.8-27b-4bit` |

The task-worktree `.env.tester` still names Gemma. It is ignored, not mounted
by the running Tester, and was left untouched because this worktree is not an
authorized next-launch source in this task.

## Runtime inventory and Guardian readback

All observations were non-inference reads.

`GET http://127.0.0.1:8000/v1/models` advertised exactly:

1. `mlx-community/Llama-3.2-3B-Instruct-4bit`
2. `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit`

The string `qwen3.8-27b-4bit` was absent. The Qwen path is not an accepted
alias for the configured identifier, so it cannot satisfy ADR-074's strict
availability contract.

Guardian readback on the active Tester (`127.0.0.1:8889`) recorded:

- `/health`: `200`, selected provider `local`, valid
  `v1-whooshd-deepseek-web` profile;
- `/health/chat`: Redis `ok`, fresh chat-worker heartbeat, queue depth `0`,
  but `ok=false` only because configured Qwen is not advertised;
- `/api/health/llm`: `status=down`,
  `failure_kind=configured_model_not_advertised_by_whooshd`;
- `/api/llm/catalog`: local provider authorized and reachable but
  `enabled=false`, with the two inventory IDs above; and
- DeepSeek unchanged as the bounded `deepseek-v4-flash` lane, enabled and
  available, with `attempted=false`, `executed=false`, and `completed=false`.

Redis `LLEN codexify:queue:chat` remained `0`; the normal chat-worker
heartbeat had a positive TTL. No containers were restarted.

## Execution boundary

No `.env.tester`, tracked configuration, source, test, host launchd plist,
Whoosh'd registry, model artifact, database, Redis, or Chroma state was
changed. No model was downloaded. No Whoosh'd host repair was attempted.

`MODEL_INVOCATIONS_DURING_AUTHORITY_RECONCILIATION=0`.
`DEEPSEEK_REQUESTS_DURING_AUTHORITY_RECONCILIATION=0`.

No ordinary chat task, model warmup, completion, Watchdog attempt, Watchdog
dispatch, GitHub I/O, Command Bus, or Build Loop activity occurred.

## ADR impact, validation, and follow-through

**Aligned with ADR-074 and the governing dual-provider topology; no new ADR.**

`docs/architecture/00-current-state.md` remained untouched. No focused test
applies because no tracked configuration changed. Documentation validation and
Git diff checks for this proof artifact are recorded with task closeout.

The required next task is a bounded Whoosh'd runtime-identity repair that makes
the existing Qwen runtime advertise exact `qwen3.8-27b-4bit`, or an explicit
model-authority decision. Do not bind or qualify Watchdog until one ordinary
authenticated local/Qwen completion is subsequently proven without cloud
fallback.
