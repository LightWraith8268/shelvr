# Shelvr Windows Installer

This directory holds the artifacts that turn the Shelvr server into a
distributable Windows binary.

## Files

- `shelvrd.spec` — PyInstaller spec that builds `dist/shelvrd/shelvrd.exe`
  with bundled dependencies, alembic migrations, and the compiled web SPA.
- `shelvrd_entry.py` — Entry point used by the spec. Resolves the bundle's
  data directory at runtime and delegates to `shelvr.cli:main`.

## Local build

```powershell
python -m pip install pyinstaller
cd web
npm ci
npm run build
cd ..
pyinstaller installer/shelvrd.spec --noconfirm
```

The resulting `dist/shelvrd/` folder is fully self-contained and can be run
with `dist\shelvrd\shelvrd.exe serve`. Configuration is read from the same
`shelvr.toml` and `SHELVR_*` environment variables as the source-checkout
server.

## CI

The `.github/workflows/build-installer.yml` workflow runs on every push to
`main` plus `workflow_dispatch`. It builds the binary on a Windows runner
and uploads the `dist/shelvrd/` directory as a workflow artifact named
`shelvrd-windows`. Future days will add NSIS bundling and nssm-driven
service registration on top of this artifact.
