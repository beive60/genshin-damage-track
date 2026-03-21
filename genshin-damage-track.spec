# -*- mode: python ; coding: utf-8 -*-

import warnings
# Suppress harmless third-party warnings during PyInstaller analysis
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")

import os, Cython, paddleocr, paddle
_cython_dir = os.path.dirname(Cython.__file__)
_paddleocr_dir = os.path.dirname(paddleocr.__file__)
_paddle_libs = os.path.join(os.path.dirname(paddle.__file__), 'libs')

a = Analysis(
    ['src\\genshin_damage_track\\main.py'],
    pathex=[],
    binaries=[
        (os.path.join(_paddle_libs, '*.dll'), 'paddle/libs'),
    ],
    datas=[
        (os.path.join(_cython_dir, 'Utility'), 'Cython/Utility'),
        # PaddleOCR resolves tools/ and ppocr/ relative to its __file__.
        # Include at both paddleocr/ and root to cover both resolution paths.
        (os.path.join(_paddleocr_dir, 'tools'), 'paddleocr/tools'),
        (os.path.join(_paddleocr_dir, 'ppocr'), 'paddleocr/ppocr'),
        (os.path.join(_paddleocr_dir, 'ppstructure'), 'paddleocr/ppstructure'),
        (os.path.join(_paddleocr_dir, 'tools'), 'tools'),
        (os.path.join(_paddleocr_dir, 'ppocr'), 'ppocr'),
        (os.path.join(_paddleocr_dir, 'ppstructure'), 'ppstructure'),
    ],
    hiddenimports=['tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy.special._cdflib', 'tzdata'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='genshin-damage-track',
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
