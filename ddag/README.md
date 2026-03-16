# ddag — Dynamic DAG

An LLM-driven alternative to notebooks for iterative data analysis. Each transformation step is a standalone `.ddag` node, and the DAG connecting them is discovered automatically. You evolve the pipeline through natural language prompts — adding nodes, rewiring dependencies, branching for experiments — without manually managing pipeline code or execution order.

## Quick Start

Every ddag pipeline starts by telling the LLM what data you have and what you want to produce. The LLM handles all node creation, wiring, and builds.

### From a data file

Point at a CSV or Parquet file to wrap it as a source node and start building transforms on top of it:

```
/ddag visits.csv
```

The LLM creates a source node documenting the file, then asks what you want to do with it. Describe your transform in plain English — "filter to visits after January, group by user, count visits per user" — and the LLM proposes a plan, writes the transform, builds it, and shows you sample output.

### From other nodes

Once you have nodes producing outputs, new nodes can consume them. Just describe what you need:

> "Create a node that joins clean_visits with user_profiles and adds a tenure column"

The LLM finds the upstream outputs, wires the sources automatically, and walks you through the same plan → code → build → review cycle.

### From a database

Nodes can query databases directly. The transform function runs arbitrary Python, so any database client works:

```python
def transform(sources, params, outputs):
    import polars as pl
    import duckdb
    conn = duckdb.connect(params['db_path'])
    df = pl.from_arrow(conn.execute(params['query']).fetch_arrow_table())
    df.write_parquet(outputs['raw_events'])
```

These "sourceless" compute nodes have no upstream files — they pull fresh data on each build (auto-stale daily).

### Shared settings

When multiple nodes need the same parameters — thresholds, constants, study-wide configuration — put them in `ddag_settings.py` in the project root:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # Minimum cohort size for reportable results.
    min_cohort_size: int = 30

settings = Settings()
```

Any node can import it: `from ddag_settings import settings`. The frozen dataclass prevents accidental mutation. Just tell the LLM "this should be a global setting" and it will create or update the file.

### Local Python modules

The project root is on the Python path during builds, so you can create local modules for shared utilities — database connectors, custom validators, plotting helpers — and import them from any node's transform function. This keeps transforms focused on the "what" while reusable logic lives in normal Python files alongside the pipeline.

## How It Works

Each `.ddag` file is a self-contained SQLite database storing metadata and a Python transform function (never data). Two node types:

- **Source nodes** document raw data files that exist outside the pipeline
- **Compute nodes** contain a `def transform(sources, params, outputs)` function that reads inputs and writes outputs

DAG edges are discovered automatically by matching source paths to output paths across nodes. If node A's output `clean.parquet` is listed as a source in node B, there's an edge from A to B. Duplicate output paths across active nodes are detected and rejected.

Staleness detection is makefile-like — a compute node is stale if it's never been built, its transform was updated after the last build, or any upstream node was rebuilt more recently. Only stale nodes are rebuilt.

## Features

### Core Pipeline

- **Automatic DAG assembly** from source/output path matching
- **Makefile-like builds** — only rebuild what's changed
- **Cycle detection** with clear error reporting
- **Per-node or full-pipeline builds** with sample output display
- **Force-stale flag** to trigger rebuilds regardless of timestamps
- **Clean command** to delete all compute outputs while preserving source files

### Metadata & Documentation

- **Transform plans** — plain-English descriptions of what each node does, required by the API and kept in sync with code
- **Output descriptions** and **column-level descriptions** for data lineage
- **Schema drift detection** — identifies columns added or removed since descriptions were last written
- **Project settings** (`ddag_settings.py`) — shared frozen-dataclass parameters across nodes, with documentation requirements matching node-level rigor

### Editing & Experimentation

- **In-conversation editing** — modify transforms through natural language prompts
- **External code editor** — opens vim in iTerm2 with vimdiff review and commit workflow
- **Marimo notebook export/import** — export a node to an interactive notebook, experiment, then sync changes back
- **Dump/load cycle** — dump a transform to a `.py` file for external editing, load it back
- **Branching** — clone a node to experiment with alternatives while preserving the original; swap back if needed

### Audit & Quality

- **Node auditor agent** — checks consistency between transform plan, code, inputs, outputs, and column descriptions
- **Comment review workflow** — evaluates inline comments against coding standards
- **Build script generation** — compile the pipeline to a standalone Python file for production, with edit-and-sync-back round-trip

### Inspection

- **Pipeline summary** — node list in topological order with types, descriptions, staleness, and inactive nodes
- **File context lookup** — find which node produces or consumes any data file
- **Lineage tracing** — upstream and downstream dependency chains
- **Diagram rendering** — Graphviz DAG visualization (PNG or `.dot` fallback)
- **JSON output modes** for programmatic use of CLI commands

## Node Schema

Each `.ddag` SQLite database contains 6 tables:

| Table | Purpose |
|-------|---------|
| `script_info` | Node description, active/inactive status, branching origin |
| `sources` | Input file paths (relative to project root) |
| `parameters` | Typed key-value parameters with descriptions |
| `transform_function` | Python function body and transform plan |
| `outputs` | Output file paths with stats (row count, col count, build timestamp) |
| `output_columns` | Per-output column names and descriptions |

## Transform Functions

Compute nodes store a Python function with this signature:

```python
def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df.write_parquet(outputs['clean_visits'])
```

All imports go inside the function body. Dict keys are the file stem (`visits.csv` → `sources['visits']`). Polars is preferred for data operations.

Visualization nodes follow the same pattern, writing an image file:

```python
def transform(sources, params, outputs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    df = pd.read_parquet(sources['metrics'])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df['date'], df['value'])
    plt.savefig(outputs['metrics_chart'], dpi=150, bbox_inches='tight')
    plt.close()
```

Visualization nodes must use `matplotlib.use("Agg")` for headless rendering and `plt.close()` instead of `plt.show()`.

## Project Settings

For pipelines where multiple nodes share parameters (thresholds, constants, study-wide settings), a `ddag_settings.py` file in the project root provides a single source of truth:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # Minimum cohort size for reportable results.
    min_cohort_size: int = 30

settings = Settings()
```

The frozen dataclass prevents accidental mutation at runtime. Transforms access settings via `from ddag_settings import settings`. Every field requires a type annotation, default value, and inline comment explaining its purpose.

## Dependencies

- Python 3.10+
- SQLite (bundled with Python)
- polars (preferred) or pandas for data operations
- Optional: [marimo](https://marimo.io) for interactive notebook editing
- Optional: [Graphviz](https://graphviz.org) for diagram rendering (`brew install graphviz`)

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
