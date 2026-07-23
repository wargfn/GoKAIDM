"""
PDF resource loader for GoKAIDM.

Extracts text and metadata from PDF rulebooks and sourcebooks using
``pypdf``.  The extracted content can be bulk-imported into a
:class:`~gokaidm.persistence.ruleset.Ruleset` via the helper methods
on this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PDFPage:
    """Represents a single page extracted from a PDF."""

    page_number: int
    text: str
    source_file: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.text.strip()


# ---------------------------------------------------------------------------
# Loader class
# ---------------------------------------------------------------------------


class PDFLoader:
    """Load and parse PDF files for GoKAIDM resource import.

    Requires the ``pypdf`` package (listed in ``requirements.txt``).

    Example::

        loader = PDFLoader("rulebook.pdf")
        pages = loader.load()
        entries = loader.to_ruleset_entries(category="combat")
    """

    def __init__(self, pdf_path: str | Path) -> None:
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
        self._pages: list[PDFPage] | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, page_range: tuple[int, int] | None = None) -> list[PDFPage]:
        """Extract all (or a range of) pages from the PDF.

        Args:
            page_range: Optional ``(start, end)`` tuple (1-based, inclusive).

        Returns:
            List of :class:`PDFPage` objects.
        """
        try:
            import pypdf  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'pypdf' package is required. Run: pip install pypdf"
            ) from exc

        reader = pypdf.PdfReader(str(self.pdf_path))
        num_pages = len(reader.pages)

        start = 1
        end = num_pages
        if page_range:
            start = max(1, page_range[0])
            end = min(num_pages, page_range[1])

        pages: list[PDFPage] = []
        for i in range(start - 1, end):
            raw = reader.pages[i].extract_text() or ""
            pages.append(
                PDFPage(
                    page_number=i + 1,
                    text=raw,
                    source_file=self.pdf_path.name,
                )
            )

        self._pages = pages
        return pages

    @property
    def pages(self) -> list[PDFPage]:
        if self._pages is None:
            return self.load()
        return self._pages

    # ------------------------------------------------------------------
    # Text utilities
    # ------------------------------------------------------------------

    def full_text(self) -> str:
        """Return the combined text of all loaded pages."""
        return "\n\n".join(p.text for p in self.pages if not p.is_empty())

    def search(self, query: str, case_sensitive: bool = False) -> list[PDFPage]:
        """Return pages containing *query*."""
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        return [p for p in self.pages if pattern.search(p.text)]

    # ------------------------------------------------------------------
    # Ruleset integration
    # ------------------------------------------------------------------

    def to_ruleset_entries(
        self,
        category: str = "general",
        chunk_size: int = 800,
        overlap: int = 100,
    ) -> list[dict[str, Any]]:
        """Convert loaded pages into ruleset-entry dicts suitable for
        :meth:`~gokaidm.persistence.ruleset.Ruleset.add_entry`.

        Each chunk is limited to roughly *chunk_size* characters with an
        *overlap* character window to avoid splitting mid-paragraph.
        """
        entries: list[dict[str, Any]] = []
        for page in self.pages:
            if page.is_empty():
                continue
            chunks = _chunk_text(page.text, chunk_size, overlap)
            for idx, chunk in enumerate(chunks):
                title = f"{self.pdf_path.stem} – p.{page.page_number}"
                if len(chunks) > 1:
                    title += f" (part {idx + 1})"
                entries.append(
                    {
                        "title": title,
                        "content": chunk.strip(),
                        "category": category,
                        "source": f"PDF:{self.pdf_path.name}:{page.page_number}",
                        "tags": [],
                    }
                )
        return entries

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_pdf_info(self) -> dict[str, Any]:
        """Return metadata from the PDF file (author, title, etc.)."""
        try:
            import pypdf  # type: ignore[import-untyped]
        except ImportError:
            return {}
        reader = pypdf.PdfReader(str(self.pdf_path))
        info = reader.metadata or {}
        return {k.lstrip("/"): v for k, v in dict(info).items()}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def extract_text_from_pdf(
    pdf_path: str | Path,
    page_range: tuple[int, int] | None = None,
) -> str:
    """Convenience function – load a PDF and return its full text."""
    loader = PDFLoader(pdf_path)
    loader.load(page_range)
    return loader.full_text()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split *text* into chunks of at most *chunk_size* chars with *overlap*."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to end on a sentence/paragraph boundary
        boundary = max(
            chunk.rfind("\n"), chunk.rfind(". "), chunk.rfind("! "), chunk.rfind("? ")
        )
        if boundary > chunk_size // 2:
            end = start + boundary + 1
            chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks
