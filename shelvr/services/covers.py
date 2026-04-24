"""Cover-image persistence and thumbnail generation.

Writes three versions side by side in the book's directory:
    cover.jpg         — converted JPEG of the original bytes
    cover-small.jpg   — 200px-wide thumbnail, aspect preserved
    cover-medium.jpg  — 600px-wide thumbnail, aspect preserved

All outputs are JPEG regardless of source format. RGBA/P inputs are flattened
onto a white background (JPEG doesn't support alpha).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

from PIL import Image

_SMALL_WIDTH = 200
_MEDIUM_WIDTH = 600

_QUALITY_ORIGINAL = 90
_QUALITY_MEDIUM = 85
_QUALITY_SMALL = 80


def save_cover(
    source_bytes: bytes, dest_dir: Path
) -> dict[Literal["original", "small", "medium"], Path]:
    """Save the cover in three sizes to ``dest_dir``.

    Args:
        source_bytes: Raw image bytes (PNG, JPEG, etc. — anything Pillow can open).
        dest_dir: Directory where the three output files will be written.
            Created if it doesn't exist.

    Returns:
        A mapping of size name → output file path.

    Raises:
        PIL.UnidentifiedImageError: If ``source_bytes`` isn't a decodable image.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(source_bytes)) as source_image:
        rgb_image = _ensure_rgb(source_image)

        original_path = dest_dir / "cover.jpg"
        rgb_image.save(original_path, format="JPEG", quality=_QUALITY_ORIGINAL)

        medium_path = dest_dir / "cover-medium.jpg"
        _save_thumbnail(rgb_image, medium_path, _MEDIUM_WIDTH, _QUALITY_MEDIUM)

        small_path = dest_dir / "cover-small.jpg"
        _save_thumbnail(rgb_image, small_path, _SMALL_WIDTH, _QUALITY_SMALL)

    return {
        "original": original_path,
        "medium": medium_path,
        "small": small_path,
    }


def _ensure_rgb(img: Image.Image) -> Image.Image:
    """JPEG doesn't support alpha — flatten RGBA/P/LA inputs onto white."""
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background
    return img.convert("RGB")


def _save_thumbnail(img: Image.Image, path: Path, target_width: int, quality: int) -> None:
    """Write ``img`` resized to ``target_width``-wide JPEG (no upscaling)."""
    if img.size[0] <= target_width:
        img.save(path, format="JPEG", quality=quality)
        return
    aspect = img.size[1] / img.size[0]
    target_size = (target_width, round(target_width * aspect))
    resized = img.resize(target_size, Image.Resampling.LANCZOS)
    resized.save(path, format="JPEG", quality=quality)
