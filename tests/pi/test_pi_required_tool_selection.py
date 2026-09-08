"""Provider-free required-tool selection regression suite.

Covers three layers:

1. Pure projection helper (Node ES module imported via subprocess).
2. Real vendored Anthropic request-builder integration (inert synthetic
   credentials, local sentinel prevents network).
3. Real wrapper subprocess against the tracked fake Pi package.

No provider, no network, no real credentials.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths and helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HELPER_PATH = REPO_ROOT / "codex_runner" / "src" / "guardian-required-tool-selection.js"
WRAPPER_PATH = REPO_ROOT / "codex_runner" / "src" / "agent-wrapper.js"
FAKE_SOURCE_DIR = REPO_ROOT / "tests" / "pi" / "fixtures" / "fake_pi_package"
FAKE_SOURCE_INDEX = FAKE_SOURCE_DIR / "source" / "index.js"
FAKE_PACKAGE_JSON = FAKE_SOURCE_DIR / "package.json"
VENDORED_ANTHROPIC = (
    REPO_ROOT
    / "codex_runner"
    / "vendor"
    / "pi-coding-agent"
    / "node_modules"
    / "@earendil-works"
    / "pi-ai"
    / "dist"
    / "api"
    / "anthropic-messages.js"
)


def _node_eval_helper(script: str) -> dict:
    """Run a small Node script that imports the helper and returns JSON."""
    cmd = ["node", "--input-type=module", "-e", script]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"helper subprocess failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def _import_helper() -> str:
    """Return a Node import prelude that loads the helper module."""
    return (
        f"import {{ applyGuardianRequiredToolSelection, "
        f"RequiredToolSelectionError }} from "
        f"{json.dumps(str(HELPER_PATH))};\n"
    )


# ---------------------------------------------------------------------------
# 1. Pure projection helper
# ---------------------------------------------------------------------------


def test_helper_lowercase_advertised_write_selected() -> None:
    """Anthropic lowercase advertised tools: helper selects `write`."""
    script = _import_helper() + """
        const out = applyGuardianRequiredToolSelection({
            providerId: "anthropic",
            requiredToolName: "write",
            payload: {
                model: "claude-sonnet-4-6",
                tools: [
                    { name: "read" },
                    { name: "bash" },
                    { name: "edit" },
                    { name: "write" },
                ],
            },
        });
        process.stdout.write(JSON.stringify({
            tool_choice: out.tool_choice ?? null,
            tool_names: out.tools.map(t => t.name),
            input_unmodified_keys: [
                "model", "messages", "system", "thinking",
                "output_config", "max_tokens", "stream", "metadata",
            ].filter(k => k in out),
        }));
        """
    out = _node_eval_helper(script)
    assert out["tool_choice"] == {"type": "tool", "name": "write"}
    assert out["tool_names"] == ["read", "bash", "edit", "write"]


def test_helper_claude_code_casing_selected() -> None:
    """Anthropic Claude-Code casing: helper selects `Write` (exact casing)."""
    script = _import_helper() + """
        const out = applyGuardianRequiredToolSelection({
            providerId: "anthropic",
            requiredToolName: "write",
            payload: {
                tools: [
                    { name: "Read" },
                    { name: "Bash" },
                    { name: "Edit" },
                    { name: "Write" },
                ],
            },
        });
        process.stdout.write(JSON.stringify({
            tool_choice: out.tool_choice,
        }));
        """
    out = _node_eval_helper(script)
    assert out["tool_choice"] == {"type": "tool", "name": "Write"}


def test_helper_existing_matching_choice_accepted() -> None:
    """Existing matching choice: helper accepts the same exact advertised tool."""
    script = _import_helper() + """
        const out = applyGuardianRequiredToolSelection({
            providerId: "anthropic",
            requiredToolName: "write",
            payload: {
                tools: [{ name: "write" }],
                tool_choice: { type: "tool", name: "write" },
            },
        });
        process.stdout.write(JSON.stringify({ tool_choice: out.tool_choice }));
        """
    out = _node_eval_helper(script)
    assert out["tool_choice"] == {"type": "tool", "name": "write"}


def test_helper_existing_conflicting_choice_fails_closed() -> None:
    """Existing conflicting choice: helper fails closed with a bounded code."""
    script = _import_helper() + """
        let code = null;
        try {
            applyGuardianRequiredToolSelection({
                providerId: "anthropic",
                requiredToolName: "write",
                payload: {
                    tools: [{ name: "write" }],
                    tool_choice: { type: "tool", name: "read" },
                },
            });
        } catch (e) {
            code = e && e.code;
        }
        process.stdout.write(JSON.stringify({ code }));
        """
    out = _node_eval_helper(script)
    assert out["code"] == "guard.required_tool_selection.conflicting_choice"


def test_helper_missing_write_fails_closed() -> None:
    """Missing write: helper fails closed with a bounded code."""
    script = _import_helper() + """
        let code = null;
        try {
            applyGuardianRequiredToolSelection({
                providerId: "anthropic",
                requiredToolName: "write",
                payload: { tools: [{ name: "read" }, { name: "bash" }] },
            });
        } catch (e) {
            code = e && e.code;
        }
        process.stdout.write(JSON.stringify({ code }));
        """
    out = _node_eval_helper(script)
    assert out["code"] == "guard.required_tool_selection.missing_advertised"


def test_helper_duplicate_write_fails_closed() -> None:
    """Duplicate case-insensitive write: helper fails closed."""
    script = _import_helper() + """
        let code = null;
        try {
            applyGuardianRequiredToolSelection({
                providerId: "anthropic",
                requiredToolName: "write",
                payload: {
                    tools: [
                        { name: "write" },
                        { name: "Write" },
                    ],
                },
            });
        } catch (e) {
            code = e && e.code;
        }
        process.stdout.write(JSON.stringify({ code }));
        """
    out = _node_eval_helper(script)
    assert out["code"] == "guard.required_tool_selection.duplicate_advertised"


def test_helper_unsupported_provider_fails_closed() -> None:
    """Unsupported provider: helper fails closed."""
    script = _import_helper() + """
        let code = null;
        try {
            applyGuardianRequiredToolSelection({
                providerId: "openai-codex",
                requiredToolName: "write",
                payload: { tools: [{ name: "write" }] },
            });
        } catch (e) {
            code = e && e.code;
        }
        process.stdout.write(JSON.stringify({ code }));
        """
    out = _node_eval_helper(script)
    assert out["code"] == "guard.required_tool_selection.unsupported_provider"


def test_helper_does_not_modify_unrelated_payload_fields() -> None:
    """Helper does not modify unrelated payload fields (deep-equality)."""
    payload = {
        "model": "claude-sonnet-4-6",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "x"}]}],
        "system": "synthetic",
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": "medium"},
        "max_tokens": 1024,
        "stream": True,
        "metadata": {"user_id": "synthetic"},
        "tools": [
            {"name": "read"},
            {"name": "bash"},
            {"name": "edit"},
            {"name": "write"},
        ],
    }
    script = _import_helper() + f"""
        const original = {json.dumps(payload)};
        const out = applyGuardianRequiredToolSelection({{
            providerId: "anthropic",
            requiredToolName: "write",
            payload: original,
        }});
        const fields = [
            "model", "messages", "system", "thinking",
            "output_config", "max_tokens", "stream", "metadata", "tools"
        ];
        const result = {{}};
        for (const f of fields) {{
            result[f] = JSON.stringify(out[f]) === JSON.stringify(original[f]);
        }}
        result.tool_choice_added = JSON.stringify(out.tool_choice) === JSON.stringify({{
            type: "tool", name: "write"
        }});
        result.input_was_unchanged_object = Object.keys(original).every(k => out[k] !== original[k] || true);
        process.stdout.write(JSON.stringify(result));
        """
    out = _node_eval_helper(script)
    for field in [
        "model",
        "messages",
        "system",
        "thinking",
        "output_config",
        "max_tokens",
        "stream",
        "metadata",
        "tools",
    ]:
        assert out[field] is True, f"field {field!r} was modified"
    assert out["tool_choice_added"] is True


# ---------------------------------------------------------------------------
# 2. Adaptive-thinking preservation
# ---------------------------------------------------------------------------


def test_helper_preserves_adaptive_thinking_and_effort() -> None:
    """Helper must not modify thinking/output_config even with adaptive thinking."""
    payload = {
        "model": "claude-sonnet-4-6",
        "tools": [
            {"name": "read"},
            {"name": "bash"},
            {"name": "edit"},
            {"name": "write"},
        ],
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": "medium"},
    }
    script = _import_helper() + f"""
        const original = {json.dumps(payload)};
        const out = applyGuardianRequiredToolSelection({{
            providerId: "anthropic",
            requiredToolName: "write",
            payload: original,
        }});
        process.stdout.write(JSON.stringify({{
            thinking: out.thinking,
            output_config: out.output_config,
            tool_choice: out.tool_choice,
        }}));
        """
    out = _node_eval_helper(script)
    assert out["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert out["output_config"] == {"effort": "medium"}
    assert out["tool_choice"] == {"type": "tool", "name": "write"}


# ---------------------------------------------------------------------------
# 3. Real vendored Anthropic request-builder integration
# ---------------------------------------------------------------------------


def _run_vendored_request_builder(
    *,
    advertise_casing: str,
    api_key: str,
) -> dict:
    """Drive the vendored Anthropic request-builder with our helper, sentinel-stops."""
    if not VENDORED_ANTHROPIC.exists():
        pytest.skip(f"vendored Anthropic adapter not present at {VENDORED_ANTHROPIC}")

    script = f"""
    import {{ pathToFileURL }} from "node:url";
    import {{ readFileSync }} from "node:fs";
    const anthropicMod = await import(
        pathToFileURL({json.dumps(str(VENDORED_ANTHROPIC))}).href
    );
    const toolsMod = await import(
        pathToFileURL({json.dumps(str(
            REPO_ROOT / "codex_runner/vendor/pi-coding-agent/dist/core/tools/index.js"
        ))}).href
    );
    const modelRuntimeMod = await import(
        pathToFileURL({json.dumps(str(
            REPO_ROOT / "codex_runner/vendor/pi-coding-agent/dist/index.js"
        ))}).href
    );
    const {{ ModelRuntime }} = modelRuntimeMod;
    const {{ applyGuardianRequiredToolSelection }} = await import(
        pathToFileURL({json.dumps(str(HELPER_PATH))}).href
    );
    const runtime = await ModelRuntime.create({{ allowModelNetwork: false }});
    const model = runtime.getModel("anthropic", "claude-sonnet-4-6");
    const tools = [
        toolsMod.createReadToolDefinition(),
        toolsMod.createBashToolDefinition(),
        toolsMod.createEditToolDefinition(),
        toolsMod.createWriteToolDefinition(),
    ];
    const advertised = {json.dumps(advertise_casing)};
    const apiKey = {json.dumps(api_key)};
    const context = {{
        systemPrompt: "synthetic",
        messages: [{{ role: "user", content: [{{ type: "text", text: "x" }}] }}],
        tools: tools,
    }};
    let captured = null;
    const onPayload = (params, m) => {{
        // Apply the new helper
        const projected = applyGuardianRequiredToolSelection({{
            providerId: m.provider,
            requiredToolName: "write",
            payload: params,
        }});
        captured = {{
            request_model: m.id,
            request_tool_count: projected.tools ? projected.tools.length : 0,
            request_tool_names: projected.tools
                ? projected.tools.map(t => t.name)
                : [],
            tool_choice_present: Object.prototype.hasOwnProperty.call(
                projected, "tool_choice"
            ),
            tool_choice_value: projected.tool_choice ?? null,
            thinking_type: projected.thinking ? projected.thinking.type : null,
            effort: projected.output_config ? projected.output_config.effort : null,
        }};
        // Throw the sentinel to halt before network.
        throw new Error("__SENTINEL_STOP_NO_NETWORK__");
    }};
    const stream = runtime.streamSimple(model, context, {{apiKey: apiKey, reasoning: "medium", onPayload: onPayload}});
    let sentinelCaught = false;
    let errMsg = null;
    try {{
        for await (const event of stream) {{
            if (event && event.type === "error") {{
                errMsg = event.error && event.error.errorMessage;
                if (errMsg && /SENTINEL_STOP_NO_NETWORK/.test(String(errMsg))) {{
                    sentinelCaught = true;
                }}
                break;
            }}
        }}
    }} catch (e) {{
        errMsg = e && e.message;
        if (errMsg && /SENTINEL_STOP_NO_NETWORK/.test(String(errMsg))) {{
            sentinelCaught = true;
        }}
    }}
    process.stdout.write(JSON.stringify({{
        captured,
        sentinel_caught: sentinelCaught,
        err: errMsg && !sentinelCaught ? String(errMsg) : null,
    }}));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"vendored request-builder failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_vendored_anthropic_api_key_branch_tool_choice_write() -> None:
    """Real vendored Anthropic adapter (API-key branch) emits tool_choice.write."""
    out = _run_vendored_request_builder(
        advertise_casing="lowercase",
        api_key="sk-ant-provider-free-selection-probe",
    )
    assert out["sentinel_caught"] is True
    cap = out["captured"]
    assert cap is not None
    assert cap["request_model"] == "claude-sonnet-4-6"
    assert cap["request_tool_count"] == 4
    assert cap["request_tool_names"] == ["read", "bash", "edit", "write"]
    assert cap["tool_choice_value"] == {"type": "tool", "name": "write"}
    assert cap["thinking_type"] == "adaptive"
    assert cap["effort"] == "medium"


def test_vendored_anthropic_oauth_branch_tool_choice_Write() -> None:
    """Real vendored Anthropic adapter (OAuth branch) emits tool_choice.Write."""
    out = _run_vendored_request_builder(
        advertise_casing="claude-code",
        api_key="sk-ant-oat-provider-free-selection-probe",
    )
    assert out["sentinel_caught"] is True
    cap = out["captured"]
    assert cap is not None
    assert cap["request_tool_count"] == 4
    assert cap["request_tool_names"] == ["Read", "Bash", "Edit", "Write"]
    assert cap["tool_choice_value"] == {"type": "tool", "name": "Write"}
    assert cap["thinking_type"] == "adaptive"
    assert cap["effort"] == "medium"


# ---------------------------------------------------------------------------
# 4. Real wrapper + tracked fake Pi integration
# ---------------------------------------------------------------------------


def _materialize_fake_pi_package(tmp_path: Path) -> Path:
    package_root = tmp_path / "fake_pi_package"
    (package_root / "dist").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FAKE_PACKAGE_JSON, package_root / "package.json")
    shutil.copyfile(FAKE_SOURCE_INDEX, package_root / "dist" / "index.js")
    return package_root


def _run_real_wrapper(
    materialized_fake_pi: Path,
    *,
    fake_home: Path,
    cwd: Path,
    advertise_casing: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(fake_home),
        "TMPDIR": str(cwd),
        "PI_CODING_AGENT_PACKAGE_ROOT": str(materialized_fake_pi),
        "PI_PROVIDER": "anthropic",
        "PI_MODEL": "claude-sonnet-4-6",
        "PI_GUARDIAN_AUTHORIZED": "1",
        "PI_GUARDIAN_HARNESS_ID": "pi-coding-agent",
        "PI_GUARDIAN_HARNESS_VERSION": "0.82.1",
        "PI_DISABLE_TOOLS": "0",
        "PI_FAKE_ADVERTISE_CASING": advertise_casing,
    }
    if extra_env:
        env.update(extra_env)
    # Always exercise the bounded one-write lifecycle so the wrapper's
    # 10-field tool_telemetry and selection evidence are both populated.
    env.setdefault("PI_FAKE_I_BEHAVIOR", "assistant-tool-call")
    return subprocess.run(
        ["node", str(WRAPPER_PATH), "guardian-authorized-task", "fixture prompt"],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.skipif(
    not FAKE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_required_tool_lowercase_write(tmp_path: Path) -> None:
    """Real wrapper + fake Pi: API-key-style naming yields tool_choice.write."""
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _run_real_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        advertise_casing="lowercase",
        extra_env={"PI_GUARDIAN_REQUIRED_TOOL": "write"},
    )
    assert (
        result.returncode == 0
    ), f"wrapper failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    assert parsed["status"] == "ok"
    sel = parsed.get("required_tool_selection")
    assert sel is not None
    assert sel["required_tool_name"] == "write"
    assert sel["hard_tool_selection_applied"] is True
    assert sel["hard_tool_selection_application_count"] == 1
    # ten-field telemetry preserved
    tt = parsed["tool_telemetry"]
    assert tt["effective_tool_names"] == ["read", "bash", "edit", "write"]
    assert tt["write_tool_available"] is True
    assert tt["tool_execution_start_count"] == 1
    assert tt["tool_execution_end_count"] == 1
    assert tt["executed_tool_names"] == ["write"]
    assert tt["assistant_tool_call_count"] == 1


@pytest.mark.skipif(
    not FAKE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_required_tool_claude_code_casing(tmp_path: Path) -> None:
    """Real wrapper + fake Pi: OAuth-style naming yields tool_choice.Write."""
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _run_real_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        advertise_casing="claude-code",
        extra_env={"PI_GUARDIAN_REQUIRED_TOOL": "write"},
    )
    assert (
        result.returncode == 0
    ), f"wrapper failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    assert parsed["status"] == "ok"
    sel = parsed.get("required_tool_selection")
    assert sel is not None
    assert sel["required_tool_name"] == "write"
    assert sel["hard_tool_selection_applied"] is True
    assert sel["hard_tool_selection_application_count"] == 1
    # Tool name casing preserved per the OAuth compatibility layer; the
    # bounded wrapper evidence records the canonical required_tool_name
    # ("write") and the application count (1), not the outbound casing.
    # The outbound casing is observable only via the request-shape
    # capture (covered by test_vendored_anthropic_oauth_branch_*).
    tt = parsed["tool_telemetry"]
    # The session's effective tool names are the application's tool
    # names (always lowercase); only the outbound advertised provider
    # tool names change between API-key and OAuth casings.
    assert tt["effective_tool_names"] == ["read", "bash", "edit", "write"]
    assert tt["write_tool_available"] is True
    assert tt["tool_execution_start_count"] == 1
    assert tt["tool_execution_end_count"] == 1
    assert tt["executed_tool_names"] == ["write"]
    assert tt["assistant_tool_call_count"] == 1


# ---------------------------------------------------------------------------
# 5. Async Pi payload-hook chaining regression
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not FAKE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_chains_preexisting_async_onpayload(tmp_path: Path) -> None:
    """Real wrapper + fake Pi with a pre-existing ASYNC onPayload hook.

    Reproduces the real Pi 0.82.1 session-level `Agent.onPayload`
    contract: the vendored SDK installs an `async` hook on the
    session agent. The wrapper's installed hook must therefore
    also be async and must `await` the previous hook before
    applying the bounded required-tool projection.

    Failure mode that this test proves absent:

    * With the pre-repair synchronous wrapper, the chain captured
      a Promise from the previous async hook, treated that Promise
      as the effective payload, and the projection helper failed
      closed with `guard.required_tool_selection.no_tools`. The
      wrapper's outer protocol layer then emitted a
      `wrapper_protocol_failed` / `tool_selection` failure instead
      of the success terminal payload.

    * With the async-hook repair, the wrapper awaits the previous
      hook, observes the resolved provider payload, and applies
      `tool_choice.write` exactly once.
    """
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _run_real_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        advertise_casing="lowercase",
        extra_env={
            "PI_GUARDIAN_REQUIRED_TOOL": "write",
            # Activate the bounded pre-existing async onPayload knob
            # on the tracked fake Pi fixture. With this knob unset,
            # the fake exposes `onPayload: null` and the existing
            # tests above exercise that historical shape.
            "PI_FAKE_PRE_EXISTING_ASYNC_ONPAYLOAD": "1",
        },
    )
    assert (
        result.returncode == 0
    ), f"wrapper failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    # Bounded required-tool selection evidence is exposed in a
    # separate top-level key (never inside the ten-field
    # tool_telemetry object).
    assert (
        parsed["status"] == "ok"
    ), f"expected successful terminal JSON; got: {parsed!r}"
    sel = parsed.get("required_tool_selection")
    assert sel is not None, (
        "required_tool_selection evidence missing from terminal JSON; "
        "the wrapper did not apply the bounded required-tool projection."
    )
    assert sel["required_tool_name"] == "write"
    assert sel["hard_tool_selection_applied"] is True
    assert sel["hard_tool_selection_application_count"] == 1
    # The pre-existing async hook must be awaited exactly once; the
    # second iteration in the fake exercises the continuation turn
    # which the wrapper's hook treats as a no-op (returns the
    # effective payload unchanged).
    tt = parsed["tool_telemetry"]
    assert tt["effective_tool_names"] == ["read", "bash", "edit", "write"]
    assert tt["write_tool_available"] is True
    assert tt["tool_execution_start_count"] == 1
    assert tt["tool_execution_end_count"] == 1
    assert tt["executed_tool_names"] == ["write"]
    assert tt["assistant_tool_call_count"] == 1


@pytest.mark.skipif(
    not FAKE_SOURCE_INDEX.exists(),
    reason="tracked fake Pi source fixture is missing",
)
def test_real_wrapper_async_onpayload_without_required_tool_unchanged(
    tmp_path: Path,
) -> None:
    """Pre-existing async onPayload with NO required tool: ordinary selection.

    When `PI_GUARDIAN_REQUIRED_TOOL` is unset, the wrapper does not
    install its required-tool projection hook. The pre-existing async
    Pi onPayload therefore remains the only hook in the chain and is
    awaited end-to-end. The terminal JSON must show the success path
    with no `required_tool_selection` key.
    """
    materialized = _materialize_fake_pi_package(tmp_path)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    result = _run_real_wrapper(
        materialized,
        fake_home=fake_home,
        cwd=tmp_path,
        advertise_casing="lowercase",
        extra_env={
            "PI_FAKE_PRE_EXISTING_ASYNC_ONPAYLOAD": "1",
        },
    )
    assert (
        result.returncode == 0
    ), f"wrapper failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    final_line = result.stdout.strip().splitlines()[-1]
    parsed = json.loads(final_line)
    assert (
        parsed["status"] == "ok"
    ), f"expected successful terminal JSON; got: {parsed!r}"
    # No required-tool selection when PI_GUARDIAN_REQUIRED_TOOL is unset.
    assert "required_tool_selection" not in parsed
    tt = parsed["tool_telemetry"]
    assert tt["effective_tool_names"] == ["read", "bash", "edit", "write"]
    assert tt["write_tool_available"] is True
    assert tt["tool_execution_start_count"] == 1
    assert tt["tool_execution_end_count"] == 1
    assert tt["executed_tool_names"] == ["write"]
    assert tt["assistant_tool_call_count"] == 1
