---
name: viz
description: >
  Create publication-quality interactive visualizations from data files.
  Use when user asks to plot, chart, graph, or visualize data.
  Supports matplotlib/seaborn with interactive display and PNG output.
allowed-tools: >
  Read, Write(.viz/*), Glob(.viz/*),
  Bash(uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py *),
  Bash
---

# Viz Skill

## Data Requirement

All data must live in `.viz/`. Before plotting, always copy or generate the source data into `.viz/<name>.parquet` (or `.csv`), even if the original is a local file. This makes every visualization fully self-contained and reproducible.

## Workflow

1. **Materialize data** — Copy or generate data into `.viz/<name>.parquet` (or `.csv`)
2. **Check for collisions** — Verify no existing `.viz/<name>.py` conflicts with your chosen name
3. **Write script** — Use the Write tool to create `.viz/<name>.py`
4. **Execute** — Run via the viz runner
5. **Report** — Confirm the output path `.viz/<name>.png` to the user

## File Convention

Every visualization is a name-prefix triplet inside `.viz/`:

| File | Purpose |
|------|---------|
| `<name>.parquet` | Data (or `.csv`) |
| `<name>.py` | Plotting script |
| `<name>.png` | Output image |

Names must be `lowercase_snake_case`. All paths inside scripts are **relative** — the runner `cd`s into `.viz/` before execution.

## Script Generation

Every generated script must include these sections in order:

1. **Imports** — All imports inside the script (self-contained execution)
2. **Data loading** — Hardcoded: `pd.read_parquet('<name>.parquet')` or `pd.read_csv('<name>.csv')`
3. **Plot creation** — matplotlib/seaborn, publication quality
4. **Watermark** — Small semi-transparent name label at bottom-right
5. **Save** — `plt.savefig('<name>.png', dpi=150, bbox_inches='tight')`
6. **Show** — `plt.show()` as the last line

### Example Script

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_parquet('monthly_sales.parquet')

fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(data=df, x='month', y='revenue', ax=ax)
ax.set_title('Monthly Revenue', fontsize=14)
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Revenue ($)', fontsize=12)
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()

fig.text(0.99, 0.01, 'monthly_sales', transform=fig.transFigure,
         fontsize=7, color='gray', alpha=0.3, ha='right', va='bottom')

plt.savefig('monthly_sales.png', dpi=150, bbox_inches='tight')
plt.show()
```

## Runner Usage

Create a visualization:
```bash
uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py <name>
```

Update an existing visualization (overwrites the PNG):
```bash
uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py <name> --overwrite
```

List all existing visualizations:
```bash
uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py --list
```

## Efficiency Tips

- **Parallelize** independent Write calls (e.g., writing the data-generation script and the plot script at the same time when they are independent).
- **Chain** data generation with the runner in a single Bash call where possible:
  ```bash
  python -c "import shutil; shutil.copy('/path/to/source.parquet', '.viz/sales.parquet')" && uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py sales
  ```
- For simple data copies, combine into one Bash invocation. Write both scripts in parallel, then chain execution sequentially.

## Styling

For publication-quality guidance — font sizes, figure sizes, colorblind-friendly palettes, and when to choose seaborn vs matplotlib — see **{SKILL_DIR}/references/styling.md**.

## Refinement

To modify an existing plot, use the read-modify-overwrite pattern:

1. Read `.viz/<name>.py`
2. Modify the script
3. Overwrite `.viz/<name>.py` (using the Write tool)
4. Run: `uv run --directory {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/viz_runner.py <name> --overwrite`

For extended iteration (5+ rounds of refinement), consider spawning a subagent to keep the main conversation clean.
