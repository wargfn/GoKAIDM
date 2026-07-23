from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.pdf_to_markdown import format_markdown, main, normalize_text


class NormalizeTextTests(unittest.TestCase):
    def test_normalize_text_trims_lines_and_collapses_blank_runs(self) -> None:
        original = "  First line  \n\n\n Second line \n   \nThird line   \n"

        self.assertEqual(
            normalize_text(original),
            "First line\n\nSecond line\n\nThird line",
        )


class FormatMarkdownTests(unittest.TestCase):
    def test_format_markdown_includes_page_headings(self) -> None:
        result = format_markdown([" First page ", "", "Second page"])

        self.assertEqual(result, "## Page 1\n\nFirst page\n\n## Page 3\n\nSecond page")

    def test_format_markdown_can_skip_page_headings(self) -> None:
        result = format_markdown([" First page ", "Second page"], include_page_headings=False)

        self.assertEqual(result, "First page\n\nSecond page")


class MainTests(unittest.TestCase):
    def test_main_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_pdf = temp_path / "sample.pdf"
            output_md = temp_path / "sample.md"
            input_pdf.write_bytes(b"%PDF-1.4\n")

            with patch("tools.pdf_to_markdown.extract_markdown", return_value="Converted text"):
                exit_code = main([str(input_pdf), "--output", str(output_md)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_md.read_text(encoding="utf-8"), "Converted text\n")


if __name__ == "__main__":
    unittest.main()
