#!/usr/bin/env python3
"""Run the canonical Fantasy AGE extraction pipeline using PDF as default source.

Default flow:
1) Extract text from source PDF -> work-process/raw/fantasy_age_2e_pdf_text.md
2) Clean + chapter structure -> work-process/processed/
3) Build chunks/entities -> work-process/
4) QA + strict validation -> work-process/processed/

Usage:
  python work-process/scripts/run_canonical_pipeline.py
  python work-process/scripts/run_canonical_pipeline.py --pdf "source_material/<book>.pdf"
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_PDF = (
    "source_material/Fantasy Age Core Rulebook -- Crystal Frasier, Steve Kenson, Chris Pramas, Malcolm -- "
    "2023 -- Green Ronin Publishing -- 9781949160321 -- af8d7d40c4c1ed6f1121913768a331bd -- Anna\u2019s Archive.pdf"
)


def run_cmd(cmd: list[str], cwd: Path) -> None:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"[pipeline] {printable}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run canonical PDF-first rules pipeline")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Source PDF path")
    parser.add_argument("--outroot", default="work-process", help="Output root folder")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    outroot = Path(args.outroot)
    raw_text = outroot / "raw" / "fantasy_age_2e_pdf_text.md"
    pdf_report = outroot / "processed" / "pdf_extraction_report.json"
    processed = outroot / "processed"

    scripts = outroot / "scripts"

    run_cmd(
        [
            sys.executable,
            str(scripts / "extract_pdf_text.py"),
            "--pdf",
            args.pdf,
            "--text-out",
            str(raw_text),
            "--report-out",
            str(pdf_report),
        ],
        repo_root,
    )

    run_cmd(
        [
            sys.executable,
            str(scripts / "prepare_rules_corpus.py"),
            "--input",
            str(raw_text),
            "--outdir",
            str(processed),
        ],
        repo_root,
    )

    run_cmd(
        [
            sys.executable,
            str(scripts / "build_rules_knowledge_base.py"),
            "--cleaned",
            str(processed / "rules_cleaned.md"),
            "--structured",
            str(processed / "rules_structured.json"),
            "--outroot",
            str(outroot),
        ],
        repo_root,
    )

    run_cmd(
        [
            sys.executable,
            str(scripts / "qa_extraction_report.py"),
            "--outroot",
            str(outroot),
        ],
        repo_root,
    )

    run_cmd(
        [
            sys.executable,
            str(scripts / "strict_validate_rules.py"),
            "--outroot",
            str(outroot),
        ],
        repo_root,
    )

    print("[pipeline] complete")
    print(f"[pipeline] strict report: {processed / 'strict_validation_report.md'}")


if __name__ == "__main__":
    main()
