# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['MainUI.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('reference_modules/python-can', 'reference_modules/python-can'),
        ('reference_modules/python-can-isotp', 'reference_modules/python-can-isotp'),
        ('reference_modules/python-udsoncan', 'reference_modules/python-udsoncan'),
    ],
    hiddenimports=[
        'can',
        'isotp',
        'udsoncan',
        'can.interfaces.vector',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DiagnosticToolBox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)