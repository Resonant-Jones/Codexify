#!/usr/bin/env node
/**
 * Pi Agent Wrapper for Campaign Runner
 *
 * Provides a clean interface to the Pi SDK for:
 * - Audit stage (analyze repo, generate findings as JSON)
 * - Compile stage (generate campaign set from audit)
 * - Task execution (run individual tasks with results)
 *
 * Usage:
 *   node agent-wrapper.js audit "<prompt>" [options]
 *   node agent-wrapper.js compile "<prompt>" [options]
 *   node agent-wrapper.js task "<prompt>" [options]
 *   node agent-wrapper.js readiness
 */

import path from "node:path";
import { readFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";

// Parse command line args
const args = process.argv.slice(2);
const mode = args[0] || "help";
const prompt = args.slice(1).join(" ");
const guardianAuthorizedMode = mode === "guardian-authorized-task";
const guardianAuthorizedReadinessMode = mode === "guardian-authorized-readiness";
const ACTUAL_HARNESS_ID = "pi-coding-agent";

const AUTHORIZED_FAILURE_CLASSES = new Set([
	"adapter_timeout",
	"wrapper_unavailable",
	"runtime_module_unavailable",
	"authorized_identity_rejected",
	"provider_unresolved",
	"model_unresolved",
	"oauth_auth_unavailable",
	"session_initialization_failed",
	"provider_request_failed",
	"provider_transport_failed",
	"wrapper_protocol_failed",
	"actual_identity_missing",
	"target_posture_violation",
	"unknown_adapter_failure",
]);

const OPTIONS = {
	cwd: process.cwd(),
	model: process.env.PI_MODEL || "claude-sonnet-4-20250514",
	provider: process.env.PI_PROVIDER || "anthropic",
	thinking: process.env.PI_THINKING || "medium",
	verbose: process.env.PI_VERBOSE === "1",
	disableTools: ["1", "true", "yes", "on"].includes(
		(process.env.PI_DISABLE_TOOLS || "").toLowerCase()
	),
};

// Known model mappings
const MODEL_ALIASES = {
	"sonnet": "claude-sonnet-4-20250514",
	"sonnet4": "claude-sonnet-4-20250514",
	"opus": "claude-opus-4-5",
	"opus4": "claude-opus-4-5",
	"haiku": "claude-haiku-4",
	"haiku4": "claude-haiku-4",
	"sonnet-4": "claude-sonnet-4-20250514",
	"opus-4": "claude-opus-4-5",
	"haiku-4": "claude-haiku-4",
};

function resolveModel(modelId, getModel) {
	// Check alias first
	if (MODEL_ALIASES[modelId.toLowerCase()]) {
		return MODEL_ALIASES[modelId.toLowerCase()];
	}
	// Check if it's a valid full model ID
	const model = getModel(OPTIONS.provider, modelId);
	if (model) return modelId;
	// Try partial match
	const normalized = modelId.toLowerCase().replace(/[^a-z0-9]/g, "");
	const models = ["claude-sonnet-4-20250514", "claude-opus-4-5", "claude-haiku-4"];
	for (const m of models) {
		if (m.toLowerCase().replace(/[^a-z0-9]/g, "").includes(normalized)) {
			return m;
		}
	}
	return modelId; // Return as-is, let SDK handle error
}

// Session state
let session = null;

function isModuleResolutionError(error) {
	const message = error instanceof Error ? error.message : String(error);
	return message.includes("Cannot find package") || message.includes("Cannot find module");
}

function boundedFailureClass(value) {
	return AUTHORIZED_FAILURE_CLASSES.has(value)
		? value
		: "unknown_adapter_failure";
}

function classifyAuthorizedError(error) {
	const message = error instanceof Error ? error.message : String(error);
	const text = message.toLowerCase();
	if (text.includes("cannot find package") || text.includes("cannot find module")) {
		return "runtime_module_unavailable";
	}
	if (text.includes("guardian_authorized_identity_missing") || text.includes("identity does not match")) {
		return "authorized_identity_rejected";
	}
	if (text.includes("timeout") || text.includes("timed out")) {
		return "adapter_timeout";
	}
	if (text.includes("econn") || text.includes("fetch failed") || text.includes("network") || text.includes("socket")) {
		return "provider_transport_failed";
	}
	if (text.includes("401") || text.includes("403") || text.includes("429") || text.includes("provider request") || text.includes("response")) {
		return "provider_request_failed";
	}
	if (text.includes("auth") || text.includes("oauth") || text.includes("credential") || text.includes("api key")) {
		return "oauth_auth_unavailable";
	}
	return "unknown_adapter_failure";
}

function emitAuthorizedFailure(failureClass, failureStage, details = {}) {
	const payload = {
		status: "error",
		failure_class: boundedFailureClass(failureClass),
		failure_stage: String(failureStage || "adapter_execution"),
		actual_runtime_identity: details.actual_runtime_identity || null,
		runtime_identity_established: details.runtime_identity_established === true,
		session_initialized: details.session_initialized === true,
		provider_request_started: details.provider_request_started === true,
	};
	console.log(JSON.stringify(payload));
}

async function loadPiSdk() {
	const wrapperDirectory = path.dirname(fileURLToPath(import.meta.url));
	const packageRoot = process.env.PI_CODING_AGENT_PACKAGE_ROOT
		? path.resolve(process.env.PI_CODING_AGENT_PACKAGE_ROOT)
		: path.resolve(wrapperDirectory, "../vendor/pi-coding-agent");
	const nodeModulesRoot = process.env.PI_CODING_AGENT_NODE_MODULES
		? path.resolve(process.env.PI_CODING_AGENT_NODE_MODULES)
		: path.join(packageRoot, "node_modules");
	const codingAgent = await import(pathToFileURL(path.join(packageRoot, "dist/index.js")).href);
	const piAi = await import(
		pathToFileURL(path.join(nodeModulesRoot, "@mariozechner/pi-ai/dist/index.js")).href
	);
	const packageMetadata = JSON.parse(
		await readFile(path.join(packageRoot, "package.json"), "utf8")
	);
	return {
		createAgentSession: codingAgent.createAgentSession,
		SessionManager: codingAgent.SessionManager,
		AuthStorage: codingAgent.AuthStorage,
		ModelRegistry: codingAgent.ModelRegistry,
		createCodingTools: codingAgent.createCodingTools,
		getModel: piAi.getModel,
		getProviders: piAi.getProviders,
		harnessId: ACTUAL_HARNESS_ID,
		harnessVersion: String(packageMetadata.version || ""),
	};
}

async function checkGuardianAuthorizedReadiness() {
	let identity;
	try {
		identity = requireGuardianAuthorizedIdentity();
	} catch (_error) {
		emitAuthorizedFailure("authorized_identity_rejected", "authorization");
		return;
	}

	let runtime;
	try {
		runtime = await loadPiSdk();
	} catch (error) {
		emitAuthorizedFailure(
			isModuleResolutionError(error) ? "runtime_module_unavailable" : "wrapper_unavailable",
			"runtime_load",
		);
		return;
	}

	const { AuthStorage, ModelRegistry, getModel, getProviders, harnessId, harnessVersion } = runtime;
	const providerIds = getProviders().map((provider) =>
		typeof provider === "string" ? provider : provider?.id,
	);
	if (!providerIds.includes(identity.providerId)) {
		emitAuthorizedFailure("provider_unresolved", "provider_resolution");
		return;
	}
	const model = getModel(identity.providerId, identity.modelId);
	if (!model) {
		emitAuthorizedFailure("model_unresolved", "model_resolution");
		return;
	}
	const actualRuntimeIdentity = {
		actual_provider_id: model.provider,
		actual_model_id: model.id,
		actual_harness_id: harnessId,
		actual_harness_version: harnessVersion,
	};
	const identityMatches =
		model.provider === identity.providerId &&
		model.id === identity.modelId &&
		harnessId === identity.harnessId &&
		harnessVersion === identity.harnessVersion;
	if (!identityMatches) {
		emitAuthorizedFailure("authorized_identity_rejected", "identity_verification", {
			actual_runtime_identity: actualRuntimeIdentity,
			runtime_identity_established: true,
		});
		return;
	}

	try {
		const authStorage = AuthStorage.create();
		const modelRegistry = ModelRegistry.create(authStorage);
		if (!authStorage.hasAuth(model.provider)) {
			emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness", {
				actual_runtime_identity: actualRuntimeIdentity,
				runtime_identity_established: true,
			});
			return;
		}
		const available = await modelRegistry.getAvailable();
		if (!available.some((candidate) => candidate.provider === model.provider && candidate.id === model.id)) {
			emitAuthorizedFailure("model_unresolved", "model_availability", {
				actual_runtime_identity: actualRuntimeIdentity,
				runtime_identity_established: true,
			});
			return;
		}
		console.log(JSON.stringify({
			status: "ok",
			failure_class: null,
			failure_stage: "oauth_readiness",
			actual_runtime_identity: actualRuntimeIdentity,
			runtime_identity_established: true,
			session_initialized: false,
			provider_request_started: false,
			oauth_available: true,
		}));
	} catch (_error) {
		emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness", {
			actual_runtime_identity: actualRuntimeIdentity,
			runtime_identity_established: true,
		});
	}
}

function requireGuardianAuthorizedIdentity() {
	const identity = {
		providerId: String(process.env.PI_PROVIDER || "").trim(),
		modelId: String(process.env.PI_MODEL || "").trim(),
		harnessId: String(process.env.PI_GUARDIAN_HARNESS_ID || "").trim(),
		harnessVersion: String(process.env.PI_GUARDIAN_HARNESS_VERSION || "").trim(),
	};
	if (process.env.PI_GUARDIAN_AUTHORIZED !== "1" || Object.values(identity).some(value => !value)) {
		throw new Error("guardian_authorized_identity_missing");
	}
	return identity;
}

async function checkReadiness() {
	const payload = {
		adapter_initialized: false,
		provider_resolved: false,
		provider_credential_available: false,
		effective_provider: OPTIONS.provider,
		effective_model: OPTIONS.model,
		reason: "adapter_initialization_failed",
	};

	try {
		const { AuthStorage, ModelRegistry, getModel } = await loadPiSdk();
		const resolvedModelId = resolveModel(OPTIONS.model, getModel);
		payload.effective_model = resolvedModelId;
		const model = getModel(OPTIONS.provider, resolvedModelId);
		if (!model) {
			payload.adapter_initialized = true;
			payload.reason = "provider_unresolved";
			return payload;
		}

		payload.adapter_initialized = true;
		payload.provider_resolved = true;
		payload.effective_provider = model.provider;
		payload.effective_model = model.id;

		const authStorage = AuthStorage.create();
		ModelRegistry.create(authStorage);
		// hasAuth checks stored/env/fallback presence without refreshing OAuth or
		// contacting the provider. Readiness is not credential-validity proof.
		payload.provider_credential_available = authStorage.hasAuth(model.provider);
		payload.reason = payload.provider_credential_available
			? null
			: "provider_credential_missing";
		return payload;
	} catch (_error) {
		return payload;
	}
}

async function runAgent() {
	let createAgentSession;
	let SessionManager;
	let AuthStorage;
	let ModelRegistry;
	let createCodingTools;
	let getModel;
	let getProviders;
	let harnessId;
	let harnessVersion;

	const authorizedIdentity = guardianAuthorizedMode
		? requireGuardianAuthorizedIdentity()
		: null;

	try {
		({
			createAgentSession,
			SessionManager,
			AuthStorage,
			ModelRegistry,
			createCodingTools,
			getModel,
			getProviders,
			harnessId,
			harnessVersion,
		} = await loadPiSdk());
	} catch (error) {
		if (guardianAuthorizedMode) {
			emitAuthorizedFailure(
				isModuleResolutionError(error) ? "runtime_module_unavailable" : "wrapper_unavailable",
				"runtime_load",
			);
			return;
		}
		if (isModuleResolutionError(error)) {
			console.error("Pi SDK dependencies are not available in this Node environment.");
			console.error("The coding-worker image supplies the pinned SDK through its configured runtime path.");
			console.error("Rebuild worker-coding, or restore the vendored SDK artifacts for a source-only run.");
			console.error("Shared Pi auth still reuses ~/.pi/agent/auth.json once the SDK is present.");
			process.exit(1);
		}
		throw error;
	}

	const resolvedModelId = guardianAuthorizedMode
		? authorizedIdentity.modelId
		: resolveModel(OPTIONS.model, getModel);
	const resolvedProviderId = guardianAuthorizedMode
		? authorizedIdentity.providerId
		: OPTIONS.provider;

	// Set up auth and model registry
	let authStorage;
	let modelRegistry;
	try {
		authStorage = AuthStorage.create();
		modelRegistry = ModelRegistry.create(authStorage);
	} catch (error) {
		if (guardianAuthorizedMode) {
			emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness");
			return;
		}
		throw error;
	}

	const tools = OPTIONS.disableTools ? [] : createCodingTools(OPTIONS.cwd);

	// Get model
	const model = getModel(resolvedProviderId, resolvedModelId);
	if (!model) {
		if (guardianAuthorizedMode) {
			const providerIds = getProviders().map((provider) =>
				typeof provider === "string" ? provider : provider?.id,
			);
			emitAuthorizedFailure(
				providerIds.includes(resolvedProviderId) ? "model_unresolved" : "provider_unresolved",
				providerIds.includes(resolvedProviderId) ? "model_resolution" : "provider_resolution",
			);
			return;
		}
		console.error(`Model not found: ${resolvedModelId}`);
		console.error("Available models:");
		console.error("  - claude-sonnet-4-20250514 (Claude Sonnet 4)");
		console.error("  - claude-opus-4-5 (Claude Opus 4)");
		console.error("  - claude-haiku-4 (Claude Haiku 4)");
		console.error("Aliases: sonnet, opus, haiku (or with -4 suffix)");
		console.error("\nAlso supported via Pi providers:");
		console.error("  PI_PROVIDER=openai PI_MODEL=gpt-4o");
		console.error("  PI_PROVIDER=google PI_MODEL=gemini-2.5-pro");
		process.exit(1);
	}
	if (guardianAuthorizedMode && (
		authorizedIdentity.harnessId !== harnessId ||
		authorizedIdentity.harnessVersion !== harnessVersion ||
		model.provider !== authorizedIdentity.providerId ||
		model.id !== authorizedIdentity.modelId
	)) {
		emitAuthorizedFailure("authorized_identity_rejected", "identity_verification");
		return;
	}
	const actualRuntimeIdentity = guardianAuthorizedMode
		? {
			actual_provider_id: model.provider,
			actual_model_id: model.id,
			actual_harness_id: harnessId,
			actual_harness_version: harnessVersion,
		}
		: null;

	// Check API key availability
	try {
		const available = await modelRegistry.getAvailable();
		const hasModel = available.some(
			m => m.provider === model.provider && m.id === model.id,
		);
		if (!hasModel) {
			if (guardianAuthorizedMode) {
				emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness", {
					actual_runtime_identity: actualRuntimeIdentity,
					runtime_identity_established: true,
				});
				return;
			}
			console.error(`\nNo API key configured for ${OPTIONS.provider}.`);
			console.error("\nThis wrapper reads the shared Pi auth store at ~/.pi/agent/auth.json.");
			console.error("If you already logged into Pi for this user, make sure Codexify sees the same HOME directory.");
			console.error("\nOtherwise, authenticate with Pi or set the provider API key directly:");
			console.error("  pi /login");
			console.error("\nShared auth is reused automatically; Codexify does not require a separate Pi sign-in.");
			console.error("\nOr set the matching provider API key in your shell.");
			console.error("\nSee: ~/.pi/agent/auth.json for stored credentials");
			process.exit(1);
		}
	} catch (err) {
		if (err.message?.includes("No API key")) {
			if (guardianAuthorizedMode) {
				emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness", {
					actual_runtime_identity: actualRuntimeIdentity,
					runtime_identity_established: true,
				});
				return;
			}
			console.error(`\nNo API key configured for ${OPTIONS.provider}.`);
			console.error("\nThis wrapper reads the shared Pi auth store at ~/.pi/agent/auth.json.");
			console.error("If you already logged into Pi for this user, make sure Codexify sees the same HOME directory.");
			console.error("\nOtherwise, authenticate with Pi or set the provider API key directly:");
			console.error("  pi /login");
			console.error("\nShared auth is reused automatically; Codexify does not require a separate Pi sign-in.");
			console.error("\nOr set the matching provider API key in your shell.");
			console.error("\nSee: ~/.pi/agent/auth.json for stored credentials");
			process.exit(1);
		}
		if (guardianAuthorizedMode) {
			emitAuthorizedFailure("oauth_auth_unavailable", "oauth_readiness", {
				actual_runtime_identity: actualRuntimeIdentity,
				runtime_identity_established: true,
			});
			return;
		}
		throw err;
	}

	// Create session
	let result;
	try {
		result = await createAgentSession({
			cwd: OPTIONS.cwd,
			model,
			thinkingLevel: OPTIONS.thinking,
			authStorage,
			modelRegistry,
			tools,
			sessionManager: SessionManager.inMemory(),
		});
	} catch (error) {
		if (guardianAuthorizedMode) {
			emitAuthorizedFailure("session_initialization_failed", "session_initialization", {
				actual_runtime_identity: actualRuntimeIdentity,
				runtime_identity_established: true,
			});
			return;
		}
		throw error;
	}

	session = result.session;

	// Subscribe to events
	session.subscribe((event) => {
		if (OPTIONS.verbose) {
			if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
				process.stdout.write(event.assistantMessageEvent.delta);
			}
			if (event.type === "tool_execution_start") {
				process.stderr.write(`\n[tool: ${event.toolName}]\n`);
			}
			if (event.type === "agent_end") {
				process.stderr.write("\n[complete]\n");
			}
		}
	});

	// Run the prompt
	const fullPrompt = buildPrompt(mode, prompt);
	try {
		await session.prompt(fullPrompt);
	} catch (error) {
		if (guardianAuthorizedMode) {
			emitAuthorizedFailure(classifyAuthorizedError(error), "provider_request", {
				actual_runtime_identity: actualRuntimeIdentity,
				runtime_identity_established: true,
				session_initialized: true,
				provider_request_started: true,
			});
			return;
		}
		throw error;
	}

	// Get messages and extract JSON
	const messages = session.agent.state.messages;

	// Print final output
	if (guardianAuthorizedMode) {
		const response = extractJsonResponse(messages);
		console.log(JSON.stringify({
			status: "ok",
			summary: "Guardian-authorized Pi task completed",
			actual_runtime_identity: actualRuntimeIdentity,
			execution_result: {
				status: "completed",
				result_kind: response && Object.prototype.hasOwnProperty.call(response, "text")
					? "text"
					: "structured",
				content_omitted: true,
			},
		}));
		return;
	}
	if (mode === "audit" || mode === "compile" || mode === "task") {
		const response = extractJsonResponse(messages);
		if (response) {
			console.log(JSON.stringify(response, null, 2));
		}
	}
}

function buildPrompt(mode, userPrompt) {
	switch (mode) {
		case "audit":
			return userPrompt || "Analyze this repository and output findings as JSON.";
		case "compile":
			return userPrompt || "Compile the audit results into a campaign set JSON.";
		case "task":
			return userPrompt || "Execute the task and output results as JSON.";
		case "guardian-authorized-task":
			return userPrompt || "Execute the authorized task and return bounded evidence.";
		case "help":
		default:
			return null;
	}
}

function extractJsonResponse(messages) {
	// Find the last assistant message
	const assistantMessages = messages.filter(m => m.role === "assistant");
	if (assistantMessages.length === 0) return null;

	const last = assistantMessages[assistantMessages.length - 1];
	if (!last.content) return null;

	// Handle content as array or string
	let text = "";
	if (Array.isArray(last.content)) {
		for (const block of last.content) {
			if (block.type === "text") {
				text += block.text;
			}
		}
	} else if (typeof last.content === "string") {
		text = last.content;
	}

	// Try to extract JSON
	try {
		// Look for JSON code blocks
		const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
		if (jsonMatch) {
			return JSON.parse(jsonMatch[1]);
		}

		// Try direct parse
		const trimmed = text.trim();
		if (trimmed.startsWith("{")) {
			return JSON.parse(trimmed);
		}
	} catch (e) {
		// Not JSON, return the text
		return { text: text.trim() };
	}

	return { text: text.trim() };
}

// Readiness is deliberately non-executing: it imports the adapter, resolves the
// configured model, and asks Pi whether a matching credential is available.
if (mode === "readiness") {
	checkReadiness()
		.then((payload) => console.log(JSON.stringify(payload)))
		.catch(() => console.log(JSON.stringify({
			adapter_initialized: false,
			provider_resolved: false,
			provider_credential_available: false,
			effective_provider: OPTIONS.provider,
			effective_model: OPTIONS.model,
			reason: "adapter_initialization_failed",
		})));
} else if (guardianAuthorizedReadinessMode) {
	checkGuardianAuthorizedReadiness().catch(() => {
		emitAuthorizedFailure("unknown_adapter_failure", "preflight");
	});
} else if (mode === "help" || !prompt) {
	console.log(`
Pi Agent Wrapper for Campaign Runner
====================================

Usage:
  node agent-wrapper.js <mode> [prompt...]

Modes:
  audit    - Run audit analysis on the repository
  compile  - Compile audit results into campaign set
  task     - Execute a single task
	  guardian-authorized-task - Execute one explicitly authorized task with identity attestation
	  guardian-authorized-readiness - Verify authorized runtime/provider/model/auth without a prompt
  readiness - Check adapter and credential posture without executing a prompt
  help     - Show this help

Environment Variables:
  PI_MODEL      - Model to use (default: claude-sonnet-4-20250514)
  PI_PROVIDER   - Provider to use (default: anthropic)
  PI_THINKING   - Thinking level: off, minimal, low, medium, high, xhigh
  PI_VERBOSE    - Set to 1 for verbose output
  PI_DISABLE_TOOLS - Set to 1 to run without coding tools

Model Aliases:
  sonnet, sonnet4, sonnet-4  → claude-sonnet-4-20250514
  opus, opus4, opus-4         → claude-opus-4-5
  haiku, haiku4, haiku-4      → claude-haiku-4

Providers:
  anthropic  - Default, Claude models
  openai     - GPT models
  google     - Gemini models

Authentication:
  Run 'pi /login' to authenticate via OAuth, or set API key:
    export ANTHROPIC_API_KEY=sk-ant-...

Examples:
  # Basic audit
  node agent-wrapper.js audit "Analyze this repo for security issues"

  # Use different model
  PI_MODEL=opus PI_THINKING=high node agent-wrapper.js audit "Thorough review"

  # Compile audit results
  node agent-wrapper.js compile "Generate campaigns from findings"

  # Execute task
  node agent-wrapper.js task "Fix the bug in src/index.ts"
`);
	process.exit(0);
} else {
	// Run
	runAgent().catch(err => {
		if (guardianAuthorizedMode || guardianAuthorizedReadinessMode) {
			emitAuthorizedFailure(classifyAuthorizedError(err), "adapter_execution");
			return;
		}
		console.error("Error:", err.message);
		process.exit(1);
	});
}
