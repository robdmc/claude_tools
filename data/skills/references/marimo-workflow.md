# Marimo Notebook Creation Workflow

When the user asks to open a data file in a marimo notebook:

1. **Name the notebook** based on the data file (e.g., `sales.csv` → `sales_explorer.py`)
2. **Create the notebook** using the Write tool with this minimal structure (no markdown, no summaries — just load and display):

```python
import marimo

app = marimo.App(width="full")

@app.cell
def _():
    import marimo as mo
    import pandas as pd
    return mo, pd

@app.cell
def _(pd):
    df = pd.read_csv("<path_to_file>")  # adjust reader for file type
    df
    return (df,)

if __name__ == "__main__":
    app.run()
```

3. **Install marimo prompts** into the user's working directory so future sessions know how to edit marimo notebooks:

```bash
mkdir -p .claude/prompts
cp {SKILL_DIR}/prompts/marimo.md .claude/prompts/marimo.md
cp {SKILL_DIR}/prompts/marimo-check.md .claude/prompts/marimo-check.md
cp {SKILL_DIR}/prompts/viz-preferences.md .claude/prompts/viz-preferences.md
```

4. **Read all three prompts** so they are in context for the current session. Use the Read tool on each file before creating or editing any notebook cells:
   - `.claude/prompts/marimo.md`
   - `.claude/prompts/marimo-check.md`
   - `.claude/prompts/viz-preferences.md`

5. **Validate** the notebook:

```bash
uv run --project {SKILL_DIR}/scripts marimo check <notebook_file>
```

6. **Ask the user** if they'd like to open the notebook. If they say yes, launch it as a background task:

```bash
uv run --project {SKILL_DIR}/scripts marimo edit <notebook_file>
```

Always run this command with `run_in_background: true` so the user can continue working while the notebook opens.
