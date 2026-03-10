# ddag

Data pipeline DAG management where each node is a `.ddag` SQLite file storing transformation metadata.

## What It Does

- Create and manage data pipeline nodes as `.ddag` files (SQLite databases)
- Define transform functions between data files with a standard `def transform(sources, params, outputs)` signature
- Automatically discover DAG edges by matching source paths to output paths across nodes
- Detect staleness (makefile-like) and rebuild only what's needed
- Document data lineage with output and column-level descriptions
- Branch nodes for exploratory workflows while preserving the original
- Generate standalone build scripts or Mermaid DAG diagrams

## Node Types

- **Source nodes**: Document raw files that exist outside the pipeline (no transform function)
- **Compute nodes**: Contain a Python transform function that reads inputs and writes outputs

## Key Concepts

- Each `.ddag` file is a self-contained SQLite database with 6 tables
- All file paths are relative to the project root
- DAG edges are discovered automatically by matching source paths to output paths
- Staleness is makefile-like: compare timestamps to determine what needs rebuilding
- Transform functions use `def transform(sources, params, outputs)` with imports inside the function body

## Dependencies

- Python 3.10+
- polars (preferred) or pandas for data operations
- Optional: `mmdc` (mermaid-cli) for diagram rendering

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
