# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import customtkinter

block_cipher = None

# Locate CustomTkinter package assets dynamically
ctk_dir = os.path.dirname(customtkinter.__file__)

# Define bundled data files (Source Path, Target Subfolder)
datas = [
    (ctk_dir, 'customtkinter'),
    ('pdf_icon.ico', '.'),
]

# Explicit hidden imports to prevent missing C-extensions or dynamic submodules
hidden_imports = [
    'customtkinter',
    'fitz',
    'fitz._fitz',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'pdf_engine',
    'app_ui',
]

# Exclude unnecessary heavy libraries if present in build environment
excludes = [
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'IPython',
    'unittest',
    'pytest',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single-Folder Executable Target
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,     # Single-folder mode (--onedir)
    name='PDF-toolio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,             # Windowed GUI mode (--noconsole)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='pdf_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF-toolio',
)
