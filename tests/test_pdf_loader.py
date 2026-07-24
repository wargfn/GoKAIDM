"""Tests for PDF resource loader."""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gokaidm.resources.pdf_loader import PDFLoader, PDFPage, extract_text_from_pdf, _chunk_text


# ---------------------------------------------------------------------------
# _chunk_text helper
# ---------------------------------------------------------------------------


def test_chunk_text_short_text() -> None:
    chunks = _chunk_text("Short text.", chunk_size=800, overlap=100)
    assert chunks == ["Short text."]


def test_chunk_text_long_text() -> None:
    # Create text longer than chunk_size
    long_text = "This is a sentence. " * 100  # ~2000 chars
    chunks = _chunk_text(long_text, chunk_size=800, overlap=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 900  # chunk_size + a bit for boundary search


def test_chunk_text_with_newline_boundary() -> None:
    text = "A" * 400 + "\n" + "B" * 400
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# PDFPage
# ---------------------------------------------------------------------------


def test_pdf_page_is_empty() -> None:
    empty = PDFPage(page_number=1, text="   \n\t  ")
    nonempty = PDFPage(page_number=1, text="Some text.")
    assert empty.is_empty()
    assert not nonempty.is_empty()


# ---------------------------------------------------------------------------
# PDFLoader – file not found
# ---------------------------------------------------------------------------


def test_loader_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        PDFLoader("/nonexistent/path/to.pdf")


# ---------------------------------------------------------------------------
# PDFLoader – mocked pypdf
# ---------------------------------------------------------------------------


def _make_mock_reader(pages_text: list[str]) -> MagicMock:
    """Build a minimal mock pypdf.PdfReader."""
    reader = MagicMock()
    mock_pages = []
    for text in pages_text:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    reader.pages = mock_pages
    reader.metadata = {}
    return reader


def test_loader_load_all_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader(["Page one text.", "Page two text."])):
        loader = PDFLoader(pdf_path)
        pages = loader.load()

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "Page one text." in pages[0].text


def test_loader_load_page_range(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    texts = [f"Page {i}" for i in range(1, 6)]
    with patch("pypdf.PdfReader", return_value=_make_mock_reader(texts)):
        loader = PDFLoader(pdf_path)
        pages = loader.load(page_range=(2, 4))

    assert len(pages) == 3
    assert pages[0].page_number == 2
    assert pages[-1].page_number == 4


def test_loader_full_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader(["Intro text.", "More text."])):
        loader = PDFLoader(pdf_path)
        loader.load()
        text = loader.full_text()

    assert "Intro text." in text
    assert "More text." in text


def test_loader_search(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader([
        "Combat rules and attack bonuses.",
        "Magic spells and mana costs.",
        "More combat scenarios.",
    ])):
        loader = PDFLoader(pdf_path)
        loader.load()
        results = loader.search("combat")

    assert len(results) == 2


def test_loader_to_ruleset_entries(tmp_path: Path) -> None:
    pdf_path = tmp_path / "rulebook.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader([
        "Rule text for initiative. " * 10,
        "Empty page placeholder.",
    ])):
        loader = PDFLoader(pdf_path)
        loader.load()
        entries = loader.to_ruleset_entries(category="combat")

    assert len(entries) >= 1
    for entry in entries:
        assert entry["category"] == "combat"
        assert "PDF:rulebook.pdf:" in entry["source"]
        assert entry["title"]
        assert entry["content"]


def test_loader_empty_pages_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader(["", "   ", "Real content here."])):
        loader = PDFLoader(pdf_path)
        loader.load()
        entries = loader.to_ruleset_entries()

    assert len(entries) == 1
    assert "Real content" in entries[0]["content"]


# ---------------------------------------------------------------------------
# extract_text_from_pdf convenience function
# ---------------------------------------------------------------------------


def test_extract_text_from_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    with patch("pypdf.PdfReader", return_value=_make_mock_reader(["Chapter 1", "Chapter 2"])):
        text = extract_text_from_pdf(pdf_path)

    assert "Chapter 1" in text
    assert "Chapter 2" in text


def test_extract_text_from_pdf_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/no/such/file.pdf")
