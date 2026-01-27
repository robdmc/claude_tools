# Viz

Data visualization and inspection skill for Claude Code. Create matplotlib/seaborn plots from data files or marimo notebooks, or inspect DataFrames to see their structure and contents.

## Features

- **Visualization**: Generate publication-quality plots with matplotlib and seaborn
- **Data Inspection**: View DataFrame shape, columns, dtypes, and sample rows
- **Marimo Integration**: Extract variables from marimo notebooks via dependency analysis
- **Artifact Management**: Plots saved to `.viz/` with metadata and self-contained scripts

## Usage

### Creating Plots

Ask Claude to visualize your data:

```
Create a bar chart of sales by region from /path/to/sales.csv
```

```
Plot the forecast data from my marimo notebook at /path/to/forecast.nb.py
```

### Inspecting Data

Ask Claude to show you the data:

```
Show me the first 10 rows of the dataframe in /path/to/notebook.nb.py
```

```
What columns are in the forecast table?
```

### Managing Artifacts

List existing visualizations:
```bash
python viz_runner.py --list
```

Clean up all artifacts:
```bash
python viz_runner.py --clean
```

Regenerate a plot (after data changes):
```bash
python .viz/my_plot.py
```

## How It Works

1. **For standalone data**: Claude generates a complete matplotlib script, injects `savefig()`, executes it, and returns the paths
2. **For marimo notebooks**: The skill parses the notebook AST, resolves dependencies to find required cells, assembles a pruned notebook with the plotting code, and executes it

All plots are saved to `.viz/` with:
- `<id>.png` - The rendered plot
- `<id>.py` - Self-contained script (can be re-run directly)
- `<id>.json` - Metadata (description, timestamp, source info)

## Requirements

The skill uses a Python environment fallback chain:

1. **Project environment** - If the data source directory has `pyproject.toml` or `uv.lock`, uses `uv run` from that directory
2. **System Python** - Falls back to `python` on PATH if it has matplotlib
3. **Skill environment** - Last resort uses the skill's own bundled dependencies

### Bundled Dependencies

The skill includes its own `pyproject.toml` with:
- pandas, polars (data handling)
- matplotlib, seaborn (plotting)
- marimo (notebook support)

## Installation

Use the `/install` command from the claude_tools repository:

```
/install viz
```

Or manually copy/symlink the `viz/skills/` directory to your Claude Code skills location.
