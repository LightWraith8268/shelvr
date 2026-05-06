"""Validate and extract uploaded plugin zip files into the plugin directory.

Security model: plugins run in the same Python process as the server, so the
host has no real sandbox — installation is an act of trust. This module's
job is to make the trust deliberate (admin-only upload route) and to refuse
the obviously hostile shapes (path traversal, zip bombs, missing manifest)
before extraction. It does not attempt to vet plugin code.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from shelvr.plugins.manifest import PluginManifest, load_manifest


class PluginUploadError(Exception):
    """Raised when an uploaded plugin zip is rejected."""


# 5 MiB compressed; 50 MiB uncompressed. Plugin code is small text — these
# limits leave room for a few static assets without inviting zip bombs.
MAX_COMPRESSED_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class ExtractedPlugin:
    """Metadata returned after a successful extraction."""

    manifest: PluginManifest
    install_path: Path


def install_plugin_zip(
    *,
    zip_bytes: bytes,
    plugins_dir: Path,
    overwrite: bool = False,
) -> ExtractedPlugin:
    """Validate a plugin zip and extract it under ``plugins_dir/<plugin_id>``.

    Raises:
        PluginUploadError: if the zip is malformed, exceeds size limits, contains
            traversal-style entries, lacks a ``plugin.toml`` manifest, or would
            overwrite an existing directory when ``overwrite`` is false.
    """
    if len(zip_bytes) > MAX_COMPRESSED_BYTES:
        raise PluginUploadError(
            f"plugin archive is too large ({len(zip_bytes)} bytes; max {MAX_COMPRESSED_BYTES})"
        )

    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise PluginUploadError(f"not a valid zip archive: {exc}") from exc

    members = archive.infolist()
    if not members:
        raise PluginUploadError("plugin archive is empty")

    total_uncompressed = sum(member.file_size for member in members)
    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise PluginUploadError(
            f"plugin uncompressed size {total_uncompressed} exceeds limit "
            f"{MAX_UNCOMPRESSED_BYTES} (zip bomb)"
        )

    for member in members:
        _check_safe_member_name(member.filename)

    manifest_member, top_prefix = _locate_manifest(members)
    manifest = _parse_manifest_from_zip(archive, manifest_member)

    target_dir = (plugins_dir / manifest.id).resolve()
    plugins_root = plugins_dir.resolve()
    if not _is_within(target_dir, plugins_root):
        raise PluginUploadError("resolved install path escaped the plugins directory")

    if target_dir.exists():
        if not overwrite:
            raise PluginUploadError(
                f"plugin '{manifest.id}' is already installed; pass overwrite=true to replace"
            )
        shutil.rmtree(target_dir)

    plugins_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="shelvr-plugin-") as scratch:
        scratch_dir = Path(scratch)
        archive.extractall(scratch_dir)
        # If everything was nested under a single top-level directory inside
        # the zip, promote that directory's contents to the install path.
        source_dir = scratch_dir / top_prefix if top_prefix else scratch_dir
        shutil.move(str(source_dir), target_dir)

    return ExtractedPlugin(manifest=manifest, install_path=target_dir)


def _locate_manifest(members: list[zipfile.ZipInfo]) -> tuple[zipfile.ZipInfo, str]:
    """Find the manifest entry and detect the optional shared top-level dir."""
    direct_root = next((member for member in members if member.filename == "plugin.toml"), None)
    if direct_root is not None:
        return direct_root, ""

    # Otherwise expect every entry to share a single top-level directory and
    # the manifest to live at <top>/plugin.toml.
    top_prefixes: set[str] = set()
    for member in members:
        head = member.filename.split("/", 1)[0]
        if head:
            top_prefixes.add(head)
    if len(top_prefixes) != 1:
        raise PluginUploadError(
            "plugin archive must contain plugin.toml at the root or under a single top-level "
            "directory"
        )

    top = next(iter(top_prefixes))
    nested_path = f"{top}/plugin.toml"
    nested = next((member for member in members if member.filename == nested_path), None)
    if nested is None:
        raise PluginUploadError("plugin.toml missing from archive")
    return nested, top


def _parse_manifest_from_zip(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> PluginManifest:
    """Parse the manifest by writing it to a temp file (load_manifest reads paths)."""
    raw = archive.read(member.filename)
    try:
        # Smoke-test parse so we report toml errors with the upload, not later.
        tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PluginUploadError(f"plugin.toml is not valid UTF-8 TOML: {exc}") from exc

    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="wb") as scratch_file:
        scratch_file.write(raw)
        scratch_path = Path(scratch_file.name)
    try:
        return load_manifest(scratch_path)
    except Exception as exc:
        raise PluginUploadError(f"manifest validation failed: {exc}") from exc
    finally:
        scratch_path.unlink(missing_ok=True)


def _check_safe_member_name(name: str) -> None:
    """Reject zip entries that try to escape the extraction root."""
    if not name:
        raise PluginUploadError("zip entry with empty name")
    if name.startswith("/") or name.startswith("\\"):
        raise PluginUploadError(f"absolute path in zip entry: {name!r}")
    # ``\\`` shows up on archives built on Windows; treat as path separator too.
    parts = name.replace("\\", "/").split("/")
    if ".." in parts:
        raise PluginUploadError(f"path traversal attempt in zip entry: {name!r}")


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def remove_installed_plugin(*, plugin_id: str, plugins_dir: Path) -> bool:
    """Delete a previously-installed plugin directory. Returns ``True`` if removed."""
    target = (plugins_dir / plugin_id).resolve()
    if not _is_within(target, plugins_dir.resolve()):
        return False
    if not target.exists() or not target.is_dir():
        return False
    shutil.rmtree(target)
    return True
