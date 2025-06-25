import json
import os

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "../guardian-codex/integrity")

_contract_cache = {}


def load_contract(contract_id: str) -> str:
    filename = f"{contract_id}.md"
    path = os.path.abspath(os.path.join(CONTRACTS_DIR, filename))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Contract {contract_id} not found in {CONTRACTS_DIR}")
    with open(path, "r") as f:
        return f.read()


def extract_json_block(md_text: str) -> dict:
    import re

    match = re.search(r"```json\s*({.*?})\s*```", md_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in contract.")
    return json.loads(match.group(1))


def validate_identity_contract(data: dict) -> bool:
    required_keys = {"identity", "origin", "model_substrate", "context", "restrictions"}
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
