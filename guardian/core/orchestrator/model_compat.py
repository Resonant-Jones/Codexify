import platform

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
    return "Unknown"

def is_compatible(device_str, requirement):
    # Primitive logic for now; enhance later with actual device model/version comparisons
    return requirement in device_str or "or better" in requirement

def get_compatible_models(registry):
    device = get_device_specs()
    compatible = []

    for model in registry.get("models", []):
        req = model.get("requires", "")
        if is_compatible(device, req):
            compatible.append(model)

    return compatible