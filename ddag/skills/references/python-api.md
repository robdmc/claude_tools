# Python API Reference

All Python API calls must run via uv: `uv run --project {SKILL_DIR}/scripts python -c "..."`

```python
import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); import ddag_core; import ddag_build

# --- ddag_core: Node CRUD ---

# Creation
ddag_core.create_compute_node(ddag_path, description, source_paths, output_paths, function_body, transform_plan, params=None)
ddag_core.create_source_node(ddag_path, description, output_paths)
# Example — use keyword args exactly as named above (ddag_path, not path):
# ddag_core.create_compute_node(
#     ddag_path='my_node.ddag',
#     description='What this node does',
#     source_paths=['input.parquet'],
#     output_paths=['output.parquet'],
#     function_body='def transform(sources, params, outputs):\n    ...',  # MUST start with def transform(...)
#     transform_plan='...',
#     params={                          # optional; each entry: {type, default, value, description}
#         'min_date': {'type': 'str', 'default': '2023-01-01', 'value': '2023-01-01', 'description': 'Earliest date to include'},
#     },
# )
# WARNING: uses ON CONFLICT DO NOTHING on sources/outputs — re-calling does NOT remove old entries.
# To remove a source or output, call remove_source() / remove_output() explicitly.

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
ddag_core.set_description(ddag_path, description)                 # update the node-level description
ddag_core.set_function(ddag_path, function_body, transform_plan)  # function_body MUST start with def transform(...); validated at build time not here
ddag_core.set_transform_plan(ddag_path, transform_plan)           # plan-only update; does NOT bump updated_at, so does NOT invalidate a prior build. Use when fixing wording/typos without a code change
ddag_core.update_output_stats(ddag_path, output_path, row_count, col_count)
ddag_core.set_output_description(ddag_path, output_path, description)
ddag_core.set_column_descriptions(ddag_path, output_path, col_descriptions, replace=False)  # col_descriptions = {'col_name': 'description', ...}; replace=True deletes all existing columns first
ddag_core.remove_column_description(ddag_path, output_path, name)  # name = str or list of strs; no-ops for names not present
ddag_core.set_parameter(ddag_path, name, *, type=None, default=None, value=None, description=None)  # upsert one param; unset fields preserved on existing params, default to NULL (type → 'str') for new
ddag_core.remove_parameter(ddag_path, name)                       # name = str or list of strs; no-ops for names not present
ddag_core.remove_source(ddag_path, source_path)
ddag_core.rename_source(ddag_path, old_path, new_path)            # raises if new_path already declared on this node
ddag_core.remove_output(ddag_path, output_path)
ddag_core.rename_output(ddag_path, old_path, new_path)            # preserves description, row_count, col_count, built_at, and column descriptions; raises if new_path already declared

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
