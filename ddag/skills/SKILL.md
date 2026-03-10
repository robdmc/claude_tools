---
name: ddag
description: >
  Create and manage data pipeline DAGs where each node is a .ddag SQLite file
  storing transformation metadata. Supports data transforms, visualizations,
  and other artifacts as pipeline outputs. Invoke via /ddag, /ddag <filename>,
  or /ddag diagram. Use when: (1) user invokes /ddag with or without arguments,
  (2) creating data pipeline nodes (.ddag files), (3) defining transform
  functions between data files, (4) checking pipeline staleness or building
  stale nodes, (5) documenting data lineage and column-level metadata,
  (6) modifying existing pipeline nodes, (7) creating visualization nodes
  that produce charts/plots as pipeline outputs.
  Triggers on: /ddag, /ddag diagram, /ddag <filename>, .ddag files, data
  pipeline, DAG node, transform function, data lineage, build pipeline.
  Do NOT use for: general SQL queries, general Python data analysis,
  Airflow/Prefect/dbt pipelines, or ad-hoc data exploration.
---

# ddag Skill

`{SKILL_DIR}` is automatically resolved at runtime to this skill's installation directory.

**CLI vs Python API:** Both cover DAG-wide operations. Use the CLI for user-facing output (status tables, diagrams). Use the Python API when you need structured return values or are composing multiple operations in code.

**When to consult reference files:**
- Branching, cloning, or deactivating nodes → `references/workflows.md` § Branching
- Converting a Python script to a node → `references/workflows.md` § Script Conversion
- Need a function not listed below, or need exact parameter details/examples → `references/api.md`
- Need CLI flags beyond what's in the Quick Reference below → `references/cli.md`
- SQLite table schema and staleness rules → `references/schema.md`

### Python API Quick Reference

```python
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); import ddag_core; import ddag_build

# --- ddag_core: Node CRUD ---

# Creation
ddag_core.create_compute_node(ddag_path, description, source_paths, output_paths, function_body, transform_plan, params=None)
ddag_core.create_source_node(ddag_path, description, output_paths)

# Inspection
ddag_core.read_node(ddag_path)                        # → dict with all node metadata
ddag_core.get_sources_dict(ddag_path)                  # → {stem: path}
ddag_core.get_outputs_dict(ddag_path)                  # → {stem: path}
ddag_core.get_params_dict(ddag_path)                   # → {name: typed_value}
ddag_core.get_transform_plan(ddag_path)                  # → str or None
ddag_core.is_active(ddag_path)                         # → bool

# Modification
ddag_core.set_function(ddag_path, function_body, transform_plan)
ddag_core.update_output_stats(ddag_path, output_path, row_count, col_count)
ddag_core.set_output_description(ddag_path, output_path, description)
ddag_core.set_column_descriptions(ddag_path, output_path, {col_name: description})
ddag_core.remove_source(ddag_path, source_path)
ddag_core.remove_output(ddag_path, output_path)

# Branching & activation
ddag_core.clone_node(src_path, dest_path)       # clone with branched_from tracking
ddag_core.deactivate_node(ddag_path)             # exclude from DAG
ddag_core.activate_node(ddag_path)               # re-include in DAG

# Force staleness
ddag_core.set_force_stale(ddag_path)             # force rebuild on next build
ddag_core.clear_force_stale(ddag_path)           # resume normal staleness rules

# External editing round-trip
ddag_core.dump_function(ddag_path, output_path=None)   # → _ddag_{stem}.py
ddag_core.load_function(ddag_path, input_path=None)    # load edited .py back

# --- ddag_build: DAG-wide operations ---

nodes = ddag_build.scan_nodes(root_dir)                # scan all .ddag files → dict
edges, output_to_node = ddag_build.build_dag(nodes)    # discover DAG edges
stale = ddag_build.find_stale_nodes(root_dir)          # stale nodes in build order
script = ddag_build.generate_build_script(stale, nodes, root_dir)  # → Python script string
ddag_build.update_output_stats_after_build(node_path, root_dir)    # update stats post-build

# Lineage & lookups
ddag_build.trace_lineage(node_path, edges, 'up'|'down')  # → list of ancestor/descendant paths
ddag_build.find_node_for_file(file_path, nodes)           # → node_path or None
ddag_build.find_consumers(file_path, nodes)               # → list of consuming node paths
ddag_build.file_context(file_path, root_dir)              # → full DAG context dict for a file

# Structure
ddag_build.find_connected_components(edges)    # → list of node-path sets (subgraphs)

# Diagram
ddag_build.generate_mermaid(nodes, edges)      # → mermaid source string
ddag_build.render_diagram(root_dir, output_path)  # → PNG path

# Build script round-trip
ddag_build.load_build_script(script_path, root_dir)  # → [(node_path, changed)]
```

### CLI Quick Reference

```bash
CLI="{SKILL_DIR}/scripts/ddag_build.py"
ROOT="--root ."

# DAG-wide
python $CLI summary $ROOT
python $CLI status $ROOT
python $CLI stale $ROOT
python $CLI build $ROOT
python $CLI audit $ROOT
python $CLI diagram $ROOT -o diagram.png

# Per-node
python $CLI build --node path/to/node.ddag $ROOT
python $CLI lineage --node path/to/node.ddag $ROOT
python $CLI dump-function --node path/to/node.ddag $ROOT
python $CLI load-function --node path/to/node.ddag $ROOT

# File lookup
python $CLI file-context --file path/to/data.parquet $ROOT
python $CLI load-script --file _ddag_build.py $ROOT

# Cleanup
python $CLI clean $ROOT --yes   # Delete all compute node outputs (use --yes to skip interactive prompt)
```

## What is a Node

A **node** is a `.ddag` file (SQLite database) representing one step in a data or reporting pipeline. Two types:
- **Source node** (`function_body = NULL`): Documents a raw file that exists outside the pipeline.
- **Compute node**: Contains a Python transform function that reads inputs and writes outputs. Outputs can be data files (`.csv`, `.parquet`) or artifacts like visualizations (`.png`, `.svg`, `.pdf`).

All file paths are **relative to the project root**. The .ddag file stores only metadata, never data. DAG edges are discovered automatically by matching source paths to output paths across nodes. A single node can produce multiple output files.

For the full SQLite schema, see `references/schema.md`.

## Invocation

**Important:** Never execute a node's transform function to discover information about the DAG. All context comes from .ddag metadata only.

### Bare `/ddag` (no arguments)

1. Run `summary` (`python $CLI summary $ROOT`)
2. Scan for inactive nodes: `summary` only returns active nodes. Also glob for all `.ddag` files and call `ddag_core.is_active(path)` on each. Any inactive nodes should appear in the node table with status `INACTIVE` (appended after the active nodes).
3. Branch on the result:

**No nodes found** — Tell the user there's no pipeline yet. Ask how to start:
- Point at a data file to wrap as a source node (`/ddag data.csv`)
- Point at a script to convert into a node (`/ddag script.py`)
- Describe a transform to create from scratch

**One pipeline** (single connected DAG) — Before building the table, call `ddag_core.get_outputs_dict(path)` for each node to get the output file extensions. The `summary` command does not include output paths. Present a node table in topological order with the output file type (e.g., `.parquet`, `.csv`, `.png`) so the user can see at a glance which nodes produce data vs artifacts:

```
| Node | Type | Output | Status | Description |
|------|------|--------|--------|-------------|
| raw_sales.ddag | source | .csv | ok | Raw sales CSV |
| clean_sales.ddag | compute | .parquet | STALE | Clean and filter sales |
| sales_chart.ddag | compute | .png | ok | Monthly sales trend chart |
| old_clean.ddag | compute | .parquet | INACTIVE | (previous version of clean_sales) |
```

Then ask what the user wants to do: inspect a node, rebuild stale nodes, add a new step, view the diagram, etc.

**Multiple pipelines** (disconnected subgraphs) — Present a pipeline summary table, then the node table for each:

```
| # | Sources | Compute | Stale |
|---|---------|---------|-------|
| 1 | 1 | 1 | 1 |
| 2 | 1 | 2 | 0 |
```

Then show a node table (same format as above) per pipeline. Ask which pipeline to work with.

**Cycle detected** — Report the cycle and ask the user to fix it before proceeding.

### `/ddag diagram`

Run `diagram` (`python $CLI diagram $ROOT -o diagram.png`). Display the resulting PNG. If `mmdc` is not installed, show the `.mmd` source as a code block instead.

### "Build the pipeline file" / "Build the execution script"

The `.ddag` abstraction is for **incremental tinkering** — building and refining pipeline steps interactively. Once tinkering is done, the user wants a **single standalone Python file** they can hand off for production use. This is the "compile" step: assembling all compute nodes into one executable script.

Trigger on: "build the pipeline file", "build the pipeline", "compile the pipeline", "build the execution script", "assemble the pipeline", or any semantically similar request.

1. If multiple disconnected DAGs exist and it's ambiguous which one the user means, **ask**.
2. Run: `python $CLI script --all $ROOT`
3. Save the output to `_ddag_build.py` in the project root.
4. Show the user what was generated (node count, file path).

This script can be executed standalone with `python _ddag_build.py` to rebuild all pipeline outputs from scratch.

### Edit-and-sync-back workflow

The generated `_ddag_build.py` is not a one-way export. The user can edit individual transform functions directly in this file, then sync changes back into the `.ddag` nodes. The full round-trip:

1. `script --all` → generate `_ddag_build.py`
2. User edits functions in `_ddag_build.py`
3. Review the changes, revise the transform plan for each changed node
4. `ddag_build.load_build_script('_ddag_build.py', '.', plans={node: updated_plan, ...})` → updates changed `.ddag` nodes with revised plans

### `/ddag clean`

Delete all output files produced by **compute nodes** while leaving source node files untouched.

```bash
python $CLI clean $ROOT --yes
```

The `--yes` flag skips the interactive confirmation prompt (required in non-interactive environments). The command lists files to delete, then deletes them. Source node outputs are never touched.

### `/ddag <filename>` (with a file argument)

Behavior depends on the file type.

**Data file** (`.csv`, `.parquet`):
1. Run `file-context` (`python $CLI file-context --file <path> $ROOT`)
2. **If found in DAG** — present which node produces/consumes it, lineage chain, staleness, and column descriptions. Ask what to do next.
3. **If not found** — tell the user it's untracked. Offer to wrap as a source node (Checkpoint 1 → create → Checkpoint 2).

**Image/artifact file** (`.png`, `.svg`, `.pdf`):
1. Run `file-context` (`python $CLI file-context --file <path> $ROOT`)
2. **If found in DAG** — present which node produces it, lineage chain, staleness, and output description. Display the image if it's a PNG/SVG. Ask what to do next.
3. **If not found** — tell the user it's untracked. (Do not offer to wrap as a source node — generated artifacts are compute outputs.)

**Python script** (`.py`):
Walk the user through converting a script into a compute node. See `references/workflows.md` § Script Conversion for the full procedure.

## Exploring an Existing Pipeline

When dropped into a project with existing .ddag files:

1. Run `status` (`python $CLI status $ROOT`) to list all nodes, their types, and staleness
2. Use `ddag_core.read_node(path)` on key nodes to inspect metadata
3. Run `stale` (`python $CLI stale $ROOT`) to see what needs rebuilding

## Creation Workflow

Three mandatory checkpoints. Everything else is autonomous.

### Checkpoint 1 — Naming

Propose a descriptive name for the .ddag file based on what the node does. User confirms or renames. Place the .ddag file near its output files.

### Checkpoint 1b — Transform Plan (compute nodes only)

Every compute node stores a `transform_plan` — a plain-English description of the transform logic that must be approved by the user before code is written. The plan is **required** by the API: `create_compute_node()` and `set_function()` both require a `transform_plan` argument. This ensures the plan and code are always in sync.

Before writing any transform code, **inspect the schemas of all source files** by reading them with polars/pandas and printing `.schema` (for parquet) or `.dtypes`. Present the schemas alongside the plan so the transform handles the actual column types (e.g., `Datetime` vs `Date`, `Int64` vs `Float64`). This avoids type-mismatch errors at build time.

Then present a plain-English description of the approach. This lets the user audit and modify the logic before code is generated.

**For data output nodes**, the plan should cover:

- **Inputs**: Which source files are read and which columns/subsets are used. Include the actual dtypes from schema inspection.
- **Steps**: Numbered list of data operations in plain language (filtering, joins, aggregations, window functions, etc.). For each step, explain *what* it does and *why*.
- **Edge cases**: How nulls, duplicates, overlapping intervals, or other tricky cases are handled
- **Output**: What the result looks like — columns, grain (one row per what?), expected row count ballpark

**For visualization output nodes** (`.png`, `.svg`, `.pdf`), the plan should cover:

- **Inputs**: Which source files are read and which columns drive the visualization.
- **Chart design**: Chart type (line, bar, scatter, etc.), what's on each axis, how data is segmented (color, facets, subplots).
- **Styling**: Smoothing/aggregation, axis labels, legend, title.
- **Output**: File format and approximate figure size.

**Wait for user approval** before writing the transform function. The user may:
- Approve as-is → proceed to code
- Request changes → revise the plan and re-present
- Reject the approach entirely → discuss alternatives

The approved plan text becomes the `transform_plan` argument when creating the node.

**Skip this checkpoint** only for trivial transforms (single group-by, simple filter, column rename) where the logic is obvious from the user's request. Even then, a brief plan is still required (e.g., "Group visits by user_id, count rows per group").

### Create & Build

For **source nodes** (documenting existing files):
1. Create the .ddag file with `ddag_core.create_source_node()`
2. Proceed to Checkpoint 2

For **compute nodes** (transformations):
1. Write the transform function based on the approved plan
2. Create the .ddag file with `ddag_core.create_compute_node()`
3. Build and execute — the `build` command updates output stats automatically
4. Proceed to Checkpoint 2

### Checkpoint 2 — Metadata Review

After building (or for source nodes, after creation), review output metadata with the user when:
- **Metadata is empty** (first build) — propose descriptions
- **Schema changed** (columns added/removed) — propose descriptions for new columns

**For data outputs** (`.csv`, `.parquet`), present for each output file:
1. Proposed description for the output file
2. Sample rows (5 rows)
3. Column list with proposed descriptions

**For visualization outputs** (`.png`, `.svg`, `.pdf`), present for each output file:
1. Display the image (if PNG/SVG)
2. Proposed description of what the visualization shows — chart type, axes, segmentation, key takeaways
3. Skip column descriptions entirely (not applicable)

Use `ddag_core.set_output_description()` for all outputs. Use `ddag_core.set_column_descriptions()` for data outputs only.

User accepts all, edits specific items, or rejects.

**Skip review** if outputs rebuild with same schema/appearance and existing descriptions are accurate.

### DAG-wide Audit

Run `audit` (`python $CLI audit $ROOT`) to check description health across the entire DAG. The audit has two mandatory phases — deterministic checks (missing descriptions, schema drift) and semantic review (verify descriptions match what the code actually does). Both phases are mandatory. See `references/workflows.md` § DAG-wide Audit for the full procedure.

## Modifying Existing Nodes

- **Change the transform function only**: `ddag_core.set_function(path, new_body, updated_plan)` — faster than re-creating the node. Always update the plan to match the new code.
- **Add/remove sources or outputs**: Re-call `create_compute_node()` with the full updated lists. **Important:** it uses `ON CONFLICT DO NOTHING`, so it will **not** remove old entries — use `remove_source()` / `remove_output()` explicitly.
- **Change parameters**: Re-call `create_compute_node()` with the full updated params dict.

After any modification, run the staleness/build workflow to rebuild affected nodes.

### Deleting a Node

1. Delete the .ddag file from disk
2. Check whether other nodes reference its output paths as sources — update or remove dangling references
3. Run `status` (`python $CLI status $ROOT`) to verify the DAG is still valid

## Branching (Exploratory Workflows)

Clone a node to experiment with alternatives while preserving the original. Use `clone_node` → `deactivate_node` on the original → evolve the clone. Two active nodes must never claim the same output path. See `references/workflows.md` § Branching for the full workflow, swap-back procedure, and rules.

## Iterating on a Transform

The most common action: tweak a transform and see results.

**In-conversation editing** (three-step loop):

1. Read the current plan: `ddag_core.get_transform_plan(path)`
2. Update the function and plan together: `ddag_core.set_function(path, new_body, updated_plan)` — tweak the existing plan text to reflect the code changes
3. `python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .`

**External editor** (dump → edit → load → build): After the user edits the dumped `.py` file, read the new code, revise the existing plan to match, then call `ddag_core.load_function(path, updated_plan)`. See `references/cli.md` for the dump/load commands.

The `build` command handles staleness, execution, stat updates, and prints the first 5 rows of each output. Show these rows to the user.

## Transform Functions

Each compute node stores a Python function with this signature:

```python
def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df.write_parquet(outputs['clean_visits'])
```

Visualization nodes follow the same pattern, writing an image instead of data:

```python
def transform(sources, params, outputs):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.read_parquet(sources['metrics'])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df['date'], df['value'])
    plt.savefig(outputs['metrics_chart'], dpi=150, bbox_inches='tight')
    plt.close()
```

**Rules:** All imports go inside the function body. Source/output dict keys are the file stem (e.g., `visits.csv` → `sources['visits']`). Prefer polars when no clear winner for data library.

**Visualization rules:** Always use `matplotlib.use("Agg")` for headless rendering and `plt.close()` instead of `plt.show()` — transforms run in build scripts without a display. If the `viz` skill is installed, you can reference its styling guide (`~/.claude/skills/viz/references/styling.md`) for publication-quality defaults (fonts, colors, layout). Otherwise, use matplotlib/seaborn defaults with sensible figure sizes.

## Staleness & Building

Staleness is makefile-like: a compute node is stale if never built, if its function was updated after the last build, or if any upstream output was rebuilt more recently. Source nodes are never stale.

Before the first build, verify that required Python packages (e.g., polars, pandas, duckdb) are available in the user's Python environment.

**Preferred — use the `build` command** (handles everything in one step):

```bash
python {SKILL_DIR}/scripts/ddag_build.py build --root .
```

This finds stale nodes, executes transforms, updates output stats, and prints sample rows. Output stats (row_count, col_count) are auto-detected for CSV and Parquet files only. Visualization outputs (`.png`, `.svg`, `.pdf`) will not have stats — this is expected.

**Manual alternative** (when you need the build script as a file):
1. Run `script` to generate the build script
2. Save as `_ddag_build.py` (ephemeral, gitignored) and execute
3. Update output stats with `ddag_build.update_output_stats_after_build()`

**Incorporating edits from a build script:** If the user edited `_ddag_build.py`, run `load-script` to update the changed nodes back. This is the one exception to the "never execute a transform to learn about the DAG" rule.

After building, proceed to metadata review (Checkpoint 2) for any nodes with empty descriptions.

## Error Recovery

Common errors and fixes:

- **Build fails with ImportError**: Install the missing package (`pip install polars`, etc.) and retry.
- **Build fails with transform error**: Fix the function with `ddag_core.set_function()`, then rebuild.
- **"database is locked" error**: Another process has the .ddag file open. Close it and retry.
- **Staleness detection seems wrong**: Run `status` to inspect timestamps — check `updated_at` vs `built_at`.
- **"Duplicate output path" error on build**: Two active nodes claim the same output. Deactivate one (see Branching).
- **Schema drift after rebuild**: Run `audit` to identify new/removed columns, then update descriptions at Checkpoint 2.

## Anti-patterns

- **Never write output/column descriptions without user review** — always present proposals first
- **Never store data in .ddag files** — they only hold metadata
- **Never use absolute paths** — all paths are relative to project root
- **Never skip the metadata review** on first build
- **Never re-call `create_compute_node` when `set_function` suffices** — it's slower and touches more metadata
- **Never assume `create_compute_node` removes old sources/outputs** — it doesn't; use `remove_source()`/`remove_output()` explicitly
- **Never create a node without checking for existing nodes** that already produce the same outputs
- **Never execute a transform function to learn about the DAG** — all context comes from .ddag metadata only (exception: `load-script` for user-edited build scripts)
