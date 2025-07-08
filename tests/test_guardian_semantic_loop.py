import asyncio
from pathlib import Path
import sys
from cryptography.fernet import Fernet
import pytest

pytestmark = pytest.mark.asyncio

# Ensure project root is on sys.path so `guardian` can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))

from guardian.modules.memory_key_vault import MemoryKeyVault


class AbletonPlugin:
    """Simple stub plugin representing Ableton control."""

    name = "ableton"

    def __init__(self, vault: MemoryKeyVault) -> None:
        self.vault = vault
        self.calls = []
        self.allowed_keys = {"volume"}

    def run(self, instruction: str):
        self.calls.append(instruction)
        if "secret" in instruction and "secret" not in self.allowed_keys:
            raise PermissionError("unauthorized vault access")
        return {"status": "ok", "handled_by": self.name}


class MCP:
    """Minimal router that sends Ableton instructions to the plugin."""

    def __init__(self, plugin: AbletonPlugin) -> None:
        self.plugin = plugin

    async def handle_instruction(self, text: str):
        if "ableton" in text.lower():
            return self.plugin.run(text)
        return {"status": "error", "message": "plugin not found"}


class Guardian:
    """Very small Guardian stub to classify text and dispatch to MCP."""

    def __init__(self, vault: MemoryKeyVault, mcp: MCP) -> None:
        self.vault = vault
        self.mcp = mcp

    def classify(self, text: str) -> str:
        lowered = text.lower()
        keywords = ["lower", "raise", "set", "ableton", "plugin"]
        if any(word in lowered for word in keywords):
            return "instruction"
        return "data"

    async def process(self, text: str):
        category = self.classify(text)
        if category == "instruction":
            return await self.mcp.handle_instruction(text)
        self.vault.store_summary("user", text)
        return {"status": "stored"}


@pytest.fixture
def vault() -> MemoryKeyVault:
    v = MemoryKeyVault()
    v.set_user_key("user", Fernet.generate_key())
    return v


@pytest.fixture
def ableton_plugin(vault: MemoryKeyVault) -> AbletonPlugin:
    return AbletonPlugin(vault)


@pytest.fixture
def mcp(ableton_plugin: AbletonPlugin) -> MCP:
    return MCP(ableton_plugin)


@pytest.fixture
def guardian(vault: MemoryKeyVault, mcp: MCP) -> Guardian:
    return Guardian(vault, mcp)


@pytest.mark.asyncio
async def test_guardian_instruction_classification(guardian: Guardian, ableton_plugin: AbletonPlugin):
    text = "Lower Ableton Track 1 to -6dB"
    category = guardian.classify(text)
    assert category == "instruction"

    result = await guardian.process(text)
    assert result["status"] == "ok"
    assert ableton_plugin.calls == [text]


@pytest.mark.asyncio
async def test_guardian_data_classification(guardian: Guardian, ableton_plugin: AbletonPlugin, vault: MemoryKeyVault):
    text = "My favorite color is silver."
    category = guardian.classify(text)
    assert category == "data"

    result = await guardian.process(text)
    assert result["status"] == "stored"
    assert ableton_plugin.calls == []
    assert vault.get_summary("user") == text


@pytest.mark.asyncio
async def test_mcp_routing_and_permission(guardian: Guardian, ableton_plugin: AbletonPlugin, mcp: MCP):
    ok_text = "Lower Ableton Track 2 to -3dB"
    result = await guardian.process(ok_text)
    assert result["status"] == "ok"

    bad_text = "Use UnknownPlugin now"
    result = await guardian.process(bad_text)
    assert result["status"] == "error"

    with pytest.raises(PermissionError):
        await mcp.handle_instruction("Lower Ableton secret level")


@pytest.mark.asyncio
async def test_vault_state_snapshot(guardian: Guardian, vault: MemoryKeyVault):
    await guardian.process("Note one")
    await guardian.process("Note two")

    state = {"user": vault.get_summary("user")}
    assert state == {"user": "Note two"}

    # TODO: cover multi-turn conversations and plugin failure fallback
