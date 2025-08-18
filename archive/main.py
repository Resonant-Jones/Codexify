"""
Facade for Imprint Zero onboarding flows, exposing simple loaders and config errors.
"""

from guardian.agents.imprint_zero import imprint_zero as _agent

class ImprintZeroConfigError(Exception):
    """Raised when Imprint Zero configuration is invalid."""
    pass

def load_prompt(config_path: str = None) -> str:
    """
    Load the raw Imprint Zero onboarding prompt text.
    If a config_path is provided, simulate a broken config by raising an error.
    """
    if config_path:
        raise ImprintZeroConfigError(f"Simulated broken config at {config_path}")
    prompt, _ = _agent.start_flow()
    return prompt

def load_prompt_json(config_path: str = None) -> dict:
    """
    Load the Imprint Zero prompt and options as structured JSON.
    If a config_path is provided, simulate a broken config by raising an error.
    """
    if config_path:
        raise ImprintZeroConfigError(f"Simulated broken config at {config_path}")
    prompt, options = _agent.start_flow()
    return {"prompt": prompt, "options": options}
