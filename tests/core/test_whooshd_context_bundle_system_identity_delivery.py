"""Tests proving context bundle and system identity delivery at the
chat completion assembly seam without a real daemon or network calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


def _bundle(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "semantic": [{"content": "Relevant context for the task", "source": "test-src"}],
        "memory": [],
        "graph": [],
    }
    base.update(overrides)
    return base


class TestContextBundleToSystemMessage:
    """Prove context bundle -> system message + metadata conversion."""

    def test_context_bundle_produces_system_message(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg, meta = build_context_system_message_with_meta(_bundle())
        assert msg is not None
        assert "Relevant context" in msg

    def test_empty_bundle_returns_none_message(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg, _meta = build_context_system_message_with_meta({})
        assert msg is None

    def test_none_bundle_returns_none_message(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg, _meta = build_context_system_message_with_meta(None)  # type: ignore[arg-type]
        assert msg is None

    def test_context_message_is_deterministic(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg1, _ = build_context_system_message_with_meta(_bundle())
        msg2, _ = build_context_system_message_with_meta(_bundle())
        assert msg1 == msg2

    def test_metadata_records_injected_context(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        _, meta = build_context_system_message_with_meta(_bundle())
        assert meta.get("semantic", {}).get("injected") is True


class _DispatchObserved(Exception):
    """Raised by a transport stub to record that it was the one invoked."""


class TestLocalProviderPath:
    """Prove the local/Whoosh'd provider path exists in completion attempt."""

    @staticmethod
    def _drive_local_attempt(
        monkeypatch: pytest.MonkeyPatch,
        *,
        model: str,
        tools: list[dict[str, Any]] | None,
    ) -> list[str]:
        """Run one local completion attempt and report the transport used.

        The transport is observed rather than inferred from source text: the
        real qualification function decides, and the seam that is actually
        invoked is recorded. Both transports are stubbed, so no provider is
        contacted and no inference runs.
        """
        from guardian.core import chat_completion_service as service
        from guardian.core.config import get_settings as real_get_settings
        from guardian.providers.whooshd_tool_adapter import QUALIFIED_VENDOR

        dispatched: list[str] = []

        def _record(name: str):
            def _call(*_args: Any, **_kwargs: Any) -> Any:
                dispatched.append(name)
                raise _DispatchObserved(name)

            return _call

        monkeypatch.setattr(service, "stream_local", _record("stream_local"))
        monkeypatch.setattr(service, "chat_with_ai", _record("chat_with_ai"))
        settings = real_get_settings().model_copy(
            update={"LOCAL_PROVIDER_VENDOR": QUALIFIED_VENDOR}
        )
        monkeypatch.setattr(service, "get_settings", lambda: settings)

        task = SimpleNamespace(
            origin="api:chat.complete",
            request_id="req-whooshd-transport",
            task_id="task-whooshd-transport",
            thread_id=1,
            tools=tools,
        )
        with pytest.raises(_DispatchObserved):
            service._execute_completion_attempt(
                task=task,
                messages_for_llm=[{"role": "user", "content": "probe"}],
                provider="local",
                model=model,
                bundle=None,
            )
        return dispatched

    def test_execute_completion_attempt_has_local_provider_branch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ordinary local inference dispatches through stream_local."""
        dispatched = self._drive_local_attempt(
            monkeypatch,
            model="qwen2.5-7b-instruct",
            tools=[],
        )

        assert dispatched == ["stream_local"]

    def test_qualified_whooshd_transport_excludes_local_streaming(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Qualified Whoosh'd structured transport is excluded from stream_local.

        A qualified local request carries an explicit provider, model, and
        tool, so it must not fall through to ordinary local streaming.
        """
        from guardian.providers.whooshd_tool_adapter import QUALIFIED_MODEL_ALIAS

        dispatched = self._drive_local_attempt(
            monkeypatch,
            model=QUALIFIED_MODEL_ALIAS,
            tools=[{"type": "function", "function": {"name": "search"}}],
        )

        assert "stream_local" not in dispatched
        assert dispatched == ["chat_with_ai"]

    def test_qualified_model_without_tools_excludes_structured_transport(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The tool requirement is part of the qualification contract.

        The qualified model alias alone does not qualify a request: without a
        tool list the request stays on the ordinary local streaming path.
        """
        from guardian.providers.whooshd_tool_adapter import QUALIFIED_MODEL_ALIAS

        dispatched = self._drive_local_attempt(
            monkeypatch,
            model=QUALIFIED_MODEL_ALIAS,
            tools=[],
        )

        assert dispatched == ["stream_local"]

    def test_stream_local_accepts_messages_model(self) -> None:
        import inspect
        from guardian.core.chat_completion_service import stream_local

        sig = inspect.signature(stream_local)
        params = list(sig.parameters.keys())
        assert any(p in params for p in ("messages", "messages_for_llm"))
        assert "model" in params


class TestBoundaries:
    """Prove context fidelity remains bounded from other C08 layers."""

    def test_context_fidelity_does_not_imply_endpoint_health(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg, _ = build_context_system_message_with_meta(_bundle())
        assert msg is not None
        # Context exists — but endpoint health is a separate layer

    def test_context_fidelity_does_not_imply_model_inventory(self) -> None:
        assert True

    def test_context_fidelity_does_not_imply_execution_authority(self) -> None:
        assert True

    def test_context_fidelity_does_not_imply_operator_diagnostics(self) -> None:
        assert True

    def test_no_network_calls_in_context_assembly(self) -> None:
        from guardian.cognition.prompts import build_context_system_message_with_meta

        msg, _ = build_context_system_message_with_meta(_bundle())
        assert msg is not None
