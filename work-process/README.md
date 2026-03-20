# Work Process

This folder contains deterministic tooling to convert OCR-heavy source text into a cleaned, codified corpus for a DM assistant.

## Canonical Workflow (Default)

Use the PDF-first runner below as the canonical path for this repository.

```bash
python work-process/scripts/run_canonical_pipeline.py
```

This will regenerate:
- `work-process/raw/fantasy_age_2e_pdf_text.md`
- `work-process/processed/rules_cleaned.md`
- `work-process/processed/rules_structured.json`
- `work-process/chunks/rules_chunks_structured.jsonl`
- `work-process/entities/*.json`
- `work-process/processed/qa_report.json`
- `work-process/processed/strict_validation_report.json`
- `work-process/processed/manual_correction_queue.jsonl`

## Step 1: OCR Repair + Rule Codification

Input:
- `source_material/2nD eDITIOn.md`

Script:
- `work-process/scripts/prepare_rules_corpus.py`

Outputs (generated under `work-process/processed/`):
- `rules_cleaned.md`: normalized text with reduced OCR artifacts.
- `rules_structured.json`: chapter index and high-value structured rules.
- `rules_chunks.jsonl`: chunked corpus for LLM retrieval pipelines.

Run:

```bash
python work-process/scripts/prepare_rules_corpus.py \
  --input source_material/2nD\ eDITIOn.md \
  --outdir work-process/processed
```

## PDF Ingestion (Preferred When Available)

Script:
- `work-process/scripts/extract_pdf_text.py`

Run:

```bash
python work-process/scripts/extract_pdf_text.py \
  --pdf "source_material/<rulebook>.pdf" \
  --text-out work-process/raw/fantasy_age_2e_pdf_text.md \
  --report-out work-process/processed/pdf_extraction_report.json
```

Then feed extracted text into the same processing pipeline:

```bash
python work-process/scripts/prepare_rules_corpus.py \
  --input work-process/raw/fantasy_age_2e_pdf_text.md \
  --outdir work-process/processed

python work-process/scripts/build_rules_knowledge_base.py \
  --cleaned work-process/processed/rules_cleaned.md \
  --structured work-process/processed/rules_structured.json \
  --outroot work-process
```

Notes:
- PDF text extraction is usually higher fidelity than OCR markdown.
- If extraction quality is mixed/poor, add OCR tools and a page-level OCR fallback.

### Override PDF path

```bash
python work-process/scripts/run_canonical_pipeline.py \
  --pdf "source_material/<your-file>.pdf"
```

## Why this supports deterministic + LLM design

- Deterministic layer: parsing/cleaning/chunking is rule-based and repeatable.
- LLM layer: model consumes stable chunks + structured metadata, not raw OCR noise.
- Auditable: reruns produce predictable artifacts that can be versioned.

## Step 2-4: Structural Chunks + Entity Extraction

Script:
- `work-process/scripts/build_rules_knowledge_base.py`

Inputs:
- `work-process/processed/rules_cleaned.md`
- `work-process/processed/rules_structured.json`

Outputs:
- `work-process/chunks/rules_chunks_structured.jsonl`
- `work-process/processed/rules_hierarchical.md`
- `work-process/processed/knowledge_manifest.json`
- `work-process/entities/ancestries.json`
- `work-process/entities/classes.json`
- `work-process/entities/talents.json`
- `work-process/entities/arcana.json`
- `work-process/entities/spells.json`
- `work-process/entities/stunts.json`
- `work-process/entities/conditions.json`
- `work-process/entities/adversaries.json`

Run:

```bash
python work-process/scripts/build_rules_knowledge_base.py \
  --cleaned work-process/processed/rules_cleaned.md \
  --structured work-process/processed/rules_structured.json \
  --outroot work-process
```

### Notes on extraction quality

- This extractor is deterministic and regex-based.
- OCR noise still impacts field completeness for some entities.
- `ancestries` and `classes` are forced to full known coverage; some entries may include fallback snippets when section boundaries are damaged.
- `stunts`, `spells`, and `adversaries` are useful for bootstrapping but should be QA reviewed before strict rule enforcement.

## Schemas

- `work-process/schemas/rule_chunk.schema.json`
- `work-process/schemas/entity.schema.json`

These are starter schemas to normalize chunk/entity payloads for indexing and validation.

## QA Extraction Diagnostics

Script:
- `work-process/scripts/qa_extraction_report.py`

Run:

```bash
python work-process/scripts/qa_extraction_report.py \
  --outroot work-process
```

Outputs:
- `work-process/processed/qa_report.json`
- `work-process/processed/qa_report.md`

Purpose:
- Flags missing required fields and likely extraction weaknesses.
- Surfaces fallback snippets (`OCR block unresolved`) for manual review.
- Helps build a deterministic review queue before strict automation.

## Hybrid Retrieval (Keyword + Semantic)

Script:
- `work-process/scripts/hybrid_rules_search.py`

Single query:

```bash
python work-process/scripts/hybrid_rules_search.py \
  --chunks work-process/chunks/rules_chunks_structured.jsonl \
  --query "How do ability tests work?" \
  --top-k 5
```

Evaluate test set:

```bash
python work-process/scripts/hybrid_rules_search.py \
  --chunks work-process/chunks/rules_chunks_structured.jsonl \
  --tests work-process/tests/rules_queries.json \
  --top-k 5 \
  --save-eval work-process/processed/retrieval_eval.json
```

Notes:
- Hybrid score is `alpha * keyword + (1 - alpha) * semantic`.
- `--alpha` defaults to `0.6` and can be tuned.
- The test-set report provides a quick retrieval quality signal for your rules copilot.

## Strict Validation Gate + Manual Correction Queue

Script:
- `work-process/scripts/strict_validate_rules.py`

Run:

```bash
python work-process/scripts/strict_validate_rules.py \
  --outroot work-process
```

Outputs:
- `work-process/processed/strict_validation_report.json`
- `work-process/processed/strict_validation_report.md`
- `work-process/processed/manual_correction_queue.jsonl`

Purpose:
- Applies strict data-quality rules to extracted entities.
- Computes a gate result (`gate_pass`) and quality score.
- Produces a prioritized correction queue sorted by severity.

Recommended usage pattern:
1. Run extraction pipeline.
2. Run strict validator.
3. Fix queue items from top to bottom.
4. Re-run validator until `gate_pass` is true.
