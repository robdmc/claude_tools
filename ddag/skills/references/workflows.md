# ddag Advanced Workflows

## Contents

- [Script Conversion](#script-conversion)
- [Branching (Exploratory Workflows)](#branching-exploratory-workflows)
- [DAG-wide Audit](#dag-wide-audit)

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

Use `clone_node`, `deactivate_node`, and `activate_node` from `ddag_core` (see `references/api.md` for signatures).

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
   - Cross-cutting — is the node description accurate? Are pass-through columns consistent with upstream?

3. **Collect results**: Each agent returns either `CONSISTENT` (one line) or `INCONSISTENT` with a list of specific issues.

4. **Surface inconsistencies**: Present any `INCONSISTENT` results to the user. For each inconsistency, the user decides whether to fix the code (via `set_function`) or the metadata (via `set_output_description`, `set_column_descriptions`, etc.).

### Example

```python
result = ddag_build.audit_descriptions('.')
# result["review_packets"] has one entry per compute node
# Spawn one node-auditor agent per packet, collect results, present issues
```

For small DAGs (1-3 compute nodes), running auditors sequentially is fine. For larger DAGs, always run in parallel.
