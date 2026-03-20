#!/usr/bin/env python3
"""Extract text from a PDF using embedded text layers (pypdf).

Outputs:
- raw/fantasy_age_2e_pdf_text.md
- processed/pdf_extraction_report.json

Usage:
  python work-process/scripts/extract_pdf_text.py \
    --pdf "source_material/<book>.pdf" \
    --text-out work-process/raw/fantasy_age_2e_pdf_text.md \
    --report-out work-process/processed/pdf_extraction_report.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


def normalize_page_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_report(page_texts: list[str]) -> dict:
    char_counts = [len(t) for t in page_texts]
    non_empty = [c for c in char_counts if c > 0]
    total_pages = len(page_texts)
    text_pages = len(non_empty)
    avg_chars = (sum(non_empty) / len(non_empty)) if non_empty else 0.0

    quality = "good"
    recommendations = []
    if text_pages == 0:
        quality = "poor"
        recommendations.append("No embedded text found. OCR required.")
    elif text_pages / max(1, total_pages) < 0.7:
        quality = "mixed"
        recommendations.append("Many pages have little/no text. Consider page-level OCR fallback.")
    elif avg_chars < 900:
        quality = "mixed"
        recommendations.append("Text density is low; verify extraction quality and layout handling.")

    recommendations.append("If quality is mixed/poor, install OCR tools (tesseract + poppler) and rerun with OCR pipeline.")

    return {
        "total_pages": total_pages,
        "pages_with_text": text_pages,
        "pages_without_text": total_pages - text_pages,
        "avg_chars_per_text_page": round(avg_chars, 2),
        "quality": quality,
        "recommendations": recommendations,
    }


def extract(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        pages.append(normalize_page_text(raw))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF text from embedded text layer")
    parser.add_argument("--pdf", required=True, help="Path to source PDF")
    parser.add_argument("--text-out", required=True, help="Output markdown path")
    parser.add_argument("--report-out", required=True, help="Output JSON report path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    text_out = Path(args.text_out)
    report_out = Path(args.report_out)

    page_texts = extract(pdf_path)
    report = build_report(page_texts)

    lines = []
    lines.append(f"# Extracted Text: {pdf_path.name}")
    lines.append("")
    for i, text in enumerate(page_texts, start=1):
        lines.append(f"## Page {i}")
        lines.append("")
        lines.append(text if text else "[NO_TEXT_EXTRACTED]")
        lines.append("")

    text_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    text_out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    report_out.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
