# ddag Programmatic API Reference

Detailed signatures and examples for the Python API. For the complete function index, see the Quick Reference in SKILL.md. For CLI usage, see `references/cli.md`.

Most CLI commands have Python equivalents in `ddag_build` — use these when you need structured return values rather than printed output.

## Contents

- [Importing](#importing)
- [ddag_core — Node CRUD](#ddag_core--node-crud)
- [ddag_build — DAG Operations](#ddag_build--dag-operations)

## Importing

```python
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts')
import ddag_core
import ddag_build
```

## ddag_core — Node CRUD

```python
# Create a source node
ddag_core.create_source_node('data/visits.ddag',
    description='Raw visit logs from web analytics',
    output_paths=['data/visits.csv'])

# Create a compute node — transform_plan is required
ddag_core.create_compute_node('pipeline/clean.ddag',
    description='Filter visits to recent dates',
    source_paths=['data/visits.csv'],
    output_paths=['pipeline/clean_visits.parquet'],
    function_body=function_code,
    transform_plan='Read visits.csv, filter rows where date >= min_date, write to parquet.',
    params={'min_date': {'type': 'str', 'value': '2024-01-01', 'description': 'Cutoff date'}})

# Read node metadata — returns dict with keys:
#   description, is_active, branched_from, force_stale, sources (list of paths),
#   parameters (list of dicts), transform_function (str|None), transform_plan (str|None),
#   updated_at, outputs (list of {path, description, row_count, col_count, built_at}),
#   output_columns ({output_path: [{name, description}]}), is_source_node (bool)
meta = ddag_core.read_node('pipeline/clean.ddag')

# Read just the transform plan
plan = ddag_core.get_transform_plan('pipeline/clean.ddag')

# Update transform function — transform_plan is always required alongside
ddag_core.set_function('pipeline/clean.ddag', new_function_code, updated_plan)

# After build: update stats and descriptions
ddag_core.update_output_stats('pipeline/clean.ddag', 'pipeline/clean_visits.parquet', row_count=1000, col_count=5)
ddag_core.set_output_description('pipeline/clean.ddag', 'pipeline/clean_visits.parquet', 'Filtered visit records')

# Upsert column descriptions — merges with existing descriptions.
# Only the keys you pass are inserted or updated; existing columns not
# in the dict are left unchanged.
ddag_core.set_column_descriptions('pipeline/clean.ddag', 'pipeline/clean_visits.parquet', {
    'date': 'Visit date in YYYY-MM-DD',
    'user_id': 'Unique user identifier',
})

# Remove a source or output from a node
ddag_core.remove_source('pipeline/clean.ddag', 'data/old_input.csv')
ddag_core.remove_output('pipeline/clean.ddag', 'pipeline/old_output.parquet')

# Dump transform function to a .py file for external editing
out_file = ddag_core.dump_function('pipeline/clean.ddag')              # → _ddag_clean.py
out_file = ddag_core.dump_function('pipeline/clean.ddag', 'my_edit.py')  # custom path

# Load edited function back into node — transform_plan required
ddag_core.load_function('pipeline/clean.ddag', updated_plan)              # reads _ddag_clean.py
ddag_core.load_function('pipeline/clean.ddag', updated_plan, 'my_edit.py')  # custom path

# Get dicts suitable for passing to transform()
sources = ddag_core.get_sources_dict('pipeline/clean.ddag')   # {stem: path}
outputs = ddag_core.get_outputs_dict('pipeline/clean.ddag')   # {stem: path}
params = ddag_core.get_params_dict('pipeline/clean.ddag')     # {name: typed_value}

# Branching & activation — clone a node, deactivate the original, evolve the clone
ddag_core.clone_node('aggregate.ddag', 'aggregate_v2.ddag')  # sets branched_from on clone
ddag_core.deactivate_node('aggregate.ddag')                   # excluded from DAG
ddag_core.activate_node('aggregate.ddag')                     # re-included in DAG
ddag_core.is_active('aggregate.ddag')                         # → bool

# Force staleness — make a node rebuild regardless of timestamps
ddag_core.set_force_stale('pipeline/clean.ddag')   # unconditionally stale until cleared
ddag_core.clear_force_stale('pipeline/clean.ddag') # resume normal staleness rules
```

## ddag_build — DAG Operations

```python
# Scan nodes
nodes = ddag_build.scan_nodes('.')                              # active nodes only
nodes = ddag_build.scan_nodes('.', include_inactive=True)       # all nodes (active + inactive)
edges, output_to_node = ddag_build.build_dag(nodes)

# Conflict detection — check for two active nodes claiming the same output
conflicts = ddag_build.check_output_conflicts(nodes)  # → [(output_path, [node_paths])] or []

# Staleness
stale = ddag_build.find_stale_nodes('.')          # stale nodes in build order
all_compute = ddag_build.find_all_compute_nodes('.')  # all compute nodes in build order (for script --all)

# Build (preferred — handles conflicts, cycles, stats, and sample output in one call)
built = ddag_build.build_nodes('.', node_filter=None, sample_rows=5)  # → list of built node paths
built = ddag_build.build_nodes('.', node_filter='pipeline/clean.ddag')  # build single node (+ stale upstream)

# Build script generation (manual alternative to build_nodes)
script = ddag_build.generate_build_script(stale, nodes, '.')

# After manual build, update stats for all built nodes
for node_path in stale:
    ddag_build.update_output_stats_after_build(node_path, root_dir='.')

# Lineage traversal
ancestors = ddag_build.trace_lineage('pipeline/clean.ddag', edges, 'up')
descendants = ddag_build.trace_lineage('pipeline/clean.ddag', edges, 'down')

# File lookups
producer = ddag_build.find_node_for_file('data/visits.csv', nodes)
consumers = ddag_build.find_consumers('data/visits.csv', nodes)

# Connected components (disconnected subgraphs)
components = ddag_build.find_connected_components(edges)

# Diagram
mermaid_src = ddag_build.generate_mermaid(nodes, edges)
png_path = ddag_build.render_diagram('.', output_path='pipeline.png')

# Build script round-trip
parsed = ddag_build.parse_build_script('_ddag_build.py')  # → {node_path: function_body} (inspect without updating)
results = ddag_build.load_build_script('_ddag_build.py', '.', plans={'clean.ddag': updated_plan})  # → [(node_path, changed)]

# File context (full DAG context for a data file)
# Returns: {found, file_path, producer (node_path|None), producer_meta (read_node dict|None),
#   consumers ([node_paths]), consumer_metas ([read_node dicts]), lineage_up ([node_paths]),
#   lineage_down ([node_paths]), stale (bool|None)}
ctx = ddag_build.file_context('data/visits.csv', '.')

# Audit — returns structured drift + review packets for LLM consistency review
result = ddag_build.audit_descriptions('.')
# result["drift"]          — [{node, output, added, removed}]
# result["review_packets"] — [{node, description, inputs, transform, outputs}]
```
