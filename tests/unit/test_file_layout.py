"""Tests for file-layout sanitization and target-path computation."""

from __future__ import annotations

from pathlib import Path


def test_sanitize_strips_forbidden_characters() -> None:
    from shelvr.services.file_layout import sanitize_segment

    assert sanitize_segment("foo/bar") == "foo_bar"
    assert sanitize_segment("foo\\bar") == "foo_bar"
    assert sanitize_segment("foo:bar") == "foo_bar"
    assert sanitize_segment('foo"bar<>|?') == "foo_bar____"
    assert sanitize_segment("foo*bar") == "foo_bar"


def test_sanitize_trims_trailing_dots_and_spaces() -> None:
    """Windows disallows trailing dots/spaces on filenames."""
    from shelvr.services.file_layout import sanitize_segment

    assert sanitize_segment("foo.") == "foo"
    assert sanitize_segment("foo   ") == "foo"
    assert sanitize_segment("foo. . .") == "foo"


def test_sanitize_handles_reserved_names() -> None:
    """Windows reserved names (CON, PRN, etc.) get a suffix to avoid collision."""
    from shelvr.services.file_layout import sanitize_segment

    assert sanitize_segment("CON") == "CON_"
    assert sanitize_segment("con") == "con_"  # case-insensitive check
    assert sanitize_segment("PRN") == "PRN_"
    assert sanitize_segment("NUL") == "NUL_"
    assert sanitize_segment("COM1") == "COM1_"
    assert sanitize_segment("LPT9") == "LPT9_"


def test_sanitize_truncates_long_names() -> None:
    from shelvr.services.file_layout import sanitize_segment

    long_title = "x" * 250
    result = sanitize_segment(long_title)
    assert len(result) <= 100


def test_sanitize_empty_becomes_placeholder() -> None:
    from shelvr.services.file_layout import sanitize_segment

    assert sanitize_segment("") == "_"
    assert sanitize_segment("   ") == "_"
    assert sanitize_segment("///") == "_"


def test_compute_target_path_simple(tmp_path: Path) -> None:
    from shelvr.services.file_layout import compute_target_path

    result = compute_target_path(
        library_root=tmp_path,
        primary_author="Ursula K. Le Guin",
        title="A Wizard of Earthsea",
        extension=".epub",
    )
    assert result.parent == tmp_path / "Ursula K. Le Guin" / "A Wizard of Earthsea"
    assert result.name == "A Wizard of Earthsea.epub"


def test_compute_target_path_no_author(tmp_path: Path) -> None:
    from shelvr.services.file_layout import compute_target_path

    result = compute_target_path(
        library_root=tmp_path,
        primary_author=None,
        title="Anonymous Work",
        extension=".pdf",
    )
    assert result.parent == tmp_path / "Unknown Author" / "Anonymous Work"
    assert result.name == "Anonymous Work.pdf"


def test_compute_target_path_sanitizes_all_segments(tmp_path: Path) -> None:
    from shelvr.services.file_layout import compute_target_path

    result = compute_target_path(
        library_root=tmp_path,
        primary_author="Bad/Author:Name",
        title="Title*With?Chars",
        extension=".mobi",
    )
    # Both segments are sanitized
    author_seg = result.parent.parent.name
    title_seg = result.parent.name
    assert "/" not in author_seg and ":" not in author_seg
    assert "*" not in title_seg and "?" not in title_seg


def test_compute_target_path_normalizes_extension_without_dot(tmp_path: Path) -> None:
    """Extension arg can be with or without leading dot."""
    from shelvr.services.file_layout import compute_target_path

    result = compute_target_path(
        library_root=tmp_path,
        primary_author="Author",
        title="Title",
        extension="epub",  # no leading dot
    )
    assert result.name == "Title.epub"


def test_compute_target_path_lowercases_extension(tmp_path: Path) -> None:
    """Extension is lowercased for consistency."""
    from shelvr.services.file_layout import compute_target_path

    result = compute_target_path(
        library_root=tmp_path,
        primary_author="Author",
        title="Title",
        extension=".EPUB",
    )
    assert result.name == "Title.epub"
