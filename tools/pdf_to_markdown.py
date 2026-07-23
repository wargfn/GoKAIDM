#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'pypdf'. Install it with: python3 -m pip install -r requirements.txt"
    ) from exc


def normalize_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    previous_blank = True

    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned.append(stripped)
            previous_blank = False
            continue

        if not previous_blank and cleaned:
            cleaned.append("")
        previous_blank = True

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def format_markdown(page_texts: Iterable[str], include_page_headings: bool = True) -> str:
    sections: list[str] = []

    for page_number, page_text in enumerate(page_texts, start=1):
        normalized = normalize_text(page_text)
        if not normalized:
            continue

        if include_page_headings:
            sections.append(f"## Page {page_number}\n\n{normalized}")
        else:
            sections.append(normalized)

    return "\n\n".join(sections).strip()


def extract_markdown(pdf_path: Path, include_page_headings: bool = True) -> str:
    reader = PdfReader(str(pdf_path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    return format_markdown(page_texts, include_page_headings=include_page_headings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF file and emit markdown-friendly output."
    )
    parser.add_argument("input_pdf", type=Path, help="Path to the source PDF file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output markdown file. Defaults to stdout.",
    )
    parser.add_argument(
        "--no-page-headings",
        action="store_true",
        help="Do not include per-page markdown headings.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input_pdf.is_file():
        parser.error(f"Input PDF not found: {args.input_pdf}")

    markdown = extract_markdown(
        args.input_pdf, include_page_headings=not args.no_page_headings
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown + ("\n" if markdown else ""), encoding="utf-8")
        return 0

    sys.stdout.write(markdown)
    if markdown:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
