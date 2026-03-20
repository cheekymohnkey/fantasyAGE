#!/usr/bin/env python3
"""Build structure-based chunks and extracted rule entities from cleaned corpus.

Usage:
  python work-process/scripts/build_rules_knowledge_base.py \
    --cleaned work-process/processed/rules_cleaned.md \
    --structured work-process/processed/rules_structured.json \
    --outroot work-process
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

KNOWN_ANCESTRIES = ["Draak", "Dwarf", "Elf", "Gnome", "Goblin", "Halfling", "Human", "Orc", "Wildfolk"]
KNOWN_CLASSES = ["Envoy", "Mage", "Rogue", "Warrior"]


def slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "untitled"


def spaced_token(token: str) -> str:
    out = []
    for ch in token:
        if ch.isalpha():
            out.append(re.escape(ch) + r"\s*")
        else:
            out.append(re.escape(ch))
    return "".join(out)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def chapter_spans(clean_text: str, structured: dict) -> List[dict]:
    rows = []
    for ch in structured.get("chapters", []):
        rows.append(
            {
                "number": ch["number"],
                "title": ch["title"],
                "start": ch["start_offset"],
                "end": ch["end_offset"],
                "text": clean_text[ch["start_offset"] : ch["end_offset"]].strip(),
            }
        )
    return rows


def is_heading_like(line: str) -> bool:
    if not line:
        return False
    if line.startswith("-") or line.startswith("*") or line.startswith("\u2022"):
        return False
    if line.endswith("."):
        return False
    if len(line) > 90:
        return False
    if re.match(r"^\d+:\s+", line):
        return True
    if re.match(r"^Step\s+\d+", line):
        return True
    words = line.split()
    if len(words) <= 8 and sum(1 for w in words if w[:1].isupper()) >= max(1, len(words) - 1):
        return True
    return False


def infer_rule_type(text: str, chapter_title: str) -> str:
    t = (chapter_title + " " + text[:220]).lower()
    if "stunt" in t:
        return "stunt_rule"
    if any(k in t for k in ["spell", "arcana", "casting", "magic points"]):
        return "spell_rule"
    if any(k in t for k in ["attack", "damage", "combat", "defense", "health", "condition"]):
        return "combat_rule"
    if any(k in t for k in ["equipment", "weapon", "armor", "currency"]):
        return "equipment_rule"
    if any(k in t for k in ["game master", "gm", "campaign", "adventure"]):
        return "gm_guidance"
    if any(k in t for k in ["example of play", "example"]):
        return "example_of_play"
    if any(k in t for k in ["lore", "setting", "breakwater", "stranger shores"]):
        return "setting_lore"
    return "mechanic"


def infer_entity_type(text: str) -> str:
    t = text.lower()
    if "ability test" in t:
        return "ability_test"
    if "stunt" in t:
        return "stunt"
    if "arcana" in t or "spell" in t:
        return "spell"
    if "talent" in t:
        return "talent"
    if "ancestry" in t:
        return "ancestry"
    if "class" in t:
        return "class"
    if "condition" in t:
        return "condition"
    return "rule"


def infer_audience(chapter_no: int, chapter_title: str, text: str) -> str:
    tt = (chapter_title + " " + text[:160]).lower()
    if chapter_no in {7, 8, 11} or "game master" in tt:
        return "gm"
    if "gm" in tt and "player" not in tt:
        return "gm"
    return "shared"


def structural_chunks(chapters: List[dict]) -> List[dict]:
    chunks: List[dict] = []

    for chapter in chapters:
        lines = [ln.strip() for ln in chapter["text"].splitlines() if ln.strip()]
        cur_section = chapter["title"]
        buf: List[str] = []
        section_idx = 0

        def flush() -> None:
            nonlocal section_idx, buf
            if not buf:
                return
            text = "\n".join(buf).strip()
            chunk_id = f"ch{chapter['number']:02d}.{slugify(cur_section)}.{section_idx:03d}"
            tags = sorted({
                "mechanic" if infer_rule_type(text, chapter["title"]) == "mechanic" else infer_rule_type(text, chapter["title"]),
                slugify(chapter["title"]),
                slugify(cur_section),
            })
            chunks.append(
                {
                    "id": chunk_id,
                    "source_book": "Fantasy AGE Core Rulebook 2nd Edition",
                    "chapter_no": chapter["number"],
                    "chapter_title": chapter["title"],
                    "section_title": cur_section,
                    "subsection_title": None,
                    "page_start": None,
                    "page_end": None,
                    "rule_type": infer_rule_type(text, chapter["title"]),
                    "entity_type": infer_entity_type(text),
                    "audience": infer_audience(chapter["number"], chapter["title"], text),
                    "tags": tags,
                    "text": text,
                    "cross_refs": [],
                }
            )
            section_idx += 1
            buf = []

        for line in lines:
            if is_heading_like(line):
                if buf and len(" ".join(buf)) > 250:
                    flush()
                if re.match(r"^\d+:\s+", line):
                    cur_section = re.sub(r"^\d+:\s+", "", line).strip()
                else:
                    cur_section = line
                continue
            buf.append(line)
            if len(" ".join(buf)) > 2200:
                flush()

        flush()

    # Deduplicate very noisy repeats.
    seen = set()
    deduped = []
    for c in chunks:
        key = (c["chapter_no"], c["section_title"], c["text"][:260])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def find_block(text: str, heading: str, next_headings: List[str]) -> str:
    pat = re.compile(rf"(?m)^\s*{re.escape(heading)}\s*$")
    m = pat.search(text)
    if not m:
        return ""
    start = m.end()
    end = len(text)
    for nh in next_headings:
        nm = re.compile(rf"(?m)^\s*{re.escape(nh)}\s*$").search(text, start)
        if nm:
            end = min(end, nm.start())
    return text[start:end].strip()


def mention_snippet(text: str, token: str, radius: int = 900) -> str:
    m = re.search(rf"\b{re.escape(token)}\b", text, flags=re.IGNORECASE)
    if not m:
        return ""
    s = max(0, m.start() - radius)
    e = min(len(text), m.end() + radius)
    return text[s:e].strip()


def extract_ancestries(ch1_text: str) -> List[dict]:
    entities = []
    for i, name in enumerate(KNOWN_ANCESTRIES):
        next_heads = KNOWN_ANCESTRIES[i + 1 :] + ["Step 4 Backgrounds", "Step 5 Classes"]
        block = find_block(ch1_text, name, next_heads)
        note_text = block[:2200] if block else mention_snippet(ch1_text, name)
        entities.append(
            {
                "id": f"ancestry.{slugify(name)}",
                "type": "ancestry",
                "name": name,
                "description": (block.split("\n", 1)[0] if block else f"{name} ancestry entry; OCR block unresolved")[0:300],
                "starting_benefits": [],
                "languages": [],
                "base_speed_rule": None,
                "benefit_table": [],
                "talent_links": [],
                "notes": [note_text] if note_text else [],
            }
        )
    return entities


def extract_classes(ch1_text: str) -> List[dict]:
    entities = []
    for i, name in enumerate(KNOWN_CLASSES):
        next_heads = KNOWN_CLASSES[i + 1 :] + ["Step 6 Equipment"]
        block = find_block(ch1_text, name, next_heads)
        note_text = block[:2600] if block else mention_snippet(ch1_text, name)

        level_progression = []
        for lm in re.finditer(r"(?m)^\s*level\s+(\d+)\s*[:.-]?\s*(.+)$", block, flags=re.IGNORECASE):
            level_progression.append({"level": int(lm.group(1)), "features": [lm.group(2).strip()]})

        entities.append(
            {
                "id": f"class.{slugify(name)}",
                "type": "class",
                "name": name,
                "description": (block.split("\n", 1)[0] if block else f"{name} class entry; OCR block unresolved")[0:350],
                "core_features": [],
                "starting_hp_rule": None,
                "starting_focuses": [],
                "starting_talents": [],
                "level_progression": level_progression,
                "class_stunts": [],
                "related_entities": [],
                "notes": [note_text] if note_text else [],
            }
        )
    return entities


def extract_talents(ch3_text: str) -> List[dict]:
    # Heuristic: title-like lines with nearby Novice/Expert/Master markers.
    lines = [ln.strip() for ln in ch3_text.splitlines()]
    talents = []
    for idx, line in enumerate(lines):
        if not line or len(line) > 48:
            continue
        if re.match(r"(?i)^t\s*a\s*l\s*e\s*n\s*t\s*s$", line.replace(" ", "")):
            continue
        if re.search(r"talent|focus|specialization|chapter|table", line, flags=re.IGNORECASE):
            continue
        if not re.match(r"^[A-Za-z][A-Za-z'\- ]+$", line):
            continue

        window = "\n".join(lines[idx + 1 : idx + 80])
        if not re.search(
            rf"(?i){spaced_token('novice')}|{spaced_token('expert')}|{spaced_token('master')}",
            window,
        ):
            continue

        degrees = []
        for degree in ["Novice", "Expert", "Master"]:
            m = re.search(
                rf"(?i){spaced_token(degree)}(?:\s*[-\u2013\u2014]\s*[A-Za-z\s]+)?\s*:\s*(.+)",
                window,
            )
            if m:
                degrees.append({"degree": degree, "effects": [m.group(1).strip()]})

        # Some specialization-as-talent entries include long preamble text; scan deeper if degrees were missed.
        if not degrees:
            fallback_window = "\n".join(lines[idx + 1 : idx + 220])
            for degree in ["Novice", "Expert", "Master"]:
                m = re.search(
                    rf"(?is){spaced_token(degree)}(?:\s*[-\u2013\u2014]\s*[A-Za-z\s]+)?\s*:\s*(.+?)(?:\n\s*(?:{spaced_token('novice')}|{spaced_token('expert')}|{spaced_token('master')})|$)",
                    fallback_window,
                )
                if m:
                    effect = re.sub(r"\s+", " ", m.group(1)).strip()
                    degrees.append({"degree": degree, "effects": [effect]})

        talents.append(
            {
                "id": f"talent.{slugify(line)}",
                "type": "talent",
                "name": line,
                "description": window[:260],
                "degrees": degrees,
                "prerequisites": [],
                "related_rules": [],
            }
        )

    # Deduplicate by id.
    uniq = {}
    for t in talents:
        uniq[t["id"]] = t
    return list(uniq.values())


def extract_arcana_and_spells(ch5_text: str) -> Tuple[List[dict], List[dict]]:
    arcana = []
    spells = []

    arcana_names = sorted(set(re.findall(r"(?im)^\s*([A-Za-z]+\s+Arcana)\s*$", ch5_text)))
    for an in arcana_names:
        aid = f"arcana.{slugify(an.replace(' Arcana', ''))}"
        arcana.append(
            {
                "id": aid,
                "type": "arcana",
                "name": an,
                "description": "",
                "spells": [],
            }
        )

    req_word = spaced_token("requirements")
    header_re = re.compile(rf"(?im)^\s*([A-Za-z][A-Za-z'\- ]{{2,60}})\s+{req_word}\s*:\s+(.+)$")
    headers = list(header_re.finditer(ch5_text))
    for idx, m in enumerate(headers):
        spell_name = m.group(1).strip()
        req = m.group(2).strip()
        if "Arcana" not in req and "arcana" not in req:
            continue
        body_start = m.end()
        body_end = headers[idx + 1].start() if idx + 1 < len(headers) else len(ch5_text)
        body = ch5_text[body_start:body_end].strip()

        lines = body.splitlines()
        stat_line = lines[0].strip() if lines else ""
        spell_type = None
        m_type = re.search(rf"(?i){spaced_token('spell type')}\s*:\s*([A-Za-z/ ,]+)", stat_line)
        if m_type:
            spell_type = re.sub(r"\s+", " ", m_type.group(1)).strip()

        target_value = None
        m_tn_num = re.search(rf"(?i){spaced_token('target number')}\s*:\s*(\d+)", body)
        if m_tn_num:
            target_value = int(m_tn_num.group(1))
        else:
            m_tn_txt = re.search(rf"(?i){spaced_token('target number')}\s*:\s*([^\n]+)", body)
            if m_tn_txt:
                target_value = re.sub(r"\s+", " ", m_tn_txt.group(1)).strip()

        description_lines = lines[1:] if len(lines) > 1 else []
        description = "\n".join(description_lines).strip()
        if description.startswith("Spell Format"):
            description = ""

        arc = None
        arc_m = re.search(r"([A-Za-z]+) Arcana", req)
        if arc_m:
            arc = arc_m.group(1)
        spell_id = f"spell.{slugify(arc or 'unknown')}.{slugify(spell_name)}"
        spells.append(
            {
                "id": spell_id,
                "type": "spell",
                "name": spell_name,
                "arcana": arc,
                "tier": "Novice" if "novice" in req.lower() else ("Expert" if "expert" in req.lower() else ("Master" if "master" in req.lower() else "Unknown")),
                "casting_requirement": req,
                "target": target_value,
                "range": None,
                "duration": None,
                "effect": description,
                "stunt_interactions": [],
                "tags": ["spell"] + ([slugify(spell_type)] if spell_type else []),
            }
        )

    # Link spells to arcana objects.
    by_arc = {a["name"].replace(" Arcana", "").lower(): a for a in arcana}
    for s in spells:
        key = (s.get("arcana") or "").lower()
        if key in by_arc:
            by_arc[key]["spells"].append(s["id"])

    # Deduplicate spell ids.
    uniq_spells = {}
    for s in spells:
        uniq_spells[s["id"]] = s

    return arcana, list(uniq_spells.values())


def extract_stunts(ch6_text: str) -> List[dict]:
    stunts = []

    # Pattern 1: "You can perform the X stunt(s) ..."
    for m in re.finditer(r"(?i)perform the\s+([A-Za-z][A-Za-z'\- ]{2,40})\s+stunts?", ch6_text):
        name = m.group(1).strip()
        sid = f"stunt.derived.{slugify(name)}"
        stunts.append(
            {
                "id": sid,
                "type": "stunt",
                "name": name,
                "category": "unknown",
                "cost": None,
                "trigger": "successful test or attack with doubles generating stunt points",
                "effect": "Derived from OCR text; verify manually.",
                "restrictions": [],
                "tags": ["stunt"],
            }
        )

    # Table-like row extraction, capturing optional inline effect text.
    line_re = re.compile(r"^\s*([A-Z][A-Za-z'\- ]{2,42})\s+(\d+(?:-\d+)?)\s*\+?\s*SP\b(?:\s+(.+))?\s*$")
    for line in ch6_text.splitlines():
        m = line_re.match(line)
        if not m:
            continue
        name = m.group(1).strip()
        if any(x in name.lower() for x in ["stunts", "cost", "special", "section", "chapter"]):
            continue
        cost_text = m.group(2)
        cost_val = int(cost_text.split("-")[0]) if "-" in cost_text else int(cost_text)
        effect = (m.group(3) or "").strip()
        sid = f"stunt.{slugify(name)}"
        stunts.append(
            {
                "id": sid,
                "type": "stunt",
                "name": name,
                "category": "unknown",
                "cost": cost_val,
                "trigger": "successful test or attack with doubles generating stunt points",
                "effect": effect,
                "restrictions": [],
                "tags": ["stunt"],
            }
        )

    # Deduplicate by normalized name, preferring entries with non-empty effects.
    by_name = {}
    for s in stunts:
        key = (s.get("name") or "").strip().lower()
        if key not in by_name:
            by_name[key] = s
            continue
        if len((s.get("effect") or "").strip()) > len((by_name[key].get("effect") or "").strip()):
            by_name[key] = s
    return list(by_name.values())


def extract_conditions(ch2_text: str) -> List[dict]:
    conditions = []
    for name in ["Fatigued", "Stunned", "Defenseless", "Prone", "Dying", "Unconscious"]:
        if re.search(rf"\b{name}\b", ch2_text):
            conditions.append(
                {
                    "id": f"condition.{slugify(name)}",
                    "type": "condition",
                    "name": name,
                    "effect": "",
                    "duration": None,
                    "removal": None,
                    "tags": ["condition", "combat"],
                }
            )
    return conditions


def extract_adversaries(ch9_text: str) -> List[dict]:
    names = set(re.findall(r"(?m)^\s*([A-Z][A-Za-z'\- ]{2,40})\s*$", ch9_text))
    ignore = {"Adversaries", "Statistics Format", "Other NPCs", "Monsters", "Beasts", "Folk"}
    entities = []
    for n in sorted(names):
        if n in ignore:
            continue
        if len(n.split()) > 4:
            continue
        entities.append(
            {
                "id": f"adversary.{slugify(n)}",
                "type": "adversary",
                "name": n,
                "category": "monster",
                "stats": {
                    "accuracy": None,
                    "communication": None,
                    "constitution": None,
                    "dexterity": None,
                    "fighting": None,
                    "intelligence": None,
                    "perception": None,
                    "strength": None,
                    "willpower": None,
                    "health": None,
                    "defense": None,
                    "speed": None,
                },
                "attacks": [],
                "special_rules": [],
                "threat_notes": "",
                "tags": ["monster"],
            }
        )
    return entities


def export_hierarchical_markdown(chunks: List[dict], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# Fantasy AGE 2E - Hierarchical Rules Corpus")
    lines.append("")

    by_chapter: Dict[Tuple[int, str], Dict[str, List[dict]]] = {}
    for c in chunks:
        ch_key = (c["chapter_no"], c["chapter_title"])
        by_chapter.setdefault(ch_key, {})
        by_chapter[ch_key].setdefault(c["section_title"], []).append(c)

    for (ch_no, ch_title) in sorted(by_chapter.keys(), key=lambda x: x[0]):
        lines.append(f"# Chapter {ch_no}: {ch_title}")
        lines.append("")
        sections = by_chapter[(ch_no, ch_title)]
        for sec_title, sec_chunks in sections.items():
            lines.append(f"## {sec_title}")
            lines.append("")
            for chunk in sec_chunks:
                lines.append(f"<!-- {chunk['id']} | {chunk['rule_type']} | {chunk['audience']} -->")
                lines.append(chunk["text"])
                lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def build(outroot: Path, cleaned_path: Path, structured_path: Path) -> None:
    clean_text = cleaned_path.read_text(encoding="utf-8", errors="replace")
    structured = read_json(structured_path)
    chapters = chapter_spans(clean_text, structured)

    chapter_by_no = {c["number"]: c for c in chapters}

    chunks = structural_chunks(chapters)
    write_jsonl(outroot / "chunks" / "rules_chunks_structured.jsonl", chunks)
    export_hierarchical_markdown(chunks, outroot / "processed" / "rules_hierarchical.md")

    ancestries = extract_ancestries(chapter_by_no.get(1, {}).get("text", ""))
    classes = extract_classes(chapter_by_no.get(1, {}).get("text", ""))
    talents = extract_talents(chapter_by_no.get(3, {}).get("text", ""))
    arcana, spells = extract_arcana_and_spells(chapter_by_no.get(5, {}).get("text", ""))
    stunts = extract_stunts(chapter_by_no.get(6, {}).get("text", ""))
    conditions = extract_conditions(chapter_by_no.get(2, {}).get("text", ""))
    adversaries = extract_adversaries(chapter_by_no.get(9, {}).get("text", ""))

    write_json(outroot / "entities" / "ancestries.json", ancestries)
    write_json(outroot / "entities" / "classes.json", classes)
    write_json(outroot / "entities" / "talents.json", talents)
    write_json(outroot / "entities" / "arcana.json", arcana)
    write_json(outroot / "entities" / "spells.json", spells)
    write_json(outroot / "entities" / "stunts.json", stunts)
    write_json(outroot / "entities" / "conditions.json", conditions)
    write_json(outroot / "entities" / "adversaries.json", adversaries)

    manifest = {
        "source_cleaned": str(cleaned_path),
        "source_structured": str(structured_path),
        "chunks": {
            "path": str(outroot / "chunks" / "rules_chunks_structured.jsonl"),
            "count": len(chunks),
        },
        "entities": {
            "ancestries": len(ancestries),
            "classes": len(classes),
            "talents": len(talents),
            "arcana": len(arcana),
            "spells": len(spells),
            "stunts": len(stunts),
            "conditions": len(conditions),
            "adversaries": len(adversaries),
        },
        "notes": [
            "Extraction is deterministic and regex-based.",
            "OCR noise still requires manual QA for legal gameplay automation.",
        ],
    }
    write_json(outroot / "processed" / "knowledge_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build rules knowledge base artifacts from cleaned corpus.")
    parser.add_argument("--cleaned", required=True, help="Path to cleaned markdown")
    parser.add_argument("--structured", required=True, help="Path to structured chapter metadata JSON")
    parser.add_argument("--outroot", required=True, help="Output root directory")
    args = parser.parse_args()

    build(Path(args.outroot), Path(args.cleaned), Path(args.structured))
