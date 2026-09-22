---
name: taiwan-population-pipeline
description: Primary entrypoint for Taiwan population questions from XLS workbooks or derived datasets. Execute and verify profiler, normalizer, validator, and analyst in order; also resume an analysis request after profiling.
metadata:
  hermes:
    tags: [xls, population, pipeline, analytics]
    category: data
    requires_toolsets: [terminal]
---

# Taiwan Population Pipeline

## Execution contract

Use this workflow for population analysis requests. Execute each stage's script after loading its linked skill; merely reading instructions, recommending the next skill, or displaying profile output is not completion. Continue automatically between successful stages without asking permission to proceed.

Use the prescribed scripts to process the workbook and query the dataset. Final population figures must come exclusively from the analyst's `population_query.py` with `status: ok`. Do not substitute direct Excel inspection, ad hoc Python calculations, model-written SQL, or alternate query tools for this workflow. Reading JSON artifacts to check stage completion is allowed.

If the user explicitly requests inspection only, follow the profiler and stop with its structural report. Other explicitly limited stage requests stay within their requested scope and do not produce an analytical answer.

## Procedure and gates

1. **Bind inputs.** Preserve the original question and requested conditions. Resolve the source XLS and an output directory to absolute paths; keep the source unchanged. Use a Python environment with the pack's dependencies. Resolve script paths relative to each linked skill's directory, not the current working directory. If the source is unavailable, request its location rather than bypassing preparation using an existing database.

2. **Profile.** Load [profiler](../taiwan-population-xls-profiler/SKILL.md) and run `profile_xls.py SOURCE.xls --output OUTPUT_DIR/profile.json` (create the output directory first). Require exit code zero, valid JSON, empty `errors`, nonempty `sheets` accounting for `sheet_count`, and matching `source`. Each sheet must have a detected month/header, ages 0–99 (`age_min: 0`, `age_max: 99`, `age_column_count: 100`), exactly one candidate `100+` column, and regions. Carry warnings forward. When entering from profiler, reuse that just-completed invocation only after checking these gates for the same source; continue at normalization without invoking profiler recursively. An old `profile.json` merely existing is not evidence of completion.

3. **Normalize.** Load [normalizer](../taiwan-population-normalizer/SKILL.md) and run `normalize_population.py SOURCE.xls --output-dir OUTPUT_DIR`. Require exit code zero and generated `population_long.csv`, `population.sqlite`, and valid `dataset_manifest.json` in that directory. Check manifest months against the profiled months; never invent missing months. Proceed directly to validation; file existence alone does not establish data quality.

4. **Validate.** Load [validator](../taiwan-population-validator/SKILL.md) and run `validate_population.py OUTPUT_DIR/population.sqlite --output OUTPUT_DIR/validation.json`. Require exit code zero, `status` equal to `passed` or `passed_with_warnings`, empty `errors`, and the required `checks` and `warnings` fields. The report must come from this invocation against this database; an unrelated or stale passing report does not qualify. Retain warnings for the answer.

5. **Analyze.** Load [analyst](../taiwan-population-analyst/SKILL.md) and its query policy and intent schema. Check answerability against the generated manifest, preserve the user's conditions, and write the constrained intent to `OUTPUT_DIR/intent.json`. Ask for missing required conditions instead of guessing. Run `population_query.py OUTPUT_DIR/population.sqlite --intent OUTPUT_DIR/intent.json` and save its JSON stdout as `OUTPUT_DIR/query_result.json`. Require exit code zero, `status: ok`, nonempty `results`, and an echoed intent matching the submitted conditions before presenting figures. For other statuses, explain the returned code/coverage or request clarification; never retry with altered conditions without user direction.

## Completion and failure

Answer the original question using only verified query results, including month, geographic level, sex, age scope, units, and ties. Briefly state validation status and relevant warnings, and identify the output artifacts. Profile and normalization summaries are progress updates, not the final analysis answer.

On a failed gate, stop downstream execution and report the stage, error, and missing or invalid artifact. Missing dependencies, unavailable skills, unsupported questions, and validation failures never authorize a fallback data-reading or query path. Resume only after the blocker is resolved; rerun downstream stages if upstream artifacts change.
