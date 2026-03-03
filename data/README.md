# Data

Data wrangling, analysis, and statistics on tabular data using Python with polars, pandas, duckdb, and scipy.

## What It Does

- Analyze, filter, join, aggregate, reshape, clean, summarize, and profile tabular data
- Compute statistics (t-tests, chi-squared, correlations, etc.) via scipy
- Probe unfamiliar CSV files to understand their structure before loading
- Create marimo notebooks for interactive data exploration
- Prep data into `.viz/` Parquet files for handoff to the viz skill

## Supported Formats

- CSV / TSV
- Parquet
- JSON / NDJSON
- Excel (via openpyxl)
- Fixed-width text

## Library Selection

| Task | Library | Why |
|------|---------|-----|
| Large file, fast transforms, group-by, joins | **polars** | Fastest, lazy evaluation, low memory |
| SQL-style queries, multi-file joins, aggregations | **duckdb** | Zero-copy reads of CSV/Parquet, SQL interface |
| Compatibility with existing pandas code, small data | **pandas** | Broad ecosystem, familiar API |
| Statistical tests, distributions, linear algebra | **scipy** | `scipy.stats` for t-tests, chi-squared, correlations, etc. |

Defaults to **polars** unless there's a reason to use something else.

## Dependencies

The bundled uv environment includes:

- polars
- pandas
- duckdb
- scipy
- pyarrow
- marimo
- holoviews / hvplot
- seaborn / matplotlib

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
