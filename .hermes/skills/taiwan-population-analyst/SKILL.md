---
name: taiwan-population-analyst
description: Check population question answerability against the dataset manifest, then answer supported questions with deterministic SQL.
metadata:
  hermes:
    tags: [sqlite, analytics, population]
    category: data
    requires_toolsets: [terminal]
---

# Taiwan Population Analyst

## When to Use
Use for factual questions about a normalized population database after validation passes.

## Procedure
1. Read `dataset_manifest.json` beside the database and require passing dataset validation. Classify answerability with [query-policy.md](references/query-policy.md).
2. Produce only a constrained JSON intent following [intent-schema.md](references/intent-schema.md). Preserve the user's requested conditions. Ask for missing required conditions; never silently choose a month, replace a year, change a region, or broaden age precision.
3. Run `python scripts/population_query.py DATABASE --intent intent.json` (or `--intent -` with JSON on stdin). This is the only population query entrypoint; the program owns SQL.
4. For `status: ok`, base every number on `results`, state month, geographic level, sex, age scope, unit, and ties. For any other status, explain the returned code and available coverage or request clarification. `results: null` means unavailable, never zero. Schema syntax repairs may be retried when they preserve all user conditions; do not retry with different conditions unless the user supplies or approves them.

## Query Rules
- Use only the operation allowlist and fields in the intent schema. No model-written SQL, SQL fallback, or alternate database query tools.
- Unsupported questions remain unsupported even if they mention valid population dimensions. Explain the limitation using the query policy.
- `sex: total` combines male and female. Each query selects exactly one geographic level.
- For shares, distinguish numerator `sex` from `denominator_sex`; specify `region` for a single-region answer. For smallest/largest populations, use rank `order: asc`/`desc`, `limit: 1`, and `include_ties: true` when all ties are requested.
- Read [examples.md](references/examples.md) for valid and rejected intents.

## Verification
Require `status: ok`, non-empty results, and an echoed intent matching the submitted conditions. Check share numerators do not exceed denominators and trends follow requested chronological months.
