# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('QL1.ico', '.'), ('src/newEpilepsy', 'src/newEpilepsy'), ('..\\venv\\Lib\\site-packages\\cuda_cpp_fullscale', 'cuda_cpp_fullscale')]
binaries = [('resource\\licence_core.dll', 'resource'), ('..\\venv\\Lib\\site-packages\\AR_neurokit2_cuda_fullscale.cp312-win_amd64.pyd', '.')]
hiddenimports = ['subprocess', 'pyedfilb', 'markdown', 'openai', 'lazy_loader', 'lightgbm', 'numpy', 'numpy.core', 'numpy.core._methods', 'numpy.lib.format', 'numpy.random', 'numpy._core', 'numpy.core.multiarray', 'numpy.core.numeric', 'numpy.core.umath', 'numpy.linalg.linalg', 'numpy.random', 'openpyxl', 'openpyxl.cell._writer', 'OpenGL_accelerate', 'OpenGL.arrays', 'et_xmlfile', 'pandas.io.excel._openpyxl', 'openpyxl.workbook', 'openpyxl.writer.excel', 'pandas.io.formats.excel', 'pandas.io.excel._base', 'matplotlib.backends.backend_svg', 'matplotlib.backends.backend_eps', 'matplotlib.backends.backend_ps', 'matplotlib.backends.backend_pdf', 'matplotlib.backends.backend_pgf', 'matplotlib.backends.backend_cairo', 'matplotlib.backends.backend_agg', 'matplotlib.backends.backend_qt5agg', 'matplotlib.backends._backend_pdf_ps', 'ar_neurokit2_rust', 'ar_neurokit2_rust.ar_neurokit2_rust', 'AR_neurokit2_cuda_fullscale', 'AR_neurokit2.complexity._cuda_cpp_fullscale_backend']
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sklearn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('OpenGL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('OpenGL_accelerate')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('xgboost')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ar_neurokit2_rust')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['AR_analyser.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='AR_analyser',
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
    icon=['QL1.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AR_analyser',
)
