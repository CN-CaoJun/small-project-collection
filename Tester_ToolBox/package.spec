# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义共享的分析配置
shared_analysis = Analysis(
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
    excludes=[
        'matplotlib',  # 排除不需要的大型库
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

# 创建基础PYZ
pyz = PYZ(shared_analysis.pure, shared_analysis.zipped_data, cipher=block_cipher)

# 主程序
exe = EXE(
    pyz,
    shared_analysis.scripts,
    [],  # 不包含二进制文件
    exclude_binaries=True,  # 排除二进制文件
    name='DiagnosticToolBox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 收集所有依赖项
coll = COLLECT(
    exe,
    shared_analysis.binaries,
    shared_analysis.zipfiles,
    shared_analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DiagnosticToolBox'
)