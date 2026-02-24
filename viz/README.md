# Viz

Data visualization and inspection skill for Claude Code. Create matplotlib/seaborn plots from data files, inspect DataFrames, and manage a library of visualizations.

## Features

- **Visualization**: Generate publication-quality plots with matplotlib and seaborn
- **Data Inspection**: View DataFrame shape, columns, dtypes, and sample rows
- **Artifact Management**: Plots saved to `.viz/` with metadata and self-contained scripts
- **ID Watermarks**: Plots include a subtle ID watermark for easy tracking during iteration
- **Refinement**: Modify existing plots while preserving originals with auto-incrementing IDs

## Usage

### Creating Plots

Ask Claude to visualize your data:

```
Create a bar chart of sales by region from /path/to/sales.csv
```

### Inspecting Data

Ask Claude to show you the data structure:

```
Show me the first 10 rows of the dataframe in /path/to/notebook.nb.py
```

```
What columns are in the forecast table?
```

### Viewing Existing Plots

Open plots in your image viewer:

```
Show me all my plots
Open the sine_wave plot
Compare forecast_v1 and forecast_v2
```

### Refining Plots

Modify existing plots (originals are preserved):

```
Regenerate pop_bar with a different color scheme
Update the forecast plot to use log scale
```

When refining, the skill reads the existing script and creates a new version (e.g., `pop_bar_2`).

### Managing Artifacts

List existing visualizations:
```bash
python viz_runner.py --list
```

Clean up all artifacts:
```bash
python viz_runner.py --clean
```

Re-run a plot script directly:
```bash
python .viz/my_plot.py
```

## ID Watermarks

Plots include a small, semi-transparent watermark showing the plot ID in the bottom-right corner. This helps track plots during iterative development.

For clean/production versions, ask for "no watermark", "clean version", or "presentation quality" and Claude will omit the watermark.

## How It Works

1. Claude generates a complete matplotlib script, injects `savefig()`, executes it, and returns the paths

All plots are saved to `.viz/` with:
- `<id>.png` - The rendered plot (with ID watermark by default)
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

## Installation

Use the `/install` command from the claude_tools repository:

```
/install viz
```

Or manually copy/symlink the `viz/skills/` directory to your Claude Code skills location.
