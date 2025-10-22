import pytest
from fastapi import HTTPException

from guardian.contracts import validate
from guardian.core.orchestrator.model_interface import ModelInterface


class DummyModel(ModelInterface):
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"{system_prompt}{prompt}".strip()


def test_validate_allows_model():
    assert validate("GPT-4.1", "PCX-GUARDIAN-INT-001")


def test_validate_rejects_unknown_model():
    assert not validate("UltraSecretModel", "PCX-GUARDIAN-INT-001")


def test_chat_raises_for_disallowed_model():
    interface = DummyModel()
    with pytest.raises(HTTPException) as exc_info:
        interface.chat(
            "Hello", identity="PCX-GUARDIAN-INT-001", model="UltraSecretModel"
        )
    assert exc_info.value.status_code == 400
    assert "UltraSecretModel" in exc_info.value.detail


def test_chat_allows_permitted_model():
    interface = DummyModel()
    output = interface.chat(
        "Hello Guardian",
        identity="PCX-GUARDIAN-INT-001",
        model="GPT-4.1",
    )
    assert output == "Hello Guardian"
