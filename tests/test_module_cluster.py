from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

from guardian.modules.live_semantic_timeline import SemanticTimeline, TimelineEvent
from guardian.modules.memory_key_vault import MemoryKeyVault
from guardian.modules.plug_adapter_registry import AdapterRegistry, AdapterSpec
from guardian.modules.immutable_log import ImmutableLog
from guardian.modules.companion_foresight import Foresight, PredictionRequest
from guardian.modules.flow_tuner import FlowConfig

import pytest
pytestmark = pytest.mark.asyncio


def test_semantic_timeline_discard():
    timeline = SemanticTimeline(ttl_seconds=1)
    event = TimelineEvent(
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=2),
        narrative="old",
        user_id="u",
    )
    timeline.add_event(event)
    assert timeline.query("old") == []


def test_memory_key_vault_roundtrip():
    vault = MemoryKeyVault()
    key = Fernet.generate_key()
    vault.set_user_key("u", key)
    vault.store_summary("u", "secret")
    assert vault.get_summary("u") == "secret"


def test_adapter_registry():
    registry = AdapterRegistry()
    spec = AdapterSpec(name="a", allowed_scopes=["read"], can_pull=True)
    registry.register(spec)
    assert registry.allowed("a", "read")
    assert not registry.allowed("a", "write")


def test_immutable_log():
    log = ImmutableLog()
    entry_id = log.add_entry("x", immutable=True)
    try:
        log.update_entry(entry_id, "y")
        assert False, "expected error"
    except ValueError:
        pass


def test_companion_foresight():
    foresight = Foresight()
    out = foresight.predict_next(PredictionRequest(recent_narratives=["foo"]))
    assert "foo" in out


def test_flow_config_defaults():
    cfg = FlowConfig()
    assert cfg.context_window == 4096
