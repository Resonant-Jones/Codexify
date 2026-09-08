
// Provider-free fake Pi 0.82.1 package used only by tests.
// No network. No real provider SDK. No socket. No DNS.
// Resolves provider/model entirely in memory.

const RUNTIME_IDENTITY = {
    provider_id: "openai-codex",
    model_id: "gpt-5.6-sol",
    harness_id: "pi-coding-agent",
    harness_version: "0.82.1",
};

class FakeModelRuntime {
    constructor() {
        this._allowModelNetwork = false;
    }

    getModel(providerId, modelId) {
        return {
            provider: providerId || RUNTIME_IDENTITY.provider_id,
            id: modelId || RUNTIME_IDENTITY.model_id,
            baseUrl: "in-memory://fake-pi-runtime",
        };
    }

    getProviders() {
        return [RUNTIME_IDENTITY.provider_id];
    }

    checkAuth(providerId) {
        return {
            provider: providerId,
            mode: "in-memory-fixture",
            authenticated: true,
        };
    }

    getAvailable() {
        // Honor the configured provider/model so a Guardian-authorized
        // call with PI_PROVIDER=anthropic is not rejected as
        // oauth_auth_unavailable. The fake is provider-free; the
        // available list therefore mirrors whatever the wrapper
        // requested when the provider/model pair is recognized.
        const provider = process.env.PI_PROVIDER || RUNTIME_IDENTITY.provider_id;
        const model = process.env.PI_MODEL || RUNTIME_IDENTITY.model_id;
        return [
            {
                provider,
                id: model,
            },
        ];
    }
}

const FakeModelRuntimeFactory = {
    async create(opts = {}) {
        const runtime = new FakeModelRuntime();
        runtime._allowModelNetwork = opts.allowModelNetwork === true;
        return runtime;
    },
};

class FakeSessionManager {
    static inMemory() {
        return {
            kind: "in-memory",
            save: async () => {},
        };
    }
}

class FakeSession {
    constructor(options = {}) {
        this.options = options;
        // Behavior knob selected by the test via the subprocess env.
        // Default: success.
        this.behavior = process.env.PI_FAKE_I_BEHAVIOR || "success";
        this._activeToolNames = ["read", "bash", "edit", "write"];
        this.agent = {
            state: { messages: [], tools: [] },
            onPayload: null,
        };
        this._subscribers = [];
    }

    getActiveToolNames() {
        return this._activeToolNames.slice();
    }

    subscribe(fn) {
        this._subscribers.push(fn);
    }

    _emitSubscribers(event) {
        for (const sub of this._subscribers) {
            try {
                sub(event);
            } catch (_error) {
                // bounded evidence only; never crash on subscriber error
            }
        }
    }

    _buildFirstPayload() {
        // The fake advertises tool names. The naming convention is
        // selected by the test via PI_FAKE_ADVERTISE_CASING.
        const casing = process.env.PI_FAKE_ADVERTISE_CASING || "lowercase";
        const names = casing === "claude-code" ? ["Read", "Bash", "Edit", "Write"] : ["read", "bash", "edit", "write"];
        return {
            model: "claude-sonnet-4-6",
            messages: [
                { role: "user", content: [{ type: "text", text: "synthetic" }] },
            ],
            max_tokens: 1024,
            stream: true,
            tools: names.map((name) => ({ name })),
            thinking: { type: "adaptive", display: "summarized" },
            output_config: { effort: "medium" },
        };
    }

    async prompt(prompt) {
        // Write one diagnostic line to stdout BEFORE the canonical
        // wrapper writes its terminal JSON. This exercises the framing
        // repair end-to-end against the real agent-wrapper.js.
        process.stdout.write("FAKE_PI_SDK_DIAGNOSTIC\n");

        if (this.behavior === "failure") {
            // Raise a synthetic provider-request error so the real
            // wrapper emits its bounded failure JSON.
            throw new Error("synthetic provider request failure");
        }

        // The fake exposes the wrapper's per-session onPayload hook.
        // The first prompt() invocation is treated as the FIRST provider
        // turn; we drive the wrapper's hook with a synthetic payload so
        // it can apply the bounded required-tool projection. A second
        // invocation, if requested, is the continuation turn and
        // carries no projection.
        const params = this._buildFirstPayload();
        let onPayload = this.agent.onPayload;
        for (let turn = 0; turn < 2; turn += 1) {
            if (typeof onPayload === "function") {
                const projected = onPayload(params, {
                    provider: "anthropic",
                    id: "claude-sonnet-4-6",
                });
                if (projected !== undefined && projected !== null) {
                    params.model = projected.model || params.model;
                    params.tools = projected.tools || params.tools;
                    params.tool_choice = projected.tool_choice;
                }
            }
            // Only the first turn is a "provider request" in this fake;
            // a second invocation just records the post-tool continuation
            // and exits.
        }

        if (this.behavior === "assistant-tool-call") {
            // Emit the bounded Pi 0.82.1 event sequence the live
            // wrapper's `observeAssistantMessageEvent` and tool
            // execution counters consume.  No payload content is
            // carried; only event-type names.
            this._emitSubscribers({
                type: "message_update",
                assistantMessageEvent: { type: "toolcall_start" },
            });
            this._emitSubscribers({
                type: "tool_execution_start",
                toolName: "write",
            });
            this._emitSubscribers({
                type: "tool_execution_end",
                toolName: "write",
            });
            this._emitSubscribers({
                type: "message_update",
                assistantMessageEvent: { type: "toolcall_end" },
            });
            // Set the final session state to one assistant message
            // with one `toolCall` content block whose argument is
            // secret-shaped.  The bounded observer MUST NOT return
            // this value; the test proves it.
            this.agent.state.messages = [
                {
                    role: "assistant",
                    content: [
                        {
                            type: "toolCall",
                            name: "write",
                            arguments: "secret-not-returned",
                        },
                    ],
                },
            ];
            return;
        }

        // No-op for success; the canonical wrapper emits success JSON
        // after this returns.
    }

    abort() {}
}

async function fakeCreateAgentSession(options = {}) {
    const session = new FakeSession(options);
    return { session };
}

export const ModelRuntime = FakeModelRuntimeFactory;
export const createAgentSession = fakeCreateAgentSession;
export const SessionManager = FakeSessionManager;
