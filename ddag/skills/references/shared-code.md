# Shared Code & DRY Patterns

Transform functions can import any Python module from the project root. The build system adds the project root to `sys.path` before executing transforms, so local `.py` files are importable just like installed packages.

## Local Modules

Place shared utility files in the project root (or a subdirectory that's a proper Python package with `__init__.py`). Any transform can import from them:

```python
# project_root/cleaning.py
def standardize_dates(df):
    """Convert mixed date formats to ISO 8601."""
    import polars as pl
    return df.with_columns(pl.col("date").str.to_date().alias("date"))
```

```python
# In a node's transform function
def transform(sources, params, outputs):
    from cleaning import standardize_dates
    import polars as pl
    df = pl.read_csv(sources['raw_events'])
    df = standardize_dates(df)
    df.write_parquet(outputs['clean_events'])
```

### Conventions

- **One module per concern** — `cleaning.py`, `db.py`, `metrics.py`, not a monolithic `utils.py`
- **Functions, not classes** — keep helpers as plain functions that take and return dataframes or simple values
- **Imports inside functions** — just like in transforms, heavy imports (polars, pandas, duckdb) go inside the helper function body so the module is lightweight to import
- **Docstrings required** — every public function needs a one-line docstring explaining what it does. If the function has non-obvious parameters or edge cases, expand to a multi-line docstring
- **No side effects** — modules should define functions, not execute code on import (unlike `ddag_settings.py` which intentionally instantiates a singleton)

### Relationship to ddag_settings.py

`ddag_settings.py` is a special case of a local module — it follows a prescribed frozen-dataclass pattern for shared configuration values. See `references/settings.md` for its specific conventions.

General-purpose local modules are for shared *logic* (functions), while `ddag_settings.py` is for shared *values* (constants and thresholds).

## DRY Audit

When auditing a pipeline (via `/ddag audit` or when reviewing multiple nodes), scan for duplicated logic across transforms. This is a qualitative check — the LLM reads the transform code for all compute nodes and flags:

1. **Identical or near-identical code blocks** appearing in 2+ nodes — candidate for extraction into a shared module
2. **Hardcoded values that repeat** across nodes — candidate for `ddag_settings.py` (see `references/settings.md`)
3. **Similar patterns with slight variations** — candidate for a parameterized helper function

### When to flag

- During a full pipeline audit (`/ddag audit` with no node argument)
- When creating a new node whose transform resembles existing ones
- When the user explicitly asks to DRY up the pipeline

### How to present

After the per-node consistency checks, add a **DRY opportunities** section:

```
DRY opportunities:

1. Nodes clean_visits.ddag and clean_events.ddag both contain identical
   date-parsing logic (lines ~3-5). Extract to a shared module:
   → cleaning.py::standardize_dates(df)

2. The value 0.95 appears as a hardcoded confidence level in 3 nodes.
   → Move to ddag_settings.py::confidence_level
```

### What NOT to flag

- Boilerplate that's inherent to the transform pattern (reading sources, writing outputs)
- Single-line operations that happen to be similar (e.g., `df.head(10)` in two places)
- Logic that's similar in shape but genuinely different in intent across nodes
