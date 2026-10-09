"""Keep packaged-bootstrap resources present in the final Tauri bundle."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _rust_string_array(source: str, constant: str) -> set[str]:
    match = re.search(
        rf"const {constant}[^=]*=\s*&?\[([^]]*)\]",
        source,
        re.DOTALL,
    )
    assert match, f"could not find {constant}"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def test_packaged_bootstrap_and_webui_build_inputs_are_bundled():
    build_source = (ROOT / "src-tauri/build.rs").read_text()
    commands_source = (ROOT / "src-tauri/src/commands.rs").read_text()
    tauri_config = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text())

    staged = _rust_string_array(build_source, "BUNDLE_RESOURCE_PATHS")
    runtime_required = _rust_string_array(
        commands_source, "PACKAGED_RUNTIME_REQUIRED_ASSETS"
    )

    # These are the explicit inputs copied by Dockerfile.webui.workspace.
    # The frontend tree also contains that Dockerfile and its Docker-specific
    # ignore file, plus frontend/src/package.json.
    webui_build_inputs = {
        "frontend",
        "package.json",
        "pnpm-lock.yaml",
        "pnpm-workspace.yaml",
    }
    required = runtime_required | webui_build_inputs

    resources = tauri_config["bundle"]["resources"]
    for path in sorted(required):
        staged_path = f"./target/bundle-resources/{path}"
        assert path in staged, f"{path} is required but not staged by build.rs"
        assert resources.get(staged_path) == path, (
            f"{path} is staged but not bundled at the path packaged bootstrap resolves"
        )

    # The root contracts/ directory is staged for other runtime uses, but the
    # packaged WebUI build consumes frontend/src/contracts instead. Do not
    # turn the Tauri bundle into a copy of every staged repository path.
    assert "contracts" not in required
