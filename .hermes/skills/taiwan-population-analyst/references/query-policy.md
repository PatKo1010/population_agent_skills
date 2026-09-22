# Query policy
The model emits constrained JSON intent only. The query program validates it and runs developer-owned, parameterized SQL. Custom SQL and alternative query entrypoints are prohibited; if no supported operation fits, report the limitation.

## Answerability gate
Read the manifest before querying, before generating an intent. Convert ROC years to Gregorian (114 → 2025), then require every requested month to be present. Report the actual available months for out-of-range requests; do not silently substitute a year or omit missing periods. If the manifest is missing or validation fails, normalize/validate before analysis.

| Question class | Action |
| --- | --- |
| Direct population lookup by available month, region, sex, age | Use `population_lookup`; for a year-only population question, clarify the snapshot month. |
| Ranking, age share, or trend across available snapshots | Use the corresponding fixed operation with explicit filters. |
| Why population fell | Explain that cause data is absent. You may provide the observed change, explicitly separating it from explanations. |
| Births during a year | Explain that birth-event data is absent. Never substitute age-0 residents for births. |
| Migration counts | Explain that migration-event data is absent. Population differences are not migration counts. |
| Income, occupation, or other absent measures | State that the dataset cannot answer the question. |
| Requested period outside `available_months` | Report the actual coverage and that the requested period is unavailable. |

Treat supported dimensions/measures as an allowlist: an unlisted topic is not supported merely because it is absent from `unsupported`. For mixed questions, answer only the supported component and clearly identify the unavailable component.

## Fixed formulas
- Combined-sex population = male + female for identical month, region, and age scope.
- Elderly share = population aged 65–99 plus `100+`, divided by the same month/region/sex overall (`all`) population × 100. Use `population_share` with `age_min: 65`, `include_100_plus: true`, and `region_level: local`. If month is unspecified, ask for it.
- `population_trend` reports snapshots for an explicit chronological list of months. Report those observations; this interface does not compute differences or causal explanations. If a difference operation is needed, report the limitation rather than writing SQL or calculating mentally.
- A zero or missing denominator gives an unavailable share, not 0%.

For a database covering 2025 only, 「113 年人口多少？」 must report that 113/2024 is outside coverage; 「114 年出生多少人？」 remains unsupported even when every 2025 month exists.
