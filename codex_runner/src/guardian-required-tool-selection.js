/**
 * Guardian-authorized required-tool selection helper.
 *
 * Pure provider-mechanics projection from a Campaign Engine declared
 * required tool into a concrete provider request parameter. No I/O, no
 * credentials, no environment access, no global mutation. The helper
 * never modifies model/messages/system/thinking/output_config/tools/
 * max_tokens/stream/metadata; it only adds or validates a `tool_choice`
 * block on the first provider payload of the first authorized turn.
 *
 * Initial supported provider: anthropic.
 * Initial supported required tool: "write".
 *
 * The exact advertised outbound spelling of the required tool (e.g. the
 * lower-case "write" emitted by the API-key branch, or the Claude-Code
 * casing "Write" emitted by the OAuth compatibility layer) is preserved
 * in the resulting `tool_choice.name`.
 */

const SUPPORTED_PROVIDERS = new Set(["anthropic"]);
const SUPPORTED_REQUIRED_TOOLS = new Set(["write"]);

const ERR = {
	NOT_OBJECT: "guard.required_tool_selection.invalid_payload",
	MISSING_TOOLS: "guard.required_tool_selection.no_tools",
	MISSING_REQUIRED: "guard.required_tool_selection.missing_advertised",
	DUPLICATE_REQUIRED: "guard.required_tool_selection.duplicate_advertised",
	CONFLICTING_CHOICE: "guard.required_tool_selection.conflicting_choice",
	UNSUPPORTED_PROVIDER: "guard.required_tool_selection.unsupported_provider",
	UNSUPPORTED_TOOL: "guard.required_tool_selection.unsupported_required_tool",
};

class RequiredToolSelectionError extends Error {
	constructor(code) {
		super(code);
		this.name = "RequiredToolSelectionError";
		this.code = code;
	}
}

function _asObject(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function _findAdvertisedRequiredTool(tools, requiredToolLower) {
	// Case-insensitive match preserving first-occurrence order. The
	// canonical required tool is the unique advertised tool whose
	// lowercased name equals the required tool token. Returns the
	// exact advertised spelling (casing preserved).
	if (!Array.isArray(tools) || tools.length === 0) {
		return null;
	}
	let match = null;
	let duplicates = 0;
	for (const tool of tools) {
		if (!_asObject(tool)) {
			continue;
		}
		const name = tool.name;
		if (typeof name !== "string" || name.length === 0) {
			continue;
		}
		if (name.toLowerCase() !== requiredToolLower) {
			continue;
		}
		if (match === null) {
			match = name;
		} else {
			duplicates += 1;
		}
	}
	if (match === null) {
		return { kind: "missing" };
	}
	if (duplicates > 0) {
		return { kind: "duplicate" };
	}
	return { kind: "found", advertised: match };
}

/**
 * Apply the bounded required-tool selection to a provider payload.
 *
 * Returns a shallow copy of the input payload with `tool_choice`
 * added. The helper never mutates the caller's input.
 *
 * Behavior contract:
 *
 * - providerId must be a non-empty string in `SUPPORTED_PROVIDERS`.
 * - requiredToolName must be a non-empty string in
 *   `SUPPORTED_REQUIRED_TOOLS`.
 * - payload must be a plain object with a `tools` array.
 * - exactly one advertised tool must match the required tool
 *   case-insensitively; multiple matches fail closed.
 * - if `payload.tool_choice` is already present, it must name the same
 *   exact advertised required tool; otherwise the helper fails closed.
 * - the helper returns a NEW shallow-copied payload with the
 *   `tool_choice` set; it never mutates the input.
 */
export function applyGuardianRequiredToolSelection({
	providerId,
	requiredToolName,
	payload,
}) {
	if (typeof providerId !== "string" || !SUPPORTED_PROVIDERS.has(providerId)) {
		throw new RequiredToolSelectionError(ERR.UNSUPPORTED_PROVIDER);
	}
	if (
		typeof requiredToolName !== "string" ||
		!SUPPORTED_REQUIRED_TOOLS.has(requiredToolName)
	) {
		throw new RequiredToolSelectionError(ERR.UNSUPPORTED_TOOL);
	}
	if (!_asObject(payload)) {
		throw new RequiredToolSelectionError(ERR.NOT_OBJECT);
	}
	if (!Array.isArray(payload.tools)) {
		throw new RequiredToolSelectionError(ERR.MISSING_TOOLS);
	}
	const result = _findAdvertisedRequiredTool(payload.tools, requiredToolName);
	if (result.kind === "missing") {
		throw new RequiredToolSelectionError(ERR.MISSING_REQUIRED);
	}
	if (result.kind === "duplicate") {
		throw new RequiredToolSelectionError(ERR.DUPLICATE_REQUIRED);
	}
	const advertised = result.advertised;
	const copied = { ...payload };
	if (Object.prototype.hasOwnProperty.call(copied, "tool_choice")) {
		const existing = copied.tool_choice;
		const existingName =
			_asObject(existing) && typeof existing.name === "string"
				? existing.name
				: null;
		if (existingName !== advertised) {
			throw new RequiredToolSelectionError(ERR.CONFLICTING_CHOICE);
		}
		// Existing choice already names the same exact advertised tool.
		return copied;
	}
	copied.tool_choice = { type: "tool", name: advertised };
	return copied;
}

/**
 * Canonical supported required-tool set, exported for tests.
 */
export const SUPPORTED_REQUIRED_TOOL_NAMES = Object.freeze(
	Array.from(SUPPORTED_REQUIRED_TOOLS)
);

/**
 * Canonical supported provider set for required-tool selection, exported
 * for tests.
 */
export const SUPPORTED_PROVIDER_IDS = Object.freeze(
	Array.from(SUPPORTED_PROVIDERS)
);

/**
 * Bounded error code allowlist (no payload content). Useful for tests
 * and for documentation. Not required by callers; thrown errors carry
 * the code on the `code` property.
 */
export const REQUIRED_TOOL_SELECTION_ERROR_CODES = Object.freeze(Object.values(ERR));

export { RequiredToolSelectionError };
