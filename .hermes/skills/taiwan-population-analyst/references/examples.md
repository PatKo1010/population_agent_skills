# Examples

Write the JSON intent to `intent.json`, then run:

```bash
python scripts/population_query.py population.sqlite --intent intent.json
```

65+ population share for local jurisdictions in December 2025:

```json
{"operation":"population_share","month":"2025-12","region_level":"local","sex":"total","age_min":65,"include_100_plus":true}
```

Overall population in Taipei, including all ages:

```json
{"operation":"population_lookup","month":"2025-12","region":"臺北市","region_level":"local","sex":"total"}
```

Largest local populations in an explicitly requested month:

```json
{"operation":"population_rank","month":"2025-12","region_level":"local","sex":"total","limit":5}
```

Two explicitly requested snapshots:

```json
{"operation":"population_trend","months":["2025-01","2025-12"],"region":"臺北市","region_level":"local","sex":"total"}
```

For a dataset containing all months of 2025, a December 2024 lookup is rejected with `status: out_of_scope`, `code: MONTH_NOT_AVAILABLE`, `requested: 2024-12`, `available_range: [2025-01, 2025-12]`, the full `available_months` list, and `results: null`. Keep the requested year unchanged.

A ranking without `month` yields `needs_clarification` / `MISSING_REQUIRED_FIELDS`. An exact `age: 105` yields `out_of_scope` / `AGE_PRECISION_NOT_SUPPORTED`; explain that only the combined `100+` group exists and ask before changing the request. A missing region yields `REGION_NOT_AVAILABLE`, not a population of zero.
