# ddag SQLite Schema Reference

> **Source of truth**: The authoritative schema is `SCHEMA_SQL` in `scripts/ddag_core.py`. This file is a human-readable reference and must stay in sync.

Each `.ddag` file is a SQLite database representing one node in a data pipeline DAG.

## Tables

Tables: script_info, sources, parameters, transform_function, outputs, output_columns.

### script_info (singleton)

Describes what this node does. One row always.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Always 1, PRIMARY KEY |
| description | TEXT | Human/LLM-readable purpose of this node |
| is_active | INTEGER | 1 = active (in DAG), 0 = inactive (excluded). Default 1 |
| branched_from | TEXT | Path of the node this was cloned from, or NULL |
| force_stale | INTEGER | 1 = force stale, 0 = normal staleness rules. Only toggled by user. Default 0 |

### sources

Input file dependencies (CSV or Parquet). DAG edges are discovered by matching source paths to output paths across nodes.

| Column | Type | Notes |
|--------|------|-------|
| path | TEXT | Relative path from project root, UNIQUE |

### parameters

Build parameters the transformation depends on.

| Column | Type | Notes |
|--------|------|-------|
| name | TEXT | PRIMARY KEY |
| type | TEXT | Python type: str, int, float, bool. Default 'str' |
| default_value | TEXT | |
| current_value | TEXT | |
| description | TEXT | |

### transform_function (singleton)

Embedded Python transform function. NULL function_body = source node.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Always 1, PRIMARY KEY |
| function_body | TEXT | Python function def, or NULL for source nodes |
| transform_plan | TEXT | Plain-English description of what the transform does, reviewed by user before code was written. Required whenever function_body is set. |
| updated_at | TEXT | ISO 8601 timestamp |

### outputs

Output files this node produces (Parquet). Stats populated after build.

| Column | Type | Notes |
|--------|------|-------|
| path | TEXT | Relative path from project root, PRIMARY KEY |
| description | TEXT | LLM-readable purpose |
| row_count | INTEGER | NULL until built |
| col_count | INTEGER | NULL until built |
| built_at | TEXT | ISO 8601 timestamp |

### output_columns

Column-level descriptions per output file. For LLM consumption.

| Column | Type | Notes |
|--------|------|-------|
| output_path | TEXT | FK to outputs.path |
| name | TEXT | Column name |
| description | TEXT | LLM-readable purpose |
| | | PRIMARY KEY (output_path, name) |

## Node Types

- **Source node**: `transform_function.function_body IS NULL`
- **Compute node**: `transform_function.function_body` contains a Python function definition

## Staleness Rules

1. **force_stale**: Any node with `force_stale = 1` is unconditionally stale. The flag itself does not propagate, but all downstream nodes are also considered stale (because their upstream is stale). Only toggled by explicit user action.
2. **Source nodes**: Never stale (externally managed) unless force_stale is set.
3. **Sourceless compute nodes** (e.g. DB queries): Stale if last built before today (same-day rule).
4. **Compute nodes with sources**: Stale if never built, output files missing, function updated after build, or upstream outputs are newer.

See SKILL.md for node type details and transform function signature.
