#!/usr/bin/env python3
r"""Deterministically clean OCR text and extract structured RPG rules artifacts.

Usage:
  python work-process/scripts/prepare_rules_corpus.py \
    --input source_material/2nD\ eDITIOn.md \
    --outdir work-process/processed
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

CHAPTER_HEADING_RE = re.compile(r"^(?P<num>\d{1,2}):\s+(?P<title>[^\n]+?)\s*$", re.MULTILINE)

def spaced_word_pattern(word: str) -> str:
    chars = []
    for ch in word:
        if ch.isalpha():
            chars.append(re.escape(ch) + r"\s*")
        else:
            chars.append(re.escape(ch))
    return "".join(chars)


@dataclass
class Chapter:
    number: int
    title: str
    start: int
    end: int


def normalize_line(line: str) -> str:
    line = line.replace("\u2019", "'")
    line = line.replace("\u2018", "'")
    line = line.replace("\u201c", '"')
    line = line.replace("\u201d", '"')
    line = line.replace("\u2014", "-")
    line = line.replace("\u2013", "-")
    line = line.replace("\u00a0", " ")
    line = line.replace("\t", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_probable_header_footer(line: str) -> bool:
    if not line:
        return False
    if re.fullmatch(r"\d+", line):
        return True
    if re.search(r"\bChapter\s+\d+\b", line) and re.search(r"\bBasic Rules|Character Creation|Stunts|magic\b", line, re.IGNORECASE):
        return True
    if "table of contents" in line.lower() and len(line) < 40:
        return True
    if line.lower() in {"player's section", "section"}:
        return True
    return False


def should_join(prev: str, nxt: str) -> bool:
    if not prev or not nxt:
        return False
    if prev.startswith("#") or nxt.startswith("#"):
        return False
    if re.match(r"^\d{1,2}:\s", prev):
        return False
    if re.match(r"^Step\s+\d+", prev, flags=re.IGNORECASE):
        return False
    if prev.endswith((".", ":", "!", "?", ")", "]")):
        return False
    if prev.startswith("- ") or prev.startswith("* "):
        return False
    if nxt.startswith(("- ", "* ")):
        return False
    if re.match(r"^\d{1,2}:\s", nxt):
        return False
    if nxt[0].isupper() and prev[-1].islower():
        return False
    return True


def clean_ocr_text(raw: str) -> str:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"`{3,}", "", raw)

    lines = [normalize_line(line) for line in raw.split("\n")]
    lines = [line for line in lines if line]

    filtered: List[str] = []
    for line in lines:
        if is_probable_header_footer(line):
            continue
        filtered.append(line)

    joined: List[str] = []
    i = 0
    while i < len(filtered):
        cur = filtered[i]
        if i + 1 < len(filtered):
            nxt = filtered[i + 1]
            if cur.endswith("-") and nxt and nxt[0].islower():
                cur = cur[:-1] + nxt
                i += 1
            elif should_join(cur, nxt):
                cur = f"{cur} {nxt}"
                i += 1
        joined.append(cur)
        i += 1

    text = "\n".join(joined)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text.strip() + "\n"


def find_chapters(clean_text: str) -> List[Chapter]:
    expected_titles = {
        1: "Character Creation",
        2: "Basic Rules",
        3: "Character Options",
        4: "Equipment",
        5: "magic",
        6: "Stunts",
        7: "The Game Master",
        8: "mastering the rules",
        9: "Adversaries",
        10: "Rewards",
        11: "Breakwater Bay",
    }

    # Match only heading-like lines, not in-text references or TOC lines with dotted leaders.
    matches_per_num: dict[int, list[tuple[str, int]]] = {n: [] for n in expected_titles}
    for num, token in expected_titles.items():
        spaced = spaced_word_pattern(token)
        pat = re.compile(rf"(?im)^\s*{num}:\s*({spaced})\s*$")
        for m in pat.finditer(clean_text):
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            matches_per_num[num].append((title, m.start()))

    # Prefer the later occurrence for chapter 1 to skip the TOC, then keep first valid heading after prior chapter.
    ordered_nums = sorted(expected_titles.keys())
    ordered: list[tuple[int, str, int]] = []
    start_floor = 0
    if matches_per_num[1]:
        ch1_title, ch1_start = matches_per_num[1][-1]
        ordered.append((1, ch1_title, ch1_start))
        start_floor = ch1_start

    for num in ordered_nums[1:]:
        options = [(t, s) for t, s in matches_per_num[num] if s > start_floor]
        if not options:
            continue
        t, s = options[0]
        ordered.append((num, t, s))
        start_floor = s

    chapters: List[Chapter] = []
    for idx, (num, title, start) in enumerate(ordered):
        end = ordered[idx + 1][2] if idx + 1 < len(ordered) else len(clean_text)
        chapters.append(Chapter(number=num, title=title, start=start, end=end))
    return chapters


def first_match_group(patterns: Iterable[str], text: str, group: int = 1) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(group).strip()
    return None


def split_csv_words(value: str) -> List[str]:
    value = value.replace(" and ", ", ")
    parts = [p.strip(" .") for p in value.split(",")]
    cleaned = [re.sub(r"^(?:or|and)\s+", "", p, flags=re.IGNORECASE) for p in parts]
    return [p for p in cleaned if p]


def snippet_around(text: str, needle: str, radius: int = 220) -> str:
    m = re.search(re.escape(needle), text, flags=re.IGNORECASE)
    if not m:
        return ""
    start = max(0, m.start() - radius)
    end = min(len(text), m.end() + radius)
    return text[start:end].strip()


def build_chunks(clean_text: str, chapters: List[Chapter], chunk_size: int = 1400, overlap: int = 200) -> List[dict]:
    chunks: List[dict] = []

    for chapter in chapters:
        chapter_text = clean_text[chapter.start:chapter.end].strip()
        pos = 0
        idx = 0
        while pos < len(chapter_text):
            end = min(pos + chunk_size, len(chapter_text))
            snippet = chapter_text[pos:end].strip()
            chunks.append(
                {
                    "id": f"ch{chapter.number:02d}_{idx:03d}",
                    "chapter_number": chapter.number,
                    "chapter_title": chapter.title,
                    "start_offset": chapter.start + pos,
                    "end_offset": chapter.start + end,
                    "text": snippet,
                }
            )
            if end >= len(chapter_text):
                break
            pos = max(0, end - overlap)
            idx += 1

    return chunks


def extract_structured(clean_text: str, chapters: List[Chapter], source_file: str) -> dict:
    canonical_chapter_titles = {
        1: "Character Creation",
        2: "Basic Rules",
        3: "Character Options",
        4: "Equipment",
        5: "Magic",
        6: "Stunts",
        7: "The Game Master",
        8: "Mastering the Rules",
        9: "Adversaries",
        10: "Rewards",
        11: "Breakwater Bay",
    }
    ancestry_phrase = first_match_group(
        [r"Your character can be (?:a|an) (.+?)\."],
        clean_text,
    )
    class_phrase = first_match_group(
        [r"You can choose ([A-Za-z,\s]+?)\."],
        clean_text,
    )
    encounter_phrase = first_match_group([
        r"There are three basic types of encounters in Fantasy AGE:(.+?)Action encounters",
    ], clean_text)
    formula = first_match_group([r"Test result\s*=\s*3d6\s*\+\s*Ability"], clean_text, group=0)

    known_ancestries = ["draak", "dwarf", "elf", "gnome", "goblin", "halfling", "human", "orc", "wildfolk"]
    known_classes = ["Envoy", "Mage", "Rogue", "Warrior"]
    ancestries = [a for a in known_ancestries if re.search(rf"\b{a}\b", clean_text, flags=re.IGNORECASE)]
    classes = [c for c in known_classes if re.search(rf"\b{c}\b", clean_text, flags=re.IGNORECASE)]

    systems = []
    for term in ["Peril", "Daring", "Fortune", "Stunts", "Arcana", "Health", "Magic Points", "Ability Tests"]:
        if re.search(rf"\b{re.escape(term)}\b", clean_text, flags=re.IGNORECASE):
            systems.append(term)

    return {
        "document": {
            "title": "Fantasy AGE 2nd Edition (OCR cleaned)",
            "source_file": source_file,
        },
        "chapters": [
            {
                "number": c.number,
                "title": canonical_chapter_titles.get(c.number, c.title),
                "start_offset": c.start,
                "end_offset": c.end,
            }
            for c in chapters
        ],
        "core_mechanics": {
            "ability_test_formula": formula,
            "target_number_note": first_match_group([r"Target Number of\s+\d+"], clean_text, group=0),
            "health_note": first_match_group([r"Health is a measure of your character's fitness and wellbeing\.?"], clean_text, group=0),
            "stunt_note": first_match_group(
                [
                    r"doubles are rolled on a successful attack roll or ability test, this generates [\"']?stunt points[\"']?",
                    r"Roll doubles on 3d6 to pull off unexpected moves",
                ],
                clean_text,
                group=0,
            ),
        },
        "character_options": {
            "ancestries": split_csv_words(ancestry_phrase) if ancestry_phrase else ancestries,
            "classes": split_csv_words(class_phrase) if class_phrase else classes,
        },
        "encounters": {
            "summary_text": encounter_phrase or snippet_around(clean_text, "types of encounters in Fantasy AGE"),
            "keywords": ["action encounters", "exploration encounters", "social encounters"],
            "snippets": {
                "action": snippet_around(clean_text, "Action encounters"),
                "exploration": snippet_around(clean_text, "exploration encounters"),
                "social": snippet_around(clean_text, "social encounters"),
            },
        },
        "optional_systems_detected": systems,
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def run(input_path: Path, outdir: Path) -> None:
    raw = input_path.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_ocr_text(raw)
    chapters = find_chapters(cleaned)
    structured = extract_structured(cleaned, chapters, str(input_path))
    chunks = build_chunks(cleaned, chapters)

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "rules_cleaned.md").write_text(cleaned, encoding="utf-8")
    write_json(outdir / "rules_structured.json", structured)
    write_jsonl(outdir / "rules_chunks.jsonl", chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare cleaned + structured RPG rules corpus from OCR markdown.")
    parser.add_argument("--input", required=True, help="Path to OCR markdown file")
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()

    run(Path(args.input), Path(args.outdir))
