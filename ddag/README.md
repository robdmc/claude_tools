# ddag — Dynamic DAG

An LLM-driven alternative to notebooks for iterative data analysis.

## The Idea

Transforming raw data into analysis typically involves piecemeal iteration — experimenting with different transformations, filters, and aggregations to discover what's useful. Notebooks are the traditional tool for this, but they mix code, state, and output in ways that make reproducibility and iteration difficult.

**ddag** takes a different approach: each transformation step is a standalone `.ddag` node (a SQLite file storing metadata and a Python transform function), and the DAG connecting them is discovered automatically. You evolve the pipeline dynamically through natural language prompts to an LLM agent — adding nodes, rewiring dependencies, branching for experiments — without manually managing pipeline code or execution order.

When combined with the [viz](/viz) tool in this project, ddag provides a fully prompt-driven workflow for going from raw data to polished visualizations.

## How It Works

- **Source nodes** document raw data files that exist outside the pipeline
- **Compute nodes** contain a Python transform function (`def transform(sources, params, outputs)`) that reads inputs and writes outputs
- DAG edges are discovered automatically by matching source paths to output paths across nodes
- Staleness detection is makefile-like: only rebuild what's changed
- Nodes can be branched for exploratory workflows while preserving the original

## Key Concepts

- Each `.ddag` file is a self-contained SQLite database with 6 tables
- All file paths are relative to the project root
- Transform functions have imports inside the function body
- Build scripts and Mermaid diagrams can be generated from the DAG

## Dependencies

- Python 3.10+
- polars (preferred) or pandas for data operations
- Optional: `mmdc` (mermaid-cli) for diagram rendering

## Installation

Use the `/install` command from the claude_tools repository:

```
/install
```
