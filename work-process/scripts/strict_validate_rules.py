#!/usr/bin/env python3
"""Strict validation for extracted RPG rules artifacts.

Creates:
- processed/strict_validation_report.json
- processed/strict_validation_report.md
- processed/manual_correction_queue.jsonl

Usage:
  python work-process/scripts/strict_validate_rules.py --outroot work-process
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def severity_weight(level: str) -> int:
    return {"critical": 100, "high": 70, "medium": 40, "low": 20}.get(level, 10)


def add_issue(issues: List[dict], queue: List[dict], *, entity_file: str, entity_id: str, entity_type: str, field: str, reason: str, severity: str, recommended_fix: str) -> None:
    issue = {
        "entity_file": entity_file,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "field": field,
        "reason": reason,
        "severity": severity,
        "recommended_fix": recommended_fix,
    }
    issues.append(issue)
    queue.append(issue)


def validate_entities(outroot: Path) -> Dict[str, Any]:
    entities_dir = outroot / "entities"
    issues: List[dict] = []
    queue: List[dict] = []
    per_file_summary: Dict[str, dict] = {}
    required_non_empty = {"ancestries.json", "classes.json", "talents.json", "arcana.json", "spells.json", "stunts.json"}

    for path in sorted(entities_dir.glob("*.json")):
        rows = read_json(path)
        if not isinstance(rows, list):
            continue

        if path.name in required_non_empty and len(rows) == 0:
            add_issue(
                issues,
                queue,
                entity_file=path.name,
                entity_id="<file>",
                entity_type=path.stem,
                field="rows",
                reason="Required entity file is empty",
                severity="critical",
                recommended_fix="Improve extraction boundaries/patterns and regenerate this entity file.",
            )

        duplicate_name_counts: Dict[str, int] = {}
        for row in rows:
            name = (row.get("name") or "").strip().lower()
            if name:
                duplicate_name_counts[name] = duplicate_name_counts.get(name, 0) + 1

        file_issues_before = len(issues)
        for row in rows:
            entity_id = row.get("id", "")
            entity_type = row.get("type", path.stem.rstrip("s"))
            name = row.get("name", "")

            if not entity_id or not name:
                add_issue(
                    issues,
                    queue,
                    entity_file=path.name,
                    entity_id=entity_id or "<missing-id>",
                    entity_type=entity_type,
                    field="id/name",
                    reason="Missing id or name",
                    severity="critical",
                    recommended_fix="Populate required identifiers from canonical source section.",
                )

            notes = row.get("notes") or []
            if any("OCR block unresolved" in str(n) for n in notes):
                add_issue(
                    issues,
                    queue,
                    entity_file=path.name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    field="notes",
                    reason="Fallback OCR snippet in place of bounded section extraction",
                    severity="high",
                    recommended_fix="Replace note with validated section-bounded extraction text.",
                )

            dup_count = duplicate_name_counts.get((name or "").strip().lower(), 0)
            if dup_count > 1:
                add_issue(
                    issues,
                    queue,
                    entity_file=path.name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    field="name",
                    reason=f"Duplicate entity name appears {dup_count} times",
                    severity="medium",
                    recommended_fix="Merge duplicates or disambiguate IDs/names by category and source section.",
                )

            if path.name == "spells.json":
                if row.get("tier") in (None, "", "Unknown"):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="tier",
                        reason="Spell tier unresolved",
                        severity="high",
                        recommended_fix="Infer Novice/Expert/Master from local heading context.",
                    )
                if not row.get("effect"):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="effect",
                        reason="Spell effect text missing",
                        severity="high",
                        recommended_fix="Extract effect sentence block after spell header.",
                    )
                if not row.get("target") and not row.get("range") and not row.get("duration"):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="target/range/duration",
                        reason="Spell structured fields are missing",
                        severity="medium",
                        recommended_fix="Parse target, range, and duration from spell format lines.",
                    )

            if path.name == "stunts.json":
                if row.get("cost") is None:
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="cost",
                        reason="Stunt cost missing",
                        severity="high",
                        recommended_fix="Map cost from stunt table row.",
                    )
                if not row.get("effect"):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="effect",
                        reason="Stunt effect missing",
                        severity="high",
                        recommended_fix="Extract stunt effect sentence from table row.",
                    )
                if "Derived from OCR text; verify manually." in (row.get("effect") or ""):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="effect",
                        reason="Stunt effect is placeholder text",
                        severity="medium",
                        recommended_fix="Replace placeholder with source-grounded effect.",
                    )

            if path.name == "talents.json":
                if not row.get("degrees"):
                    add_issue(
                        issues,
                        queue,
                        entity_file=path.name,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        field="degrees",
                        reason="Talent has no degree entries",
                        severity="high",
                        recommended_fix="Extract Novice/Expert/Master degree effects.",
                    )

        file_issues_after = len(issues)
        per_file_summary[path.name] = {
            "rows": len(rows),
            "issues": file_issues_after - file_issues_before,
        }

    queue.sort(
        key=lambda x: (
            -severity_weight(x["severity"]),
            x["entity_file"],
            x["entity_id"],
            x["field"],
        )
    )

    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    penalty = int(len(issues) * 0.15) + (critical_count * 25)
    score = max(0, 100 - min(100, penalty))
    gate_pass = score >= 85 and critical_count == 0

    return {
        "quality_score": score,
        "gate_pass": gate_pass,
        "total_issues": len(issues),
        "issues_by_severity": {
            "critical": sum(1 for i in issues if i["severity"] == "critical"),
            "high": sum(1 for i in issues if i["severity"] == "high"),
            "medium": sum(1 for i in issues if i["severity"] == "medium"),
            "low": sum(1 for i in issues if i["severity"] == "low"),
        },
        "per_file_summary": per_file_summary,
        "sample_issues": issues[:80],
        "manual_correction_queue": queue,
    }


def build_markdown(report: dict) -> str:
    lines: List[str] = []
    lines.append("# Strict Validation Report")
    lines.append("")
    lines.append("## Gate Result")
    lines.append("")
    lines.append(f"- `quality_score`: {report['quality_score']}")
    lines.append(f"- `gate_pass`: {report['gate_pass']}")
    lines.append(f"- `total_issues`: {report['total_issues']}")
    lines.append("")
    lines.append("## Severity Breakdown")
    lines.append("")
    for k, v in report["issues_by_severity"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Per-File Summary")
    lines.append("")
    for fn, data in report["per_file_summary"].items():
        lines.append(f"- {fn}: rows={data['rows']}, issues={data['issues']}")
    lines.append("")
    lines.append("## Top Priority Fix Queue (first 30)")
    lines.append("")
    for i, item in enumerate(report["manual_correction_queue"][:30], start=1):
        lines.append(
            f"{i}. [{item['severity']}] {item['entity_file']} | {item['entity_id']} | {item['field']} | {item['reason']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Strict validation for extracted rules artifacts")
    parser.add_argument("--outroot", required=True, help="Output root folder (e.g. work-process)")
    args = parser.parse_args()

    outroot = Path(args.outroot)
    report = validate_entities(outroot)

    report_out = {
        "quality_score": report["quality_score"],
        "gate_pass": report["gate_pass"],
        "total_issues": report["total_issues"],
        "issues_by_severity": report["issues_by_severity"],
        "per_file_summary": report["per_file_summary"],
        "sample_issues": report["sample_issues"],
    }

    write_json(outroot / "processed" / "strict_validation_report.json", report_out)
    write_text(outroot / "processed" / "strict_validation_report.md", build_markdown(report))
    write_jsonl(outroot / "processed" / "manual_correction_queue.jsonl", report["manual_correction_queue"])


if __name__ == "__main__":
    main()
