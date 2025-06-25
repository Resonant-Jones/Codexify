import json
import logging
import sys
from importlib import import_module
from pathlib import Path

logger = logging.getLogger(__name__)


def get_default_model_key():
    if sys.platform == "darwin":
        try:
            import objc  # crude check for iOS via Pythonista or embedded Python

            return "phi_local"
        except ImportError:
            return "gemma_local"
    elif sys.platform.startswith("linux"):
        return "phi_local"
    return "phi_local"  # fallback


def load_model_backend(name="default"):
    """
    Load a model backend from the registry using the specified name.
    Defaults to the entry marked 'default' in model_registry.json.
    """
    registry_path = Path(__file__).parent / "model_registry.json"
    with open(registry_path, "r") as f:
        registry = json.load(f)

    model_key = get_default_model_key() if name == "default" else name
    logger.info(f"Loading model backend: {model_key}")
    logger.debug(f"Available registry keys: {list(registry.keys())}")

    if model_key not in registry:
        raise ValueError(f"Model backend '{model_key}' not found in registry.")

    config = registry[model_key]
    adapter_name = config["adapter"]
    model_name = config.get("model", None)

    # Dynamically import the adapter from known adapter locations
    adapter_class = resolve_adapter(adapter_name)

    return adapter_class(model_name=model_name) if model_name else adapter_class()


def resolve_adapter(adapter_name):
    """
    Dynamically import adapter class based on its name.
    Assumes adapters are defined in the current package or submodules.
    """
    known_adapters = {
        "GemmaOllamaAdapter": "guardian.core.orchestrator.model_interface",
        # Add other adapters as needed
    }

    if adapter_name not in known_adapters:
        logger.warning(f"Adapter '{adapter_name}' not found in known_adapters.")
        raise ImportError(f"No module mapping found for adapter '{adapter_name}'.")

    module_path = known_adapters[adapter_name]
    module = import_module(module_path)
    logger.info(f"Resolved adapter '{adapter_name}' from module '{module_path}'")
    return getattr(module, adapter_name)
