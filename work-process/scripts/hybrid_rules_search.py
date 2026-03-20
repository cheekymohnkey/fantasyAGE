#!/usr/bin/env python3
"""Hybrid search over structured rules chunks (keyword + vector-like score).

This is dependency-free and deterministic:
- Keyword channel: BM25-style scoring over tokenized text.
- Similarity channel: cosine similarity over hashed term-frequency vectors.

Usage:
  python work-process/scripts/hybrid_rules_search.py \
    --chunks work-process/chunks/rules_chunks_structured.jsonl \
    --query "How do ability tests work?" --top-k 5

  python work-process/scripts/hybrid_rules_search.py \
    --chunks work-process/chunks/rules_chunks_structured.jsonl \
    --tests work-process/tests/rules_queries.json --top-k 5
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) >= 2]


def norm(vec: Dict[str, float]) -> float:
    return math.sqrt(sum(v * v for v in vec.values()))


def dot(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    na = norm(a)
    nb = norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return dot(a, b) / (na * nb)


def bm25_scores(query_tokens: List[str], docs_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75) -> List[float]:
    N = len(docs_tokens)
    if N == 0:
        return []

    doc_lens = [len(d) for d in docs_tokens]
    avg_dl = sum(doc_lens) / N if N else 0.0

    df = Counter()
    tfs = []
    for tokens in docs_tokens:
        tf = Counter(tokens)
        tfs.append(tf)
        for t in tf.keys():
            df[t] += 1

    scores = []
    for i, tf in enumerate(tfs):
        dl = doc_lens[i]
        score = 0.0
        for q in query_tokens:
            if q not in tf:
                continue
            n_q = df.get(q, 0)
            idf = math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))
            f = tf[q]
            denom = f + k1 * (1 - b + b * (dl / avg_dl if avg_dl else 0))
            score += idf * ((f * (k1 + 1)) / denom)
        scores.append(score)
    return scores


def tfidf_vectors(docs_tokens: List[List[str]]) -> Tuple[List[Dict[str, float]], Dict[str, float]]:
    N = len(docs_tokens)
    df = Counter()
    for tokens in docs_tokens:
        for t in set(tokens):
            df[t] += 1

    idf = {t: math.log((1 + N) / (1 + n)) + 1.0 for t, n in df.items()}
    vectors = []
    for tokens in docs_tokens:
        tf = Counter(tokens)
        vec = {t: f * idf.get(t, 0.0) for t, f in tf.items()}
        vectors.append(vec)
    return vectors, idf


def vectorize_query(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = Counter(tokens)
    return {t: f * idf.get(t, 0.0) for t, f in tf.items()}


def max_norm(values: List[float]) -> List[float]:
    if not values:
        return values
    m = max(values)
    if m <= 0:
        return [0.0 for _ in values]
    return [v / m for v in values]


def score_chunks(chunks: List[dict], query: str, alpha: float = 0.6) -> List[dict]:
    docs_text = [
        " ".join(
            [
                c.get("chapter_title", ""),
                c.get("section_title", ""),
                " ".join(c.get("tags") or []),
                c.get("text", ""),
            ]
        )
        for c in chunks
    ]
    docs_tokens = [tokenize(t) for t in docs_text]
    q_tokens = tokenize(query)

    bm25 = bm25_scores(q_tokens, docs_tokens)
    bm25n = max_norm(bm25)

    doc_vecs, idf = tfidf_vectors(docs_tokens)
    q_vec = vectorize_query(q_tokens, idf)
    cos_scores = [cosine(q_vec, dv) for dv in doc_vecs]
    cosn = max_norm(cos_scores)

    out = []
    for i, c in enumerate(chunks):
        hybrid = alpha * bm25n[i] + (1.0 - alpha) * cosn[i]
        out.append(
            {
                "id": c.get("id"),
                "score": hybrid,
                "keyword_score": bm25n[i],
                "semantic_score": cosn[i],
                "chapter_no": c.get("chapter_no"),
                "chapter_title": c.get("chapter_title"),
                "section_title": c.get("section_title"),
                "rule_type": c.get("rule_type"),
                "tags": c.get("tags") or [],
                "text": c.get("text") or "",
            }
        )

    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def evaluate_queries(chunks: List[dict], tests: List[dict], top_k: int, alpha: float) -> dict:
    rows = []
    pass_count = 0

    for t in tests:
        results = score_chunks(chunks, t["query"], alpha=alpha)[:top_k]
        tag_expect = [x.lower() for x in (t.get("expected_tags_any") or [])]
        term_expect = [x.lower() for x in (t.get("expected_terms_any") or [])]

        result_text = "\n".join(r["text"] for r in results).lower()
        result_tags = set(tag.lower() for r in results for tag in r.get("tags", []))

        tag_hit = any(tag in result_tags for tag in tag_expect) if tag_expect else True
        term_hit = any(term in result_text for term in term_expect) if term_expect else True
        ok = tag_hit and term_hit
        pass_count += 1 if ok else 0

        rows.append(
            {
                "id": t.get("id"),
                "query": t.get("query"),
                "pass": ok,
                "tag_hit": tag_hit,
                "term_hit": term_hit,
                "top_result_ids": [r["id"] for r in results],
            }
        )

    return {
        "total": len(tests),
        "passed": pass_count,
        "pass_rate": (pass_count / len(tests)) if tests else 0.0,
        "results": rows,
    }


def preview_text(s: str, limit: int = 220) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] + ("..." if len(s) > limit else "")


def run_query(chunks: List[dict], query: str, top_k: int, alpha: float) -> None:
    results = score_chunks(chunks, query, alpha=alpha)[:top_k]
    print(f"Query: {query}")
    print(f"Top {top_k} results:")
    for i, r in enumerate(results, start=1):
        print(
            f"{i}. {r['id']} | score={r['score']:.4f} (kw={r['keyword_score']:.4f}, sem={r['semantic_score']:.4f}) | "
            f"{r['chapter_title']} -> {r['section_title']}"
        )
        print(f"   tags={','.join(r['tags'])}")
        print(f"   {preview_text(r['text'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid search for structured Fantasy AGE chunks")
    parser.add_argument("--chunks", required=True, help="Path to rules_chunks_structured.jsonl")
    parser.add_argument("--query", help="Single query string")
    parser.add_argument("--tests", help="Path to test query JSON file")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--alpha", type=float, default=0.6, help="Hybrid weight: keyword alpha, semantic 1-alpha")
    parser.add_argument("--save-eval", help="Optional path to write evaluation JSON")
    args = parser.parse_args()

    chunks = read_jsonl(Path(args.chunks))

    if args.query:
        run_query(chunks, args.query, args.top_k, args.alpha)

    if args.tests:
        tests = read_json(Path(args.tests))
        report = evaluate_queries(chunks, tests, args.top_k, args.alpha)
        print(json.dumps(report, indent=2))
        if args.save_eval:
            Path(args.save_eval).write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if not args.query and not args.tests:
        parser.error("Provide --query and/or --tests")


if __name__ == "__main__":
    main()
