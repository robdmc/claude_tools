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
  open in editor, pipeline settings, global parameters, global variables,
  shared constants, project-wide settings, ddag_settings, change a setting
  across all nodes, same threshold everywhere.
  Do NOT use for: general SQL queries, general Python data analysis,
  Airflow/Prefect/dbt pipelines, or ad-hoc data exploration.
---

# ddag Skill

`{SKILL_DIR}` is automatically resolved at runtime to this skill's installation directory.

**When to consult reference files:**
- Python API function signatures → `references/python-api.md`
- Branching, cloning, or deactivating nodes → `references/workflows.md` § Branching
- Converting a Python script to a node → `references/workflows.md` § Script Conversion
- Build-script generation, edit-and-sync-back workflow → `references/workflows.md` § Build Script Workflow
- Build or transform errors → `references/workflows.md` § Error Recovery
- Need CLI flags beyond what's in the Quick Reference below → `references/cli.md`
- SQLite table schema and staleness rules → `references/schema.md`
- Inline commenting standards for transform code → `references/code-comments.md`
- Project-wide settings file (ddag_settings.py) → `references/settings.md`

### Python API (REQUIRED for all node operations)

```python
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); import ddag_core; import ddag_build
```

**NEVER manipulate .ddag SQLite files directly — no raw SQL, no sqlite3 CLI, no direct file access.** All node creation, modification, branching, and metadata updates MUST go through the Python API. Before making any API call, read `references/python-api.md` for exact function signatures — do not rely on memory for parameter names or order. If unsure how to execute a task involving .ddag nodes, consult the Python API reference first — the function you need likely already exists.

For read-only inspection, prefer CLI commands (see CLI Quick Reference below).

### Important Routing Rule

**When the user expresses any intent to view, inspect, review, or edit a node's transform code — ALWAYS invoke the External Code Editor flow** (opens vim in iTerm2). Do NOT dump the code inline in the conversation or use `dump-function` to display it. The user wants hands-on access in their editor, not a read-only display in chat. Match semantically, not literally — "let me see the code", "can I look at the code", "show me the transform", "pull up the code", "I want to check the implementation" all mean the same thing. See the "External Code Editor" section below for invocation details.

### CLI Quick Reference

```bash
CLI="{SKILL_DIR}/scripts/ddag_build.py"
ROOT="--root ."

# DAG-wide
python $CLI summary $ROOT
python $CLI summary --include-inactive $ROOT
python $CLI status $ROOT
python $CLI status --include-inactive $ROOT
python $CLI stale $ROOT
python $CLI build $ROOT
python $CLI audit $ROOT
python $CLI audit --node path/to/node.ddag $ROOT   # single-node audit
python $CLI diagram $ROOT -o diagram.png

# Per-node inspection
python $CLI show --node path/to/node.ddag $ROOT    # full node metadata as JSON

# Per-node operations
python $CLI build --node path/to/node.ddag $ROOT
python $CLI lineage --node path/to/node.ddag $ROOT
python $CLI dump-function --node path/to/node.ddag $ROOT
python $CLI load-function --node path/to/node.ddag --plan "Updated plan text" $ROOT

# File lookup
python $CLI file-context --file path/to/data.parquet $ROOT

# JSON output (for programmatic use)
python $CLI stale --json $ROOT
python $CLI build --json $ROOT
python $CLI audit --json $ROOT

# Build script generation
python $CLI script $ROOT > _ddag_build.py

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

1. Run `summary --include-inactive` (`python $CLI summary --include-inactive $ROOT`) — this single call returns everything needed: node list in topological order, descriptions, output paths, node types (source/compute), staleness, and inactive nodes.
2. Branch on the result:

**No nodes found** — Tell the user there's no pipeline yet. Ask how to start:
- Point at a data file to wrap as a source node (`/ddag data.csv`)
- Point at a script to convert into a node (`/ddag script.py`)
- Describe a transform to create from scratch

**One pipeline** (single connected DAG) — All data is in the summary response: `outputs` for file paths, `types` for source/compute, `stale_nodes` for staleness, `descriptions` for descriptions. No additional CLI calls needed. Present a node table in topological order with columns: Node, Type (source/compute), Output extension, Status (ok/STALE/INACTIVE), Description. Include inactive nodes at the bottom. Ask what the user wants to do next.

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

### Audit (single node or whole DAG)

**Trigger:** user says "audit", "audit <node>", "audit the pipeline", or semantically similar.

An audit has two steps — structural check via CLI, then LLM critique via node-auditor agents. **Always do both.**

1. **Get review packets:**
   - Single node: `python $CLI audit --node <path> $ROOT --json`
   - Whole DAG: `python $CLI audit $ROOT --json`

2. **Spawn `node-auditor` agents** — one per review packet in the result's `review_packets` array. Pass the full packet (inputs, transform code, transform plan, parameters, outputs, drift) as the agent prompt. Each agent checks:
   - Transform plan vs code — does the code implement what the plan describes?
   - Input consistency — does the code use all declared sources and parameters?
   - Output consistency — do output/column descriptions match what the code produces?
   - Schema drift — columns added/removed since descriptions were written?
   - Cross-node consistency — are column semantics preserved across node boundaries?
   - Cross-cutting — is the node description accurate?

3. **Run agents in parallel** for 4+ nodes. For 1–3 nodes, sequential is fine.

4. **Present results:** Each agent returns `CONSISTENT` or `INCONSISTENT` with specific issues. Surface any inconsistencies to the user for resolution (fix code via `set_function` or fix metadata via `set_output_description`/`set_column_descriptions`).

The CLI `audit` command alone only checks structural metadata (drift, missing descriptions). The node-auditor agent is what reviews plan-to-code consistency — **always spawn it**.

### Comment Review

**Trigger:** "check comments", "update comments", "improve comments", "review the comments", "comment this node", "add comments", or any semantically similar request about inline code commenting quality. May target a single node ("improve comments on X") or the whole pipeline.

1. Read `references/code-comments.md` to load the commenting standards
2. **Scope:**
   - Single node specified → `show --node <path>` to get transform code and plan
   - No node specified → run `summary` to get all compute nodes, then `show --node` each one
3. For each node, evaluate comments against the guide:
   - Add missing *why*-comments (business logic, edge cases, domain assumptions)
   - Remove comments that just restate the code
   - Add a transform header if the function is non-trivial and lacks one
   - Add section comments for multi-step transforms
4. Present the proposed changes per node — show the updated function body as a diff or side-by-side so the user can review
5. On approval, update via `set_function()` with the existing `transform_plan` preserved (commenting changes don't alter the plan)
6. Skip source nodes (no transform code)

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

**`summary --include-inactive`** is the single entry point for understanding a pipeline. It returns JSON with node list (topological order), types, descriptions, output paths, staleness, and inactive nodes — everything needed to orient. Use `show --node` only when you need a specific node's transform code, plan, column descriptions, or parameters.

When dropped into a project with existing .ddag files:

1. Run `summary --include-inactive` (`python $CLI summary --include-inactive $ROOT`) — one call gives you nodes, types, outputs, staleness, and descriptions
2. Use `python $CLI show --node <path> $ROOT` only for nodes you need to inspect in detail (transform code, plan, column metadata)

## Explaining a Node's Logic

When the user asks how a node works, what its logic is, what it does, or anything semantically similar — respond with three parts in this order:

1. **Purpose** (1-2 sentences): Why this node exists — what job it does for the pipeline. Focus on the *why*, not the plumbing. Don't just say what feeds it or consumes it (the user can see that from the table); instead explain the analytical role it plays. Use `python $CLI show --node <path> $ROOT` metadata (description, sources, outputs, downstream consumers) to infer purpose.

2. **Transform plan (verbatim)**: Present the node's `transform_plan` exactly as stored, word-for-word. Format it for readability (line breaks, bullet points) but **do not change, omit, or rephrase any content**. Do NOT use blockquote (`>`) formatting — it renders dimmed in terminals. Use regular markdown instead. This is the audited source of truth. The `show` command includes `transform_plan` in its JSON output.

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

1. Read the current plan: `python $CLI show --node <path> $ROOT` (the `transform_plan` field in the JSON output)
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

**Commenting:** Comment transform code per `references/code-comments.md` — explain *why* (business logic, edge cases, domain assumptions), skip comments that just restate the code. Read the reference before writing non-trivial transforms.

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
1. Run `python $CLI script $ROOT > _ddag_build.py` to generate the build script
2. Execute `_ddag_build.py` (ephemeral, gitignored)
3. Update output stats with `ddag_build.update_output_stats_after_build()`

**Incorporating edits from a build script:** If the user edited `_ddag_build.py`, use the edit-and-sync-back workflow (see `references/workflows.md` § Build Script Workflow) to parse changes and update nodes via the Python API. This is the one exception to the "never execute a transform to learn about the DAG" rule.

After building, proceed to metadata review (Checkpoint 2) for any nodes with empty descriptions.

## Error Recovery

For common errors (ImportError, database locked, staleness detection issues, duplicate output paths, schema drift), see `references/workflows.md` § Error Recovery.

## External Code Editor

Open a node's transform code in vim in a new iTerm2 window for hands-on editing, review, and commit — without going through the conversation.

**Trigger:** Any user intent to view, inspect, review, or edit a node's transform code. Match semantically — don't require exact phrases. Examples include "see the code", "show me the code", "let me look at the implementation", "can I review this", "pull up the transform", "open in editor", "open in vim", etc. When in doubt, prefer opening the editor over dumping code inline.

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

## Marimo Notebook Export

Export a node's transform function to a Marimo notebook for interactive experimentation, then import changes back.

**Trigger:** "open in marimo", "marimo notebook", "export to marimo", "experiment interactively", or semantically similar requests for interactive notebook editing.

**Export:**

```python
subprocess.run([sys.executable, '{SKILL_DIR}/scripts/ddag_marimo.py', node_path, '--root', '.'])
```

Creates `<stem>.ddag.nb.py` in the working directory with three cells: imports, transform function, and a run cell pre-populated with the node's sources/params/outputs dicts. On first export, fetches marimo docs to `.claude/prompts/marimo.md` in the working project.

After export, tell the user to run `marimo edit <stem>.ddag.nb.py` to open the notebook.

**Import (after user edits):**

```python
subprocess.run([sys.executable, '{SKILL_DIR}/scripts/ddag_marimo.py', node_path, '--import', '--root', '.'])
```

Only the `def transform(sources, params, outputs)` function is extracted from the notebook — all other cells are ignored. The existing `transform_plan` is preserved; the user/agent updates it separately if needed. After import, build the node to execute the updated transform.

**Edge cases:**
- Source nodes: rejected with error (no transform to export)
- Existing notebook on export: overwritten with warning
- No changes detected on import: skipped with message

## Project Settings (ddag_settings.py)

**Recognize this need when the user says:** "global parameter", "global variable", "shared constant", "project-wide setting", "same value across nodes", "change this threshold everywhere", "use the same X in all nodes", "pipeline settings", or refers to a value that multiple nodes should agree on. When you detect this intent, check for an existing `ddag_settings.py` in the project root — create one if absent, or add the new field if it exists.

For file structure, documentation requirements, settings vs params guidance, and the field-creation checklist → `references/settings.md`

Quick reference — accessing settings in transform code:
```python
def transform(sources, params, outputs):
    from ddag_settings import settings
    # settings.min_cohort_size, settings.confidence_level, etc.
```

## Anti-patterns

- **Never write output/column descriptions without user review** — always present proposals first
- **Never store data in .ddag files** — they only hold metadata
- **Never use absolute paths** — all paths are relative to project root
- **Never skip the metadata review** on first build
- **Never re-call `create_compute_node` when `set_function` suffices** — it's slower and touches more metadata
- **Never assume `create_compute_node` removes old sources/outputs** — it doesn't; use `remove_source()`/`remove_output()` explicitly
- **Never create a node without checking for existing nodes** that already produce the same outputs
- **Never execute a transform function to learn about the DAG** — all context comes from .ddag metadata only (exception: `load-script` for user-edited build scripts)
