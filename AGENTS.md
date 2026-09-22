# Population analysis workflow

For questions requiring population figures from a workbook or its derived dataset, load and follow [.hermes/skills/taiwan-population-pipeline/SKILL.md](.hermes/skills/taiwan-population-pipeline/SKILL.md). Execute profiler → normalizer → validator → analyst and verify each stage's artifacts before continuing. Reading skill instructions or producing a profile alone does not complete an analysis request.

Base final population figures exclusively on `status: ok` results from the analyst's `population_query.py`, after validation passes for that dataset. Do not bypass the pipeline with direct Excel reads, ad hoc Python calculations, model-written SQL, or alternate query tools. The prescribed profiler and normalizer scripts may read the source workbook as part of the pipeline.

If a stage fails or a required source/condition is unavailable, report the blocker or request the missing information; do not substitute an alternate analysis path. Stop after profiling only when the user explicitly requests inspection only. Explicit requests limited to another individual stage remain limited to that stage and do not authorize an analytical answer.

These rules apply to population analysis, not to editing or testing this project's code and skills.
