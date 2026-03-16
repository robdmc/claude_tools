"""test_ddag.py — Test battery for ddag core and build functionality."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Ensure scripts dir is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "scripts"))

import ddag_core
import ddag_build
import ddag_marimo


def setup_test_dir():
    """Create a temp directory with test data."""
    tmp = tempfile.mkdtemp(prefix="ddag_test_")
    # Create a test CSV
    csv_path = os.path.join(tmp, "visits.csv")
    with open(csv_path, "w") as f:
        f.write("date,user_id,page\n")
        f.write("2024-01-01,1,/home\n")
        f.write("2024-01-02,2,/about\n")
        f.write("2024-01-03,1,/pricing\n")
        f.write("2024-01-04,3,/home\n")
        f.write("2024-01-05,2,/signup\n")
    return tmp


def test_source_node(tmp):
    """Test 1: Create a source node wrapping a CSV."""
    print("Test 1: Create source node...", end=" ")
    ddag_path = os.path.join(tmp, "visits.ddag")
    ddag_core.create_source_node(ddag_path, "Raw visit logs from web analytics", ["visits.csv"])

    meta = ddag_core.read_node(ddag_path)
    assert meta["is_source_node"], "Should be a source node"
    assert meta["description"] == "Raw visit logs from web analytics"
    assert meta["sources"] == []
    assert len(meta["outputs"]) == 1
    assert meta["outputs"][0]["path"] == "visits.csv"
    print("PASS")


def test_compute_node(tmp):
    """Test 2: Create a compute node that reads CSV and writes Parquet."""
    print("Test 2: Create compute node...", end=" ")
    ddag_path = os.path.join(tmp, "clean_visits.ddag")

    function_body = '''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df.write_parquet(outputs['clean_visits'])
'''

    ddag_core.create_compute_node(
        ddag_path,
        "Filter visits to recent dates only",
        source_paths=["visits.csv"],
        output_paths=["clean_visits.parquet"],
        function_body=function_body,
        transform_plan="Read visits.csv, filter rows where date >= min_date parameter, write to parquet.",
        params={"min_date": {"type": "str", "value": "2024-01-03", "description": "Minimum date filter"}},
    )

    meta = ddag_core.read_node(ddag_path)
    assert not meta["is_source_node"], "Should be a compute node"
    assert meta["sources"] == ["visits.csv"]
    assert len(meta["outputs"]) == 1
    assert meta["transform_function"] is not None
    assert meta["transform_plan"] == "Read visits.csv, filter rows where date >= min_date parameter, write to parquet."
    assert meta["updated_at"] is not None

    # Test helper dicts
    sources = ddag_core.get_sources_dict(ddag_path)
    assert sources == {"visits": "visits.csv"}
    outputs = ddag_core.get_outputs_dict(ddag_path)
    assert outputs == {"clean_visits": "clean_visits.parquet"}
    params = ddag_core.get_params_dict(ddag_path)
    assert params == {"min_date": "2024-01-03"}
    print("PASS")


def test_dag_assembly(tmp):
    """Test 3: DAG assembly — edges discovered via source/output matching."""
    print("Test 3: DAG assembly...", end=" ")
    nodes = ddag_build.scan_nodes(tmp)
    assert len(nodes) == 2, f"Expected 2 nodes, got {len(nodes)}"

    edges, output_to_node = ddag_build.build_dag(nodes)

    # clean_visits.ddag depends on visits.ddag (via visits.csv)
    clean_key = "clean_visits.ddag"
    visits_key = "visits.ddag"
    assert visits_key in edges[clean_key], f"Expected {visits_key} in deps of {clean_key}"
    assert edges[visits_key] == [], "Source node should have no deps"
    print("PASS")


def test_staleness(tmp):
    """Test 4: Staleness detection."""
    print("Test 4: Staleness detection...", end=" ")
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)

    # Source nodes are never stale
    assert not ddag_build.is_stale("visits.ddag", nodes, edges)
    # Compute node with no built_at is stale
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges)
    print("PASS")


def test_topological_sort(tmp):
    """Test 5: Topological sort."""
    print("Test 5: Topological sort...", end=" ")
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    order = ddag_build.topological_sort(edges)
    visits_idx = order.index("visits.ddag")
    clean_idx = order.index("clean_visits.ddag")
    assert visits_idx < clean_idx, "visits.ddag should come before clean_visits.ddag"
    print("PASS")


def test_build_and_stats(tmp):
    """Test 6: Build execution and output stats update."""
    print("Test 6: Build and stats...", end=" ")
    try:
        import polars as pl
    except ImportError:
        print("SKIP (polars not installed)")
        return

    nodes = ddag_build.scan_nodes(tmp)
    stale = ddag_build.find_stale_nodes(tmp)
    assert "clean_visits.ddag" in stale

    # Generate and execute build script
    script = ddag_build.generate_build_script(stale, nodes, tmp)
    ns = {"__name__": "__main__"}
    exec(compile(script, "<build>", "exec"), ns)

    # Verify output file exists
    output_file = os.path.join(tmp, "clean_visits.parquet")
    assert os.path.exists(output_file), "Output parquet should exist"

    # Update stats
    ddag_build.update_output_stats_after_build("clean_visits.ddag", tmp)

    # Verify stats
    meta = ddag_core.read_node(os.path.join(tmp, "clean_visits.ddag"))
    out = meta["outputs"][0]
    assert out["row_count"] == 3, f"Expected 3 rows, got {out['row_count']}"
    assert out["col_count"] == 3, f"Expected 3 cols, got {out['col_count']}"
    assert out["built_at"] is not None
    print("PASS")


def test_not_stale_after_build(tmp):
    """Test 7: Node should not be stale after successful build."""
    print("Test 7: Not stale after build...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should not be stale after build"
    print("PASS")


def test_stale_after_output_deleted(tmp):
    """Test 7b: Node becomes stale when its output file is deleted."""
    print("Test 7b: Stale after output deleted...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    output_file = os.path.join(tmp, "clean_visits.parquet")
    assert os.path.exists(output_file), "Output should exist from previous build"

    os.remove(output_file)
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should be stale when output is missing"

    # Rebuild to restore state for subsequent tests
    ddag_build.build_nodes(tmp)
    assert os.path.exists(output_file), "Output should be restored after rebuild"
    print("PASS")


def test_stale_after_function_update(tmp):
    """Test 8: Node becomes stale when function is updated."""
    print("Test 8: Stale after function update...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    import time
    time.sleep(0.01)  # Ensure timestamp differs

    new_function = '''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df = df.with_columns(pl.lit(True).alias('filtered'))
    df.write_parquet(outputs['clean_visits'])
'''
    ddag_core.set_function(os.path.join(tmp, "clean_visits.ddag"), new_function,
                           "Read visits.csv, filter rows where date >= min_date, add 'filtered' boolean column, write to parquet.")

    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should be stale after function update"
    print("PASS")


def test_rebuild_stale_only(tmp):
    """Test 9: Rebuild only rebuilds stale nodes."""
    print("Test 9: Rebuild stale only...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    stale = ddag_build.find_stale_nodes(tmp)
    assert "clean_visits.ddag" in stale
    assert "visits.ddag" not in stale, "Source node should not be stale"
    assert len(stale) == 1, f"Expected 1 stale node, got {len(stale)}"
    print("PASS")


def test_cycle_detection(tmp):
    """Test 10: Cycle detection."""
    print("Test 10: Cycle detection...", end=" ")
    # Create two nodes that reference each other's outputs
    ddag_core.create_compute_node(
        os.path.join(tmp, "a.ddag"),
        "Node A", source_paths=["b_out.parquet"], output_paths=["a_out.parquet"],
        function_body="def transform(sources, params, outputs): pass",
        transform_plan="Pass-through from B output.",
    )
    ddag_core.create_compute_node(
        os.path.join(tmp, "b.ddag"),
        "Node B", source_paths=["a_out.parquet"], output_paths=["b_out.parquet"],
        function_body="def transform(sources, params, outputs): pass",
        transform_plan="Pass-through from A output.",
    )

    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    cycle = ddag_build.detect_cycle(edges)
    assert cycle is not None, "Should detect cycle"

    # Also test that find_stale_nodes raises
    try:
        ddag_build.find_stale_nodes(tmp)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Cycle" in str(e)
    print("PASS")


def test_metadata_descriptions(tmp):
    """Test 11: Output and column descriptions."""
    print("Test 11: Metadata descriptions...", end=" ")
    ddag_path = os.path.join(tmp, "clean_visits.ddag")
    ddag_core.set_output_description(ddag_path, "clean_visits.parquet", "Filtered visit logs with recent dates only")
    ddag_core.set_column_descriptions(ddag_path, "clean_visits.parquet", {
        "date": "Visit date in YYYY-MM-DD format",
        "user_id": "Unique user identifier",
        "page": "URL path visited",
    })

    meta = ddag_core.read_node(ddag_path)
    assert meta["outputs"][0]["description"] == "Filtered visit logs with recent dates only"
    cols = meta["output_columns"]["clean_visits.parquet"]
    assert len(cols) == 3
    col_names = {c["name"] for c in cols}
    assert col_names == {"date", "user_id", "page"}
    print("PASS")


def test_clone_and_deactivate(tmp):
    """Test 12: Clone a node and deactivate the original."""
    print("Test 12: Clone and deactivate...", end=" ")
    src = os.path.join(tmp, "clean_visits.ddag")
    dest = os.path.join(tmp, "clean_visits_v2.ddag")

    ddag_core.clone_node(src, dest)
    clone_meta = ddag_core.read_node(dest)
    assert clone_meta["is_active"] is True
    assert clone_meta["branched_from"] == src
    assert clone_meta["transform_function"] is not None

    # Same outputs as original
    orig_meta = ddag_core.read_node(src)
    assert [o["path"] for o in clone_meta["outputs"]] == [o["path"] for o in orig_meta["outputs"]]

    # Deactivate original
    ddag_core.deactivate_node(src)
    assert ddag_core.is_active(src) is False
    assert ddag_core.is_active(dest) is True

    # scan_nodes should only find the clone (not the original)
    nodes = ddag_build.scan_nodes(tmp)
    rel_src = "clean_visits.ddag"
    rel_dest = "clean_visits_v2.ddag"
    assert rel_src not in nodes, "Inactive node should be excluded"
    assert rel_dest in nodes, "Clone should be included"
    print("PASS")


def test_output_conflict_detection(tmp):
    """Test 13: Conflict detection when two active nodes claim same output."""
    print("Test 13: Output conflict detection...", end=" ")
    # Reactivate original so both claim clean_visits.parquet
    src = os.path.join(tmp, "clean_visits.ddag")
    ddag_core.activate_node(src)

    nodes = ddag_build.scan_nodes(tmp)
    conflicts = ddag_build.check_output_conflicts(nodes)
    assert len(conflicts) > 0, "Should detect conflict"
    assert any("clean_visits.parquet" in c[0] for c in conflicts)

    # Deactivate original again to leave state clean
    ddag_core.deactivate_node(src)
    print("PASS")


def test_activate_swap_back(tmp):
    """Test 14: Swap back to original by deactivating clone and reactivating original."""
    print("Test 14: Swap back...", end=" ")
    src = os.path.join(tmp, "clean_visits.ddag")
    dest = os.path.join(tmp, "clean_visits_v2.ddag")

    ddag_core.deactivate_node(dest)
    ddag_core.activate_node(src)

    nodes = ddag_build.scan_nodes(tmp)
    assert "clean_visits.ddag" in nodes
    assert "clean_visits_v2.ddag" not in nodes

    conflicts = ddag_build.check_output_conflicts(nodes)
    assert len(conflicts) == 0, "No conflicts after swap back"
    print("PASS")


def test_build_command(tmp):
    """Test 15: build_nodes executes and returns built nodes."""
    print("Test 15: Build command...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Clean up cycle test nodes
    for f in ["a.ddag", "b.ddag"]:
        p = os.path.join(tmp, f)
        if os.path.exists(p):
            os.remove(p)

    # Also remove inactive clone from earlier tests
    p = os.path.join(tmp, "clean_visits_v2.ddag")
    if os.path.exists(p):
        os.remove(p)

    # Make clean_visits stale by updating function
    import time
    time.sleep(0.01)
    ddag_core.set_function(
        os.path.join(tmp, "clean_visits.ddag"),
        '''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df.write_parquet(outputs['clean_visits'])
''',
        "Read visits.csv, filter rows where date >= min_date parameter, write to parquet.",
    )

    built = ddag_build.build_nodes(tmp)
    assert "clean_visits.ddag" in built
    assert "visits.ddag" not in built, "Source node should not be built"

    # Verify not stale after build
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("clean_visits.ddag", nodes, edges)
    print("PASS")


def test_build_single_node(tmp):
    """Test 16: build_nodes with node_filter builds only that node."""
    print("Test 16: Build single node...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Add a downstream node
    ddag_core.create_compute_node(
        os.path.join(tmp, "agg_visits.ddag"),
        "Aggregate visits by user",
        source_paths=["clean_visits.parquet"],
        output_paths=["agg_visits.parquet"],
        function_body='''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_parquet(sources['clean_visits'])
    agg = df.group_by('user_id').agg(pl.len().alias('visit_count'))
    agg.write_parquet(outputs['agg_visits'])
''',
        transform_plan="Read clean_visits.parquet, group by user_id, count visits per user, write to parquet.",
    )

    built = ddag_build.build_nodes(tmp, node_filter="agg_visits.ddag")
    assert "agg_visits.ddag" in built
    # clean_visits should NOT have been rebuilt (it's already fresh)
    assert "clean_visits.ddag" not in built

    # Clean up the extra node
    os.remove(os.path.join(tmp, "agg_visits.ddag"))
    os.remove(os.path.join(tmp, "agg_visits.parquet"))
    print("PASS")


def test_schema_has_all_columns(tmp):
    """Test 17: Fresh nodes have all expected columns."""
    print("Test 17: Schema has all columns...", end=" ")
    meta = ddag_core.read_node(os.path.join(tmp, "visits.ddag"))
    assert "is_active" in meta
    assert "branched_from" in meta
    assert "force_stale" in meta
    assert meta["is_active"] is True
    assert meta["branched_from"] is None
    assert meta["force_stale"] is False
    print("PASS")


def test_audit_descriptions(tmp):
    """Test 18: Audit builds review packets for compute nodes."""
    print("Test 18: Audit descriptions...", end=" ")
    result = ddag_build.audit_descriptions(tmp)

    # review_packets should have one entry for clean_visits.ddag (the only compute node)
    assert len(result["review_packets"]) == 1
    packet = result["review_packets"][0]
    assert packet["node"] == "clean_visits.ddag"
    assert packet["transform"] is not None
    assert packet["transform_plan"] is not None, "Review packet must include transform_plan"
    assert "parameters" in packet, "Review packet must include parameters"
    assert "drift" in packet, "Review packet must include drift"
    assert len(packet["inputs"]) > 0
    assert len(packet["outputs"]) > 0
    print("PASS")


def test_audit_review_packet_inputs(tmp):
    """Test 19: Review packet includes upstream column descriptions."""
    print("Test 19: Audit review packet inputs...", end=" ")

    # Add column descriptions to visits.ddag
    visits_path = os.path.join(tmp, "visits.ddag")
    ddag_core.set_column_descriptions(visits_path, "visits.csv", {
        "date": "Date of the visit",
        "user_id": "Unique user ID",
        "page": "Page URL path",
    })

    result = ddag_build.audit_descriptions(tmp)
    packet = result["review_packets"][0]
    # The input (visits.csv) should carry the upstream column descriptions
    visits_input = [i for i in packet["inputs"] if i["path"] == "visits.csv"]
    assert len(visits_input) == 1
    assert len(visits_input[0]["columns"]) == 3, "Should have 3 column descriptions from upstream"
    print("PASS")


def test_dump_and_load_function(tmp):
    """Test 20: Round-trip dump and load of transform function."""
    print("Test 20: Dump and load function...", end=" ")
    node_path = os.path.join(tmp, "clean_visits.ddag")
    original = ddag_core.read_node(node_path)["transform_function"]

    # Dump to default path
    out_file = ddag_core.dump_function(node_path)
    assert out_file == "_ddag_clean_visits.py"
    assert os.path.exists(out_file)
    content = open(out_file).read()
    assert "def transform(" in content

    # Edit the file
    modified = content.replace("min_date", "cutoff_date")
    with open(out_file, "w") as f:
        f.write(modified)

    # Load back
    ddag_core.load_function(node_path, "Read visits.csv, filter rows where date >= cutoff_date parameter, write to parquet.")
    updated = ddag_core.read_node(node_path)
    assert "cutoff_date" in updated["transform_function"]
    assert "min_date" not in updated["transform_function"]
    assert "cutoff_date" in updated["transform_plan"]

    # Restore original and clean up
    ddag_core.set_function(node_path, original, "Read visits.csv, filter rows where date >= min_date parameter, write to parquet.")
    os.remove(out_file)

    # Dump to custom path
    custom = os.path.join(tmp, "my_edit.py")
    out_file = ddag_core.dump_function(node_path, custom)
    assert out_file == custom
    assert os.path.exists(custom)
    os.remove(custom)

    # Source node should error
    try:
        ddag_core.dump_function(os.path.join(tmp, "visits.ddag"))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    print("PASS")


def test_load_build_script(tmp):
    """Test 21: Round-trip generate build script, edit, load back."""
    print("Test 21: Load build script...", end=" ")

    # Generate a build script (clean_visits is the only compute node)
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    stale_nodes = [n for n in ddag_build.topological_sort(edges)
                   if not nodes[n]["is_source_node"]]
    script = ddag_build.generate_build_script(stale_nodes, nodes, tmp)

    # Write and verify it parses
    script_path = os.path.join(tmp, "_ddag_build.py")
    with open(script_path, "w") as f:
        f.write(script)

    parsed = ddag_build.parse_build_script(script_path)
    assert "clean_visits.ddag" in parsed
    assert "def transform(" in parsed["clean_visits.ddag"]

    # No changes yet — load should show unchanged
    results = ddag_build.load_build_script(script_path, tmp)
    assert all(not changed for _, changed in results)

    # Now edit the script: change min_date to start_date
    modified = script.replace("min_date", "start_date")
    with open(script_path, "w") as f:
        f.write(modified)

    plans = {"clean_visits.ddag": "Read visits.csv, filter rows where date >= start_date parameter, write to parquet."}
    results = ddag_build.load_build_script(script_path, tmp, plans=plans)
    changed_nodes = [n for n, c in results if c]
    assert "clean_visits.ddag" in changed_nodes

    # Verify the node was updated
    meta = ddag_core.read_node(os.path.join(tmp, "clean_visits.ddag"))
    assert "start_date" in meta["transform_function"]
    assert "min_date" not in meta["transform_function"]
    assert "start_date" in meta["transform_plan"]

    # Restore original
    original_body = parsed["clean_visits.ddag"]
    ddag_core.set_function(os.path.join(tmp, "clean_visits.ddag"), original_body,
                           "Read visits.csv, filter rows where date >= min_date parameter, write to parquet.")

    os.remove(script_path)
    print("PASS")


def test_force_stale_compute_node(tmp):
    """Test 22: force_stale compute node actually rebuilds."""
    print("Test 22: Force stale compute node...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Ensure clean_visits is freshly built
    ddag_build.build_nodes(tmp)
    node_path = os.path.join(tmp, "clean_visits.ddag")

    # Verify not stale
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should not be stale after build"

    # Set force_stale and verify it actually rebuilds
    ddag_core.set_force_stale(node_path)
    meta = ddag_core.read_node(node_path)
    assert meta["force_stale"] is True

    old_built_at = meta["outputs"][0]["built_at"]
    import time; time.sleep(0.01)
    built = ddag_build.build_nodes(tmp)
    assert "clean_visits.ddag" in built, "force_stale node should actually rebuild"

    # Verify built_at updated
    meta = ddag_core.read_node(node_path)
    assert meta["outputs"][0]["built_at"] != old_built_at, "built_at should have updated"

    # force_stale is still set — should still be stale
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should still be stale (flag is sticky)"

    # Clear and verify
    ddag_core.clear_force_stale(node_path)
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Should not be stale after clearing"
    print("PASS")


def test_force_stale_source_rebuilds_downstream(tmp):
    """Test 23: force_stale on source node causes downstream to actually rebuild."""
    print("Test 23: Force stale source rebuilds downstream...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Ensure everything is freshly built
    ddag_build.build_nodes(tmp)
    visits_path = os.path.join(tmp, "visits.ddag")
    clean_path = os.path.join(tmp, "clean_visits.ddag")

    # Record old built_at on downstream node
    old_built_at = ddag_core.read_node(clean_path)["outputs"][0]["built_at"]

    # Force-stale the source node
    import time; time.sleep(0.01)
    ddag_core.set_force_stale(visits_path)

    # Verify staleness
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("visits.ddag", nodes, edges), "Source should be stale"
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Downstream should be stale too"

    # Actually build and verify downstream rebuilt
    built = ddag_build.build_nodes(tmp)
    assert "clean_visits.ddag" in built, "Downstream should have rebuilt"
    new_built_at = ddag_core.read_node(clean_path)["outputs"][0]["built_at"]
    assert new_built_at != old_built_at, "Downstream built_at should have updated"

    # Clean up
    ddag_core.clear_force_stale(visits_path)
    print("PASS")


def test_force_stale_transitive(tmp):
    """Test 24: force_stale propagates staleness transitively (A -> B -> C)."""
    print("Test 24: Force stale transitive...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Add a downstream node: visits -> clean_visits -> agg_visits
    ddag_core.create_compute_node(
        os.path.join(tmp, "agg_visits.ddag"),
        "Aggregate visits by user",
        source_paths=["clean_visits.parquet"],
        output_paths=["agg_visits.parquet"],
        function_body='''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_parquet(sources['clean_visits'])
    agg = df.group_by('user_id').agg(pl.len().alias('visit_count'))
    agg.write_parquet(outputs['agg_visits'])
''',
        transform_plan="Read clean_visits.parquet, group by user_id, count visits per user, write to parquet.",
    )
    ddag_build.build_nodes(tmp, node_filter="agg_visits.ddag")

    # Everything is fresh
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("agg_visits.ddag", nodes, edges)

    # Force-stale the root source node
    ddag_core.set_force_stale(os.path.join(tmp, "visits.ddag"))
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("visits.ddag", nodes, edges), "Source should be stale"
    assert ddag_build.is_stale("clean_visits.ddag", nodes, edges), "Middle node should be stale"
    assert ddag_build.is_stale("agg_visits.ddag", nodes, edges), "Leaf node should be stale (transitive)"

    # Actually build — all compute nodes should rebuild
    import time; time.sleep(0.01)
    built = ddag_build.build_nodes(tmp)
    assert "clean_visits.ddag" in built, "Middle node should rebuild"
    assert "agg_visits.ddag" in built, "Leaf node should rebuild"

    # Clean up
    ddag_core.clear_force_stale(os.path.join(tmp, "visits.ddag"))
    os.remove(os.path.join(tmp, "agg_visits.ddag"))
    os.remove(os.path.join(tmp, "agg_visits.parquet"))
    print("PASS")


def test_force_stale_no_flag_propagation(tmp):
    """Test 25: force_stale flag does NOT propagate — only staleness does."""
    print("Test 25: Force stale flag isolation...", end=" ")

    visits_path = os.path.join(tmp, "visits.ddag")
    clean_path = os.path.join(tmp, "clean_visits.ddag")

    ddag_core.set_force_stale(visits_path)

    # The downstream node should NOT have force_stale set
    meta = ddag_core.read_node(clean_path)
    assert meta["force_stale"] is False, "force_stale flag should not propagate to downstream node"

    ddag_core.clear_force_stale(visits_path)
    print("PASS")


def test_sourceless_compute_same_day(tmp):
    """Test 26: Sourceless compute node is not stale if built today."""
    print("Test 26: Sourceless compute same-day rule...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Create a sourceless compute node (e.g. DB query)
    ddag_path = os.path.join(tmp, "db_fetch.ddag")
    ddag_core.create_compute_node(
        ddag_path,
        "Fetch data from database",
        source_paths=[],
        output_paths=["db_data.parquet"],
        function_body='''def transform(sources, params, outputs):
    import polars as pl
    df = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    df.write_parquet(outputs['db_data'])
''',
        transform_plan="Generate a static test dataframe with id and val columns, write to parquet.",
    )

    # Build it
    built = ddag_build.build_nodes(tmp, node_filter="db_fetch.ddag")
    assert "db_fetch.ddag" in built

    # Should NOT be stale (built today)
    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert not ddag_build.is_stale("db_fetch.ddag", nodes, edges), "Should not be stale if built today"

    # Clean up
    os.remove(ddag_path)
    os.remove(os.path.join(tmp, "db_data.parquet"))
    print("PASS")


def test_sourceless_compute_stale_yesterday(tmp):
    """Test 27: Sourceless compute node is stale if built before today."""
    print("Test 27: Sourceless compute stale yesterday...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    from datetime import datetime, timedelta, timezone

    # Create and build a sourceless node
    ddag_path = os.path.join(tmp, "db_fetch2.ddag")
    ddag_core.create_compute_node(
        ddag_path,
        "Fetch data from database",
        source_paths=[],
        output_paths=["db_data2.parquet"],
        function_body='''def transform(sources, params, outputs):
    import polars as pl
    df = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    df.write_parquet(outputs['db_data2'])
''',
        transform_plan="Generate a static test dataframe with id and val columns, write to parquet.",
    )
    ddag_build.build_nodes(tmp, node_filter="db_fetch2.ddag")

    # Backdate the built_at to yesterday
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    db = __import__("sqlite3").connect(ddag_path)
    db.execute("UPDATE outputs SET built_at = ?", (yesterday,))
    db.commit()
    db.close()

    nodes = ddag_build.scan_nodes(tmp)
    edges, _ = ddag_build.build_dag(nodes)
    assert ddag_build.is_stale("db_fetch2.ddag", nodes, edges), "Should be stale if built yesterday"

    # Clean up
    os.remove(ddag_path)
    os.remove(os.path.join(tmp, "db_data2.parquet"))
    print("PASS")


def test_transform_plan_required(tmp):
    """Test 29: transform_plan is required for compute nodes and set_function."""
    print("Test 29: Transform plan required...", end=" ")

    # create_compute_node without plan should fail
    try:
        ddag_core.create_compute_node(
            os.path.join(tmp, "bad.ddag"),
            "Bad node", source_paths=[], output_paths=["bad.parquet"],
            function_body="def transform(sources, params, outputs): pass",
            transform_plan=None,
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "transform_plan" in str(e)

    # Empty string plan should also fail
    try:
        ddag_core.create_compute_node(
            os.path.join(tmp, "bad.ddag"),
            "Bad node", source_paths=[], output_paths=["bad.parquet"],
            function_body="def transform(sources, params, outputs): pass",
            transform_plan="",
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "transform_plan" in str(e)

    # set_function without plan should fail
    try:
        ddag_core.set_function(
            os.path.join(tmp, "clean_visits.ddag"),
            "def transform(sources, params, outputs): pass",
            None,
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "transform_plan" in str(e)

    print("PASS")


def test_force_stale_default(tmp):
    """Test 28: New nodes default to force_stale=False."""
    print("Test 28: Force stale default...", end=" ")
    ddag_path = os.path.join(tmp, "fresh.ddag")
    ddag_core.create_source_node(ddag_path, "Fresh node", ["fresh.csv"])
    meta = ddag_core.read_node(ddag_path)
    assert meta["force_stale"] is False
    os.remove(ddag_path)
    print("PASS")


def test_marimo_generate_notebook(tmp):
    """Test 30: Notebook generation produces valid Python with correct structure."""
    print("Test 30: Marimo notebook generation...", end=" ")
    function_body = '''def transform(sources, params, outputs):
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.filter(pl.col('date') >= params['min_date'])
    df.write_parquet(outputs['clean_visits'])
'''
    sources = {"visits": "data/visits.csv"}
    outputs = {"clean_visits": "pipeline/clean_visits.parquet"}
    params = {"min_date": "2023-01-01"}

    content = ddag_marimo.generate_notebook(function_body, sources, outputs, params)

    # Should be valid Python
    compile(content, "<notebook>", "exec")

    # Should contain the key structural elements
    assert "import marimo" in content
    assert "app = marimo.App()" in content
    assert "@app.function" in content
    assert "def transform(sources, params, outputs):" in content
    assert "@app.cell" in content

    # Dict values should appear
    assert "'data/visits.csv'" in content
    assert "'pipeline/clean_visits.parquet'" in content
    assert "'2023-01-01'" in content

    print("PASS")


def test_marimo_source_node_rejection(tmp):
    """Test 31: Marimo export rejects source nodes."""
    print("Test 31: Marimo source node rejection...", end=" ")
    visits_path = os.path.join(tmp, "visits.ddag")

    try:
        ddag_marimo.export_notebook(visits_path)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "source node" in str(e)

    print("PASS")


def test_marimo_round_trip(tmp):
    """Test 32: Export → modify notebook → import updates node."""
    print("Test 32: Marimo round-trip...", end=" ")
    node_path = os.path.join(tmp, "clean_visits.ddag")
    original_meta = ddag_core.read_node(node_path)
    original_body = original_meta["transform_function"]

    # Export
    old_cwd = os.getcwd()
    os.chdir(tmp)
    try:
        nb_path = ddag_marimo.export_notebook(node_path, root=tmp)
        assert nb_path == "clean_visits.ddag.nb.py"
        assert os.path.exists(nb_path)

        # Verify the notebook is valid Python
        nb_content = open(nb_path).read()
        compile(nb_content, nb_path, "exec")

        # Modify the transform in the notebook (change min_date to start_date)
        modified = nb_content.replace("min_date", "start_date")
        with open(nb_path, "w") as f:
            f.write(modified)

        # Import back
        _, changed = ddag_marimo.import_notebook(node_path, nb_path)
        assert changed, "Should detect changes"

        # Verify the node was updated
        updated_meta = ddag_core.read_node(node_path)
        assert "start_date" in updated_meta["transform_function"]
        assert "min_date" not in updated_meta["transform_function"]

        # Import again with no changes — should detect no change
        _, changed2 = ddag_marimo.import_notebook(node_path, nb_path)
        assert not changed2, "Should detect no changes on second import"

        # Restore original
        ddag_core.set_function(node_path, original_body,
                               "Read visits.csv, filter rows where date >= min_date parameter, write to parquet.")
        os.remove(nb_path)
    finally:
        os.chdir(old_cwd)

    print("PASS")


def test_marimo_output_file_naming(tmp):
    """Test 33: Notebook output file uses <stem>.ddag.nb.py convention."""
    print("Test 33: Marimo output file naming...", end=" ")
    node_path = os.path.join(tmp, "clean_visits.ddag")

    old_cwd = os.getcwd()
    os.chdir(tmp)
    try:
        nb_path = ddag_marimo.export_notebook(node_path, root=tmp)
        assert nb_path == "clean_visits.ddag.nb.py"
        os.remove(nb_path)
    finally:
        os.chdir(old_cwd)

    print("PASS")


def test_marimo_extract_transform(tmp):
    """Test 34: Extract transform from notebook AST."""
    print("Test 34: Marimo extract transform...", end=" ")
    # Create a minimal notebook file
    notebook_content = '''\
import marimo

app = marimo.App()


@app.cell
def transform_cell():
    def transform(sources, params, outputs):
        import polars as pl
        df = pl.read_csv(sources['visits'])
        df.write_parquet(outputs['clean'])
    return (transform,)


if __name__ == "__main__":
    app.run()
'''
    nb_file = os.path.join(tmp, "test_extract.nb.py")
    with open(nb_file, "w") as f:
        f.write(notebook_content)

    result = ddag_marimo.extract_transform_from_notebook(nb_file)
    assert result is not None
    assert "import polars as pl" in result
    assert "pl.read_csv" in result
    # Returns body only (no def line) per @app.function extraction
    assert "def transform(" not in result

    os.remove(nb_file)
    print("PASS")


def test_marimo_check_fix_round_trip(tmp):
    """Test 36: Export → marimo check --fix → edit → reimport."""
    print("Test 36: Marimo check --fix round-trip...", end=" ")
    import shutil as _shutil
    marimo_bin = _shutil.which("marimo")
    if not marimo_bin:
        print("SKIP (marimo not installed)")
        return

    import subprocess
    node_path = os.path.join(tmp, "clean_visits.ddag")
    original_meta = ddag_core.read_node(node_path)
    original_body = original_meta["transform_function"]

    old_cwd = os.getcwd()
    os.chdir(tmp)
    try:
        # Export
        nb_path = ddag_marimo.export_notebook(node_path, root=tmp)
        assert os.path.exists(nb_path)

        # marimo check --fix (export_notebook already runs this, but verify it's clean)
        result = subprocess.run(
            [marimo_bin, "check", nb_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"marimo check failed after export: {result.stderr}"

        # Edit the notebook: add a comment inside the transform
        nb_content = open(nb_path).read()
        modified = nb_content.replace(
            "import polars as pl",
            "import polars as pl\n    # Added by test edit",
        )
        assert modified != nb_content, "Edit should change content"
        with open(nb_path, "w") as f:
            f.write(modified)

        # Run marimo check --fix on the edited notebook (as a user would)
        result = subprocess.run(
            [marimo_bin, "check", "--fix", nb_path],
            capture_output=True, text=True,
        )
        # Re-read after fix (marimo may reformat)
        fixed_content = open(nb_path).read()
        assert "# Added by test edit" in fixed_content, "Edit should survive marimo check --fix"

        # Import back
        _, changed = ddag_marimo.import_notebook(node_path, nb_path)
        assert changed, "Should detect changes after edit"

        # Verify the node was updated with the comment
        updated_meta = ddag_core.read_node(node_path)
        assert "# Added by test edit" in updated_meta["transform_function"]

        # Restore original
        ddag_core.set_function(node_path, original_body,
                               "Read visits.csv, filter rows where date >= min_date parameter, write to parquet.")
        os.remove(nb_path)
    finally:
        os.chdir(old_cwd)

    print("PASS")


def test_settings_no_file(tmp):
    """Test 37: Transform using ddag_settings fails when no settings file exists."""
    print("Test 37: Settings — no file present...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Create a node whose transform imports ddag_settings
    ddag_path = os.path.join(tmp, "with_settings.ddag")
    ddag_core.create_compute_node(
        ddag_path,
        "Node that uses project settings",
        source_paths=["visits.csv"],
        output_paths=["settings_out.parquet"],
        function_body='''def transform(sources, params, outputs):
    from ddag_settings import settings
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.head(settings.max_rows)
    df.write_parquet(outputs['settings_out'])
''',
        transform_plan="Read visits.csv, limit to settings.max_rows rows, write to parquet.",
    )

    # Ensure no ddag_settings module is cached or importable from tmp
    settings_path = os.path.join(tmp, "ddag_settings.py")
    if os.path.exists(settings_path):
        os.remove(settings_path)
    sys.modules.pop("ddag_settings", None)

    # Build should fail because ddag_settings.py doesn't exist
    try:
        ddag_build.build_nodes(tmp, node_filter="with_settings.ddag")
        assert False, "Should have raised due to missing ddag_settings"
    except Exception as e:
        assert "ddag_settings" in str(e) or "No module named" in str(e), f"Unexpected error: {e}"

    # Clean up
    os.remove(ddag_path)
    output_path = os.path.join(tmp, "settings_out.parquet")
    if os.path.exists(output_path):
        os.remove(output_path)
    print("PASS")


def test_settings_with_file(tmp):
    """Test 38: Transform using ddag_settings works when settings file exists."""
    print("Test 38: Settings — file present...", end=" ")
    try:
        import polars  # noqa: F401
    except ImportError:
        print("SKIP (polars not installed)")
        return

    # Create ddag_settings.py in the project root (tmp)
    settings_path = os.path.join(tmp, "ddag_settings.py")
    with open(settings_path, "w") as f:
        f.write('''\
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    max_rows: int = 3

settings = Settings()
''')

    # Create a node that imports settings
    ddag_path = os.path.join(tmp, "with_settings.ddag")
    ddag_core.create_compute_node(
        ddag_path,
        "Node that uses project settings",
        source_paths=["visits.csv"],
        output_paths=["settings_out.parquet"],
        function_body='''def transform(sources, params, outputs):
    from ddag_settings import settings
    import polars as pl
    df = pl.read_csv(sources['visits'])
    df = df.head(settings.max_rows)
    df.write_parquet(outputs['settings_out'])
''',
        transform_plan="Read visits.csv, limit to settings.max_rows rows, write to parquet.",
    )

    # Build should succeed
    built = ddag_build.build_nodes(tmp, node_filter="with_settings.ddag")
    assert "with_settings.ddag" in built, "Node should have built successfully"

    # Verify output: visits.csv has 5 rows, max_rows=3 so output should have 3
    import polars as pl
    df = pl.read_parquet(os.path.join(tmp, "settings_out.parquet"))
    assert len(df) == 3, f"Expected 3 rows (settings.max_rows), got {len(df)}"

    # Clean up
    os.remove(ddag_path)
    os.remove(os.path.join(tmp, "settings_out.parquet"))
    os.remove(settings_path)
    sys.modules.pop("ddag_settings", None)
    print("PASS")


def test_marimo_empty_dicts(tmp):
    """Test 35: Notebook generation handles empty dicts."""
    print("Test 35: Marimo empty dicts...", end=" ")
    function_body = '''def transform(sources, params, outputs):
    pass
'''
    content = ddag_marimo.generate_notebook(function_body, {}, {}, {})
    compile(content, "<notebook>", "exec")
    assert "sources = {}" in content
    assert "params = {}" in content
    assert "outputs = {}" in content
    print("PASS")


def main():
    tmp = setup_test_dir()
    print(f"Test directory: {tmp}\n")
    try:
        test_source_node(tmp)
        test_compute_node(tmp)
        test_dag_assembly(tmp)
        test_staleness(tmp)
        test_topological_sort(tmp)
        test_build_and_stats(tmp)
        test_not_stale_after_build(tmp)
        test_stale_after_output_deleted(tmp)
        test_stale_after_function_update(tmp)
        test_rebuild_stale_only(tmp)
        test_cycle_detection(tmp)
        test_metadata_descriptions(tmp)
        test_clone_and_deactivate(tmp)
        test_output_conflict_detection(tmp)
        test_activate_swap_back(tmp)
        test_build_command(tmp)
        test_build_single_node(tmp)
        test_schema_has_all_columns(tmp)
        test_audit_descriptions(tmp)
        test_audit_review_packet_inputs(tmp)
        test_dump_and_load_function(tmp)
        test_load_build_script(tmp)
        test_force_stale_compute_node(tmp)
        test_force_stale_source_rebuilds_downstream(tmp)
        test_force_stale_transitive(tmp)
        test_force_stale_no_flag_propagation(tmp)
        test_sourceless_compute_same_day(tmp)
        test_sourceless_compute_stale_yesterday(tmp)
        test_force_stale_default(tmp)
        test_transform_plan_required(tmp)
        test_settings_no_file(tmp)
        test_settings_with_file(tmp)
        test_marimo_generate_notebook(tmp)
        test_marimo_source_node_rejection(tmp)
        test_marimo_round_trip(tmp)
        test_marimo_output_file_naming(tmp)
        test_marimo_extract_transform(tmp)
        test_marimo_empty_dicts(tmp)
        test_marimo_check_fix_round_trip(tmp)
        print("\nAll tests passed!")
    finally:
        shutil.rmtree(tmp)
        print(f"Cleaned up {tmp}")


if __name__ == "__main__":
    main()
