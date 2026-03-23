# ddag Advanced Workflows

## Contents

- [Build Script Workflow](#build-script-workflow)
- [Script Conversion](#script-conversion)
- [Branching (Exploratory Workflows)](#branching-exploratory-workflows)
- [DAG-wide Audit](#dag-wide-audit)
- [DRY Scan](#dry-scan)
- [Templating Transform Code](#templating-transform-code)
- [Error Recovery](#error-recovery)

## Build Script Workflow

The `.ddag` abstraction is for **incremental tinkering**. Once tinkering is done, the user wants a **single standalone Python file** for production use — the "compile" step.

### Generate the build script

1. If multiple disconnected DAGs exist and it's ambiguous which one the user means, **ask**.
2. Run: `python $CLI script --all $ROOT`
3. Save the output to `_ddag_build.py` in the project root.
4. Show the user what was generated (node count, file path).

This script can be executed standalone with `python _ddag_build.py` to rebuild all pipeline outputs from scratch.

### Edit-and-sync-back

The generated `_ddag_build.py` is not a one-way export. The user can edit individual transform functions directly in this file, then sync changes back into the `.ddag` nodes. The full round-trip:

1. `script --all` → generate `_ddag_build.py`
2. User edits functions in `_ddag_build.py`
3. Inspect what changed: `ddag_build.parse_build_script('_ddag_build.py')` → `{node_path: function_body}` — compare against current node functions to identify edits
4. Review the changes, revise the transform plan for each changed node. **Use the same structured bullet format as Checkpoint 1b** (Inputs/Steps/Edge cases/Output for data nodes; Inputs/Chart design/Styling/Output for viz nodes). If the existing plan is prose, reformat it into the structured format while incorporating the changes.
5. `ddag_build.load_build_script('_ddag_build.py', '.', plans={node: updated_plan, ...})` → updates changed `.ddag` nodes with revised plans

## Script Conversion

Convert a Python script into a ddag compute node (`/ddag script.py`):

1. Read the script file
2. Identify inputs (reads) and outputs (writes) — ask the user to confirm
3. Identify hardcoded values that should become parameters — propose them
4. Refactor the logic into a `def transform(sources, params, outputs)` function body
5. Present the proposed function body for user approval
6. Once approved, follow the Creation Workflow (Checkpoint 1 → create compute node → build → Checkpoint 2)

**Example result** — hardcoded reads/writes become dict lookups, hardcoded values become parameters:

```python
def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['raw_sales'])
    df = df.filter(pl.col("amount") > params['min_amount'])
    df.write_parquet(outputs['clean_sales'])
```

## Branching (Exploratory Workflows)

Branch a node to experiment with alternatives while preserving the original. The clone keeps the same output paths, so downstream nodes wire automatically — no rewiring needed.

Use `clone_node`, `deactivate_node`, and `activate_node` from `ddag_core` (see the Python API Quick Reference in SKILL.md for signatures).

### Branch a node

1. Clone: `ddag_core.clone_node("aggregate.ddag", "aggregate_v2.ddag")`
2. Deactivate original: `ddag_core.deactivate_node("aggregate.ddag")`
3. Evolve the clone freely

### Swap back

1. Deactivate clone: `ddag_core.deactivate_node("aggregate_v2.ddag")`
2. Reactivate original: `ddag_core.activate_node("aggregate.ddag")`
3. Rebuild downstream

The `status` command shows inactive nodes labeled `[INACTIVE]`.

### Rules

- **Two active nodes must never claim the same output path.** The build system errors on conflict. Always deactivate before activating the alternative.
- `clone_node` sets `branched_from` on the clone, so the origin is always traceable.
- Inactive nodes are excluded from DAG assembly, staleness checks, and builds.

## DAG-wide Audit

Run `audit` to check consistency across the entire DAG — verifying that each node's transform plan, code, and metadata tell a consistent story.

```python
result = ddag_build.audit_descriptions(root_dir)
```

### Procedure

1. **Get review packets**: Call `ddag_build.audit_descriptions(root_dir)`. Each review packet is a self-contained bundle for one compute node: input descriptions/columns (from upstream), transform code, transform plan, parameters, output descriptions/columns, and schema drift.

2. **Spawn auditor agents in parallel**: For each review packet, spawn a `node-auditor` agent (`{AGENTS_DIR}/node-auditor.md`) with the packet as its prompt. Each agent runs in its own context window and checks:
   - Transform plan vs code — does the code implement what the plan describes?
   - Input consistency — does the code use all declared sources and parameters?
   - Output consistency — do output/column descriptions match what the code produces?
   - Schema drift — are there columns added/removed from actual files since descriptions were written?
   - Cross-node consistency — does the code/plan treat each input consistently with the producer's output descriptions? Do join scopes align? Are column semantics preserved or silently reinterpreted?
   - Cross-cutting — is the node description accurate?

3. **Collect results**: Each agent returns either `CONSISTENT` (one line) or `INCONSISTENT` with a list of specific issues.

4. **Surface inconsistencies**: Present any `INCONSISTENT` results to the user. For each inconsistency, the user decides whether to fix the code (via `set_function`) or the metadata (via `set_output_description`, `set_column_descriptions`, etc.).

### Example

```python
result = ddag_build.audit_descriptions('.')
# result["review_packets"] has one entry per compute node
# Spawn one node-auditor agent per packet, collect results, present issues
```

For small DAGs (1-3 compute nodes), running auditors sequentially is fine. For larger DAGs, always run in parallel.

## DRY Scan

The DRY scan compares transform code across all compute nodes to find duplicated logic, repeated hardcoded values, and patterns that should be extracted into shared modules or `ddag_settings.py`.

### Procedure

1. **Dump all transforms to `.ddag_work/`** — never to the project root:

   ```bash
   mkdir -p .ddag_work
   python $CLI dump-function --node <node.ddag> --output .ddag_work/<node>.py $ROOT
   # repeat for each compute node
   ```

2. **Read the dumped files** and scan for:
   - Identical or near-identical code blocks copied across nodes
   - The same literal value (threshold, date, column name) hardcoded in multiple transforms
   - Boilerplate setup (imports, DB connections, path construction) repeated verbatim

   See `references/shared-code.md` § DRY Audit for what to flag and how to present it.

3. **Cleanup** — delete `.ddag_work/` contents immediately after presenting results (or if the scan is abandoned):

   ```bash
   rm -f .ddag_work/*.py
   ```

   `.ddag_work/` is a single-session scratch space shared with the External Code Editor. Never leave files there between sessions. If files from a previous session are found at the start of a DRY scan, delete them before proceeding.

## Templating Transform Code

When creating multiple nodes from a shared template (e.g., parallel analysis tracks that differ only in dataset name or chart title), **never use Python's `.format()` or f-strings** to interpolate values into transform function strings. Python dict literals and f-strings use `{` and `}` which collide with `.format()` delimiters, causing `KeyError` or broken string literals.

**Do this:** Use `str.replace()` with UPPER_CASE placeholder tokens that can't collide with Python syntax:

```python
template = '''def transform(sources, params, outputs):
    panel = pd.read_parquet(sources["PANEL_KEY"])
    ax.set_title("CHART_TITLE")
'''
fn = template.replace('PANEL_KEY', 'did_panel_activated').replace('CHART_TITLE', 'My Title')
```

**Don't do this:**
```python
# BROKEN — .format() interprets { in dict literals as format placeholders
template = '''results = {"att": round(float(att), 6)}'''
fn = template.format(panel_key='did_panel_activated')  # KeyError: '"att"'
```

## Error Recovery

Common errors and fixes:

- **Build fails with ImportError**: Install the missing package (`pip install polars`, etc.) and retry.
- **Build fails with transform error**: Fix the function with `ddag_core.set_function()`, then rebuild.
- **"database is locked" error**: Another process has the .ddag file open. Close it and retry.
- **Staleness detection seems wrong**: Run `status` to inspect timestamps — check `updated_at` vs `built_at`.
- **"Duplicate output path" error on build**: Two active nodes claim the same output. Deactivate one (see Branching).
- **Schema drift after rebuild**: Run `audit` to identify new/removed columns, then update descriptions at Checkpoint 2.
