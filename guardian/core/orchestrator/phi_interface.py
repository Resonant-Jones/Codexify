from guardian.core.orchestrator.model_interface import ModelInterface
from subprocess import run, PIPE


class PhiOllamaAdapter(ModelInterface):
    def __init__(self, model_name="phi3:mini"):
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        full_prompt = f"{system_prompt.strip()}\n\n{prompt.strip()}".strip()
        command = ["ollama", "run", self.model_name, full_prompt]

        result = run(command, stdout=PIPE, stderr=PIPE, text=True)
        print("Raw Ollama Output:", result.stdout)  # Debug print
        return result.stdout.strip()