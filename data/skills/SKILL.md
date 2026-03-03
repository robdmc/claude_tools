---
name: data
description: >
  Data wrangling, analysis, and statistics on tabular data.
  Use when user wants to examine, explore, filter, join, aggregate, reshape,
  clean, summarize, profile, or compute statistics on any data file readable
  by pandas or polars (CSV, Parquet, Excel, JSON, etc.).
  Also use when user wants to open a data file in a marimo notebook.
  Do NOT use for charting, plotting, or visualization — delegate those to viz.
allowed-tools: >
  Read, Glob, Write,
  Bash(uv run --project {SKILL_DIR}/scripts python *),
  Bash(uv run --project {SKILL_DIR}/scripts marimo *),
  Bash(mkdir -p .claude/prompts*),
  Bash(cp {SKILL_DIR}/prompts/*)
---

# Data Skill

Analyze, wrangle, and compute statistics on tabular data using Python with polars, pandas, duckdb, and scipy.

## Execution

Run all analysis via:

```bash
uv run --project {SKILL_DIR}/scripts python -c "<code>"
```

For multi-line scripts (>3 lines), write a temp file and run it:

```bash
uv run --project {SKILL_DIR}/scripts python /tmp/data_analysis.py
```

Always use `{SKILL_DIR}/scripts` so the skill's dependencies are available.

## Library Selection

| Task | Library |
|------|---------|
| Large file, fast transforms, group-by, joins | **polars** |
| SQL-style queries, multi-file joins, aggregations | **duckdb** |
| Compatibility with existing pandas code, small data | **pandas** |
| Statistical tests, distributions, linear algebra | **scipy.stats** |

Default to **polars** unless there's a reason to use something else.

## Messy Data Workflow

**When to probe vs. load directly:**

- **Parquet files**: Load directly — already typed and clean
- **CSV with a `.parquet` sibling** (cleaned by gsheet): Load the parquet
- **Raw/unfamiliar CSV files**: Probe first, then clean
- **When in doubt**: Probe — it's fast and cheap

**Probing unfamiliar files:**

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/probe.py <file>
```

Use the probe output to identify skip_rows, header row, and relevant column groups, then load with targeted parameters and clean formatted numbers (`$`, `,`, `%`).

## Supported Formats

CSV, TSV, Parquet, JSON, NDJSON, Excel (`uv run --with openpyxl`), fixed-width text.

## Output

Print results to stdout. For statistical tests, include test name, statistic, p-value, and interpretation.

## Viz Delegation

Do not generate charts. Prep data for the viz skill:

```python
df.write_parquet(".viz/prepared_data.parquet")
```

Then tell the user to use `/viz`.

## Marimo Notebooks

For interactive data exploration, create marimo notebooks. See [references/marimo-workflow.md](references/marimo-workflow.md) for the full creation workflow.
