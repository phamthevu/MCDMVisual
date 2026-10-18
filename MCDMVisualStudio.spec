# PyInstaller onedir package; run from project root.
from pathlib import Path
root = Path(SPECPATH)
datas = []
for folder in ("Template", "Demo Data"):
    source = root / folder
    if source.exists():
        datas.append((str(source), folder))
a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[], datas=datas, hiddenimports=["pyqtgraph.exporters"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MCDMVisualStudio",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
               name="MCDMVisualStudio")
