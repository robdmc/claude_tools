"""ddag_build.py — DAG assembly, staleness detection, and build execution."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ddag_core


def scan_nodes(root_dir=".", include_inactive=False):
    """Find all .ddag files under root_dir and return {path: node_metadata}.

    By default, only active nodes are returned. Set include_inactive=True to get all.
    """
    root = Path(root_dir)
    nodes = {}
    for ddag_file in root.rglob("*.ddag"):
        if not ddag_file.is_file():
            continue
        rel = str(ddag_file.relative_to(root))
        meta = ddag_core.read_node(str(ddag_file))
        if include_inactive or meta.get("is_active", True):
            nodes[rel] = meta
    return nodes


def build_dag(nodes):
    """Build DAG edges by matching source paths to output paths.

    Returns:
        edges: dict mapping node_path -> list of upstream node_paths
        output_to_node: dict mapping output_path -> node_path
    """
    # Map each output path to its producing node
    output_to_node = {}
    for node_path, meta in nodes.items():
        for out in meta["outputs"]:
            output_to_node[out["path"]] = node_path

    # Build edges: for each node, find which nodes produce its sources
    edges = {node_path: [] for node_path in nodes}
    for node_path, meta in nodes.items():
        for src_path in meta["sources"]:
            upstream = output_to_node.get(src_path)
            if upstream:
                edges[node_path].append(upstream)

    return edges, output_to_node


def check_output_conflicts(nodes):
    """Check for multiple active nodes claiming the same output path.

    Returns list of (output_path, [node_paths]) for conflicts, or empty list.
    """
    output_owners = {}
    for node_path, meta in nodes.items():
        for out in meta["outputs"]:
            output_owners.setdefault(out["path"], []).append(node_path)
    return [(path, owners) for path, owners in output_owners.items() if len(owners) > 1]


def detect_cycle(edges):
    """Detect cycles using DFS. Returns list of nodes in cycle, or None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in edges}
    parent = {}

    def dfs(node):
        color[node] = GRAY
        for dep in edges.get(node, []):
            if color[dep] == GRAY:
                # Reconstruct cycle
                cycle = [dep, node]
                cur = node
                while cur != dep:
                    cur = parent.get(cur)
                    if cur is None:
                        break
                    cycle.append(cur)
                return cycle
            if color[dep] == WHITE:
                parent[dep] = node
                result = dfs(dep)
                if result:
                    return result
        color[node] = BLACK
        return None

    for node in edges:
        if color[node] == WHITE:
            result = dfs(node)
            if result:
                return result
    return None


def topological_sort(edges):
    """Return nodes in build order (dependencies first)."""
    # Build reverse adjacency: node -> list of nodes that depend on it
    dependents = {n: [] for n in edges}
    in_degree = {n: 0 for n in edges}
    for node, deps in edges.items():
        for dep in deps:
            if dep not in dependents:
                dependents[dep] = []
            if dep not in in_degree:
                in_degree[dep] = 0
            dependents[dep].append(node)
        in_degree[node] = len(deps)

    queue = [n for n, d in in_degree.items() if d == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for dependent in dependents.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    return order


def _parse_iso(ts):
    """Parse ISO 8601 timestamp string to datetime."""
    if ts is None:
        return None
    return datetime.fromisoformat(ts)


def _get_local_module_paths(function_body, root_dir="."):
    """Extract local module file paths from a transform's import statements.

    Parses the function body with ast to find import/from-import statements,
    then checks if they resolve to .py files under root_dir.

    Returns list of Path objects for local modules the transform depends on.
    """
    import ast
    if not function_body:
        return []
    try:
        tree = ast.parse(function_body)
    except SyntaxError:
        return []
    root = Path(root_dir).resolve()
    module_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_names.add(node.module.split(".")[0])
    paths = []
    for name in module_names:
        # Check for single-file module
        candidate = root / f"{name}.py"
        if candidate.exists():
            paths.append(candidate)
            continue
        # Check for package
        candidate = root / name / "__init__.py"
        if candidate.exists():
            paths.append(candidate)
    return paths


def is_stale(node_path, nodes, edges, root_dir="."):
    """Check if a node needs rebuilding.

    A node is stale if:
    - force_stale flag is set (any node type)
    - It has no built_at on any output
    - Its transform_function.updated_at > any output.built_at
    - Any local module it imports has been modified since last build
    - Any upstream node's output.built_at > this node's output.built_at
    - It is a sourceless compute node and was last built before today
    """
    meta = nodes[node_path]

    # Any node: force_stale overrides everything
    if meta.get("force_stale"):
        return True

    # Source nodes are never stale (they're externally managed)
    if meta["is_source_node"]:
        return False

    # Missing output file means stale
    if any(not Path(o["path"]).exists() for o in meta["outputs"]):
        return True

    # Get this node's earliest built_at
    built_times = [_parse_iso(o["built_at"]) for o in meta["outputs"]]
    if not built_times or any(t is None for t in built_times):
        return True  # Never built
    earliest_built = min(t for t in built_times if t is not None)

    # Check if function was updated after build
    fn_updated = _parse_iso(meta["updated_at"])
    if fn_updated and fn_updated > earliest_built:
        return True

    # Check if any local module dependency was modified after build
    module_paths = _get_local_module_paths(meta["transform_function"], root_dir=root_dir)
    for mod_path in module_paths:
        mod_mtime = datetime.fromtimestamp(mod_path.stat().st_mtime).astimezone()
        earliest_aware = earliest_built if earliest_built.tzinfo else earliest_built.astimezone()
        if mod_mtime > earliest_aware:
            return True

    # Sourceless compute nodes: stale if built before today
    if not meta["sources"] and not edges.get(node_path, []):
        today = datetime.now().date()
        if earliest_built.date() < today:
            return True

    # Check upstream: if upstream is stale, this node is too
    for upstream_path in edges.get(node_path, []):
        upstream_meta = nodes[upstream_path]
        if is_stale(upstream_path, nodes, edges, root_dir=root_dir):
            return True
        for out in upstream_meta["outputs"]:
            upstream_built = _parse_iso(out["built_at"])
            if upstream_built and upstream_built > earliest_built:
                return True

    return False


def find_stale_nodes(root_dir="."):
    """Scan all nodes and return list of stale node paths in build order."""
    nodes = scan_nodes(root_dir)
    edges, _ = build_dag(nodes)

    cycle = detect_cycle(edges)
    if cycle:
        raise ValueError(f"Cycle detected in DAG: {' -> '.join(cycle)}")

    order = topological_sort(edges)
    return [n for n in order if is_stale(n, nodes, edges, root_dir=root_dir)]


def find_all_compute_nodes(root_dir="."):
    """Return all compute node paths in topological (build) order."""
    nodes = scan_nodes(root_dir)
    edges, _ = build_dag(nodes)

    cycle = detect_cycle(edges)
    if cycle:
        raise ValueError(f"Cycle detected in DAG: {' -> '.join(cycle)}")

    order = topological_sort(edges)
    return [n for n in order if not nodes[n]["is_source_node"]]


def _node_fn_name(node_path):
    """Derive a unique function name from a node path, e.g. 'clean_visits.ddag' -> 'transform_clean_visits'."""
    stem = Path(node_path).stem  # strip .ddag
    # Replace non-alphanumeric chars with underscores
    import re
    safe = re.sub(r'[^a-zA-Z0-9]', '_', stem).strip('_')
    return f"transform_{safe}"


def generate_build_script(stale_nodes, nodes, root_dir="."):
    """Generate a Python script that executes all stale transforms in order.

    Functions are defined in topological (DAG) order so dependencies appear
    before dependents.  All execution is collected in a main() function at
    the bottom.

    Returns the script content as a string.
    """
    root = Path(root_dir).resolve()
    header = [
        "#!/usr/bin/env python3",
        '"""Auto-generated ddag build script."""',
        "import sys, os",
        f"os.chdir({str(root)!r})",
        f"sys.path.insert(0, {str(root)!r})",
        "",
    ]

    fn_defs = []    # function definition blocks
    main_calls = [] # lines inside main()

    for node_path in stale_nodes:
        meta = nodes[node_path]
        if meta["is_source_node"]:
            continue

        fn_body = meta["transform_function"]
        if not fn_body or not fn_body.strip().startswith("def transform("):
            raise ValueError(
                f"Node {node_path}: function_body must define 'def transform(...)'. "
                f"Got: {(fn_body or '')[:80]!r}"
            )

        fn_name = _node_fn_name(node_path)
        # Rename 'def transform(' to 'def transform_<stem>('
        renamed_body = fn_body.replace("def transform(", f"def {fn_name}(", 1)

        sources = ddag_core.get_sources_dict(str(Path(root_dir) / node_path))
        outputs = ddag_core.get_outputs_dict(str(Path(root_dir) / node_path))
        params = ddag_core.get_params_dict(str(Path(root_dir) / node_path))

        fn_defs.append(f"# --- Node: {node_path} ---")
        fn_defs.append(renamed_body)
        fn_defs.append("")

        main_calls.append(f"    {fn_name}(sources={sources!r}, params={params!r}, outputs={outputs!r})")
        main_calls.append(f"    print('Built: {node_path}')")

    # Assemble: header, function defs, main(), guard
    lines = header + fn_defs
    lines.append("")
    lines.append("def main():")
    if main_calls:
        lines.extend(main_calls)
    else:
        lines.append("    pass")
    lines.append("")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    main()")
    lines.append("")

    return "\n".join(lines)


def parse_build_script(script_path):
    """Parse a build script back into {node_path: function_body} pairs.

    Splits on '# --- Node: ... ---' markers and extracts function bodies.
    The function names are transform_<stem> in the generated script; this
    parser renames them back to 'def transform(' for storage in .ddag nodes.
    """
    text = Path(script_path).read_text()
    import re
    # Split into sections by node marker
    sections = re.split(r'^# --- Node: (.+?) ---\s*$', text, flags=re.MULTILINE)
    # sections[0] is the preamble, then alternating (node_path, section_body)
    result = {}
    for i in range(1, len(sections), 2):
        node_path = sections[i]
        body = sections[i + 1]
        fn_name = _node_fn_name(node_path)
        # Extract function body: stop at main() or end of section
        fn_lines = []
        for line in body.split("\n"):
            if line.startswith("def main()"):
                break
            fn_lines.append(line)
        # Strip leading/trailing blank lines
        fn_body = "\n".join(fn_lines).strip()
        # Rename back to 'def transform('
        if fn_body:
            fn_body = fn_body.replace(f"def {fn_name}(", "def transform(", 1)
            result[node_path] = fn_body
    return result


def load_build_script(script_path, root_dir=".", plans=None):
    """Load edited functions from a build script back into their nodes.

    plans: dict mapping node_path to updated transform_plan text (required for changed nodes).
    Returns list of (node_path, changed: bool) tuples.
    """
    plans = plans or {}
    parsed = parse_build_script(script_path)
    results = []
    for node_path, new_body in parsed.items():
        full_path = str(Path(root_dir) / node_path)
        meta = ddag_core.read_node(full_path)
        old_body = (meta["transform_function"] or "").strip()
        changed = new_body != old_body
        if changed:
            plan = plans.get(node_path)
            if not plan:
                raise ValueError(
                    f"transform_plan required for changed node {node_path} — "
                    f"pass plans={{'{node_path}': '...'}}"
                )
            ddag_core.set_function(full_path, new_body, plan)
        results.append((node_path, changed))
    return results


def update_output_stats_after_build(node_path, root_dir="."):
    """After building a node, update row/col counts from actual output files."""
    full_path = str(Path(root_dir) / node_path)
    meta = ddag_core.read_node(full_path)

    for out in meta["outputs"]:
        out_file = Path(root_dir) / out["path"]
        if not out_file.exists():
            continue

        row_count, col_count = None, None
        suffix = out_file.suffix.lower()

        if suffix == ".parquet":
            try:
                import polars as pl
                df = pl.scan_parquet(str(out_file))
                schema = df.collect_schema()
                col_count = len(schema)
                row_count = df.select(pl.len()).collect().item()
            except ImportError:
                try:
                    import pandas as pd
                    df = pd.read_parquet(str(out_file))
                    row_count, col_count = df.shape
                except ImportError:
                    pass
        elif suffix == ".csv":
            try:
                import polars as pl
                df = pl.scan_csv(str(out_file))
                schema = df.collect_schema()
                col_count = len(schema)
                row_count = df.select(pl.len()).collect().item()
            except ImportError:
                try:
                    import pandas as pd
                    df = pd.read_csv(str(out_file))
                    row_count, col_count = df.shape
                except ImportError:
                    pass

        ddag_core.update_output_stats(full_path, out["path"], row_count, col_count)


def build_nodes(root_dir=".", node_filter=None, sample_rows=5, quiet=False):
    """Build stale nodes and print sample output.

    Args:
        root_dir: Project root directory.
        node_filter: Optional single node path to build (just that node).
        sample_rows: Number of rows to print per output (0 to skip). Default 5.
        quiet: Suppress all stdout output (for JSON mode). Default False.

    Returns list of built node paths.
    """
    nodes = scan_nodes(root_dir)
    if not nodes:
        if not quiet:
            print("No active nodes found.")
        return []

    conflicts = check_output_conflicts(nodes)
    if conflicts:
        if not quiet:
            for path, owners in conflicts:
                print(f"CONFLICT: {path} claimed by: {', '.join(owners)}")
        raise ValueError("Resolve output conflicts before building.")

    edges, _ = build_dag(nodes)
    cycle = detect_cycle(edges)
    if cycle:
        raise ValueError(f"Cycle detected: {' -> '.join(cycle)}")

    stale = [n for n in topological_sort(edges) if is_stale(n, nodes, edges, root_dir=root_dir)]

    if node_filter:
        if node_filter not in nodes:
            raise ValueError(f"Node not found (or inactive): {node_filter}")
        # Build only this node, but verify upstream is fresh
        upstream_stale = [n for n in stale if n != node_filter and n in
                          set(_all_upstream(node_filter, edges))]
        if upstream_stale:
            if not quiet:
                print(f"Upstream stale: {', '.join(upstream_stale)} — building them first.")
            stale = upstream_stale + ([node_filter] if node_filter in stale or upstream_stale else [node_filter])
        elif node_filter in stale:
            stale = [node_filter]
        else:
            if not quiet:
                print(f"{node_filter} is up to date.")
            return []

    if not stale:
        if not quiet:
            print("Nothing to build.")
        return []

    # Generate and execute
    script = generate_build_script(stale, nodes, root_dir)
    ns = {"__name__": "__main__"}
    exec(compile(script, "<ddag_build>", "exec"), ns)

    # Update stats and sample
    root = Path(root_dir)
    for node_path in stale:
        update_output_stats_after_build(node_path, root_dir)
        if sample_rows > 0 and not quiet:
            meta = ddag_core.read_node(str(root / node_path))
            for out in meta["outputs"]:
                _print_sample(str(root / out["path"]), sample_rows, node_path, out["path"])

    return stale


def _all_upstream(node_path, edges):
    """Collect all transitive upstream nodes."""
    visited = set()
    def walk(n):
        for dep in edges.get(n, []):
            if dep not in visited:
                visited.add(dep)
                walk(dep)
    walk(node_path)
    return visited


def _print_sample(file_path, n, node_path, output_path):
    """Print first n rows of a CSV or Parquet file."""
    p = Path(file_path)
    if not p.exists():
        return
    suffix = p.suffix.lower()
    try:
        if suffix == ".parquet":
            try:
                import polars as pl
                df = pl.read_parquet(file_path, n_rows=n)
            except ImportError:
                import pandas as pd
                df = pd.read_parquet(file_path).head(n)
        elif suffix == ".csv":
            try:
                import polars as pl
                df = pl.read_csv(file_path, n_rows=n)
            except ImportError:
                import pandas as pd
                df = pd.read_csv(file_path, nrows=n)
        else:
            return
        print(f"\n── {output_path} (from {node_path}) ──")
        print(df)
    except Exception as e:
        print(f"  (could not sample {output_path}: {e})")


def trace_lineage(node_path, edges, direction="up"):
    """Trace lineage for a node. direction='up' for ancestors, 'down' for descendants.
    Returns list of node paths in dependency order."""
    if direction == "up":
        # Walk upstream
        visited = set()
        result = []
        def walk(n):
            if n in visited:
                return
            visited.add(n)
            for upstream in edges.get(n, []):
                walk(upstream)
            result.append(n)
        walk(node_path)
        return result
    else:
        # Walk downstream — need reverse edges
        reverse = {n: [] for n in edges}
        for n, deps in edges.items():
            for dep in deps:
                reverse.setdefault(dep, []).append(n)
        visited = set()
        result = []
        def walk(n):
            if n in visited:
                return
            visited.add(n)
            result.append(n)
            for downstream in reverse.get(n, []):
                walk(downstream)
        walk(node_path)
        return result


def find_node_for_file(file_path, nodes):
    """Find which node produces a given output file path."""
    for node_path, meta in nodes.items():
        for out in meta["outputs"]:
            if out["path"] == file_path:
                return node_path
    return None


def find_consumers(file_path, nodes):
    """Find which nodes consume a given file as a source."""
    consumers = []
    for node_path, meta in nodes.items():
        if file_path in meta["sources"]:
            consumers.append(node_path)
    return consumers


def find_connected_components(edges):
    """Find disconnected subgraphs in the DAG.

    Returns list of sets, each set containing the node paths in one connected component.
    Treats edges as undirected for connectivity purposes.
    """
    # Build undirected adjacency
    adj = {n: set() for n in edges}
    for node, deps in edges.items():
        for dep in deps:
            adj.setdefault(node, set()).add(dep)
            adj.setdefault(dep, set()).add(node)

    visited = set()
    components = []

    for node in adj:
        if node in visited:
            continue
        component = set()
        queue = [node]
        while queue:
            n = queue.pop()
            if n in visited:
                continue
            visited.add(n)
            component.add(n)
            for neighbor in adj.get(n, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    return components


def file_context(file_path, root_dir="."):
    """Look up a data file across all nodes. Returns a dict describing its role in the DAG.

    Returns:
        {
            "found": bool,
            "file_path": str,
            "producer": str | None,         # node that outputs this file
            "producer_meta": dict | None,    # full metadata of producer node
            "consumers": [str],              # nodes that use this file as a source
            "consumer_metas": [dict],        # metadata for each consumer
            "lineage_up": [str],             # ancestor nodes (if producer exists)
            "lineage_down": [str],           # descendant nodes (from all consumers)
            "stale": bool | None,            # whether producer is stale
        }
    """
    nodes = scan_nodes(root_dir)
    if not nodes:
        return {"found": False, "file_path": file_path}

    edges, _ = build_dag(nodes)

    producer = find_node_for_file(file_path, nodes)
    consumers = find_consumers(file_path, nodes)

    if not producer and not consumers:
        return {"found": False, "file_path": file_path}

    result = {
        "found": True,
        "file_path": file_path,
        "producer": producer,
        "producer_meta": nodes[producer] if producer else None,
        "consumers": consumers,
        "consumer_metas": [nodes[c] for c in consumers],
        "lineage_up": trace_lineage(producer, edges, "up") if producer else [],
        "lineage_down": [],
        "stale": is_stale(producer, nodes, edges, root_dir=root_dir) if producer else None,
    }

    # Collect downstream from all consumers
    seen = set()
    for c in consumers:
        for n in trace_lineage(c, edges, "down"):
            if n not in seen:
                seen.add(n)
                result["lineage_down"].append(n)

    return result


def audit_descriptions(root_dir="."):
    """Audit schema drift and build per-node review packets for LLM consistency review.

    Returns a dict with:
        drift:   [{node, output, added, removed}] — columns in actual files not matching .ddag descriptions
        review_packets: [{node, description, inputs, transform, outputs}] — per-node context for LLM review
    """
    nodes = scan_nodes(root_dir)
    if not nodes:
        return {"drift": [], "review_packets": []}

    edges, _ = build_dag(nodes)
    root = Path(root_dir)
    drift = []
    review_packets = []

    for node_path, meta in nodes.items():
        node_drift = []
        for out in meta["outputs"]:
            opath = out["path"]
            described_cols = meta.get("output_columns", {}).get(opath, [])
            actual_cols = _read_actual_columns(str(root / opath))
            if actual_cols is not None and described_cols:
                described_names = {c["name"] for c in described_cols}
                added = actual_cols - described_names
                removed = described_names - actual_cols
                if added or removed:
                    entry = {
                        "node": node_path, "output": opath,
                        "added": sorted(added), "removed": sorted(removed),
                    }
                    drift.append(entry)
                    node_drift.append(entry)

        if not meta["is_source_node"]:
            packet = _build_review_packet(node_path, meta, nodes, edges)
            packet["drift"] = node_drift
            review_packets.append(packet)

    return {"drift": drift, "review_packets": review_packets}


def audit_node(node_path, root_dir="."):
    """Audit a single node for schema drift and build its review packet.

    Returns the same structure as audit_descriptions() but scoped to one node:
        drift:   [{node, output, added, removed}]
        review_packets: [{node, description, inputs, transform, transform_plan, parameters, outputs, drift}]
    """
    nodes = scan_nodes(root_dir)
    if node_path not in nodes:
        raise ValueError(f"Node not found: {node_path}")

    edges, _ = build_dag(nodes)
    root = Path(root_dir)
    meta = nodes[node_path]

    drift = []
    for out in meta["outputs"]:
        opath = out["path"]
        described_cols = meta.get("output_columns", {}).get(opath, [])
        actual_cols = _read_actual_columns(str(root / opath))
        if actual_cols is not None and described_cols:
            described_names = {c["name"] for c in described_cols}
            added = actual_cols - described_names
            removed = described_names - actual_cols
            if added or removed:
                drift.append({
                    "node": node_path, "output": opath,
                    "added": sorted(added), "removed": sorted(removed),
                })

    review_packets = []
    if not meta["is_source_node"]:
        packet = _build_review_packet(node_path, meta, nodes, edges)
        packet["drift"] = drift
        review_packets.append(packet)

    return {"drift": drift, "review_packets": review_packets}


def _build_review_packet(node_path, meta, nodes, edges):
    """Assemble per-node context for LLM consistency review.

    Gathers: input file descriptions + column descriptions (from upstream producers),
    the node's own description and transform code, and output descriptions + column descriptions.
    """
    # Collect input context from upstream producers
    inputs = []
    for source_path in meta["sources"]:
        input_info = {"path": source_path, "description": None, "columns": []}
        # Find which upstream node produces this source
        for up_path in edges.get(node_path, []):
            up_meta = nodes[up_path]
            for out in up_meta["outputs"]:
                if out["path"] == source_path:
                    input_info["description"] = out.get("description")
                    input_info["columns"] = up_meta.get("output_columns", {}).get(source_path, [])
                    break
        inputs.append(input_info)

    # Collect output context
    outputs = []
    for out in meta["outputs"]:
        outputs.append({
            "path": out["path"],
            "description": out.get("description"),
            "columns": meta.get("output_columns", {}).get(out["path"], []),
        })

    # Include project settings if the transform references them
    project_settings = None
    transform_code = meta.get("transform_function") or ""
    if "ddag_settings" in transform_code:
        # Walk up from the node to find ddag_settings.py
        node_dir = Path(node_path).parent
        for candidate in [node_dir, Path(".")]:
            settings_path = candidate / "ddag_settings.py"
            if settings_path.exists():
                project_settings = settings_path.read_text()
                break

    return {
        "node": node_path,
        "description": meta.get("description"),
        "inputs": inputs,
        "transform": meta.get("transform_function"),
        "transform_plan": meta.get("transform_plan"),
        "parameters": meta.get("parameters", []),
        "project_settings": project_settings,
        "outputs": outputs,
    }


def _read_actual_columns(file_path):
    """Read column names from a CSV or Parquet file. Returns set or None."""
    p = Path(file_path)
    if not p.exists():
        return None
    suffix = p.suffix.lower()
    try:
        if suffix == ".parquet":
            try:
                import polars as pl
                return set(pl.read_parquet_schema(file_path))
            except ImportError:
                import pandas as pd
                return set(pd.read_parquet(file_path, nrows=0).columns)
        elif suffix == ".csv":
            try:
                import polars as pl
                return set(pl.scan_csv(file_path).collect_schema().names())
            except ImportError:
                import pandas as pd
                return set(pd.read_csv(file_path, nrows=0).columns)
    except Exception:
        pass
    return None



def generate_dot(nodes, edges):
    """Generate Graphviz DOT source for the DAG."""
    lines = [
        "digraph ddag {",
        "    rankdir=LR;",
        '    node [fontname="Helvetica", fontsize=10];',
        '    edge [color="#666666"];',
    ]
    node_ids = {}
    for i, node_path in enumerate(nodes):
        nid = f"n{i}"
        node_ids[node_path] = nid
        label = Path(node_path).stem
        if nodes[node_path]["is_source_node"]:
            lines.append(f'    {nid} [label="{label}", shape=cylinder, style=filled, fillcolor="#e8f4f8"];')
        else:
            lines.append(f'    {nid} [label="{label}", shape=box, style="filled,rounded", fillcolor="#f0f0f0"];')
    for node_path, deps in edges.items():
        for dep in deps:
            lines.append(f"    {node_ids[dep]} -> {node_ids[node_path]};")
    lines.append("}")
    return "\n".join(lines)


def render_diagram(root_dir=".", output_path=None):
    """Generate a Graphviz DAG diagram and render to PNG via dot.

    Returns the output PNG path.
    """
    import subprocess, tempfile
    nodes = scan_nodes(root_dir)
    if not nodes:
        print("No .ddag nodes found.")
        return None
    edges, _ = build_dag(nodes)
    dot_content = generate_dot(nodes, edges)

    if output_path is None:
        output_path = str(Path(root_dir) / "_ddag_diagram.png")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as f:
        f.write(dot_content)
        dot_path = f.name

    # Determine output format from extension
    ext = Path(output_path).suffix.lstrip(".").lower()
    fmt = ext if ext in ("png", "svg", "pdf") else "png"

    try:
        subprocess.run(
            ["dot", f"-T{fmt}", dot_path, "-o", output_path],
            check=True, capture_output=True, text=True,
        )
        print(f"Diagram saved to {output_path}")
        return output_path
    except FileNotFoundError:
        print("Error: dot (Graphviz) not found. Install with: brew install graphviz")
        # Still save the .dot source as fallback
        dot_out = str(Path(output_path).with_suffix(".dot"))
        Path(dot_out).write_text(dot_content)
        print(f"DOT source saved to {dot_out}")
        return dot_out
    finally:
        Path(dot_path).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    import argparse
    parser = argparse.ArgumentParser(
        description="ddag DAG build system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
commands:
  status        List all nodes with type (source/compute) and staleness
  stale         List only stale nodes in build order
  script        Generate Python build script for stale nodes
  build         Build stale nodes and print sample output (--node for single node)
  audit         Check description coverage, schema drift, and cross-node consistency
  lineage       Show upstream/downstream lineage for a node (requires --node)
  diagram       Render Graphviz DAG diagram to PNG (requires dot) or .dot fallback
  file-context  Look up a data file across all nodes as JSON (requires --file)
  summary       JSON overview: node count, pipeline count, per-pipeline breakdown
  dump-function Dump a node's transform function to a .py file (requires --node)
  load-function Load a transform function from a .py file back into a node (requires --node)
  load-script   Parse an edited build script and update changed functions back into nodes
  clean         Delete all compute node output files (leaves source outputs untouched)

examples:
  %(prog)s status --root .
  %(prog)s stale --root .
  %(prog)s script --root . > _ddag_build.py
  %(prog)s build --root .
  %(prog)s build --node pipeline/clean.ddag --root .
  %(prog)s show --node pipeline/clean.ddag --root .
  %(prog)s audit --root .
  %(prog)s lineage --node pipeline/clean.ddag --root .
  %(prog)s diagram --root . -o pipeline.png
  %(prog)s file-context --file data/sales.csv --root .
  %(prog)s summary --root .
  %(prog)s dump-function --node pipeline/clean.ddag --root .
  %(prog)s load-function --node pipeline/clean.ddag --root .
  %(prog)s load-script --file _ddag_build.py --root .""",
    )
    parser.add_argument("command", choices=["status", "stale", "script", "build", "audit", "lineage", "diagram", "file-context", "summary", "show", "dump-function", "load-function", "load-script", "clean"])
    parser.add_argument("--root", default=".", help="Project root directory (default: .)")
    parser.add_argument("--node", help="Node .ddag path, relative to root (for lineage, show, build)")
    parser.add_argument("--file", help="Data file path, relative to root (for file-context)")
    parser.add_argument("--output", "-o", help="Output file path (for diagram, default: _ddag_diagram.png)")
    parser.add_argument("--all", action="store_true", help="Include all compute nodes, not just stale (for script)")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts (for clean)")
    parser.add_argument("--plan", help="Transform plan text (for load-function)")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive nodes (for status, summary)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON (for stale, build, audit)")
    args = parser.parse_args()

    if args.command == "status":
        nodes = scan_nodes(args.root)
        edges, _ = build_dag(nodes)
        cycle = detect_cycle(edges)
        if cycle:
            print(f"CYCLE: {' -> '.join(cycle)}")
            sys.exit(1)
        order = topological_sort(edges)
        for n in order:
            stale_flag = " [STALE]" if is_stale(n, nodes, edges, root_dir=args.root) else ""
            node_type = "source" if nodes[n]["is_source_node"] else "compute"
            print(f"  {n} ({node_type}){stale_flag}")
        if args.include_inactive:
            inactive = scan_nodes(args.root, include_inactive=True)
            inactive_only = {k: v for k, v in inactive.items() if not v.get("is_active", True)}
            for n, meta in inactive_only.items():
                node_type = "source" if meta["is_source_node"] else "compute"
                print(f"  {n} ({node_type}) [INACTIVE]")

    elif args.command == "stale":
        try:
            stale = find_stale_nodes(args.root)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        if args.json_output:
            import json
            print(json.dumps(stale, indent=2))
        else:
            for n in stale:
                print(n)

    elif args.command == "script":
        nodes = scan_nodes(args.root)
        try:
            if args.all:
                target_nodes = find_all_compute_nodes(args.root)
            else:
                target_nodes = find_stale_nodes(args.root)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        if not target_nodes:
            print("Nothing to build." if not args.all else "No compute nodes found.")
        else:
            print(generate_build_script(target_nodes, nodes, args.root))

    elif args.command == "build":
        try:
            if args.json_output:
                built = build_nodes(args.root, node_filter=args.node, sample_rows=0, quiet=True)
                import json
                print(json.dumps({"built": built, "count": len(built)}, indent=2))
            else:
                built = build_nodes(args.root, node_filter=args.node, sample_rows=5)
                if built:
                    print(f"\nBuilt {len(built)} node(s): {', '.join(built)}")
        except ValueError as e:
            if args.json_output:
                import json
                print(json.dumps({"error": str(e)}, indent=2))
            else:
                print(f"ERROR: {e}")
            sys.exit(1)

    elif args.command == "audit":
        import json
        result = audit_node(args.node, args.root) if args.node else audit_descriptions(args.root)
        if args.json_output:
            print(json.dumps(result, indent=2, default=str))
        else:
            if result["drift"]:
                print(f"Schema drift ({len(result['drift'])}):")
                for d in result["drift"]:
                    parts = []
                    if d["added"]:
                        parts.append(f"new: {', '.join(d['added'])}")
                    if d["removed"]:
                        parts.append(f"gone: {', '.join(d['removed'])}")
                    print(f"  {d['node']} → {d['output']}: {'; '.join(parts)}")
                print()
            if result["review_packets"]:
                print(json.dumps(result["review_packets"], indent=2))
            else:
                print("No compute nodes to review.")

    elif args.command == "lineage":
        if not args.node:
            print("ERROR: --node is required for lineage command")
            sys.exit(1)
        nodes = scan_nodes(args.root)
        edges, _ = build_dag(nodes)
        if args.node not in nodes:
            print(f"ERROR: Node not found: {args.node}")
            sys.exit(1)
        up = trace_lineage(args.node, edges, "up")
        down = trace_lineage(args.node, edges, "down")
        print(f"Upstream lineage for {args.node}:")
        for n in up:
            marker = " <-- target" if n == args.node else ""
            print(f"  {n}{marker}")
        print(f"\nDownstream lineage for {args.node}:")
        for n in down:
            marker = " <-- target" if n == args.node else ""
            print(f"  {n}{marker}")

    elif args.command == "diagram":
        render_diagram(args.root, args.output)

    elif args.command == "file-context":
        if not args.file:
            print("ERROR: --file is required for file-context command")
            sys.exit(1)
        import json
        ctx = file_context(args.file, args.root)
        # Strip full metadata to keep output readable — show descriptions only
        if ctx.get("producer_meta"):
            meta = ctx["producer_meta"]
            ctx["producer_meta"] = {
                "description": meta["description"],
                "is_source_node": meta["is_source_node"],
                "sources": meta["sources"],
                "outputs": [{"path": o["path"], "description": o.get("description"),
                             "row_count": o.get("row_count"), "col_count": o.get("col_count")}
                            for o in meta["outputs"]],
                "output_columns": meta.get("output_columns", {}),
                "parameters": meta.get("parameters", []),
            }
        ctx["consumer_metas"] = [
            {"node": consumers, "description": m["description"],
             "sources": m["sources"],
             "outputs": [o["path"] for o in m["outputs"]]}
            for consumers, m in zip(ctx.get("consumers", []), ctx.get("consumer_metas", []))
        ]
        print(json.dumps(ctx, indent=2, default=str))

    elif args.command == "summary":
        import json
        nodes = scan_nodes(args.root)
        if not nodes:
            result = {"node_count": 0, "pipelines": []}
        else:
            edges, _ = build_dag(nodes)
            cycle = detect_cycle(edges)
            components = find_connected_components(edges)
            stale_set = set()
            if not cycle:
                stale_set = set(find_stale_nodes(args.root))

            pipelines = []
            for comp in components:
                # Sort by topological order within component
                order = [n for n in topological_sort(edges) if n in comp]
                source_nodes = [n for n in order if nodes[n]["is_source_node"]]
                compute_nodes = [n for n in order if not nodes[n]["is_source_node"]]
                stale_nodes = [n for n in order if n in stale_set]
                pipelines.append({
                    "nodes": order,
                    "source_count": len(source_nodes),
                    "compute_count": len(compute_nodes),
                    "stale_count": len(stale_nodes),
                    "stale_nodes": stale_nodes,
                    "descriptions": {n: nodes[n]["description"] for n in order},
                    "outputs": {n: [o["path"] for o in nodes[n]["outputs"]] for n in order},
                    "types": {n: "source" if nodes[n]["is_source_node"] else "compute" for n in order},
                })

            result = {
                "node_count": len(nodes),
                "pipeline_count": len(pipelines),
                "cycle": cycle,
                "pipelines": pipelines,
            }

        if args.include_inactive:
            all_nodes = scan_nodes(args.root, include_inactive=True)
            inactive_only = {k: v for k, v in all_nodes.items() if not v.get("is_active", True)}
            result["inactive_count"] = len(inactive_only)
            result["inactive_nodes"] = {k: v["description"] for k, v in inactive_only.items()}

        print(json.dumps(result, indent=2, default=str))

    elif args.command == "show":
        if not args.node:
            print("ERROR: --node is required for show command")
            sys.exit(1)
        import json
        node_path = str(Path(args.root) / args.node)
        meta = ddag_core.read_node(node_path)
        meta["sources_dict"] = ddag_core.get_sources_dict(node_path)
        meta["outputs_dict"] = ddag_core.get_outputs_dict(node_path)
        meta["params_dict"] = ddag_core.get_params_dict(node_path)
        print(json.dumps(meta, indent=2, default=str))

    elif args.command == "dump-function":
        if not args.node:
            print("ERROR: --node is required for dump-function command")
            sys.exit(1)
        node_path = str(Path(args.root) / args.node)
        try:
            out = ddag_core.dump_function(node_path, args.output)
            print(out)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    elif args.command == "load-function":
        if not args.node:
            print("ERROR: --node is required for load-function command")
            sys.exit(1)
        if not args.plan:
            print("ERROR: --plan is required for load-function command (provide updated transform plan)")
            sys.exit(1)
        node_path = str(Path(args.root) / args.node)
        try:
            inp = ddag_core.load_function(node_path, args.plan, args.output)
            print(f"Loaded function from {inp} into {args.node}")
        except (ValueError, FileNotFoundError) as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    elif args.command == "load-script":
        print("ERROR: load-script requires transform plans for changed nodes.")
        print("Use the Python API: ddag_build.load_build_script(path, root, plans={...})")
        sys.exit(1)

    elif args.command == "clean":
        nodes = scan_nodes(args.root)
        root = Path(args.root)
        to_delete = []
        for node_path, meta in nodes.items():
            if meta["is_source_node"]:
                continue
            for out in meta["outputs"]:
                out_path = root / out["path"]
                if out_path.exists():
                    to_delete.append(out["path"])

        if not to_delete:
            print("No compute output files to delete.")
        else:
            print("Will delete:")
            for f in sorted(to_delete):
                print(f"  {f}")
            print(f"\n{len(to_delete)} file(s). Source outputs are untouched.")
            if args.yes:
                answer = "y"
            else:
                answer = input("Proceed? [y/N] ").strip().lower()
            if answer == "y":
                for f in to_delete:
                    (root / f).unlink()
                    print(f"  deleted: {f}")
                print(f"\nDeleted {len(to_delete)} file(s).")
            else:
                print("Aborted.")
