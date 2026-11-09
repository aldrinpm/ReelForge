# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ui.py'],
    pathex=[],
    binaries=[],
    datas=[('ui', 'ui'), ('scripts', 'scripts'), ('config.json', '.')],
    hiddenimports=['ui.ui_backend', 'config', 'llm_client', 'engineio.async_drivers.threading', 'fastapi', 'uvicorn', 'pydantic', 'starlette'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReelForge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReelForge',
)
