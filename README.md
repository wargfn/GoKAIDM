# GoKAIDM
Gates of Krystalia AI DM instance for Solo Games.

## PDF to Markdown tool

This repository includes a small Python 3 utility for extracting text from PDF files into markdown-friendly text.

### Install

```bash
python3 -m pip install -r requirements.txt
```

### Usage

Write markdown to stdout:

```bash
python3 tools/pdf_to_markdown.py input.pdf
```

Write markdown to a file:

```bash
python3 tools/pdf_to_markdown.py input.pdf --output output.md
```

Skip page headings:

```bash
python3 tools/pdf_to_markdown.py input.pdf --no-page-headings
```
