---
name: taiwan-population-xls-profiler
description: Profile Taiwan population XLS structure and anomalies. For analysis questions, continue through the population pipeline after profiling; stop here only for explicit inspection-only requests.
metadata:
  hermes:
    tags: [xls, population, data-quality]
    category: data
    requires_toolsets: [terminal]
---

# Taiwan Population XLS Profiler

## When to Use
Use before transforming a Taiwan population workbook with monthly sheets, merged headers, age-band subtotals, or inconsistent layouts.

## Procedure
1. Locate the source `.xls`; do not modify it.
2. Run `python scripts/profile_xls.py SOURCE.xls --output profile.json` from this skill directory.
3. Check the verification criteria below. Report dimensions, detected month/header, age coverage, subtotal columns, regions, missing totals, and warnings as a progress update when analysis is requested.
4. For an analysis request, immediately load and follow [taiwan-population-pipeline](../taiwan-population-pipeline/SKILL.md), carrying the original question, absolute source path, and just-produced profile path. The pipeline verifies this completed stage and resumes at normalizer → validator → analyst; do not merely recommend another skill or ask whether to continue.
5. Stop with a profiling report only when the user explicitly requests inspection only. If profiling fails, report the blocker and stop downstream work. Never answer population questions by reading Excel directly or using substitute analysis tools; final figures must come from the pipeline's verified analyst results.

## Pitfalls
- Do not treat merged blanks as missing observations.
- Do not forward-fill regions: a region's `計` row can precede its named row.
- Do not assume every month has the same column count.

## Verification
The command must produce valid JSON, detect ages 0-99, identify `100+`, and find regions in every processed month. See [format-notes.md](references/format-notes.md) when explaining anomalies.
