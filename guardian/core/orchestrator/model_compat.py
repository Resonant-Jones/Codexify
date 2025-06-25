import logging
import platform

logger = logging.getLogger(__name__)


def get_device_specs():
    # You can enhance this detection logic based on actual device metadata later
    machine = platform.machine()
    system = platform.system()

    if system == "Darwin":
        if "iPhone" in machine:
            return "iPhone 15 Pro"  # assume best iPhone for now
        elif "arm64" in machine:
            return "MacBook M2"
        else:
            return "MacBook Intel"
    result = "Unknown"
    logger.debug(f"Detected system: {system}, machine: {machine}")
    return result


def is_compatible(device_str, requirement):
    # Primitive logic for now; enhance later with actual device model/version comparisons
    result = requirement in device_str or "or better" in requirement
    logger.debug(
        f"Checking compatibility: device='{device_str}', requirement='{requirement}' -> result={result}"
    )
    return result


def get_compatible_models(registry):
    logger.debug(f"Evaluating compatible models for device: {get_device_specs()}")
    device = get_device_specs()
    compatible = []

    for model in registry.get("models", []):
        req = model.get("requires", "")
        compatible_result = is_compatible(device, req)
        logger.debug(
            f"Model '{model.get('name', 'unknown')}' requires '{req}' -> compatible={compatible_result}"
        )
        if compatible_result:
            compatible.append(model)

    return compatible
