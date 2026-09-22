# Schema
`population` stores one row per month, region, sex, and age label. `age_label` is `all`, `0`-`99`, or `100+`; `age` is null for `all` and `100+`. `region_level` is `national`, `province`, or `local`. The primary key is `(year_month, region_name, sex, age_label)`.

`source_region_total` stores the supplied combined-sex overall total when present. Missing source total rows are reported, not invented.

`dataset_manifest.json` accompanies each normalized database. `available_months` is the sorted, deduplicated `YYYY-MM` projection of actual population rows, not sheet count or a hardcoded year. `dimensions` and `measures` describe the populated normalized schema; `unsupported` records the semantic limits of this population-stock dataset. These limits cannot be inferred from numeric values alone. The annual validator still requires 12 months; incomplete inputs remain incomplete in the manifest and fail validation.
