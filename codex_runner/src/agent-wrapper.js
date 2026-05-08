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
 */

// Parse command line args
const args = process.argv.slice(2);
const mode = args[0] || "help";
const prompt = args.slice(1).join(" ");

const OPTIONS = {
	cwd: process.cwd(),
	model: process.env.PI_MODEL || "claude-sonnet-4-20250514",
	provider: process.env.PI_PROVIDER || "anthropic",
	thinking: process.env.PI_THINKING || "medium",
	verbose: process.env.PI_VERBOSE === "1",
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

async function loadPiSdk() {
	const codingAgent = await import(new URL("../vendor/pi-coding-agent/dist/index.js", import.meta.url).href);
	const piAi = await import(
		new URL("../vendor/pi-coding-agent/node_modules/@mariozechner/pi-ai/dist/index.js", import.meta.url).href
	);
	return {
		createAgentSession: codingAgent.createAgentSession,
		SessionManager: codingAgent.SessionManager,
		AuthStorage: codingAgent.AuthStorage,
		ModelRegistry: codingAgent.ModelRegistry,
		createCodingTools: codingAgent.createCodingTools,
		getModel: piAi.getModel,
	};
}

async function runAgent() {
	let createAgentSession;
	let SessionManager;
	let AuthStorage;
	let ModelRegistry;
	let createCodingTools;
	let getModel;

	try {
		({
			createAgentSession,
			SessionManager,
			AuthStorage,
			ModelRegistry,
			createCodingTools,
			getModel,
		} = await loadPiSdk());
	} catch (error) {
		if (isModuleResolutionError(error)) {
			console.error("Pi SDK dependencies are not available in this Node environment.");
			console.error("The repo expects a vendored copy under codex_runner/vendor/pi-coding-agent.");
			console.error("If that tree is missing or incomplete, restore the checkout or refresh the vendored package.");
			console.error("Shared Pi auth still reuses ~/.pi/agent/auth.json once the SDK is present.");
			process.exit(1);
		}
		throw error;
	}

	const resolvedModelId = resolveModel(OPTIONS.model, getModel);

	// Set up auth and model registry
	const authStorage = AuthStorage.create();
	const modelRegistry = ModelRegistry.create(authStorage);

	// Create default coding tools
	const tools = createCodingTools(OPTIONS.cwd);

	// Get model
	const model = getModel(OPTIONS.provider, resolvedModelId);
	if (!model) {
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

	// Check API key availability
	try {
		const available = await modelRegistry.getAvailable();
		const hasModel = available.some(m => m.id === model.id);
		if (!hasModel) {
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
	}

	// Create session
	const result = await createAgentSession({
		cwd: OPTIONS.cwd,
		model,
		thinkingLevel: OPTIONS.thinking,
		authStorage,
		modelRegistry,
		tools,
		sessionManager: SessionManager.inMemory(),
	});

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
	await session.prompt(fullPrompt);

	// Get messages and extract JSON
	const messages = session.agent.state.messages;

	// Print final output
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

// Help output
if (mode === "help" || !prompt) {
	console.log(`
Pi Agent Wrapper for Campaign Runner
====================================

Usage:
  node agent-wrapper.js <mode> [prompt...]

Modes:
  audit    - Run audit analysis on the repository
  compile  - Compile audit results into campaign set
  task     - Execute a single task
  help     - Show this help

Environment Variables:
  PI_MODEL      - Model to use (default: claude-sonnet-4-20250514)
  PI_PROVIDER   - Provider to use (default: anthropic)
  PI_THINKING   - Thinking level: off, minimal, low, medium, high, xhigh
  PI_VERBOSE    - Set to 1 for verbose output

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
}

// Run
runAgent().catch(err => {
	console.error("Error:", err.message);
	process.exit(1);
});
