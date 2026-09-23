# Query intent contract

Input is one JSON object. Unknown fields, duplicate JSON keys, nulls in required fields, and wrong types are rejected. Only these operations are allowed:

| operation | Required fields in addition to operation, sex, region_level | Optional fields |
| --- | --- | --- |
| population_lookup | month, region | age selection |
| population_rank | month | age selection, limit, order, include_ties |
| population_share | month | age selection, limit, region, denominator_sex |
| population_trend | months, region | age selection |

- `month`: exact available Gregorian `YYYY-MM`. `months`: non-empty, unique, chronological array of such months. All must exist; unavailable interior months are rejected even within `available_range`.
- `region`: exact existing region name in every requested month. No aliases or automatic replacement.
- `region_level`: one of `local`, `province`, `national`, required and consistent with region. Arrays and multi-region sums are unsupported, preventing province/local double counting.
- `sex`: required, one of `male`, `female`, `total`.
- Age selection: omit all age fields for overall population (including `100+`); or use `age` as integer 0–99 or string `100+`; or use `age_min` (integer 0–99), `include_100_plus` (boolean), and optional `age_max` (integer, defaults to 99). Range endpoints are inclusive and ordered. Including `100+` requires `age_max` 99. Exact ages 100 and above are unavailable. Exact-age and range fields cannot coexist.
- `limit`: optional integer 1–1000, default 10; controls output length, not population filters.
- `order`: rank only, `desc` (default, largest first) or `asc` (smallest first). Use `limit: 1` for a maximum/minimum.
- `include_ties`: rank only, boolean, default `false` for compatibility. Set `true` when all ties are requested: return the first `limit` rows plus every row tied with the last included population. The result may exceed `limit`.
- `region`: optional for shares; when supplied, return that exact region only, still checking `region_level`. When omitted, compare regions within the selected level (default limit 10).
- `denominator_sex`: share only, `male`, `female`, or `total`; defaults to `sex` for compatibility. `sex` selects the numerator. The denominator always uses the same month and region, all ages, and `denominator_sex`. It must equal `sex` or be `total`, so the numerator is a population subset. Female/all-person share requires `sex: female, denominator_sex: total` with age fields omitted. Female elderly/all-female share uses `sex: female` and the elderly age range. `percentage` is in percentage points (0–100), rounded to 4 decimal places; numerator and denominator are also returned.

Do not invent fields such as `sort_by`, `sort_order`, `top_n`, `numerator`, `denominator`, or `filters`. Use the flat fields above. `UNKNOWN_FIELDS` returns `allowed_fields` for the selected operation. A correction to field names that preserves every requested condition is a syntax repair, not a change of user intent; retry after consulting this contract. Do not drop unsupported conditions to make an intent pass. See [examples.md](examples.md) for share and extremum templates.

The `age_max` default of 99 is the upper bound of individually recorded ages; `include_100_plus` must still be explicit for a range. Optional defaults are part of this contract, never substitutes for missing month, region level, or sex. If user meaning is ambiguous, request clarification before generating intent.

The only entrypoint is `population_query.py DATABASE --intent PATH`, or `--intent -` for stdin. Outputs are always JSON. Success returns `status: ok`, original `intent`, and `results`. Rejection exits 2 with `status`, `code`, `requested` where relevant, and `results: null`. `needs_clarification` identifies missing required conditions; `out_of_scope` identifies unavailable operations, months, regions or exact age precision. Invalid combinations use `invalid_intent`; database/manifest problems use `data_error`. Never modify a rejected intent to force success.
