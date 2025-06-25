# 🧠 model_interface.py
#
"""
LLM-agnostic interface for interpreting user input and producing orchestrator-ready commands.
Gemma is the symbolic voice, not a fixed model. This module routes to whichever local or remote model is chosen.
"""

import json
import logging
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from guardian.core.orchestrator.pulse_orchestrator import orchestrate

# -- Base interface --


class ModelInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass


# -- Gemma (via Ollama) adapter implementation --


class GemmaOllamaAdapter(ModelInterface):
    def __init__(self, model_name="gemma:4b-it"):
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        from subprocess import PIPE, run

        full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}".strip()
        command = ["ollama", "run", self.model_name, full_prompt]

        logger.info(f"Generating with model '{self.model_name}' using prompt: {prompt}")
        result = run(command, stdout=PIPE, stderr=PIPE, text=True)
        return result.stdout.strip()


# -- Natural language to action orchestration (simulated for now) --


def interpret_user_input(natural_language: str, model: ModelInterface):
    """
    Replace this simulation with model.generate() to do real structured output inference.
    """
    logger.info(f"Interpreting user input: {natural_language}")
    if "did I do my ritual" in natural_language.lower():
        command = {"action": "fetch_memory", "params": {"tag": "ritual"}}

    elif "how was my sleep" in natural_language.lower():
        command = {
            "action": "get_health_summary",
            "params": {"timeframe": "last_week", "metrics": ["sleep"]},
        }

    elif "predict stress" in natural_language.lower():
        command = {"action": "run_foresight", "params": {"context": "stress"}}

    else:
        return {
            "status": "unknown",
            "message": "Could not parse your request into an action.",
        }

    return orchestrate(command)


# -- CLI test entrypoint --

if __name__ == "__main__":
    user_input = input("You: ")
    adapter = GemmaOllamaAdapter()
    result = interpret_user_input(user_input, adapter)
    print(json.dumps(result, indent=2))
