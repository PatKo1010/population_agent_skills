---
name: taiwan-population-validator
description: Validate normalized Taiwan population data and totals.
metadata:
  hermes:
    tags: [sqlite, validation, population]
    category: data
    requires_toolsets: [terminal]
---

# Taiwan Population Validator

## When to Use
Use after normalization and before population analysis, reporting, or question generation.

## Procedure
Run `python scripts/validate_population.py population.sqlite --output validation.json`. Stop analytical work if `status` is `failed`. Report failed check names and examples.

Checks cover manifest presence and agreement with the database months and supported schema, database integrity, expected months, both sexes, single-age coverage, age-to-total reconciliation, source combined-sex totals, and non-overlapping geographic aggregation.

## Pitfalls
- A missing source `計` row is a warning when male and female facts remain complete.
- Reconcile the nation using six municipalities plus `臺灣省` and `福建省`; never add province aggregates to their local constituents.

## Verification
JSON must contain `status`, `checks`, `warnings`, and `errors`. Exit code is zero only for passing results. See [validation-rules.md](references/validation-rules.md).
