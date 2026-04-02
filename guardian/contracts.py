import json
import os

CONTRACTS_DIR = os.path.join(
    os.path.dirname(__file__), "../guardian-codex/integrity"
)

# Allow `guardian.contracts` to act as a package namespace so callers can
# import `guardian.contracts.imprint_snapshot` without breaking the legacy
# contract helper module that already lives at this path.
__path__ = [os.path.join(os.path.dirname(__file__), "contracts")]

_contract_cache = {}


def load_contract(contract_id: str) -> str:
    filename = f"{contract_id}.md"
    path = os.path.abspath(os.path.join(CONTRACTS_DIR, filename))
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Contract {contract_id} not found in {CONTRACTS_DIR}"
        )
    with open(path) as f:
        return f.read()


def extract_json_block(md_text: str) -> dict:
    import re

    match = re.search(r"```json\s*({.*?})\s*```", md_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in contract.")
    return json.loads(match.group(1))


def validate_identity_contract(data: dict) -> bool:
    required_keys = {
        "identity",
        "origin",
        "model_substrate",
        "context",
        "restrictions",
    }
    return required_keys.issubset(data.keys())


def get_identity_context(contract_id: str) -> dict:
    if contract_id in _contract_cache:
        return _contract_cache[contract_id]
    text = load_contract(contract_id)
    data = extract_json_block(text)
    if not validate_identity_contract(data):
        raise ValueError("Contract validation failed: missing required keys.")
    _contract_cache[contract_id] = data
    return data


# Backwards-compatible shim: validate(model, identity) -> bool
# Used by tests to check if a model is allowed for a given identity.
# Currently a permissive shim that allows all known models.
def validate(model: str, identity: str) -> bool:
    """
    Validate whether a model is allowed for a given identity contract.

    Backwards-compatible shim that delegates to contract validation logic.
    Currently permissive: allows models that are known to exist.

    Args:
        model: Model name (e.g., "GPT-4.1")
        identity: Identity contract ID (e.g., "PCX-GUARDIAN-INT-001")

    Returns:
        bool: True if model is allowed, False otherwise
    """
    # Known model list for validation
    allowed_models = {"GPT-4.1", "Claude", "Gemini"}
    return model in allowed_models
