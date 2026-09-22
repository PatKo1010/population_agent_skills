# Hermes installation

## Install dependency
```bash
unzip taiwan-population-skill-pack.zip
cd taiwan-population-skill-pack
python3 -m pip install -r requirements.txt
```
Use the Python environment visible to Hermes terminal commands.

## Global installation
```bash
mkdir -p ~/.hermes/skills
cp -R skills/taiwan-population-* ~/.hermes/skills/
```
Restart Hermes. The five folders become slash commands with the same names.

## Project-only installation
From a Git project root:
```bash
mkdir -p .hermes/skills
cp -R /path/to/taiwan-population-skill-pack/skills/taiwan-population-* .hermes/skills/
hermes skills trust
```

## Verify and run

Use the pipeline as the primary entrypoint for analysis:
```text
/taiwan-population-pipeline 使用 /absolute/path/data.xls 回答 2025 年 12 月各縣市 65 歲以上人口占比排名，輸出到 /absolute/path/output
```

Keep the repository-root `AGENTS.md` with the project so its population workflow rules are available as project instructions. When installing the skills into another project, carry those instructions into that project's `AGENTS.md` as well.

The individual commands below are for explicitly scoped stage work. A profiler invocation that also requests an analytical answer must continue through the pipeline.
```text
/taiwan-population-xls-profiler profile /absolute/path/data.xls
/taiwan-population-normalizer normalize it into /absolute/path/output
/taiwan-population-validator validate /absolute/path/output/population.sqlite
/taiwan-population-analyst rank 65+ population share in December 2025 using that database
```

Hermes officially scans `~/.hermes/skills/`, `.hermes/skills/`, and `.agents/skills/`. Restart after copying so the skill index refreshes.
