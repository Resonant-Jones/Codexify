#!/usr/bin/env node
// Provider-free harness around the maintained Pi 0.82.1 AgentSession
// recovery path. Used only by tests/pi/test_pi_required_tool_selection.py.
//
// Exercises the real maintained vendored code:
//
//   AgentSession._handlePostAgentRun()
//   AgentSession._checkCompaction()
//   isContextOverflow()            (from @earendil-works/pi-ai/compat)
//   getLatestCompactionEntry()     (from ./session-manager.js)
//   AgentSession._isRetryableError()
//   SettingsManager.getCompactionSettings()
//   SettingsManager.getCompactionEnabled()
//
// The maintained Pi implementation itself decides:
//   - whether the overflow qualifies for compaction (isContextOverflow)
//   - whether compaction is enabled (getCompactionSettings)
//   - whether auto-compaction should run (_checkCompaction -> _runAutoCompaction)
//   - whether continuation should be attempted (return value of
//     _handlePostAgentRun consumed by the recovery loop)
//
// The harness only stubs:
//   - agent.continue() — spy for counting continuation attempts
//   - _runAutoCompaction() — replaced on the instance with a spy
//     (the decision to CALL it is made by maintained _checkCompaction;
//     the stub only counts the call and returns true to simulate
//     successful compaction with retry, which is the compaction
//     summarization side effect the spec explicitly permits stubbing)
//   - sessionManager — minimal mock for branch/context operations
//     (filesystem/session persistence)
//   - extensionRunner — minimal mock
//   - _emit — no-op event sink
//
// Usage:
//   node pi_compaction_recovery_harness.mjs <mode>
//
// Modes:
//   disabled-block  — SettingsManager.compaction.enabled = false
//                     Expected: maintained gate blocks at line 1510,
//                     no _runAutoCompaction call, no agent.continue() call.
//   enabled-trigger — SettingsManager.compaction.enabled = true
//                     Expected: maintained code reaches overflow detection,
//                     calls _runAutoCompaction("overflow", willRetry=true),
//                     recovery loop calls agent.continue() exactly once.
//
// Output: a single JSON line on stdout.

import { AgentSession } from "../../../codex_runner/vendor/pi-coding-agent/dist/core/agent-session.js";
import { SettingsManager } from "../../../codex_runner/vendor/pi-coding-agent/dist/core/settings-manager.js";

const mode = process.argv[2];

if (mode !== "disabled-block" && mode !== "enabled-trigger") {
    console.error(`unknown mode: ${mode}`);
    process.exit(2);
}

function createHarness({ compactionEnabled }) {
    // Real SettingsManager from vendored Pi. The maintained
    // _checkCompaction reads getCompactionSettings() and honors
    // settings.enabled at its gate.
    const settingsManager = SettingsManager.inMemory({
        retry: { enabled: false },
        compaction: { enabled: compactionEnabled },
    });

    let continueCallCount = 0;
    let runAutoCompactionCallCount = 0;
    let runAutoCompactionArgs = null;

    // Minimal agent mock. Only the surface the maintained recovery
    // path actually touches:
    //   - state.messages (compaction may remove the trailing error
    //     message before retry)
    //   - continue() (spied)
    //   - hasQueuedMessages() (checked at the tail of _handlePostAgentRun)
    //   - subscribe() (called by the real AgentSession constructor,
    //     but we bypass the constructor via Object.create)
    const agent = {
        state: { messages: [], tools: [], model: null },
        subscribe: () => () => {},
        continue: async () => {
            continueCallCount += 1;
        },
        hasQueuedMessages: () => false,
        beforeToolCall: null,
        afterToolCall: null,
        prepareNextTurnWithContext: null,
        streamFunction: null,
    };

    // Minimal sessionManager mock. getBranch() is consulted by
    // getLatestCompactionEntry inside _checkCompaction; an empty
    // branch yields null (no prior compaction), which is the
    // expected state for a fresh required-tool session.
    const sessionManager = {
        getBranch: () => [],
        getEntries: () => [],
        buildSessionContext: () => ({ messages: [] }),
        appendCompaction: () => {},
    };

    // model is a getter on AgentSession that reads agent.state.model
    // (see agent-session.js:580). We set the model on agent.state.
    agent.state.model = {
        provider: "anthropic",
        id: "claude-sonnet-4-6",
        contextWindow: 200000,
    };

    // Bypass the AgentSession constructor (which requires a real
    // agent, modelRuntime, and resourceLoader). We use
    // Object.create(AgentSession.prototype) so that _checkCompaction,
    // _handlePostAgentRun, and _isRetryableError are the MAINTAINED
    // methods from vendored Pi — the prototype is not replaced.
    const session = Object.create(AgentSession.prototype);
    session.agent = agent;
    session.sessionManager = sessionManager;
    session.settingsManager = settingsManager;
    session._lastAssistantMessage = undefined;
    session._overflowRecoveryAttempted = false;
    session._retryAttempt = 0;
    session._extensionRunner = {
        hasHandlers: () => false,
        emit: async () => ({}),
    };
    session._autoCompactionAbortController = undefined;
    session._compactionAbortController = undefined;
    session._emit = () => {};

    // Replace _runAutoCompaction on the INSTANCE with a spy. The
    // maintained _checkCompaction decides whether to call it; the
    // spy only counts the call and returns true to simulate a
    // successful compaction with retry. This is the
    // "compaction summarization" side effect the spec explicitly
    // permits stubbing.
    session._runAutoCompaction = async function (reason, willRetry) {
        runAutoCompactionCallCount += 1;
        runAutoCompactionArgs = { reason, willRetry };
        return true;
    };

    return {
        session,
        settingsManager,
        getContinueCallCount: () => continueCallCount,
        getRunAutoCompactionCallCount: () => runAutoCompactionCallCount,
        getRunAutoCompactionArgs: () => runAutoCompactionArgs,
    };
}

// A recognized context-overflow assistant message. The maintained
// isContextOverflow() function in @earendil-works/pi-ai matches the
// Anthropic /prompt is too long/i pattern in OVERFLOW_PATTERNS.
function createOverflowMessage() {
    return {
        role: "assistant",
        stopReason: "error",
        errorMessage: "prompt is too long: 213462 tokens > 200000 maximum",
        provider: "anthropic",
        model: "claude-sonnet-4-6",
        timestamp: Date.now(),
        usage: {
            input: 213462,
            output: 0,
            cacheRead: 0,
            cacheWrite: 0,
        },
    };
}

const h = createHarness({
    compactionEnabled: mode === "enabled-trigger",
});

// Feed the overflow message and simulate the maintained recovery
// loop (the same control flow as _runAgentPrompt's
// `while (await this._handlePostAgentRun()) { await this.agent.continue(); }`).
h.session._lastAssistantMessage = createOverflowMessage();
let iterations = 0;
while (await h.session._handlePostAgentRun()) {
    await h.session.agent.continue();
    iterations += 1;
    if (iterations > 5) {
        // Safety guard; the maintained loop should exit after at
        // most one iteration because _handlePostAgentRun clears
        // _lastAssistantMessage on entry.
        break;
    }
    // Prevent infinite loop: the maintained _handlePostAgentRun
    // clears _lastAssistantMessage on entry, so the next iteration
    // returns false immediately.
    h.session._lastAssistantMessage = undefined;
}

const result = {
    mode,
    compactionEnabled: h.settingsManager.getCompactionEnabled(),
    runAutoCompactionCallCount: h.getRunAutoCompactionCallCount(),
    runAutoCompactionArgs: h.getRunAutoCompactionArgs(),
    continueCallCount: h.getContinueCallCount(),
    iterations,
};

console.log(JSON.stringify(result));
