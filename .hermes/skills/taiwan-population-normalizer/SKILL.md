---
name: taiwan-population-normalizer
description: Normalize Taiwan population XLS into CSV and SQLite.
metadata:
  hermes:
    tags: [xls, sqlite, etl]
    category: data
    requires_toolsets: [terminal]
---

# Taiwan Population Normalizer

## When to Use
Use to convert a profiled monthly population workbook into a stable relational dataset.

## Procedure
1. Run `python scripts/normalize_population.py SOURCE.xls --output-dir OUTPUT_DIR`.
2. Preserve the source workbook unchanged.
3. Confirm `dataset_manifest.json` is generated beside `population_long.csv` and `population.sqlite`. Its sorted `available_months` must list every month actually present (all 12 for a complete annual workbook); never fill missing months from expectations. Use the CSV for inspection and SQLite for queries.
4. Run `/taiwan-population-validator` before analysis.

## Data Rules
- Normalize spaces in region names and convert ROC dates to Gregorian.
- Store male and female source facts; calculate combined sex during queries.
- Store ages 0-99 and `100+`; exclude source age-band subtotals.
- Classify `總計` as `national`, province aggregates as `province`, and counties/cities as `local`.
- Infer an unlabeled final numeric column after age 99 as `100+` only when unique.

## Pitfalls
Never forward-fill regions or mix local and province rows in one geographic sum. Stop if ages or `100+` are ambiguous.

## Verification
Confirm CSV and SQLite outputs exist, SQLite integrity passes, and every month has both sexes. Read [schema.md](references/schema.md) before writing SQL.
