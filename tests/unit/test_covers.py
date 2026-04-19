"""Tests for the covers service (Pillow-backed thumbnail generation)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError


@pytest.fixture
def sample_cover_bytes() -> bytes:
    """Generate a synthetic 1200x1800 cover image (2:3 aspect)."""
    img = Image.new("RGB", (1200, 1800), color=(100, 120, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_save_cover_produces_three_files(sample_cover_bytes: bytes, tmp_path: Path) -> None:
    """save_cover writes cover.jpg + cover-small.jpg + cover-medium.jpg."""
    from shelvr.services.covers import save_cover

    result = save_cover(sample_cover_bytes, tmp_path)

    assert (tmp_path / "cover.jpg").exists()
    assert (tmp_path / "cover-small.jpg").exists()
    assert (tmp_path / "cover-medium.jpg").exists()

    assert result["original"] == tmp_path / "cover.jpg"
    assert result["small"] == tmp_path / "cover-small.jpg"
    assert result["medium"] == tmp_path / "cover-medium.jpg"


def test_save_cover_small_is_200_wide(sample_cover_bytes: bytes, tmp_path: Path) -> None:
    """Small thumbnail is 200 pixels wide, aspect preserved."""
    from shelvr.services.covers import save_cover

    save_cover(sample_cover_bytes, tmp_path)

    with Image.open(tmp_path / "cover-small.jpg") as img:
        assert img.size[0] == 200
        # Source is 1200x1800 (ratio 2:3) → 200x300
        assert img.size[1] == 300


def test_save_cover_medium_is_600_wide(sample_cover_bytes: bytes, tmp_path: Path) -> None:
    """Medium thumbnail is 600 pixels wide, aspect preserved."""
    from shelvr.services.covers import save_cover

    save_cover(sample_cover_bytes, tmp_path)

    with Image.open(tmp_path / "cover-medium.jpg") as img:
        assert img.size[0] == 600
        assert img.size[1] == 900


def test_save_cover_jpeg_format(sample_cover_bytes: bytes, tmp_path: Path) -> None:
    """All three outputs are JPEG regardless of source format."""
    from shelvr.services.covers import save_cover

    save_cover(sample_cover_bytes, tmp_path)

    for name in ("cover.jpg", "cover-small.jpg", "cover-medium.jpg"):
        with Image.open(tmp_path / name) as img:
            assert img.format == "JPEG"


def test_save_cover_accepts_jpeg_input(tmp_path: Path) -> None:
    """Input bytes can be JPEG — output still produces all three variants."""
    from shelvr.services.covers import save_cover

    img = Image.new("RGB", (800, 1200), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)

    save_cover(buf.getvalue(), tmp_path)
    assert (tmp_path / "cover-small.jpg").exists()


def test_save_cover_smaller_than_thresholds_no_upscale(tmp_path: Path) -> None:
    """If source is smaller than the thumbnail width, don't upscale."""
    from shelvr.services.covers import save_cover

    img = Image.new("RGB", (150, 225), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    save_cover(buf.getvalue(), tmp_path)

    with Image.open(tmp_path / "cover-small.jpg") as small:
        assert small.size[0] <= 200
    with Image.open(tmp_path / "cover-medium.jpg") as medium:
        assert medium.size[0] <= 600


def test_save_cover_flattens_rgba_onto_white(tmp_path: Path) -> None:
    """RGBA input gets flattened (JPEG doesn't support alpha)."""
    from shelvr.services.covers import save_cover

    # Semi-transparent red image
    img = Image.new("RGBA", (400, 600), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    save_cover(buf.getvalue(), tmp_path)

    with Image.open(tmp_path / "cover.jpg") as result:
        assert result.mode == "RGB"
        assert result.format == "JPEG"


def test_save_cover_rejects_invalid_image(tmp_path: Path) -> None:
    """Non-image bytes raise Pillow's UnidentifiedImageError (caller's problem)."""
    from shelvr.services.covers import save_cover

    with pytest.raises(UnidentifiedImageError):
        save_cover(b"this is not an image", tmp_path)


def test_save_cover_creates_dest_dir(tmp_path: Path) -> None:
    """save_cover creates the destination directory if it doesn't exist."""
    from shelvr.services.covers import save_cover

    img = Image.new("RGB", (400, 600), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    nested = tmp_path / "nonexistent" / "subdir"
    assert not nested.exists()

    save_cover(buf.getvalue(), nested)
    assert (nested / "cover.jpg").exists()
