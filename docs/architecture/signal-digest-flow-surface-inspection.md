Signal Digest Flow Surface Inspection

Purpose: Inspect current Codexify Flow and adjacent runtime capabilities for Signal Digest MVP feasibility. The goal is to identify which loop steps are already possible with no code, which steps would require thin helper primitives, and which areas remain unproven in the currently inspected surface.
Last updated: 2026-03-11

Source anchors:
 • docs/architecture/signal-digest-flow-first-mvp.md
 • docs/architecture/flows.md
 • guardian/routes/flows.py
 • guardian/flows/spec.py
 • guardian/flows/compiler.py
 • guardian/flows/runner.py
 • guardian/flows/primitives.py
 • guardian/cron/scheduler.py
 • guardian/cron/executor.py
 • guardian/workers/cron_worker.py
 • guardian/routes/channels.py
 • guardian/channels/adapters/slack.py
 • guardian/core/research/Modules/browser/crawl_ai.py

Signal Digest Flow Surface Inspection

Signal Digest MVP Loop
 • scheduled or manual trigger
 • source fetch from reddit and google_news
 • normalization into a shared candidate shape
 • full-content read attempt where possible
 • LLM relevance scoring against a user profile
 • ranking and thresholding
 • digest composition
 • delivery to one channel first

Capability Mapping

Step Existing surface Evidence Status Notes
scheduled or manual trigger Manual Flow execution exists through the Flow API. Flow specs also carry cron trigger metadata, and a separate cron subsystem exists. guardian/routes/flows.py exposes POST /api/flows/{flow_id}/run. guardian/flows/spec.py defines FlowTrigger with manual, cron, and event. docs/architecture/flows.md, guardian/cron/scheduler.py, guardian/cron/executor.py, and guardian/workers/cron_worker.py show cron as a separate runtime path, with execution limited to noop and webhook. Supported now Manual trigger is proven now. Cron metadata exists, but a cron-driven Flow execution path is not proven in the inspected files.
source fetch from reddit and google_news The inspected Flow surface has no source-specific fetch primitive. A generic crawl surface exists outside Flow. guardian/flows/spec.py and guardian/flows/primitives.py define no Reddit or Google News fetch primitive. guardian/flows/primitives.py registers only generic contracts and binds them to stub handlers. guardian/core/research/Modules/browser/crawl_ai.py exposes generic URL and content crawling, not a Flow-exposed Reddit or Google News fetch path. Not yet proven The inspected files do not prove that a Flow can fetch Reddit or Google News candidates with no new code.
normalization into a shared candidate shape Flow step outputs are generic dictionaries, but no shared candidate schema is present. guardian/flows/spec.py uses generic dict[str, Any] step params and outputs. guardian/flows/runner.py stores step_outputs as generic dictionaries. docs/architecture/signal-digest-flow-first-mvp.md explicitly allows a candidate normalization helper if Flow cannot provide a stable schema. Supported with thin helper A small normalization helper appears sufficient once source items exist, but the shared candidate shape is not already defined in the inspected Flow surface.
full-content read attempt where possible A crawl surface exists for webpage and PDF reading, but it is not exposed as a Flow primitive. guardian/core/research/Modules/browser/crawl_ai.py provides get_summary() and get_pdf_summary(). guardian/flows/spec.py and guardian/flows/primitives.py do not define a full-content extraction primitive, and the default primitive handlers are stubs. Supported with thin helper The inspected repo already has a content-reading substrate. The missing piece is a thin Flow-accessible bridge, not a new backend domain.
LLM relevance scoring against a user profile Flow contracts exist for classify, summarize, and plan, but the inspected runtime path does not prove real LLM execution. guardian/flows/spec.py defines classify, summarize, and plan. guardian/flows/primitives.py binds all default primitives to_stub_handler. guardian/routes/flows.py calls compile_flow() and run_flow() without supplying a non-default registry. guardian/flows/runner.py invokes the registry it is given. Not yet proven The contract shape for scoring exists, but the inspected Flow API path does not prove that those steps call a model rather than returning stub output.
ranking and thresholding The runner can pass step outputs forward, but no ranking or threshold primitive is defined. guardian/flows/runner.py carries step_outputs across steps. guardian/flows/spec.py and guardian/flows/primitives.py define no ranking or threshold primitive, and the available generic primitives are still stubbed. Not yet proven The inspected files do not prove a concrete ranking implementation in Flow, either deterministic or model-driven.
digest composition A summarize-shaped Flow contract exists, but the inspected runtime path does not prove real digest assembly. guardian/flows/spec.py includes summarize. guardian/flows/primitives.py registers summarize with a stub handler. guardian/routes/flows.py uses the default compile/run path. Not yet proven Digest composition is contract-shaped but not runtime-proven in the inspected surface.
delivery to one channel first Existing channel infrastructure exists, including per-user channel config and a concrete Slack adapter, but Flow does not expose channel delivery directly. guardian/routes/channels.py provides channel config storage. guardian/channels/adapters/slack.py provides outbound Slack sending. guardian/flows/spec.py and guardian/flows/primitives.py define no delivery primitive or channel-send bridge. Supported with thin helper Existing channel infrastructure is real, but Flow-native delivery exposure is not proven. The first delivery channel remains undecided on current evidence.

Thin Helper Assessment

No minimum thin helper should be selected yet from this inspection alone.

The first blocking issue is not a narrow missing bridge. The inspected Flow API path does not yet prove two more fundamental things:
 • source fetch from reddit and google_news
 • real non-stub LLM execution for scoring and digest composition

Until those proof gaps are narrowed, choosing a helper would be premature.

If later inspection confirms that real Flow handlers already exist outside the inspected files, then the smallest likely helper would be the full-content extraction bridge, because guardian/core/research/Modules/browser/crawl_ai.py already provides the reading substrate while the Flow primitive catalog does not expose it directly.

Delivery Path Assessment

The inspected repo proves existing channel infrastructure, but it does not yet prove Flow-native delivery exposure.

Existing channel infrastructure:
 • guardian/routes/channels.py proves per-user channel configuration storage exists.
 • guardian/channels/adapters/slack.py proves at least one concrete outbound adapter exists.

Flow-native delivery exposure:
 • guardian/flows/spec.py and guardian/flows/primitives.py do not define a delivery primitive.
 • guardian/routes/flows.py and guardian/flows/runner.py do not show a bridge from Flow execution into channel delivery.

Because of that split, the inspected files do not prove a lowest-friction first delivery path. Slack has the strongest inspected channel evidence, but the current Flow surface does not prove that Slack is the first channel with the least integration work. The first delivery channel should remain explicitly undecided.

Gaps and Risks
 • The Flow API path in guardian/routes/flows.py uses the default compiler and runner path, while guardian/flows/primitives.py binds the default primitive catalog to stub handlers. Contract presence is therefore not proof of runtime capability.
 • guardian/flows/spec.py supports cron trigger metadata, but the inspected files do not show Flow definitions being scheduled or executed by the cron subsystem. The inspected cron executor in guardian/cron/executor.py only proves noop and webhook.
 • No inspected Flow primitive proves Reddit or Google News source fetches.
 • No inspected Flow primitive proves ranking or thresholding behavior.
 • Existing channel infrastructure and existing content-crawl infrastructure are both outside the inspected Flow-native primitive surface.

Recommendation

Perform one narrower inspection if a critical proof gap remains.

That narrower inspection should answer one precise question: whether Codexify already has a non-stub Flow execution path or tool-binding path that can perform real source fetch, real LLM scoring or composition, and channel delivery without adding new Flow primitives.

Conclusion

Signal Digest MVP appears directionally feasible on current Codexify rails, but not yet proven as an end-to-end Flow-first assembly from the inspected runtime path.

The next move is not zero-code assembly yet, and it is not one thin helper yet. The next move is one narrower inspection to resolve the current proof gap around non-stub Flow execution.

Validation

No automated tests apply.

