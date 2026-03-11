# Inline Commenting Standards for Transform Code

**Core principle:** Explain *why*, not *what*. Comments should capture business logic, domain knowledge, and non-obvious decisions — not restate what the code already says.

## When to comment

- **Business logic** that isn't obvious from the code (why this filter, why this threshold, why this date cutoff)
- **Edge case handling** — nulls, duplicates, date boundaries, type coercions, and how they're resolved
- **Aggregation/window function choices** with semantic meaning (why sum vs count, why this partition key, why this sort order)
- **Complex joins or filters** that embody domain rules (why inner join excludes certain rows, why this predicate)
- **Data quirks or assumptions** — "column X is nullable before 2023", "source file uses -1 for missing", "grain changes after dedup"

## When to skip comments

- Code is self-explanatory (simple reads, writes, renames, trivial filters)
- You'd just be restating the polars/pandas expression in English
- Trivial transforms (single filter, simple group-by, column selection)

## Transform header

For non-trivial transforms, add a 1-2 line comment at the top of the function body (after imports) explaining the overall approach:

```python
def transform(sources, params, outputs):
    import polars as pl

    # Reconstruct subscription periods from profile snapshots
    # by detecting changes in the account_active_through field
    df = pl.read_parquet(sources['profiles'])
    ...
```

Skip this for simple transforms where the function body is already clear.

## Section comments

For multi-step transforms, comment each logical section with its purpose — like CTE headers in SQL but for pipeline stages within the function:

```python
    # Deduplicate: keep last snapshot per profile per day
    # (multiple syncs per day create duplicates; we only need end-of-day state)
    df = df.sort('sync_time').group_by('profile_id', pl.col('sync_time').dt.date()).last()

    # Detect subscription transitions: flag rows where paid-through date changes
    df = df.with_columns(
        (pl.col('active_through') != pl.col('active_through').shift(1).over('profile_id'))
        .alias('is_transition')
    )
```

## Examples

**Bad:** `# Filter by date`

**Good:** `# Exclude pre-migration data (before 2020) which has inconsistent stripe IDs`

**Bad:** `# Join users and orders`

**Good:** `# Inner join excludes users who never ordered — intentional for active-user analysis`

**Bad:** `# Use max on customer_id`

**Good:** `# MAX prefers non-null, so we get the Stripe ID once it's assigned`

**Bad:** `# Group by user_id and count`

**Good:** (skip — self-explanatory)

## Commenting existing code

When refactoring external code into a node, converting a script, or manually improving comments on an existing node:

1. Read the transform plan — it documents *what* and *why* at a high level
2. Identify sections where the code implements non-obvious business logic
3. Add comments that capture domain knowledge the plan doesn't repeat at the code level
4. Remove any comments that just restate the code
