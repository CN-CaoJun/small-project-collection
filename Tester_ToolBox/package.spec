# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

shared_analysis = Analysis(
    ['MainUI.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('reference_modules/python-can', 'reference_modules/python-can'),
        ('reference_modules/python-can-isotp', 'reference_modules/python-can-isotp'),
        ('reference_modules/python-udsoncan', 'reference_modules/python-udsoncan'),
        ('assets/icon.ico', 'assets'),
        ('readme.md', '.')  # 修改目标路径为当前目录
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
    excludes=[
        'matplotlib',  
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(shared_analysis.pure, shared_analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    shared_analysis.scripts,
    [], 
    exclude_binaries=True,  
    name='Chery_DiagnosticToolBox',
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
    version='version.txt', 
    icon='assets/icon.ico'
)

coll = COLLECT(
    exe,
    shared_analysis.binaries,
    shared_analysis.zipfiles,
    shared_analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Chery_DiagnosticToolBox_V1.0.0.1' 
)