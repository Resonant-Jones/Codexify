# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from pyinstaller_shared import common_datas, repo_root, runtime_hiddenimports

datas = common_datas(repo_root())
hiddenimports = runtime_hiddenimports()

a = Analysis(
    [str(repo_root() / "backend" / "compiled_runtime_entry.py")],
    pathex=[str(repo_root())],
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
    name="codexify-runtime",
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
    name="codexify-runtime",
)
