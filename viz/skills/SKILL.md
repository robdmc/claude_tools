---
name: viz
description: Data visualization and inspection skill. Use when user asks to plot, chart, graph, or visualize data from files or marimo notebooks. Also use for DataFrame inspection when user wants to "show", "display", or "see" data structure (columns, dtypes, first N rows). Supports matplotlib/seaborn for plots, marimo notebook extraction, and artifact management in .viz/.
allowed-tools: Read, Write(.viz/_draft.py), Glob(.viz/*), Grep(.viz/*), Bash(rm -f .viz/_draft.py), Bash(python {SKILL_DIR}/scripts/viz_runner.py:*), Bash(uv run --directory {SKILL_DIR}/scripts python *), Bash(open *)
---

# Viz Skill: Data Visualization and Inspection

> **CRITICAL: Never use heredocs (`<< 'EOF'`) to pass scripts to viz_runner.py.**
> Always use the Write tool to create `.viz/_draft.py`, then pass `--file .viz/_draft.py` to the runner.

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

**CRITICAL: Absolute Paths Required** — Scripts execute from `.viz/`, not the caller's directory. All file paths must be absolute.

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

### Existing Plot References
If user references a plot by ID (e.g., "regenerate pop_bar", "modify the cosine_wave plot"):
1. Check if `.viz/<id>.py` exists
2. If yes, read the script and follow the [Refinement and Regeneration](#refinement-and-regeneration) workflow
3. If no, inform user the plot wasn't found and offer to list available plots with `--list`

**Action:** `python {SKILL_DIR}/scripts/viz_runner.py --list` shows all available plots.

### View Mode (open images)
Use when the user wants to **see existing plot images**:
- "Show me all my plots"
- "Open the images" / "View what I've created"
- "Let me see the sine_wave plot"
- "Compare plot1 and plot2"
- "Show me the recent plots"

**Selecting which images to open:**

1. **Explicit ID reference**: User names a plot → open that specific PNG
   - "open the sine_wave" → `open -a Preview .viz/sine_wave.png`

2. **Recent context**: User just created a plot or discussed one → open that one
   - After generating `forecast_chart`: "let me see it" → `open -a Preview .viz/forecast_chart.png`

3. **All plots**: User asks for everything or uses plural without specifics
   - "show me my plots" / "open all images" → `open -a Preview .viz/*.png`

4. **Subset by pattern**: User describes a category or pattern
   - "show me the forecast plots" → use `--list` to find matching IDs, then open those

5. **Comparison**: User wants to compare specific plots
   - "compare X and Y" → `open -a Preview .viz/X.png .viz/Y.png`

6. **Ambiguous**: When unclear which plot(s) the user means
   - Run `--list` first, then ask or infer from context

**Action:** Use `open -a Preview` to open PNG files. Use `--list` first if needed to identify which plots exist.

## Artifact Management

All artifacts are managed in `.viz/` via the helper script.

### Helper: `viz_runner.py`

```bash
python {SKILL_DIR}/scripts/viz_runner.py --file .viz/_draft.py --id NAME --desc "Description"
```

The runner:
1. Creates `.viz/` if needed and adds it to `.gitignore`
2. Ensures ID uniqueness (appends `_2`, `_3`, etc. if collision)
3. Injects `plt.savefig('.viz/<id>.png', dpi=150, bbox_inches='tight')` before `plt.show()`
4. Writes the script to `.viz/<id>.py`
5. Executes the script
6. Writes metadata to `.viz/<id>.json`

### Output Format

Terminal output:
```
Plot: pop_bar
  "Bar chart of members by month"
  png: .viz/pop_bar.png
```

### List and Cleanup

```bash
python {SKILL_DIR}/scripts/viz_runner.py --list   # Show all visualizations
python {SKILL_DIR}/scripts/viz_runner.py --clean  # Remove all files
```

### Viewing Plots

Open plots in Preview (macOS):
```bash
open -a Preview .viz/*.png           # All plots
open -a Preview .viz/my_plot.png     # Single plot
open -a Preview .viz/plot1.png .viz/plot2.png  # Multiple specific plots
```

## Skill Workflow

**CRITICAL: Do NOT use heredocs (`<< 'EOF'`).** Use the temp file pattern:

1. **Infer data loading**: Generate Python code to load/create the DataFrame using absolute paths
2. **Generate visualization**: Add matplotlib/seaborn code for the requested plot
3. **Write to temp file**: Run `rm -f .viz/_draft.py` first, then use the Write tool to create `.viz/_draft.py` with the complete script
4. **Execute via runner**:
   ```bash
   python {SKILL_DIR}/scripts/viz_runner.py --file .viz/_draft.py --id suggested_name --desc "Short description"
   ```
   The runner reads the temp file, deletes it, then writes the final script to `.viz/<id>.py`.
5. **Return to caller**: Report final ID and paths

### Example Tool Sequence

```
1. Bash tool  → rm -f .viz/_draft.py (delete stale draft if present)
2. Write tool → .viz/_draft.py (complete Python script)
3. Bash tool  → python viz_runner.py --file .viz/_draft.py --id my_plot --desc "..."
```

**Why no heredocs?** Heredocs clutter the console output and require extra permissions. The temp file pattern is cleaner.

### Important: Do NOT Auto-Read PNGs

Do NOT automatically read the PNG into context after generating a plot. The plot window opens via `plt.show()`, so the user can already see it.

**Only read the PNG when:**
- The user explicitly asks you to analyze the graph
- You need to learn something from the visual output

**Instead, offer to open it:**
```bash
open -a Preview .viz/pop_bar.png  # Single plot (macOS)
open -a Preview .viz/*.png        # All plots
```

## ID Watermarks

Plots include a small, semi-transparent watermark showing the plot ID in the bottom-right corner by default. This helps track plots during iterative development.

### Disabling Watermarks

Add `--no-watermark` for clean/production versions:
```bash
python {SKILL_DIR}/scripts/viz_runner.py --file .viz/_draft.py --id my_plot --no-watermark
```

### When to Disable Watermarks

Recognize these user requests as triggers for `--no-watermark`:
- "clean version" / "clean copy"
- "for presentation" / "presentation quality"
- "production ready" / "final version"
- "no watermark" / "without ID"
- "export quality"

## Refinement and Regeneration

### Refining an Existing Plot
1. Read the existing script from `.viz/<id>.py`
2. Apply modifications
3. Execute with a new ID (e.g., `pop_bar_2`)

### Regenerating a Plot
To regenerate while preserving the original:
1. Read the existing script from `.viz/<id>.py`
2. Write to temp file and execute via runner with the same ID:
   ```bash
   rm -f .viz/_draft.py
   # Write script content to .viz/_draft.py
   python {SKILL_DIR}/scripts/viz_runner.py --file .viz/_draft.py --id pop_bar --desc "Regenerated"
   ```

The runner's `get_unique_id()` will automatically create `pop_bar_2`, `pop_bar_3`, etc. if the ID exists, preserving the original.

## Marimo Notebook Support

For extracting and plotting data from marimo notebooks, see **[references/marimo.md](references/marimo.md)**.

Key features:
- Extract variables via AST-based dependency analysis
- Prune notebooks to only required cells
- `--show` mode for data inspection
- `--target-line` for capturing intermediate state

## Library Selection and Styling

For guidance on choosing between matplotlib/seaborn and publication quality standards, see **[references/styling.md](references/styling.md)**.
