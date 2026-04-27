# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.utils.hooks import collect_submodules

repo_root = Path.cwd()

datas = [
    (str(repo_root / "config" / "public_routes.yaml"), "config"),
    (str(repo_root / "docs" / "builtin-help" / "codexify-guide.md"), "docs/builtin-help"),
    (str(repo_root / "guardian" / "contracts.py"), "bootstrap/guardian"),
    (str(repo_root / "guardian" / "contracts" / "imprint_snapshot.py"), "bootstrap/guardian/contracts"),
    (str(repo_root / "guardian" / "contracts" / "imprint_proposal.py"), "bootstrap/guardian/contracts"),
]
datas.extend(
    (
        str(path),
        "config/supported_profiles",
    )
    for path in sorted((repo_root / "config" / "supported_profiles").glob("*.yaml"))
)
hiddenimports = [
    "backend.rag.chatgpt_migration",
    "chromadb.api.rust",
    "chromadb.telemetry.product",
    "chromadb.telemetry.product.posthog",
    "guardian.contracts",
    "guardian.contracts.imprint_proposal",
    "guardian.contracts.imprint_snapshot",
    *collect_submodules("guardian.contracts"),
]

a = Analysis(
    [str(repo_root / "backend" / "compiled_backend_entry.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="codexify-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="codexify-backend",
)
