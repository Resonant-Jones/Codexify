from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import uvicorn


def _bootstrap_contract_modules() -> None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "bootstrap" / "guardian"
    module_specs = [
        ("guardian.contracts", base / "contracts.py"),
        ("guardian.contracts.imprint_snapshot", base / "contracts" / "imprint_snapshot.py"),
        ("guardian.contracts.imprint_proposal", base / "contracts" / "imprint_proposal.py"),
    ]

    for module_name, module_path in module_specs:
        if module_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {module_name} from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)


def main() -> None:
    _bootstrap_contract_modules()
    from guardian.guardian_api import app

    port = int(os.getenv("PORT", "8888"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
