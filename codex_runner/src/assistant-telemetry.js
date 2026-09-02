// Bounded Pi 0.82.1 assistant-response telemetry observers.
//
// Pure functions used by both the live wrapper and deterministic
// regression tests.  Records only event/block-type names and counts.
// Never retains prompt text, reasoning content, tool arguments,
// tool-call IDs, or provider payloads.
//
// Position contract (do not reorder without updating all consumers):
//   toolTelemetry.assistant_message_count
//   toolTelemetry.assistant_content_block_types
//   toolTelemetry.assistant_message_event_types
//   toolTelemetry.assistant_tool_call_event_count

// Pi-native assistant tool-call lifecycle event names (lowercase 'c' on
// 'toolcall').  These are the bounds used to detect assistant-side
// tool-call lifecycle events on Pi 0.82.1 `message_update` events.
export const PI_ASSISTANT_TOOLCALL_EVENT_TYPES = new Set([
	"toolcall_start",
	"toolcall_delta",
	"toolcall_end",
]);

// Pure bounded observer of Pi 0.82.1 `message_update` assistant events.
// Records only type-name strings.  Never retains text, reasoning,
// arguments, IDs, or payloads.
export function observeAssistantMessageEvent(toolTelemetry, event) {
	if (!event || event.type !== "message_update") return;
	const assistantEvent = event.assistantMessageEvent;
	if (!assistantEvent || typeof assistantEvent.type !== "string") return;
	const eventType = assistantEvent.type;
	if (eventType.length === 0) return;
	if (!toolTelemetry.assistant_message_event_types.includes(eventType)) {
		toolTelemetry.assistant_message_event_types.push(eventType);
	}
	if (PI_ASSISTANT_TOOLCALL_EVENT_TYPES.has(eventType)) {
		toolTelemetry.assistant_tool_call_event_count += 1;
	}
}

// Pure bounded observer of the final Pi 0.82.1 assistant messages.
// Walks `session.agent.state.messages`, counts assistant-role messages,
// collects ordered unique content-block type strings, and counts final
// `toolCall` content blocks.  Never reads text/reasoning/args/IDs.
export function observeFinalAssistantMessages(toolTelemetry, session) {
	try {
		const messages = session?.agent?.state?.messages;
		if (!Array.isArray(messages)) return;
		for (const message of messages) {
			if (!message || message.role !== "assistant") continue;
			toolTelemetry.assistant_message_count += 1;
			if (!Array.isArray(message.content)) continue;
			for (const block of message.content) {
				if (!block || typeof block !== "object") continue;
				if (typeof block.type !== "string" || block.type.length === 0) continue;
				const blockType = block.type;
				if (!toolTelemetry.assistant_content_block_types.includes(blockType)) {
					toolTelemetry.assistant_content_block_types.push(blockType);
				}
				if (block.type === "toolCall") {
					toolTelemetry.assistant_tool_call_count += 1;
				}
			}
		}
	} catch (_error) {
		// bounded evidence only
	}
}

// Create a fresh toolTelemetry accumulator with all 10 bounded fields
// initialized to None / empty.  Used by both the live wrapper and tests.
export function createToolTelemetry() {
	return {
		effective_tool_names: null,
		write_tool_available: null,
		tool_execution_start_count: 0,
		tool_execution_end_count: 0,
		executed_tool_names: [],
		assistant_tool_call_count: 0,
		assistant_message_count: 0,
		assistant_content_block_types: [],
		assistant_message_event_types: [],
		assistant_tool_call_event_count: 0,
	};
}
