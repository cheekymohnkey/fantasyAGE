#!/usr/bin/env python3
"""Generate QA diagnostics for extracted rules chunks/entities.

Usage:
  python work-process/scripts/qa_extraction_report.py \
    --outroot work-process
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def missing_fields(rows: Iterable[dict], required: List[str], kind: str) -> List[dict]:
    issues = []
    for row in rows:
        missing = [k for k in required if k not in row or row.get(k) in (None, "", [])]
        if missing:
            issues.append({"kind": kind, "id": row.get("id"), "missing": missing})
    return issues


def duplicate_ids(rows: Iterable[dict], kind: str) -> List[dict]:
    counts = Counter(r.get("id") for r in rows)
    return [{"kind": kind, "id": k, "count": v} for k, v in counts.items() if k and v > 1]


def duplicate_names(rows: Iterable[dict], kind: str) -> List[dict]:
    counts = Counter((r.get("name") or "").strip().lower() for r in rows if r.get("name"))
    return [{"kind": kind, "name": k, "count": v} for k, v in counts.items() if k and v > 1]


def qa_entities(entity_name: str, rows: List[dict]) -> dict:
    findings: Dict[str, List[dict]] = defaultdict(list)

    findings["missing_core_fields"] = missing_fields(rows, ["id", "type", "name"], entity_name)
    findings["duplicate_ids"] = duplicate_ids(rows, entity_name)
    findings["duplicate_names"] = duplicate_names(rows, entity_name)

    if entity_name == "spells":
        for r in rows:
            if not r.get("arcana"):
                findings["missing_arcana"].append({"id": r.get("id"), "name": r.get("name")})
            if not r.get("casting_requirement"):
                findings["missing_casting_requirement"].append({"id": r.get("id"), "name": r.get("name")})
    if entity_name == "stunts":
        for r in rows:
            if r.get("cost") is None:
                findings["missing_cost"].append({"id": r.get("id"), "name": r.get("name")})
            if not r.get("effect"):
                findings["missing_effect"].append({"id": r.get("id"), "name": r.get("name")})
    if entity_name == "talents":
        for r in rows:
            if not r.get("degrees"):
                findings["missing_degrees"].append({"id": r.get("id"), "name": r.get("name")})

    unresolved_marker = "OCR block unresolved"
    for r in rows:
        notes = r.get("notes") or []
        if any(unresolved_marker in n for n in notes if isinstance(n, str)):
            findings["fallback_snippets"].append({"id": r.get("id"), "name": r.get("name")})

    counts = {k: len(v) for k, v in findings.items()}
    return {"entity": entity_name, "count": len(rows), "issue_counts": counts, "findings": findings}


def qa_chunks(chunks: List[dict]) -> dict:
    findings: Dict[str, List[dict]] = defaultdict(list)
    for c in chunks:
        cid = c.get("id")
        text = c.get("text") or ""
        tags = c.get("tags") or []

        if not text:
            findings["missing_text"].append({"id": cid})
        if len(text) < 120:
            findings["very_short_text"].append({"id": cid, "len": len(text)})
        if len(text) > 2800:
            findings["very_long_text"].append({"id": cid, "len": len(text)})
        if not tags:
            findings["missing_tags"].append({"id": cid})
        if c.get("rule_type") == "mechanic" and "mechanic" not in tags:
            findings["rule_type_tag_mismatch"].append({"id": cid, "rule_type": c.get("rule_type"), "tags": tags})

    issue_counts = {k: len(v) for k, v in findings.items()}
    return {"count": len(chunks), "issue_counts": issue_counts, "findings": findings}


def build_markdown(summary: dict) -> str:
    lines = []
    lines.append("# Extraction QA Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Chunks analyzed: {summary['chunks']['count']}")
    lines.append(f"- Entity files analyzed: {len(summary['entities'])}")
    lines.append("")

    lines.append("## Chunk Issues")
    lines.append("")
    for k, v in sorted(summary["chunks"]["issue_counts"].items()):
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Entity Issues")
    lines.append("")
    for entity_report in summary["entities"]:
        lines.append(f"### {entity_report['entity']}")
        lines.append(f"- Rows: {entity_report['count']}")
        for k, v in sorted(entity_report["issue_counts"].items()):
            lines.append(f"- {k}: {v}")
        lines.append("")

    lines.append("## Suggested Next QA Actions")
    lines.append("")
    lines.append("- Review `missing_cost` stunts and fill deterministic costs from chapter stunt tables.")
    lines.append("- Review `missing_arcana` spells and map each spell to an arcana family.")
    lines.append("- Review `fallback_snippets` entity notes and replace with fully bounded section text.")
    lines.append("- Split any `very_long_text` chunks by subsection boundaries.")
    lines.append("")
    return "\n".join(lines)


def run(outroot: Path) -> None:
    entities_dir = outroot / "entities"
    chunks_path = outroot / "chunks" / "rules_chunks_structured.jsonl"

    chunks = read_jsonl(chunks_path)
    chunk_report = qa_chunks(chunks)

    entity_reports = []
    for path in sorted(entities_dir.glob("*.json")):
        rows = read_json(path)
        if isinstance(rows, list):
            entity_reports.append(qa_entities(path.stem, rows))

    summary = {
        "chunks": chunk_report,
        "entities": entity_reports,
    }

    write_json(outroot / "processed" / "qa_report.json", summary)
    write_text(outroot / "processed" / "qa_report.md", build_markdown(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QA extracted rule chunks and entities.")
    parser.add_argument("--outroot", required=True, help="Output root (e.g., work-process)")
    args = parser.parse_args()
    run(Path(args.outroot))
