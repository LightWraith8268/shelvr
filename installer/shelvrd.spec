# PyInstaller spec for shelvrd — the Shelvr Windows server binary.
#
# Build with:
#   pyinstaller installer/shelvrd.spec --noconfirm
#
# Produces dist/shelvrd/shelvrd.exe plus a sibling tree of bundled deps.
# Sized for "ship to a homelab user" — single folder, run shelvrd.exe.
# Companion files (alembic migrations, web/dist) are included so the binary
# is self-contained and can run a first-time migrate + serve the SPA.

# ruff: noqa
# mypy: ignore-errors

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

REPO_ROOT = Path.cwd()

# Hidden imports — uvicorn loads its workers and protocols dynamically, and
# alembic loads our migration scripts by path; PyInstaller's static analyzer
# misses them. Add anything else discovered as a runtime ImportError here.
hiddenimports: list[str] = [
    "uvicorn",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.loops.auto",
    "aiosqlite",
    "passlib.handlers.argon2",
    "argon2",
    *collect_submodules("shelvr"),
    *collect_submodules("alembic"),
]

datas = [
    (str(REPO_ROOT / "alembic"), "alembic"),
    (str(REPO_ROOT / "alembic.ini"), "."),
    (str(REPO_ROOT / "web" / "dist"), "web/dist"),
    *collect_data_files("passlib"),
]

a = Analysis(
    [str(REPO_ROOT / "installer" / "shelvrd_entry.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="shelvrd",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="shelvrd",
)
