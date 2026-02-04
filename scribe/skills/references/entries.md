# Entries Reference

Detailed examples for creating entries with the prepare → Edit → finalize flow.

## Example Interaction

> **User:** scribe, log this
>
> **Claude:** Here's what I'll log:
>
> ---
> **14:35 — Fixed null handling in ETL pipeline**
>
> Found that nulls originated from the 2019 migration. Updated `etl.py` to coalesce nulls to zero for pre-2019 records. Validated on test dataset.
>
> **Files touched:** `etl.py`, `exploration.ipynb`
>
> ---
>
> **Archive these files?** (optional)
> - [ ] `etl.py`
> - [ ] `exploration.ipynb`
>
> Let me know if this looks right, or any changes.

Then the user might say:
- "looks good" → Claude runs prepare, Edit, finalize
- "also snapshot etl.py" → Claude adds `--archive "etl.py:Before fix"` to prepare
- "no, the issue was timezone handling not nulls" → Claude revises and re-proposes

## Complete Flow Example

### Step 1: Prepare the entry

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py prepare \
  --touched "etl.py:Added coalesce logic" \
  --touched "config.yaml:Updated timeout"
```

Output: `/path/to/.scribe/__2026-01-23-14-35__.md`

### Step 2: Edit the staging file

Use the Edit tool twice:

1. Replace `__TITLE__` with the actual title:
   - old_string: `__TITLE__`
   - new_string: `Fixed null handling in ETL pipeline`
   - replace_all: true

2. Replace `__BODY__` with the narrative:
   - old_string: `__BODY__`
   - new_string: `Found that nulls originated from the 2019 migration...`

### Step 3: Finalize

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py finalize
```

Output: `Entry finalized: 2026-01-23-14-35`

## Entry Format (Final)

After finalize, the entry in the daily log looks like:

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: Fixed null handling in ETL pipeline
git: abc1234
---
## 14:35 — Fixed null handling in ETL pipeline

Found that nulls originated from the 2019 migration. The legacy system used
empty strings, but the new schema expects actual NULLs. Updated `etl.py` to
coalesce empty strings to NULL for pre-2019 records.

**Files touched:**
- `etl.py` — Added coalesce logic
- `config.yaml` — Updated timeout

---
```

## Git Entry Example

When the user explicitly requests a git entry:

> **User:** scribe, git entry — this fixes the ETL bug

### Step 1: Show what will be committed

```bash
git status
```

### Step 2: Prepare with git-entry flag

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py prepare \
  --git-entry \
  --touched "etl.py:Fixed null handling"
```

### Step 3: Edit title and body (same as regular entry)

### Step 4: Finalize

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py finalize
```

Output:
```
Created commit: def5678
Entry finalized: 2026-01-23-14-35
```

The finalize command stages modified tracked files and creates the commit automatically.

## Archiving Files

When the user wants to archive a file:

> "scribe, save this notebook"
> "scribe, snapshot the ETL script before I refactor"

### Archive Flow

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py prepare \
  --archive "src/analysis/clustering.ipynb:First working version" \
  --touched "clustering.ipynb:Fixed StandardScaler placement"
```

The prepare command:
1. Generates the entry ID
2. Builds the **Archived:** section with correct asset paths
3. Stores archive info in `_pending` for finalize to process

When finalize runs, it copies the files to `.scribe/assets/`.

### Entry with Archive

```markdown
---
id: 2026-01-23-14-35
timestamp: "14:35"
title: First working clustering pipeline
git: abc1234
---
## 14:35 — First working clustering pipeline

Finally got k-means working after fixing the normalization issue.

**Files touched:**
- `clustering.ipynb` — Fixed StandardScaler placement; moved before PCA

**Archived:**
- `src/analysis/clustering.ipynb` → [`2026-01-23-14-35-clustering.ipynb`](assets/2026-01-23-14-35-clustering.ipynb) — First working version

---
```

## Restoring Files

When the user wants to run or inspect an archived file:

1. Use `Grep` in `.scribe/` to find the relevant asset and its original path
2. Use the restore script to copy it to the original directory

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/assets.py get \
  2026-01-23-14-35-clustering.ipynb \
  --dest src/analysis/
```

The script copies to `src/analysis/_2026-01-23-14-35-clustering.ipynb` (underscore prefix makes it obvious).

### List Assets

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/assets.py list
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/assets.py list 2026-01-23
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/assets.py list transform
```

## Related Entries

Link to previous entries when following up:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py prepare \
  --related 2026-01-22-10-15 \
  --touched "etl.py:Added fallback"
```

The prepare command looks up the title automatically and generates:

```markdown
**Related:** 2026-01-22-10-15 — Fixed null handling in ETL pipeline
```

To find the last entry ID:

```bash
uv run --project {SKILL_DIR}/scripts python {SKILL_DIR}/scripts/entry.py last --with-title
```

## What to Capture

- The question, problem, or goal being worked on
- Approaches tried
- What worked, what failed, and why
- Files created or modified, with brief descriptions of changes
- Key discoveries, surprises, or turning points

## User Annotations

The user may add context: `scribe — this was a dead end`. Incorporate their editorial judgment.

## After Finalize

Display a brief summary so the user can verify:

> Logged:
>
> **14:35 — [Title]**
>
> [First sentence or two of the narrative]
>
> *Files touched: `file1.py`, `file2.py`*
>
> *Git: abc1234*
