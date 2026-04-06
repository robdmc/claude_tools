# ddag CLI Reference

All commands: `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py <command> --root .`

Run `--help` for full details on any command. Use the CLI for inspection and information gathering. For node mutations (create, modify, branch), use the Python API (`references/python-api.md`).

## Commands

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `status` | Show all nodes with type and staleness | `--include-inactive` |
| `stale` | List stale nodes in build order | `--json` |
| `script` | Generate Python build script for stale nodes | `--all` for all compute nodes |
| `build` | Build stale nodes, update stats, print sample rows | `--node <path>` for single node, `--json` |
| `audit` | Check descriptions: missing, schema drift, shared columns | `--node <path>`, `--json` |
| `summary` | JSON overview: node count, pipeline count, breakdown | `--include-inactive` |
| `show` | Full node metadata as JSON (read_node + dicts) | `--node <path>` (required) |
| `lineage` | Upstream/downstream lineage for a node | `--node <path>` (required) |
| `file-context` | Look up a data file across all nodes (JSON) | `--file <path>` (required) |
| `diagram` | Render Graphviz DAG diagram to PNG or .dot fallback | `-o <path>` |
| `dump-function` | Dump transform function to .py for external editing | `--node <path>` (required) |
| `load-function` | Load edited transform function back into node | `--node <path>` (required), `--plan <text>` (required) |
| `load-script` | *Disabled in CLI* — use Python API: `ddag_build.load_build_script(path, root, plans={...})` | |
| `clean` | Delete all compute node output files (interactive confirmation) | `--yes` / `-y` to skip prompt |

### Marimo Notebook Commands

Separate script: `uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_marimo.py`

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `ddag_marimo.py <ddag_path>` | Export node to Marimo notebook (`<stem>.ddag.nb.py`) | `--root <dir>` |
| `ddag_marimo.py <ddag_path> --import` | Import transform from notebook back into node | `--notebook <path>`, `--root <dir>` |

## JSON Output Schemas

### `show --node <path>`

Returns a flat JSON object (not wrapped in an array or keyed by name):

```json
{
  "description": "string",
  "is_active": true,
  "branched_from": null,
  "force_stale": false,
  "sources": [{"path": "input.parquet", "description": "..."}],
  "parameters": [{"name": "min_date", "value": "2023-01-01", "description": "..."}],
  "transform_function": "string (Python code)",
  "transform_plan": "string",
  "updated_at": "ISO timestamp",
  "outputs": [
    {"path": "output.parquet", "description": "...", "row_count": 1000, "col_count": 5, "built_at": "ISO timestamp"}
  ],
  "output_columns": {
    "output.parquet": [{"name": "col_name", "description": "..."}]
  },
  "is_source_node": false,
  "sources_dict": {"input": "input.parquet"},
  "outputs_dict": {"output": "output.parquet"},
  "params_dict": {"min_date": "2023-01-01"}
}
```

Key details:
- **No `name` key** at top level — the node name is the filename you passed in
- **`outputs_dict`** values are **plain path strings**, not nested objects
- **`sources_dict`** and **`params_dict`** are also `{stem: string}` mappings
- **`outputs`** is a list of objects with `path`, `description`, `row_count`, `col_count`, `built_at`
- `row_count`/`col_count`/`built_at` are `null` for nodes that haven't been built yet

### `summary`

```json
{
  "node_count": 16,
  "pipeline_count": 1,
  "cycle": null,
  "pipelines": [
    {
      "nodes": ["a.ddag", "b.ddag"],
      "source_count": 2,
      "compute_count": 4,
      "stale_count": 3,
      "stale_nodes": ["b.ddag"],
      "descriptions": {"a.ddag": "...", "b.ddag": "..."},
      "outputs": {"a.ddag": ["input.parquet"], "b.ddag": ["output.parquet", "report.csv"]},
      "types": {"a.ddag": "source", "b.ddag": "compute"}
    }
  ],
  "inactive_count": 0,
  "inactive_nodes": {}
}
```

- `outputs` maps each node to an **array of output file paths** (relative to root)
- `types` maps each node to `"source"` or `"compute"`
- `inactive_count` and `inactive_nodes` only appear with `--include-inactive`

### `stale --json`

Returns a JSON **array of node path strings** in build order:

```json
["upstream.ddag", "downstream.ddag"]
```

### `build --json`

Success:

```json
{"built": ["upstream.ddag", "downstream.ddag"], "count": 2}
```

Error:

```json
{"error": "error message string"}
```

- `built` is an array of node paths in the order they were built
- On error, exits with code 1

### `audit --json`

```json
{
  "drift": [{"node": "...", "output": "...", "added": [...], "removed": [...]}],
  "review_packets": [
    {
      "node": "node.ddag",
      "description": "...",
      "inputs": [{"path": "...", "columns": [...]}],
      "transform": "Python code string",
      "transform_plan": "plan string",
      "parameters": [...],
      "outputs": [{"path": "...", "description": "...", "columns": [...]}],
      "drift": []
    }
  ]
}
```

### `file-context --file <path>`

```json
{
  "found": true,
  "file_path": "visits.parquet",
  "producer": "visits.ddag",
  "producer_meta": {
    "description": "...",
    "is_source_node": false,
    "sources": [...],
    "outputs": [{"path": "...", "description": "...", "row_count": null, "col_count": null}],
    "output_columns": {"visits.parquet": [{"name": "...", "description": "..."}]},
    "parameters": []
  },
  "consumers": ["downstream.ddag"],
  "consumer_metas": [{"description": "...", "sources": [...]}]
}
```

When not found: `{"found": false, ...}`

### `lineage --node <path>`

Outputs **human-readable text** (not JSON):

```
Upstream lineage for node.ddag:
  source.ddag
  node.ddag <-- target

Downstream lineage for node.ddag:
  node.ddag <-- target
  consumer.ddag
```

## Examples

```bash
# Build everything stale
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py build --root .

# Build a single node (with upstream if needed)
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .

# Dump → edit → load → build cycle
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py dump-function --node path/to/node.ddag --root .
# ... user edits _ddag_{stem}.py ...
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py load-function --node path/to/node.ddag --plan "Updated plan describing the new logic" --root .
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .
```

```bash
# Delete all compute outputs (prompts for confirmation)
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py clean --root .
```

```bash
# Export a node to a Marimo notebook for interactive editing
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_marimo.py path/to/node.ddag --root .
# ... user runs: marimo edit node.ddag.nb.py ...
# Import changes back
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_marimo.py path/to/node.ddag --import --root .
# Build the updated node
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/ddag_build.py build --node path/to/node.ddag --root .
```

If any CLI command fails (non-zero exit or traceback), show the error to the user and investigate before continuing.
