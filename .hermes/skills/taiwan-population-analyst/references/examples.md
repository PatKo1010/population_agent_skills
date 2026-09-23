# Examples

## Single-region shares and rankings

Female population as a percentage of the national all-person population (G012):

```json
{"operation":"population_share","month":"2025-12","region":"總計","region_level":"national","sex":"female","denominator_sex":"total"}
```

National ages 0–14 as a percentage of the all-person population (G013):

```json
{"operation":"population_share","month":"2025-12","region":"總計","region_level":"national","sex":"total","age_min":0,"age_max":14,"include_100_plus":false}
```

National ages 65+ as a percentage of the all-person population (G014):

```json
{"operation":"population_share","month":"2025-11","region":"總計","region_level":"national","sex":"total","age_min":65,"age_max":99,"include_100_plus":true}
```

Largest local population, including every tie (G015):

```json
{"operation":"population_rank","month":"2025-12","region_level":"local","sex":"total","order":"desc","limit":1,"include_ties":true}
```

Smallest local population, including every tie (G016):

```json
{"operation":"population_rank","month":"2025-12","region_level":"local","sex":"total","order":"asc","limit":1,"include_ties":true}
```

Smallest local 100+ population, including every tie (G017):

```json
{"operation":"population_rank","month":"2025-11","region_level":"local","sex":"total","age":"100+","order":"asc","limit":1,"include_ties":true}
```

Region names above must be checked against the current dataset manifest/data; never replace unavailable requested regions. Omitting age fields in the female-share example is intentional: the numerator is all ages, not a particular age group.

## Other operations and rejection behavior

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
