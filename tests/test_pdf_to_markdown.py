from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.pdf_to_markdown import extract_markdown, format_markdown, main, normalize_text


def build_test_pdf(text: str) -> bytes:
    stream = f"BT\n/F1 24 Tf\n72 96 Td\n({text}) Tj\nET\n".encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("utf-8") + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    parts = [b"%PDF-1.4\n"]
    offsets: list[int] = []

    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("utf-8"))
        parts.append(obj)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets:
        parts.append(f"{offset:010d} 00000 n \n".encode("utf-8"))

    parts.append(
        f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "utf-8"
        )
    )
    return b"".join(parts)


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
    def test_extract_markdown_reads_a_real_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_pdf = Path(temp_dir) / "sample.pdf"
            input_pdf.write_bytes(build_test_pdf("Hello PDF"))

            self.assertEqual(extract_markdown(input_pdf), "## Page 1\n\nHello PDF")

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

    def test_main_reports_missing_input_file(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            main(["/tmp/does-not-exist.pdf"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("Input PDF not found", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
