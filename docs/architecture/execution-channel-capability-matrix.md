# Execution Channel Capability Matrix

Research date: 2026-09-26

## Scope and evidence labels

This matrix records external harness surfaces found in official vendor or project sources. It is a research snapshot, not a Codexify adapter registry, integration plan approval, or support claim. Vendor documentation can establish only what that external project documents.

Evidence labels mean:

- **declared**: the capability is stated by a first-party source for that harness or vendor.
- **verified-by-Codexify**: a bounded Codexify proof covers the exact local seam described; this does not imply generalized channel support.
- **external-documentation-only**: an official source exposes a candidate surface, but its contract, maturity, or relevant behavior is ambiguous or not sufficiently documented for a stronger classification.

Maturity labels report the vendor's explicit lifecycle statement where found. **Unknown** means the reviewed official material did not give a clear stable, beta, or preview classification. No external row claims Codexify runtime support. The only Codexify verification noted here is a bounded pre-existing Pi invocation seam.

## Vendor harnesses

### OpenAI Codex

- **Candidate channel ID:** codex.
- **Vendor / ownership:** OpenAI; first-party.
- **Interface forms:** Codex CLI and IDE/app surfaces; App Server is a maintained, first-class integration surface using a long-running process and bidirectional JSON-RPC-style messages over JSONL/stdin/stdout. The TypeScript Codex SDK wraps programmatic access.
- **Long-running/server:** App Server hosts the Codex core process; session/thread operations are available through that surface.
- **Headless:** Codex Exec provides non-interactive execution.
- **SDK/protocol:** App Server protocol and TypeScript SDK.
- **Session/resume:** threads can be created, resumed, forked, and archived; this identity remains native Codex lineage.
- **Model-provider plurality:** App Server documents OpenAI-backed operation and Amazon Bedrock authentication. The sources checked do not establish arbitrary third-party inference-provider compatibility.
- **Authentication:** App Server documents API key, ChatGPT-managed sign-in, and Amazon Bedrock credential modes. The actual selected entitlement route remains separate from channel identity.
- **Maturity:** unknown for App Server's formal lifecycle; OpenAI describes it as a first-class maintained path but the reviewed article does not assign stable/beta status.
- **Codexify candidate integration seam:** App Server adapter; bounded CLI Exec is a separate headless candidate.
- **Evidence:** [OpenAI, Unlocking the Codex harness: how we built the App Server](https://openai.com/index/unlocking-the-codex-harness/), [Codex App Server documentation](https://developers.openai.com/codex/app-server/), and [Codex SDK documentation](https://developers.openai.com/codex/sdk/), checked 2026-09-26.
- **Evidence status:** declared. No Codexify adapter or supported native Codex channel is established.

### Anthropic Claude

- **Candidate channel ID:** claude.
- **Vendor / ownership:** Anthropic; first-party.
- **Interface forms:** Claude Code CLI, Claude Agent SDK for programmatic local harness use, and the distinct hosted Claude Managed Agents service.
- **Long-running/server:** Managed Agents exposes hosted, long-running sessions with event streaming and managed or self-hosted execution environments. This hosted surface is distinct from the local Claude Code CLI/SDK.
- **Headless:** Claude Code supports non-interactive prompt mode.
- **SDK/protocol:** Claude Agent SDK for TypeScript/Python; Managed Agents API and event-stream surface.
- **Session/resume:** Claude Code supports session IDs and resume/continue; Managed Agents documents session operations and server-side state.
- **Model-provider plurality:** Anthropic models are the native route; official Claude Code docs also cover enterprise providers such as Amazon Bedrock and Google Vertex AI. Claude Code can be configured with third-party gateways, but Anthropic states it does not endorse, maintain, or audit LiteLLM.
- **Authentication:** Claude Code documents Anthropic Console/API-key, Claude account subscription, and supported enterprise cloud-provider authentication. Managed Agents requires an Anthropic Console API key.
- **Maturity:** mixed by surface; Managed Agents is explicitly Beta, while the reviewed CLI/SDK documentation does not provide one shared lifecycle label.
- **Codexify candidate integration seam:** Claude Agent SDK for a local native loop, or Managed Agents as a separately governed hosted channel; these are not interchangeable deployment modes.
- **Evidence:** [Claude Managed Agents quickstart](https://platform.claude.com/docs/en/managed-agents/quickstart), [Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview), [Claude Code CLI usage](https://docs.anthropic.com/en/docs/claude-code/cli-usage), [Claude Code authentication](https://docs.anthropic.com/en/docs/claude-code/getting-started), [Claude Code LLM gateway configuration](https://docs.anthropic.com/en/docs/claude-code/llm-gateway), and [Anthropic Claude Agent SDK TypeScript repository](https://github.com/anthropics/claude-agent-sdk-typescript), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native Claude channel is established.

### Qwen Code

- **Candidate channel ID:** qwen-code.
- **Vendor / ownership:** Alibaba Cloud / Qwen; first-party.
- **Interface forms:** interactive CLI/TUI, headless CLI, ACP, TypeScript and Python SDKs, and a local HTTP/SSE daemon called qwen serve.
- **Long-running/server:** qwen serve exposes a workspace-scoped HTTP/SSE runtime with session and transcript operations. Current documentation labels it Stage 1 experimental and lists production and multi-daemon guarantees as deferred.
- **Headless:** direct non-interactive CLI and SDK query paths are documented.
- **SDK/protocol:** TypeScript SDK, Python SDK, ACP, HTTP/SSE daemon API, and an MCP bridge to the daemon.
- **Session/resume:** CLI/SDK session continuation and daemon session load/resume are documented.
- **Model-provider plurality:** SDK documentation lists OpenAI, Anthropic, Gemini, and Vertex AI auth modes; configuration supports multiple provider/model choices. Current Qwen OAuth examples are explicitly described as legacy after that free tier was discontinued.
- **Authentication:** provider credentials follow the configured inference service. The daemon defaults to trusted loopback without bearer authentication; shared or untrusted hosts require bearer authentication. Daemon access authentication is separate from inference entitlement.
- **Maturity:** mixed; Qwen Code CLI is documented as stable from 0.4, the TypeScript SDK is described as minimum/experimental, and qwen serve is Stage 1 experimental and first ships in a 0.16-alpha.
- **Codexify candidate integration seam:** headless/SDK process seam for the least stateful candidate; assess qwen serve only after its declared production and network-flakiness gaps are resolved.
- **Evidence:** [Qwen Code architecture](https://qwenlm.github.io/qwen-code-docs/en/developers/architecture/), [qwen serve daemon](https://qwenlm.github.io/qwen-code-docs/en/users/qwen-serve/), [TypeScript SDK](https://qwenlm.github.io/qwen-code-docs/en/developers/sdk-typescript/), and [REST API integration guide](https://qwenlm.github.io/qwen-code-docs/en/developers/rest-api-integration/), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native Qwen channel is established.

### MiniMax Code

- **Candidate channel ID:** minimax-code.
- **Vendor / ownership:** MiniMax; first-party.
- **Interface forms:** interactive terminal agent, headless exec command, and ACP process.
- **Long-running/server:** the reviewed official README documents process-based ACP and session continuation, but no separate long-running daemon/server contract.
- **Headless:** mcode exec is documented for scripts, CI, batch work, and evaluation.
- **SDK/protocol:** ACP is the documented client protocol; no separate first-party SDK was found in the reviewed README.
- **Session/resume:** continue and explicit session resume are documented.
- **Model-provider plurality:** MiniMax Code supports MiniMax and configured OpenAI-compatible or Anthropic-compatible provider endpoints, including third-party or self-hosted endpoints. MiniMax's own Token Plan page explicitly describes using MiniMax credentials in Claude Code and other compatible clients, showing that MiniMax inference identity does not determine the selected harness.
- **Authentication:** MiniMax account/Token Plan and API-key routes are documented; custom provider credentials are configured separately.
- **Maturity:** unknown; the public CLI source is versioned, but the reviewed source does not assign stable/beta/preview status.
- **Codexify candidate integration seam:** ACP adapter, with headless exec as a simpler bounded alternative.
- **Evidence:** [MiniMax Code official repository](https://github.com/MiniMax-AI/minimax-code) and [MiniMax Token Plan / compatible coding-tool guidance](https://platform.minimax.io/subscribe/coding-plan), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native MiniMax channel is established.

### Gemini CLI

- **Candidate channel ID:** gemini-cli.
- **Vendor / ownership:** Google; first-party.
- **Interface forms:** interactive terminal CLI, headless prompt mode, published Gemini CLI Core package, and a separately packaged A2A server project in the official repository.
- **Long-running/server:** the official repository contains and publishes a distinct A2A server package; this does not mean the normal Gemini CLI process itself is an A2A server.
- **Headless:** non-interactive prompt mode and stream/JSON output are documented.
- **SDK/protocol:** Gemini CLI Core is the programmatic package; A2A server is a separate package and candidate surface.
- **Session/resume:** sessions persist by project and can be resumed by latest, index, or ID.
- **Model-provider plurality:** first-party authentication options include Google account access, Gemini API key, and Vertex AI. The reviewed sources do not establish arbitrary third-party inference-provider compatibility.
- **Authentication:** Google account OAuth, API key, or Vertex AI credentials depending on configuration.
- **Maturity:** stable CLI release channel is documented; the reviewed sources do not separately classify the A2A server lifecycle.
- **Codexify candidate integration seam:** Core/headless CLI for a local process adapter; evaluate the separate A2A server only as a distinct protocol surface.
- **Evidence:** [Gemini CLI repository](https://github.com/google-gemini/gemini-cli), [authentication](https://geminicli.com/docs/get-started/authentication/), [session management](https://geminicli.com/docs/cli/session-management/), [package overview](https://geminicli.com/docs/npm/), and [release channels](https://geminicli.com/docs/releases/), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native Gemini channel is established.

### Z.ai ZCode

- **Candidate channel ID:** zcode.
- **Vendor / ownership:** Z.ai; first-party.
- **Interface forms:** desktop, browser, and terminal workspace; the official repository contains the CLI and agent runtime.
- **Long-running/server:** the repository includes server and client SDK packages and documents a local Web mode. Current CLI source dispatches app-server and agent-server commands, but the reviewed public English documentation does not define their protocol, compatibility, or lifecycle contract in sufficient detail.
- **Headless:** prompt/target invocations and resume flags are visible in the CLI source.
- **SDK/protocol:** server/client SDK packages are present in the repository. Exact app-server/agent-server protocol guarantees remain unclear from the checked public contract.
- **Session/resume:** CLI source accepts continue/resume session requests; public compatibility guarantees were not located.
- **Model-provider plurality:** not established by the checked first-party English documentation.
- **Authentication:** CLI login/logout commands are present; Web mode documents its own local/remote server token behavior. How vendor account login maps to inference entitlement, API keys, and app-server auth remains unclear.
- **Maturity:** unknown; the README identifies a v3.14.3 product update but does not label the agent protocol stable, beta, or preview.
- **Codexify candidate integration seam:** do not select a protocol adapter until Z.ai publishes or otherwise verifies the app-server/agent-server wire contract and auth/session guarantees; CLI headless mode is only an exploratory alternative.
- **Evidence:** [ZCode English repository README](https://github.com/zai-org/ZCode/blob/main/README.en.md) and [official CLI command dispatcher source](https://github.com/zai-org/ZCode/blob/main/apps/zcode-cli/packages/cli/src/run.ts), checked 2026-09-26.
- **Evidence status:** external-documentation-only. Surface names are present in first-party source, but protocol and auth semantics are too ambiguous to classify as a mature Codexify integration seam. No Codexify native ZCode channel is established.

### Mistral Vibe

- **Candidate channel ID:** mistral-vibe.
- **Vendor / ownership:** Mistral; first-party.
- **Interface forms:** interactive CLI and programmatic prompt mode.
- **Long-running/server:** no separate daemon or persistent agent server contract was found in the reviewed official CLI pages.
- **Headless:** programmatic prompt invocation with bounded turns is documented.
- **SDK/protocol:** CLI invocation is documented; no separate SDK or agent protocol was identified in the reviewed sources.
- **Session/resume:** continue and resume by session ID are documented; local interaction logging provides the resume record.
- **Model-provider plurality:** provider/model profiles include Mistral and generic OpenAI-style provider configuration, including OpenRouter.
- **Authentication:** Mistral API key or configured provider key via environment variables; Mistral account plans may supply Vibe usage, but funding posture remains distinct from channel identity.
- **Maturity:** unknown; the reviewed CLI documentation does not assign a lifecycle label.
- **Codexify candidate integration seam:** bounded programmatic CLI process adapter; a richer SDK/server seam was not found in the checked first-party docs.
- **Evidence:** [Mistral Vibe CLI usage](https://docs.mistral.ai/vibe/code/cli/work-with-cli) and [API keys and profiles](https://docs.mistral.ai/vibe/code/cli/api-keys-profiles), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native Mistral Vibe channel is established.

### DeepSeek Harness

- **Candidate channel ID:** deepseek-harness.
- **Vendor / ownership:** DeepSeek; first-party developer-preview harness.
- **Interface forms:** local harness profiles include web, headless, SDK, ACP, and SDK-minimal modes.
- **Long-running/server:** local web server and JSON-RPC/ACP server profiles are documented. The web server is loopback by default; deployment beyond loopback has additional authentication and transport considerations.
- **Headless:** headless profile and SDK are documented.
- **SDK/protocol:** Python SDK plus ACP and JSON-RPC server profile surfaces.
- **Session/resume:** SDK accepts profile and session identity for continuation.
- **Model-provider plurality:** DeepSeek inference is the documented native route; profiles and compatible endpoint configuration exist, but the developer-preview status does not establish broad production compatibility.
- **Authentication:** DeepSeek API key for inference; the web-server reference says the server binds to loopback by default and the base server carrier does not supply TLS/authentication, so remote exposure requires a separately secured deployment.
- **Maturity:** preview; DeepSeek API documentation explicitly calls DeepSeek Harness a developer preview.
- **Codexify candidate integration seam:** isolated SDK/ACP adapter after preview review; headless mode is another candidate for bounded experiments.
- **Evidence:** [DeepSeek API harness integration](https://api-docs.deepseek.com/guides/harness), [Harness SDK and architecture reference](https://deepseek-harness.github.io/deepseek-harness/en/reference/), [Python SDK](https://deepseek-harness.github.io/deepseek-harness/en/guide/python-sdk), and [web-server reference](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/web-server), checked 2026-09-26.
- **Evidence status:** declared. No Codexify native DeepSeek Harness channel is established.

### Pi

- **Candidate channel ID:** pi.
- **Vendor / ownership:** independent third-party open-source harness; not a first-party harness for any single model vendor.
- **Interface forms:** interactive terminal agent, print/headless mode, RPC mode, and TypeScript SDK.
- **Long-running/server:** RPC mode provides a process-hosted protocol surface; exact invocation and lifecycle suitability remain adapter-specific.
- **Headless:** print mode supports scripted invocation.
- **SDK/protocol:** TypeScript SDK and RPC mode.
- **Session/resume:** session files and session IDs support continuation/resumption.
- **Model-provider plurality:** provider and model selection spans multiple hosted providers and local runtimes, including OpenAI, Anthropic, Google, DeepSeek, Mistral, Z.ai, MiniMax, and Ollama-family endpoints.
- **Authentication:** provider-specific subscriptions, OAuth, or API keys; local endpoint authentication follows the selected runtime. These credentials remain separate from channel identity.
- **Maturity:** unknown; the official project README describes capabilities but does not assign stable/beta/preview status.
- **Codexify candidate integration seam:** preserve and evolve the existing bounded Guardian/Pi invocation adapter where explicitly selected; do not require Pi to proxy native harnesses.
- **Evidence:** [Pi coding agent project, package README](https://github.com/earendil-works/pi/tree/main/packages/coding-agent), checked 2026-09-26. Codexify's bounded Pi invocation seam is separately documented in [the local proof packet](./proofs/2026-08-16-guardian-pi-live-invocation-seam-proof.md).
- **Evidence status:** verified-by-Codexify for that bounded existing Pi invocation primitive only; broader Pi channel behavior, arbitrary provider/model combinations, composer routing, and release support are not established.

## Interpretation

The matrix informs future capability records and candidate integration seams only. A channel's existence, an advertised protocol, a successful isolated adapter experiment, and a supported Codexify release path are separate evidence levels. Runtime routing may expose only combinations whose effective capabilities have been proven under applicable policy, entitlement, environment, and task requirements.

The explicit ambiguity flags are:

- **Z.ai ZCode:** app-server and agent-server names exist in current source, but public protocol, authentication, and compatibility semantics were not clear enough to classify as stable integration contracts.
- **Qwen Code daemon:** qwen serve is a current documented experimental surface with production and multi-daemon gaps; the direct CLI/SDK and daemon require separate maturity assessment.
- **DeepSeek Harness:** developer preview.
- **Claude Managed Agents:** beta; distinct from local Claude Code/Agent SDK execution.

No matrix entry changes Codexify runtime behavior or release claims.
