---
name: ddag
description: >
  Like Make for data files — track dependencies between data files and
  automatically rebuild stale outputs. Each pipeline node is a .ddag SQLite
  file storing transformation metadata (never data). Supports data transforms,
  visualizations, and other artifacts as pipeline outputs.
  Invoke via /ddag, /ddag <filename>, or /ddag diagram.
  Use when: (1) user invokes /ddag with or without arguments,
  (2) creating data pipeline nodes (.ddag files), (3) defining transforms
  between data files, (4) checking pipeline staleness or building stale nodes,
  (5) documenting data lineage and column-level metadata,
  (6) modifying existing pipeline nodes, (7) creating visualization nodes
  that produce charts/plots as pipeline outputs,
  (8) asking which node produces a given file or where data comes from.
  Triggers on: /ddag, /ddag diagram, /ddag <filename>, .ddag files, data
  pipeline, DAG node, data lineage, build pipeline, which node produces
  this file, data provenance, edit code, see the code, review code,
  open in editor.
  Do NOT use for: general SQL queries, general Python data analysis,
  Airflow/Prefect/dbt pipelines, or ad-hoc data exploration.
---

# ddag Skill

`{SKILL_DIR}` is automatically resolved at runtime to this skill's installation directory.

**CLI vs Python API:** Both cover DAG-wide operations. Use the CLI for user-facing output (status tables, diagrams). Use the Python API when you need structured return values or are composing multiple operations in code.

**When to consult reference files:**
- Branching, cloning, or deactivating nodes → `references/workflows.md` § Branching
- Converting a Python script to a node → `references/workflows.md` § Script Conversion
- Build-script generation, edit-and-sync-back workflow → `references/workflows.md` § Build Script Workflow
- Build or transform errors → `references/workflows.md` § Error Recovery
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
ddag_core.read_node(ddag_path)                        # → dict (see keys below)
#   Keys: description, is_active, branched_from, force_stale, sources (list of paths),
#   parameters (list of dicts), transform_function (str|None), transform_plan (str|None),
#   updated_at, outputs (list of {path, description, row_count, col_count, built_at}),
#   output_columns ({output_path: [{name, description}]}), is_source_node (bool)
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
ddag_core.dump_function(ddag_path, output_path=None)              # → _ddag_{stem}.py
ddag_core.load_function(ddag_path, transform_plan, input_path=None)  # load edited .py back (plan required)

# --- ddag_build: DAG-wide operations ---

nodes = ddag_build.scan_nodes(root_dir)                           # scan active .ddag files → dict
nodes = ddag_build.scan_nodes(root_dir, include_inactive=True)    # scan ALL .ddag files (active + inactive)
edges, output_to_node = ddag_build.build_dag(nodes)               # discover DAG edges
conflicts = ddag_build.check_output_conflicts(nodes)              # → [(output_path, [node_paths])] or []
stale = ddag_build.find_stale_nodes(root_dir)                     # stale nodes in build order
all_compute = ddag_build.find_all_compute_nodes(root_dir)         # all compute nodes in build order
script = ddag_build.generate_build_script(stale, nodes, root_dir) # → Python script string
built = ddag_build.build_nodes(root_dir, node_filter=None, sample_rows=5)  # build stale, update stats, print samples → [node_paths]
ddag_build.update_output_stats_after_build(node_path, root_dir)   # update stats post-build

# Lineage & lookups
ddag_build.trace_lineage(node_path, edges, 'up'|'down')  # → list of ancestor/descendant paths
ddag_build.find_node_for_file(file_path, nodes)           # → node_path or None
ddag_build.find_consumers(file_path, nodes)               # → list of consuming node paths
ddag_build.file_context(file_path, root_dir)              # → dict (see keys below)
#   Keys: found (bool), file_path, producer (node_path|None), producer_meta (read_node dict|None),
#   consumers ([node_paths]), consumer_metas ([read_node dicts]), lineage_up ([node_paths]),
#   lineage_down ([node_paths]), stale (bool|None)

# Structure
ddag_build.find_connected_components(edges)    # → list of node-path sets (subgraphs)

# Diagram
ddag_build.generate_dot(nodes, edges)            # → Graphviz DOT source string
ddag_build.render_diagram(root_dir, output_path)  # → PNG path (requires dot)

# Build script round-trip
ddag_build.parse_build_script(script_path)                        # → {node_path: function_body} (inspect without updating)
ddag_build.load_build_script(script_path, root_dir, plans={node: plan})  # → [(node_path, changed)] (plans required for changed nodes)

# Audit
result = ddag_build.audit_descriptions(root_dir)  # → {"drift": [...], "review_packets": [...]}
result = ddag_build.audit_node(node_path, root_dir)  # → same structure, scoped to one node
# Each review_packet: {node, description, inputs, transform, transform_plan, parameters, outputs, drift}
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
python $CLI audit --node path/to/node.ddag $ROOT   # single-node audit
python $CLI diagram $ROOT -o diagram.png

# Per-node
python $CLI build --node path/to/node.ddag $ROOT
python $CLI lineage --node path/to/node.ddag $ROOT
python $CLI dump-function --node path/to/node.ddag $ROOT
python $CLI load-function --node path/to/node.ddag --plan "Updated plan text" $ROOT

# File lookup
python $CLI file-context --file path/to/data.parquet $ROOT

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
2. Scan for inactive nodes: `summary` only returns active nodes. Call `ddag_build.scan_nodes(root_dir, include_inactive=True)` and filter for nodes where `is_active` is False. Any inactive nodes should appear in the node table with status `INACTIVE` (appended after the active nodes).
3. Branch on the result:

**No nodes found** — Tell the user there's no pipeline yet. Ask how to start:
- Point at a data file to wrap as a source node (`/ddag data.csv`)
- Point at a script to convert into a node (`/ddag script.py`)
- Describe a transform to create from scratch

**One pipeline** (single connected DAG) — Call `ddag_core.get_outputs_dict(path)` for each node to get output file extensions (not included in `summary`). Present a node table in topological order with columns: Node, Type (source/compute), Output extension, Status (ok/STALE/INACTIVE), Description. Include inactive nodes at the bottom. Ask what the user wants to do next.

**Multiple pipelines** (disconnected subgraphs) — Show a pipeline summary (sources, compute, stale counts per subgraph), then a node table per pipeline. Ask which pipeline to work with.

**Cycle detected** — Report the cycle and ask the user to fix it before proceeding.

### `/ddag diagram`

Run `diagram` (`python $CLI diagram $ROOT -o diagram.png`). Display the resulting PNG. If `dot` is not installed, show the `.dot` source as a code block and tell the user to install Graphviz (`brew install graphviz`).

### "Build the pipeline file" / "Build the execution script"

Compile all compute nodes into a single standalone Python file for production use. See `references/workflows.md` § Build Script Workflow for the full procedure including the edit-and-sync-back round-trip.

Trigger on: "build the pipeline file", "build the pipeline", "compile the pipeline", "build the execution script", "assemble the pipeline", or any semantically similar request.

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

**`summary` vs `status`:** `summary` returns JSON (node counts, pipeline structure) — use it for programmatic decisions (e.g., bare `/ddag` invocation). `status` prints a human-readable table with per-node staleness — use it for display and exploration.

When dropped into a project with existing .ddag files:

1. Run `status` (`python $CLI status $ROOT`) to list all nodes, their types, and staleness
2. Use `ddag_core.read_node(path)` on key nodes to inspect metadata
3. Run `stale` (`python $CLI stale $ROOT`) to see what needs rebuilding

## Explaining a Node's Logic

When the user asks how a node works, what its logic is, what it does, or anything semantically similar — respond with three parts in this order:

1. **Purpose** (1-2 sentences): Why this node exists — what job it does for the pipeline. Focus on the *why*, not the plumbing. Don't just say what feeds it or consumes it (the user can see that from the table); instead explain the analytical role it plays. Use `read_node()` metadata (description, sources, outputs, downstream consumers) to infer purpose.

2. **Transform plan (verbatim)**: Present the node's `transform_plan` exactly as stored, word-for-word. Format it for readability (line breaks, bullet points) but **do not change, omit, or rephrase any content**. Do NOT use blockquote (`>`) formatting — it renders dimmed in terminals. Use regular markdown instead. This is the audited source of truth. Use `ddag_core.get_transform_plan(path)` to retrieve it.

3. **In plain English** (2-4 short sentences): A casual rephrasing of the plan in simpler language. Keep sentences short and direct — no run-ons. This is clearly labeled as a summary and is secondary to the verbatim plan above.

**Why verbatim matters:** The transform plan is the user-approved, audited specification. Paraphrasing risks losing precision or introducing inaccuracies. The exact wording is what was reviewed and approved.

## Creation Workflow

Three mandatory checkpoints. Everything else is autonomous.

### Checkpoint 1 — Naming

Propose a descriptive name for the .ddag file based on what the node does. User confirms or renames. Place the .ddag file alongside its output files (e.g., if outputs go to `analysis/`, put the .ddag file in `analysis/` too).

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

The approved plan text becomes the `transform_plan` argument when creating the node. **Store the plan in the exact structured format that was presented to the user** — with the labeled bullet sections (Inputs, Steps, Edge cases, Output for data nodes; Inputs, Chart design, Styling, Output for visualization nodes). The stored plan and the presented plan must be identical.

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

Check consistency across the entire DAG — verifying that each node's transform plan, code, and metadata tell a consistent story. See `references/workflows.md` § DAG-wide Audit for the full procedure including how to spawn `node-auditor` agents in parallel.

## Modifying Existing Nodes

- **Change the transform function only**: `ddag_core.set_function(path, new_body, updated_plan)` — faster than re-creating the node. Always update the plan to match the new code, using the structured bullet format from Checkpoint 1b.
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
2. Update the function and plan together: `ddag_core.set_function(path, new_body, updated_plan)` — revise the existing plan to reflect the code changes. **The updated plan must use the same structured bullet format as Checkpoint 1b** (Inputs/Steps/Edge cases/Output for data nodes; Inputs/Chart design/Styling/Output for viz nodes). If the existing plan is prose, reformat it into the structured format while incorporating the changes.
3. `python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .`

**External editor** (vim in iTerm2): Opens the node's code in vim in a new terminal window. See "External Code Editor" section below.

**External editor** (dump → edit → load → build): After the user edits the dumped `.py` file, read the new code, revise the existing plan to match, then call `ddag_core.load_function(path, updated_plan)`. **The revised plan must use the same structured bullet format as Checkpoint 1b.** See `references/cli.md` for the dump/load commands.

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

**Incorporating edits from a build script:** If the user edited `_ddag_build.py`, use the edit-and-sync-back workflow (see `references/workflows.md` § Build Script Workflow) to parse changes and update nodes via the Python API. This is the one exception to the "never execute a transform to learn about the DAG" rule.

After building, proceed to metadata review (Checkpoint 2) for any nodes with empty descriptions.

## Error Recovery

For common errors (ImportError, database locked, staleness detection issues, duplicate output paths, schema drift), see `references/workflows.md` § Error Recovery.

## External Code Editor

Open a node's transform code in vim in a new iTerm2 window for hands-on editing, review, and commit — without going through the conversation.

**Trigger phrases:** "edit the code", "see the code", "review the code", "open in editor", "open in vim", "let me edit it"

**Invocation:**

```python
subprocess.run([sys.executable, '{SKILL_DIR}/scripts/ddag_edit.py', '<node_path>', '--root', '.'])
```

**What happens:**
1. The node's `function_body` is written to `.ddag_work/<name>.code.py`
2. Vim opens in a new iTerm2 window with the code
3. After vim exits, vimdiff shows a side-by-side review if changes were made
4. User chooses to commit or abandon
5. On commit, changes are written back to the .ddag file via `load_function` (existing transform plan is preserved)
6. A single-node audit runs automatically, showing the review packet and any schema drift

**After the user returns from editing:** The iTerm2 window handles the full commit workflow. If the user committed changes, the node's function is already updated. Run a build to execute the updated transform:

```bash
python {SKILL_DIR}/scripts/ddag_build.py build --node <node_path> --root .
```

**Error cases:**
- Source nodes (no code): exits with error message
- Previous session files in `.ddag_work/`: warns and cleans up before proceeding
- `load_function` failure: temp files are preserved so the user can retry

## Anti-patterns

- **Never write output/column descriptions without user review** — always present proposals first
- **Never store data in .ddag files** — they only hold metadata
- **Never use absolute paths** — all paths are relative to project root
- **Never skip the metadata review** on first build
- **Never re-call `create_compute_node` when `set_function` suffices** — it's slower and touches more metadata
- **Never assume `create_compute_node` removes old sources/outputs** — it doesn't; use `remove_source()`/`remove_output()` explicitly
- **Never create a node without checking for existing nodes** that already produce the same outputs
- **Never execute a transform function to learn about the DAG** — all context comes from .ddag metadata only (exception: `load-script` for user-edited build scripts)
