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

Run `audit` (`python {SKILL_DIR}/scripts/ddag_build.py audit --root .`) to check description health across the entire DAG. Both phases below are mandatory — deterministic checks alone miss stale or inaccurate descriptions.

### Phase 1 — Deterministic checks

The command reports missing descriptions and schema drift (new/removed columns since last description update). Fix any drift by:
- Adding descriptions for new columns via `ddag_core.set_column_descriptions()`
- Removing stale column descriptions for columns that no longer exist

### Phase 2 — Semantic review

The command emits a **review packet** per compute node containing: input descriptions (from upstream producers), the node's transform code, and the node's output descriptions. For each packet, verify:

- Does the node description accurately reflect what the transform does?
- Does the output file description match the actual content produced?
- Are column descriptions accurate given what the code does to them? (e.g., if the code does `group_by('user_id').count()`, the output `user_id` is now "Group key" not "Unique user identifier")
- Are pass-through columns described consistently with their upstream source?

For large DAGs, review packets in parallel using subagents — one per node or batch of nodes. Propose corrections via `ddag_core.set_output_description()` and `ddag_core.set_column_descriptions()`, presenting changes to the user before applying.
