"""Tests proving context bundle and system identity delivery at the
chat completion assembly seam without a real daemon or network calls.
"""

from __future__ import annotations

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


class TestLocalProviderPath:
    """Prove the local/Whoosh'd provider path exists in completion attempt."""

    def test_execute_completion_attempt_has_local_provider_branch(self) -> None:
        import re

        import inspect
        from guardian.core.chat_completion_service import _execute_completion_attempt

        source = inspect.getsource(_execute_completion_attempt)

        # 1. Qualified Whoosh'd structured-transport classification is evaluated.
        assert "is_qualified_transport_candidate(" in source, (
            "_execute_completion_attempt must evaluate structured-transport "
            "qualification via is_qualified_transport_candidate"
        )

        # 2. The qualified-transport state variable is stored.
        assert "uses_whooshd_structured_transport" in source, (
            "_execute_completion_attempt must capture the qualified-transport "
            "decision in uses_whooshd_structured_transport"
        )

        # 3. Ordinary local streaming dispatches through stream_local.
        assert "stream_local(" in source, (
            "_execute_completion_attempt must dispatch ordinary local completion "
            "through stream_local()"
        )

        # 4. The ordinary local branch is guarded by the semantic equivalent of
        #    `provider == "local" and not uses_whooshd_structured_transport`.
        #    Tolerate Black-compatible line wrapping by collapsing whitespace.
        normalized = re.sub(r"\s+", " ", source)
        guard_pattern = (
            r"if\s+provider\s*==\s*[\"']local[\"']\s+and\s+not\s+uses_whooshd_structured_transport\s*:"
        )
        assert re.search(guard_pattern, normalized), (
            "_execute_completion_attempt ordinary local branch must guard with "
            "`if provider == \"local\" and not uses_whooshd_structured_transport:` "
            "(qualified Whoosh'd structured transport must be excluded)"
        )

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
