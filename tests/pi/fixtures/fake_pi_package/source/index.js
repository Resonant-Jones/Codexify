
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
        return [
            {
                provider: RUNTIME_IDENTITY.provider_id,
                id: RUNTIME_IDENTITY.model_id,
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
        this.agent = { state: { messages: [] } };
        this._subscribers = [];
    }

    getActiveToolNames() {
        return this._activeToolNames.slice();
    }

    subscribe(fn) {
        this._subscribers.push(fn);
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
