# Marimo Notebook Support

The viz skill can extract data from marimo notebooks and generate plots without modifying the original notebook.

## How It Works

1. **Copy notebook** to `/tmp/viz/<id>.py`
2. **Analyze dependencies** to identify cells needed for target data
3. **Prune unneeded cells** from the copied notebook
4. **Inject plotting code** as a new cell at the end
5. **Execute via subprocess** with `cwd` set to original notebook's directory (so relative paths work)

## CLI Interface

```bash
python {SKILL_DIR}/scripts/viz_runner.py \
    --marimo \
    --notebook /path/to/notebook.nb.py \
    --target-var df_forecast \
    --id forecast_plot \
    --desc "Monthly forecast visualization" \
    << 'EOF'
# Plotting code that uses df_forecast
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(df_forecast['date'], df_forecast['total_final_members'])
plt.show()
EOF
```

## Parameters

- `--marimo`: Enable marimo notebook mode (required)
- `--notebook`: Path to the marimo notebook file (required)
- `--target-var`: Variable to extract from the notebook (required)
- `--target-line`: Optional line number for capturing intermediate state (for mutated variables)
- `--id`: Suggested ID for the visualization (optional)
- `--desc`: Description of the visualization (optional)
- `--show`: Show mode - print dataframe info to console instead of plotting (no stdin required)
- `--rows`: Number of rows to display in show mode (default: 5)

## Dependency Analysis

Marimo notebooks encode dependencies explicitly:
- Cell parameters = variables the cell **reads** (refs)
- Cell return tuple = variables the cell **defines** (defs)

The skill walks backwards from the target variable through the dependency graph to find all required cells.

## Target Line (Advanced)

When a variable is mutated within a cell, use `--target-line` to capture intermediate state:

```python
@app.cell
def _(raw_data):
    df = raw_data.copy()           # line 45
    df = df[df['value'] > 0]       # line 46 - filtered
    df = df.groupby('cat').sum()   # line 47 - aggregated
    return (df,)
```

Use `--target-var df --target-line 46` to capture `df` after filtering but before aggregation.

## Show Mode (Data Inspection)

Use `--show` to print dataframe info to console instead of generating a plot:

```bash
python {SKILL_DIR}/scripts/viz_runner.py \
    --marimo \
    --notebook /path/to/notebook.nb.py \
    --target-var df \
    --show \
    --rows 10
```

Output:
```
Shape: (12345, 5)
Columns: ['date', 'profile_id', 'kind', 'state', 'channel_type']

Dtypes:
date              datetime64[ns]
profile_id                 int64
kind                      object
state                     object
channel_type              object

First 10 rows:
        date  profile_id     kind state channel_type
0 2021-01-01      123456  monthly    CA      organic
1 2021-01-02      123457  monthly    TX         paid
...
```

## Example Workflow

**User request:**
> "Plot the member forecast over time from the operational forecast notebook"

**Agent workflow:**
1. Read the notebook to identify candidate variables
2. Ask clarifying questions if multiple candidates exist
3. Execute:

```bash
python {SKILL_DIR}/scripts/viz_runner.py \
    --marimo \
    --notebook /Users/rob/repos/project/forecast.nb.py \
    --target-var df_deliverable \
    --id member_forecast \
    --desc "Historical and forecast members" \
    << 'EOF'
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(df_deliverable['date'], df_deliverable['total_final_members'])
ax.set_xlabel('Date')
ax.set_ylabel('Members')
ax.set_title('Member Population Over Time')
plt.tight_layout()
plt.show()
EOF
```

## Important Notes

- The **original notebook is never modified** (read-only access)
- All work happens on a copy in `/tmp/viz/`
- The script runs with the notebook's directory as cwd, so relative file paths work
- Uses `uv run python` if the notebook directory contains `pyproject.toml` or `uv.lock`
