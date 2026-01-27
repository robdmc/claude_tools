---
name: viz
description: Data visualization and inspection skill. Use when user asks to plot, chart, graph, or visualize data from files or marimo notebooks. Also use for DataFrame inspection when user wants to "show", "display", or "see" data structure (columns, dtypes, first N rows). Supports matplotlib/seaborn for plots, marimo notebook extraction, and artifact management in /tmp/viz/.
allowed-tools: Read, Write(/tmp/viz/_draft.py), Glob(/tmp/viz/*), Grep(/tmp/viz/*), Bash(rm -f /tmp/viz/_draft.py), Bash(python {SKILL_DIR}/scripts/viz_runner.py:*), Bash(uv run --directory {SKILL_DIR}/scripts python *)
---

# Viz Skill: Data Visualization and Inspection

> **CRITICAL: Never use heredocs (`<< 'EOF'`) to pass scripts to viz_runner.py.**
> Always use the Write tool to create `/tmp/viz/_draft.py`, then pass `--file /tmp/viz/_draft.py` to the runner.

## Contents

- [Purpose](#purpose)
- [Input Specification](#input-specification)
- [Intent Detection](#intent-detection)
- [Artifact Management](#artifact-management)
- [Skill Workflow](#skill-workflow)
- [Refinement and Regeneration](#refinement-and-regeneration)
- [Marimo Notebook Support](#marimo-notebook-support) (see references/marimo.md)
- [Library Selection and Styling](#library-selection-and-styling) (see references/styling.md)

## Purpose

This skill **directly executes** visualizations. The calling agent provides a visualization spec along with data context, and the skill:
1. Infers the data loading code from the provided context
2. Generates the complete plotting script
3. Executes it via the `viz_runner.py` helper
4. Returns artifact paths for the caller to reference

**Key pattern:**
```
Caller (with data context) → Skill (infers data loading, generates script, executes) → Plot appears
```

## Input Specification

### Required
- **Visualization spec**: What to plot (chart type, axes, title, special features)

### Data Context (one of these forms)
- **Database + query**: "Data from `/full/path/to/data.ddb`, table `forecast`, columns month, members"
- **SQL query**: "Run this SQL: `SELECT * FROM forecast WHERE year >= 2024`"
- **Code snippet**: "Load data like this: `df = pd.read_parquet('/full/path/to/data.parquet')`"
- **File path**: "CSV at `/tmp/data.csv` with columns X, Y, Z"

**CRITICAL: Absolute Paths Required** — Scripts execute from `/tmp/viz/`, not the caller's directory. All file paths must be absolute.

### Optional
- **Suggested ID**: A name hint (e.g., `pop_bar`, `churn_trend`). The runner ensures uniqueness.

## Intent Detection

**Before generating any code, analyze the user's request to determine the appropriate mode.**

### Inspection Mode (use `--show`)
Use when the user wants to **see the data itself**, not a visualization:
- "Show me the dataframe"
- "Display the first N rows"
- "What does the data look like?"
- "What columns are in X?"

**Action:** Use `--show` flag. Do NOT generate plot code.

### Visualization Mode (generate plot)
Use when the user wants a **chart, graph, or visual representation**:
- "Plot the data"
- "Create a chart of..."
- "Visualize the trend"
- "Bar chart showing..."

**Action:** Generate matplotlib/seaborn code, write to temp file, execute via runner.

### Ambiguous Requests
If unclear (e.g., "show me X over time"):
- If the request mentions chart types (bar, line, scatter) → visualization
- If the request is about structure/columns/rows → inspection
- When in doubt, use `--show` first (it's cheaper), then offer to plot

## Artifact Management

All artifacts are managed in `/tmp/viz/` via the helper script.

### Helper: `viz_runner.py`

```bash
python {SKILL_DIR}/scripts/viz_runner.py --file /tmp/viz/_draft.py --id NAME --desc "Description"
```

The runner:
1. Creates `/tmp/viz/` if needed
2. Ensures ID uniqueness (appends `_2`, `_3`, etc. if collision)
3. Injects `plt.savefig('/tmp/viz/<id>.png', dpi=150, bbox_inches='tight')` before `plt.show()`
4. Writes the script to `/tmp/viz/<id>.py`
5. Executes the script
6. Writes metadata to `/tmp/viz/<id>.json`

### Output Format

Terminal output:
```
Plot: pop_bar
  "Bar chart of members by month"
  png: /tmp/viz/pop_bar.png
```

### List and Cleanup

```bash
python {SKILL_DIR}/scripts/viz_runner.py --list   # Show all visualizations
python {SKILL_DIR}/scripts/viz_runner.py --clean  # Remove all files
```

## Skill Workflow

**CRITICAL: Do NOT use heredocs (`<< 'EOF'`).** Use the temp file pattern:

1. **Infer data loading**: Generate Python code to load/create the DataFrame using absolute paths
2. **Generate visualization**: Add matplotlib/seaborn code for the requested plot
3. **Write to temp file**: Run `rm -f /tmp/viz/_draft.py` first, then use the Write tool to create `/tmp/viz/_draft.py` with the complete script
4. **Execute via runner**:
   ```bash
   python {SKILL_DIR}/scripts/viz_runner.py --file /tmp/viz/_draft.py --id suggested_name --desc "Short description"
   ```
   The runner reads the temp file, deletes it, then writes the final script to `/tmp/viz/<id>.py`.
5. **Return to caller**: Report final ID and paths

### Example Tool Sequence

```
1. Bash tool  → rm -f /tmp/viz/_draft.py (delete stale draft if present)
2. Write tool → /tmp/viz/_draft.py (complete Python script)
3. Bash tool  → python viz_runner.py --file /tmp/viz/_draft.py --id my_plot --desc "..."
```

**Why no heredocs?** Heredocs clutter the console output and require extra permissions. The temp file pattern is cleaner.

### Important: Do NOT Auto-Read PNGs

Do NOT automatically read the PNG into context after generating a plot. The plot window opens via `plt.show()`, so the user can already see it.

**Only read the PNG when:**
- The user explicitly asks you to analyze the graph
- You need to learn something from the visual output

**Instead, offer to open it:**
```bash
open /tmp/viz/pop_bar.png  # macOS
```

## Refinement and Regeneration

### Refining an Existing Plot
1. Read the existing script from `/tmp/viz/<id>.py`
2. Apply modifications
3. Execute with a new ID (e.g., `pop_bar_2`)

### Regenerating a Plot
Run the saved script using the viz skill's Python environment:
```bash
uv run --directory {SKILL_DIR}/scripts python /tmp/viz/pop_bar.py
```

The script contains the hardcoded savefig path, so it overwrites the existing PNG.

## Marimo Notebook Support

For extracting and plotting data from marimo notebooks, see **[references/marimo.md](references/marimo.md)**.

Key features:
- Extract variables via AST-based dependency analysis
- Prune notebooks to only required cells
- `--show` mode for data inspection
- `--target-line` for capturing intermediate state

## Library Selection and Styling

For guidance on choosing between matplotlib/seaborn and publication quality standards, see **[references/styling.md](references/styling.md)**.
