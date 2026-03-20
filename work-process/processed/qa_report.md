# Extraction QA Report

## Summary

- Chunks analyzed: 1090
- Entity files analyzed: 8

## Chunk Issues


## Entity Issues

### adversaries
- Rows: 84
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### ancestries
- Rows: 9
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### arcana
- Rows: 19
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### classes
- Rows: 4
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### conditions
- Rows: 6
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### spells
- Rows: 152
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### stunts
- Rows: 49
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

### talents
- Rows: 56
- duplicate_ids: 0
- duplicate_names: 0
- missing_core_fields: 0

## Suggested Next QA Actions

- Review `missing_cost` stunts and fill deterministic costs from chapter stunt tables.
- Review `missing_arcana` spells and map each spell to an arcana family.
- Review `fallback_snippets` entity notes and replace with fully bounded section text.
- Split any `very_long_text` chunks by subsection boundaries.
