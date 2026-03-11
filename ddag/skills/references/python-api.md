# Python API Reference

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
